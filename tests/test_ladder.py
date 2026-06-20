"""ladder: the shared graded-climb kernel. A tier clears only if every item passes; the climb is
the highest CONTIGUOUS tier from the bottom (no grade-skipping). Used by curriculum + reasoning."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm.ladder import render_climb, run_ladder  # noqa: E402


def _tiers():
    return [
        {"tier": 1, "grade": "a"},
        {"tier": 2, "grade": "b"},
        {"tier": 3, "grade": "c"},
    ]


def test_contiguous_climb_stops_at_first_gap():
    def score(t):
        return {"attempted": 2, "passed": {1: 2, 2: 2, 3: 1}[t["tier"]]}  # T3 partial

    s = run_ladder(_tiers(), score)
    assert s["highest_tier_cleared"] == 2
    assert s["highest_grade_cleared"] == "b"
    assert s["total_passed"] == 5 and s["total"] == 6


def test_acing_a_high_tier_while_failing_a_low_one_does_not_skip():
    def score(t):
        return {"attempted": 2, "passed": {1: 1, 2: 2, 3: 2}[t["tier"]]}  # T1 fails

    s = run_ladder(_tiers(), score)
    assert s["highest_tier_cleared"] == 0
    assert s["highest_grade_cleared"] == "none"


def test_extra_passthrough_and_render():
    def score(t):
        return {"attempted": 2, "passed": 2, "extra": {"note": "ok"}}

    s = run_ladder(_tiers(), score)
    assert all(r["note"] == "ok" for r in s["tiers"])
    out = render_climb(s, "X")
    assert "X" in out and "cleared through T3" in out
