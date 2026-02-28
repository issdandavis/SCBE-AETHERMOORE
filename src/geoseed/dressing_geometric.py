"""
Geometric Bit Dressing Pipeline — 14-Layer SCBE Traversal
==========================================================

Full geometric dressing: each raw data unit traverses all 14 SCBE layers,
acquiring a multi-dimensional fingerprint. This is the F1 tier used for
training data generation.

For the lightweight M6 integration layer, see dressing.py.

Three Tiers:
    F1: Full bit-level dressing (this module, training data)
    F2: Lightweight SS1/BPE bridge (dressing.py, public tokenizer interop)
    F3: Sacred Eggs + GeoSeal identity genesis

@layer L1-L14
@component GeoSeed.DressingGeometric
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.geoseed.sphere_grid import (
    TONGUE_NAMES,
    TONGUE_PHASES,
    LWS_WEIGHTS,
    PHI_WEIGHTS,
    PHI,
    poincare_project,
    mobius_add,
    hyperbolic_distance,
    CL6,
)

# Import 14-layer reference functions
from src.scbe_14layer_reference import (
    layer_0_intent_modulation,
    layer_1_complex_state,
    layer_2_realification,
    layer_3_weighted_transform,
    layer_4_poincare_embedding,
    layer_5_hyperbolic_distance,
    layer_6_breathing_transform,
    layer_9_spectral_coherence,
    layer_10_spin_coherence,
    layer_11_triadic_temporal,
    layer_12_harmonic_scaling,
    layer_13_risk_decision,
)


class DressingTier(Enum):
    F1 = "training"
    F2 = "interop"
    F3 = "genesis"


class GovernanceDecision(Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    DENY = "DENY"


@dataclass
class GeometricDressedBit:
    """A data unit that has traversed the full 14-layer SCBE stack.

    Carries its geometric history as a multi-dimensional fingerprint.
    """

    raw_value: int
    position: int
    tongue: str
    tier: DressingTier = DressingTier.F1

    # Layer outputs
    complex_state: Optional[np.ndarray] = None
    real_state: Optional[np.ndarray] = None
    weighted_state: Optional[np.ndarray] = None
    poincare_pos: Optional[np.ndarray] = None
    hyperbolic_dist: float = 0.0
    breathed_pos: Optional[np.ndarray] = None
    phase_pos: Optional[np.ndarray] = None
    realm_dist: float = 0.0
    spectral_score: float = 0.5
    spin_score: float = 0.5
    temporal_score: float = 0.5
    harmonic_score: float = 1.0
    decision: GovernanceDecision = GovernanceDecision.ALLOW
    risk_score: float = 0.0
    audio_energy: float = 0.0

    # Geometric output for sphere grid deposition
    sphere_position: Optional[np.ndarray] = None
    multivector: Optional[np.ndarray] = None

    @property
    def is_allowed(self) -> bool:
        return self.decision == GovernanceDecision.ALLOW

    def to_signal(self) -> np.ndarray:
        """Pack into a 64-component Cl(6,0) multivector signal.

        Layout:
        - [0]: scalar = harmonic_score * governance_sign
        - [1-6]: grade-1 = Poincaré position (6D)
        - [7-21]: grade-2 = fingerprint scores (15 bivector slots)
        - [22+]: higher grades zeroed (reserved)
        """
        signal = np.zeros(64)

        sign = 1.0 if self.is_allowed else -0.5
        signal[0] = self.harmonic_score * sign

        if self.poincare_pos is not None:
            pos = self.poincare_pos
            if len(pos) > 6:
                pos = pos[:6]
            elif len(pos) < 6:
                pos = np.pad(pos, (0, 6 - len(pos)))
            signal[1:7] = pos

        scores = np.array([
            self.spectral_score,
            self.spin_score,
            self.temporal_score,
            self.harmonic_score,
            self.risk_score,
            self.audio_energy,
            float(self.raw_value) / 255.0,
            TONGUE_PHASES[self.tongue] / (2 * math.pi),
            LWS_WEIGHTS[self.tongue],
        ])
        scores = np.pad(scores, (0, 15 - len(scores)))
        signal[7:22] = scores

        self.multivector = signal
        return signal


# Default realm centers (safe operation zones)
DEFAULT_REALMS = [
    np.zeros(12),
    np.array([0.1] * 6 + [0.0] * 6),
    np.array([0.0] * 6 + [0.1] * 6),
]


class GeometricBitDresser:
    """Full F1 dressing through the 14-layer SCBE stack.

    Each unit gets assigned to a Sacred Tongue via round-robin (position % 6)
    and traverses L1-L14 to produce a dressed bit with full geometric fingerprint.
    """

    def __init__(
        self,
        tier: DressingTier = DressingTier.F1,
        dimension: int = 6,
        breathing_factor: float = 1.0,
        realms: Optional[List[np.ndarray]] = None,
        key: str = "geoseed_default",
    ):
        self.tier = tier
        self.dimension = dimension
        self.breathing_factor = breathing_factor
        self.realms = realms or DEFAULT_REALMS
        self.key = key

        # Temporal history for L11
        self._recent_dists: List[float] = []
        self._mid_dists: List[float] = []
        self._global_dist_sum: float = 0.0
        self._global_dist_count: int = 0

    def dress(self, value: int, position: int, context: Optional[bytes] = None) -> GeometricDressedBit:
        """Dress a single data unit through the 14-layer stack."""
        tongue = TONGUE_NAMES[position % 6]
        bit = GeometricDressedBit(raw_value=value, position=position, tongue=tongue, tier=self.tier)

        if self.tier == DressingTier.F2:
            return self._dress_lightweight(bit)

        return self._dress_full(bit, context)

    def _dress_full(self, bit: GeometricDressedBit, context: Optional[bytes]) -> GeometricDressedBit:
        """Full F1/F3 dressing through all 14 layers."""
        D = self.dimension
        tongue_idx = TONGUE_NAMES.index(bit.tongue)

        t = np.zeros(2 * D)
        t[tongue_idx] = float(bit.raw_value) / 255.0
        t[D + tongue_idx] = TONGUE_PHASES[bit.tongue]

        # L0: Intent modulation
        t = layer_0_intent_modulation(t, self.key)

        # L1-L4: Complex → Real → Weighted → Poincaré
        bit.complex_state = layer_1_complex_state(t, D)
        bit.real_state = layer_2_realification(bit.complex_state)
        bit.weighted_state = layer_3_weighted_transform(bit.real_state)
        bit.poincare_pos = layer_4_poincare_embedding(bit.weighted_state)

        # L5: Hyperbolic distance from origin
        origin = np.zeros_like(bit.poincare_pos)
        bit.hyperbolic_dist = layer_5_hyperbolic_distance(bit.poincare_pos, origin)

        # L6: Breathing transform
        bit.breathed_pos = layer_6_breathing_transform(bit.poincare_pos, self.breathing_factor)

        # L7: Phase transform (Möbius shift by tongue phase)
        phase_shift = np.zeros_like(bit.breathed_pos)
        if len(phase_shift) > 0:
            phase_shift[tongue_idx % len(phase_shift)] = 0.1 * math.sin(TONGUE_PHASES[bit.tongue])
        bit.phase_pos = mobius_add(bit.breathed_pos, poincare_project(phase_shift))

        # L8: Realm distance
        realm_dists = []
        for realm in self.realms:
            r = realm
            if len(r) != len(bit.phase_pos):
                r = np.zeros_like(bit.phase_pos)
                r[: min(len(realm), len(r))] = realm[: min(len(realm), len(r))]
            realm_dists.append(layer_5_hyperbolic_distance(bit.phase_pos, r))
        bit.realm_dist = min(realm_dists) if realm_dists else 0.0

        # L9: Spectral coherence
        if context is not None and len(context) >= 4:
            signal = np.array([float(b) for b in context])
            bit.spectral_score = layer_9_spectral_coherence(signal)
        else:
            bit.spectral_score = layer_9_spectral_coherence(np.array(bit.real_state))

        # L10: Spin coherence — use local phasors (position neighborhood),
        # not all 6 tongue phases which are uniformly spread by design
        local_phases = np.array([
            TONGUE_PHASES[bit.tongue],
            TONGUE_PHASES[bit.tongue] + bit.hyperbolic_dist * 0.1,
            TONGUE_PHASES[bit.tongue] - bit.realm_dist * 0.05,
        ])
        bit.spin_score = layer_10_spin_coherence(local_phases)

        # L11: Triadic temporal
        self._recent_dists.append(bit.hyperbolic_dist)
        if len(self._recent_dists) > 10:
            self._mid_dists.append(np.mean(self._recent_dists[-10:]))
            self._recent_dists = self._recent_dists[-10:]
        self._global_dist_sum += bit.hyperbolic_dist
        self._global_dist_count += 1

        d1 = np.mean(self._recent_dists[-3:]) if len(self._recent_dists) >= 3 else bit.hyperbolic_dist
        d2 = np.mean(self._mid_dists[-5:]) if self._mid_dists else d1
        dG = self._global_dist_sum / max(self._global_dist_count, 1)
        bit.temporal_score = layer_11_triadic_temporal(d1, d2, dG, d_scale=5.0)

        # L12: Harmonic wall — phase deviation measures how far from coherent
        # Use (1 - spin_score) as the deviation metric, not raw phase comparison
        phase_dev = 1.0 - bit.spin_score
        bit.harmonic_score = layer_12_harmonic_scaling(bit.realm_dist, phase_dev)

        # L13: Governance decision
        risk_base = 1.0 - bit.spectral_score * bit.spin_score
        decision_str, risk_val = layer_13_risk_decision(risk_base, bit.harmonic_score)
        bit.decision = GovernanceDecision(decision_str)
        bit.risk_score = risk_val

        # L14: Audio axis
        freq = 440.0 * PHI ** TONGUE_NAMES.index(bit.tongue)
        bit.audio_energy = math.sin(2 * math.pi * freq * bit.position / 44100.0) ** 2

        # Compute sphere position for grid deposition
        pos_6d = bit.poincare_pos[:6] if len(bit.poincare_pos) >= 6 else np.pad(
            bit.poincare_pos, (0, max(0, 6 - len(bit.poincare_pos)))
        )
        idx = TONGUE_NAMES.index(bit.tongue)
        coord_pairs = [(0, 1), (2, 3), (4, 5), (0, 2), (1, 3), (2, 4)]
        ci, cj = coord_pairs[idx]
        sphere_3d = np.array([pos_6d[ci], pos_6d[cj], pos_6d[(ci + cj) % 6]])
        norm = np.linalg.norm(sphere_3d)
        if norm > 1e-12:
            sphere_3d /= norm
        else:
            sphere_3d = np.array([0.0, 0.0, 1.0])
        bit.sphere_position = sphere_3d

        bit.to_signal()
        return bit

    def _dress_lightweight(self, bit: GeometricDressedBit) -> GeometricDressedBit:
        """F2 lightweight dressing — L1-L4 only."""
        D = self.dimension
        tongue_idx = TONGUE_NAMES.index(bit.tongue)

        t = np.zeros(2 * D)
        t[tongue_idx] = float(bit.raw_value) / 255.0
        t[D + tongue_idx] = TONGUE_PHASES[bit.tongue]

        bit.complex_state = layer_1_complex_state(t, D)
        bit.real_state = layer_2_realification(bit.complex_state)
        bit.weighted_state = layer_3_weighted_transform(bit.real_state)
        bit.poincare_pos = layer_4_poincare_embedding(bit.weighted_state)

        bit.harmonic_score = 1.0
        bit.decision = GovernanceDecision.ALLOW
        bit.spectral_score = 0.5
        bit.spin_score = 0.5

        pos_6d = bit.poincare_pos[:6] if len(bit.poincare_pos) >= 6 else np.pad(
            bit.poincare_pos, (0, max(0, 6 - len(bit.poincare_pos)))
        )
        idx = TONGUE_NAMES.index(bit.tongue)
        coord_pairs = [(0, 1), (2, 3), (4, 5), (0, 2), (1, 3), (2, 4)]
        ci, cj = coord_pairs[idx]
        sphere_3d = np.array([pos_6d[ci], pos_6d[cj], pos_6d[(ci + cj) % 6]])
        norm = np.linalg.norm(sphere_3d)
        if norm > 1e-12:
            sphere_3d /= norm
        else:
            sphere_3d = np.array([0.0, 0.0, 1.0])
        bit.sphere_position = sphere_3d

        bit.to_signal()
        return bit

    def dress_bytes(self, data: bytes) -> List[GeometricDressedBit]:
        """Dress a sequence of bytes."""
        dressed = []
        for i, byte_val in enumerate(data):
            context = data[max(0, i - 8) : i + 8]
            dressed.append(self.dress(byte_val, i, context))
        return dressed

    def dress_string(self, text: str) -> List[GeometricDressedBit]:
        """Dress a UTF-8 string."""
        return self.dress_bytes(text.encode("utf-8"))
