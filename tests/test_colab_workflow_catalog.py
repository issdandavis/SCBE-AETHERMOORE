from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "system" / "colab_workflow_catalog.py"


def _run(*args: str) -> str:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(f"command failed: {args}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proc.stdout


def test_list_json_contains_pivot_and_finetune() -> None:
    payload = json.loads(_run("list", "--json"))
    names = {row["name"] for row in payload}
    assert "scbe-pivot-v2" in names
    assert "scbe-finetune-free" in names


def test_show_resolves_alias() -> None:
    payload = json.loads(_run("show", "pivot", "--json"))
    assert payload["name"] == "scbe-pivot-v2"
    assert payload["path"] == "notebooks/scbe_pivot_training_v2.ipynb"
    assert payload["exists"] is True


def test_url_points_to_colab() -> None:
    out = _run("url", "finetune").strip()
    assert out.startswith("https://colab.research.google.com/github/")
    assert "\\" not in out
    assert "notebooks/scbe_finetune_colab.ipynb" in out
