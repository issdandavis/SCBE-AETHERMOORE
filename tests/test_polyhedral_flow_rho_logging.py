"""
Tests for the rho_i logging instrumentation in composite_harmonic_wall.
================================================================================

Verifies:
- Default (env unset) writes nothing and changes no return value.
- SCBE_RHO_LOG=1 writes one JSONL record per call.
- Per-axis rho is None until the warmup threshold is reached, then a number in [-1, 1].
- _pearson math is correct on simple analytic inputs.
- Logging failure can never break the safety output.
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from symphonic_cipher.scbe_aethermoore.axiom_grouped.polyhedral_flow import (
    _pearson,
    _RHO_HISTORY,
    _RHO_LOG_MIN_SAMPLES,
    composite_harmonic_wall,
)


@pytest.fixture(autouse=True)
def _reset_rho_state(monkeypatch):
    """Clear module-level rolling buffer + env between tests."""
    monkeypatch.delenv("SCBE_RHO_LOG", raising=False)
    monkeypatch.delenv("SCBE_RHO_LOG_PATH", raising=False)
    _RHO_HISTORY.clear()
    yield
    _RHO_HISTORY.clear()


def test_pearson_perfect_positive():
    samples = [(float(i), 2.0 * i + 1.0) for i in range(10)]
    assert _pearson(samples) == pytest.approx(1.0, abs=1e-9)


def test_pearson_perfect_negative():
    samples = [(float(i), -3.0 * i + 5.0) for i in range(10)]
    assert _pearson(samples) == pytest.approx(-1.0, abs=1e-9)


def test_pearson_zero_variance_returns_zero():
    samples = [(0.5, float(i)) for i in range(10)]
    assert _pearson(samples) == 0.0


def test_pearson_too_few_samples_returns_none():
    assert _pearson([]) is None
    assert _pearson([(1.0, 1.0)]) is None


def test_default_off_writes_nothing(tmp_path):
    log_path = tmp_path / "should_not_exist.jsonl"
    os.environ.pop("SCBE_RHO_LOG", None)
    os.environ["SCBE_RHO_LOG_PATH"] = str(log_path)
    out = composite_harmonic_wall({"KO": 0.1, "AV": 0.2})
    assert "h_composite" in out
    assert "tier" in out
    assert not log_path.exists()


def test_env_on_writes_one_record_per_call(tmp_path, monkeypatch):
    log_path = tmp_path / "rho.jsonl"
    monkeypatch.setenv("SCBE_RHO_LOG", "1")
    monkeypatch.setenv("SCBE_RHO_LOG_PATH", str(log_path))
    for _ in range(5):
        composite_harmonic_wall({"KO": 0.1, "AV": 0.3})
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 5
    rec = json.loads(lines[0])
    assert set(rec) >= {"ts", "distances", "h_composite", "tier", "phase_deviation", "rho_per_axis"}
    assert set(rec["distances"]) == {"KO", "AV"}
    assert rec["tier"] in ("ALLOW", "QUARANTINE", "DENY")


def test_rho_is_none_below_warmup_then_real(tmp_path, monkeypatch):
    log_path = tmp_path / "rho.jsonl"
    monkeypatch.setenv("SCBE_RHO_LOG", "1")
    monkeypatch.setenv("SCBE_RHO_LOG_PATH", str(log_path))
    n = _RHO_LOG_MIN_SAMPLES + 5
    for i in range(n):
        composite_harmonic_wall({"KO": 0.01 * i, "AV": 0.005 * i})
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    early = json.loads(lines[0])
    late = json.loads(lines[-1])
    assert early["rho_per_axis"]["KO"] is None
    assert early["rho_per_axis"]["AV"] is None
    for axis, val in late["rho_per_axis"].items():
        assert val is not None, axis
        assert -1.0 <= val <= 1.0, (axis, val)


def test_return_value_unchanged_by_logging(tmp_path, monkeypatch):
    """The wall's return shape and values must be identical with logging on vs off."""
    distances = {"KO": 0.07, "AV": 0.13, "RU": 0.21}
    monkeypatch.delenv("SCBE_RHO_LOG", raising=False)
    off = composite_harmonic_wall(distances, phase_deviation=0.05)

    monkeypatch.setenv("SCBE_RHO_LOG", "1")
    monkeypatch.setenv("SCBE_RHO_LOG_PATH", str(tmp_path / "rho.jsonl"))
    on = composite_harmonic_wall(dict(distances), phase_deviation=0.05)
    assert off == on


def test_log_write_failure_does_not_break_wall(tmp_path, monkeypatch):
    """If the log path is unwritable, the wall must still return a valid result."""
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file, not a directory", encoding="utf-8")
    # makedirs() will fail because the parent is a regular file, not a dir.
    bad_path = blocker / "rho.jsonl"
    monkeypatch.setenv("SCBE_RHO_LOG", "1")
    monkeypatch.setenv("SCBE_RHO_LOG_PATH", str(bad_path))
    out = composite_harmonic_wall({"KO": 0.1})
    assert math.isfinite(out["h_composite"])
    assert out["tier"] in ("ALLOW", "QUARANTINE", "DENY")
    assert not bad_path.exists()
