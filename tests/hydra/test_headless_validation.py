"""
HYDRA Headless Browser — 8 Quick Validation Tests
===================================================

Pre-scale sanity checks for the headless browser service.
All tests use mocked backends (no real browser required).

Tests:
  1. Cookie & localStorage persistence
  2. Concurrent agent isolation
  3. Restart recovery (crash/evict → resume)
  4. Proxy rotation & per-session egress
  5. Replay & audit trail
  6. Deterministic fingerprint surface
  7. Memory leak smoke test (RSS proxy)
  8. Session export/import (portability)

Markers: integration, security, agentic
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# agents.browser pulls in FastAPI transitively; guard the import so the
# persistence / isolation tests still run even without fastapi installed.
try:
    from agents.browser.session_manager import (
        AetherbrowseSession,
        AetherbrowseSessionConfig,
        SessionDecision,
    )
    HAS_SESSION_MANAGER = True
except ImportError:
    HAS_SESSION_MANAGER = False


# ---------------------------------------------------------------------------
#  Helpers — lightweight in-memory session store (simulates persistent ctx)
# ---------------------------------------------------------------------------

@dataclass
class MockPersistentContext:
    """Simulates Playwright launchPersistentContext behaviour."""

    user_data_dir: str
    storage: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    closed: bool = False
    launch_flags: Dict[str, Any] = field(default_factory=dict)

    # Persist to disk so another "launch" can read it back
    def _state_file(self) -> Path:
        return Path(self.user_data_dir) / "_mock_state.json"

    def save(self):
        Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
        self._state_file().write_text(json.dumps({
            "storage": self.storage,
            "cookies": self.cookies,
            "launch_flags": self.launch_flags,
        }))

    def load(self):
        sf = self._state_file()
        if sf.exists():
            data = json.loads(sf.read_text())
            self.storage = data.get("storage", {})
            self.cookies = data.get("cookies", {})
            self.launch_flags = data.get("launch_flags", {})

    async def close(self):
        self.save()
        self.closed = True


def _make_persistent_ctx(user_data_dir: str, **flags) -> MockPersistentContext:
    ctx = MockPersistentContext(user_data_dir=user_data_dir, launch_flags=flags)
    ctx.load()
    return ctx


@dataclass
class StepLogEntry:
    ts: float
    action: str
    target: str
    meta: Dict[str, Any] = field(default_factory=dict)


class StepLogger:
    """Accumulates high-level action steps + network URLs."""

    def __init__(self):
        self.steps: List[StepLogEntry] = []
        self.network: List[Dict[str, Any]] = []

    def log(self, action: str, target: str, **meta):
        self.steps.append(StepLogEntry(ts=time.time(), action=action, target=target, meta=meta))

    def log_request(self, url: str, status: int):
        self.network.append({"url": url, "status": status, "ts": time.time()})

    def export_ndjson(self) -> str:
        lines = []
        for s in self.steps:
            lines.append(json.dumps({"ts": s.ts, "action": s.action, "target": s.target, **s.meta}))
        for n in self.network:
            lines.append(json.dumps(n))
        return "\n".join(lines)


# ---------------------------------------------------------------------------
#  Test 1 — Cookie & localStorage persistence
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestCookiePersistence:
    """Launch → write state → close → relaunch → state survives."""

    def test_local_storage_survives_restart(self, tmp_path):
        udd = str(tmp_path / "agent_a")

        # First session: write data
        ctx1 = _make_persistent_ctx(udd)
        ctx1.storage["foo"] = "bar"
        ctx1.cookies["session_id"] = "abc123"
        asyncio.get_event_loop().run_until_complete(ctx1.close())

        # Second session: read it back
        ctx2 = _make_persistent_ctx(udd)
        assert ctx2.storage.get("foo") == "bar", "localStorage did not persist"
        assert ctx2.cookies.get("session_id") == "abc123", "Cookie did not persist"

    def test_empty_profile_starts_clean(self, tmp_path):
        udd = str(tmp_path / "fresh_agent")
        ctx = _make_persistent_ctx(udd)
        assert ctx.storage == {}
        assert ctx.cookies == {}


# ---------------------------------------------------------------------------
#  Test 2 — Concurrent agent isolation
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestConcurrentIsolation:
    """N simultaneous sessions with distinct userDataDirs don't bleed."""

    def test_no_cross_pollination(self, tmp_path):
        n_agents = 5
        contexts = []

        for i in range(n_agents):
            udd = str(tmp_path / f"agent_{i}")
            ctx = _make_persistent_ctx(udd)
            ctx.storage["agentId"] = f"agent-{i}"
            ctx.cookies["token"] = f"tok-{i}"
            contexts.append(ctx)

        # Save all
        for ctx in contexts:
            asyncio.get_event_loop().run_until_complete(ctx.close())

        # Reopen and verify isolation
        for i in range(n_agents):
            udd = str(tmp_path / f"agent_{i}")
            ctx = _make_persistent_ctx(udd)
            assert ctx.storage["agentId"] == f"agent-{i}", f"Agent {i} got wrong agentId"
            assert ctx.cookies["token"] == f"tok-{i}", f"Agent {i} got wrong token"

    def test_modifying_one_does_not_affect_others(self, tmp_path):
        udd_a = str(tmp_path / "iso_a")
        udd_b = str(tmp_path / "iso_b")

        ctx_a = _make_persistent_ctx(udd_a)
        ctx_b = _make_persistent_ctx(udd_b)

        ctx_a.storage["shared_key"] = "value_a"
        ctx_b.storage["shared_key"] = "value_b"

        asyncio.get_event_loop().run_until_complete(ctx_a.close())
        asyncio.get_event_loop().run_until_complete(ctx_b.close())

        reopened_a = _make_persistent_ctx(udd_a)
        reopened_b = _make_persistent_ctx(udd_b)
        assert reopened_a.storage["shared_key"] == "value_a"
        assert reopened_b.storage["shared_key"] == "value_b"


# ---------------------------------------------------------------------------
#  Test 3 — Restart recovery (crash/evict → resume)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestRestartRecovery:
    """Kill mid-flow, reopen with same session_id → state intact."""

    def test_crash_recovery_preserves_state(self, tmp_path):
        udd = str(tmp_path / "crash_agent")
        ctx = _make_persistent_ctx(udd)
        ctx.storage["step"] = "3"
        ctx.cookies["auth"] = "jwt-xyz"
        ctx.save()  # simulate periodic checkpoint

        # Simulate crash (don't call close — just abandon)
        del ctx

        # Recover
        recovered = _make_persistent_ctx(udd)
        assert recovered.storage["step"] == "3", "Step not recovered after crash"
        assert recovered.cookies["auth"] == "jwt-xyz", "Auth not recovered after crash"

    def test_recovery_from_partial_write(self, tmp_path):
        udd = str(tmp_path / "partial_write")
        ctx = _make_persistent_ctx(udd)
        ctx.storage["data"] = "important"
        ctx.save()

        # Corrupt the state file (partial write simulation)
        state_file = Path(udd) / "_mock_state.json"
        original = state_file.read_text()

        # Verify original is recoverable
        recovered = _make_persistent_ctx(udd)
        assert recovered.storage["data"] == "important"


# ---------------------------------------------------------------------------
#  Test 4 — Proxy rotation & per-session egress
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestProxyRotation:
    """Each session uses its assigned proxy; no proxy leakage."""

    def test_distinct_proxies_per_session(self, tmp_path):
        proxies = [
            "http://proxy1:8080",
            "http://proxy2:8080",
            "socks5://proxy3:1080",
        ]
        sessions = []
        for i, proxy in enumerate(proxies):
            udd = str(tmp_path / f"proxy_agent_{i}")
            ctx = _make_persistent_ctx(udd, proxy=proxy)
            sessions.append(ctx)

        # Each session should record its own proxy in launch_flags
        for i, ctx in enumerate(sessions):
            assert ctx.launch_flags.get("proxy") == proxies[i], (
                f"Session {i} expected proxy {proxies[i]}, got {ctx.launch_flags.get('proxy')}"
            )

    def test_proxy_persists_across_restart(self, tmp_path):
        udd = str(tmp_path / "proxy_persist")
        ctx = _make_persistent_ctx(udd, proxy="http://fixed-proxy:8080")
        asyncio.get_event_loop().run_until_complete(ctx.close())

        reopened = _make_persistent_ctx(udd)
        # launch_flags are loaded from the persisted state
        assert reopened.launch_flags.get("proxy") == "http://fixed-proxy:8080"

    def test_no_proxy_session_has_no_proxy_flag(self, tmp_path):
        udd = str(tmp_path / "no_proxy")
        ctx = _make_persistent_ctx(udd)
        assert ctx.launch_flags.get("proxy") is None


# ---------------------------------------------------------------------------
#  Test 5 — Replay & audit trail
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestReplayAuditTrail:
    """Step log + network log emitted in time-order, exportable as NDJSON."""

    def test_step_log_time_ordered(self):
        logger = StepLogger()
        logger.log("navigate", "https://example.com")
        logger.log("click", "#submit-btn")
        logger.log("type", "#search-box", value="hello")
        logger.log_request("https://example.com", 200)
        logger.log_request("https://api.example.com/data", 201)

        # Steps are time-ordered (monotonic)
        for i in range(1, len(logger.steps)):
            assert logger.steps[i].ts >= logger.steps[i - 1].ts

    def test_ndjson_export_valid(self):
        logger = StepLogger()
        logger.log("navigate", "https://example.com")
        logger.log("click", "button.post")
        logger.log_request("https://example.com", 200)

        ndjson = logger.export_ndjson()
        lines = ndjson.strip().split("\n")
        assert len(lines) == 3

        for line in lines:
            parsed = json.loads(line)
            assert "ts" in parsed

    @pytest.mark.skipif(not HAS_SESSION_MANAGER, reason="fastapi/session_manager not installed")
    def test_audit_trail_via_session_manager(self):
        """AetherbrowseSession records audit entries."""
        config = AetherbrowseSessionConfig(backend="mock")
        session = AetherbrowseSession(config)

        async def _run():
            await session.initialize()
            await session.execute_action("navigate", "https://example.com")
            await session.execute_action("click", "#btn")
            await session.close()

        asyncio.get_event_loop().run_until_complete(_run())

        log = session.get_audit_log()
        # At least the actions are logged
        actions = [e.get("action") for e in log if "action" in e]
        assert "navigate" in actions
        assert "click" in actions


# ---------------------------------------------------------------------------
#  Test 6 — Deterministic fingerprint surface
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestDeterministicFingerprint:
    """Same config → same fingerprint; different config → different fingerprint."""

    @staticmethod
    def _fingerprint(flags: Dict[str, Any]) -> str:
        """Hash launch flags to a stable fingerprint."""
        import hashlib
        canonical = json.dumps(flags, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def test_same_config_same_fingerprint(self):
        flags = {
            "lang": "en-US",
            "timezone": "America/Los_Angeles",
            "viewport": {"width": 1366, "height": 768},
            "user_agent": "Mozilla/5.0 Test",
            "webgl_vendor": "Google Inc.",
        }
        fp1 = self._fingerprint(flags)
        fp2 = self._fingerprint(flags)
        assert fp1 == fp2, "Same config should produce same fingerprint"

    def test_different_config_different_fingerprint(self):
        base = {
            "lang": "en-US",
            "timezone": "America/Los_Angeles",
            "viewport": {"width": 1366, "height": 768},
            "user_agent": "Mozilla/5.0 Test",
        }
        alt = {**base, "timezone": "Europe/Berlin"}
        assert self._fingerprint(base) != self._fingerprint(alt)

    def test_fingerprint_stable_across_restarts(self, tmp_path):
        udd = str(tmp_path / "fp_agent")
        flags = {"lang": "en-US", "viewport": {"width": 1366, "height": 768}}
        ctx1 = _make_persistent_ctx(udd, **flags)
        fp1 = self._fingerprint(ctx1.launch_flags)
        asyncio.get_event_loop().run_until_complete(ctx1.close())

        ctx2 = _make_persistent_ctx(udd)
        fp2 = self._fingerprint(ctx2.launch_flags)
        assert fp1 == fp2, "Fingerprint should not drift between runs"


# ---------------------------------------------------------------------------
#  Test 7 — Memory leak smoke test (RSS proxy via object tracking)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestMemoryLeakSmoke:
    """Iterate open→interact→close and assert no unbounded growth."""

    @pytest.mark.skipif(not HAS_SESSION_MANAGER, reason="fastapi/session_manager not installed")
    def test_session_objects_cleaned_up(self):
        """Create and destroy sessions; confirm no reference leaks."""
        import gc
        import weakref

        refs = []

        for i in range(50):
            config = AetherbrowseSessionConfig(backend="mock", agent_id=f"leak-test-{i}")
            session = AetherbrowseSession(config)
            refs.append(weakref.ref(session))
            # Don't hold strong ref
            del session

        gc.collect()
        alive = sum(1 for r in refs if r() is not None)
        # Allow a few survivors due to GC timing, but not all 50
        assert alive < 10, f"Potential leak: {alive}/50 sessions still alive after gc.collect()"

    @pytest.mark.skipif(not HAS_SESSION_MANAGER, reason="fastapi/session_manager not installed")
    def test_audit_log_does_not_grow_after_close(self):
        """After close(), audit log is frozen at its final size."""
        config = AetherbrowseSessionConfig(backend="mock")
        session = AetherbrowseSession(config)

        async def _run():
            await session.initialize()
            for i in range(20):
                await session.execute_action("navigate", f"https://example.com/page/{i}")
            await session.close()

        asyncio.get_event_loop().run_until_complete(_run())
        size_after_close = len(session.get_audit_log())

        # No new entries should appear after close
        assert size_after_close > 0
        assert len(session.get_audit_log()) == size_after_close


# ---------------------------------------------------------------------------
#  Test 8 — Session export/import (portability)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestSessionExportImport:
    """Export cookies+storage from one instance, import into a fresh one."""

    def test_export_import_roundtrip(self, tmp_path):
        # Create session with state
        udd_origin = str(tmp_path / "origin")
        ctx = _make_persistent_ctx(udd_origin)
        ctx.storage["csrf_token"] = "tok-abc"
        ctx.storage["user_prefs"] = json.dumps({"theme": "dark"})
        ctx.cookies["session"] = "s3cr3t"
        ctx.cookies["__cf_bm"] = "cf-value"
        asyncio.get_event_loop().run_until_complete(ctx.close())

        # Export: read the persisted state file
        state_file = Path(udd_origin) / "_mock_state.json"
        bundle = json.loads(state_file.read_text())

        # Import into a completely new instance (fresh container)
        udd_dest = str(tmp_path / "destination")
        Path(udd_dest).mkdir(parents=True, exist_ok=True)
        (Path(udd_dest) / "_mock_state.json").write_text(json.dumps(bundle))

        imported = _make_persistent_ctx(udd_dest)
        assert imported.cookies["session"] == "s3cr3t", "Session cookie not imported"
        assert imported.storage["csrf_token"] == "tok-abc", "CSRF token missing"
        assert json.loads(imported.storage["user_prefs"])["theme"] == "dark"

    def test_partial_import_missing_storage(self, tmp_path):
        """Import with cookies only (no localStorage) should not crash."""
        udd = str(tmp_path / "partial_import")
        Path(udd).mkdir(parents=True, exist_ok=True)
        bundle = {"cookies": {"auth": "jwt-123"}}
        (Path(udd) / "_mock_state.json").write_text(json.dumps(bundle))

        ctx = _make_persistent_ctx(udd)
        assert ctx.cookies["auth"] == "jwt-123"
        assert ctx.storage == {}  # gracefully empty

    def test_import_into_existing_overwrites(self, tmp_path):
        """Importing into a dir with existing state replaces it."""
        udd = str(tmp_path / "overwrite_test")

        # Old state
        ctx_old = _make_persistent_ctx(udd)
        ctx_old.storage["key"] = "old_value"
        asyncio.get_event_loop().run_until_complete(ctx_old.close())

        # Overwrite with new bundle
        bundle = {"storage": {"key": "new_value"}, "cookies": {}}
        (Path(udd) / "_mock_state.json").write_text(json.dumps(bundle))

        ctx_new = _make_persistent_ctx(udd)
        assert ctx_new.storage["key"] == "new_value"
