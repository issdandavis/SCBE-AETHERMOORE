from __future__ import annotations

import cmath

import pytest

from scripts.experiments.eml_tree_probe import EXP_TREE, LN_TREE, evaluate, run_probe, ternary_candidate


def test_exp_tree_matches_cmath_exp() -> None:
    for sample in [0.25 + 0j, 2 + 0j, 0.5 + 0.25j]:
        assert abs(evaluate(EXP_TREE, sample) - cmath.exp(sample)) <= 1e-12


def test_ln_tree_matches_cmath_log_on_positive_reals() -> None:
    for sample in [0.25 + 0j, 0.5 + 0j, 2 + 0j, 3.5 + 0j]:
        assert abs(evaluate(LN_TREE, sample) - cmath.log(sample)) <= 1e-12


def test_ternary_candidate_self_seeds_to_one_for_valid_inputs() -> None:
    for sample in [0.25 + 0j, 0.5 + 0j, 2 + 0j, 3.5 + 0j, 0.5 + 0.25j]:
        assert abs(ternary_candidate(sample, sample, sample) - 1) <= 1e-12


def test_ternary_candidate_exposes_invalid_seed_boundary() -> None:
    with pytest.raises(ZeroDivisionError):
        ternary_candidate(1 + 0j, 1 + 0j, 1 + 0j)


def test_probe_report_passes_and_keeps_boundary_note() -> None:
    result = run_probe()
    assert result["passed"] is True
    assert result["max_abs_error"] <= 1e-10
    assert "boundary_note" in result["source"]

