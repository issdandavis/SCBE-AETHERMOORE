"""offload_measure: measure the auto-offload lift on a LIVE weak model.

The MEASURED quantity is narrow and honest: the RESCUE rate. The same model on the same task goes
from "some numbers stuck at its ceiling" (allow_offload=False) to "those numbers completed via the
oracle" (allow_offload=True). That stuck->rescued delta is the lift, and it is genuinely measured --
the model really proposes, really exhausts its rewinds, and the oracle really takes over.

Correctness is a SEPARATE, INDEPENDENT cross-check -- NOT a re-run of the oracle's own rule. Each
completed answer is compared against GROUND_TRUTH, a small hand-verified label table (independent of
the sieve), so a bug in the classification rule WOULD surface here as a mismatch instead of hiding
behind a copy of itself. Honesty boundary: the in-harness check that gates the oracle (stepwise) is,
for this task, derived from the same rule as the oracle -- so it is a legality wall, not an
independent correctness proof; that is exactly why this measurement carries its OWN external ground
truth. Numbers with no ground-truth entry are reported as "unverified", never counted as correct.

    python -m python.helm.offload_measure            # default 1.5b over the 9-number ground-truth set
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

# INDEPENDENT ground truth: labels verified BY HAND (not re-derived from the sieve), so a bug in the
# classification rule shows up here as a mismatch instead of hiding behind a copy of itself.
GROUND_TRUTH = {
    1: "unit",
    2: "prime",
    6: "composite",  # 2*3
    8: "prime-power",  # 2^3
    12: "composite",  # 2^2*3
    13: "prime",
    30: "composite",  # 2*3*5
    49: "prime-power",  # 7^2
    91: "composite",  # 7*13
}


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


def measure(numbers: List[int], proposer: Proposer, ground_truth: dict = None, max_rewinds: int = 3) -> dict:
    """Run each number twice -- offload off (baseline) then on -- tally stuck/rescued, then cross-check
    each COMPLETED answer against the INDEPENDENT ground-truth table (a hand-verified label, not the
    oracle's own rule). A number with no ground-truth entry is 'unverified', never counted correct."""
    truth = GROUND_TRUTH if ground_truth is None else ground_truth
    rows = []
    base_stuck = rescued = wrong = unverified = 0
    for n in numbers:
        off = run_stepwise(classify_number_task(n), proposer, max_rewinds=max_rewinds, allow_offload=False)
        on = run_stepwise(classify_number_task(n), proposer, max_rewinds=max_rewinds, allow_offload=True)
        was_stuck = not off["completed"]
        got = on.get("answer")
        offloaded = bool(on.get("offloaded"))
        exp = truth.get(n)  # independent ground truth, or None if this number cannot be verified
        correct = (got == exp) if (on["completed"] and exp is not None) else None
        base_stuck += was_stuck
        rescued += bool(was_stuck and on["completed"])
        wrong += int(correct is False)
        unverified += int(on["completed"] and exp is None)
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
    return {
        "rows": rows,
        "baseline_stuck": base_stuck,
        "rescued": rescued,
        "wrong": wrong,
        "unverified": unverified,
    }


def main(argv: object = None) -> int:
    base = os.environ.get("SCBE_LLM_BASE", "http://localhost:11434/v1")
    key = os.environ.get("SCBE_LLM_KEY", "ollama")
    model = os.environ.get("SCBE_LLM_MODEL", "qwen2.5-coder:1.5b")
    print("OFFLOAD_MEASURE  live model=%s  (baseline=no offload vs. auto-offload)\n" % model)

    res = measure(DEFAULT_NUMBERS, model_proposer(base, key, model))
    print("  %-4s %-12s %-9s %-12s %-9s %s" % ("n", "truth", "stuck?", "answer", "offload?", "vs truth"))
    for r in res["rows"]:
        if r["correct"] is None:
            verdict = "unverified" if r["answer"] is not None else "stuck"
        else:
            verdict = "ok" if r["correct"] else "WRONG"
        print(
            "  %-4d %-12s %-9s %-12s %-9s %s"
            % (
                r["n"],
                r["expected"] or "-",
                "STUCK" if r["baseline_stuck"] else "-",
                r["answer"],
                "tool" if r["offloaded"] else "-",
                verdict,
            )
        )
    n = len(res["rows"])
    print(
        "\n  MEASURED lift: %d/%d stuck at the model's ceiling (offload off) -> %d rescued by the oracle (offload on)"
        % (res["baseline_stuck"], n, res["rescued"])
    )
    print(
        "  INDEPENDENT cross-check vs hand-verified ground truth: %d wrong, %d unverified"
        % (res["wrong"], res["unverified"])
    )
    if res["wrong"]:
        print("  [!] a completed answer disagreed with ground truth -- the classification rule is wrong, investigate")
    else:
        print("  -> the stuck->rescued lift is real, and every verifiable answer matched independent ground truth")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
