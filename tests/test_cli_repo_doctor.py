from __future__ import annotations

import importlib.util
import json
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


scbe_cli = _load_module("test_cli_repo_doctor_scbe", ROOT / "scbe.py")


class _Result:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_repo_smoke_doctor_runs_local_truth_loop(monkeypatch, capsys) -> None:
    captured: list[list[str]] = []

    def fake_run(cmd, **_kwargs):  # noqa: ANN001 - monkeypatched subprocess signature
        captured.append(cmd)
        return _Result(0, stdout="ok\n")

    monkeypatch.setattr(scbe_cli.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["scbe", "doctor", "--repo-smoke", "--json"])

    assert scbe_cli.main() == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema_version"] == "scbe_repo_doctor_v1"
    assert payload["ok"] is True
    assert payload["mode"] == "smoke"
    assert [cmd[:2] for cmd in captured[:2]] == [[sys.executable, "scbe.py"], [sys.executable, "scbe.py"]]
    assert any("pytest" in cmd for command in captured for cmd in command)


def test_repo_smoke_doctor_returns_failure_when_a_check_fails(monkeypatch, capsys) -> None:
    calls = 0

    def fake_run(cmd, **_kwargs):  # noqa: ANN001 - monkeypatched subprocess signature
        nonlocal calls
        calls += 1
        if calls == 2:
            return _Result(1, stderr="version mismatch\n")
        return _Result(0, stdout="ok\n")

    monkeypatch.setattr(scbe_cli.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["scbe", "doctor", "--repo-smoke", "--json"])

    assert scbe_cli.main() == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is False
    assert payload["checks"][1]["returncode"] == 1
    assert payload["checks"][1]["stderr_tail"] == ["version mismatch"]
