"""
BraidedPollyPad — PollyPad with Semantic Voxel Storage
=======================================================

Wires PollyPad's interaction loop to BraidedVoxelStore so every
conversation turn gets:
1. 6D addressed (tongue/weight/context/time/intent/instruction)
2. Scanned through antivirus membrane
3. Encoded through SemanticEncoder (bit-level fingerprints)
4. Braided with 3 temporal strands (intent x memory x governance)
5. Stored in dual voxel+merkle storage
6. Training pair generated (SFT/DPO)

The "what's small is big" principle: micro-level bit dressing
produces macro-level semantic structure. Same Fibonacci ratios
at both scales.

@patent USPTO #63/961,403
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .memory import PersistentMemory, MemoryCell, MemoryQuery, SixDAddress, TONGUE_WEIGHTS
from .pad import PollyPad, Interaction, TrainingPair

# Lazy imports — these modules depend on numpy/etc.
_braided_store = None
_braided_types = None


def _get_braided_store():
    global _braided_store
    if _braided_store is None:
        from src.braided_storage.pipeline import BraidedVoxelStore
        _braided_store = BraidedVoxelStore
    return _braided_store


def _get_braided_types():
    global _braided_types
    if _braided_types is None:
        import src.braided_storage.types as bt
        _braided_types = bt
    return _braided_types


# ---------------------------------------------------------------------------
#  BraidedInteraction: enriched interaction with voxel metadata
# ---------------------------------------------------------------------------

@dataclass
class BraidedInteraction:
    """An interaction enriched with braided storage metadata."""
    interaction: Interaction
    record_id: Optional[str] = None
    dominant_tongue: str = "KO"
    braid_distance: float = 0.0
    harmonic_cost: float = 1.0
    phase_state: Tuple[int, int] = (0, 0)
    storage_hint: str = "DUAL"
    quarantined: bool = False
    voxel_cube_id: Optional[str] = None
    merkle_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = self.interaction.to_dict()
        d["braided"] = {
            "record_id": self.record_id,
            "dominant_tongue": self.dominant_tongue,
            "braid_distance": self.braid_distance,
            "harmonic_cost": self.harmonic_cost,
            "phase_state": list(self.phase_state),
            "storage_hint": self.storage_hint,
            "quarantined": self.quarantined,
            "voxel_cube_id": self.voxel_cube_id,
            "merkle_hash": self.merkle_hash,
        }
        return d


# ---------------------------------------------------------------------------
#  BraidedPollyPad
# ---------------------------------------------------------------------------

class BraidedPollyPad(PollyPad):
    """PollyPad wired to BraidedVoxelStore for full semantic storage.

    Every interaction flows through:
      PollyPad (6D address + governance + training pair)
        -> BraidedVoxelStore (semantic encode + braid weave + dual store)

    The 6D address from PollyPad maps to the braided storage:
      - tongue -> SemanticEncoder tongue classification
      - weight -> braid strand weighting
      - context -> storage routing hints
      - time -> temporal braid strand (memory decay)
      - intent -> intent braid strand
      - instruction -> fingerprint correlation
    """

    def __init__(
        self,
        data_dir: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        super().__init__(data_dir=data_dir, session_id=session_id)

        # Create the braided store
        BVS = _get_braided_store()
        self._braided_store = BVS()
        self._braided_interactions: List[BraidedInteraction] = []

    def interact(
        self,
        user_text: str,
        context: str = "conversation",
        intent: str = "tell",
        response_text: Optional[str] = None,
    ) -> Interaction:
        """Process interaction through PollyPad + BraidedVoxelStore."""
        # Standard PollyPad interaction (6D address, governance, training pair)
        interaction = super().interact(user_text, context, intent, response_text)

        # Now also store through BraidedVoxelStore
        braided = self._store_braided(
            user_text, interaction.response_text,
            interaction.address, interaction,
        )
        self._braided_interactions.append(braided)

        return interaction

    def _store_braided(
        self,
        user_text: str,
        response_text: str,
        address: SixDAddress,
        interaction: Interaction,
    ) -> BraidedInteraction:
        """Store the interaction in braided voxel storage."""
        bt = _get_braided_types()

        # Combine user + response for storage
        combined = f"[{address.tongue}:{address.context}] {user_text}\n---\n{response_text}"
        raw_bytes = combined.encode("utf-8")

        # Map 6D intent to numeric for braid weaver
        intent_map = {
            "ask": 0.8, "tell": 1.0, "create": 1.2,
            "modify": 0.9, "delete": 0.5, "search": 0.7,
            "analyze": 1.1, "decide": 1.3, "play": 0.6, "learn": 1.0,
        }
        intent_signal = intent_map.get(address.intent, 1.0)

        # Ingest through full pipeline
        try:
            record = self._braided_store.ingest(
                raw_bytes=raw_bytes,
                source=f"pollypad:{self.session_id}:{interaction.interaction_id}",
                mime_type="text/plain",
                intent=intent_signal,
                tongue_hint=address.tongue,
            )

            return BraidedInteraction(
                interaction=interaction,
                record_id=record.record_id,
                dominant_tongue=record.dominant_tongue,
                braid_distance=record.braid_distance,
                harmonic_cost=record.harmonic_cost,
                phase_state=record.phase_state,
                storage_hint=record.storage_hint.value,
                quarantined=record.quarantined,
                voxel_cube_id=record.voxel_cube_id,
                merkle_hash=record.merkle_entry_hash,
            )
        except Exception:
            # Graceful degradation: if braided store fails, still return base interaction
            return BraidedInteraction(interaction=interaction)

    def recall_braided(
        self,
        query_text: str,
        context: Optional[str] = None,
        include_quarantined: bool = False,
    ) -> List[Dict[str, Any]]:
        """Recall from braided storage using tongue-based query."""
        bt = _get_braided_types()
        address = SixDAddress.from_interaction(query_text, context or "conversation")

        query = bt.RetrievalQuery(
            tongue=address.tongue,
            include_quarantined=include_quarantined,
            max_results=10,
            export_format=bt.ExportFormat.FLAT_DICT,
        )
        return self._braided_store.retrieve(query)

    def storage_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostics from both memory systems."""
        pad_stats = self.stats()
        braided_diag = self._braided_store.diagnostics()

        return {
            "pollypad": pad_stats,
            "braided_store": braided_diag,
            "braided_interactions": len(self._braided_interactions),
            "wired": True,
        }

    def save(self) -> Dict[str, Any]:
        """Save everything: memory + training pairs + braided log."""
        result = super().save()

        # Also save braided interaction log
        braided_dir = os.path.join(
            os.path.dirname(self.training_dir), "braided"
        )
        os.makedirs(braided_dir, exist_ok=True)
        braided_path = os.path.join(
            braided_dir, f"session_{self.session_id}.jsonl"
        )
        with open(braided_path, "w") as f:
            for bi in self._braided_interactions:
                f.write(json.dumps(bi.to_dict()) + "\n")

        result["braided"] = braided_path
        result["braided_count"] = len(self._braided_interactions)
        return result

    def export_braided_training_data(self) -> List[Dict[str, Any]]:
        """Export training pairs enriched with braid metadata."""
        enriched = []
        for bi in self._braided_interactions:
            pair = bi.interaction.training_pair
            if pair is None:
                continue
            d = pair.to_dict()
            d["braid_distance"] = bi.braid_distance
            d["harmonic_cost"] = bi.harmonic_cost
            d["phase_state"] = list(bi.phase_state)
            d["quarantined"] = bi.quarantined
            d["record_id"] = bi.record_id
            enriched.append(d)
        return enriched
