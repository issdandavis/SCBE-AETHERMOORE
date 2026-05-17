"""Geoseal CLI subcommand error-handling contract.

The bridge subcommands (terminus-training, yin-yang-dual, pair-agent-training)
delegate to backing modules that raise ValueError/KeyError on invalid domain
input. The CLI must surface those as a clean one-line error with a non-zero
exit code -- matching geoseal_cli house style -- never a raw Python traceback.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "src.geoseal_cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


def test_yin_yang_dual_bad_size_fails_cleanly() -> None:
    proc = _run("yin-yang-dual", "--ko-text", "a", "--dr-text", "b", "--size", "8")
    assert proc.returncode != 0
    assert "Traceback (most recent call last)" not in proc.stderr
    assert "size must be an odd integer >= 5" in proc.stderr


def test_terminus_training_bad_scenario_fails_cleanly() -> None:
    proc = _run("terminus-training", "--mode", "scripted", "--scenario", "nope")
    assert proc.returncode != 0
    assert "Traceback (most recent call last)" not in proc.stderr


def test_yin_yang_dual_valid_input_still_succeeds() -> None:
    proc = _run("yin-yang-dual", "--ko-text", "route", "--dr-text", "shape", "--frame", "1", "--json")
    assert proc.returncode == 0, proc.stderr
    assert '"schema_version": "scbe-yin-yang-dual-token-v1"' in proc.stdout
