"""ladder: the shared kernel for graded "how high did it climb" tests.

curriculum.py (code, scored by running held-out tests) and reasoning_ladder.py (Q&A, scored by
exact match) are the SAME shape -- tiers of held-out items, a climber, a score per tier, and the
climb is the highest CONTIGUOUS tier cleared from the bottom (no grade-skipping). That shape lives
here once, with the scorer left pluggable, so the content and grading differ across ladders but the
laddering is never reimplemented. (Extracted after the redundancy gate flagged the overlap.)
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Sequence

# score_tier(tier) -> {"attempted": int, "passed": int, "extra": {...optional passthrough...}}
ScoreTier = Callable[[Dict[str, Any]], Dict[str, Any]]


def run_ladder(tiers: Sequence[Dict[str, Any]], score_tier: ScoreTier) -> Dict[str, Any]:
    """Score every tier, then report the highest CONTIGUOUS tier cleared from the bottom.

    A tier is cleared only if every item in it passes. The climb stops at the first tier that is
    not fully cleared -- acing tier 5 while failing tier 3 still leaves you stuck at tier 2."""
    per_tier: List[Dict[str, Any]] = []
    for t in tiers:
        s = score_tier(t)
        attempted, passed = int(s["attempted"]), int(s["passed"])
        row: Dict[str, Any] = {
            "tier": t["tier"],
            "grade": t["grade"],
            "attempted": attempted,
            "passed": passed,
            "cleared": attempted > 0 and passed == attempted,
        }
        row.update(s.get("extra", {}))
        per_tier.append(row)
    climb = 0
    for r in per_tier:
        if r["cleared"]:
            climb = r["tier"]
        else:
            break
    grade = next((r["grade"] for r in per_tier if r["tier"] == climb), "none")
    return {
        "highest_tier_cleared": climb,
        "highest_grade_cleared": grade,
        "total_passed": sum(r["passed"] for r in per_tier),
        "total": sum(r["attempted"] for r in per_tier),
        "tiers": per_tier,
    }


def render_climb(summary: Dict[str, Any], title: str = "LADDER CLIMB") -> str:
    lines = [title]
    for r in summary["tiers"]:
        bar = "#" * r["passed"] + "." * (r["attempted"] - r["passed"])
        mark = "PASS" if r["cleared"] else ""
        lines.append("  T%d %-13s %d/%d  %-10s %s" % (r["tier"], r["grade"], r["passed"], r["attempted"], bar, mark))
    lines.append(
        "  --> cleared through T%d (%s);  total %d/%d"
        % (summary["highest_tier_cleared"], summary["highest_grade_cleared"], summary["total_passed"], summary["total"])
    )
    return "\n".join(lines)
