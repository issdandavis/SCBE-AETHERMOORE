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


Ask = Callable[[str], str]


def solve_rate_with_repair(
    problems: Sequence[Dict[str, Any]], ask: Ask, public_k: int = 1, rounds: int = 3
) -> Dict[str, Any]:
    """Like solve_rate, but the model runs the write->run->repair LOOP (solve_with_trace) instead of one
    shot. Beyond solved/total it records `recovered` = problems solved ONLY after a failed attempt -- the
    behavior VTC trains on. recovery_rate = recovered / solved. `ask` is prompt->str (the loop re-prompts
    with execution feedback), distinct from solve_rate's problem->code Generator."""
    from .verified_trajectory import solve_with_trace

    solved_ids = set()
    recovered = 0
    attempted = 0
    for p in problems:
        asserts = list(p.get("test_list", []))
        if len(asserts) <= public_k:
            continue
        attempted += 1
        tr = solve_with_trace(p, ask, public_k=public_k, rounds=rounds)  # verifies on held-out hidden
        if tr["verified"]:
            solved_ids.add(p.get("task_id"))
            if tr["attempts"] > 1:  # needed a repair -> the model RECOVERED
                recovered += 1
    solved = len(solved_ids)
    return {
        "solved": solved,
        "total": attempted,
        "solved_ids": solved_ids,
        "recovered": recovered,
        "recovery_rate": round(recovered / solved, 3) if solved else 0.0,
    }


def recovery_lift(base_solve: Dict[str, Any], trained_solve: Dict[str, Any]) -> Dict[str, Any]:
    """The VTC thesis number for the REPAIR loop: does training raise the rate at which the model solves
    only AFTER failing once? Built from two solve_rate_with_repair() results. recovery_lift > 0 is the
    specific, falsifiable claim VTC makes; net solve lift (lift_from_solve) is the raw-capability number."""
    base_solve, trained_solve = dict(base_solve), dict(trained_solve)
    report = lift_from_solve(base_solve, trained_solve)
    report["base_recovery_rate"] = base_solve.get("recovery_rate", 0.0)
    report["trained_recovery_rate"] = trained_solve.get("recovery_rate", 0.0)
    report["recovery_lift"] = round(report["trained_recovery_rate"] - report["base_recovery_rate"], 3)
    report["base_recovered"] = base_solve.get("recovered", 0)
    report["trained_recovered"] = trained_solve.get("recovered", 0)
    return report


def measure_recovery_lift(
    base: Ask, trained: Ask, eval_problems: Sequence[Dict[str, Any]], public_k: int = 1, rounds: int = 3
) -> Dict[str, Any]:
    """Run BOTH models through the repair loop on the SAME held-out problems; return solve lift + the
    recovery lift (the repair-behavior delta). `base`/`trained` are prompt->str (e.g. LoRA-off vs -on)."""
    return recovery_lift(
        solve_rate_with_repair(eval_problems, base, public_k, rounds),
        solve_rate_with_repair(eval_problems, trained, public_k, rounds),
    )


def measure_code_lift(
    base: Generator, trained: Generator, eval_problems: Sequence[Dict[str, Any]], public_k: int = 1
) -> Dict[str, Any]:
    """Run BOTH generators over the SAME held-out problems and return the execution-verified delta.
    newly_solved = the thesis number (trained solves, base failed); regressed = the reverse."""
    return lift_from_solve(solve_rate(eval_problems, base, public_k), solve_rate(eval_problems, trained, public_k))


def render(rep: Dict[str, Any]) -> str:
    lines = [
        "VTC CODE LIFT  (base vs trained, execution-verified on held-out MBPP)",
        "  base solved   : %d / %d" % (rep["base_solved"], rep["total"]),
        "  trained solved: %d / %d" % (rep["trained_solved"], rep["total"]),
        "  newly solved  : %d  %s   <- trained passes, base could not (the lift)"
        % (len(rep["newly_solved"]), sorted(rep["newly_solved"])),
        "  regressed     : %d  %s   <- base passed, trained broke" % (len(rep["regressed"]), sorted(rep["regressed"])),
        "  NET LIFT      : %+d" % rep["net_lift"],
    ]
    if "recovery_lift" in rep:  # repair-loop run -> show the recovery (solve-after-failure) delta too
        lines += [
            "  recovery rate : base %.3f -> trained %.3f  (solved only after a failed attempt)"
            % (rep["base_recovery_rate"], rep["trained_recovery_rate"]),
            "  RECOVERY LIFT : %+.3f   <- the VTC thesis: learned to recover from failure?" % rep["recovery_lift"],
        ]
    return "\n".join(lines)


def _ollama_ask(model: str):
    """An ask(prompt)->str over Ollama's OpenAI-compatible endpoint, for the recovery (repair-loop) run."""
    import os

    from .free_generator import DEFAULT_BASE, _chat, strip_to_code

    base = os.environ.get("SCBE_LLM_BASE", DEFAULT_BASE)
    key = os.environ.get("SCBE_LLM_KEY", "ollama")

    def ask(prompt: str) -> str:
        try:
            return strip_to_code(_chat([{"role": "user", "content": prompt}], base=base, key=key, model=model))
        except Exception as exc:  # fail closed: emit failing code, never a fabricated pass
            return "# generation failed (%s)\ndef _f(*a, **k):\n    return None\n" % type(exc).__name__

    return ask


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scbe-code-lift", description="base-vs-trained code capability lift on held-out MBPP"
    )
    ap.add_argument(
        "--demo",
        action="store_true",
        help="HARNESS CHECK ONLY: stub(base) vs answer-key(trained) over the offline fixture -- proves the math",
    )
    ap.add_argument("--base", default=None, help="ollama model id for the BASE slot (e.g. qwen2.5-coder:1.5b)")
    ap.add_argument("--trained", default=None, help="ollama model id for the TRAINED slot (e.g. vtc-qwen15)")
    ap.add_argument("--corpus", default=None, help="training corpus jsonl; its task_ids are excluded from eval")
    ap.add_argument("--limit", type=int, default=300, help="pull this many MBPP problems before excluding train ids")
    ap.add_argument("--recovery", action="store_true", help="also run the repair-loop recovery measurement")
    ap.add_argument("--rounds", type=int, default=3, help="repair rounds per problem (with --recovery)")
    a = ap.parse_args(list(argv) if argv is not None else None)

    if a.demo:
        probs = pb.load_fixture()
        rep = measure_code_lift(pb.naive_generator, pb.reference_generator, probs)
        print("[DEMO = harness check, NOT a model result: 'base' is a failing stub, 'trained' is the answer key]")
        print(render(rep))
        return 0

    if a.base and a.trained:  # local base-vs-trained over ollama (e.g. stock vs the imported QLoRA model)
        from .free_generator import make_generator
        from .vtc_split import load_corpus, split_by_task_id

        records = load_corpus(a.corpus)
        eval_problems = split_by_task_id(records, pb.pull_mbpp(limit=a.limit))["eval_problems"]
        print("held-out: %d problems (excluded %d trained task_ids)" % (len(eval_problems), len(records)))
        rep = measure_code_lift(make_generator(model=a.base), make_generator(model=a.trained), eval_problems)
        print(render(rep))
        if a.recovery:
            rec = measure_recovery_lift(_ollama_ask(a.base), _ollama_ask(a.trained), eval_problems, rounds=a.rounds)
            print(render(rec))
        return 0

    print("code_lift: run a real comparison with")
    print("  --base <ollama_model> --trained <ollama_model> [--corpus <jsonl>] [--recovery]")
    print("  or --demo for the offline answer-key-vs-stub harness check.")
    print("  The Colab run lives in notebooks/vtc_lift_qwen15_colab.ipynb.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
