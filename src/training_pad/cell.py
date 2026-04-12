"""Executable cell model for training pad review tooling."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class CellStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    RAN = "ran"
    FAILED = "failed"


@dataclass
class Cell:
    code: str = ""
    language: str = "python"
    status: CellStatus = CellStatus.DRAFT
    feedback: List[dict] = field(default_factory=list)

    def add_feedback(self, note: dict) -> None:
        self.feedback.append(note)
