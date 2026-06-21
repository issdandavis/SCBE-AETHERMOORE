"""los_codegen_bench: LoS-Codegen -- "verified code under comms-delay, NO TAKEBACKS" (research wedge #1).

The unmet measurement at the intersection of space-robotics autonomy and AI code generation. At planetary
delay an onboard agent must COMMIT code it cannot revise (loss-of-signal); the only thing that matters is
whether what it shipped is correct -- and whether VERIFYING BEFORE COMMIT (the SCBE thesis) prevents
shipping wrong code when there are no takebacks.

This is a $0, install-free, deterministic harness. A FLAKY code generator (models an unreliable onboard
model) runs under three protocols over the SAME seeded DTN link (reusing mars_dtn_sim):
  * naive               -- commit the first thing generated (no local check)            [the fair baseline]
  * LoS-safe + examples -- verify against the LOCAL visible examples before commit; on failure regenerate
                           within a phone-home-free budget; if exhausted, commit a SAFE ABSTAIN (defer to
                           ground) instead of guessing.
  * LoS-safe + properties -- same, but the local gate is partial INVARIANTS (a stronger face).
Committed decisions are shipped as DTN bundles; the FAR END reconstructs them and judges with HIDDEN tests
the generator never saw -- the INDEPENDENT ORACLE (the real mission outcome).

WHY THE DESIGN IS HONEST (it answers the three traps the research critique flagged):
  1. INDEPENDENT ORACLE. Correctness is judged by hidden tests that are NOT the local gate. Cross-face /
     example agreement alone never decides the score (a candidate can be consistently wrong locally).
  2. FAIR BASELINE = THE LIFT. The headline is the no-takeback wrong-commit rate of each gated protocol
     RELATIVE TO naive (same generator, same seeds, same link). We report the delta, not a harness score --
     the repo was already burned by a +24 that died in fair controls.
  3. THE CIRCULAR-TRUST RESIDUAL IS MEASURED, NOT HIDDEN. The local gate can only see local info, so it
     CANNOT catch a candidate that passes every local check but fails the hidden oracle ("overfit"). That
     residual is reported by kind -- it is exactly the trust-without-a-reviewer hole, and exactly what a
     STRONGER face (cross-language execution / a sound C checker -- the next wedge) is needed to close.

SCOPE (honest): the candidate CODE and its execution are real; only WHICH candidate a flaky model emits is
simulated. v1 uses self-contained pure-Python tasks (zero installs); wrapping real F-prime/Basilisk tasks
with a real small model (e.g. Qwen2.5-Coder) is the next step -- the `generate`/`verifier` seams are
pluggable for exactly that. consistency != correctness; a passed local check is evidence, not proof.

    PYTHONPATH=. python research/comms_sim/los_codegen_bench.py
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import mars_dtn_sim as dtn  # noqa: E402  (sibling: the NASA-DTN relay model)

SAFE_ABSTAIN = "ABSTAIN(defer-to-ground)"  # the conservative safe-mode commit: do no harm, wait for ground
_ERR = object()  # sentinel: a candidate that raised is simply wrong


def _call(fn: Callable[..., Any], args: tuple) -> Any:
    try:
        return fn(*args)
    except Exception:  # noqa: BLE001 -- a crashing candidate is just a wrong answer
        return _ERR


# --- partial invariants used by the property gate. These are PARTIAL specs (NOT the reference impl and NOT
#     the hidden oracle): they constrain the answer without fully determining it, the way a real spec does. -
def _p_clamp_range(fn, a, o):
    return o is not _ERR and 0 <= o <= 10


def _p_clamp_identity(fn, a, o):
    return not (0 <= a[0] <= 10) or o == a[0]


def _p_absdiff_nonneg(fn, a, o):
    return o is not _ERR and o >= 0


def _p_absdiff_symmetric(fn, a, o):
    return _call(fn, (a[1], a[0])) == o


def _p_sign_range(fn, a, o):
    return o in (-1, 0, 1)


def _p_sign_odd(fn, a, o):
    return o is not _ERR and _call(fn, (-a[0],)) == -o


def _p_last_append(fn, a, o):
    return _call(fn, (a[0] + [7],)) == 7  # metamorphic: appending 7 must make the last element 7


def _p_last_empty(fn, a, o):
    return a[0] != [] or o == 0


def _p_count_bounds(fn, a, o):
    return o is not _ERR and 0 <= o <= len(a[0])


def _p_count_add_pos(fn, a, o):
    return o is not _ERR and _call(fn, (a[0] + [9],)) == o + 1  # adding a positive raises the count by 1


def _p_count_add_zero(fn, a, o):
    return o is not _ERR and _call(fn, (a[0] + [0],)) == o  # adding a non-positive leaves it unchanged


@dataclass(frozen=True)
class Task:
    """A coding task. `correct` is the reference; `wrong_general` is a broadly-wrong impl (fails some
    examples AND some hidden cases). `examples` is the LOCAL visible I/O the onboard agent may check; `hidden`
    is the INDEPENDENT ORACLE the far end judges with; `properties` are partial invariants for the property
    gate; `rand_args` generates random inputs for property testing."""

    name: str
    correct: Callable[..., Any]
    wrong_general: Callable[..., Any]
    examples: List[Tuple[tuple, Any]]
    hidden: List[Tuple[tuple, Any]]
    properties: List[Callable[..., bool]]
    rand_args: Callable[[random.Random], tuple]


def _memorize(examples, fallback):
    """A candidate that MEMORIZES the visible examples and falls back to a wrong general formula otherwise --
    i.e. it passes every local example yet is wrong on unseen inputs. The realistic overfit failure mode, and
    the one a local gate provably cannot catch."""
    table = {repr(tuple(a)): o for a, o in examples}

    def f(*args):
        return table.get(repr(tuple(args)), fallback(*args))

    return f


# kind -> how it behaves vs the LOCAL example gate / the HIDDEN oracle:
#   correct        passes examples,  passes hidden
#   wrong_visible  FAILS examples,   fails hidden     (locally detectable)
#   wrong_overfit  passes examples,  FAILS hidden     (locally UNDETECTABLE -> the circular-trust residual)
def candidate(task: Task, kind: str) -> Callable[..., Any]:
    if kind == "correct":
        return task.correct
    if kind == "wrong_visible":
        return task.wrong_general
    if kind == "wrong_overfit":
        return _memorize(task.examples, task.wrong_general)
    raise ValueError(kind)


TASKS: List[Task] = [
    Task(
        "clamp_0_10",
        lambda x: max(0, min(10, x)),
        lambda x: min(10, x),
        [((5,), 5), ((-3,), 0), ((20,), 10), ((0,), 0)],
        [((7,), 7), ((-100,), 0), ((11,), 10), ((1000,), 10)],
        [_p_clamp_range, _p_clamp_identity],
        lambda rng: (rng.randint(-50, 50),),
    ),
    Task(
        "abs_diff",
        lambda a, b: abs(a - b),
        lambda a, b: a - b,
        [((3, 5), 2), ((10, 4), 6), ((7, 7), 0)],
        [((1, 9), 8), ((100, 0), 100), ((0, 100), 100)],
        [_p_absdiff_nonneg, _p_absdiff_symmetric],
        lambda rng: (rng.randint(-50, 50), rng.randint(-50, 50)),
    ),
    Task(
        "sign",
        lambda x: (x > 0) - (x < 0),
        lambda x: 1 if x > 0 else 0,
        [((5,), 1), ((-2,), -1), ((0,), 0)],
        [((100,), 1), ((-100,), -1), ((0,), 0), ((-1,), -1)],
        [_p_sign_range, _p_sign_odd],
        lambda rng: (rng.randint(-50, 50),),
    ),
    Task(
        "last_or_zero",
        lambda xs: xs[-1] if xs else 0,
        lambda xs: xs[0] if xs else 0,
        [(([1, 2, 3],), 3), (([5],), 5), (([],), 0)],
        [(([9, 8, 7],), 7), (([1, 2],), 2), (([],), 0)],
        [_p_last_append, _p_last_empty],
        lambda rng: ([rng.randint(-9, 9) for _ in range(rng.randint(0, 5))],),
    ),
    Task(
        "count_positives",
        lambda xs: sum(1 for v in xs if v > 0),
        lambda xs: sum(1 for v in xs if v >= 0),
        [(([1, -2, 3],), 2), (([-1, -2],), 0), (([0, 5],), 1)],
        [(([0, 0, 0],), 0), (([1, 2, 3],), 3), (([-5, 5],), 1)],
        [_p_count_bounds, _p_count_add_pos, _p_count_add_zero],
        lambda rng: ([rng.randint(-9, 9) for _ in range(rng.randint(0, 6))],),
    ),
]

TRIALS = 200


# ---- the LOCAL gates (phone-home-free). A gate sees only local info; it never sees the hidden oracle. ----
def verify_examples(fn: Callable[..., Any], task: Task, rng: random.Random) -> bool:
    return all(_call(fn, args) == exp for args, exp in task.examples)


def verify_properties(fn: Callable[..., Any], task: Task, rng: random.Random, trials: int = 40) -> bool:
    if not verify_examples(fn, task, rng):  # properties subsume the visible examples
        return False
    for _ in range(trials):
        args = task.rand_args(rng)
        out = _call(fn, args)
        if out is _ERR or not all(p(fn, args, out) for p in task.properties):
            return False
    return True


# ---- the flaky onboard GENERATOR (pluggable: a real model returns (label, fn) here instead). ----
def simulated_generator(task: Task, rng: random.Random, weights=(0.5, 0.3, 0.2)) -> Tuple[str, Callable]:
    r = rng.random()
    if r < weights[0]:
        kind = "correct"
    elif r < weights[0] + weights[1]:
        kind = "wrong_visible"
    else:
        kind = "wrong_overfit"
    return kind, candidate(task, kind)


# ---- the INDEPENDENT ORACLE: the far end judges a committed candidate on hidden tests it never saw. ----
def judge_against_oracle(task: Task, kind: str, fn) -> str:
    if kind == "abstain":
        return "abstain"  # safe-mode commit: not correct, but did no harm
    ok = fn is not None and all(_call(fn, args) == exp for args, exp in task.hidden)
    return "correct" if ok else "wrong"


def solve_task(task, rng, *, generator=simulated_generator, verifier=None, local_budget=5):
    """Produce one committed (kind, fn). naive (verifier=None) commits the first generation. A gated protocol
    regenerates locally until the gate passes or the phone-home-free budget is spent, then SAFE-ABSTAINS."""
    if verifier is None:
        return generator(task, rng)
    for _ in range(local_budget):
        kind, fn = generator(task, rng)
        if verifier(fn, task, rng):
            return kind, fn
    return "abstain", None


def run_trial(tasks, seed, *, generator=simulated_generator, verifier=None, local_budget=5):
    """One mission's commits. Per task the RNG is seeded by (seed, task index) so every protocol faces the
    same first generation -- the comparison is the protocol, not luck of the draw."""
    out = []
    for i, task in enumerate(tasks):
        rng = random.Random("%d-%d" % (seed, i))
        kind, fn = solve_task(task, rng, generator=generator, verifier=verifier, local_budget=local_budget)
        out.append((task.name, kind, judge_against_oracle(task, kind, fn)))
    return out


def run_sweep(tasks, trials=TRIALS, *, generator=simulated_generator, verifier=None, local_budget=5) -> Dict:
    tally = {"correct": 0, "wrong": 0, "abstain": 0}
    wrong_by_kind: Dict[str, int] = {}
    for s in range(trials):
        for _name, kind, verdict in run_trial(
            tasks, s, generator=generator, verifier=verifier, local_budget=local_budget
        ):
            tally[verdict] += 1
            if verdict == "wrong":
                wrong_by_kind[kind] = wrong_by_kind.get(kind, 0) + 1
    return {"total": trials * len(tasks), **tally, "wrong_by_kind": wrong_by_kind}


def ship_and_reconstruct(commits, conditions, seed=7):
    """Autonomy: ship each committed decision as a DTN bundle, then rebuild it at the far end by seq-order +
    dedup (reusing mars_dtn_sim). Returns (reconstructed, sent)."""
    bundles = [dtn.Bundle(i, (name, kind)) for i, (name, kind, _) in enumerate(commits)]
    delivered = dtn._relay(bundles, random.Random(seed), **conditions)
    recon: Dict[str, str] = {}
    for b in sorted(delivered, key=lambda x: x.seq):
        name, kind = b.payload
        recon[name] = kind
    sent = {name: kind for name, kind, _ in commits}
    return recon, sent


def _pct(s, key="wrong"):
    return 100.0 * s[key] / s["total"]


def main() -> int:
    print("LoS-Codegen: verified code under comms-delay, NO TAKEBACKS  (research wedge #1)\n")
    print(
        "  %d tasks x %d trials. Flaky onboard generator: 50%% correct, 30%% locally-detectable wrong,\n"
        "  20%% overfit wrong (passes the visible examples, fails the hidden oracle). Judge = HIDDEN tests\n"
        "  the generator never saw (independent oracle).\n" % (len(TASKS), TRIALS)
    )
    base = run_sweep(TASKS, verifier=None)
    ex = run_sweep(TASKS, verifier=verify_examples)
    pr = run_sweep(TASKS, verifier=verify_properties)

    print("  %-30s %8s %8s %8s   %s" % ("protocol", "correct", "WRONG", "abstain", "wrong-by-kind"))
    print("  " + "-" * 84)
    for label, s in (
        ("naive (commit first gen)", base),
        ("LoS-safe + example tests", ex),
        ("LoS-safe + property tests", pr),
    ):
        print("  %-30s %8d %8d %8d   %s" % (label, s["correct"], s["wrong"], s["abstain"], dict(s["wrong_by_kind"])))

    print("\n  HEADLINE (the LIFT, judged by the independent oracle; lower wrong = better):")
    print(
        "    wrong code shipped with no takebacks -> naive %.0f%%  |  example-gate %.0f%%  |  property-gate %.0f%%"
        % (_pct(base), _pct(ex), _pct(pr))
    )
    print(
        "    verify-before-commit converts would-be-wrong commits into correct retries or SAFE ABSTAINS\n"
        "    (abstain: naive %d -> example %d -> property %d)." % (base["abstain"], ex["abstain"], pr["abstain"])
    )
    print(
        "  HONEST RESIDUAL: the example gate's leftover wrong is exactly the locally-UNOBSERVABLE overfit\n"
        "    class %s -- a candidate consistent with every local check but wrong on the oracle. That is the\n"
        "    circular-trust hole; closing it needs a STRONGER FACE (property tests here; cross-language exec\n"
        "    / a sound C checker = the next wedge). consistency != correctness; a passed check is evidence."
        % dict(ex["wrong_by_kind"])
    )

    commits = run_trial(TASKS, 0, verifier=verify_properties)
    recon, sent = ship_and_reconstruct(commits, {"reorder": True, "dup_prob": 0.4}, seed=7)
    print(
        "\n  autonomy: committed decisions reconstruct at the far end under delay+reorder+dup: %s"
        % ("CONVERGED" if recon == sent else "DIVERGED")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
