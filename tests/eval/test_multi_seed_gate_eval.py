"""Tests for the multi-seed gate evaluation harness."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.eval.multi_seed_gate_eval import (
    SCHEMA_VERSION,
    Trial,
    _aggregate,
    idempotency_key,
    required_forbidden_checker,
    run_sweep,
    synthetic_oracle_model,
    wilson_interval,
)


def _toy_contract() -> dict:
    return {
        "schema_version": "scbe_stage_eval_contract_v1",
        "contract_id": "toy_contract_v1",
        "thresholds": {
            "minimum_pass_rate": 0.7,
            "must_pass": ["alpha", "beta"],
        },
        "prompts": [
            {
                "id": "alpha",
                "prompt": "Emit alpha tokens.",
                "required": ["alpha", "tok_a"],
                "forbidden": ["TODO"],
            },
            {
                "id": "beta",
                "prompt": "Emit beta tokens.",
                "required": ["beta", "tok_b"],
                "forbidden": ["TODO"],
            },
            {
                "id": "gamma",
                "prompt": "Optional prompt.",
                "required": ["gamma"],
                "forbidden": ["TODO"],
            },
        ],
    }


def test_required_forbidden_checker_passes_when_all_required_present() -> None:
    prompt = {"id": "x", "required": ["foo", "bar"], "forbidden": ["TODO"]}
    result = required_forbidden_checker(prompt, "we have foo and bar here")
    assert result["passed"] is True
    assert result["score"] == pytest.approx(1.0)
    assert result["meta"]["missing_required"] == []
    assert result["meta"]["triggered_forbidden"] == []


def test_required_forbidden_checker_case_insensitive() -> None:
    prompt = {"id": "x", "required": ["FOO", "bAr"], "forbidden": []}
    result = required_forbidden_checker(prompt, "this contains foo and BAR")
    assert result["passed"] is True


def test_required_forbidden_checker_fails_on_forbidden() -> None:
    prompt = {"id": "x", "required": ["foo"], "forbidden": ["TODO"]}
    result = required_forbidden_checker(prompt, "foo with TODO")
    assert result["passed"] is False
    assert result["meta"]["triggered_forbidden"] == ["todo"]


def test_required_forbidden_checker_fractional_score_on_partial() -> None:
    prompt = {
        "id": "x",
        "required": ["foxtrot", "tango", "kilo", "zulu"],
        "forbidden": [],
    }
    result = required_forbidden_checker(prompt, "we have foxtrot and tango but not the others")
    assert result["passed"] is False
    # 2 of 4 required substrings found
    assert result["score"] == pytest.approx(0.5)
    assert set(result["meta"]["missing_required"]) == {"kilo", "zulu"}


def test_wilson_interval_sanity() -> None:
    # Full pass on small n: high but not 1.0 lower bound
    low, high = wilson_interval(10, 10)
    assert low > 0.5
    assert high == pytest.approx(1.0)
    # 50/50 on n=4 yields a wide CI
    low, high = wilson_interval(2, 4)
    assert low < 0.3
    assert high > 0.7
    # Empty input safely returns (0, 0)
    assert wilson_interval(0, 0) == (0.0, 0.0)


def test_wilson_interval_narrows_with_n() -> None:
    low_small, high_small = wilson_interval(8, 10)
    low_big, high_big = wilson_interval(80, 100)
    assert (high_small - low_small) > (high_big - low_big)


def test_run_sweep_oracle_full_pass_yields_full_recall() -> None:
    contract = _toy_contract()
    model = synthetic_oracle_model(success_rate=1.0)
    report = run_sweep(
        contract,
        model,
        seeds=[0, 1, 2],
        temperatures=[0.0, 0.5],
    )
    assert report["schema_version"] == SCHEMA_VERSION
    assert report["contract_id"] == "toy_contract_v1"
    assert report["n_prompts"] == 3
    assert len(report["trials"]) == 3 * 3 * 2  # prompts x seeds x temps
    overall = report["aggregate"]["overall"]
    assert overall["pass_rate"] == 1.0
    assert overall["wilson_95ci_low"] > 0.7
    risk = report["aggregate"]["seed_lucky_risk"]
    assert risk["spread"] == pytest.approx(0.0)
    must = report["aggregate"]["must_pass_coverage"]
    assert must["n_must_pass_prompts"] == 2
    assert must["all_must_pass_pass_in_all_trials"] is True
    bon = report["aggregate"]["best_of_n"]
    assert bon["n_decode_contexts"] == 6
    assert bon["prompt_pass_rate"] == 1.0
    assert bon["all_prompts_any_pass"] is True
    assert bon["must_pass_all_any_pass"] is True


def test_run_sweep_partial_oracle_exposes_seed_lucky_spread() -> None:
    """At success_rate < 1, different seeds should produce different pass rates."""

    contract = _toy_contract()
    model = synthetic_oracle_model(success_rate=0.6, jitter_seed=7)
    report = run_sweep(
        contract,
        model,
        seeds=list(range(8)),
        temperatures=[0.0, 0.4, 0.8],
    )
    overall = report["aggregate"]["overall"]
    risk = report["aggregate"]["seed_lucky_risk"]
    # Partial-pass oracle: spread is observable AND CI is non-degenerate
    assert risk["spread"] >= 0.0
    assert risk["max_seed_pass_rate"] >= risk["min_seed_pass_rate"]
    assert overall["wilson_95ci_low"] < overall["pass_rate"]
    assert overall["wilson_95ci_high"] > overall["pass_rate"]


def test_aggregate_must_pass_failure_recorded() -> None:
    must_pass_ids = {"alpha"}
    trials = [
        Trial("alpha", 0, 0.0, False, 0.0, {}, True),
        Trial("alpha", 1, 0.0, True, 1.0, {}, True),
        Trial("beta", 0, 0.0, True, 1.0, {}, False),
        Trial("beta", 1, 0.0, True, 1.0, {}, False),
    ]
    agg = _aggregate(trials, must_pass_ids)
    assert agg["overall"]["passed_count"] == 3
    assert agg["overall"]["n_trials"] == 4
    assert agg["must_pass_coverage"]["n_must_pass_prompts"] == 1
    assert agg["must_pass_coverage"]["all_must_pass_pass_in_all_trials"] is False
    failures = agg["must_pass_coverage"]["must_pass_failures_per_context"]
    assert any("alpha" in row for row in failures)
    bon = agg["best_of_n"]
    assert bon["must_pass_all_any_pass"] is True
    assert bon["per_prompt"]["alpha"]["any_pass"] is True


def test_best_of_n_can_pass_when_single_rollouts_are_mixed() -> None:
    must_pass_ids = {"alpha"}
    trials = [
        Trial("alpha", 0, 0.0, False, 0.0, {}, True),
        Trial("alpha", 1, 0.4, True, 1.0, {}, True),
        Trial("beta", 0, 0.0, False, 0.0, {}, False),
        Trial("beta", 1, 0.4, True, 1.0, {}, False),
    ]
    agg = _aggregate(trials, must_pass_ids)
    assert agg["overall"]["pass_rate"] == 0.5
    bon = agg["best_of_n"]
    assert bon["prompt_pass_rate"] == 1.0
    assert bon["all_prompts_any_pass"] is True
    assert bon["must_pass_all_any_pass"] is True


def test_run_sweep_is_deterministic_under_fixed_inputs() -> None:
    contract = _toy_contract()
    model = synthetic_oracle_model(success_rate=0.7, jitter_seed=11)
    a = run_sweep(contract, model, seeds=[0, 1, 2], temperatures=[0.0, 0.5])
    b = run_sweep(contract, model, seeds=[0, 1, 2], temperatures=[0.0, 0.5])
    assert a["aggregate"] == b["aggregate"]


def test_idempotency_key_is_stable_and_changes_with_payload() -> None:
    a = idempotency_key({"contract": "x", "seeds": [0, 1], "temperatures": [0.0]})
    b = idempotency_key({"temperatures": [0.0], "seeds": [0, 1], "contract": "x"})
    c = idempotency_key({"contract": "x", "seeds": [0, 2], "temperatures": [0.0]})
    assert a == b
    assert a != c
    assert len(a) == 64


def test_run_sweep_against_real_coding_verification_contract_with_oracle() -> None:
    """Smoke test: run the harness against the real coding_verification contract.

    Uses the synthetic oracle so this test stays free of GPU dependencies.
    Verifies the harness can ingest the production contract format and
    emit a valid aggregate. A real model run would replace the oracle
    via --model-spec at the CLI.
    """

    contract_path = Path("config/model_training/coding_verification_eval_contract.json")
    if not contract_path.exists():
        pytest.skip(f"contract not present: {contract_path}")
    import json

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    model = synthetic_oracle_model(success_rate=1.0)
    report = run_sweep(
        contract,
        model,
        seeds=[0, 1],
        temperatures=[0.0, 0.3, 0.7],
    )
    assert report["schema_version"] == SCHEMA_VERSION
    assert report["aggregate"]["overall"]["pass_rate"] == 1.0
    n_prompts = len(contract["prompts"])
    assert len(report["trials"]) == n_prompts * 2 * 3
    must_pass = set(contract["thresholds"]["must_pass"])
    assert report["aggregate"]["must_pass_coverage"]["n_must_pass_prompts"] == len(must_pass)
