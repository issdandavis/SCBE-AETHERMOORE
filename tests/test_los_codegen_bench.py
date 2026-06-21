"""Tests for los_codegen_bench -- the "verified code under comms-delay, no takebacks" benchmark (wedge #1).

The benchmark's value is its HONESTY, so the tests pin the honest properties:
  * verify-before-commit lifts the no-takeback wrong rate vs the naive baseline (and a stronger gate lifts
    more) -- judged by the INDEPENDENT hidden oracle;
  * the example gate's only residual is the locally-UNOBSERVABLE overfit class (the circular-trust hole),
    never a locally-detectable failure -- proving the gate works AND that its limit is real, not a bug;
  * naive ships both wrong classes (so the lift is not an artifact of an easy generator);
  * committed decisions reconstruct identically at the far end under DTN chaos;
  * abstain is scored safe (never wrong); the whole sweep is reproducible.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "comms_sim"))

import los_codegen_bench as lb  # noqa: E402


def test_verify_before_commit_lifts_over_naive_and_stronger_gate_lifts_more():
    base = lb.run_sweep(lb.TASKS, trials=120, verifier=None)
    ex = lb.run_sweep(lb.TASKS, trials=120, verifier=lb.verify_examples)
    pr = lb.run_sweep(lb.TASKS, trials=120, verifier=lb.verify_properties)
    # the LIFT (judged by the independent hidden oracle): each stronger gate ships strictly less wrong code
    assert base["wrong"] > ex["wrong"] > pr["wrong"]
    # the property gate ~eliminates the no-takeback wrong commits
    assert pr["wrong"] <= base["wrong"] // 5


def test_example_gate_residual_is_only_the_locally_unobservable_overfit():
    ex = lb.run_sweep(lb.TASKS, trials=150, verifier=lb.verify_examples)
    # the gate NEVER commits a candidate that fails a visible example -> no wrong_visible ever ships
    assert "wrong_visible" not in ex["wrong_by_kind"]
    assert set(ex["wrong_by_kind"]) <= {"wrong_overfit"}  # the residual is exactly the circular-trust hole


def test_naive_ships_both_wrong_classes_so_the_lift_is_real():
    base = lb.run_sweep(lb.TASKS, trials=150, verifier=None)
    assert base["wrong_by_kind"].get("wrong_visible", 0) > 0
    assert base["wrong_by_kind"].get("wrong_overfit", 0) > 0


def test_committed_decisions_reconstruct_at_far_end_under_dtn_chaos():
    commits = lb.run_trial(lb.TASKS, seed=3, verifier=lb.verify_properties)
    recon, sent = lb.ship_and_reconstruct(commits, {"reorder": True, "dup_prob": 0.4}, seed=7)
    assert recon == sent  # custody + seq-replay rebuild the exact committed set


def test_abstain_is_scored_safe_not_wrong():
    # a tight local budget forces some safe abstains; they must reduce wrong commits, not be counted wrong
    naive = lb.run_sweep(lb.TASKS, trials=150, verifier=None)
    gated = lb.run_sweep(lb.TASKS, trials=150, verifier=lb.verify_examples, local_budget=1)
    assert gated["abstain"] > 0
    assert "wrong_visible" not in gated["wrong_by_kind"]  # a failed first draw abstains, never ships wrong
    assert gated["wrong"] < naive["wrong"]


def test_sweep_is_reproducible():
    a = lb.run_sweep(lb.TASKS, trials=60, verifier=lb.verify_examples)
    b = lb.run_sweep(lb.TASKS, trials=60, verifier=lb.verify_examples)
    assert a == b


def test_oracle_is_independent_of_the_gate():
    # a candidate that passes the LOCAL gate can still be judged wrong by the hidden oracle (overfit) --
    # i.e. the score is decided by the oracle, never by the gate the agent could satisfy itself
    task = lb.TASKS[0]  # clamp_0_10
    overfit = lb.candidate(task, "wrong_overfit")
    assert lb.verify_examples(overfit, task, None) is True  # passes the local gate
    assert lb.judge_against_oracle(task, "wrong_overfit", overfit) == "wrong"  # but the oracle catches it
