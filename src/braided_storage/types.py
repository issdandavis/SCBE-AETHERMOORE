"""
BraidedVoxelStore — Shared Types
================================

Dataclasses and enums for the Semantic Forager Storage Pipeline.

@layer Layer 5, Layer 10, Layer 12, Layer 13
@component BraidedStorage.Types
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
#  Verdicts (reused from antivirus_membrane thresholds)
# ---------------------------------------------------------------------------

class Verdict(str, Enum):
    CLEAN = "CLEAN"
    CAUTION = "CAUTION"
    SUSPICIOUS = "SUSPICIOUS"
    MALICIOUS = "MALICIOUS"


# ---------------------------------------------------------------------------
#  Storage routing
# ---------------------------------------------------------------------------

class StorageHint(str, Enum):
    VOXEL_FAST = "VOXEL_FAST"
    MERKLE_AUDIT = "MERKLE_AUDIT"
    DUAL = "DUAL"
    EXPORT_ONLY = "EXPORT_ONLY"


class ExportFormat(str, Enum):
    JSONL = "JSONL"
    BYTES = "BYTES"
    HF_DATASET = "HF_DATASET"
    FLAT_DICT = "FLAT_DICT"
    VOXEL_RAW = "VOXEL_RAW"


# ---------------------------------------------------------------------------
#  Forager payloads
# ---------------------------------------------------------------------------

@dataclass
class ForagerPayload:
    """Raw payload carried by a forager agent."""
    raw_bytes: bytes
    source: str
    mime_type: str
    timestamp: float = field(default_factory=time.time)
    size_bytes: int = 0
    provenance: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.size_bytes == 0:
            self.size_bytes = len(self.raw_bytes)


@dataclass(frozen=True)
class ScanResult:
    """Result of antivirus membrane scan."""
    verdict: Verdict
    risk_score: float
    action: str
    reasons: Tuple[str, ...]


# ---------------------------------------------------------------------------
#  Encoding outputs
# ---------------------------------------------------------------------------

@dataclass
class SemanticBits:
    """Output of the SemanticEncoder stage."""
    dominant_tongue: str
    tongue_trits: List[int]
    fingerprint_ids: List[str]
    sha256_hash: str
    threat_score: float
    governance_decision: str
    molecular_bonds: List[Any] = field(default_factory=list)


@dataclass
class BraidedPayload:
    """Output of the BraidWeaver stage — 3-strand temporal braid."""
    strand_intent: float        # Ti: intent x tongue affinity
    strand_memory: float        # Tm: exponential time decay
    strand_governance: float    # Tg: threat_score x harmonic_cost
    braided_time: float         # T_b3 = Ti * Tm * Tg
    d_braid: float              # braid distance
    harmonic_cost: float        # phi^(d^2)
    phase_state: Tuple[int, int]
    phase_label: str
    semantic_bits: SemanticBits
    raw_bytes: bytes
    source: str
    mime_type: str
    timestamp: float = field(default_factory=time.time)
    quarantined: bool = False


# ---------------------------------------------------------------------------
#  Storage records
# ---------------------------------------------------------------------------

@dataclass
class StoredRecord:
    """A record stored in the hive (voxel and/or merkle)."""
    record_id: str
    source: str
    dominant_tongue: str
    storage_hint: StorageHint
    voxel_cube_id: Optional[str] = None
    merkle_entry_hash: Optional[str] = None
    braid_distance: float = 0.0
    harmonic_cost: float = 1.0
    phase_state: Tuple[int, int] = (0, 0)
    timestamp: float = field(default_factory=time.time)
    quarantined: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
#  Retrieval
# ---------------------------------------------------------------------------

@dataclass
class RetrievalQuery:
    """Query for retrieving stored records."""
    tongue: Optional[str] = None
    spectral_fingerprint: Optional[str] = None
    time_start: Optional[float] = None
    time_end: Optional[float] = None
    phase_state: Optional[Tuple[int, int]] = None
    include_quarantined: bool = False
    max_results: int = 100
    export_format: ExportFormat = ExportFormat.FLAT_DICT
