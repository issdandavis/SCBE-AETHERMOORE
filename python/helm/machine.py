"""Helm — the operator loop with criteria-based approval.

An objective comes in; for each step the AI checks the step's **approval criteria**.
**If the criteria are met, the step is approved and runs. That's it.** Approval is a
*procedure* (checkable rules), not a human clicking a queue — so the AI runs the whole
loop on its own, and a human's job is to *encode the criteria once*, not to approve
each action.

- A step with no criteria is unconditional (it just runs) — fine for low-stakes work.
- A risky step (deploy, spend, ...) carries criteria that must all pass, e.g.
  "the build verified" + "tests passed" + "within budget". Met -> it ships, autonomously.
- A genuinely human-gated action is just a criterion that checks a human-provided
  signal (``human("approved_deploy")``) — so human approval is *expressible* but not
  the default.

Every step is receipted into a tamper-evident chain. Steps and criteria are pluggable
callables, so codeforge (build+verify), the governance gate, and tools drop straight in.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# A step's action: (objective, context) -> result. Only called once the step is approved.
Action = Callable[[str, Dict[str, Any]], Any]
# A criterion check: (objective, context, step) -> bool | (bool, reason).
Check = Callable[[str, Dict[str, Any], "Step"], Any]


@dataclass
class Criterion:
    name: str
    check: Check

    def evaluate(self, objective: str, ctx: Dict[str, Any], step: "Step") -> Tuple[bool, str]:
        try:
            result = self.check(objective, ctx, step)
        except Exception as exc:  # a criterion that errors is treated as NOT met (fail safe)
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
    criteria: Tuple[Criterion, ...] = ()  # ALL must pass for the step to be approved + run
    note: str = ""


# ---- criteria builders (the common rules) -----------------------------------


def met(name: str, fn: Callable[[str, Dict[str, Any], "Step"], bool]) -> Criterion:
    """Approve when an arbitrary predicate of (objective, context, step) is true."""
    return Criterion(name, fn)


def flag(key: str) -> Criterion:
    """Approve when context[key] is truthy (a switch set upstream / in the initial context)."""
    return Criterion(f"flag:{key}", lambda obj, ctx, step: (bool(ctx.get(key)), f"context[{key!r}] not set"))


def human(key: str) -> Criterion:
    """A genuinely human-gated action: approve only when a human set context[key] truthy."""
    return Criterion(f"human:{key}", lambda obj, ctx, step: (bool(ctx.get(key)), "awaiting human signal"))


def upstream(step_name: str, key: str, equals: Any = True) -> Criterion:
    """Approve when an earlier step's result[key] == equals (e.g. build verified, tests passed)."""

    def check(obj: str, ctx: Dict[str, Any], step: "Step") -> Tuple[bool, str]:
        res = ctx.get("results", {}).get(step_name)
        if not isinstance(res, dict) or key not in res:
            return False, f"{step_name}.{key} missing"
        return res[key] == equals, f"{step_name}.{key}={res[key]!r} != {equals!r}"

    return Criterion(f"{step_name}.{key}=={equals}", check)


# ---- receipts + run ---------------------------------------------------------


@dataclass
class Receipt:
    step: str
    kind: str
    status: str  # approved | denied | failed
    chain: str
    criteria: List[Dict[str, Any]] = field(default_factory=list)  # [{name, passed, reason}]
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
    denied: List[Dict[str, Any]]  # steps whose criteria weren't met (with which failed)
    chain_digest: str
    approved: int
    denied_count: int
    failed: int

    @property
    def fully_autonomous(self) -> bool:
        """True if every step's criteria were met and it ran (nothing blocked or failed)."""
        return self.denied_count == 0 and self.failed == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective": self.objective,
            "chain_digest": self.chain_digest,
            "counts": {"approved": self.approved, "denied": self.denied_count, "failed": self.failed},
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


def run_objective(objective: str, steps: List[Step], context: Optional[Dict[str, Any]] = None) -> OperatorRun:
    """Run an objective. Each step is approved iff ALL its criteria pass; approved steps
    execute, denied steps are recorded (with which criterion failed) and skipped.

    Re-run with an updated ``context`` (or after upstream steps produce results) to let
    previously-denied steps clear their criteria — the same loop, driven by the rules.
    """
    ctx: Dict[str, Any] = {"objective": objective, "results": {}}
    ctx.update(context or {})
    ctx.setdefault("results", {})

    receipts: List[Receipt] = []
    denied: List[Dict[str, Any]] = []
    chain = _digest(["helm.v2", objective])
    approved = denied_count = failed = 0

    for step in steps:
        crit_rows, unmet = _evaluate(step, objective, ctx)

        if unmet:
            chain = _digest([chain, step.name, "denied"])
            reason = "criteria not met: " + ", ".join(unmet)
            receipts.append(Receipt(step.name, step.kind, "denied", chain, criteria=crit_rows, reason=reason))
            denied.append({"step": step.name, "kind": step.kind, "unmet": unmet, "note": step.note})
            denied_count += 1
            continue

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
        chain = _digest([chain, step.name, "approved", rd])
        receipts.append(Receipt(step.name, step.kind, "approved", chain, criteria=crit_rows, result_digest=rd))
        approved += 1

    return OperatorRun(
        objective=objective,
        receipts=receipts,
        results=ctx["results"],
        denied=denied,
        chain_digest=chain,
        approved=approved,
        denied_count=denied_count,
        failed=failed,
    )


def render(run: OperatorRun) -> str:
    """Human-readable run state: what cleared its criteria and ran, and what was denied."""
    glyph = {"approved": "✓", "denied": "✗", "failed": "!"}
    head = (
        f"helm · {run.objective!r} · {run.approved} approved"
        f"{f', {run.denied_count} denied' if run.denied_count else ''}"
        f"{f', {run.failed} failed' if run.failed else ''}"
        f"{' · FULLY AUTONOMOUS' if run.fully_autonomous else ''}"
        f" · chain {run.chain_digest}"
    )
    lines = [head]
    for r in run.receipts:
        mark = glyph.get(r.status, "?")
        tail = f"  ← {r.reason}" if r.reason else ""
        lines.append(f"  {mark} {r.step} ({r.kind}){tail}")
    return "\n".join(lines)
