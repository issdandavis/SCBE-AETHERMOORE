from __future__ import annotations

from pathlib import Path

import pytest

from scripts.run_thermal_mirror_probe import PROBE_SCRIPT, build_probe_command, main


def test_build_probe_command_targets_probe_script() -> None:
    command = build_probe_command(Path(r"C:\Users\issda\Python312\python.exe"), ["--json", "--control", "banded"])

    assert command[0] == r"C:\Users\issda\Python312\python.exe"
    assert command[1] == str(PROBE_SCRIPT)
    assert command[-3:] == ["--json", "--control", "banded"]


def test_main_dry_run_skips_subprocess(monkeypatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        "scripts.run_thermal_mirror_probe.choose_python_for_eval",
        lambda preferred_python=None: Path(r"C:\Users\issda\Python312\python.exe"),
    )

    def _should_not_run(*args, **kwargs):
        raise AssertionError("subprocess.run should not be called during dry-run")

    monkeypatch.setattr("scripts.run_thermal_mirror_probe.subprocess.run", _should_not_run)

    exit_code = main(["--dry-run", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Resolved command:" in captured.out
    assert "--json" in captured.out
