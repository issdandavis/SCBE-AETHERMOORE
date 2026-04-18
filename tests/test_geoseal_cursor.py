from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import src.geoseal_cli as geoseal_cli


def test_cursor_agent_path_prefers_env(monkeypatch, tmp_path: Path) -> None:
    agent_cmd = tmp_path / "agent.cmd"
    agent_cmd.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setenv("CURSOR_AGENT_CMD", str(agent_cmd))

    resolved = geoseal_cli._cursor_agent_path()

    assert resolved == agent_cmd


def test_cmd_cursor_invokes_agent_and_writes_ledger(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    ledger = tmp_path / "cursor.jsonl"
    agent_cmd = tmp_path / "agent.cmd"
    agent_cmd.write_text("@echo off\n", encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_run(argv, capture_output, text, check, cwd):  # type: ignore[no-untyped-def]
        captured["argv"] = argv
        captured["cwd"] = cwd
        return subprocess.CompletedProcess(argv, 0, stdout="cursor ok\n", stderr="")

    monkeypatch.setattr(geoseal_cli, "_cursor_agent_path", lambda: agent_cmd)
    monkeypatch.setattr(geoseal_cli.subprocess, "run", fake_run)

    args = argparse.Namespace(
        task="review src/coding_spine/router.py",
        workspace=str(workspace),
        model="composer-2-fast",
        mode="plan",
        force=True,
        output_format="json",
        stream_partial_output=False,
        continue_session=False,
        no_ledger=False,
        ledger=str(ledger),
        verbose=False,
    )

    rc = geoseal_cli.cmd_cursor(args)

    assert rc == 0
    assert captured["cwd"] == str(workspace.resolve())
    assert captured["argv"] == [
        str(agent_cmd),
        "-p",
        "--trust",
        "--workspace",
        str(workspace.resolve()),
        "--model",
        "composer-2-fast",
        "--mode",
        "plan",
        "--force",
        "--output-format",
        "json",
        "review src/coding_spine/router.py",
    ]
    ledger_text = ledger.read_text(encoding="utf-8")
    assert '"type": "cursor"' in ledger_text
    assert '"returncode": 0' in ledger_text


def test_cmd_cursor_returns_error_when_workspace_missing(monkeypatch, tmp_path: Path) -> None:
    agent_cmd = tmp_path / "agent.cmd"
    agent_cmd.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr(geoseal_cli, "_cursor_agent_path", lambda: agent_cmd)

    args = argparse.Namespace(
        task="explain repo",
        workspace=str(tmp_path / "missing"),
        model=None,
        mode=None,
        force=False,
        output_format="text",
        stream_partial_output=False,
        continue_session=False,
        no_ledger=True,
        ledger=str(tmp_path / "unused.jsonl"),
        verbose=False,
    )

    rc = geoseal_cli.cmd_cursor(args)

    assert rc == 1
