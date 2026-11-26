"""offload_measure: measure deterministic helper rescue on a LIVE weak model.

The measured quantity is narrow: the TOOL-RESCUE completion rate. The same model on the same task goes
from "some numbers stuck at its ceiling" (allow_offload=False) to "those numbers completed via the
deterministic task helper" (allow_offload=True). That stuck->rescued delta is genuinely measured --
the model really proposes, really exhausts its rewinds, and the helper really takes over. It is not a
model-capability lift claim; it is an environment/tool-rescue measurement.

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

from python.helm.free_generator import LLMConfig, chat_with_config, resolve_llm_config
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
    """A proposer backed by a live model: hand it the rebuilt context, take back one legal label.

    Mapping is exact-match-first, then substring with options sorted LONGEST-first -- so a correct
    'prime-power' reply is NOT swallowed by the shorter 'prime' (a real bug a review caught: 'prime'
    is a substring of 'prime-power', so naive first-match mislabelled every correct prime-power answer
    as 'prime' and fabricated fake rescues). A transport failure is raised, never returned: a dead
    endpoint must fail loud, not masquerade as a model ceiling that the helper then 'rescues'.
    """

    config = LLMConfig(base=base, key=key, model=model)

    def p(ctx: str, options: List[str]) -> str:
        prompt = ctx + "\n\nReply with EXACTLY one of these labels and nothing else: " + ", ".join(options)
        try:
            reply = chat_with_config([{"role": "user", "content": prompt}], config)
        except Exception as exc:  # infra failure, NOT a model failure -> fail loud (never count as a lift)
            raise ConnectionError("LLM endpoint error: %s: %s" % (type(exc).__name__, exc)) from exc
        text = ((reply or "").strip().splitlines() or [""])[0].strip().strip(".'\"` ")
        low = text.lower()
        for opt in options:  # an exact label wins outright
            if low == opt.lower():
                return opt
        for opt in sorted(options, key=len, reverse=True):  # longest-first: 'prime-power' beats 'prime'
            if opt.lower() in low:
                return opt
        return text  # genuinely off-menu -> a legitimate misstep (not in options)

    return p


def measure(numbers: List[int], proposer: Proposer, ground_truth: dict = None, max_rewinds: int = 3) -> dict:
    """Run each number twice -- offload off (baseline) then on -- tally stuck/rescued, then cross-check
    each COMPLETED answer against the INDEPENDENT ground-truth table (a hand-verified label, not the
    oracle's own rule). A number with no ground-truth entry is 'unverified', never counted correct."""
    truth = GROUND_TRUTH if ground_truth is None else ground_truth
    rows = []
    base_stuck = rescued = wrong = unverified = 0
    for n in numbers:
        # prune_wrong=False on BOTH arms: offload (the tool) is the only variable under test, so the
        # restructure rung must stay off or it would complete steps and steal credit from the oracle.
        off = run_stepwise(classify_number_task(n), proposer, max_rewinds, allow_offload=False, prune_wrong=False)
        on = run_stepwise(classify_number_task(n), proposer, max_rewinds, allow_offload=True, prune_wrong=False)
        was_stuck = not off["completed"]
        got = on.get("answer")
        offloaded = bool(on.get("offloaded"))
        exp = truth.get(n)  # independent ground truth, or None if this number cannot be verified
        correct = (got == exp) if (on["completed"] and exp is not None) else None
        base_stuck += was_stuck
        rescued += int(was_stuck and on["completed"] and offloaded)  # a rescue means the TOOL actually fired
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
    config = resolve_llm_config(
        base=os.environ.get("SCBE_LLM_BASE", "http://localhost:11434/v1"),
        key=os.environ.get("SCBE_LLM_KEY", "ollama"),
        model=os.environ.get("SCBE_LLM_MODEL", "qwen2.5-coder:1.5b"),
    )
    print("OFFLOAD_MEASURE  live model=%s  (baseline=no offload vs. deterministic helper)\n" % config.model)

    try:
        res = measure(DEFAULT_NUMBERS, model_proposer(config.base, config.key, config.model))
    except ConnectionError as exc:  # a dead endpoint must never read as a clean lift
        print("  [endpoint down] %s\n  -> NO measurement produced (a transport failure is not a result)" % exc)
        return 2
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
        "\n  TOOL-RESCUE completion: %d/%d stuck at the model's ceiling (offload off) -> %d rescued by the helper (offload on)"
        % (res["baseline_stuck"], n, res["rescued"])
    )
    print(
        "  INDEPENDENT cross-check vs hand-verified ground truth: %d wrong, %d unverified"
        % (res["wrong"], res["unverified"])
    )
    if res["wrong"]:
        print("  [!] a completed answer disagreed with ground truth -- the classification rule is wrong, investigate")
    else:
        print("  -> the stuck->rescued tool-rescue count is measured; every verifiable answer matched ground truth")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
