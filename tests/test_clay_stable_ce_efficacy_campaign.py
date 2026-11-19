from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from python.scbe.clay_stable_ce_efficacy_campaign import (
    EXPECTED_SEEDS,
    _comparison,
    parse_args,
)


def _row(seed: int, accuracy: float, macro_f1: float, predictions: list[dict]) -> dict:
    return {
        "seed": seed,
        "metrics": {"accuracy": accuracy, "macro_f1": macro_f1},
        "predictions": predictions,
    }


def test_parse_args_pins_three_seeds_and_controls() -> None:
    args = parse_args(
        [
            "--baseline-run",
            "baseline",
            "--output-dir",
            "output",
            "--source-dir",
            "source",
            "--preregistration",
            "pre.json",
        ]
    )
    assert args.seeds == EXPECTED_SEEDS
    assert args.steps == 2000
    assert args.checkpoint_every == 250
    assert args.batch_size == 128


def test_parse_args_rejects_nonpositive_budget() -> None:
    with pytest.raises(SystemExit):
        parse_args(
            [
                "--baseline-run",
                "baseline",
                "--output-dir",
                "output",
                "--source-dir",
                "source",
                "--preregistration",
                "pre.json",
                "--steps",
                "0",
            ]
        )


def test_comparison_keeps_metric_and_paired_controls() -> None:
    primary = []
    control = []
    for index, seed in enumerate(EXPECTED_SEEDS):
        primary.append(
            _row(
                seed,
                0.8 + index * 0.01,
                0.7 + index * 0.01,
                [{"example_index": 0, "correct": True}],
            )
        )
        control.append(
            _row(
                seed,
                0.2 + index * 0.01,
                0.1 + index * 0.01,
                [{"example_index": 0, "correct": False}],
            )
        )
    result = _comparison(primary, control)
    assert result["metrics"]["accuracy"]["clears_positive_gate"] is True
    assert result["metrics"]["macro_f1"]["clears_positive_gate"] is True
    assert result["paired"]["wins"] == 3


def test_argparse_namespace_keeps_paths() -> None:
    args = parse_args(
        [
            "--baseline-run",
            "baseline",
            "--output-dir",
            "output",
            "--source-dir",
            "source",
            "--preregistration",
            "pre.json",
        ]
    )
    assert isinstance(args, argparse.Namespace)
    assert args.output_dir == Path("output")
