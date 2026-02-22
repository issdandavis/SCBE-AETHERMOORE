"""
Concept Blocks — Telemetry
==========================

Unified telemetry format shared across all concept blocks.
Every block tick produces a TelemetryRecord that can be logged,
queried, and bridged into the SCBE 21D state vector.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TelemetryRecord:
    """Single telemetry event from a concept block tick."""

    block_name: str
    timestamp: float = field(default_factory=time.time)
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    status: str = "ok"
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block": self.block_name,
            "ts": self.timestamp,
            "in": self.inputs,
            "out": self.outputs,
            "status": self.status,
            "dur_ms": self.duration_ms,
            "meta": self.metadata,
        }


class TelemetryLog:
    """Append-only telemetry log with query helpers."""

    def __init__(self, max_records: int = 10_000) -> None:
        self._records: List[TelemetryRecord] = []
        self._max = max_records

    def append(self, record: TelemetryRecord) -> None:
        self._records.append(record)
        if len(self._records) > self._max:
            self._records = self._records[-self._max:]

    def query(
        self,
        block_name: Optional[str] = None,
        since: Optional[float] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[TelemetryRecord]:
        out: List[TelemetryRecord] = []
        for r in reversed(self._records):
            if block_name and r.block_name != block_name:
                continue
            if since and r.timestamp < since:
                break
            if status and r.status != status:
                continue
            out.append(r)
            if len(out) >= limit:
                break
        return list(reversed(out))

    def summary(self) -> Dict[str, Any]:
        by_block: Dict[str, int] = {}
        errors = 0
        for r in self._records:
            by_block[r.block_name] = by_block.get(r.block_name, 0) + 1
            if r.status != "ok":
                errors += 1
        return {
            "total": len(self._records),
            "by_block": by_block,
            "errors": errors,
        }

    def __len__(self) -> int:
        return len(self._records)
