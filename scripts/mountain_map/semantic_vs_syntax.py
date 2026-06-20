"""Surface spelling is not semantics -- an EXECUTED counter-measurement to the mountain map.

The mountain map (build_mountain_map.py) measures how often languages SPELL a construct with
identical characters -- a syntactic phylogeny. This script RUNS the two cases where that
surface metric anti-correlates with the actual computation, on the backends this box can run:

  * identical spelling, DIFFERENT meaning -- `1 == "1"`: one glyph `==`, but Python value
    equality says False while JavaScript coercing equality says true. The map counts `==` as a
    match; it is a semantic trap.
  * different spelling, SAME computation -- double a list: Python `[x*2 for x in xs]` vs JS
    `xs.map(x => x*2)`. Spelled nothing alike, identical result [2, 4, 6]. The map scores these
    as maximally dissimilar; semantically they are the same operation.

So the mountain map's distances are notation lineage, not semantic distance -- and a high
surface score (e.g. `==` everywhere) can hide divergence while a low one (Haskell) can hide
kinship. A full semantic distance is undecidable in general; "same computation, many faces" is
established where it counts by the shared IR + polyglot_conformance.py RUNNING the backends, not
by spelling.

    python scripts/mountain_map/semantic_vs_syntax.py
"""

from __future__ import annotations

import json
import shutil
import subprocess


def _node(expr: str) -> str:
    out = subprocess.run(
        ["node", "-e", "process.stdout.write(String(%s))" % expr],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return out.stdout.strip()


def measure() -> dict:
    """Run both cases; report where surface spelling and semantics agree or split."""
    have_node = shutil.which("node") is not None

    # Case 1: identical spelling `==`, possibly different meaning.
    py_eq = bool(1 == "1")  # Python: value equality -> False  # noqa: F632 (the trap is the point)
    js_eq_raw = _node('1 == "1"') if have_node else None  # JS: coercion -> "true"
    js_eq = {"true": True, "false": False}.get(js_eq_raw) if js_eq_raw is not None else None
    eq_diverges = (js_eq is not None) and (py_eq != js_eq)

    # Case 2: different spelling, possibly identical computation.
    py_map = [x * 2 for x in [1, 2, 3]]
    js_map_raw = _node("JSON.stringify([1,2,3].map(x => x * 2))") if have_node else None
    js_map = json.loads(js_map_raw) if js_map_raw else None
    map_converges = (js_map is not None) and (py_map == js_map)

    return {
        "have_node": have_node,
        "case1_same_spelling_eq": {
            "spelling": "== (identical in python & js)",
            "python": py_eq,
            "javascript": js_eq,
            "semantics_diverge": eq_diverges,
        },
        "case2_diff_spelling_map": {
            "spelling": "[x*2 for x in xs]  vs  xs.map(x => x*2)  (different)",
            "python": py_map,
            "javascript": js_map,
            "computation_converges": map_converges,
        },
        "lesson": (
            "surface spelling anti-correlates with semantics: identical `==` diverges, "
            "unalike map/comprehension converges -- so the mountain map is notation lineage, "
            "not semantic distance"
        ),
    }


def main() -> int:
    m = measure()
    print("SURFACE != SEMANTICS  (executed; node=%s)\n" % m["have_node"])
    c1 = m["case1_same_spelling_eq"]
    print('  case 1  identical spelling `==`  ->  1 == "1"')
    print(
        "    python=%s  javascript=%s  ->  %s"
        % (
            c1["python"],
            c1["javascript"],
            (
                "SEMANTICS DIVERGE (same glyph, different meaning)"
                if c1["semantics_diverge"]
                else "(node unavailable -- python-only)"
            ),
        )
    )
    c2 = m["case2_diff_spelling_map"]
    print("  case 2  different spelling, double a list")
    print(
        "    python=%s  javascript=%s  ->  %s"
        % (
            c2["python"],
            c2["javascript"],
            (
                "COMPUTATION CONVERGES (different spelling, same result)"
                if c2["computation_converges"]
                else "(node unavailable -- python-only)"
            ),
        )
    )
    print("\n  %s" % m["lesson"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
