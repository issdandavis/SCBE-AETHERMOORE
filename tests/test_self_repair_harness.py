"""Tests for self_repair_harness -- staged retry-loop runner + intrinsic recovery-lift."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm import self_repair_harness as h  # noqa: E402
from python.helm import staged_retry_score as srs  # noqa: E402

PROB = {
    "task_id": "add",
    "good": "def f(a,b):\n    return a+b",
    "public": ["assert f(2,3)==5"],
    "hidden": ["assert f(-1,1)==0"],
}


def test_first_try_solved_when_generator_returns_good():
    rec = h.run_problem(PROB, lambda p, i: p["good"], h._ref_repair())
    assert rec["category"] == srs.SOLVED_FIRST_TRY


def test_public_fail_then_repair_is_fix_solved():
    gen = lambda p, i: "def f(*a):\n    return None"  # noqa: E731 -- fails public, agent knows
    rec = h.run_problem(PROB, gen, h._ref_repair())
    assert rec["category"] == srs.FIX_SOLVED and rec["retried"] is True


def test_public_fail_no_repair_is_fix_failed():
    gen = lambda p, i: "def f(*a):\n    return None"  # noqa: E731
    rec = h.run_problem(PROB, gen, repair=None)  # baseline: no repair available
    assert rec["category"] == srs.FIX_FAILED and rec["retried"] is False


def test_overfit_passes_public_fails_hidden_no_retry():
    # memorizes the public answer (5), wrong on hidden -> PUBLIC_PASS_HIDDEN_FAIL, never retried
    gen = lambda p, i: "def f(*a):\n    return 5"  # noqa: E731
    rec = h.run_problem(PROB, gen, h._ref_repair())
    assert rec["category"] == srs.PUBLIC_PASS_HIDDEN_FAIL and rec["retried"] is False


def test_repair_converts_public_failures_into_lift():
    # deterministic generator: every first attempt fails the PUBLIC test (recoverable) -> repair fixes all
    gen = lambda p, i: "def f(*a):\n    return None"  # noqa: E731
    records = h.run_staged(h._ref_problems(), gen, h._ref_repair())
    lift = h.recovery_lift(records)
    assert lift["recovery_lift"] == 1.0  # all recoverable misses converted (idealized repair)
    assert lift["with_repair_solve_rate"] >= lift["first_try_solve_rate"]


def test_overfit_failures_give_no_lift_repair_is_powerless():
    # every attempt passes PUBLIC, fails HIDDEN -> never retried -> repair cannot help (the residual story)
    gen = lambda p, i: "def f(*a):\n    return %s" % p["public"][0].split("==", 1)[1].strip()  # noqa: E731
    records = h.run_staged(h._ref_problems(), gen, h._ref_repair())
    lift = h.recovery_lift(records)
    assert lift["recovery_lift"] == 0.0 and lift["overfit_no_retry_rate"] > 0.5


def test_lift_equals_fix_solved_fraction():
    records = h.run_staged(h._ref_problems(), h._ref_generator(), h._ref_repair())
    s = srs.score(records)
    expected = round(s["counts"][srs.FIX_SOLVED] / s["total"], 3)
    assert h.recovery_lift(records)["recovery_lift"] == expected  # the fair-baseline identity


def test_emitted_records_feed_staged_retry_score():
    records = h.run_staged(h._ref_problems(), h._ref_generator(), h._ref_repair())
    assert srs.score(records)["total"] == len(records) and srs.score(records)["unclassified"] == 0


def test_reproducible():
    a = h.run_staged(h._ref_problems(), h._ref_generator(), h._ref_repair())
    b = h.run_staged(h._ref_problems(), h._ref_generator(), h._ref_repair())
    assert [r["category"] for r in a] == [r["category"] for r in b]


# ---- the stronger-face gate (wedge #1+#2+#3 composition) --------------------------------------------------
def test_gate_catches_overfit_and_converts_it_to_a_retry():
    # overfit: passes PUBLIC, fails the shadow self-check -> the gate forces a retry that the repair fixes
    gen = lambda p, i: "def f(*a):\n    return %s" % p["public"][0].split("==", 1)[1].strip()  # noqa: E731
    without = h.run_problem(PROB | {"shadow": ["assert f(9,9)==18"]}, gen, h._ref_repair(), gate=None)
    withg = h.run_problem(PROB | {"shadow": ["assert f(9,9)==18"]}, gen, h._ref_repair(), gate=h._ref_shadow_gate())
    assert without["category"] == srs.PUBLIC_PASS_HIDDEN_FAIL  # no gate -> shipped wrong, no retry
    assert withg["category"] == srs.FIX_SOLVED and withg.get("caught_by_gate") is True  # gate -> caught -> fixed


def test_compare_gate_reduces_residual_and_gains_lift():
    cmp = h.compare_gate(h._ref_problems(), h._ref_generator(), h._ref_repair(), h._ref_shadow_gate())
    assert cmp["residual_reduction"] > 0  # the stronger face shrinks the overfit no-retry bucket
    assert cmp["lift_gain"] > 0  # ...and converts it into recovered solves


def test_gate_leaves_first_try_solves_untouched():
    rec = h.run_problem(PROB, lambda p, i: p["good"], h._ref_repair(), gate=h._ref_shadow_gate())
    assert rec["category"] == srs.SOLVED_FIRST_TRY  # the gate only acts on public-pass/hidden-fail
