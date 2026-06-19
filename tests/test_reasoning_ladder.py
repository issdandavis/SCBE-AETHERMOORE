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


def test_llm_climber_extracts_the_answer_and_grades(monkeypatch):
    # a mocked model that wraps the right answer in prose -- tests extraction + grading, no live call
    from python.helm import free_generator as fg
    from python.helm.reasoning_ladder import REASONING_LADDER, llm_climber

    answers = {it["question"]: it["answer"] for tier in REASONING_LADDER for it in tier["items"]}

    def fake_chat(messages, **kw):
        q = messages[0]["content"].split("\n\n")[0]
        return "Let me think... the answer is %s." % answers.get(q, "0")

    monkeypatch.setattr(fg, "_chat", fake_chat)
    s = run_reasoning(llm_climber(model="mock"))
    assert s["highest_tier_cleared"] == 5 and s["total_passed"] == 20


def test_extract_answer_handles_real_model_quirks():
    from python.helm.reasoning_ladder import _extract_answer

    assert _extract_answer("The answer is 56.") == "56"
    assert _extract_answer("It costs $30") == "30"
    assert _extract_answer("about 30%") == "30"
    assert _extract_answer("1,000 ways") == "1000"  # the real bug: commas used to split into '000'
    assert _extract_answer("7*8 = 56, so 56") == "56"  # non-grouping comma left alone
    assert _extract_answer("-5 degrees") == "-5"
    assert _extract_answer("no number here") == "no number here"  # falls back to text


def test_llm_climber_dead_endpoint_scores_zero(monkeypatch):
    # a dead endpoint must score 0, never a fabricated pass (honest like free_generator)
    from python.helm import free_generator as fg
    from python.helm.reasoning_ladder import llm_climber

    def boom(messages, **kw):
        raise ConnectionError("no model running")

    monkeypatch.setattr(fg, "_chat", boom)
    s = run_reasoning(llm_climber())
    assert s["total_passed"] == 0
