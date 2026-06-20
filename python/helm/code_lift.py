"""code_lift: the base-vs-trained CODE-capability lift measurement (the VTC thesis number).

reasoning_ladder.measure_lift compares raw-vs-harnessed on Q&A by exact-match. THIS compares
base-vs-finetuned on CODE by EXECUTION: every candidate runs through public_bench._verify -- the same
sandboxed public+hidden split that minted the corpus -- so a "solve" means the HIDDEN tests actually
passed, not that the answer looked right. The headline number is `newly_solved`: held-out problems the
TRAINED model solves that the BASE could not. `regressed` (base solved, trained broke) is reported too,
so net lift is always visible and the harness can never manufacture a lift that is not there.

Honest by construction:
  * grades by RUNNING hidden tests, never by string match;
  * fields are base/trained (NOT baseline/tooled) -- this is finetune lift, not the raw-vs-harnessed
    harness lift reasoning_ladder measures; mislabeling would misread the result;
  * a dead endpoint / failed generation emits failing code -> scores 0, never a fabricated pass.

A generator is any Callable[[problem], code_str]: public_bench.reference_generator (the answer key -- a
HARNESS check, NOT a model result), free_generator.make_generator (a live $0 OpenAI/Ollama endpoint),
or an in-process Colab checkpoint. The base-vs-trained comparison MUST use the identical generator
wrapper/prompt for both sides (e.g. LoRA-disabled vs LoRA-enabled on the same base) so the delta is the
adapter, not prompt drift.

    python -m python.helm.code_lift --demo      # answer-key vs stub over the offline fixture (math check)
"""

from __future__ import annotations

import argparse
from typing import Any, Callable, Dict, Optional, Sequence

from . import public_bench as pb

Generator = Callable[[Dict[str, Any]], str]


def solve_rate(problems: Sequence[Dict[str, Any]], generator: Generator, public_k: int = 1) -> Dict[str, Any]:
    """Run `generator` over each problem and execution-verify with public_bench._verify. A problem
    counts as solved only when its PUBLIC and HIDDEN asserts both pass. Problems with <= public_k tests
    are skipped (an empty hidden set would make 'solved' trivially true)."""
    solved_ids = set()
    attempted = 0
    for p in problems:
        asserts = list(p.get("test_list", []))
        if len(asserts) <= public_k:
            continue
        attempted += 1
        public, hidden = asserts[:public_k], asserts[public_k:]
        try:
            src = generator(p)
        except Exception:  # a generator that throws scores 0 -- never a fabricated pass
            src = ""
        v = pb._verify(src, public, hidden, p.get("test_imports", []))
        if v["public_passed"] and v["hidden_passed"]:
            solved_ids.add(p.get("task_id"))
    return {"solved": len(solved_ids), "total": attempted, "solved_ids": solved_ids}


def lift_from_solve(base_solve: Dict[str, Any], trained_solve: Dict[str, Any]) -> Dict[str, Any]:
    """Build the lift report from two precomputed solve_rate() results. For callers that cannot run two
    independent generators -- e.g. a single Colab checkpoint toggled LoRA-OFF (base) vs LoRA-ON (trained)
    over the same eval set, the cleanest base-vs-trained comparison because only the adapter differs."""
    newly = trained_solve["solved_ids"] - base_solve["solved_ids"]
    regressed = base_solve["solved_ids"] - trained_solve["solved_ids"]
    return {
        "base_solved": base_solve["solved"],
        "trained_solved": trained_solve["solved"],
        "total": base_solve["total"],
        "newly_solved": newly,
        "regressed": regressed,
        "net_lift": len(newly) - len(regressed),
        "base_solved_ids": base_solve["solved_ids"],
        "trained_solved_ids": trained_solve["solved_ids"],
    }


def measure_code_lift(
    base: Generator, trained: Generator, eval_problems: Sequence[Dict[str, Any]], public_k: int = 1
) -> Dict[str, Any]:
    """Run BOTH generators over the SAME held-out problems and return the execution-verified delta.
    newly_solved = the thesis number (trained solves, base failed); regressed = the reverse."""
    return lift_from_solve(
        solve_rate(eval_problems, base, public_k), solve_rate(eval_problems, trained, public_k)
    )


def render(rep: Dict[str, Any]) -> str:
    return "\n".join(
        [
            "VTC CODE LIFT  (base vs trained, execution-verified on held-out MBPP)",
            "  base solved   : %d / %d" % (rep["base_solved"], rep["total"]),
            "  trained solved: %d / %d" % (rep["trained_solved"], rep["total"]),
            "  newly solved  : %d  %s   <- trained passes, base could not (the lift)"
            % (len(rep["newly_solved"]), sorted(rep["newly_solved"])),
            "  regressed     : %d  %s   <- base passed, trained broke"
            % (len(rep["regressed"]), sorted(rep["regressed"])),
            "  NET LIFT      : %+d" % rep["net_lift"],
        ]
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scbe-code-lift", description="base-vs-trained code capability lift on held-out MBPP"
    )
    ap.add_argument(
        "--demo",
        action="store_true",
        help="HARNESS CHECK ONLY: stub(base) vs answer-key(trained) over the offline fixture -- proves the math",
    )
    a = ap.parse_args(list(argv) if argv is not None else None)
    if a.demo:
        probs = pb.load_fixture()
        rep = measure_code_lift(pb.naive_generator, pb.reference_generator, probs)
        print("[DEMO = harness check, NOT a model result: 'base' is a failing stub, 'trained' is the answer key]")
        print(render(rep))
        return 0
    print("code_lift is a library; the real run lives in notebooks/vtc_lift_qwen15_colab.ipynb")
    print("  (base = the stock checkpoint, trained = QLoRA-adapted, both over the held-out eval set).")
    print("  CLI smoke: --demo runs the answer-key-vs-stub harness check over the offline fixture.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
