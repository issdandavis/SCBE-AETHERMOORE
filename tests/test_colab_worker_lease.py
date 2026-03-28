from __future__ import annotations

import json
from pathlib import Path

from scripts.system import colab_worker_lease as worker


def test_build_worker_lease_has_expiry() -> None:
    lease = worker.build_worker_lease(
        worker_id="worker-colab-01",
        notebook_name="scbe-pivot-v2",
        lease_seconds=900,
    )
    assert lease["owner"] == "worker-colab-01"
    assert lease["provider"] == "colab"
    assert lease["resource_class"] == "browser-colab"
    assert lease["lease_seconds"] == 900
    assert lease["claimed_at_utc"] < lease["expires_at_utc"]


def test_provision_colab_worker_dry_run_emits_packets(
    tmp_path: Path, monkeypatch
) -> None:
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
    assert Path(artifact["artifact_path"]).exists()
    saved = json.loads(Path(artifact["artifact_path"]).read_text(encoding="utf-8"))
    assert saved["packets"]["claim"] == "pkt-1"
    assert saved["packets"]["internal"] == "pkt-2"
    assert saved["packets"]["evidence"] == "pkt-3"


def test_provision_colab_worker_with_fake_playwright_marks_auth_required(
    tmp_path: Path, monkeypatch
) -> None:
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

    monkeypatch.setattr(
        worker, "_load_sync_playwright", lambda: (lambda: FakePlaywright())
    )

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
            },
        )
        == "runtime_disconnected"
    )
    assert (
        worker._derive_runtime_state(
            "auth_required",
            {
                "usage_visible": True,
                "connect_button_visible": False,
            },
        )
        == "auth_required"
    )
