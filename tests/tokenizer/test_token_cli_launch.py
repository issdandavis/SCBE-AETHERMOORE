"""Tokenizer command-line surfaces must work outside pytest's import path."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "relative_script",
    (
        "scripts/tokenizer/build_intermodel_token_ledger.py",
        "scripts/tokenizer/build_token_honeycomb_nest.py",
        "scripts/tokenizer/scan_token_layer_geometry.py",
        "scripts/tokenizer/build_eot_token_lattice.py",
        "scripts/tokenizer/grow_token_tree_wafer.py",
        "scripts/tokenizer/build_token_action_lithography.py",
    ),
)
def test_cli_help_launches_from_an_unrelated_working_directory(relative_script: str, tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / relative_script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()
