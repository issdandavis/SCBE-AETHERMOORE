from __future__ import annotations

import importlib.util
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


scbe_cli = _load_module("test_scbe_unified_cli_forwarding", ROOT / "scbe")


class _Result:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


def test_scbe_run_forwards_to_system_runtime(monkeypatch) -> None:
    captured: list[list[str]] = []

    def fake_run(cmd, check=False):  # noqa: ANN001 - monkeypatched subprocess signature
        captured.append(cmd)
        return _Result(0)

    monkeypatch.setattr(scbe_cli.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        ["scbe", "run", "--language", "python", "--code", "print('x')"],
    )

    assert scbe_cli.main() == 0
    assert captured == [[
        sys.executable,
        str(ROOT / "scripts" / "scbe-system-cli.py"),
        "--repo-root",
        str(ROOT),
        "runtime",
        "run",
        "--language",
        "python",
        "--code",
        "print('x')",
    ]]


def test_scbe_pollypad_forwards_to_system_cli(monkeypatch) -> None:
    captured: list[list[str]] = []

    def fake_run(cmd, check=False):  # noqa: ANN001 - monkeypatched subprocess signature
        captured.append(cmd)
        return _Result(0)

    monkeypatch.setattr(scbe_cli.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        ["scbe", "pollypad", "list"],
    )

    assert scbe_cli.main() == 0
    assert captured == [[
        sys.executable,
        str(ROOT / "scripts" / "scbe-system-cli.py"),
        "--repo-root",
        str(ROOT),
        "pollypad",
        "list",
    ]]
