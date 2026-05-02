"""
Packet Ledger
=============

Dedup cache for AgentPacketV1. When the same packet is presented again
(same state_hash + request + route + expected_output), the prior
MergeReport can be returned directly instead of fanning to the model
pair. This is the "do-not-repeat-known-context" rule from the packet
protocol pivot.

The ledger is a content-addressed cache keyed by a fingerprint of the
packet's *intent*, not its task_id. Two packets with different task_ids
but identical work hit the same ledger entry — that's the point.

@module agent_comms/ledger
@layer L13 (Risk decision)
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from .packet import AgentPacketV1, MergeReport


def fingerprint(packet: AgentPacketV1) -> str:
    """
    Deterministic fingerprint of packet *intent*.

    Excludes task_id and created_at — two packets with different task_ids
    but identical work are deliberately the same fingerprint.
    """
    h = hashlib.sha256()
    h.update(packet.state_hash.encode("utf-8"))
    h.update(b"\x00")
    h.update(packet.route.tongue.encode("utf-8"))
    h.update(b"\x00")
    h.update(packet.route.domain.encode("utf-8"))
    h.update(b"\x00")
    h.update(packet.route.permission.encode("utf-8"))
    h.update(b"\x00")
    h.update(packet.phase.encode("utf-8"))
    h.update(b"\x00")
    h.update(packet.expected_output.encode("utf-8"))
    h.update(b"\x00")
    h.update(packet.request.encode("utf-8"))
    h.update(b"\x00")
    for ref in sorted(packet.context_refs, key=lambda r: (r.kind, r.value)):
        h.update(ref.kind.encode("utf-8"))
        h.update(b":")
        h.update(ref.value.encode("utf-8"))
        h.update(b"\x00")
    return f"pkt:{h.hexdigest()[:32]}"


@dataclass
class LedgerEntry:
    fingerprint: str
    report: Dict[str, Any]
    recorded_at: float
    hits: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "report": self.report,
            "recorded_at": self.recorded_at,
            "hits": self.hits,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LedgerEntry":
        return cls(
            fingerprint=data["fingerprint"],
            report=data["report"],
            recorded_at=data.get("recorded_at", time.time()),
            hits=data.get("hits", 0),
        )


class PacketLedger:
    """
    Bounded LRU cache mapping packet fingerprint -> prior MergeReport.

    Thread-safe. Optional JSONL persistence: pass `path=` to load existing
    entries and append-write on every record(). Promote-only entries are
    persisted when ``promoted_only=True`` (default), so holds and rejects
    are not cached and will be re-tried.
    """

    def __init__(
        self,
        *,
        max_entries: int = 256,
        path: Optional[Path] = None,
        promoted_only: bool = True,
    ) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be > 0")
        self._max = max_entries
        self._path = Path(path) if path is not None else None
        self._promoted_only = promoted_only
        self._entries: "OrderedDict[str, LedgerEntry]" = OrderedDict()
        self._lock = Lock()
        if self._path is not None and self._path.is_file():
            self._load()

    def _load(self) -> None:
        assert self._path is not None
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = LedgerEntry.from_dict(json.loads(line))
                except (json.JSONDecodeError, KeyError):
                    continue
                self._entries[entry.fingerprint] = entry
                if len(self._entries) > self._max:
                    self._entries.popitem(last=False)

    def _persist(self, entry: LedgerEntry) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict(), sort_keys=True))
            fh.write("\n")

    def seen(self, packet: AgentPacketV1) -> Optional[MergeReport]:
        """Return prior MergeReport if this packet's fingerprint is cached."""
        fp = fingerprint(packet)
        with self._lock:
            entry = self._entries.get(fp)
            if entry is None:
                return None
            self._entries.move_to_end(fp)
            entry.hits += 1
        return MergeReport.from_dict(dict(entry.report))

    def record(self, packet: AgentPacketV1, report: MergeReport) -> None:
        """Record (packet, report). No-op for non-promote reports when promoted_only."""
        if self._promoted_only and report.decision != "promote":
            return
        fp = fingerprint(packet)
        entry = LedgerEntry(fingerprint=fp, report=report.to_dict(), recorded_at=time.time())
        with self._lock:
            if fp in self._entries:
                self._entries.move_to_end(fp)
                self._entries[fp] = entry
            else:
                self._entries[fp] = entry
                if len(self._entries) > self._max:
                    self._entries.popitem(last=False)
        self._persist(entry)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def __contains__(self, packet: AgentPacketV1) -> bool:
        with self._lock:
            return fingerprint(packet) in self._entries


__all__ = [
    "fingerprint",
    "LedgerEntry",
    "PacketLedger",
]
