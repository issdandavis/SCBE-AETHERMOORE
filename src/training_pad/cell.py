"""Cell model — the fundamental unit of the Training Pad.

Each cell is a self-contained code unit. Cells connect via imports,
forming dependency graphs (mini constellations). Every action on a
cell is recorded as a CellEvent for SFT training data generation.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class CellStatus(str, Enum):
    UNTESTED = "untested"
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"


class EventType(str, Enum):
    WRITE = "write"
    RUN = "run"
    FAIL = "fail"
    FIX = "fix"
    IMPORT = "import"
    FEEDBACK = "feedback"


@dataclass
class CellEvent:
    """A single action on a cell — the atomic training signal."""

    event_type: EventType
    timestamp: float = field(default_factory=time.time)
    code_snapshot: str = ""
    stdout: str = ""
    stderr: str = ""
    error: str = ""
    feedback_notes: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        return d


@dataclass
class Cell:
    """A code cell in the Training Pad.

    Tongue sets intent (KO=dispatch, CA=compute, UM=secure, etc).
    Language is independent — Python, Rust, TypeScript, SQL, whatever fits.
    """

    cell_id: str = ""
    tongue: str = "CA"
    language: str = "python"
    code: str = ""
    imports: list[str] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)
    history: list[CellEvent] = field(default_factory=list)
    status: CellStatus = CellStatus.UNTESTED
    feedback: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.cell_id:
            self.cell_id = self._generate_id()

    def _generate_id(self) -> str:
        seed = f"{self.tongue}-{time.time()}-{id(self)}"
        return f"cell-{hashlib.sha256(seed.encode()).hexdigest()[:8]}"

    def write(self, code: str) -> CellEvent:
        """Record a write/edit action."""
        is_fix = self.status == CellStatus.FAIL and self.code != ""
        event_type = EventType.FIX if is_fix else EventType.WRITE
        self.code = code
        event = CellEvent(
            event_type=event_type,
            code_snapshot=code,
        )
        self.history.append(event)
        self.status = CellStatus.UNTESTED
        return event

    def record_run(self, stdout: str = "", stderr: str = "", return_value: Any = None) -> CellEvent:
        """Record a successful execution."""
        self.status = CellStatus.PASS
        self.outputs["stdout"] = stdout
        self.outputs["stderr"] = stderr
        if return_value is not None:
            self.outputs["return_value"] = return_value
        event = CellEvent(
            event_type=EventType.RUN,
            code_snapshot=self.code,
            stdout=stdout,
            stderr=stderr,
        )
        self.history.append(event)
        return event

    def record_fail(self, error: str, stderr: str = "") -> CellEvent:
        """Record a failed execution."""
        self.status = CellStatus.FAIL
        event = CellEvent(
            event_type=EventType.FAIL,
            code_snapshot=self.code,
            stderr=stderr,
            error=error,
        )
        self.history.append(event)
        return event

    def record_feedback(self, notes: list[dict]) -> CellEvent:
        """Record life guard feedback."""
        self.feedback.extend(notes)
        event = CellEvent(
            event_type=EventType.FEEDBACK,
            code_snapshot=self.code,
            feedback_notes=notes,
        )
        self.history.append(event)
        return event

    def add_import(self, cell_id: str) -> CellEvent:
        """Record importing from another cell."""
        if cell_id not in self.imports:
            self.imports.append(cell_id)
        event = CellEvent(
            event_type=EventType.IMPORT,
            metadata={"imported_cell": cell_id},
        )
        self.history.append(event)
        return event

    def to_dict(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "tongue": self.tongue,
            "language": self.language,
            "code": self.code,
            "imports": self.imports,
            "outputs": self.outputs,
            "history": [e.to_dict() for e in self.history],
            "status": self.status.value,
            "feedback": self.feedback,
        }
