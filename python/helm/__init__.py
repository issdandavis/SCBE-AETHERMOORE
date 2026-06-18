"""Helm — the operator loop: AI runs the reversible work, humans approve the gates.

    from python.helm import Step, run_objective, render

    steps = [
        Step("research", "research", lambda obj, ctx: f"notes on {obj}"),
        Step("build",    "build",    lambda obj, ctx: build_it(obj)),       # autonomous
        Step("verify",   "verify",   lambda obj, ctx: verify(ctx)),          # autonomous
        Step("deploy",   "deploy",   lambda obj, ctx: ship_to_prod(ctx)),    # GATED -> queued
        Step("charge",   "spend",    lambda obj, ctx: enable_billing()),     # GATED -> queued
    ]
    run = run_objective("ship the tool", steps)
    run.needs_human            # True — deploy + charge are queued
    print(render(run))
    # after you approve:
    run2 = run_objective("ship the tool", steps, approvals={"deploy"})  # deploy now executes

The loop runs everything reversible/low-stakes itself and parks money/deploy/legal/
destructive/admin steps for a human. Steps are pluggable callables, so codeforge
(build+verify), the governance gate, and shell/tools drop straight in.
"""

from .machine import (
    HUMAN_GATED_KINDS,
    Action,
    GateVerdict,
    OperatorRun,
    Receipt,
    Step,
    default_policy,
    render,
    run_objective,
)

__all__ = [
    "Step",
    "Action",
    "GateVerdict",
    "Receipt",
    "OperatorRun",
    "run_objective",
    "render",
    "default_policy",
    "HUMAN_GATED_KINDS",
]
