"""stepwise: a guided step machine where a misstep REWINDS instead of failing -- the repair loop.

The weak-model failures we measured (fizzbuzz's i%3 polarity, max_coins' wrong objective) share a
shape: the model does an exact computation in its head and gets it subtly wrong, then commits the
mistake into the final answer with no chance to recover. This machine removes both halves of that:

  * DETERMINISTIC STEPS ARE A CALCULATOR -- a step can be a `calc` run by CODE (a lookup table / the
    sieve / plain arithmetic), never the model. The exact computation the model would botch (a
    modulo, a table lookup) is just done correctly. The model is only asked to make the CHOICES that
    actually need judgement.
  * A MISSTEP REWINDS, IT DOES NOT FAIL -- at a `choice` step the model proposes a value; a checker
    (the walls + a correctness test) accepts or rejects it. A rejected value is a MISSTEP: the
    machine stays put (the bad value is never committed), emits a WARNING, rebuilds the context from
    the goal + the steps that already ran + what went wrong, and lets the model try again from
    exactly the position before the misstep.
  * AUTO-OFFLOAD ON FAILURE -- a `choice` step may register an `oracle`: a deterministic tool that
    computes a value. When the model burns its rewinds and still can't, the machine does NOT go
    stuck -- it falls back to the oracle and continues. This is the measured lift, automated: the
    harness SUPPLIES the capability the model lacks instead of just surfacing the wall. The honest
    boundary holds: a step with NO oracle (a genuine judgement the code can't do) still stops
    honestly. The oracle is held to the SAME gate as the model -- its value must be legal (in the
    step's options) and pass the step's `check` if one exists; a value that fails the gate is never
    committed, it falls through to stuck. (Caveat, no overclaim: when the `check` is derived from the
    same rule as the oracle, that gate is only a legality wall -- not an independent correctness
    proof. The gate is exactly as strong as the predicates the step supplies, no stronger.)
  * STUCK-PRIOR / FORCED DEVIATION (`prune_wrong`) -- the data says self-repair gives ~+0: told its
    answer is wrong, a weak model re-proposes the SAME wrong thing (its System-1 prior is sticky).
    So don't just ask again the same way -- RESTRUCTURE: a value that fails the check is eliminated
    from the menu offered next, so the model literally cannot fall back into the rut. Pruning removes
    only proven-wrong values (never the correct one, which passes the check), so it can only narrow
    toward the answer, never away. This is the harness supplying the "notice I'm looping and change
    approach" metacognition the model doesn't have. Rescue ladder: retry -> restructure -> tool -> stop.

So the scaffold carries the exactness, the memory, a tool fallback, AND the deliberate-deviation the
model can't run internally; the model supplies judgement, its mistakes are caught + rewound, the rut
is pruned out from under it, and the steps a tool CAN do are auto-rescued when even that isn't enough.
Proposers are pluggable callables; the scripted stubs prove the loop, a real model drops into the slot.

    t = number_label_task(6)                 # r3=6%3, r5=6%5 done by CALC; the label is the choice
    run_stepwise(t, scripted_proposer(["Buzz", "Fizz"]))   # 'Buzz' missteps -> rewind -> 'Fizz' ok
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

# a proposer is the model slot: given the rebuilt context and the legal options, choose a value
Proposer = Callable[[str, List[str]], str]


@dataclass
class Step:
    """One step. A `calc` step is deterministic (code, never the model). A `choice` step asks the
    model for a value, gated by `options` (the legal set / walls) and `check` (is it correct). An
    optional `oracle` is a deterministic tool that computes a value -- the auto-offload fallback used
    when the model exhausts its rewinds; its value is held to the same options/check gate as the model."""

    name: str
    key: str
    calc: Optional[Callable[[Dict[str, Any]], Any]] = None
    options: Optional[Callable[[Dict[str, Any]], List[str]]] = None
    check: Optional[Callable[[Dict[str, Any], str], bool]] = None
    oracle: Optional[Callable[[Dict[str, Any]], Any]] = None

    def is_calc(self) -> bool:
        return self.calc is not None


@dataclass
class Task:
    name: str
    steps: List[Step]
    goal: str = ""


def build_context(task: Task, state: Dict[str, Any], step: Step, options: List[str], trace: List[dict]) -> str:
    """Reconstruct the instruction from the goal + the steps already run + any misstep warning.

    This is the 'instructions gathered from context and the ran steps up to that point' -- a stateless
    model rehydrates exactly where it is and what just went wrong, without holding its own history.
    """
    done = [t for t in trace if t["status"] == "ok"]
    lines = ["goal: %s" % (task.goal or task.name)]
    if done:
        lines.append("steps done: " + " | ".join("%s=%s" % (t["step"], t["value"]) for t in done))
    lines.append("now: choose %s   allowed: %s" % (step.name, options))
    if state.get("_warning"):
        lines.append("[!] " + state["_warning"])  # the rewind warning
    return "\n".join(lines)


def run_stepwise(
    task: Task,
    proposer: Proposer,
    max_rewinds: int = 3,
    allow_offload: bool = True,
    prune_wrong: bool = True,
) -> Dict[str, Any]:
    """Walk the steps. Calc steps run in code; choice steps call the model and rewind on a misstep.

    STUCK-PRIOR / FORCED DEVIATION (`prune_wrong`): a weak model often LOOPS -- it re-proposes the
    same wrong value, because "try again" hits the same System-1 reflex (the +0 self-repair wall).
    So a value that fails the step's check is ELIMINATED from the options offered on the next retry:
    the model cannot re-pick a proven-wrong answer because it is no longer on the menu. This is the
    harness externalizing "deliberately deviate from my habit" -- the metacognition the model lacks.
    Pruning only removes PROVEN-WRONG values (they failed the check), never the correct answer (it
    passes the check, so it is never eliminated), so the final commit is still gated and still correct;
    if the answer is in the options, monotone narrowing forces the model toward it. A re-proposal of an
    already-eliminated value is the stuck-prior tell, counted in `stuck_priors`.

    When a choice step exhausts its rewinds: if `allow_offload` and the step has an `oracle`, fall
    back to the oracle (auto-offload) instead of going stuck -- but only if the oracle's value clears
    the SAME gate the model must (legal/in the FULL options, and the step's check if any); otherwise it
    falls through to stuck. The rescue ladder is retry -> restructure (prune) -> tool (offload) -> stuck.
    `allow_offload=False` measures the un-rescued baseline; `prune_wrong=False` the un-restructured one.
    """
    state: Dict[str, Any] = {}
    trace: List[dict] = []
    pos = 0
    total_rewinds = 0
    model_calls = 0
    stuck_priors = 0
    offloaded: List[str] = []
    while pos < len(task.steps):
        step = task.steps[pos]
        if step.is_calc():
            v = step.calc(state)  # type: ignore[misc]
            state[step.key] = v
            trace.append({"step": step.name, "source": "calc", "value": v, "status": "ok"})
            pos += 1
            continue
        full_options = step.options(state) if step.options else []
        tried_wrong: List[str] = []  # proven-wrong values at this step -> eliminated from the menu
        rewinds = 0
        while True:
            # forced deviation: offer the menu minus everything already proven wrong at this step
            options = [o for o in full_options if o not in tried_wrong] if prune_wrong else list(full_options)
            ctx = build_context(task, state, step, options, trace)
            value = proposer(ctx, options)
            model_calls += 1
            repeated = value in tried_wrong  # the stuck-prior tell: re-proposing a known-wrong value
            if repeated:
                stuck_priors += 1
            legal = (not full_options) or (value in options)
            correct = step.check(state, value) if step.check else legal
            if legal and correct:
                state[step.key] = value
                state.pop("_warning", None)
                trace.append(
                    {
                        "step": step.name,
                        "source": "model",
                        "value": value,
                        "status": "ok",
                        "rewinds": rewinds,
                        "remaining": len(options),
                    }
                )
                pos += 1
                break
            rewinds += 1
            total_rewinds += 1
            why = (
                "repeated a proven-wrong answer"
                if repeated
                else ("not in the allowed set" if not legal else "failed the step's check")
            )
            if value in full_options and value not in tried_wrong:
                tried_wrong.append(value)  # proven wrong -> eliminate from the menu (forced deviation)
            trace.append(
                {
                    "step": step.name,
                    "source": "model",
                    "value": value,
                    "status": "misstep",
                    "why": why,
                    "repeated": repeated,
                }
            )
            if rewinds > max_rewinds:  # model exhausted -> try the deterministic oracle, else stop honestly
                state.pop("_warning", None)
                if allow_offload and step.oracle is not None:
                    ov = step.oracle(state)
                    # hold the oracle to the SAME gate as the model: legal (in the FULL options) AND, if
                    # the step has a check, passing it. A gate-failing oracle value is never committed.
                    legal = (not full_options) or (ov in full_options)
                    if legal and (step.check(state, ov) if step.check else True):
                        state[step.key] = ov
                        offloaded.append(step.name)
                        trace.append({"step": step.name, "source": "offload", "value": ov, "status": "ok"})
                        pos += 1
                        break
                return {
                    "completed": False,
                    "stuck_at": step.name,
                    "state": state,
                    "rewinds": total_rewinds,
                    "model_calls": model_calls,
                    "stuck_priors": stuck_priors,
                    "offloaded": offloaded,
                    "trace": trace,
                }
            # rewind: position is unchanged (the bad value was never committed); retry with a warning
            warning = "misstep at '%s': %r %s." % (step.name, value, why)
            if prune_wrong and tried_wrong:
                warning += " Eliminated (do NOT repeat): %s. Choose from %s" % (tried_wrong, options)
            else:
                warning += " Back up and choose from %s" % (options,)
            state["_warning"] = warning
    return {
        "completed": True,
        "answer": trace[-1]["value"] if trace else None,
        "state": state,
        "rewinds": total_rewinds,
        "model_calls": model_calls,
        "stuck_priors": stuck_priors,
        "offloaded": offloaded,
        "trace": trace,
    }


# --- pluggable proposer stubs (a real model drops into the same slot) ----------------
def scripted_proposer(seq: List[str]) -> Proposer:
    """Return the given answers in order (clamped to the last) -- to script misstep/recover paths."""
    calls = {"i": 0}

    def p(_ctx: str, _options: List[str]) -> str:
        i = min(calls["i"], len(seq) - 1)
        calls["i"] += 1
        return seq[i]

    return p


def always_proposer(value: str) -> Proposer:
    def p(_ctx: str, _options: List[str]) -> str:
        return value

    return p


def sticky_proposer(favorite: str) -> Proposer:
    """A sticky System-1 prior: keep proposing `favorite`; only when forced deviation eliminates it
    from the menu does it fall to the first still-legal option. Models the loop the +0 repair data
    showed -- it never self-corrects, it just stops repeating once the rut is pruned out from under it."""

    def p(_ctx: str, options: List[str]) -> str:
        if favorite in options:
            return favorite
        return options[0] if options else favorite

    return p


# --- a demo task: classify a number, with the modulo done by CALC (not the model) ----
_LABELS = ("Fizz", "Buzz", "FizzBuzz")


def number_label_task(i: int) -> Task:
    """r3 = i%3 and r5 = i%5 are computed deterministically; only the LABEL is a model choice.

    This is exactly the fizzbuzz failure mode defused: the model never does the modulo it kept getting
    wrong -- it only picks the label, and a wrong pick rewinds instead of shipping.
    """

    def correct_label(st: Dict[str, Any]) -> str:
        if st["r3"] == 0 and st["r5"] == 0:
            return "FizzBuzz"
        if st["r3"] == 0:
            return "Fizz"
        if st["r5"] == 0:
            return "Buzz"
        return str(i)

    return Task(
        name="number_label(%d)" % i,
        goal="label %d by the fizzbuzz rule" % i,
        steps=[
            Step("r3", "r3", calc=lambda st: i % 3),
            Step("r5", "r5", calc=lambda st: i % 5),
            Step(
                "label",
                "label",
                options=lambda st: list(_LABELS) + [str(i)],
                check=lambda st, v: v == correct_label(st),
                oracle=correct_label,  # the rule itself: auto-offload fallback when the model can't
            ),
        ],
    )


def main(argv: Optional[List[str]] = None) -> int:
    print("STEPWISE  a misstep rewinds (with warning + rebuilt context) instead of failing\n")

    print("== clean run: the model picks the right label first try (mod done by calc) ==")
    r = run_stepwise(number_label_task(6), scripted_proposer(["Fizz"]))
    print(
        "  6 -> %s   completed=%s  rewinds=%d  model_calls=%d"
        % (r["answer"], r["completed"], r["rewinds"], r["model_calls"])
    )

    print("\n== misstep + recover: 'Buzz' is wrong for 6, the machine rewinds and warns ==")
    r = run_stepwise(number_label_task(6), scripted_proposer(["Buzz", "Fizz"]))
    for t in r["trace"]:
        extra = ("  <- " + t["why"]) if t["status"] == "misstep" else ""
        print("  %-6s %-6s %-9s %s%s" % (t["step"], t["source"], t["status"], t["value"], extra))
    print("  -> %s   completed=%s  rewinds=%d" % (r["answer"], r["completed"], r["rewinds"]))

    print("\n== a model that NEVER gets it: without auto-offload it stops honestly ==")
    r = run_stepwise(number_label_task(6), always_proposer("Buzz"), max_rewinds=2, allow_offload=False)
    print("  allow_offload=False -> completed=%s  stuck_at=%s" % (r["completed"], r.get("stuck_at")))

    print("\n== same hopeless model, WITH auto-offload: the oracle (the rule) rescues the step ==")
    r = run_stepwise(number_label_task(6), always_proposer("Buzz"), max_rewinds=2, allow_offload=True)
    print(
        "  allow_offload=True  -> completed=%s  answer=%r  offloaded=%s"
        % (r["completed"], r.get("answer"), r["offloaded"])
    )
    print("  (the model burned its tries; the deterministic rule supplied the right label -> 6 is 'Fizz')")

    print("\n== STUCK PRIOR: a model that keeps re-proposing the same wrong label (10 is 'Buzz') ==")
    sticky = sticky_proposer("Fizz")  # its sticky prior: always grab 'Fizz' (wrong for 10)
    r = run_stepwise(number_label_task(10), sticky, max_rewinds=3, allow_offload=False, prune_wrong=False)
    print(
        "  no restructure -> completed=%s  stuck_at=%s  stuck_priors=%d  (it loops on 'Fizz', never deviates)"
        % (r["completed"], r.get("stuck_at"), r["stuck_priors"])
    )

    print("\n== FORCED DEVIATION: eliminate the proven-wrong label; the model can't fall back into the rut ==")
    r = run_stepwise(
        number_label_task(10), sticky_proposer("Fizz"), max_rewinds=3, allow_offload=False, prune_wrong=True
    )
    for t in r["trace"]:
        if t["source"] == "model":
            note = (
                ("  <- " + t["why"])
                if t["status"] == "misstep"
                else ("  (remaining options: %d)" % t.get("remaining", 0))
            )
            print("  %-6s %-9s %-6s%s" % (t["step"], t["status"], t["value"], note))
    print(
        "  -> %s  completed=%s  rewinds=%d  stuck_priors=%d  offloaded=%s"
        % (r["answer"], r["completed"], r["rewinds"], r["stuck_priors"], r["offloaded"])
    )
    print("  (no tool used: pruning 'Fizz' off the menu forced the model onto 'Buzz' -- restructure, not offload)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
