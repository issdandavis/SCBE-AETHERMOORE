"""restructure_measure: measure the FORCED-DEVIATION (stuck-prior) lift on a LIVE weak model.

This isolates the restructure rung from the tool rung. Both arms run with the oracle OFF
(allow_offload=False), so ANY completion under pruning is a pure RESTRUCTURE rescue -- the harness
eliminated the proven-wrong option the model kept looping on and forced it into a new region, with no
deterministic tool supplying the answer. That distinguishes this lift from offload_measure's tool lift.

  * baseline arm  -- prune_wrong=False: the model is free to re-propose its wrong prior; it loops
    (stuck_priors > 0) and stalls (the +0 self-repair wall, live).
  * restructure arm -- prune_wrong=True: each proven-wrong value is pruned from the menu, so the model
    cannot fall back into the rut. Completions here are the model making a fresh choice in a narrowed
    legal set -- not the model getting smarter.

Correctness is cross-checked against the INDEPENDENT hand-verified GROUND_TRUTH table (reused from
offload_measure -- NOT re-derived from the sieve), and each rescue is labelled `forced` (pruned down
to a single legal option -- the harness solved it by elimination) vs `choice` (>1 option remained, so
the model genuinely picked the right one). No overclaim: the honest measured quantity is the
stuck->rescued delta and how much of it was real model choice vs pure elimination.

    python -m python.helm.restructure_measure
    SCBE_LLM_MODEL=qwen2.5-coder:3b python -m python.helm.restructure_measure
"""

from __future__ import annotations

import os
from typing import List, Optional

from python.helm.offload_measure import GROUND_TRUTH, model_proposer
from python.scbe.sieve_calc import classify_number_task
from python.scbe.stepwise import Proposer, run_stepwise

DEFAULT_NUMBERS = [1, 2, 6, 8, 12, 13, 30, 49, 91]


def _label_remaining(result: dict) -> Optional[int]:
    """How many options were still on the menu when the label step was committed by the MODEL."""
    for t in result["trace"]:
        if t["step"] == "label" and t["status"] == "ok" and t["source"] == "model":
            return t.get("remaining")
    return None


def measure_restructure(
    numbers: List[int], proposer: Proposer, ground_truth: dict = None, max_rewinds: int = 3
) -> dict:
    """Run each number twice with the tool OFF: prune off (baseline loop) vs prune on (forced deviation)."""
    truth = GROUND_TRUTH if ground_truth is None else ground_truth
    rows = []
    base_stuck = base_loops = rescued = wrong = forced = choice = 0
    for n in numbers:
        base = run_stepwise(classify_number_task(n), proposer, max_rewinds, allow_offload=False, prune_wrong=False)
        res = run_stepwise(classify_number_task(n), proposer, max_rewinds, allow_offload=False, prune_wrong=True)
        was_stuck = not base["completed"]
        got = res.get("answer")
        exp = truth.get(n)
        completed = res["completed"]
        remaining = _label_remaining(res)
        is_rescue = bool(was_stuck and completed)
        correct = (got == exp) if (completed and exp is not None) else None
        base_stuck += was_stuck
        base_loops += base["stuck_priors"]
        rescued += is_rescue
        wrong += int(correct is False)
        if is_rescue and remaining is not None:
            if remaining <= 1:
                forced += 1
            else:
                choice += 1
        rows.append(
            {
                "n": n,
                "expected": exp,
                "baseline_stuck": was_stuck,
                "baseline_loops": base["stuck_priors"],
                "answer": got,
                "completed": completed,
                "remaining": remaining,
                "correct": correct,
            }
        )
    return {
        "rows": rows,
        "baseline_stuck": base_stuck,
        "baseline_loops": base_loops,
        "rescued": rescued,
        "forced": forced,
        "choice": choice,
        "wrong": wrong,
    }


def main(argv: object = None) -> int:
    base = os.environ.get("SCBE_LLM_BASE", "http://localhost:11434/v1")
    key = os.environ.get("SCBE_LLM_KEY", "ollama")
    model = os.environ.get("SCBE_LLM_MODEL", "qwen2.5-coder:1.5b")
    print("RESTRUCTURE_MEASURE  live model=%s  (tool OFF both arms; prune off=loop vs on=forced deviation)\n" % model)

    res = measure_restructure(DEFAULT_NUMBERS, model_proposer(base, key, model))
    print(
        "  %-4s %-12s %-9s %-8s %-12s %-10s %s"
        % ("n", "truth", "loops(off)", "stuck?", "answer(on)", "remaining", "vs truth")
    )
    for r in res["rows"]:
        if r["correct"] is None:
            verdict = "unverified" if r["completed"] else "stuck"
        else:
            verdict = "ok" if r["correct"] else "WRONG"
        rem = "-" if r["remaining"] is None else str(r["remaining"])
        print(
            "  %-4d %-12s %-9d %-8s %-12s %-10s %s"
            % (
                r["n"],
                r["expected"] or "-",
                r["baseline_loops"],
                "STUCK" if r["baseline_stuck"] else "-",
                r["answer"],
                rem,
                verdict,
            )
        )
    n = len(res["rows"])
    print(
        "\n  BASELINE (prune off): %d/%d stuck, %d total re-proposals of a known-wrong value (the System-1 rut)"
        % (res["baseline_stuck"], n, res["baseline_loops"])
    )
    print(
        "  RESTRUCTURE (prune on, NO tool): %d of the %d stuck rescued by forced deviation"
        % (res["rescued"], res["baseline_stuck"])
    )
    print(
        "    of those rescues: %d a genuine model choice (>1 option left), %d elimination-to-one (harness-forced)"
        % (res["choice"], res["forced"])
    )
    print("  INDEPENDENT correctness vs hand-verified ground truth: %d wrong" % res["wrong"])
    if res["wrong"]:
        print("  [!] a completed answer disagreed with ground truth -- investigate")
    elif res["rescued"]:
        print("  -> forced deviation lifted results with NO tool: pruning the rut moved the model off its stuck prior")
    else:
        print(
            "  -> restructure alone did NOT rescue this model (it ignores the narrowed menu) -- the tool rung is needed"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
