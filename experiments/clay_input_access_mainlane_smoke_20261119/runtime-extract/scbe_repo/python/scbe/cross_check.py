"""cross_check: a differential harness that flags when two implementations of ONE contract DIVERGE.

The instrument for the failure mode that bit the observer this session: a parallel lane built a second
assumption-core surface whose jump-back target read the MINIMIZED core, silently dropping the root and
disagreeing with the canonical earliest_repair_point -- yet its own (narrow) test passed. A differential
check would have caught it: fuzz a shared input domain, run BOTH implementations on each input, and return
the FIRST divergence witness -- a concrete, reproducible counterexample, not a vague "they differ".

    agree(left, right, gen, n, seed) -> CrossCheck(agreed, samples, divergence_or_None)

Deterministic (seeded), zero-dependency. Differing return values diverge; so does a one-side exception
(one raises where the other does not, or they raise different error types) -- silent crash-divergence is a
real disagreement. A `key` normalizes outputs before comparison (e.g. to ignore order)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable, List, Optional


@dataclass
class Divergence:
    """A concrete witness: the input both implementations were run on, and what each produced. When a
    `shrinker` is supplied to agree(), `input` is the MINIMAL diverging input (delta-debugged), not the raw
    random one -- far more diagnosable."""

    index: int  # which sample (0-based) first diverged
    input: Any  # the actual (possibly shrunk) input object -- reproducible, directly re-runnable
    input_repr: str  # repr of the input -- for display
    left: Any  # left(input) result (or "raised: <Type>")
    right: Any  # right(input) result (or "raised: <Type>")


@dataclass
class CrossCheck:
    agreed: bool  # no divergence over the sample
    samples: int  # how many inputs were compared (== n on agreement; first-divergence index+1 otherwise)
    divergence: Optional[Divergence]  # the first witness, or None


def _eval(fn: Callable[[Any], Any], x: Any) -> Any:
    """Run fn(x); a raised exception becomes a sentinel string so a one-side crash is a comparable value."""
    try:
        return fn(x)
    except Exception as exc:  # a crash on one side is a genuine divergence, not a harness failure
        return "raised: %s" % type(exc).__name__


def _diverges(left: Callable, right: Callable, x: Any, key: Callable) -> bool:
    return _eval(lambda v=x: key(left(v)), x) != _eval(lambda v=x: key(right(v)), x)


def shrink_list(xs: Any) -> Any:
    """A generic shrinker for sequence inputs: each candidate drops one element. (Good for lists/histories.)"""
    for i in range(len(xs)):
        yield xs[:i] + xs[i + 1 :]


def shrink(
    left: Callable[[Any], Any],
    right: Callable[[Any], Any],
    witness: Any,
    shrinker: Callable[[Any], Any],
    key: Callable[[Any], Any] = lambda v: v,
) -> Any:
    """Greedily minimize a diverging input (delta-debugging): repeatedly replace it with the first smaller
    candidate from shrinker(current) that STILL diverges, until none does. Returns a LOCALLY-minimal witness
    (no single shrink step reduces it further) -- not guaranteed globally minimal, but far more diagnosable.
    A random 6-record divergence reduces to the 2-3 records that actually drive the disagreement."""
    current = witness
    changed = True
    while changed:
        changed = False
        for cand in shrinker(current):
            if _diverges(left, right, cand, key):
                current = cand
                changed = True
                break  # restart shrinking from the smaller candidate
    return current


def agree(
    left: Callable[[Any], Any],
    right: Callable[[Any], Any],
    gen: Callable[[random.Random], Any],
    n: int = 1000,
    seed: int = 0,
    key: Callable[[Any], Any] = lambda v: v,
    shrinker: Optional[Callable[[Any], Any]] = None,
) -> CrossCheck:
    """Fuzz n seeded inputs from `gen` and compare key(left(x)) vs key(right(x)). Return the FIRST divergence
    (a reproducible witness) or agreement over the whole sample. `gen(rng)` builds one input from a seeded
    Random; `key` normalizes outputs (default identity). If `shrinker` is given, the witness is delta-debugged
    to a locally-minimal input before reporting. Determinism: same (gen, n, seed) -> same result."""
    rng = random.Random(seed)
    for i in range(n):
        x = gen(rng)
        if _diverges(left, right, x, key):
            w = shrink(left, right, x, shrinker, key) if shrinker is not None else x
            lw = _eval(lambda v=w: key(left(v)), w)
            rw = _eval(lambda v=w: key(right(v)), w)
            return CrossCheck(agreed=False, samples=i + 1, divergence=Divergence(i, w, repr(w), lw, rw))
    return CrossCheck(agreed=True, samples=n, divergence=None)


# ---------------------------------------------------------------------------
# Applied to the contract that actually diverged this session: the observer's CBJ jump-back target. Two
# surfaces claim it -- earliest_repair_point (canonical) and earliest_repair_point_from_assumption_core. The
# parallel lane's pre-fix version read min(minimized core), dropping the root. The harness AGREES with the
# fixed surface and CATCHES the buggy one with a concrete witness.
# ---------------------------------------------------------------------------
def _gen_history(rng: random.Random) -> List[Any]:
    from .observer_dynamics import ALLOW, DENY, DecisionRecord, ESCALATE, REFUSED

    n = rng.randint(1, 6)
    routes = ["r", "s", "t", None]
    out = []
    for i in range(n):
        dec = rng.choice([ALLOW, DENY, ESCALATE, REFUSED])
        out.append(DecisionRecord(i, "in%d" % i, dec, route=rng.choice(routes)))
    return out


def _buggy_root_from_min_core(records: List[Any]) -> Optional[int]:
    """The parallel lane's pre-#2592 bug, re-created for the demo: take the earliest of the MINIMIZED core
    (which can drop the root) instead of the full-conflict earliest. The harness must catch this."""
    from .observer_dynamics import solve_under_record_assumptions

    sol = solve_under_record_assumptions(records)
    if not sol.cores:
        return None
    return min(min(c.core) for c in sol.cores)


def demo() -> dict:
    from .observer_dynamics import earliest_repair_point, earliest_repair_point_from_assumption_core

    # the FIXED surface agrees with the canonical target across a fuzz of random histories
    fixed = agree(earliest_repair_point, earliest_repair_point_from_assumption_core, _gen_history, n=3000, seed=1)
    # the BUGGY (min-of-core) surface diverges -- with a shrinker, the witness is delta-debugged to minimal
    buggy = agree(earliest_repair_point, _buggy_root_from_min_core, _gen_history, n=3000, seed=1, shrinker=shrink_list)
    return {
        "fixed_surface_agrees": fixed.agreed,
        "buggy_surface_is_caught": (not buggy.agreed) and buggy.divergence is not None,
        "buggy_witness_is_minimal": buggy.divergence is not None and len(buggy.divergence.input) <= 3,
        "_fixed": fixed,
        "_buggy": buggy,
    }


def main() -> int:
    d = demo()
    f, b = d["_fixed"], d["_buggy"]
    print("CROSS-CHECK -- differential agreement of two implementations of ONE contract")
    print("  contract: the observer CBJ jump-back target (earliest_repair_point)")
    print("  FIXED assumption-core surface agrees over %d fuzzed histories : %s" % (f.samples, f.agreed))
    if b.divergence:
        w = b.divergence
        print("  BUGGY min-of-core surface CAUGHT at sample %d (shrunk to %d records):" % (w.index, len(w.input)))
        print("    minimal witness : %s" % [(r.decision, r.route) for r in w.input])
        print("    canonical=%s  vs  buggy=%s  (the dropped root)" % (w.left, w.right))
    print("  => the harness turns a silent divergence into a MINIMAL, reproducible witness (delta-debugged).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
