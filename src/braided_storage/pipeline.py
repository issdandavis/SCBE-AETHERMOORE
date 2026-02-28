"""
BraidedVoxelStore — Main Pipeline
==================================

The hive orchestrator: Forager -> SemanticEncoder -> BraidWeaver
-> StorageRouter -> VoxelComb / MerkleChain -> ExportBridge.

@layer All layers (L1-L14 touched through sub-modules)
@component BraidedStorage.Pipeline
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

from src.braided_storage.types import (
    BraidedPayload,
    ExportFormat,
    ForagerPayload,
    RetrievalQuery,
    ScanResult,
    SemanticBits,
    StorageHint,
    StoredRecord,
    Verdict,
)
from src.braided_storage.forager import Forager
from src.braided_storage.semantic_encoder import SemanticEncoder
from src.braided_storage.braid_weaver import BraidWeaver
from src.braided_storage.voxel_store import VoxelComb
from src.braided_storage.merkle_store import MerkleChain, MerkleEntry

# Size threshold for "large" payloads (64 KB)
LARGE_PAYLOAD_BYTES = 65_536


class BraidedVoxelStore:
    """The Hive — main orchestrator for braided voxel storage.

    Pipeline::

        raw_bytes -> SemanticEncoder -> BraidWeaver -> StorageRouter
                                                         |
                                            ┌────────────┼────────────┐
                                            v            v            v
                                        VoxelComb   MerkleChain   (export)
                                        (spatial)   (temporal)

    StorageRouter logic:
      CLEAN + small  -> DUAL (both voxel + merkle)
      CLEAN + large  -> MERKLE_AUDIT (too big for voxel grid)
      CAUTION        -> MERKLE_AUDIT (needs review)
      SUSPICIOUS+    -> quarantine in merkle, no voxel
      hot_data flag  -> VOXEL_FAST priority
    """

    def __init__(
        self,
        *,
        forager: Optional[Forager] = None,
        encoder: Optional[SemanticEncoder] = None,
        weaver: Optional[BraidWeaver] = None,
        voxel_comb: Optional[VoxelComb] = None,
        merkle_chain: Optional[MerkleChain] = None,
        large_threshold: int = LARGE_PAYLOAD_BYTES,
    ):
        self.forager = forager or Forager()
        self.encoder = encoder or SemanticEncoder()
        self.weaver = weaver or BraidWeaver()
        self.voxel_comb = voxel_comb or VoxelComb()
        self.merkle_chain = merkle_chain or MerkleChain()
        self._large_threshold = large_threshold

        # Map record_id -> StoredRecord for retrieval
        self._records: Dict[str, StoredRecord] = {}
        self._ingest_count = 0

    # ------------------------------------------------------------------
    #  ingest: full encode -> route -> store
    # ------------------------------------------------------------------

    def ingest(
        self,
        raw_bytes: bytes,
        source: str = "direct",
        mime_type: str = "application/octet-stream",
        *,
        intent: float = 1.0,
        tongue_hint: Optional[str] = None,
        hot_data: bool = False,
        scan_override: Optional[ScanResult] = None,
    ) -> StoredRecord:
        """Ingest raw bytes through the full pipeline.

        Args:
            raw_bytes: Content to ingest.
            source: Source URL or path.
            mime_type: MIME type hint.
            intent: Intent signal for braid weaving (default 1.0).
            tongue_hint: Optional Sacred Tongue override.
            hot_data: If True, prioritize VOXEL_FAST routing.
            scan_override: Optional pre-computed scan result.

        Returns:
            StoredRecord with storage locations and metadata.
        """
        self._ingest_count += 1
        data = bytes(raw_bytes or b"")

        # 1. Scan (if not pre-scanned by forager)
        if scan_override is not None:
            scan = scan_override
        else:
            payload = ForagerPayload(raw_bytes=data, source=source, mime_type=mime_type)
            scan = self.forager.scan(payload)

        # 2. Encode semantics
        semantic_bits = self.encoder.encode(data, mime_type, tongue_hint)

        # 3. Weave braid
        braided = self.weaver.weave(
            semantic_bits=semantic_bits,
            raw_bytes=data,
            source=source,
            mime_type=mime_type,
            intent=intent,
        )

        # Override quarantine from scan result
        if scan.verdict in (Verdict.SUSPICIOUS, Verdict.MALICIOUS):
            braided = BraidedPayload(
                strand_intent=braided.strand_intent,
                strand_memory=braided.strand_memory,
                strand_governance=braided.strand_governance,
                braided_time=braided.braided_time,
                d_braid=braided.d_braid,
                harmonic_cost=braided.harmonic_cost,
                phase_state=braided.phase_state,
                phase_label=braided.phase_label,
                semantic_bits=braided.semantic_bits,
                raw_bytes=braided.raw_bytes,
                source=braided.source,
                mime_type=braided.mime_type,
                timestamp=braided.timestamp,
                quarantined=True,
            )

        # 4. Route
        hint = self._route(scan, len(data), hot_data)

        # 5. Store
        record = self._store(braided, hint)
        self._records[record.record_id] = record
        return record

    # ------------------------------------------------------------------
    #  forage: Forager.forage() + ingest
    # ------------------------------------------------------------------

    def forage(self, url_or_path: str, *, intent: float = 1.0) -> Optional[StoredRecord]:
        """Forage from a URL/path and ingest into storage."""
        return self.forager.forage(url_or_path, self)

    # ------------------------------------------------------------------
    #  retrieve
    # ------------------------------------------------------------------

    def retrieve(self, query: RetrievalQuery) -> List[Dict[str, Any]]:
        """Search both stores and return results in requested format."""
        results: List[StoredRecord] = []

        for record in self._records.values():
            if not self._matches_query(record, query):
                continue
            results.append(record)

        results.sort(key=lambda r: r.timestamp, reverse=True)
        results = results[: query.max_results]

        return [
            self.export(record, query.export_format)
            for record in results
        ]

    # ------------------------------------------------------------------
    #  export / reconvert
    # ------------------------------------------------------------------

    def export(self, record: StoredRecord, fmt: ExportFormat = ExportFormat.FLAT_DICT) -> Dict[str, Any]:
        """Export a stored record in the requested format."""
        base = {
            "record_id": record.record_id,
            "source": record.source,
            "dominant_tongue": record.dominant_tongue,
            "storage_hint": record.storage_hint.value,
            "braid_distance": record.braid_distance,
            "harmonic_cost": record.harmonic_cost,
            "phase_state": list(record.phase_state),
            "timestamp": record.timestamp,
            "quarantined": record.quarantined,
        }

        if fmt == ExportFormat.FLAT_DICT:
            return base

        if fmt == ExportFormat.JSONL:
            base["_format"] = "jsonl"
            base["_line"] = json.dumps(base, sort_keys=True)
            return base

        if fmt == ExportFormat.HF_DATASET:
            return {
                "text": f"[{record.dominant_tongue}] source={record.source}",
                "tongue": record.dominant_tongue,
                "braid_distance": record.braid_distance,
                "harmonic_cost": record.harmonic_cost,
                "quarantined": record.quarantined,
                "metadata": base,
            }

        if fmt == ExportFormat.BYTES:
            # Return raw bytes if available from merkle chain
            entry = self._get_merkle_entry(record)
            base["raw_bytes_hex"] = entry.raw_bytes.hex() if entry else ""
            return base

        if fmt == ExportFormat.VOXEL_RAW:
            base["voxel_cube_id"] = record.voxel_cube_id
            return base

        return base

    def reconvert(
        self,
        record: StoredRecord,
        from_format: ExportFormat,
        to_format: ExportFormat,
    ) -> Dict[str, Any]:
        """Convert a record between export formats."""
        return self.export(record, to_format)

    # ------------------------------------------------------------------
    #  diagnostics
    # ------------------------------------------------------------------

    def diagnostics(self) -> Dict[str, Any]:
        """Storage stats, occupancy, chain length, braid health."""
        return {
            "ingest_count": self._ingest_count,
            "record_count": len(self._records),
            "voxel_count": self.voxel_comb.voxel_count,
            "merkle_chain_length": self.merkle_chain.chain_length,
            "merkle_quarantine_count": self.merkle_chain.quarantine_count,
            "octree_point_count": self.voxel_comb.octree_point_count,
            "octree_occupancy": self.voxel_comb.occupancy(),
            "weaver_memory_size": self.weaver.memory_size,
            "forager_count": self.forager.forage_count,
            "tongue_distribution": self.merkle_chain.tongue_distribution(),
            "merkle_root": self.merkle_chain.compute_merkle_root(),
            "chain_valid": self.merkle_chain.verify_chain()[0],
        }

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    def _route(self, scan: ScanResult, data_size: int, hot_data: bool) -> StorageHint:
        """StorageRouter: determine where to store based on scan + size."""
        if scan.verdict in (Verdict.SUSPICIOUS, Verdict.MALICIOUS):
            return StorageHint.MERKLE_AUDIT  # Quarantine: merkle only

        if scan.verdict == Verdict.CAUTION:
            return StorageHint.MERKLE_AUDIT  # Needs review: merkle only

        # CLEAN
        if hot_data:
            return StorageHint.VOXEL_FAST

        if data_size > self._large_threshold:
            return StorageHint.MERKLE_AUDIT  # Too large for voxel grid

        return StorageHint.DUAL  # Clean + small = both stores

    def _store(self, braided: BraidedPayload, hint: StorageHint) -> StoredRecord:
        """Store in the appropriate backend(s) based on hint."""
        record_id = f"rec_{uuid.uuid4().hex[:12]}"
        voxel_id: Optional[str] = None
        merkle_hash: Optional[str] = None

        if hint in (StorageHint.DUAL, StorageHint.VOXEL_FAST):
            voxel_id = self.voxel_comb.deposit(braided)

        if hint in (StorageHint.DUAL, StorageHint.MERKLE_AUDIT):
            merkle_hash = self.merkle_chain.append(braided)

        # Export-only doesn't persist (but we still create a record)
        return StoredRecord(
            record_id=record_id,
            source=braided.source,
            dominant_tongue=braided.semantic_bits.dominant_tongue,
            storage_hint=hint,
            voxel_cube_id=voxel_id,
            merkle_entry_hash=merkle_hash,
            braid_distance=braided.d_braid,
            harmonic_cost=braided.harmonic_cost,
            phase_state=braided.phase_state,
            timestamp=braided.timestamp,
            quarantined=braided.quarantined,
        )

    def _matches_query(self, record: StoredRecord, query: RetrievalQuery) -> bool:
        """Check if a record matches a retrieval query."""
        if not query.include_quarantined and record.quarantined:
            return False

        if query.tongue is not None and record.dominant_tongue != query.tongue:
            return False

        if query.time_start is not None and record.timestamp < query.time_start:
            return False

        if query.time_end is not None and record.timestamp > query.time_end:
            return False

        if query.phase_state is not None and record.phase_state != query.phase_state:
            return False

        return True

    def _get_merkle_entry(self, record: StoredRecord) -> Optional[MerkleEntry]:
        """Look up the merkle entry for a stored record."""
        if record.merkle_entry_hash:
            return self.merkle_chain.get_entry(record.merkle_entry_hash)
        return None
