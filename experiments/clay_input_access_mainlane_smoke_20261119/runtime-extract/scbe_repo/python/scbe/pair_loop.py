"""pair_loop: a juggling harness for small/free models -- improvise only when needed, by strength.

The scaffold is the intelligence; the models are commodity hands. A TASK is a TEMPLATE: FIXED tokens
the harness emits for free (zero model calls) interleaved with BLANKs -- the genuine choice points.
The harness runs the fixed steps in order and only calls a model at a blank. Three ideas make
weak/free models actually useful together:

  * IMPROVISE ONLY WHEN NEEDED -- the model is called exactly once per blank (plus retries), never
    for the fixed structure. Most of a bounded task is mechanical; the model fills only the gaps.
  * ROUTE BY STRENGTH -- each blank declares the CAPABILITY it needs (count / name / pick / ...) and
    the harness routes it to the model that is good at THAT, then drops the model's answer into the
    command slot. If a model is great at counting, let it count the things the system needs counted;
    its count becomes the value. Play to strengths; the harness reroutes them to commands.
  * JUGGLE -- like the Fleet Juggling Scheduler: the harness keeps the blanks in the air and throws
    each to the right free hand; a CHECKER (the catch) accepts or rejects each value against the
    allowed walls -- a bad guess is just dropped, never corrupting the output.

Models are pluggable callables keyed by capability; the deterministic stubs prove the loop by
execution. Drop a real free model into a capability slot to measure it on what it is good at.

    from python.scbe.pair_loop import BLANK, Blank, template_level, run_loop, STUBS, accepting_checker
    lvl = template_level("[1, 2, 3] has ", BLANK, " items", blanks=[Blank("count", ["3"])])
    run_loop(lvl, STUBS, accepting_checker)["output"]   # -> '[1, 2, 3] has 3 items' (count routed in)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence

BLANK = object()  # the choice-point sentinel: where a model must improvise

Improviser = Callable[[str, str, Sequence[str]], str]  # (goal, output_so_far, allowed) -> value
Checker = Callable[[str, str, Sequence[str]], bool]  # (output_so_far, proposed, allowed) -> accept?


@dataclass
class Blank:
    capability: str  # the skill this choice-point needs: "count" | "name" | "pick" | ...
    allowed: List[str]  # the walls: the values the checker will accept


@dataclass
class Level:
    name: str
    goal: str
    template: List[object]  # fixed strings, with BLANK at choice points
    blanks: List[Blank]  # one per BLANK, in order

    def fixed_count(self) -> int:
        return sum(1 for t in self.template if t is not BLANK)

    def blank_count(self) -> int:
        return sum(1 for t in self.template if t is BLANK)


def template_level(
    *template: object, blanks: Optional[List[Blank]] = None, name: str = "task", goal: str = ""
) -> Level:
    blanks = blanks or []
    n = sum(1 for t in template if t is BLANK)
    if len(blanks) != n:
        raise ValueError("template has %d blanks but %d Blank specs given" % (n, len(blanks)))
    return Level(name=name, goal=goal or name, template=list(template), blanks=blanks)


def run_loop(
    level: Level,
    routers: Dict[str, Improviser],
    checker: Checker = None,  # type: ignore[assignment]
    default: Improviser = None,  # type: ignore[assignment]
    budget: int = 60,
) -> dict:
    """Run the template: emit fixed tokens free, route each blank to its capability's model, check it."""
    checker = checker or accepting_checker
    default = default or stub_improviser
    idx, bidx, out = 0, 0, ""
    counts = {"deterministic": 0, "improvised": 0, "rejected": 0}
    by_capability: Dict[str, int] = {}
    transcript: List[dict] = []
    steps = 0
    while idx < len(level.template) and steps < budget:
        steps += 1
        tok = level.template[idx]
        if tok is not BLANK:  # pre-programmed: emit for free, no model
            out += str(tok)
            idx += 1
            counts["deterministic"] += 1
            transcript.append({"step": steps, "source": "fixed", "value": tok, "status": "ok"})
            continue
        blank = level.blanks[bidx]
        model = routers.get(blank.capability, default)  # ROUTE BY STRENGTH
        value = model(level.goal, out, blank.allowed)  # the only place a model is called
        counts["improvised"] += 1
        by_capability[blank.capability] = by_capability.get(blank.capability, 0) + 1
        if not checker(out, value, blank.allowed):  # the catch / the walls
            counts["rejected"] += 1
            transcript.append({"step": steps, "source": blank.capability, "value": value, "status": "dropped"})
            continue  # the blank stays in the air -- throw again next iteration
        out += str(value)
        idx += 1
        bidx += 1
        transcript.append({"step": steps, "source": blank.capability, "value": value, "status": "ok"})
    return {
        "level": level.name,
        "cleared": idx >= len(level.template),
        "output": out,
        "steps": steps,
        "model_calls": counts["improvised"],  # == blanks (+ retries), never the fixed structure
        "by_capability": by_capability,
        "counts": counts,
        "transcript": transcript,
    }


# --- deterministic stub "models", one per strength (real free models replace these) ----
def stub_improviser(goal: str, out: str, allowed: Sequence[str]) -> str:
    return allowed[0] if allowed else ""


def count_stub(goal: str, out: str, allowed: Sequence[str]) -> str:
    """Good at counting: count the list items already in the output, route the number into the slot."""
    n = out.count(",") + 1 if "[" in out and "]" in out else len(out.split())
    return str(n)


def name_stub(goal: str, out: str, allowed: Sequence[str]) -> str:
    """Good at naming: pick a legal identifier from the allowed set."""
    ids = [a for a in allowed if a[:1].isalpha()]
    return ids[0] if ids else (allowed[0] if allowed else "x")


STUBS: Dict[str, Improviser] = {"count": count_stub, "name": name_stub, "pick": stub_improviser}


def accepting_checker(out: str, proposed: str, allowed: Sequence[str]) -> bool:
    """The catch: accept iff the value is within the walls (the allowed set for this blank)."""
    return proposed in allowed


def _demo_levels() -> List[Level]:
    return [
        template_level(
            "[1, 2, 3] has ",
            BLANK,
            " items",
            blanks=[Blank("count", ["3"])],
            name="count_items",
            goal="state how many items the list has; route the counting to the counting model",
        ),
        template_level(
            "def ",
            BLANK,
            "(): return ",
            BLANK,
            blanks=[Blank("name", ["greet", "f"]), Blank("pick", ["42", "0"])],
            name="write_function",
            goal="name a function and pick its return value",
        ),
        template_level("x = 1", name="fully_fixed"),  # no blanks -> no model is ever called
    ]


def main(argv: Optional[Sequence[str]] = None) -> int:
    print("PAIR LOOP  juggling harness: improvise only when needed, route blanks by strength\n")
    for lvl in _demo_levels():
        r = run_loop(lvl, STUBS, accepting_checker)
        print("  %-16s -> %-28r cleared=%s" % (lvl.name, r["output"], r["cleared"]))
        print(
            "      %d fixed emitted free; %d blank(s) routed by strength %s; model_calls=%d"
            % (lvl.fixed_count(), lvl.blank_count(), r["by_capability"] or "{}", r["model_calls"])
        )
    print("\n  fixed structure costs 0 model calls; each blank goes to the model good at its capability.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
