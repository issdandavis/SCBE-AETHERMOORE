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

The honest measured quantity is the stuck->rescued delta. Each rescue is described by how many legal
options remained when it committed -- `single` (pruned to one option: the harness solved it by
elimination) vs `multi` (>1 option still on the menu). `multi` is necessary but NOT sufficient for
"genuine model judgement" (a model that just grabs the first remaining option also shows >1), so it is
reported descriptively, never claimed as proof of reasoning. A real model that re-proposes the SAME
pruned value is NOT rescued (it accrues stuck_priors and stays stuck) -- so a nonzero restructure lift
here means the live model actually deviates when its rut is pruned, which is the thing under test.
Correctness is a consistency check vs the hand-verified GROUND_TRUTH table; since only check-passing
values commit, it guards the rule/table, not model error (see the note in measure_restructure).

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
    """Run each number twice with the tool OFF: prune off (baseline loop) vs prune on (forced deviation).

    The two arms are deterministic (the live proposer runs at temperature 0), so a number stuck in the
    baseline arm that completes in the restructure arm is a real effect of pruning, not sampling luck --
    the arms are paired in practice. `base_looped` counts NUMBERS where the model re-proposed a known-
    wrong value at least once (a knob-independent trait), not total repeats (which just track the rewind
    budget). `multi` vs `single` is whether >1 legal option remained when it committed -- descriptive
    only: >1 is necessary but not sufficient for "genuine judgement", so it is reported, not claimed.
    """
    truth = GROUND_TRUTH if ground_truth is None else ground_truth
    rows = []
    base_stuck = base_looped = rescued = wrong = single = multi = 0
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
        base_looped += int(base["stuck_priors"] > 0)
        rescued += is_rescue
        wrong += int(correct is False)
        if is_rescue and remaining is not None:
            if remaining <= 1:
                single += 1
            else:
                multi += 1
        rows.append(
            {
                "n": n,
                "expected": exp,
                "baseline_stuck": was_stuck,
                "baseline_looped": base["stuck_priors"] > 0,
                "answer": got,
                "completed": completed,
                "remaining": remaining,
                "correct": correct,
            }
        )
    return {
        "rows": rows,
        "baseline_stuck": base_stuck,
        "base_looped": base_looped,
        "rescued": rescued,
        "single": single,
        "multi": multi,
        "wrong": wrong,
    }


def main(argv: object = None) -> int:
    base = os.environ.get("SCBE_LLM_BASE", "http://localhost:11434/v1")
    key = os.environ.get("SCBE_LLM_KEY", "ollama")
    model = os.environ.get("SCBE_LLM_MODEL", "qwen2.5-coder:1.5b")
    print("RESTRUCTURE_MEASURE  live model=%s  (tool OFF both arms; prune off=loop vs on=forced deviation)\n" % model)

    try:
        res = measure_restructure(DEFAULT_NUMBERS, model_proposer(base, key, model))
    except ConnectionError as exc:  # a dead endpoint must never read as a clean lift
        print("  [endpoint down] %s\n  -> NO measurement produced (a transport failure is not a result)" % exc)
        return 2
    print(
        "  %-4s %-12s %-9s %-8s %-12s %-10s %s"
        % ("n", "truth", "looped?", "stuck?", "answer(on)", "remaining", "vs truth")
    )
    for r in res["rows"]:
        if r["correct"] is None:
            verdict = "unverified" if r["completed"] else "stuck"
        else:
            verdict = "ok" if r["correct"] else "WRONG"
        rem = "-" if r["remaining"] is None else str(r["remaining"])
        print(
            "  %-4d %-12s %-9s %-8s %-12s %-10s %s"
            % (
                r["n"],
                r["expected"] or "-",
                "loop" if r["baseline_looped"] else "-",
                "STUCK" if r["baseline_stuck"] else "-",
                r["answer"],
                rem,
                verdict,
            )
        )
    n = len(res["rows"])
    print(
        "\n  BASELINE (prune off): %d/%d stuck; %d/%d numbers where the model re-proposed a known-wrong value"
        % (res["baseline_stuck"], n, res["base_looped"], n)
    )
    print(
        "  RESTRUCTURE (prune on, NO tool): %d of the %d stuck rescued by forced deviation"
        % (res["rescued"], res["baseline_stuck"])
    )
    print(
        "    when committed: %d with >1 legal option left, %d down to a single option (elimination)"
        % (res["multi"], res["single"])
    )
    # the cross-check guards the sieve/ground-truth rule, not model error: only check-passing values
    # ever commit, so a completed answer ALWAYS matches the rule -- 'wrong' fires only if GROUND_TRUTH
    # disagrees with the sieve (it does not, by construction). So 0 wrong is a consistency check, not proof.
    print(
        "  CONSISTENCY vs hand-verified ground truth: %d disagreements (guards the rule, not the model)" % res["wrong"]
    )
    if res["wrong"]:
        print("  [!] a completed answer disagreed with ground truth -- the rule/table drifted, investigate")
    elif res["rescued"]:
        print(
            "  -> forced deviation lifted results with NO tool on %d numbers (pruning moved the model off its rut)"
            % res["rescued"]
        )
    else:
        print(
            "  -> restructure alone did NOT rescue this model (it re-proposes the pruned value) -- tool rung needed"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
