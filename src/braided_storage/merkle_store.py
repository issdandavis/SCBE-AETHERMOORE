"""
BraidedVoxelStore — Merkle Chain
=================================

Braid-aware append-only Merkle chain for temporal/audit storage.

Each entry stores SHA-256 hash, braid coordinates, tongue,
timestamp, and previous hash — forming an immutable audit trail.

@layer Layer 13 (audit), Layer 12 (harmonic cost stamp)
@component BraidedStorage.MerkleChain
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


from src.braided_storage.types import BraidedPayload


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


GENESIS_HASH = _sha256("BRAIDED-VOXEL-STORE-GENESIS")


@dataclass
class MerkleEntry:
    """A single entry in the braid-aware Merkle chain."""
    entry_hash: str
    content_hash: str
    prev_hash: str
    timestamp: float
    dominant_tongue: str
    d_braid: float
    harmonic_cost: float
    phase_state: Tuple[int, int]
    phase_label: str
    source: str
    quarantined: bool
    index: int
    raw_bytes: bytes = field(repr=False, default=b"")

    def to_dict(self) -> Dict:
        return {
            "entry_hash": self.entry_hash,
            "content_hash": self.content_hash,
            "prev_hash": self.prev_hash,
            "timestamp": self.timestamp,
            "dominant_tongue": self.dominant_tongue,
            "d_braid": self.d_braid,
            "harmonic_cost": self.harmonic_cost,
            "phase_state": list(self.phase_state),
            "phase_label": self.phase_label,
            "source": self.source,
            "quarantined": self.quarantined,
            "index": self.index,
        }


def _compute_entry_hash(
    content_hash: str,
    prev_hash: str,
    timestamp: float,
    tongue: str,
    d_braid: float,
    index: int,
) -> str:
    """Compute deterministic hash for a Merkle entry."""
    data = json.dumps({
        "content": content_hash,
        "prev": prev_hash,
        "ts": timestamp,
        "tongue": tongue,
        "d_braid": round(d_braid, 8),
        "index": index,
    }, sort_keys=True)
    return _sha256(data)


def merkle_root(hashes: List[str]) -> str:
    """Compute Merkle root from a list of hashes."""
    if not hashes:
        return _sha256("empty")
    if len(hashes) == 1:
        return hashes[0]

    layer = list(hashes)
    if len(layer) % 2 != 0:
        layer.append(layer[-1])

    while len(layer) > 1:
        next_layer: List[str] = []
        for i in range(0, len(layer), 2):
            next_layer.append(_sha256(layer[i] + layer[i + 1]))
        layer = next_layer

    return layer[0]


class MerkleChain:
    """Braid-aware append-only Merkle chain.

    Every entry carries braid coordinates (d_braid, harmonic_cost,
    phase_state) alongside the standard content hash and prev_hash.

    Supports:
    - append(braided_payload) -> entry_hash
    - verify(entry_hash) -> bool
    - query_by_time(start, end) -> entries
    - query_by_tongue(tongue) -> entries
    - query_quarantined() -> entries
    """

    def __init__(self) -> None:
        self._entries: List[MerkleEntry] = []
        self._by_hash: Dict[str, MerkleEntry] = {}
        self._prev_hash: str = GENESIS_HASH

    # ------------------------------------------------------------------
    #  append
    # ------------------------------------------------------------------

    def append(self, braided: BraidedPayload) -> str:
        """Append a braided payload to the chain.

        Returns:
            entry_hash of the new entry.
        """
        content_hash = braided.semantic_bits.sha256_hash
        now = braided.timestamp
        tongue = braided.semantic_bits.dominant_tongue
        index = len(self._entries)

        entry_hash = _compute_entry_hash(
            content_hash=content_hash,
            prev_hash=self._prev_hash,
            timestamp=now,
            tongue=tongue,
            d_braid=braided.d_braid,
            index=index,
        )

        entry = MerkleEntry(
            entry_hash=entry_hash,
            content_hash=content_hash,
            prev_hash=self._prev_hash,
            timestamp=now,
            dominant_tongue=tongue,
            d_braid=braided.d_braid,
            harmonic_cost=braided.harmonic_cost,
            phase_state=braided.phase_state,
            phase_label=braided.phase_label,
            source=braided.source,
            quarantined=braided.quarantined,
            index=index,
            raw_bytes=braided.raw_bytes,
        )

        self._entries.append(entry)
        self._by_hash[entry_hash] = entry
        self._prev_hash = entry_hash

        return entry_hash

    # ------------------------------------------------------------------
    #  verify
    # ------------------------------------------------------------------

    def verify(self, entry_hash: str) -> bool:
        """Verify that an entry exists and its hash chain is valid."""
        entry = self._by_hash.get(entry_hash)
        if entry is None:
            return False

        # Recompute and check
        expected = _compute_entry_hash(
            content_hash=entry.content_hash,
            prev_hash=entry.prev_hash,
            timestamp=entry.timestamp,
            tongue=entry.dominant_tongue,
            d_braid=entry.d_braid,
            index=entry.index,
        )
        return expected == entry_hash

    def verify_chain(self) -> Tuple[bool, Optional[int], Optional[str]]:
        """Verify the entire chain's hash linkage.

        Returns:
            (valid, broken_index, reason) — (True, None, None) if valid.
        """
        prev = GENESIS_HASH
        for i, entry in enumerate(self._entries):
            if entry.prev_hash != prev:
                return False, i, "broken hash link"
            expected = _compute_entry_hash(
                content_hash=entry.content_hash,
                prev_hash=entry.prev_hash,
                timestamp=entry.timestamp,
                tongue=entry.dominant_tongue,
                d_braid=entry.d_braid,
                index=entry.index,
            )
            if expected != entry.entry_hash:
                return False, i, "hash mismatch"
            prev = entry.entry_hash

        return True, None, None

    # ------------------------------------------------------------------
    #  queries
    # ------------------------------------------------------------------

    def query_by_time(
        self,
        start: float,
        end: Optional[float] = None,
    ) -> List[MerkleEntry]:
        """Query entries within a time range."""
        if end is None:
            end = time.time() + 1.0
        return [
            e for e in self._entries
            if start <= e.timestamp <= end
        ]

    def query_by_tongue(self, tongue: str) -> List[MerkleEntry]:
        """Filter entries by dominant tongue."""
        return [
            e for e in self._entries
            if e.dominant_tongue == tongue
        ]

    def query_quarantined(self) -> List[MerkleEntry]:
        """List all quarantined entries."""
        return [e for e in self._entries if e.quarantined]

    def get_entry(self, entry_hash: str) -> Optional[MerkleEntry]:
        """Look up a single entry by hash."""
        return self._by_hash.get(entry_hash)

    # ------------------------------------------------------------------
    #  Merkle root
    # ------------------------------------------------------------------

    def compute_merkle_root(self) -> str:
        """Compute the Merkle root of all entry hashes."""
        hashes = [e.entry_hash for e in self._entries]
        return merkle_root(hashes)

    # ------------------------------------------------------------------
    #  diagnostics
    # ------------------------------------------------------------------

    @property
    def chain_length(self) -> int:
        return len(self._entries)

    @property
    def quarantine_count(self) -> int:
        return sum(1 for e in self._entries if e.quarantined)

    def tongue_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for e in self._entries:
            dist[e.dominant_tongue] = dist.get(e.dominant_tongue, 0) + 1
        return dist
