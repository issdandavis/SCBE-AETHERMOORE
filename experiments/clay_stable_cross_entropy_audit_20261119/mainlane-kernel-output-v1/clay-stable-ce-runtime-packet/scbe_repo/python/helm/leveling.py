"""leveling: a "slope to skill" difficulty track over the curriculum -- Line Rider, not a cliff.

`curriculum` grades a climber in whole TIERS: clear all 3 problems of a tier or you "climbed nothing"
of it, and the score is the highest CONTIGUOUS tier. That is a cliff. A model that solves
`reverse_string` but not `fizzbuzz` scores the same as one that solves neither -- the partial
progress is thrown away, and you learn nothing about WHERE it crashed.

This is the level-design fix. The same problems, the same hidden-test verification (run_public_bench),
but laid out as a smooth TRACK a rider climbs one step at a time:

  * SLOPE TO SKILL -- every problem gets a difficulty on a curve, so the ramp is smooth, not stepped.
    The curve is the level designer's knob (the shape of the hill): `gentle` gives a shallow on-ramp
    so a weak rider builds momentum before the climbs get steep; `steep` front-loads the hard stuff;
    `golden` spaces difficulty by powers of phi. Pick the slope that fits the rider.
  * MOMENTUM + CRASH -- clearing a level lifts the rider's skill to that height; a miss is a crash.
    `patience` is how many crashes in a row the rider survives before the run ends (a forgiving slope
    lets it skip one bump and try the next). So the run stops at the rider's real CEILING, not at the
    first pebble, and it doesn't waste budget hammering a wall.
  * CONTINUOUS SCORE -- "how high did it ride" (peak difficulty cleared) + how many levels + how clean
    the ride was. A weak climber gets a real graded number where the tier cliff gave it a zero.

Honest scope: this does NOT make a model better at code -- it is measurement + sequencing. Its value
is recovering the signal the cliff discards and keeping a weak rider in its productive zone. The
climber is the same pluggable `public_bench.Generator`; the verification is the same hidden tests.

    python -m python.helm.leveling --reference        # rides clean to the top (track is real)
    python -m python.helm.leveling --capped 25         # a rider with a skill ceiling -> graded climb
    python -m python.helm.leveling --compare           # the same rider on every slope shape
"""

from __future__ import annotations

import argparse
from typing import Any, Dict, List, Optional, Sequence

from .curriculum import CURRICULUM, run_curriculum
from .public_bench import Generator, naive_generator, reference_generator, run_public_bench

PHI = (1 + 5**0.5) / 2
CURVES = ("linear", "gentle", "steep", "golden")


def _curve(x: float, shape: str) -> float:
    """Map a normalized position x in [0,1] along the track to a normalized height in [0,1]."""
    if shape == "linear":
        return x
    if shape == "gentle":  # shallow early (easy on-ramp), steeper later
        return x**1.8
    if shape == "steep":  # hard fast (front-loaded cliff)
        return x**0.55
    if shape == "golden":  # difficulty spaced by powers of phi (growth curve)
        return (PHI ** (3 * x) - 1) / (PHI**3 - 1)
    raise ValueError("unknown curve %r (have %s)" % (shape, ", ".join(CURVES)))


def difficulty(rank: int, n: int, curve: str = "linear") -> float:
    """The difficulty (0..100) of the rank-th level out of n, under the chosen slope shape."""
    x = rank / max(1, n - 1)
    return round(_curve(x, curve) * 100, 1)


def track(curriculum: Sequence[Dict[str, Any]] = CURRICULUM) -> List[Dict[str, Any]]:
    """Flatten the tiered curriculum into one ordered track of levels (rank 0 = easiest)."""
    levels: List[Dict[str, Any]] = []
    rank = 0
    for t in curriculum:
        for prob in t["problems"]:
            levels.append({"id": prob["task_id"], "tier": t["tier"], "rank": rank, "problem": prob})
            rank += 1
    return levels


def ride(
    generator: Generator = reference_generator,
    curve: str = "linear",
    patience: int = 1,
    public_k: int = 1,
    curriculum: Sequence[Dict[str, Any]] = CURRICULUM,
) -> Dict[str, Any]:
    """Climb the track bottom-up; stop after `patience` consecutive crashes (the rider's ceiling)."""
    levels = track(curriculum)
    n = len(levels)
    for lv in levels:
        lv["difficulty"] = difficulty(lv["rank"], n, curve)
    skill, peak, crashes, run_crash = 0.0, 0.0, 0, 0
    cleared: List[str] = []
    trace: List[Dict[str, Any]] = []
    for lv in levels:
        s = run_public_bench([lv["problem"]], generator=generator, public_k=public_k)
        ok = s["attempted"] > 0 and s["verified"] == s["attempted"]
        d = lv["difficulty"]
        if ok:
            cleared.append(lv["id"])
            skill = d
            peak = max(peak, d)
            run_crash = 0
            trace.append({"id": lv["id"], "tier": lv["tier"], "difficulty": d, "result": "clear"})
        else:
            crashes += 1
            run_crash += 1
            trace.append({"id": lv["id"], "tier": lv["tier"], "difficulty": d, "result": "crash"})
            if run_crash >= patience:
                break
    attempted = len(trace)
    smoothness = round(len(cleared) / attempted, 2) if attempted else 0.0
    return {
        "generator": generator.__name__,
        "curve": curve,
        "patience": patience,
        "levels": n,
        "cleared": len(cleared),
        "attempted": attempted,
        "peak_difficulty": peak,
        "skill": skill,
        "crashes": crashes,
        "smoothness": smoothness,
        "cleared_ids": cleared,
        "trace": trace,
    }


def skill_capped_generator(
    max_difficulty: float,
    curve: str = "linear",
    curriculum: Sequence[Dict[str, Any]] = CURRICULUM,
) -> Generator:
    """A synthetic rider with a known skill ceiling: solves levels at/below max_difficulty, fails above.

    Not a real model -- a deterministic stand-in to exercise + test the leveling mechanics, so the
    track's behaviour is provable without a live model in the loop.
    """
    levels = track(curriculum)
    n = len(levels)
    diff = {lv["id"]: difficulty(lv["rank"], n, curve) for lv in levels}

    def gen(problem: Dict[str, Any]) -> str:
        d = diff.get(problem["task_id"], 0.0)
        return reference_generator(problem) if d <= max_difficulty else naive_generator(problem)

    gen.__name__ = "capped@%g" % max_difficulty
    return gen


def cliff_vs_slope(generator: Generator, curve: str = "linear", patience: int = 1) -> Dict[str, Any]:
    """Contrast the tier CLIFF (highest contiguous tier) with the SLOPE ride (graded), same climber."""
    cliff = run_curriculum(generator=generator)
    slope = ride(generator, curve=curve, patience=patience)
    return {
        "cliff_tier": cliff["highest_tier_cleared"],
        "cliff_grade": cliff["highest_grade_cleared"],
        "slope_cleared": slope["cleared"],
        "slope_of": slope["levels"],
        "slope_peak": slope["peak_difficulty"],
        "recovered": [
            t["id"] for t in slope["trace"] if t["result"] == "clear" and t["tier"] > cliff["highest_tier_cleared"]
        ],
    }


def render(r: Dict[str, Any]) -> str:
    """Draw the ride as a little hill: each level a rung at its height, cleared (=) or crashed (X)."""
    lines = [
        "SLOPE RIDE  (curriculum as a difficulty track, hidden-test verified)",
        "  rider: %s   slope: %s   patience: %d" % (r["generator"], r["curve"], r["patience"]),
    ]
    for t in r["trace"]:
        rung = int(t["difficulty"] / 5)
        mark = "=" if t["result"] == "clear" else "X"
        pad = " " * rung
        lines.append("  T%d %-15s %5.1f |%s%s" % (t["tier"], t["id"], t["difficulty"], pad, mark))
    lines.append(
        "  --> rode to difficulty %.1f; cleared %d/%d levels; %d crash(es); smoothness %.2f"
        % (r["peak_difficulty"], r["cleared"], r["levels"], r["crashes"], r["smoothness"])
    )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-leveling", description="ride the curriculum as a slope, not a cliff")
    ap.add_argument("--reference", action="store_true", help="answer-key rider (rides clean to the top)")
    ap.add_argument("--naive", action="store_true", help="failing-stub rider (crashes at the first rung)")
    ap.add_argument("--capped", type=float, metavar="D", help="a synthetic rider with a skill ceiling at difficulty D")
    ap.add_argument("--curve", choices=CURVES, default="linear", help="the slope shape (level design)")
    ap.add_argument("--patience", type=int, default=1, help="consecutive crashes the rider survives")
    ap.add_argument("--compare", action="store_true", help="the same capped rider on every slope shape")
    ap.add_argument("--llm", action="store_true", help="ride a free local small model (Ollama via helm.free_generator)")
    ap.add_argument("--model", help="model id for --llm (default: SCBE_LLM_MODEL or the free_generator default)")
    a = ap.parse_args(list(argv) if argv is not None else None)

    if a.compare:
        gen = skill_capped_generator(a.capped if a.capped is not None else 40.0)
        print("SLOPE COMPARISON  same rider (%s), different track shapes\n" % gen.__name__)
        for shape in CURVES:
            r = ride(gen, curve=shape, patience=a.patience)
            print(
                "  %-7s -> cleared %d/%d  peak %.1f  smoothness %.2f"
                % (shape, r["cleared"], r["levels"], r["peak_difficulty"], r["smoothness"])
            )
        return 0

    if a.naive:
        gen = naive_generator
    elif a.llm:
        from .free_generator import make_generator

        gen = make_generator(model=a.model)
    elif a.capped is not None:
        gen = skill_capped_generator(a.capped, curve=a.curve)
    else:
        gen = reference_generator
    r = ride(gen, curve=a.curve, patience=a.patience)
    print(render(r))
    if a.capped is not None or a.llm:
        c = cliff_vs_slope(gen, curve=a.curve, patience=a.patience)
        print(
            "\n  CLIFF vs SLOPE: the tier cliff says 'tier %d (%s)'; the slope also credits %s"
            % (c["cliff_tier"], c["cliff_grade"], c["recovered"] or "(nothing past the cliff)")
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
