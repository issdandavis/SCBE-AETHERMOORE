"""Unit smoke for TrendGrowthBooster.

Covers: latch behavior, fallback metric, prior-session blend, audit JSONL.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.training.callbacks.trend_growth_booster import (
    TrendGrowthBooster,
    _scan_prior_session_slopes,
)


def _curve(path: Path, ys: list[float], key: str = "mean_token_accuracy") -> None:
    metrics = [{"step": i, key: y, "epoch": float(i)} for i, y in enumerate(ys)]
    payload = {"label": path.stem, "metrics": metrics}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _hist(values: list[tuple[int, float]], key: str = "contract_eval_accuracy") -> list[dict]:
    return [{"step": s, key: v} for s, v in values]


def _drive(booster: TrendGrowthBooster, samples: list[tuple[int, float]]) -> list[dict]:
    """Feed samples one at a time so the booster sees each new step exactly once."""
    decisions: list[dict] = []
    for i in range(1, len(samples) + 1):
        decisions.append(booster.evaluate(_hist(samples[:i])))
    return decisions


def test_latches_after_two_consecutive_shortfalls(tmp_path: Path) -> None:
    booster = TrendGrowthBooster(
        trend_window=3,
        fire_ratio=0.5,
        consecutive_required=2,
        in_session_weight=1.0,
        prior_session_weight=0.0,
        prior_reports_dir=tmp_path / "no_priors",
        fire_log_path=tmp_path / "fire.jsonl",
    )

    samples = [
        (1, 0.10),
        (2, 0.30),
        (3, 0.50),
        (4, 0.52),
        (5, 0.53),
        (6, 0.54),
    ]
    _drive(booster, samples[:5])
    assert booster.is_engaged() is False
    _drive(booster, samples[5:6])
    assert booster.is_engaged() is True


def test_latch_persists_after_recovery(tmp_path: Path) -> None:
    booster = TrendGrowthBooster(
        trend_window=3,
        fire_ratio=0.5,
        consecutive_required=2,
        in_session_weight=1.0,
        prior_session_weight=0.0,
        prior_reports_dir=tmp_path / "no_priors",
        fire_log_path=tmp_path / "fire.jsonl",
        latch=True,
    )

    samples = [
        (1, 0.10),
        (2, 0.30),
        (3, 0.50),
        (4, 0.51),
        (5, 0.52),
        (6, 0.53),
        (7, 0.95),
        (8, 1.30),
    ]
    _drive(booster, samples)

    assert booster.is_engaged() is True
    booster.disengage()
    assert booster.is_engaged() is True


def test_fallback_metric_is_used_when_primary_absent(tmp_path: Path) -> None:
    booster = TrendGrowthBooster(
        trend_window=3,
        fire_ratio=0.5,
        consecutive_required=2,
        in_session_weight=1.0,
        prior_session_weight=0.0,
        prior_reports_dir=tmp_path / "no_priors",
        fire_log_path=tmp_path / "fire.jsonl",
    )

    history = [
        {"step": 1, "mean_token_accuracy": 0.10},
        {"step": 2, "mean_token_accuracy": 0.30},
        {"step": 3, "mean_token_accuracy": 0.50},
    ]
    decision = booster.evaluate(history)
    assert decision["sampled"] is True
    assert decision["value"] == pytest.approx(0.50)


def test_prior_session_slopes_are_scanned(tmp_path: Path) -> None:
    reports = tmp_path / "training_reports"
    reports.mkdir()
    _curve(reports / "run_a_training_curve_x.json", [0.1, 0.2, 0.3, 0.4])
    _curve(reports / "run_b_training_curve_y.json", [0.5, 0.6, 0.7, 0.8])

    slopes = _scan_prior_session_slopes(reports, ("contract_eval_accuracy", "mean_token_accuracy"))
    assert len(slopes) == 2
    assert all(s == pytest.approx(0.1) for s in slopes)


def test_audit_jsonl_written_on_fire(tmp_path: Path) -> None:
    log_path = tmp_path / "fire.jsonl"
    booster = TrendGrowthBooster(
        trend_window=3,
        fire_ratio=0.5,
        consecutive_required=2,
        in_session_weight=1.0,
        prior_session_weight=0.0,
        prior_reports_dir=tmp_path / "no_priors",
        fire_log_path=log_path,
    )

    samples = [(1, 0.10), (2, 0.30), (3, 0.50), (4, 0.51), (5, 0.52), (6, 0.53)]
    _drive(booster, samples)

    assert booster.is_engaged() is True
    assert log_path.exists()
    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(row.get("event") == "fire" for row in rows)


def test_no_fire_when_growth_meets_expectation(tmp_path: Path) -> None:
    booster = TrendGrowthBooster(
        trend_window=3,
        fire_ratio=0.5,
        consecutive_required=2,
        in_session_weight=1.0,
        prior_session_weight=0.0,
        prior_reports_dir=tmp_path / "no_priors",
        fire_log_path=tmp_path / "fire.jsonl",
    )

    samples = [(1, 0.10), (2, 0.30), (3, 0.50), (4, 0.70), (5, 0.90), (6, 1.10)]
    _drive(booster, samples)

    assert booster.is_engaged() is False
