from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from urllib import error as urllib_error

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from agents import aetherbrowse_cli as cli  # noqa: E402
except ImportError:
    cli = None

pytestmark = pytest.mark.skipif(cli is None, reason="agents dependencies not installed")


def test_check_cdp_readiness_connection_refused_is_actionable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_read_json_url(url: str, timeout: float = 2.0):
        raise urllib_error.URLError(ConnectionRefusedError(10061, "Connection refused"))

    monkeypatch.setattr(cli, "_read_json_url", fake_read_json_url)
    monkeypatch.setattr(
        cli,
        "get_chrome_launch_command",
        lambda port=9222: f"chrome --remote-debugging-port={port}",
    )

    message = asyncio.run(cli._check_cdp_readiness("127.0.0.1", 9222, None))

    assert message is not None
    assert "http://127.0.0.1:9222/json" in message
    assert "chrome --remote-debugging-port=9222" in message
    assert "--backend playwright" in message
    assert "Connection refused" in message


def test_check_cdp_readiness_reports_empty_target_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "_read_json_url", lambda url, timeout=2.0: (200, []))
    monkeypatch.setattr(
        cli,
        "get_chrome_launch_command",
        lambda port=9223: f"chrome --remote-debugging-port={port}",
    )

    message = asyncio.run(cli._check_cdp_readiness("localhost", 9223, None))

    assert message is not None
    assert "no debuggable targets" in message
    assert "open at least one tab" in message
    assert "chrome --remote-debugging-port=9223" in message


def test_check_cdp_readiness_reports_missing_target_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    targets = [
        {
            "id": "page-1",
            "title": "Example",
            "type": "page",
            "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/page-1",
        }
    ]
    monkeypatch.setattr(cli, "_read_json_url", lambda url, timeout=2.0: (200, targets))

    message = asyncio.run(cli._check_cdp_readiness("127.0.0.1", 9222, "missing-target"))

    assert message is not None
    assert "--target-id missing-target" in message
    assert "page-1 (Example)" in message
    assert "pass a valid --target-id" in message


def test_main_exits_cleanly_on_cdp_readiness_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_check_cdp_readiness(host: str, port: int, target_id: str | None) -> str:
        return "CDP unavailable for test"

    class FailIfConstructed:
        def __init__(self, config):
            raise AssertionError("session should not be constructed when CDP is unavailable")

    monkeypatch.setattr(cli, "_check_cdp_readiness", fake_check_cdp_readiness)
    monkeypatch.setattr(cli, "AetherbrowseSession", FailIfConstructed)
    monkeypatch.setattr(sys, "argv", ["aetherbrowse_cli.py", "navigate", "https://example.com"])

    with pytest.raises(SystemExit) as excinfo:
        cli.main()

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "CDP unavailable for test" in captured.err
    assert "Traceback" not in captured.err
