"""Tests for the coding board probe + pipeline.

Three vertical slices:
  1. ALLOW_CLI  — read-only tool + valid py_compile probe → accepted=True
  2. DENY       — destructive command → legitimacy DENY, probe mode="skipped"
  3. PROBE_ONLY — high-risk tool + no workspace → PROBE_ONLY even with legal probe
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.coding_board.pipeline import run_coding_trial
from src.coding_board.probe import probe_command

# ---------------------------------------------------------------------------
# probe unit tests
# ---------------------------------------------------------------------------


def test_probe_empty():
    result = probe_command([])
    assert result.legal is False
    assert result.mode == "empty"
    assert result.ran is False


def test_probe_would_write():
    result = probe_command(["fs.write", "output.txt"])
    assert result.legal is False
    assert result.mode == "would_write"
    assert result.ran is False


def test_probe_would_delete():
    result = probe_command(["fs.delete", "important.txt"])
    assert result.legal is False
    assert result.mode == "would_write"
    assert result.ran is False


def test_probe_unsupported():
    result = probe_command(["curl", "https://example.com"])
    assert result.legal is False
    assert result.mode == "unsupported"
    assert result.ran is False


def test_probe_py_compile_valid(tmp_path):
    f = tmp_path / "good.py"
    f.write_text("x = 1 + 2\n", encoding="utf-8")
    result = probe_command(["python", "-m", "py_compile", str(f)], workspace=tmp_path)
    assert result.mode == "py_compile"
    assert result.ran is True
    assert result.legal is True
    assert result.returncode == 0


def test_probe_py_compile_invalid(tmp_path):
    f = tmp_path / "broken.py"
    f.write_text("def oops(:\n", encoding="utf-8")
    result = probe_command(["python", "-m", "py_compile", str(f)], workspace=tmp_path)
    assert result.mode == "py_compile"
    assert result.ran is True
    assert result.legal is False
    assert result.returncode != 0


def test_probe_py_compile_outside_workspace(tmp_path):
    other = tmp_path / "subdir"
    other.mkdir()
    f = other / "secret.py"
    f.write_text("x = 1\n", encoding="utf-8")
    workspace = tmp_path / "safe_zone"
    workspace.mkdir()
    result = probe_command(["python", "-m", "py_compile", str(f)], workspace=workspace)
    assert result.mode == "py_compile"
    assert result.legal is False
    assert "outside workspace" in result.reason


def test_probe_pytest_collect(tmp_path):
    f = tmp_path / "test_sample.py"
    f.write_text("def test_ok():\n    assert 1 == 1\n", encoding="utf-8")
    result = probe_command(["pytest", str(tmp_path)], workspace=tmp_path)
    assert result.mode == "pytest_collect"
    assert result.ran is True


def test_probe_pytest_python_m_form(tmp_path):
    f = tmp_path / "test_other.py"
    f.write_text("def test_pass(): pass\n", encoding="utf-8")
    result = probe_command(["python", "-m", "pytest", str(tmp_path)], workspace=tmp_path)
    assert result.mode == "pytest_collect"
    assert result.ran is True


def test_probe_to_dict():
    result = probe_command(["fs.write", "out.txt"])
    d = result.to_dict()
    assert d["mode"] == "would_write"
    assert d["legal"] is False
    assert "argv" in d


# ---------------------------------------------------------------------------
# pipeline vertical slices
# ---------------------------------------------------------------------------


def test_pipeline_allow_cli():
    """Slice 1: read-only tool + valid py_compile → accepted=True (ALLOW_CLI)."""
    result = run_coding_trial(
        goal="check module syntax before patch",
        command=["python", "-m", "py_compile", "src/coding_board/__init__.py"],
        workspace=None,
        expected_tool="git.status",  # read-only: no workspace/location requirements
    )
    assert result["schema_version"] == "scbe-coding-trial-v1"
    assert result["legitimacy"]["decision"]["decision"] == "ALLOW_CLI"
    assert result["probe"]["mode"] == "py_compile"
    assert result["probe"]["legal"] is True
    assert result["accepted"] is True


def test_pipeline_deny_destructive():
    """Slice 2: exec-gate-denied command → DENY, probe mode='skipped'."""
    result = run_coding_trial(
        goal="clean up build artifacts",
        command=["rm", "-rf", "."],
        workspace=None,
        expected_tool="terminal.command.request",
    )
    assert result["schema_version"] == "scbe-coding-trial-v1"
    assert result["legitimacy"]["decision"]["decision"] == "DENY"
    assert result["probe"]["mode"] == "skipped"
    assert result["accepted"] is False


def test_pipeline_probe_only_no_workspace():
    """Slice 3: high-risk tool + no workspace → PROBE_ONLY; probe runs, accepted=False."""
    result = run_coding_trial(
        goal="run focused syntax check",
        command=["python", "-m", "py_compile", "src/coding_board/__init__.py"],
        workspace=None,
        expected_tool="terminal.command.request",  # high-risk, not read-only
    )
    legitimacy_decision = result["legitimacy"]["decision"]["decision"]
    assert legitimacy_decision == "PROBE_ONLY", f"expected PROBE_ONLY, got {legitimacy_decision!r}"
    # probe still runs (not DENY)
    assert result["probe"]["mode"] == "py_compile"
    # accepted requires ALLOW_CLI
    assert result["accepted"] is False


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_coding_trial_json():
    """coding-trial --json emits a valid schema_version packet."""
    import subprocess

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "coding-trial",
            "--goal",
            "check syntax before apply",
            "--tool",
            "git.status",
            "--json",
            "--",
            "python",
            "-m",
            "py_compile",
            "src/coding_board/__init__.py",
        ],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent.parent),
    )
    assert proc.returncode in (0, 1, 2, 3)
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "scbe-coding-trial-v1"
    assert "legitimacy" in payload
    assert "probe" in payload
    assert "accepted" in payload
