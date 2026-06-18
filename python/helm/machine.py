"""Helm — the operator loop.

An objective comes in; the AI runs every **reversible, low-stakes** step on its
own, and **parks the human-gated steps** (spend money, deploy, sign/legal, anything
destructive or irreversible, admin/credential access) in an **approval queue** for
a human to clear. The AI runs the 90%; you approve the 10% that law and security
require a human for.

Why it's built this way: there is an irreducible set of actions no autonomous agent
can (or should) take alone — paying money needs a human's identity, deploying to
prod needs a human's "ship it", and some approvals are literally a human-only click
(the Windows UAC prompt is the canonical example). Helm runs everything up to those
gates and surfaces them as a short, explicit queue.

Each step is receipted into a tamper-evident chain, so the run is auditable. Steps
are pluggable callables, so the real work (codeforge to build, the gate to verify,
shell/tools to act) drops in as the step's action — the loop itself stays
deterministic and testable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

# A step's action does the work: (objective, context) -> result.
Action = Callable[[str, Dict[str, Any]], Any]

# Kinds that ALWAYS require a human approval (by law / security / irreversibility).
HUMAN_GATED_KINDS = frozenset(
    {
        "spend",  # money / payments / payouts (needs a human's identity)
        "deploy",  # ship to prod / external infra
        "publish",  # post publicly / send to customers
        "legal",  # sign, accept terms, accept liability
        "destructive",  # delete / overwrite / wipe
        "admin",  # elevated / system / UAC-gated
        "credential",  # create or hand out secrets/keys
        "email",  # send mail on someone's behalf
    }
)


@dataclass
class Step:
    name: str
    kind: str  # "build" | "verify" | "draft" | "research" | "deploy" | "spend" | ...
    do: Action  # the action; only called when the step is autonomous OR approved
    reversible: bool = True
    note: str = ""


@dataclass
class GateVerdict:
    gated: bool
    reason: str = ""


def default_policy(step: Step) -> GateVerdict:
    """Conservative default: gate anything that costs money, ships, is irreversible,
    or needs elevated/legal authority. Everything else the AI may do on its own."""
    if step.kind in HUMAN_GATED_KINDS:
        return GateVerdict(True, f"'{step.kind}' requires human approval")
    if not step.reversible:
        return GateVerdict(True, "irreversible action requires human approval")
    return GateVerdict(False)


@dataclass
class Receipt:
    step: str
    kind: str
    status: str  # done | pending-approval | approved-done | failed
    chain: str
    result_digest: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "kind": self.kind,
            "status": self.status,
            "chain": self.chain,
            "result_digest": self.result_digest,
            "reason": self.reason,
        }


@dataclass
class OperatorRun:
    objective: str
    receipts: List[Receipt]
    results: Dict[str, Any]  # outputs of completed steps (autonomous + approved)
    approval_queue: List[Dict[str, str]]  # gated steps awaiting a human
    chain_digest: str
    autonomous_done: int
    approved_done: int
    pending_approval: int
    failed: int

    @property
    def needs_human(self) -> bool:
        return self.pending_approval > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective": self.objective,
            "chain_digest": self.chain_digest,
            "counts": {
                "autonomous_done": self.autonomous_done,
                "approved_done": self.approved_done,
                "pending_approval": self.pending_approval,
                "failed": self.failed,
            },
            "approval_queue": self.approval_queue,
            "receipts": [r.to_dict() for r in self.receipts],
        }


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def run_objective(
    objective: str,
    steps: List[Step],
    policy: Callable[[Step], GateVerdict] = default_policy,
    approvals: Optional[set] = None,
) -> OperatorRun:
    """Run an objective. Autonomous steps execute; gated steps are queued unless their
    name is in ``approvals`` (a human's go-ahead), in which case they execute too.

    Re-run with a growing ``approvals`` set to model the human-in-the-loop: first run
    parks the gates; after the human approves some, re-run and those gates execute.
    """
    approved = set(approvals or set())
    context: Dict[str, Any] = {"objective": objective, "results": {}}
    receipts: List[Receipt] = []
    queue: List[Dict[str, str]] = []
    chain = _digest(["helm.v1", objective])
    auto_done = appr_done = pending = failed = 0

    for step in steps:
        verdict = policy(step)
        if verdict.gated and step.name not in approved:
            chain = _digest([chain, step.name, "pending-approval"])
            receipts.append(Receipt(step.name, step.kind, "pending-approval", chain, reason=verdict.reason))
            queue.append({"step": step.name, "kind": step.kind, "reason": verdict.reason, "note": step.note})
            pending += 1
            continue

        was_gated = verdict.gated  # gated-but-approved vs ordinary autonomous
        try:
            result = step.do(objective, context)
        except Exception as exc:  # one step failing must not abort the operator
            chain = _digest([chain, step.name, "failed"])
            receipts.append(Receipt(step.name, step.kind, "failed", chain, reason=f"{type(exc).__name__}: {exc}"))
            failed += 1
            continue

        rd = _digest(result)
        context["results"][step.name] = result
        status = "approved-done" if was_gated else "done"
        chain = _digest([chain, step.name, status, rd])
        receipts.append(Receipt(step.name, step.kind, status, chain, result_digest=rd))
        if was_gated:
            appr_done += 1
        else:
            auto_done += 1

    return OperatorRun(
        objective=objective,
        receipts=receipts,
        results=context["results"],
        approval_queue=queue,
        chain_digest=chain,
        autonomous_done=auto_done,
        approved_done=appr_done,
        pending_approval=pending,
        failed=failed,
    )


def render(run: OperatorRun) -> str:
    """Human-readable run state: what the AI did, and the queue waiting on you."""
    glyph = {"done": "✓", "approved-done": "✓+", "pending-approval": "⏸", "failed": "✗"}
    head = (
        f"helm · {run.objective!r} · {run.autonomous_done} auto-done"
        f"{f', {run.approved_done} approved' if run.approved_done else ''}"
        f"{f', {run.failed} failed' if run.failed else ''}"
        f"{f', {run.pending_approval} AWAITING YOU' if run.pending_approval else ''}"
        f" · chain {run.chain_digest}"
    )
    lines = [head]
    for r in run.receipts:
        mark = glyph.get(r.status, "?")
        tail = f"  ← {r.reason}" if r.reason else ""
        lines.append(f"  {mark} {r.step} ({r.kind}){tail}")
    if run.approval_queue:
        lines.append("\nAPPROVAL QUEUE (clear these and re-run with their names approved):")
        for q in run.approval_queue:
            lines.append(f"  • {q['step']} — {q['reason']}" + (f" — {q['note']}" if q["note"] else ""))
    return "\n".join(lines)
