"""offload_measure: measure the auto-offload lift on a LIVE weak model.

The claim under test is narrow and honest: when a step has a deterministic `oracle`, the harness can
SUPPLY the capability the model lacks instead of merely stopping at its ceiling. So the same model on
the same task should go from "some numbers stuck, never wrong" (allow_offload=False) to "nothing
stuck, still never wrong" (allow_offload=True) -- and the rescued answers must be CORRECT, because
the oracle's value is itself checked before it is committed.

This is a measurement, not a demo: it runs the real local model as the proposer (Ollama by default,
qwen2.5-coder:1.5b) over a fixed set of numbers, twice, and reports stuck-vs-rescued plus a
correctness check on every completed answer. Nothing is asserted true that wasn't executed.

    python -m python.helm.offload_measure            # default 1.5b over a 9-number spread
    SCBE_LLM_MODEL=qwen2.5-coder:3b python -m python.helm.offload_measure
"""

from __future__ import annotations

import os
from typing import List

from python.helm.free_generator import _chat
from python.scbe.sieve_calc import classify_number_task
from python.scbe.stepwise import Proposer, run_stepwise

# the numbers the 1.5b reliably trips on: prime-powers (8=2^3, 49=7^2) and the unit (1) are the walls
DEFAULT_NUMBERS = [1, 2, 6, 8, 12, 13, 30, 49, 91]


def model_proposer(base: str, key: str, model: str) -> Proposer:
    """A proposer backed by a live model: hand it the rebuilt context, take back one legal label."""

    def p(ctx: str, options: List[str]) -> str:
        prompt = ctx + "\n\nReply with EXACTLY one of these labels and nothing else: " + ", ".join(options)
        try:
            reply = _chat([{"role": "user", "content": prompt}], base=base, key=key, model=model)
        except Exception as exc:  # a dead endpoint must not masquerade as a model failure
            return "(endpoint-error: %s)" % type(exc).__name__
        reply = (reply or "").strip().splitlines()[0].strip().strip(".'\"` ")
        for opt in options:  # tolerate "the answer is composite" -> composite
            if opt.lower() in reply.lower():
                return opt
        return reply  # let an off-menu answer count as a misstep (it is not in options)

    return p


def _expected_label(n: int) -> str:
    from src import numtheory as nt

    if n == 1:
        return "unit"
    if nt.is_prime(n):
        return "prime"
    return "prime-power" if len(nt.factorization(n)) == 1 else "composite"


def measure(numbers: List[int], proposer: Proposer, max_rewinds: int = 3) -> dict:
    """Run each number twice -- offload off (baseline) then on -- and tally outcomes + correctness."""
    rows = []
    base_stuck = rescued = wrong = 0
    for n in numbers:
        off = run_stepwise(classify_number_task(n), proposer, max_rewinds=max_rewinds, allow_offload=False)
        on = run_stepwise(classify_number_task(n), proposer, max_rewinds=max_rewinds, allow_offload=True)
        exp = _expected_label(n)
        was_stuck = not off["completed"]
        got = on.get("answer")
        offloaded = bool(on.get("offloaded"))
        correct = on["completed"] and got == exp
        base_stuck += was_stuck
        rescued += was_stuck and on["completed"]
        wrong += on["completed"] and not correct
        rows.append(
            {
                "n": n,
                "expected": exp,
                "baseline_stuck": was_stuck,
                "answer": got,
                "offloaded": offloaded,
                "correct": correct,
            }
        )
    return {"rows": rows, "baseline_stuck": base_stuck, "rescued": rescued, "wrong": wrong}


def main(argv: object = None) -> int:
    base = os.environ.get("SCBE_LLM_BASE", "http://localhost:11434/v1")
    key = os.environ.get("SCBE_LLM_KEY", "ollama")
    model = os.environ.get("SCBE_LLM_MODEL", "qwen2.5-coder:1.5b")
    print("OFFLOAD_MEASURE  live model=%s  (baseline=no offload vs. auto-offload)\n" % model)

    res = measure(DEFAULT_NUMBERS, model_proposer(base, key, model))
    print("  %-4s %-12s %-9s %-12s %-9s %s" % ("n", "expected", "stuck?", "answer", "offload?", "correct?"))
    for r in res["rows"]:
        print(
            "  %-4d %-12s %-9s %-12s %-9s %s"
            % (
                r["n"],
                r["expected"],
                "STUCK" if r["baseline_stuck"] else "-",
                r["answer"],
                "tool" if r["offloaded"] else "-",
                "ok" if r["correct"] else "WRONG",
            )
        )
    n = len(res["rows"])
    print("\n  baseline: %d/%d stuck at the model's ceiling (never shipped wrong)" % (res["baseline_stuck"], n))
    print("  auto-offload: %d of those rescued by the oracle, %d shipped wrong" % (res["rescued"], res["wrong"]))
    if res["wrong"]:
        print("  [!] an offloaded answer was WRONG -- the checked-oracle guarantee FAILED, investigate")
    else:
        print("  -> every rescue was correct: the harness supplied the capability, never faked it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
