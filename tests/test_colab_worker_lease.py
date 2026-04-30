from __future__ import annotations

import json
from pathlib import Path

from scripts.system import colab_worker_lease as worker


def test_build_worker_lease_has_expiry() -> None:
    scope = worker.build_intersection_scope(languages="en, ko", regions="us, asia", jurisdictions="public, export-safe")
    lease = worker.build_worker_lease(
        worker_id="worker-colab-01",
        notebook_name="scbe-pivot-v2",
        lease_seconds=900,
        parallel_group="coding-swarm",
        shard_index=1,
        shard_count=4,
        intersection_scope=scope,
    )
    assert lease["owner"] == "worker-colab-01"
    assert lease["provider"] == "colab"
    assert lease["resource_class"] == "browser-colab"
    assert lease["lease_seconds"] == 900
    assert lease["claimed_at_utc"] < lease["expires_at_utc"]
    assert lease["parallel"]["group"] == "coding-swarm"
    assert lease["parallel"]["shard_index"] == 1
    assert lease["parallel"]["shard_count"] == 4
    assert lease["intersection_scope"]["languages"] == ["en", "ko"]
    assert lease["intersection_scope"]["regions"] == ["us", "asia"]
    assert lease["intersection_scope"]["jurisdictions"] == ["public", "export-safe"]
    assert lease["intersection_scope"]["intersection_count"] == 4


def test_provision_colab_worker_dry_run_emits_packets(tmp_path: Path, monkeypatch) -> None:
    emitted: list[dict[str, object]] = []

    def fake_emit_packet(**kwargs):
        emitted.append(kwargs)
        return {"packet_id": f"pkt-{len(emitted)}", "all_delivered": True, "lanes": {}}

    monkeypatch.setattr(worker.relay, "emit_packet", fake_emit_packet)

    artifact = worker.provision_colab_worker(
        notebook_query="pivot",
        mission_id="mission-1",
        worker_id="worker-colab-01",
        session_id="worker-colab-01-session",
        recipient="agent.claude",
        sender="agent.codex",
        profile_dir=tmp_path / "profile",
        artifact_root=tmp_path / "artifacts",
        lease_seconds=1200,
        headless=True,
        keep_open=False,
        timeout_ms=1000,
        dry_run=True,
        parallel_group="training-swarm",
        shard_index=0,
        shard_count=2,
        intersection_scope=worker.build_intersection_scope(languages="en,ja", regions="global"),
    )

    assert artifact["state"] == "dry_run"
    assert artifact["notebook"]["name"] == "scbe-pivot-v2"
    assert len(emitted) == 3
    assert [row["packet_class"] for row in emitted] == [
        "governance",
        "internal",
        "evidence",
    ]
    assert emitted[1]["worker_id"] == "worker-colab-01"
    assert emitted[1]["mission_id"] == "mission-1"
    assert emitted[1]["lease"]["parallel"]["group"] == "training-swarm"
    assert emitted[1]["lease"]["intersection_scope"]["languages"] == ["en", "ja"]
    assert artifact["parallel"]["shard_count"] == 2
    assert artifact["intersection_scope"]["regions"] == ["global"]
    assert Path(artifact["artifact_path"]).exists()
    saved = json.loads(Path(artifact["artifact_path"]).read_text(encoding="utf-8"))
    assert saved["packets"]["claim"] == "pkt-1"
    assert saved["packets"]["internal"] == "pkt-2"
    assert saved["packets"]["evidence"] == "pkt-3"


def test_provision_colab_worker_with_fake_playwright_marks_auth_required(tmp_path: Path, monkeypatch) -> None:
    emitted: list[dict[str, object]] = []

    def fake_emit_packet(**kwargs):
        emitted.append(kwargs)
        return {"packet_id": f"pkt-{len(emitted)}", "all_delivered": True, "lanes": {}}

    monkeypatch.setattr(worker.relay, "emit_packet", fake_emit_packet)

    screenshot_calls: list[str] = []
    wait_calls: list[int] = []
    evaluate_calls: list[str] = []

    class FakePage:
        def __init__(self) -> None:
            self.url = "https://accounts.google.com/v3/signin/identifier"

        def goto(self, url: str, wait_until: str, timeout: int) -> None:
            assert "colab.research.google.com/github/" in url
            assert wait_until == "domcontentloaded"
            assert timeout == 5000

        def title(self) -> str:
            return "Sign in - Google Accounts"

        def wait_for_timeout(self, delay: int) -> None:
            wait_calls.append(delay)

        def evaluate(self, script: str):
            evaluate_calls.append(script)
            return {
                "notebook_loaded": False,
                "usage_visible": False,
                "usage_text": "",
                "machine_type": "",
                "connect_button_visible": False,
                "button_samples": [],
            }

        def screenshot(self, path: str, full_page: bool) -> None:
            screenshot_calls.append(path)
            Path(path).write_bytes(b"fake-image")

    class FakeContext:
        def __init__(self) -> None:
            self.pages = [FakePage()]

        def new_page(self):
            page = FakePage()
            self.pages.append(page)
            return page

        def close(self) -> None:
            return None

    class FakeChromium:
        def launch_persistent_context(self, user_data_dir: str, headless: bool):
            assert user_data_dir.endswith("profile")
            assert headless is False
            return FakeContext()

    class FakePlaywright:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @property
        def chromium(self):
            return FakeChromium()

    monkeypatch.setattr(worker, "_load_sync_playwright", lambda: (lambda: FakePlaywright()))

    artifact = worker.provision_colab_worker(
        notebook_query="pivot",
        mission_id="mission-live",
        worker_id="worker-colab-live",
        session_id="worker-colab-live-session",
        recipient="agent.claude",
        sender="agent.codex",
        profile_dir=tmp_path / "profile",
        artifact_root=tmp_path / "artifacts",
        lease_seconds=600,
        headless=False,
        keep_open=False,
        timeout_ms=5000,
        dry_run=False,
    )

    assert artifact["state"] == "auth_required"
    assert artifact["title"] == "Sign in - Google Accounts"
    assert artifact["layer14"]["signal_class"] == "auth_required"
    assert artifact["runtime_probe"]["connect_button_visible"] is False
    assert emitted[1]["rails"]["D-"][0]["type"] == "auth_required"
    assert wait_calls == [4000]
    assert evaluate_calls
    assert screenshot_calls
    assert Path(artifact["screenshot_path"]).exists()


def test_derive_runtime_state_detects_connected_and_disconnected() -> None:
    assert (
        worker._derive_runtime_state(
            "notebook_open",
            {
                "usage_visible": True,
                "connect_button_visible": False,
                "connected_text_visible": True,
            },
        )
        == "runtime_connected"
    )
    assert (
        worker._derive_runtime_state(
            "notebook_open",
            {
                "usage_visible": False,
                "connect_button_visible": True,
                "sign_in_button_visible": False,
                "body_has_connect": False,
            },
        )
        == "runtime_disconnected"
    )
    assert (
        worker._derive_runtime_state(
            "notebook_open",
            {
                "usage_visible": False,
                "connect_button_visible": False,
                "sign_in_button_visible": False,
                "body_has_connect": True,
            },
        )
        == "runtime_disconnected"
    )
    assert (
        worker._derive_runtime_state(
            "notebook_open",
            {
                "usage_visible": False,
                "connect_button_visible": True,
                "sign_in_button_visible": True,
            },
        )
        == "auth_required"
    )


def test_open_auth_bootstrap_launches_visible_chrome(tmp_path: Path, monkeypatch) -> None:
    calls: list[list[str]] = []
    chrome = tmp_path / "chrome.exe"
    chrome.write_text("", encoding="utf-8")

    def fake_popen(args, stdout=None, stderr=None):
        calls.append(list(args))

        class Proc:
            pid = 123

        return Proc()

    monkeypatch.setenv("SCBE_COLAB_BRANCH", "test-branch")
    monkeypatch.setattr(worker.subprocess, "Popen", fake_popen)

    payload = worker.open_auth_bootstrap("zero-cost", tmp_path / "profile", str(chrome))

    assert payload["state"] == "opened"
    assert payload["notebook"]["name"] == "zero-cost-local-0p5b"
    assert payload["profile_dir"].endswith("profile")
    assert calls
    assert calls[0][0] == str(chrome)
    assert any(arg.startswith("--user-data-dir=") for arg in calls[0])
    assert "--new-window" in calls[0]


def test_attempt_runtime_connect_prefers_colab_toolbar_button() -> None:
    calls: list[str] = []

    class FakePage:
        def evaluate(self, script: str) -> bool:
            calls.append(script)
            return True

        def wait_for_timeout(self, delay: int) -> None:
            assert delay == 12000

    result = worker._attempt_runtime_connect(FakePage())

    assert result["attempted"] is True
    assert result["ok"] is True
    assert result["method"] == "colab-toolbar-button"
    assert "colab-toolbar-button#connect" in calls[0]


def test_attempt_runtime_connect_force_clicks_toolbar_fallback() -> None:
    clicked: list[dict[str, object]] = []

    class FakeLocator:
        def click(self, timeout: int, force: bool) -> None:
            clicked.append({"timeout": timeout, "force": force})

    class FakePage:
        def evaluate(self, script: str) -> bool:
            return False

        def locator(self, selector: str) -> FakeLocator:
            assert selector == "colab-toolbar-button#connect"
            return FakeLocator()

        def wait_for_timeout(self, delay: int) -> None:
            assert delay == 12000

    result = worker._attempt_runtime_connect(FakePage())

    assert result["attempted"] is True
    assert result["ok"] is True
    assert clicked == [{"timeout": 8000, "force": True}]
    assert (
        worker._derive_runtime_state(
            "auth_required",
            {
                "usage_visible": True,
                "connect_button_visible": False,
                "sign_in_button_visible": False,
            },
        )
        == "auth_required"
    )


def test_attempt_run_all_prefers_visible_run_all_button() -> None:
    calls: list[str] = []
    waits: list[int] = []

    class FakePage:
        def evaluate(self, script: str) -> bool:
            calls.append(script)
            return len(calls) == 1

        def wait_for_timeout(self, delay: int) -> None:
            waits.append(delay)

    result = worker._attempt_run_all(FakePage())

    assert result["attempted"] is True
    assert result["ok"] is True
    assert result["method"] == "run-all-button"
    assert "run all" in calls[0].lower()
    assert "run anyway" in calls[1].lower()
    assert result["warning_dismissed"] is False
    assert waits == [2500, 5000]


def test_attempt_run_all_uses_keyboard_fallback() -> None:
    keys: list[str] = []
    clicked: list[dict[str, object]] = []

    class FakeKeyboard:
        def press(self, key: str) -> None:
            keys.append(key)

    class FakeRunAnyway:
        def click(self, timeout: int) -> None:
            clicked.append({"timeout": timeout})

    class FakePage:
        keyboard = FakeKeyboard()
        calls = 0
        waits: list[int] = []

        def evaluate(self, script: str) -> bool:
            self.calls += 1
            return False

        def get_by_text(self, text: str, exact: bool) -> FakeRunAnyway:
            assert text == "Run anyway"
            assert exact is True
            return FakeRunAnyway()

        def wait_for_timeout(self, delay: int) -> None:
            self.waits.append(delay)

    result = worker._attempt_run_all(FakePage())

    assert result["attempted"] is True
    assert result["ok"] is True
    assert result["method"] == "keyboard-control-f9"
    assert result["warning_dismissed"] is True
    assert keys == ["Control+F9"]
    assert clicked == [{"timeout": 8000}]
