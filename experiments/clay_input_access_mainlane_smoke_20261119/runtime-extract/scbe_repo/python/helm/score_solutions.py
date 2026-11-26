"""Score a model's pre-generated solutions on the public benchmark.

``public_bench.py`` runs the forge loop with a ``generator(problem) -> source``. The
honest way to plug a REAL model into that slot -- Claude sub-agents, a local model, an
HF endpoint, anything -- is to generate solutions out-of-band, save them as JSON, and
score them here against the held-out HIDDEN tests. This is the "plug a real model into
the slot" piece ``public_bench`` named: the generation happens wherever the model lives,
the verification stays in the sandboxed public/hidden harness.

    # 1. generate with any model -> solutions.json  ({task_id: code} or [{task_id, code}, ...])
    # 2. score on the hidden tests:
    python -m python.helm.score_solutions --problems probs.json --solutions solutions.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from .public_bench import Generator, naive_generator, pull_mbpp, render, run_public_bench


def _load_table(path: str) -> Dict[int, str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {int(d["task_id"]): d["code"] for d in data}
    return {int(k): v for k, v in data.items()}


def solutions_generator(path: str) -> Generator:
    """A generator backed by a file of pre-generated solutions (any model).

    Missing task_ids fall back to the naive stub (the failing floor), so an absent
    solution scores as a fail rather than a silent pass.
    """
    table = _load_table(path)

    def gen(problem: Dict[str, Any]) -> str:
        tid = problem.get("task_id")
        code = table.get(int(tid)) if tid is not None else None
        return code if code else naive_generator(problem)

    gen.__name__ = "solutions(%s)" % Path(path).name
    return gen


def score(problems: Sequence[Dict[str, Any]], solutions_path: str, public_k: int = 1) -> Dict[str, Any]:
    """Score pre-generated solutions against the public/hidden split."""
    return run_public_bench(problems, generator=solutions_generator(solutions_path), public_k=public_k)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scbe-score-solutions", description="score a model's pre-generated solutions on MBPP hidden tests"
    )
    ap.add_argument("--solutions", required=True, help="JSON: {task_id: code} or [{task_id, code}, ...]")
    ap.add_argument("--problems", default="", help="JSON list of problems; if omitted, pulls MBPP")
    ap.add_argument("--limit", type=int, default=20, help="problems to pull when --problems is omitted")
    ap.add_argument("--public-k", type=int, default=1, help="how many asserts are public (rest are hidden)")
    a = ap.parse_args(list(argv) if argv is not None else None)
    if a.problems:
        problems = json.loads(Path(a.problems).read_text(encoding="utf-8"))
    else:
        try:
            problems = pull_mbpp(limit=a.limit or None)
        except Exception as e:  # network down -- be honest, do not fake
            print("could not pull MBPP (%s: %s); pass --problems FILE instead" % (type(e).__name__, e))
            return 1
    print(render(score(problems, a.solutions, public_k=a.public_k)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
