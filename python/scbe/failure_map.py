"""failure_map: localize WHERE a model drifts, and map it across models -- the capability basement.

stepwise.run_stepwise surfaces the ceiling for ONE run. This aggregates many runs (tasks x models)
into the "points on paper" map: turn pass/fail into WHERE (which step it got stuck at, point 1 ->
point F) and, across models, WHY (which step is the wall). Four views:

  * DRIFT POINT   -- per (model, task): the step index it reached and where it stuck.
  * WALL          -- per task: the modal stuck step among the models that failed it.
  * CROSS-MODEL   -- who clears a task that others don't (where does model A's edge sit vs B).
  * UNIVERSAL-FAIL -- tasks no model clears, and the wall step (if nobody passes there, that step
    IS the why -- structurally, not a claim about the model's mind).

A proposer is the model slot (stepwise.Proposer): `clears_through(k)` and scripted stubs prove the
map by construction; a real model drops into the same slot. HONEST: this LOCATES failures; it does
not explain capability. "Why" here = which step is the wall, not why the model can't climb it.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Mapping, Sequence

from .stepwise import Proposer, Step, Task, run_stepwise


def localize(task: Task, proposer: Proposer, max_rewinds: int = 3) -> Dict[str, Any]:
    """Run one (task, model) and report the drift point: where it stuck (point F) or that it cleared.

    Offload is forced OFF here: this measures the MODEL's true ceiling. An oracle would auto-rescue the
    wall step and report 'cleared', blinding the map to where the model actually drifts. failure_map
    diagnoses the wall; auto-offload (in run_stepwise) is the cure -- keep them separate or the map goes
    blind. The recovery this returns is precisely "offload that step", which the harness can now do.
    """
    r = run_stepwise(task, proposer, max_rewinds, allow_offload=False)
    names = [s.name for s in task.steps]
    if r["completed"]:
        return {"task": task.name, "cleared": True, "stuck_at": None, "stuck_index": len(names), "total": len(names)}
    stuck = r.get("stuck_at")
    return {
        "task": task.name,
        "cleared": False,
        "stuck_at": stuck,
        "stuck_index": names.index(stuck) if stuck in names else -1,
        "total": len(names),
    }


def run_map(tasks: Sequence[Task], proposers: Mapping[str, Proposer], max_rewinds: int = 3) -> Dict[str, Any]:
    """Localize every (model, task) and build the four views."""
    pnames = list(proposers)
    cells = {(p, t.name): localize(t, proposers[p], max_rewinds) for p in pnames for t in tasks}
    per_task: Dict[str, Any] = {}
    for t in tasks:
        clearers = [p for p in pnames if cells[(p, t.name)]["cleared"]]
        stuck = [cells[(p, t.name)]["stuck_at"] for p in pnames if not cells[(p, t.name)]["cleared"]]
        per_task[t.name] = {
            "clearers": clearers,
            "no_clearers": not clearers,
            "wall": Counter(stuck).most_common(1)[0][0] if stuck else None,
        }
    return {
        "tasks": [t.name for t in tasks],
        "proposers": pnames,
        "cells": cells,
        "per_task": per_task,
        "universal_fail": [t.name for t in tasks if per_task[t.name]["no_clearers"]],
    }


def render_map(m: Dict[str, Any]) -> str:
    w = max([len(t) for t in m["tasks"]] + [6])
    lines = ["FAILURE MAP  (rows=models, cols=tasks; ok=cleared, @s=drift point)"]
    lines.append("  %-12s " % "model\\task" + " ".join("%-*s" % (w, t) for t in m["tasks"]))
    for p in m["proposers"]:
        cells = []
        for t in m["tasks"]:
            c = m["cells"][(p, t)]
            cells.append("%-*s" % (w, "ok" if c["cleared"] else "@" + (c["stuck_at"] or "?")))
        lines.append("  %-12s " % p + " ".join(cells))
    for t in m["tasks"]:
        pt = m["per_task"][t]
        if pt["wall"] is not None:
            lines.append("  %s: wall at '%s'; cleared by %s" % (t, pt["wall"], ",".join(pt["clearers"]) or "nobody"))
    if m["universal_fail"]:
        lines.append("  UNIVERSAL-FAIL (no model clears): " + ", ".join(m["universal_fail"]))
    return "\n".join(lines)


# --- fixture proposers (a real model drops into the same slot) -----------------------
def clears_through(k: int) -> Proposer:
    """A model that chooses correctly through step k, then drifts -- to place drift at a known point.
    (Reads the current step number from the rebuilt context; correct answer is options[0].)"""

    def p(ctx: str, options: List[str]) -> str:
        m = re.search(r"choose s(\d+)", ctx)
        n = int(m.group(1)) if m else 1
        return options[0] if (options and n <= k) else "x"

    return p


def seq_task(name: str, answers: Sequence[str]) -> Task:
    """A task of N choice steps s1..sN; each step's correct answer is answers[i] (== options[0])."""
    steps = [
        Step(
            name="s%d" % (i + 1),
            key="s%d" % (i + 1),
            options=(lambda st, a=a: [a, "x", "y"]),
            check=(lambda st, v, a=a: v == a),
        )
        for i, a in enumerate(answers)
    ]
    return Task(name=name, steps=steps, goal=name)


def _demo() -> int:
    tasks = [seq_task("alpha", ["a1", "a2", "a3"]), seq_task("beta", ["b1", "b2"])]
    proposers = {"strong": clears_through(9), "mid": clears_through(2), "weak": clears_through(0)}
    print(render_map(run_map(tasks, proposers)))
    print("\n(strong clears all; mid drifts at alpha.s3; weak drifts at s1 everywhere)")
    return 0


def main(argv: Sequence[str] = ()) -> int:
    return _demo()


if __name__ == "__main__":
    raise SystemExit(main())
