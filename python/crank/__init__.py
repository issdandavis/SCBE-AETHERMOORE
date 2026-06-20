"""Crank — turn long AI work into a visible workflow machine.

Intent in -> controlled, checkpointed steps -> a cataloged result with receipts.
Borrowed from a mechanical calculator: a result is only real once every step has
settled into a constrained, receipted state (no in-between), and the catalog (the
receipt chain) is the proof.

    from python.crank import Phase, turn, render

    phases = [
        Phase("research", lambda intent, ctx: f"notes about: {intent}"),
        Phase("build",    lambda intent, ctx: f"impl for: {intent}"),
        Phase("review",   lambda intent, ctx: f"reviewed: {ctx['outputs']['build']}"),
        Phase("deliver",  lambda intent, ctx: {"artifact": ctx["outputs"]["build"], "status": "shipped"}),
    ]
    cat = turn("add a numfind tool", phases)
    cat.ok            # True
    cat.chain_digest  # tamper-evident proof of the whole run
    print(render(cat))

Failure modes are surfaced, not hidden: a phase that produces nothing is *drift*,
a gate refusal is *blocked*, and a phase that merely echoes an earlier one is a
*collision* (no progress). Real executors (an AI call, a loom build+verify, a
governance gate) plug in as the phase functions and the gate.
"""

from .machine import (
    Catalog,
    GateFn,
    GateVerdict,
    Phase,
    PhaseFn,
    Receipt,
    default_gate,
    render,
    turn,
)

__all__ = [
    "Phase",
    "PhaseFn",
    "GateFn",
    "GateVerdict",
    "Receipt",
    "Catalog",
    "turn",
    "render",
    "default_gate",
]
