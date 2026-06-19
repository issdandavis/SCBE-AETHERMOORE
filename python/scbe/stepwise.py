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
    exactly the position before the misstep. After `max_rewinds` it stops honestly at that step --
    that is the model's real ceiling, surfaced, not a corrupted answer.

So the scaffold carries the exactness and the memory; the model only supplies judgement, and its
mistakes are caught and rewound instead of shipped. Proposers are pluggable callables; the scripted
stubs prove the loop by construction, and a real model drops into the same slot.

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
    model for a value, gated by `options` (the legal set / walls) and `check` (is it correct)."""

    name: str
    key: str
    calc: Optional[Callable[[Dict[str, Any]], Any]] = None
    options: Optional[Callable[[Dict[str, Any]], List[str]]] = None
    check: Optional[Callable[[Dict[str, Any], str], bool]] = None

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


def run_stepwise(task: Task, proposer: Proposer, max_rewinds: int = 3) -> Dict[str, Any]:
    """Walk the steps. Calc steps run in code; choice steps call the model and rewind on a misstep."""
    state: Dict[str, Any] = {}
    trace: List[dict] = []
    pos = 0
    total_rewinds = 0
    model_calls = 0
    while pos < len(task.steps):
        step = task.steps[pos]
        if step.is_calc():
            v = step.calc(state)  # type: ignore[misc]
            state[step.key] = v
            trace.append({"step": step.name, "source": "calc", "value": v, "status": "ok"})
            pos += 1
            continue
        options = step.options(state) if step.options else []
        rewinds = 0
        while True:
            ctx = build_context(task, state, step, options, trace)
            value = proposer(ctx, options)
            model_calls += 1
            legal = (not options) or (value in options)
            correct = step.check(state, value) if step.check else legal
            if legal and correct:
                state[step.key] = value
                state.pop("_warning", None)
                trace.append({"step": step.name, "source": "model", "value": value, "status": "ok", "rewinds": rewinds})
                pos += 1
                break
            rewinds += 1
            total_rewinds += 1
            why = "not in the allowed set" if not legal else "failed the step's check"
            trace.append({"step": step.name, "source": "model", "value": value, "status": "misstep", "why": why})
            if rewinds > max_rewinds:  # exhausted -> honest ceiling at this step
                state.pop("_warning", None)
                return {
                    "completed": False,
                    "stuck_at": step.name,
                    "state": state,
                    "rewinds": total_rewinds,
                    "model_calls": model_calls,
                    "trace": trace,
                }
            # rewind: position is unchanged (the bad value was never committed); retry with a warning
            state["_warning"] = "misstep at '%s': %r %s -- back up and choose from %s" % (
                step.name,
                value,
                why,
                options,
            )
    return {
        "completed": True,
        "answer": trace[-1]["value"] if trace else None,
        "state": state,
        "rewinds": total_rewinds,
        "model_calls": model_calls,
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

    print("\n== stuck: a model that keeps mis-stepping stops honestly at its ceiling ==")
    r = run_stepwise(number_label_task(6), always_proposer("Buzz"), max_rewinds=2)
    print("  completed=%s  stuck_at=%s  rewinds=%d" % (r["completed"], r.get("stuck_at"), r["rewinds"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
