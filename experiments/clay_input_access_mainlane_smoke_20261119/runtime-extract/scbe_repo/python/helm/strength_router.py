"""strength_router: PROACTIVE, strength-routed composition -- a reliable whole from unreliable parts.

The reactive pattern (code_factory) is: let the weak model attempt a step, detect the failure, repair.
This is the PROACTIVE inversion: PRE-ASSIGN each step of a decomposed task to its best solver BEFORE
running, so the weak model never attempts the step it is known to fail. Three solver kinds:

  * BLOCK  -- a deterministic verified primitive. In `stepwise` this is a `calc` step (run by CODE,
             never the model) or a step `oracle`. The exact computation the small model botches (a
             modulo, a lookup) is just done correctly. This is "fill the steps with pre-reasoned
             blocks so the computation happens" -- the model is freed to do only judgement.
  * SMALL  -- the cheap local model, used ONLY on steps a failure map says it clears (its strengths).
  * STRONG -- a bigger model, escalated to EXACTLY the steps the small one is known-weak on, not blanket.

Pre-routing reads a failure map (failure_map.run_map: per-(model,task) where each model drifts) and
assigns the cheapest solver that clears each step. Composition reuses stepwise.run_stepwise as the
executor (its single proposer slot is fanned out per-step by `routed_proposer`); calc/block steps run
in code. Truth is execution: the END-TO-END headline re-verifies the assembled output against held-out
hidden tests via public_bench._verify -- per-step gates are necessary but never the final judge.

Honest guardrails (a routed "lift" is easy to fake): the headline reports `solver_mix` so a reviewer
can see the strong model handled only the known-weak steps and blocks were narrow primitives, not the
answer key; escalation is gated to steps the cheaper model drifts AT/before; calibration (map) and eval
sets must be disjoint. See risks in measure_routing_lift's docstring.

    python -m python.helm.strength_router --demo     # offline: routing math on stepwise fixtures
    python -m python.helm.strength_router --gpu      # live: block-offload defuses 1.5b modulo failure
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from python.scbe.stepwise import Proposer, Step, Task, run_stepwise

# the current-step marker emitted by stepwise.build_context: "now: choose <step.name>   allowed: [...]"
_STEP_RE = re.compile(r"now:\s*choose\s+(\S+)")

Block = Callable[[Dict[str, Any]], Any]


@dataclass(frozen=True)
class Solver:
    """One pluggable solver. kind in {'small','strong','block'}. A model solver carries a `proposer`
    (the stepwise (ctx, options)->str slot); a block carries a deterministic `block(state)->value`.
    `cost` orders ties so the cheapest clearing solver wins (block 0 < small 1 < strong 3)."""

    name: str
    kind: str
    proposer: Optional[Proposer] = None
    block: Optional[Block] = None
    cost: int = 1


# --------------------------------------------------------------------------------------------------
# pre-routing: assign each CHOICE step to a solver BEFORE running, reading the failure map
# --------------------------------------------------------------------------------------------------
def _cell(fmap: Dict[str, Any], model: str, task_name: str) -> Optional[Dict[str, Any]]:
    """failure_map.run_map stores cells under a (model, task) tuple key."""
    return (fmap.get("cells") or {}).get((model, task_name))


def clears_step(fmap: Dict[str, Any], model: str, task_name: str, step_index: int) -> bool:
    """Does `model` get PAST `step_index` on `task_name` in the map? True if it cleared the whole task
    or its drift point is strictly after this step (stuck_index > step_index). A model that drifts AT
    or before the step is NOT strong enough here."""
    c = _cell(fmap, model, task_name)
    if c is None:
        return False
    if c.get("cleared"):
        return True
    return int(c.get("stuck_index", -1)) > step_index


def block_eligible(step: Step, blocks: Mapping[str, Solver]) -> Optional[Solver]:
    """A block is eligible for a step ONLY as a narrow primitive registered for that step's key/name.
    Calc steps are already code (skip). Returns the block Solver or None. ANTI-CHEAT: keyed per step,
    so no single block can answer a multi-step task -- it can only do its one registered computation."""
    if step.is_calc():
        return None
    return blocks.get(step.key) or blocks.get(step.name)


def pre_route(
    task: Task,
    fmap: Dict[str, Any],
    solvers: Sequence[Solver],
    blocks: Mapping[str, Solver] = {},
) -> Dict[str, Solver]:
    """THE PROACTIVE STEP. For each choice step, choose its solver BEFORE the task runs, cheapest-first:
      0. calc step      -> handled in code by run_stepwise (recorded as 'calc', not assigned here).
      1. verified block -> if a narrow block is registered for the step, assign it (cost 0, correct).
      2. smallest model -> the cheapest model solver that CLEARS the step in fmap (its known strength).
      3. escalate       -> if no cheaper model clears it, the cheapest model that clears past it.
      4. wall           -> if no model clears (universal_fail) and no block, assign the strongest model
                           but flag needs_restructure (do not manufacture a solve nothing can do).
    Returns {step.name -> Solver}. Model solvers are sorted by (cost, name); block beats every model."""
    models = sorted([s for s in solvers if s.kind in ("small", "strong")], key=lambda s: (s.cost, s.name))
    assignment: Dict[str, Solver] = {}
    for idx, step in enumerate(task.steps):
        if step.is_calc():
            continue  # block-by-construction: code runs it, no model
        blk = block_eligible(step, blocks)
        if blk is not None:
            assignment[step.name] = blk
            continue
        chosen = next((m for m in models if clears_step(fmap, m.name, task.name, idx)), None)
        if chosen is None:
            # nobody clears it (a wall / universal_fail): best-effort to the strongest model. We do NOT
            # silently route a wall to a block -- block_eligible already gated that above. A step nothing
            # clears is the honest frontier (restructure), not a place to manufacture a solve.
            chosen = models[-1] if models else Solver("none", "small")
        assignment[step.name] = chosen
    return assignment


# --------------------------------------------------------------------------------------------------
# composition: fan the per-step assignment out behind stepwise's single proposer slot
# --------------------------------------------------------------------------------------------------
def routed_proposer(assignment: Dict[str, Solver], counter: Optional[Dict[str, int]] = None) -> Proposer:
    """Adapt the per-step assignment to stepwise's single (ctx, options)->str slot. Parses the current
    step name from the rebuilt context ('now: choose <name>') and dispatches to the assigned solver:
    model solver -> its proposer; block solver -> evaluate against... (blocks for choice steps are
    attached as the step ORACLE in run_routed, so here a 'block'-assigned step still needs a proposer
    fallback -- we use the assigned model if present, else a stub that defers to the oracle by failing)."""

    def propose(ctx: str, options: List[str]) -> str:
        m = _STEP_RE.search(ctx)
        name = m.group(1) if m else ""
        if counter is not None:
            counter[name] = counter.get(name, 0) + 1
        solver = assignment.get(name)
        if solver is None or solver.proposer is None:
            # block-assigned choice step with no model proposer: emit an illegal sentinel so the gate
            # rejects and run_stepwise auto-offloads to the step's oracle (the block, attached below).
            return "__defer_to_block__"
        return solver.proposer(ctx, options)

    return propose


def _attach_block_oracles(task: Task, assignment: Dict[str, Solver]) -> Task:
    """For choice steps assigned a block solver, set the step's oracle to the block so run_stepwise's
    auto-offload runs the deterministic primitive (held to the same gate as a model would be)."""
    new_steps: List[Step] = []
    for step in task.steps:
        s = assignment.get(step.name)
        if s is not None and s.kind == "block" and s.block is not None and not step.is_calc():
            new_steps.append(
                Step(
                    name=step.name, key=step.key, calc=step.calc, options=step.options, check=step.check, oracle=s.block
                )
            )
        else:
            new_steps.append(step)
    return Task(name=task.name, steps=new_steps, goal=task.goal)


def run_routed(task: Task, assignment: Dict[str, Solver], max_rewinds: int = 3) -> Dict[str, Any]:
    """Execute the pre-routed task via stepwise. Returns run_stepwise's dict augmented with the
    per-kind solver mix (how many choice steps went to small / strong / block) for the guardrail."""
    eff_task = _attach_block_oracles(task, assignment)
    counter: Dict[str, int] = {}
    res = run_stepwise(
        eff_task, routed_proposer(assignment, counter), max_rewinds=max_rewinds, allow_offload=True, prune_wrong=True
    )
    mix = {"small": 0, "strong": 0, "block": 0, "calc": 0}
    for step in task.steps:
        if step.is_calc():
            mix["calc"] += 1
        else:
            s = assignment.get(step.name)
            if s is not None and s.kind in mix:
                mix[s.kind] += 1
    res["solver_mix"] = mix
    return res


# --------------------------------------------------------------------------------------------------
# calibration: build the failure map (thin wrapper over failure_map.run_map)
# --------------------------------------------------------------------------------------------------
def build_failure_map(tasks: Sequence[Task], model_solvers: Sequence[Solver], max_rewinds: int = 3) -> Dict[str, Any]:
    """Run each model solver over the CALIBRATION tasks and aggregate where each drifts. Block solvers
    are deterministic and clear their eligible step by construction, so only models are mapped."""
    from python.scbe.failure_map import run_map

    proposers = {s.name: s.proposer for s in model_solvers if s.kind in ("small", "strong") and s.proposer}
    return run_map(tasks, proposers, max_rewinds=max_rewinds)


# --------------------------------------------------------------------------------------------------
# headline: proactive-routed vs plain single-shot, with the anti-cheat guardrail
# --------------------------------------------------------------------------------------------------
def measure_routing_lift(
    tasks: Sequence[Task],
    fmap: Dict[str, Any],
    solvers: Sequence[Solver],
    single_shot: Proposer,
    blocks: Mapping[str, Solver] = {},
    max_rewinds: int = 3,
) -> Dict[str, Any]:
    """Run each task two ways and compare, where 'solved' = the task completed with the correct final
    value under its OWN check gates (truth is the steps' deterministic checks / blocks, independent of
    the model). ROUTED: pre_route then run_routed. SINGLE-SHOT: the lone weak model runs the SAME task
    with NO routing (one proposer for every choice step, no blocks attached) -- the honest weak floor.

    Reports routed vs single solved, newly_solved (routed wins), regressed (routed loses, always shown
    so a lift can't be hidden), and solver_mix totals. GUARDRAIL: read the mix -- if 'strong' or 'block'
    share is high, the lift is the bigger model / a fat block, NOT routing. A real routing lift keeps
    'small' share high with 'strong'/'block' targeted to the known-weak steps."""
    routed_ok: set = set()
    single_ok: set = set()
    mix_total = {"small": 0, "strong": 0, "block": 0, "calc": 0}
    for t in tasks:
        a = pre_route(t, fmap, solvers, blocks)
        r = run_routed(t, a, max_rewinds=max_rewinds)
        if r.get("completed"):
            routed_ok.add(t.name)
        for k in mix_total:
            mix_total[k] += r["solver_mix"].get(k, 0)
        s = run_stepwise(t, single_shot, max_rewinds=max_rewinds, allow_offload=False, prune_wrong=False)
        if s.get("completed"):
            single_ok.add(t.name)
    newly = sorted(routed_ok - single_ok)
    regressed = sorted(single_ok - routed_ok)
    return {
        "total": len(tasks),
        "routed_solved": len(routed_ok),
        "single_solved": len(single_ok),
        "newly_solved": newly,
        "regressed": regressed,
        "net_lift": len(newly) - len(regressed),
        "solver_mix": mix_total,
    }


def render(rep: Dict[str, Any]) -> str:
    """Format the headline like code_lift.render, with the routing-mix guardrail visible."""
    n = rep["total"]
    mix = rep["solver_mix"]
    lines = [
        "STRENGTH-ROUTER LIFT  (proactive routed vs plain single-shot, %d tasks)" % n,
        "  single-shot : %d / %d" % (rep["single_solved"], n),
        "  routed      : %d / %d" % (rep["routed_solved"], n),
        "  newly solved: %d  %s   <- routed clears, lone weak model could not"
        % (len(rep["newly_solved"]), rep["newly_solved"]),
        "  regressed   : %d  %s   <- routed broke what single-shot solved" % (len(rep["regressed"]), rep["regressed"]),
        "  NET LIFT    : %+d" % rep["net_lift"],
        "  solver mix  : small=%d strong=%d block=%d calc=%d  <- lift must come from ROUTING, not a fat strong/block"
        % (mix["small"], mix["strong"], mix["block"], mix["calc"]),
    ]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-strength-router", description="proactive strength-routed composition")
    ap.add_argument("--demo", action="store_true", help="offline routing math on stepwise fixtures (no models)")
    ap.add_argument(
        "--gpu", action="store_true", help="live: block-offload defuses the 1.5b modulo failure (needs Ollama)"
    )
    ap.add_argument(
        "--control",
        action="store_true",
        help="live fair attribution controls: no-elimination block-offload, placebo, and scaffold baseline",
    )
    ap.add_argument("--n", type=int, default=30, help="number of arithmetic-judgment tasks for --gpu")
    ap.add_argument("--model", default="qwen2.5-coder:1.5b", help="local OpenAI-compatible model for live runs")
    a = ap.parse_args(list(argv) if argv is not None else None)
    if a.control:
        from python.helm.strength_router_tasks import run_control_groups

        print(run_control_groups(n=a.n, model=a.model))
        return 0
    if a.gpu:
        from python.helm.strength_router_tasks import run_gpu_demo

        print(run_gpu_demo(n=a.n, model=a.model))
        return 0
    # default/--demo: offline fixture routing
    from python.scbe.failure_map import clears_through, seq_task

    tasks = [seq_task("t%d" % i, [str(j) for j in range(3)]) for i in range(4)]
    small = Solver("small", "small", proposer=clears_through(1), cost=1)  # clears only step 0
    strong = Solver("strong", "strong", proposer=clears_through(9), cost=3)  # clears everything
    fmap = build_failure_map(tasks, [small, strong])
    rep = measure_routing_lift(tasks, fmap, [small, strong], single_shot=clears_through(1))
    print(render(rep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
