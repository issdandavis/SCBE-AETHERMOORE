"""
Concept Blocks — Base
=====================

Abstract base class for all concept blocks.  Every block follows the
same tick/reset/configure lifecycle so they can be composed, swapped,
and telemetry-logged uniformly.

Block lifecycle:
    1. configure(params)   — set tunable parameters
    2. tick(inputs) -> BlockResult   — one execution step
    3. reset()             — return to initial state
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from .telemetry import TelemetryLog, TelemetryRecord


class BlockStatus(Enum):
    """Outcome of a single tick."""
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


@dataclass
class BlockResult:
    """Value returned by every block tick."""
    status: BlockStatus
    output: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


class ConceptBlock(ABC):
    """Abstract concept block — the atom of the navigation stack."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._telemetry = TelemetryLog()
        self._tick_count = 0

    # -- public API ----------------------------------------------------------

    def tick(self, inputs: Dict[str, Any]) -> BlockResult:
        """Execute one step and log telemetry."""
        t0 = time.perf_counter()
        result = self._do_tick(inputs)
        dur = (time.perf_counter() - t0) * 1000.0
        self._tick_count += 1
        self._telemetry.append(TelemetryRecord(
            block_name=self.name,
            inputs=inputs,
            outputs=result.output,
            status=result.status.value,
            duration_ms=dur,
        ))
        return result

    def configure(self, params: Dict[str, Any]) -> None:
        """Update tunable parameters.  Override for validation."""
        self._do_configure(params)

    def reset(self) -> None:
        """Return block to initial state."""
        self._tick_count = 0
        self._do_reset()

    @property
    def telemetry(self) -> TelemetryLog:
        return self._telemetry

    # -- subclass hooks ------------------------------------------------------

    @abstractmethod
    def _do_tick(self, inputs: Dict[str, Any]) -> BlockResult:
        ...

    def _do_configure(self, params: Dict[str, Any]) -> None:
        """Override to accept runtime parameter changes."""

    def _do_reset(self) -> None:
        """Override to clear internal state."""
