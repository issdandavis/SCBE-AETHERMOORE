"""reasoning_ladder: a graded auto-gradable reasoning scoreboard (sibling of curriculum, on the
ladder kernel). Exact-match grading; the answer key clears all tiers (validates the grader), the
floor clears nothing, the climb is contiguous, and measure_lift reports a raw-vs-tooled delta."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm.reasoning_ladder import (  # noqa: E402
    REASONING_LADDER,
    exact_match,
    measure_lift,
    naive_climber,
    reference_climber,
    run_reasoning,
)


def test_grader_is_exact_and_numeric():
    assert exact_match("56", "56")
    assert exact_match(" 56 ", "56")  # normalized
    assert exact_match("5", "5.0")  # numeric compare
    assert not exact_match("cat", "dog")
    assert not exact_match("", "5")  # the floor's empty answer never passes


def test_reference_clears_the_whole_ladder():
    # the answer key proves every item is solvable and the grader is correct
    s = run_reasoning(reference_climber)
    assert s["highest_tier_cleared"] == 5
    assert s["total_passed"] == s["total"] == 20


def test_naive_floor_clears_nothing():
    s = run_reasoning(naive_climber)
    assert s["highest_tier_cleared"] == 0 and s["total_passed"] == 0


def test_ladder_is_graded_and_well_formed():
    grades = [t["grade"] for t in REASONING_LADDER]
    assert grades == ["arithmetic", "pre-algebra", "competition-lite", "multi-step", "hard"]
    for t in REASONING_LADDER:
        assert len(t["items"]) == 4
        for it in t["items"]:
            assert it["question"] and it["answer"]


def test_climb_is_contiguous_from_the_bottom():
    # solves everything except one tier-3 item -> stuck at tier 2, no skipping
    def almost(item):
        return "" if item["id"] == "c1" else item["answer"]

    almost.__name__ = "almost"
    s = run_reasoning(almost)
    assert s["highest_tier_cleared"] == 2
    assert s["total_passed"] == 19


def test_measure_lift_reports_the_delta():
    # MECHANISM CHECK ONLY (naive baseline vs reference tooled) -- not a capability claim
    r = measure_lift(naive_climber, reference_climber)
    assert r["tier_lift"] == 5 and r["total_lift"] == 20
