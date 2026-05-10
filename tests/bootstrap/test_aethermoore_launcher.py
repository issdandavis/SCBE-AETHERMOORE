"""Smoke tests for the aethermoore.pyz single-file launcher."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PYZ = REPO_ROOT / "scripts" / "bootstrap" / "aethermoore.pyz"
SRC_MAIN = REPO_ROOT / "scripts" / "bootstrap" / "aethermoore_src" / "__main__.py"


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO_ROOT),
    )


@pytest.mark.skipif(not SRC_MAIN.exists(), reason="launcher source missing")
def test_launcher_source_compiles() -> None:
    """The source __main__.py is valid Python."""
    src = SRC_MAIN.read_text(encoding="utf-8")
    compile(src, str(SRC_MAIN), "exec")


@pytest.mark.skipif(not PYZ.exists(), reason="launcher .pyz not built")
def test_pyz_pitch_subcommand() -> None:
    """`pitch` prints the pitch and exits 0."""
    result = _run([sys.executable, str(PYZ), "pitch"])
    assert result.returncode == 0, result.stderr
    assert "SCBE-AETHERMOORE" in result.stdout
    assert "Poincare ball model" in result.stdout
    assert "GeoSeal" in result.stdout


@pytest.mark.skipif(not PYZ.exists(), reason="launcher .pyz not built")
def test_pyz_paths_subcommand() -> None:
    """`paths` lists canonical files."""
    result = _run([sys.executable, str(PYZ), "paths"])
    assert result.returncode == 0, result.stderr
    assert "harmonicScaling.ts" in result.stdout
    assert "scbe_code.py" in result.stdout
    assert "aetherdesk" in result.stdout


@pytest.mark.skipif(not PYZ.exists(), reason="launcher .pyz not built")
def test_pyz_check_passes_inside_repo() -> None:
    """`check` returns 0 when run from the repo root."""
    result = _run([sys.executable, str(PYZ), "check"])
    assert result.returncode == 0, result.stderr
    assert "python" in result.stdout
    assert "SCBE-AETHERMOORE root: OK" in result.stdout


@pytest.mark.skipif(not PYZ.exists(), reason="launcher .pyz not built")
def test_pyz_help_lists_subcommands() -> None:
    """`--help` enumerates all subcommands."""
    result = _run([sys.executable, str(PYZ), "--help"])
    assert result.returncode == 0
    for sub in ("pitch", "paths", "check", "aetherdesk", "menu"):
        assert sub in result.stdout, f"missing subcommand in help: {sub}"


@pytest.mark.skipif(not PYZ.exists(), reason="launcher .pyz not built")
def test_pyz_unknown_subcommand_errors_cleanly() -> None:
    """An unknown subcommand exits non-zero (argparse behavior)."""
    result = _run([sys.executable, str(PYZ), "nopenope"])
    assert result.returncode != 0
