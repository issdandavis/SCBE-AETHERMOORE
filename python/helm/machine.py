"""Helm: a receipted operator loop with checkable approval criteria.

Helm v1 gated steps by broad policy: reversible build/verify work ran, while
deploy/spend/legal/destructive/admin/credential work waited for a human approval.
Helm v2 keeps that API and adds criteria-based approval: a step can declare
machine-checkable criteria, and it runs only when every criterion passes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

Action = Callable[[str, Dict[str, Any]], Any]
Check = Callable[[str, Dict[str, Any], "Step"], Any]

HUMAN_GATED_KINDS = frozenset(
    {
        "spend",
        "deploy",
        "publish",
        "legal",
        "destructive",
        "admin",
        "credential",
        "email",
    }
)


@dataclass(frozen=True)
class CriterionDescriptor:
    """Structured criterion metadata for playability/static checking."""

    kind: str
    key: str = ""
    target: str = ""
    equals: Any = True


@dataclass
class Criterion:
    name: str
    check: Check
    descriptor: Optional[CriterionDescriptor] = None

    def evaluate(self, objective: str, ctx: Dict[str, Any], step: "Step") -> Tuple[bool, str]:
        try:
            result = self.check(objective, ctx, step)
        except Exception as exc:
            return False, f"criterion error: {type(exc).__name__}: {exc}"
        if isinstance(result, tuple):
            ok, reason = result
            return bool(ok), str(reason)
        return bool(result), ""


@dataclass
class Step:
    name: str
    kind: str
    do: Action
    criteria: Tuple[Criterion, ...] = ()
    reversible: bool = True
    note: str = ""


@dataclass
class GateVerdict:
    gated: bool
    reason: str = ""


def default_policy(step: Step) -> GateVerdict:
    """Conservative legacy policy for steps without explicit criteria."""
    if step.kind in HUMAN_GATED_KINDS:
        return GateVerdict(True, f"'{step.kind}' requires human approval")
    if not step.reversible:
        return GateVerdict(True, "irreversible action requires human approval")
    return GateVerdict(False)


def met(name: str, fn: Callable[[str, Dict[str, Any], Step], bool]) -> Criterion:
    return Criterion(name, fn, CriterionDescriptor(kind="predicate", key=name))


def flag(key: str) -> Criterion:
    return Criterion(
        f"flag:{key}",
        lambda obj, ctx, step: (bool(ctx.get(key)), f"context[{key!r}] not set"),
        CriterionDescriptor(kind="flag", key=key),
    )


def human(key: str) -> Criterion:
    return Criterion(
        f"human:{key}",
        lambda obj, ctx, step: (bool(ctx.get(key)), "awaiting human signal"),
        CriterionDescriptor(kind="human", key=key),
    )


def upstream(step_name: str, key: str, equals: Any = True) -> Criterion:
    def check(obj: str, ctx: Dict[str, Any], step: Step) -> Tuple[bool, str]:
        res = ctx.get("results", {}).get(step_name)
        if not isinstance(res, dict) or key not in res:
            return False, f"{step_name}.{key} missing"
        return res[key] == equals, f"{step_name}.{key}={res[key]!r} != {equals!r}"

    return Criterion(
        f"{step_name}.{key}=={equals}",
        check,
        CriterionDescriptor(kind="upstream", target=step_name, key=key, equals=equals),
    )


@dataclass
class Receipt:
    step: str
    kind: str
    status: str
    chain: str
    criteria: List[Dict[str, Any]] = field(default_factory=list)
    result_digest: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "kind": self.kind,
            "status": self.status,
            "chain": self.chain,
            "criteria": self.criteria,
            "result_digest": self.result_digest,
            "reason": self.reason,
        }


@dataclass
class OperatorRun:
    objective: str
    receipts: List[Receipt]
    results: Dict[str, Any]
    approval_queue: List[Dict[str, str]]
    chain_digest: str
    autonomous_done: int = 0
    approved_done: int = 0
    pending_approval: int = 0
    failed: int = 0
    denied: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def approved(self) -> int:
        return self.autonomous_done + self.approved_done

    @property
    def denied_count(self) -> int:
        return self.pending_approval + len(self.denied)

    @property
    def needs_human(self) -> bool:
        return self.pending_approval > 0

    @property
    def fully_autonomous(self) -> bool:
        return self.denied_count == 0 and self.failed == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective": self.objective,
            "chain_digest": self.chain_digest,
            "counts": {
                "autonomous_done": self.autonomous_done,
                "approved_done": self.approved_done,
                "approved": self.approved,
                "pending_approval": self.pending_approval,
                "denied": self.denied_count,
                "failed": self.failed,
            },
            "approval_queue": self.approval_queue,
            "denied": self.denied,
            "receipts": [r.to_dict() for r in self.receipts],
        }


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def _evaluate(step: Step, objective: str, ctx: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    rows: List[Dict[str, Any]] = []
    unmet: List[str] = []
    for crit in step.criteria:
        ok, reason = crit.evaluate(objective, ctx, step)
        rows.append({"name": crit.name, "passed": ok, "reason": "" if ok else reason})
        if not ok:
            unmet.append(crit.name)
    return rows, unmet


def run_objective(
    objective: str,
    steps: List[Step],
    context: Optional[Dict[str, Any]] = None,
    policy: Callable[[Step], GateVerdict] = default_policy,
    approvals: Optional[set] = None,
) -> OperatorRun:
    """Run steps sequentially.

    Steps with explicit criteria use the v2 rule: all criteria must pass. Steps
    without explicit criteria use the v1 policy/approval queue behavior.
    """

    approved_names = set(approvals or set())
    ctx: Dict[str, Any] = {"objective": objective, "results": {}}
    ctx.update(context or {})
    ctx.setdefault("results", {})

    receipts: List[Receipt] = []
    queue: List[Dict[str, str]] = []
    denied: List[Dict[str, Any]] = []
    chain = _digest(["helm.v2", objective])
    auto_done = appr_done = pending = failed = 0

    for step in steps:
        if step.criteria:
            crit_rows, unmet = _evaluate(step, objective, ctx)
            if unmet:
                chain = _digest([chain, step.name, "denied"])
                reason = "criteria not met: " + ", ".join(unmet)
                receipts.append(Receipt(step.name, step.kind, "denied", chain, criteria=crit_rows, reason=reason))
                denied.append({"step": step.name, "kind": step.kind, "unmet": unmet, "note": step.note})
                continue
            was_gated = False
            status = "approved"
        else:
            crit_rows = []
            verdict = policy(step)
            if verdict.gated and step.name not in approved_names:
                chain = _digest([chain, step.name, "pending-approval"])
                receipts.append(Receipt(step.name, step.kind, "pending-approval", chain, reason=verdict.reason))
                queue.append({"step": step.name, "kind": step.kind, "reason": verdict.reason, "note": step.note})
                pending += 1
                continue
            was_gated = verdict.gated
            status = "approved-done" if was_gated else "done"

        try:
            result = step.do(objective, ctx)
        except Exception as exc:
            chain = _digest([chain, step.name, "failed"])
            receipts.append(
                Receipt(
                    step.name, step.kind, "failed", chain, criteria=crit_rows, reason=f"{type(exc).__name__}: {exc}"
                )
            )
            failed += 1
            continue

        rd = _digest(result)
        ctx["results"][step.name] = result
        chain = _digest([chain, step.name, status, rd])
        receipts.append(Receipt(step.name, step.kind, status, chain, criteria=crit_rows, result_digest=rd))
        if was_gated:
            appr_done += 1
        else:
            auto_done += 1

    return OperatorRun(
        objective=objective,
        receipts=receipts,
        results=ctx["results"],
        approval_queue=queue,
        chain_digest=chain,
        autonomous_done=auto_done,
        approved_done=appr_done,
        pending_approval=pending,
        failed=failed,
        denied=denied,
    )


def render(run: OperatorRun) -> str:
    glyph = {
        "approved": "OK",
        "done": "OK",
        "approved-done": "OK+",
        "pending-approval": "WAIT",
        "denied": "XX",
        "failed": "!!",
    }
    head = (
        f"helm * {run.objective!r} * {run.approved} approved"
        f"{f', {run.denied_count} denied' if run.denied_count else ''}"
        f"{f', {run.pending_approval} AWAITING YOU' if run.pending_approval else ''}"
        f"{f', {run.failed} failed' if run.failed else ''}"
        f"{' * FULLY AUTONOMOUS' if run.fully_autonomous else ''}"
        f" * chain {run.chain_digest}"
    )
    lines = [head]
    for r in run.receipts:
        mark = glyph.get(r.status, "?")
        tail = f"  <- {r.reason}" if r.reason else ""
        lines.append(f"  [{mark}] {r.step} ({r.kind}){tail}")
    if run.approval_queue:
        lines.append("\nAPPROVAL QUEUE (clear these and re-run with their names approved):")
        for q in run.approval_queue:
            lines.append(f"  - {q['step']} - {q['reason']}" + (f" - {q['note']}" if q["note"] else ""))
    return "\n".join(lines)
