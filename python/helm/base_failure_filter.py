"""base_failure_filter: keep only the candidate problems the REAL base model fails -> a headroom eval with
teeth against the actual model, not just against hand-written naive code.

THE FINDING THIS FIXES (measured, not theorized). pitfall_eval discriminates naive-vs-reference CODE, but a
real base (qwen2.5-coder:1.5b) already solved 8/9 of it when run through code_lift -- so a training lift
would still drown, the same way it drowned on MBPP. A discriminating eval needs problems where the BASE
MODEL ITSELF fails, not where a hand-written naive solution fails.

This filter runs the base model over a candidate pool and keeps a problem only if BOTH:
  * the REFERENCE solution PASSES it (the problem is solvable + the tests are valid), AND
  * the base model FAILS it on EVERY attempt (a consistent capability gap, not one flaky miss).
The survivors are the set where a trained model actually has room to show a lift. Everything is
execution-verified via public_bench (same oracle code_lift uses) -- no fabricated pass/fail.

    python -m python.helm.base_failure_filter --base qwen2.5-coder:1.5b --source fixture --attempts 2 \
        --out training-data/headroom/base_failures.jsonl
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import public_bench as pb

Generator = Callable[[Dict[str, Any]], str]


def select_base_failures(
    problems: Sequence[Dict[str, Any]],
    base_generator: Generator,
    *,
    ref_generator: Optional[Generator] = None,
    attempts: int = 2,
    public_k: int = 1,
    workspace: Optional[Path] = None,
) -> Dict[str, Any]:
    """Keep problems the reference solves but the base fails every attempt. Returns the kept problems +
    stats. `ref_generator`/`base_generator` are injected so this is testable without a live model."""
    ref_generator = ref_generator or pb.reference_generator
    root = Path(workspace) if workspace else Path(tempfile.mkdtemp(prefix="base-failures-"))
    root.mkdir(parents=True, exist_ok=True)

    kept: List[Dict[str, Any]] = []
    base_solved: List[Any] = []
    ref_failed: List[Any] = []
    skipped_no_hidden = 0

    for p in problems:
        if len(p.get("test_list", [])) <= public_k:
            skipped_no_hidden += 1  # need at least one hidden test to verify a real solve
            continue
        # the problem must be solvable: the reference solution must pass, or the tests are broken
        if not pb.run_problem(p, ref_generator, public_k, root)["verified"]:
            ref_failed.append(p.get("task_id"))
            continue
        # the base must FAIL every attempt (a lucky single pass would mean it's not a real gap)
        failed_all = True
        for _ in range(max(1, attempts)):
            if pb.run_problem(p, base_generator, public_k, root)["verified"]:
                failed_all = False
                break
        if failed_all:
            kept.append(p)
        else:
            base_solved.append(p.get("task_id"))

    return {
        "kept": kept,
        "attempted": len(problems),
        "kept_count": len(kept),
        "base_solved": len(base_solved),
        "ref_failed": len(ref_failed),
        "skipped_no_hidden": skipped_no_hidden,
        "attempts": attempts,
    }


def load_candidates(source: str, limit: int) -> List[Dict[str, Any]]:
    if source == "mbpp":
        return pb.pull_mbpp(limit=limit)
    return pb.load_fixture()  # local, no network -- the default candidate pool


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="filter a candidate pool to problems the real base model fails")
    ap.add_argument("--base", required=True, help="ollama model id for the base (e.g. qwen2.5-coder:1.5b)")
    ap.add_argument("--source", default="fixture", choices=["fixture", "mbpp"], help="candidate pool")
    ap.add_argument("--limit", type=int, default=60, help="how many MBPP problems to pull (--source mbpp)")
    ap.add_argument("--attempts", type=int, default=2, help="base must fail ALL this many attempts to be kept")
    ap.add_argument("--public-k", type=int, default=1)
    ap.add_argument("--out", default=None, help="write the kept (base-failing) problems here as jsonl")
    a = ap.parse_args(argv)

    from .free_generator import make_generator

    candidates = load_candidates(a.source, a.limit)
    print("candidate pool: %d problems (source=%s)" % (len(candidates), a.source))
    rep = select_base_failures(candidates, make_generator(model=a.base), attempts=a.attempts, public_k=a.public_k)
    print(
        "base=%s  attempted=%d  base-FAILED (kept as headroom)=%d  base-solved=%d  ref-broke=%d  no-hidden=%d"
        % (a.base, rep["attempted"], rep["kept_count"], rep["base_solved"], rep["ref_failed"], rep["skipped_no_hidden"])
    )
    rate = rep["kept_count"] / rep["attempted"] if rep["attempted"] else 0.0
    print("  -> %.0f%% of the pool is genuine headroom against this base (ref passes, base fails)" % (rate * 100))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text("\n".join(json.dumps(p) for p in rep["kept"]) + "\n", encoding="utf-8")
        print("  wrote %d base-failing problems -> %s" % (rep["kept_count"], a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
