"""Deployment Membrane — outer sandbox gate.

Only valid, build-tested code exits. Everything else stays
as training data. The shoreline where the ocean meets the sand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .cell import Cell, CellStatus


class Decision(str, Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    DENY = "DENY"


@dataclass
class MembraneResult:
    """Result of membrane evaluation."""

    decision: Decision
    reason: str
    cell_id: str
    code: str = ""
    warnings: list[str] = field(default_factory=list)


class DeploymentMembrane:
    """Outer sandbox — the final gate.

    Evaluates whether a cell's code can be exported for production use.
    Code must: pass execution, have no critical security findings,
    and pass the governance check.
    """

    def __init__(self, require_tests: bool = False, max_critical: int = 0, max_warnings: int = 5):
        self.require_tests = require_tests
        self.max_critical = max_critical
        self.max_warnings = max_warnings

    def evaluate(self, cell: Cell) -> MembraneResult:
        """Evaluate a cell for deployment readiness."""

        # Must have been executed successfully
        if cell.status != CellStatus.PASS:
            return MembraneResult(
                decision=Decision.DENY,
                reason=f"Cell status is {cell.status.value} — must pass execution first",
                cell_id=cell.cell_id,
            )

        # Check for critical security findings
        critical_count = sum(
            1 for f in cell.feedback
            if f.get("severity") == "critical"
        )
        if critical_count > self.max_critical:
            return MembraneResult(
                decision=Decision.DENY,
                reason=f"{critical_count} critical security findings — fix before deployment",
                cell_id=cell.cell_id,
                warnings=[f.get("message", "") for f in cell.feedback if f.get("severity") == "critical"],
            )

        # Check warning count
        warn_count = sum(
            1 for f in cell.feedback
            if f.get("severity") in ("warn", "error")
        )
        warnings = [f.get("message", "") for f in cell.feedback if f.get("severity") in ("warn", "error")]

        if warn_count > self.max_warnings:
            return MembraneResult(
                decision=Decision.QUARANTINE,
                reason=f"{warn_count} warnings exceed threshold ({self.max_warnings}) — review recommended",
                cell_id=cell.cell_id,
                code=cell.code,
                warnings=warnings,
            )

        # Must have been run at least once (not just written)
        run_events = [e for e in cell.history if e.event_type.value == "run"]
        if not run_events:
            return MembraneResult(
                decision=Decision.DENY,
                reason="Code was never executed — run it first",
                cell_id=cell.cell_id,
            )

        # ALLOW — code is clean and passes
        return MembraneResult(
            decision=Decision.ALLOW,
            reason="Code passes execution and security review",
            cell_id=cell.cell_id,
            code=cell.code,
            warnings=warnings,
        )

    def export(self, cell: Cell) -> dict[str, Any] | None:
        """Export cell code if it passes the membrane. Returns None if blocked."""
        result = self.evaluate(cell)
        if result.decision == Decision.ALLOW:
            return {
                "cell_id": cell.cell_id,
                "tongue": cell.tongue,
                "language": cell.language,
                "code": cell.code,
                "outputs": cell.outputs,
                "decision": result.decision.value,
            }
        return None
