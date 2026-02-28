"""
BraidedVoxelStore — Braid Weaver
=================================

Python implementation of 3-strand temporal braid:
  Ti (intent) x Tm (memory) x Tg (governance) -> T_b3

Uses hamiltonian_braid.py for braid_distance() and harmonic_cost(),
and the 9-state phase diagram for phase classification.

@layer Layer 5 (hyperbolic distance), Layer 8 (Hamiltonian),
       Layer 12 (harmonic cost), Layer 13 (governance)
@component BraidedStorage.BraidWeaver
"""

from __future__ import annotations

import math
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.braided_storage.types import BraidedPayload, SemanticBits

# Import braid primitives
from src.symphonic_cipher.scbe_aethermoore.ai_brain.hamiltonian_braid import (
    harmonic_cost as _harmonic_cost,
    phase_deviation,
    phase_label as _phase_label,
    PHASE_STATES,
    Rail,
    RailPoint,
    braid_distance as _braid_distance,
)
from src.symphonic_cipher.scbe_aethermoore.ai_brain.unified_state import (
    BRAIN_DIMENSIONS,
    PHI,
)

# Sacred Tongue frequency mapping (Hz) for phase state derivation
TONGUE_FREQ: Dict[str, float] = {
    "KO": 440.0,
    "AV": 528.0,
    "RU": 396.0,
    "CA": 639.0,
    "UM": 741.0,
    "DR": 852.0,
}

# Default rail: a short equilibrium rail for standalone use
_DEFAULT_RAIL = Rail(points=[
    RailPoint(
        position=np.zeros(BRAIN_DIMENSIONS),
        expected_phase=(0, 0),
        index=0,
    ),
])


class BraidWeaver:
    """3-strand temporal braid weaver.

    Strands:
      Ti = intent x tongue affinity (how strongly the content aligns
           with the intent of the dominant tongue)
      Tm = memory weight (exponential decay for repeated content;
           fresh = 1.0, stale = decay toward 0)
      Tg = governance = threat_score x harmonic_cost(d_braid)

    Braided meta-time: T_b3 = Ti * Tm * Tg

    The weaver also maintains a content-hash memory for computing
    the Tm strand.
    """

    def __init__(
        self,
        *,
        rail: Optional[Rail] = None,
        lambda_phase: float = 0.5,
        memory_decay_rate: float = 0.1,
        memory_capacity: int = 1000,
    ):
        self._rail = rail or _DEFAULT_RAIL
        self._lambda_phase = lambda_phase
        self._memory_decay_rate = memory_decay_rate
        self._memory_capacity = memory_capacity

        # Content hash -> list of timestamps (for Tm decay)
        self._memory: Dict[str, List[float]] = defaultdict(list)

    # ------------------------------------------------------------------
    #  weave: produce a BraidedPayload
    # ------------------------------------------------------------------

    def weave(
        self,
        semantic_bits: SemanticBits,
        raw_bytes: bytes,
        source: str,
        mime_type: str,
        *,
        intent: float = 1.0,
        memory_weight: Optional[float] = None,
        governance_context: Optional[dict] = None,
    ) -> BraidedPayload:
        """Weave semantic bits into a 3-strand temporal braid.

        Args:
            semantic_bits: Output from SemanticEncoder.
            raw_bytes: Original content bytes.
            source: Content source URL/path.
            mime_type: Content MIME type.
            intent: External intent signal (default 1.0 = full intent).
            memory_weight: Override for Tm strand. If None, auto-computed
                           from content hash repetition decay.
            governance_context: Optional extra governance params.

        Returns:
            BraidedPayload with all three strands woven.
        """
        now = time.time()

        # --- Strand 1: Ti (intent x tongue affinity) ---
        tongue_affinity = self._tongue_affinity(semantic_bits)
        strand_intent = max(0.0, intent) * tongue_affinity

        # --- Strand 2: Tm (memory / repetition decay) ---
        if memory_weight is not None:
            strand_memory = max(0.0, min(1.0, memory_weight))
        else:
            strand_memory = self._compute_memory_decay(
                semantic_bits.sha256_hash, now
            )
        # Record this content hash for future decay
        self._record_memory(semantic_bits.sha256_hash, now)

        # --- Strand 3: Tg (governance) ---
        # Build a 21D state vector from tongue trits for braid distance
        state_21d = self._state_from_trits(semantic_bits.tongue_trits)
        d_braid, _ = _braid_distance(
            state_21d,
            self._rail,
            current_phase=(0, 0),
            lambda_phase=self._lambda_phase,
        )
        h_cost = _harmonic_cost(d_braid)
        threat = max(0.0, min(1.0, semantic_bits.threat_score))
        strand_governance = threat * h_cost

        # --- Braided meta-time ---
        # Clamp strands to avoid degenerate zero
        ti = max(1e-12, strand_intent)
        tm = max(1e-12, strand_memory)
        tg = max(1e-12, strand_governance) if strand_governance > 0 else 1.0
        braided_time = ti * tm * tg

        # --- Phase state ---
        phase_state = self._derive_phase(semantic_bits.tongue_trits)
        label = _phase_label(phase_state)

        # --- Quarantine flag ---
        quarantined = semantic_bits.governance_decision in ("DENY", "QUARANTINE")

        return BraidedPayload(
            strand_intent=round(strand_intent, 8),
            strand_memory=round(strand_memory, 8),
            strand_governance=round(strand_governance, 8),
            braided_time=round(braided_time, 8),
            d_braid=round(d_braid, 8),
            harmonic_cost=round(h_cost, 8),
            phase_state=phase_state,
            phase_label=label,
            semantic_bits=semantic_bits,
            raw_bytes=raw_bytes,
            source=source,
            mime_type=mime_type,
            timestamp=now,
            quarantined=quarantined,
        )

    # ------------------------------------------------------------------
    #  Strand helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tongue_affinity(bits: SemanticBits) -> float:
        """Compute tongue affinity as normalized absolute trit energy.

        Higher absolute trit sum = stronger alignment to Sacred Tongues.
        Returns value in [0.1, 1.0] (never zero to avoid degenerate braid).
        """
        if not bits.tongue_trits:
            return 0.1
        energy = sum(abs(t) for t in bits.tongue_trits) / len(bits.tongue_trits)
        return max(0.1, min(1.0, energy))

    def _compute_memory_decay(self, content_hash: str, now: float) -> float:
        """Compute memory strand via exponential time decay of repetitions.

        First time seeing content: Tm = 1.0 (fresh).
        Repeated: Tm = exp(-rate * times_seen / age_factor).
        """
        history = self._memory.get(content_hash, [])
        if not history:
            return 1.0  # First encounter = fresh

        times_seen = len(history)
        most_recent = max(history)
        age = max(1.0, now - most_recent)

        decay = math.exp(-self._memory_decay_rate * times_seen / math.log1p(age))
        return max(0.01, min(1.0, decay))

    def _record_memory(self, content_hash: str, now: float) -> None:
        """Record a content observation in the memory buffer."""
        self._memory[content_hash].append(now)

        # Evict oldest entries if over capacity
        if len(self._memory) > self._memory_capacity:
            oldest_key = min(self._memory, key=lambda k: self._memory[k][-1])
            del self._memory[oldest_key]

    @staticmethod
    def _state_from_trits(tongue_trits: List[int]) -> np.ndarray:
        """Build a 21D state vector from tongue trits.

        Maps 6 tongue trits to the first 6 dimensions, fills phases
        from Sacred Tongue frequencies, and zero-fills the rest.
        """
        state = np.zeros(BRAIN_DIMENSIONS, dtype=float)

        # First 6: tongue position (trits scaled to Poincare ball interior)
        for i, t in enumerate(tongue_trits[:6]):
            state[i] = float(t) * 0.3  # Keep well inside ball

        # Dims 6-11: tongue phases (from frequency map)
        tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
        for i, tongue in enumerate(tongues):
            freq = TONGUE_FREQ.get(tongue, 440.0)
            state[6 + i] = freq / 1000.0  # Normalized

        return state

    @staticmethod
    def _derive_phase(tongue_trits: List[int]) -> Tuple[int, int]:
        """Derive a dual ternary phase state from tongue trits.

        parallel = sign(KO + AV + RU)  (first 3 tongues)
        perp = sign(CA + UM + DR)      (last 3 tongues)

        Returns one of the 9 phase states.
        """
        if len(tongue_trits) < 6:
            return (0, 0)

        par_sum = sum(tongue_trits[:3])
        perp_sum = sum(tongue_trits[3:6])

        def _sign(x: int) -> int:
            if x > 0:
                return 1
            if x < 0:
                return -1
            return 0

        par_trit = _sign(par_sum)
        perp_trit = _sign(perp_sum)

        # Clamp to valid phase states
        candidate = (par_trit, perp_trit)
        if candidate in PHASE_STATES:
            return candidate
        return (0, 0)

    # ------------------------------------------------------------------
    #  Diagnostics
    # ------------------------------------------------------------------

    @property
    def memory_size(self) -> int:
        return len(self._memory)

    def clear_memory(self) -> None:
        self._memory.clear()
