"""Smoke: generator script produces JSONL the analyzer can read."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GEN = REPO / "scripts" / "rho_logging" / "generate_sample_rho_log.py"
AN = REPO / "scripts" / "analyze_rho_log.py"


@pytest.mark.skipif(not GEN.is_file(), reason="generator script missing")
def test_generator_and_analyzer_roundtrip(tmp_path):
    log = tmp_path / "rho.jsonl"
    env = {**os.environ, "PYTHONPATH": str(REPO)}
    r = subprocess.run(
        [sys.executable, str(GEN), "--iterations", "48", "--path", str(log), "--truncate"],
        cwd=str(REPO),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert log.is_file()
    lines = [ln for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 48
    last = json.loads(lines[-1])
    assert "rho_per_axis" in last

    r2 = subprocess.run(
        [sys.executable, str(AN), "--path", str(log), "--json", "--hint"],
        cwd=str(REPO),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r2.returncode == 0, r2.stderr
    summary = json.loads(r2.stdout)
    assert summary["total_records"] == 48
    assert summary["per_axis"]
    assert "decision_hint" in summary
    assert summary["decision_hint"]["verdict"] in (
        "LOW_SIGNAL",
        "MARGINAL",
        "STRUCTURED",
        "INSUFFICIENT_WARM_AXES",
    )
