"""strength_router_tasks: the live block-offload demonstration for strength_router.

The cleanest, most attributable routing lift is the user's "fill the steps with pre-reasoned blocks"
case: a task where the small model's MEASURED weakness (modulo on multi-digit numbers -- the fizzbuzz
failure we logged) is offloaded to a deterministic CALC block, leaving the model only the judgement it
is good at (pick the label given the remainders).

Two paths over the SAME numbers, truth = the deterministic correct label (computed independently):
  * ROUTED (block-offload): a stepwise Task -- calc r3=i%3, calc r5=i%5 (BLOCKS, run in code), then a
    choice step where the small model picks the FizzBuzz label given r3, r5. The model never does the
    arithmetic it botches; it only judges.
  * BASELINE (single-shot): the same small model is asked the RAW question (do the modulo AND label in
    one shot, in its head) -- the honest weak floor.

Both face the identical number set, so any distribution skew cancels; the delta is the value of routing
the computation to a verified block. Run: python -m python.helm.strength_router --gpu --n 30
"""

from __future__ import annotations

import os
from typing import Dict, List

from python.scbe.stepwise import Step, Task, run_stepwise
from python.helm.strength_router import render

LABELS = ["FizzBuzz", "Fizz", "Buzz", "none"]


def correct_label(i: int) -> str:
    """The independent ground truth for number i under the FizzBuzz rule."""
    f, b = (i % 3 == 0), (i % 5 == 0)
    return "FizzBuzz" if (f and b) else "Fizz" if f else "Buzz" if b else "none"


def _label_from_state(state: Dict) -> str:
    f, b = (state["r3"] == 0), (state["r5"] == 0)
    return "FizzBuzz" if (f and b) else "Fizz" if f else "Buzz" if b else "none"


def number_task(i: int) -> Task:
    """Decomposed task: BLOCKS compute the remainders (the arithmetic the model botches); the model
    only picks the label. r3/r5 are calc steps -> run by code, never the model."""
    return Task(
        name="fb_%d" % i,
        goal="classify %d by the FizzBuzz rule using the computed remainders r3, r5" % i,
        steps=[
            Step(name="r3", key="r3", calc=(lambda st, i=i: i % 3)),
            Step(name="r5", key="r5", calc=(lambda st, i=i: i % 5)),
            Step(
                name="label",
                key="label",
                options=(lambda st: list(LABELS)),
                check=(lambda st, v: v == _label_from_state(st)),
            ),
        ],
    )


def _match_label(text: str) -> str:
    """Parse a model reply to one of the four labels, reading the LAST non-empty line first (the model's
    actual answer) before falling back to the whole text. This avoids being fooled by an echoed rule/option
    list ('...Fizz, Buzz, none') earlier in the reply. Within the chosen scope, both fizz and buzz present
    -> FizzBuzz."""
    t = (text or "").strip().lower()
    lines = [ln for ln in t.splitlines() if ln.strip()]
    tail = lines[-1] if lines else t
    for scope in (tail, t):  # prefer the model's last line; fall back to the whole reply
        if "fizzbuzz" in scope.replace(" ", "").replace("-", ""):
            return "FizzBuzz"
        hf, hb = ("fizz" in scope), ("buzz" in scope)
        if hf and hb:
            return "FizzBuzz"
        if hf:
            return "Fizz"
        if hb:
            return "Buzz"
        if "none" in scope:
            return "none"
    return "none"


def _chat_once(prompt: str, model: str) -> str:
    from python.helm.free_generator import _chat

    base = os.environ.get("SCBE_LLM_BASE", "http://localhost:11434/v1")
    key = os.environ.get("SCBE_LLM_KEY", "ollama")
    try:
        return _chat([{"role": "user", "content": prompt}], base=base, key=key, model=model)
    except Exception as exc:  # fail closed: an unparseable/dead reply -> wrong label, never a fake pass
        return "ERROR %s" % type(exc).__name__


def label_proposer(model: str):
    """The model's JUDGEMENT slot: given the rebuilt context (which already contains r3, r5) pick the
    label. The model does NO arithmetic -- the remainders are handed to it by the blocks."""

    def propose(ctx: str, options: List[str]) -> str:
        prompt = (
            ctx
            + "\n\nThe remainders r3 and r5 are given above (0 means divisible). "
            + "FizzBuzz if both r3 and r5 are 0; Fizz if only r3 is 0; Buzz if only r5 is 0; else none. "
            + "Reply with EXACTLY one word from: "
            + ", ".join(options)
        )
        return _match_label(_chat_once(prompt, model))

    return propose


def raw_solve(i: int, model: str) -> str:
    """BASELINE: the lone small model does the whole thing -- the multi-digit modulo AND the label -- in
    one shot, in its head. This is the weakness the routed path offloads."""
    prompt = (
        "FizzBuzz rule for N: 'FizzBuzz' if N is divisible by both 3 and 5; 'Fizz' if divisible by 3 "
        "only; 'Buzz' if divisible by 5 only; otherwise 'none'.\n"
        "N = %d\nReply with EXACTLY one word from: FizzBuzz, Fizz, Buzz, none." % i
    )
    return _match_label(_chat_once(prompt, model))


def run_gpu_demo(n: int = 30, model: str = "qwen2.5-coder:1.5b", start: int = 1000) -> str:
    """NOTE (post-refutation honesty): this arm is CALC-decomposition + rewind + menu-pruning, NOT
    block-solver routing -- the strength_router.run_routed/pre_route machinery is not exercised here, and
    the r3/r5 work is done by `calc` steps, not registered block Solvers. Its number is INFLATED by
    answer-by-elimination (the 4-option menu shrinks under prune_wrong + a ground-truth check gate), so a
    model that ignores r3/r5 still scores high. Use run_control_groups for the FAIR, no-elimination
    attribution of what the offloaded remainders are actually worth."""
    numbers = [start + k for k in range(n)]
    prop = label_proposer(model)
    routed_ok: List[int] = []
    single_ok: List[int] = []
    block_calcs = 0
    model_judgements = 0
    for i in numbers:
        truth = correct_label(i)
        # routed: blocks compute r3,r5 (calc steps), model only labels
        r = run_stepwise(number_task(i), prop, max_rewinds=2, allow_offload=False, prune_wrong=True)
        block_calcs += sum(1 for t in r["trace"] if t.get("source") == "calc")
        model_judgements += int(r.get("model_calls", 0))
        if r.get("completed") and r.get("answer") == truth:
            routed_ok.append(i)
        # baseline: model does modulo + label in one shot
        if raw_solve(i, model) == truth:
            single_ok.append(i)
    newly = sorted(set(routed_ok) - set(single_ok))
    regressed = sorted(set(single_ok) - set(routed_ok))
    rep = {
        "total": n,
        "routed_solved": len(routed_ok),
        "single_solved": len(single_ok),
        "newly_solved": newly,
        "regressed": regressed,
        "net_lift": len(newly) - len(regressed),
        "solver_mix": {"small": model_judgements, "strong": 0, "block": 0, "calc": block_calcs},
    }
    out = render(rep)
    out += (
        "\n  NOTE: %d modulo ops done by CALC steps (not block Solvers); model made %d label calls."
        "\n  This number is INFLATED by menu-elimination -- see run_control_groups for the fair delta."
        % (block_calcs, model_judgements)
    )
    return out


def _two_ints(text: str) -> tuple:
    import re

    nums = re.findall(r"-?\d+", text or "")
    return (int(nums[0]), int(nums[1])) if len(nums) >= 2 else (-1, -1)


def b_decompose_model_modulo(i: int, model: str) -> str:
    """CONTROL B (decompose, NO block): the model itself computes the remainders (two-call), then labels
    from ITS OWN remainders. Isolates decomposition-alone: same structure as routed, but the model still
    does the modulo. If B ~ single-shot, decomposition is not the lever; the BLOCK is."""
    r3m, r5m = _two_ints(_chat_once("Compute N mod 3 then N mod 5 for N=%d. Reply as: '<a> <b>'." % i, model))
    prompt = (
        "r3=%d r5=%d (0 means divisible). FizzBuzz if both 0; Fizz if only r3=0; Buzz if only r5=0; "
        "else none. Reply EXACTLY one of: FizzBuzz, Fizz, Buzz, none." % (r3m, r5m)
    )
    return _match_label(_chat_once(prompt, model))


def placebo_task(i: int) -> Task:
    """CONTROL D (placebo block): identical structure to number_task, but the blocks feed WRONG
    remainders (those of i+1). Isolates whether the lift needs CORRECT blocks or just the structure +
    some numbers in context. If D ~ single-shot, the lift is the block's CORRECTNESS, not the scaffold."""
    return Task(
        name="pb_%d" % i,
        goal="classify %d by the FizzBuzz rule using the computed remainders r3, r5" % i,
        steps=[
            Step(name="r3", key="r3", calc=(lambda st, i=i: (i + 1) % 3)),
            Step(name="r5", key="r5", calc=(lambda st, i=i: (i + 1) % 5)),
            Step(
                name="label",
                key="label",
                options=(lambda st: list(LABELS)),
                check=(lambda st, v: v == _label_from_state(st)),
            ),
        ],
    )


def label_oneshot(i: int, r3: int, r5: int, model: str) -> str:
    """Hand the model the remainders directly; ONE call, NO menu/elimination/rewind. This is the FAIR
    block-offload test: can the model label from given remainders on its own merit?"""
    prompt = (
        "r3=%d r5=%d (0 means divisible). FizzBuzz if both are 0; Fizz if only r3 is 0; Buzz if only "
        "r5 is 0; else none. Reply EXACTLY one word: FizzBuzz, Fizz, Buzz, none." % (r3, r5)
    )
    return _match_label(_chat_once(prompt, model))


def first_option_stub(ctx, options):
    """A model with NO reasoning: ignores the context, returns the first legal option. Under prune_wrong
    it just cycles the shrinking menu, so any 'solve' it gets is pure answer-by-elimination, not skill."""
    return options[0] if options else "none"


def run_control_groups(n: int = 20, model: str = "qwen2.5-coder:1.5b", start: int = 1000) -> str:
    """Fair attribution over the SAME numbers (truth=correct_label), all model arms ONE-SHOT unless noted,
    answering the refutation panel's holes:
      A raw single-shot     : model does modulo + label in one shot (the honest floor).
      B decompose, no block : model computes the remainders itself (2 calls), then labels (structure only).
      C_fair block-offload  : CORRECT remainders handed in, model labels in ONE shot, NO elimination.
      D_fair placebo        : WRONG (i+1) remainders handed in, one shot -- are the remainders load-bearing?
      C_scaffold            : blocks + rewind + prune (the INFLATED arm) -- to quantify the crutch.
      E_elim_stub           : a NO-reasoning model under the SAME scaffold -- how much elimination alone gets.
    Honest block-offload = C_fair - A. Remainders load-bearing = C_fair - D_fair. Elimination crutch =
    C_scaffold - E_elim_stub (if ~0, the inflated arm was almost entirely the menu, not the model)."""
    nums = [start + k for k in range(n)]
    prop = label_proposer(model)
    a = b = c_fair = d_fair = c_scaf = e_stub = 0
    for i in nums:
        truth = correct_label(i)
        if raw_solve(i, model) == truth:
            a += 1
        if b_decompose_model_modulo(i, model) == truth:
            b += 1
        if label_oneshot(i, i % 3, i % 5, model) == truth:
            c_fair += 1
        if label_oneshot(i, (i + 1) % 3, (i + 1) % 5, model) == truth:
            d_fair += 1
        rc = run_stepwise(number_task(i), prop, max_rewinds=2, allow_offload=False, prune_wrong=True)
        if rc.get("completed") and rc.get("answer") == truth:
            c_scaf += 1
        re_ = run_stepwise(number_task(i), first_option_stub, max_rewinds=2, allow_offload=False, prune_wrong=True)
        if re_.get("completed") and re_.get("answer") == truth:
            e_stub += 1
    pct = lambda x: 100.0 * x / n  # noqa: E731
    lines = [
        "STRENGTH-ROUTER CONTROL GROUPS  (same %d numbers, truth=correct_label, FAIR=one-shot)" % n,
        "  A  raw single-shot      : %2d/%d (%3.0f%%)   floor: model does modulo+label in head" % (a, n, pct(a)),
        "  B  decompose, no block  : %2d/%d (%3.0f%%)   model computes remainders itself, then labels" % (b, n, pct(b)),
        "  C_fair block-offload    : %2d/%d (%3.0f%%)   <- CORRECT remainders, model labels ONE-SHOT (no elim)"
        % (c_fair, n, pct(c_fair)),
        "  D_fair placebo (wrong)  : %2d/%d (%3.0f%%)   WRONG remainders handed in, one shot"
        % (d_fair, n, pct(d_fair)),
        "  C_scaffold (inflated)   : %2d/%d (%3.0f%%)   blocks + rewind + prune (menu-elimination)"
        % (c_scaf, n, pct(c_scaf)),
        "  E_elim_stub (no skill)  : %2d/%d (%3.0f%%)   NO-reasoning model under the SAME scaffold"
        % (e_stub, n, pct(e_stub)),
        "  ATTRIBUTION:",
        "    honest block-offload (C_fair - A) = %+d" % (c_fair - a),
        "    remainders load-bearing (C_fair - D_fair) = %+d" % (c_fair - d_fair),
        "    elimination crutch (C_scaffold - E_elim_stub) = %+d  (if ~0, the inflated arm was the menu, not the model)"
        % (c_scaf - e_stub),
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_gpu_demo())
