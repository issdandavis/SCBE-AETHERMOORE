"""Training Pad — session orchestrator.

Ties together the triple sandbox: cells (inner), life guard (middle),
deployment membrane (outer). Manages a coding session and exports
training data from every action.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .cell import Cell, CellStatus
from .sandbox import Sandbox, ExecutionResult
from .lifeguard import LifeGuard, LifeGuardNote
from .membrane import DeploymentMembrane, MembraneResult, Decision
from .sft_recorder import cell_to_sft_records, export_pad_session


DEFAULT_OUTPUT = Path(__file__).parent.parent.parent / "training-data" / "sft" / "training_pad_sessions.jsonl"


@dataclass
class PadSession:
    """A single training pad session — Polly's trip to the beach."""

    session_id: str = ""
    cells: dict[str, Cell] = field(default_factory=dict)
    sandbox: Sandbox = field(default_factory=Sandbox)
    lifeguard: LifeGuard = field(default_factory=LifeGuard)
    membrane: DeploymentMembrane = field(default_factory=DeploymentMembrane)
    started_at: float = field(default_factory=time.time)
    exports: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.session_id:
            self.session_id = f"pad-{int(self.started_at)}"


class TrainingPad:
    """The Training Pad — Polly's sandbox coding environment.

    Usage:
        pad = TrainingPad()
        session = pad.new_session()

        # Polly writes code
        cell = pad.create_cell(session, tongue="CA", language="python")
        pad.write(session, cell.cell_id, "def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)")

        # Execute it
        result = pad.run(session, cell.cell_id)

        # Life guard watches
        notes = pad.observe(session, cell.cell_id)

        # Try to export
        membrane_result = pad.release(session, cell.cell_id)

        # Save training data
        pad.save_session(session)
    """

    def __init__(self, output_path: str | Path = DEFAULT_OUTPUT):
        self.output_path = Path(output_path)
        self.sessions: dict[str, PadSession] = {}

    def new_session(self, session_id: str = "") -> PadSession:
        """Create a new training pad session."""
        session = PadSession(session_id=session_id)
        self.sessions[session.session_id] = session
        return session

    def create_cell(
        self,
        session: PadSession,
        tongue: str = "CA",
        language: str = "python",
    ) -> Cell:
        """Create a new cell in the session."""
        cell = Cell(tongue=tongue, language=language)
        session.cells[cell.cell_id] = cell
        return cell

    def write(self, session: PadSession, cell_id: str, code: str) -> Cell:
        """Write code to a cell."""
        cell = session.cells[cell_id]
        cell.write(code)
        return cell

    def connect(self, session: PadSession, from_id: str, to_id: str) -> None:
        """Connect two cells — from_id imports to_id."""
        cell = session.cells[from_id]
        cell.add_import(to_id)

    def run(self, session: PadSession, cell_id: str) -> ExecutionResult:
        """Execute a cell in the inner sandbox."""
        cell = session.cells[cell_id]
        result = session.sandbox.execute(cell)

        # Life guard reviews execution results
        session.lifeguard.review_execution(
            cell,
            stdout=result.stdout,
            stderr=result.stderr,
            success=result.success,
        )

        return result

    def observe(self, session: PadSession, cell_id: str) -> list[LifeGuardNote]:
        """Have the life guard observe a cell's code."""
        cell = session.cells[cell_id]
        return session.lifeguard.observe(cell)

    def release(self, session: PadSession, cell_id: str) -> MembraneResult:
        """Try to release a cell through the deployment membrane."""
        cell = session.cells[cell_id]
        result = session.membrane.evaluate(cell)

        if result.decision == Decision.ALLOW:
            exported = session.membrane.export(cell)
            if exported:
                session.exports.append(exported)

        return result

    def run_and_release(self, session: PadSession, cell_id: str) -> tuple[ExecutionResult, list[LifeGuardNote], MembraneResult]:
        """Full pipeline: observe → run → observe again → membrane check."""
        # Pre-run observation
        pre_notes = self.observe(session, cell_id)

        # Execute
        exec_result = self.run(session, cell_id)

        # Post-run observation
        post_notes = self.observe(session, cell_id)

        # Membrane check
        membrane_result = self.release(session, cell_id)

        return exec_result, pre_notes + post_notes, membrane_result

    def save_session(self, session: PadSession, output_path: str | Path | None = None) -> int:
        """Export session training data to JSONL."""
        path = Path(output_path) if output_path else self.output_path
        cells = list(session.cells.values())
        return export_pad_session(cells, path, append=True)

    def session_summary(self, session: PadSession) -> dict[str, Any]:
        """Get a summary of the session."""
        cells = list(session.cells.values())
        return {
            "session_id": session.session_id,
            "cell_count": len(cells),
            "passed": sum(1 for c in cells if c.status == CellStatus.PASS),
            "failed": sum(1 for c in cells if c.status == CellStatus.FAIL),
            "untested": sum(1 for c in cells if c.status == CellStatus.UNTESTED),
            "total_events": sum(len(c.history) for c in cells),
            "exports": len(session.exports),
            "languages": list(set(c.language for c in cells)),
            "tongues": list(set(c.tongue for c in cells)),
        }
