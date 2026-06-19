"""reasoning_ladder: a graded, auto-gradable reasoning test (the scoreboard), built on ladder.py.

A general-knowledge/reasoning sibling of curriculum.py (which scores CODE). Any climber is a
`generator(item) -> answer string`; an item is graded by EXACT MATCH against a held-out answer
(numbers compared numerically). Tiers run arithmetic -> pre-algebra -> competition-lite ->
multi-step -> hard, and the climb is the highest CONTIGUOUS tier cleared (ladder.py).

WHY exact-match hand-authored items, not "the SAT": the SAT and the public sets (GSM8K/MMLU) are
saturated and likely memorized by frontier models -- a number on them is inflated and gives no
signal. These are hand-authored, contamination-free-ER, and objectively gradable (no judge model).
HONEST LIMITS: (1) few items; (2) some are classic enough to be memorizable; (3) the top tier is
"hard multi-step competition math", NOT FrontierMath/HLE difficulty (that needs gated content).
Swap in your own items; the scoreboard is the point.

This is a SCOREBOARD, not a capability claim. The real question (Issac's thesis) is LIFT: does a
model scored THROUGH the harness (logic gates + tools) beat the same model raw? `measure_lift`
computes that delta -- but a real lift number needs a real model plugged into both slots.

    python -m python.helm.reasoning_ladder --reference   # answer key: clears all (validates grader)
    python -m python.helm.reasoning_ladder --naive        # the floor: clears nothing
"""

from __future__ import annotations

import argparse
from typing import Any, Callable, Dict, List, Sequence

from .ladder import render_climb, run_ladder

Climber = Callable[[Dict[str, Any]], str]


def _q(qid: str, question: str, answer: Any) -> Dict[str, Any]:
    return {"id": qid, "question": question, "answer": str(answer)}


REASONING_LADDER: List[Dict[str, Any]] = [
    {
        "tier": 1,
        "grade": "arithmetic",
        "items": [
            _q("a1", "What is 7 * 8?", 56),
            _q("a2", "What is 1+2+3+...+10?", 55),
            _q("a3", "What is the remainder when 17 is divided by 5?", 2),
            _q("a4", "What is 144 / 12?", 12),
        ],
    },
    {
        "tier": 2,
        "grade": "pre-algebra",
        "items": [
            _q("p1", "If 3x + 4 = 19, what is x?", 5),
            _q("p2", "A train travels 60 mph for 2.5 hours. How many miles?", 150),
            _q("p3", "What is 12% of 250?", 30),
            _q("p4", "Perimeter of a rectangle 5 by 8?", 26),
        ],
    },
    {
        "tier": 3,
        "grade": "competition-lite",
        "items": [
            _q("c1", "How many positive divisors does 36 have?", 9),
            _q("c2", "What is the sum of the first 20 positive odd numbers?", 400),
            _q("c3", "How many distinct arrangements of the letters in LEVEL?", 30),
            _q("c4", "What is the GCD of 48 and 36?", 12),
        ],
    },
    {
        "tier": 4,
        "grade": "multi-step",
        "items": [
            _q("m1", "How many integers from 1 to 1000 are divisible by 3 or 5?", 467),
            _q("m2", "How many trailing zeros does 100! have?", 24),
            _q("m3", "Lattice paths from (0,0) to (4,4) moving only right or up?", 70),
            _q("m4", "Smallest n such that n! is divisible by 1000?", 15),
        ],
    },
    {
        "tier": 5,
        "grade": "hard",
        "items": [
            _q("h1", "How many positive integers below 100 are coprime to 100?", 40),
            _q("h2", "Remainder when 3^100 is divided by 100?", 1),
            _q("h3", "How many subsets of a 5-element set contain at least one element?", 31),
            _q("h4", "What is the sum of the digits of 2^10?", 7),
        ],
    },
]


def normalize_answer(a: Any) -> str:
    return str(a).strip().lower().rstrip(".").strip()


def exact_match(got: Any, want: Any) -> bool:
    g, w = normalize_answer(got), normalize_answer(want)
    if g == w:
        return True
    try:
        return abs(float(g) - float(w)) <= 1e-9
    except ValueError:
        return False


def reference_climber(item: Dict[str, Any]) -> str:
    """The answer key -- validates the grader + that items are solvable. Not a capability measure."""
    return item["answer"]


def naive_climber(item: Dict[str, Any]) -> str:
    """The floor: no answer. Should clear nothing."""
    return ""


def run_reasoning(
    climber: Climber = reference_climber, ladder: Sequence[Dict[str, Any]] = REASONING_LADDER
) -> Dict[str, Any]:
    def score(t: Dict[str, Any]) -> Dict[str, Any]:
        passed = sum(1 for it in t["items"] if exact_match(climber(it), it["answer"]))
        return {"attempted": len(t["items"]), "passed": passed}

    summary = run_ladder(ladder, score)
    summary["climber"] = getattr(climber, "__name__", "climber")
    return summary


def measure_lift(
    baseline: Climber, tooled: Climber, ladder: Sequence[Dict[str, Any]] = REASONING_LADDER
) -> Dict[str, Any]:
    """LIFT = (tooled climb) - (baseline climb). The harness 'works' only if tooled > baseline.
    Plug the SAME model into both slots -- raw vs routed-through-the-gates-and-tools -- to get a
    real number. With non-model climbers this only confirms the measurement, not capability."""
    b, t = run_reasoning(baseline, ladder), run_reasoning(tooled, ladder)
    return {
        "baseline": b["climber"],
        "tooled": t["climber"],
        "baseline_cleared": b["highest_tier_cleared"],
        "tooled_cleared": t["highest_tier_cleared"],
        "tier_lift": t["highest_tier_cleared"] - b["highest_tier_cleared"],
        "baseline_total": b["total_passed"],
        "tooled_total": t["total_passed"],
        "total_lift": t["total_passed"] - b["total_passed"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-reasoning-ladder", description="graded auto-gradable reasoning scoreboard")
    ap.add_argument("--reference", action="store_true", help="answer-key climber (validates the grader)")
    ap.add_argument("--naive", action="store_true", help="failing-floor climber")
    a = ap.parse_args(list(argv) if argv is not None else None)
    climber = naive_climber if a.naive else reference_climber
    print(render_climb(run_reasoning(climber), title="REASONING LADDER  (auto-gradable, exact-match)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
