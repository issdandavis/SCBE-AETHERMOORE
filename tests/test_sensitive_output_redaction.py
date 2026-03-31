from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

try:
    from cryptography.fernet import Fernet  # noqa: F401
except Exception:
    pytest.skip(
        "cryptography package not functional (cffi backend missing)",
        allow_module_level=True,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

src_module = sys.modules.setdefault("src", types.ModuleType("src"))
security_module = sys.modules.setdefault("src.security", types.ModuleType("src.security"))
# Load the real secret_store module by file path so its utility functions
# (redact, fingerprint, etc.) are available, but override get/set to avoid
# touching real credential files during tests.
_ss_spec = importlib.util.spec_from_file_location(
    "src.security.secret_store", REPO_ROOT / "src" / "security" / "secret_store.py"
)
_ss_mod = importlib.util.module_from_spec(_ss_spec)
_ss_spec.loader.exec_module(_ss_mod)
_ss_mod.get_secret = lambda key, default="": default
_ss_mod.set_secret = lambda key, value, note="", tongue=None: None
src_module = sys.modules.setdefault("src", types.ModuleType("src"))
security_module = sys.modules.setdefault("src.security", types.ModuleType("src.security"))
sys.modules["src.security.secret_store"] = _ss_mod
src_module.security = security_module
src_module.security = security_module


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


terminal_ai_router = _load_module("test_terminal_ai_router", "scripts/system/terminal_ai_router.py")
sell_from_terminal = _load_module("test_sell_from_terminal", "scripts/system/sell_from_terminal.py")
scbe_system_cli = _load_module("test_scbe_system_cli", "scripts/scbe-system-cli.py")


def test_terminal_ai_router_public_payload_strips_secret_metadata() -> None:
    payload = {
        "generated_at_utc": "2026-03-14T00:00:00Z",
        "config_path": "config.json",
        "checks": ["openai"],
        "alias_sync": {
            "OPENAI_API_KEY": {"status": "synced", "source": "OPENAI_KEY"},
            "ANTHROPIC_API_KEY": {"status": "missing", "source": None},
        },
        "status": {
            "openai": {
                "status": "degraded",
                "detail": {
                    "http_status": 401,
                    "key_name": "OPENAI_API_KEY",
                    "key_source": "env",
                    "accepted_keys": ["OPENAI_API_KEY"],
                    "error": "Authorization: Bearer super-secret-token",
                },
            }
        },
    }

    public_payload = terminal_ai_router._build_public_health_payload(payload)

    assert public_payload["alias_sync_summary"] == {"set": 0, "synced": 1, "missing": 1}
    detail = public_payload["status"]["openai"]["detail"]
    assert "key_name" not in detail
    assert "key_source" not in detail
    assert "accepted_keys" not in detail
    assert "super-secret-token" not in detail["error"]
    assert "[redacted]" in detail["error"]


def test_sell_from_terminal_process_summary_omits_raw_streams() -> None:
    class Proc:
        returncode = 1
        stdout = "OPENAI_API_KEY=abc123"
        stderr = "Authorization: Bearer super-secret-token"

    summary = sell_from_terminal._summarize_process_result(["python", "tool.py"], Proc())

    assert summary["returncode"] == 1
    assert summary["stdout_present"] is True
    assert summary["stderr_present"] is True
    assert "stdout" not in summary
    assert "stderr" not in summary
    assert "[redacted]" in summary["error_excerpt"]


def test_scbe_system_cli_sanitize_agent_result_for_disk_omits_content() -> None:
    result = {
        "ok": True,
        "agent_id": "codex",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "content": "password=hunter2",
        "raw": {"secret": "x"},
        "prompt": "secret prompt",
    }

    sanitized = scbe_system_cli._sanitize_agent_result_for_disk(result)

    assert sanitized["ok"] is True
    assert sanitized["agent_id"] == "codex"
    assert "content" not in sanitized
    assert "raw" not in sanitized
    assert "prompt" not in sanitized
    assert sanitized["content_char_count"] == len("password=hunter2")
    assert len(sanitized["content_pbkdf2_sha256"]) == 64


def test_secret_store_redacts_shopify_tokens() -> None:
    payload = "token=shpat_ABCDEF1234567890"
    redacted = _ss_mod.redact_sensitive_text(payload)
    assert "[redacted]" in redacted
    assert "ABCDEF1234567890" not in redacted


def test_secret_store_write_json_ignores_unsanitized_flag(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    payload = {
        "token": "super-secret-token",
        "note": "hf_ABCDEFGH12345678 should not hit disk",
    }

    _ss_mod.write_json(out, payload, sanitize=False)
    saved = json.loads(out.read_text(encoding="utf-8"))

    assert saved["token"] == "[redacted]"
    assert "[redacted]" in saved["note"]
    assert "super-secret-token" not in out.read_text(encoding="utf-8")
