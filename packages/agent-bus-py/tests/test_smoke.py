"""Smoke tests for the scbe_agent_bus Python surface."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PKG_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PKG_SRC) not in sys.path:
    sys.path.insert(0, str(PKG_SRC))

import scbe_agent_bus  # noqa: E402
from scbe_agent_bus import (
    AgentBusError,
    recommend_companion_packages,
    run_batch,
    run_event,
)  # noqa: E402
from scbe_agent_bus.__main__ import _parse_events, main  # noqa: E402


def test_module_exports_version():
    assert scbe_agent_bus.__version__ == "0.2.0"


def test_recommend_companion_packages_skips_installed_package():
    rows = recommend_companion_packages(
        ["operator_manifold", "tokenizer", "batch dispatch"],
        available_packages=["scbe-agent-bus"],
    )

    assert rows == [
        {
            "feature": "operator-manifold",
            "package": "scbe-aethermoore",
            "install": "npm install scbe-aethermoore",
            "reason": "scbe-aethermoore provides operator-manifold without being installed as a forced dependency.",
        },
        {
            "feature": "tokenizer",
            "package": "scbe-aethermoore",
            "install": "npm install scbe-aethermoore",
            "reason": "scbe-aethermoore provides tokenizer without being installed as a forced dependency.",
        },
    ]


def test_run_batch_rejects_empty():
    with pytest.raises(AgentBusError):
        run_batch([])


def test_run_event_rejects_missing_task(tmp_path: Path):
    with pytest.raises(AgentBusError):
        run_event({}, repo_root=str(tmp_path))


def test_run_event_errors_when_runner_missing(tmp_path: Path):
    with pytest.raises(AgentBusError) as excinfo:
        run_event({"task": "hello"}, repo_root=str(tmp_path))
    assert "agent-bus runner not found" in str(excinfo.value)


def test_parse_events_handles_object_array_and_items():
    assert _parse_events(json.dumps({"task": "x"})) == [{"task": "x"}]
    assert _parse_events(json.dumps([{"task": "a"}, {"task": "b"}])) == [
        {"task": "a"},
        {"task": "b"},
    ]
    assert _parse_events(json.dumps({"items": [{"task": "y"}]})) == [{"task": "y"}]
    assert _parse_events("") == []


def test_cli_returns_two_when_no_events(tmp_path: Path, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", _NoTtyStream(""))
    rc = main(["--repo-root", str(tmp_path)])
    assert rc == 2
    captured = capsys.readouterr()
    assert "no events provided" in captured.err


class _NoTtyStream:
    def __init__(self, text: str) -> None:
        self._text = text

    def isatty(self) -> bool:
        return False

    def read(self) -> str:
        return self._text
