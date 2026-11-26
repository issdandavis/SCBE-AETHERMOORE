# Helm — the operator loop

**An objective comes in; the AI runs the reversible work itself and parks the human-gated steps in an approval queue.** The realization of "let the AI run the whole thing" — honestly scoped: the AI runs the ~90% that's reversible and low-stakes, and a human clears the ~10% that law and security require a human for.

Standalone (stdlib only). Steps are pluggable callables, so the real work plugs straight in: **codeforge** (build + verify), the **governance gate** (safe-to-act), `crank` (receipted sub-runs), shell/tools.

## Try it

```bash
python -m python.helm.demo
python -m python.helm.tool_forge_demo
python -m python.helm.tool_forge_bench
```

The demo is side-effect free. It shows static playability checking, dry-run proof without calling real step bodies, concurrent DAG execution, storylet selection from derived factors, and a broken graph caught before execution.

`tool_forge_demo` shows the agent-as-tool-maker loop: propose a tiny tool, intentionally fail verification once, repair it, verify again, and keep the working tool plus a receipt in a temp workspace.

`tool_forge_bench` turns that loop into a small local benchmark: four tool-making tasks, public examples, hidden checks, repair, kept tools, and per-task JSON receipts. It is not a claim to beat SWE-bench or Terminal-Bench; it measures the thing those benchmarks still leave thinly covered: whether an agent can create a new tool, verify it, repair it, and reuse the verified artifact.

## What's gated vs autonomous
The default policy parks a step for human approval if its kind is **spend / deploy / publish / legal / destructive / admin / credential / email**, *or* if it's flagged **irreversible**. Everything else (`build`, `verify`, `research`, `draft`, `edit`, …) the AI runs on its own.

Why: paying money needs a human's identity (KYC); shipping to prod needs a human's "ship it"; some approvals are a human-only click (the Windows UAC prompt is the canonical case). Helm runs everything up to those gates.

## Use
```python
from python.helm import Step, run_objective, render

steps = [
    Step("research", "research", lambda obj, ctx: f"notes on {obj}"),
    Step("build",    "build",    lambda obj, ctx: ctx),          # autonomous
    Step("verify",   "verify",   lambda obj, ctx: ctx),          # autonomous
    Step("deploy",   "deploy",   lambda obj, ctx: ship(ctx)),    # GATED -> queued
    Step("charge",   "spend",    lambda obj, ctx: billing()),    # GATED -> queued
]

run = run_objective("ship the tool", steps)
run.needs_human          # True
print(render(run))       # shows what ran + the queue waiting on you

# after you approve a gated step, re-run with its name approved -> it executes:
run2 = run_objective("ship the tool", steps, approvals={"deploy"})
```

## Properties
- **The gates actually hold:** a gated step's action is *never called* until it's in `approvals`. Tests prove the side-effects don't fire.
- **Auditable:** every step is receipted into a tamper-evident chain (`chain_digest`); same objective + steps → same chain.
- **Resilient:** an autonomous step that raises is recorded `failed` and the loop continues.
- **Human-in-the-loop:** re-run with a growing `approvals` set; parked gates execute once approved.

## Composes with the rest
A `build` step can be `codeforge.forge(objective)` (AI writes + verifies code, refuses unverified); a `verify` step can run the governance gate; `deploy`/`spend` stay gated. That's the operator: the AI drives the build→verify loop autonomously and only taps you for the money/ship/legal gates.
