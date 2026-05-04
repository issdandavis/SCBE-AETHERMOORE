"""Trichromatic Governance — hidden-band overlays for RuntimeGate.

Extends the visible six-tongue coordinate system with two hidden bands:
infrared for slow session state and ultraviolet for fast/emergent state.
The result is a deterministic 6 x 3 state that can be scored and audited
without changing the existing tongue extractor.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

PHI = 1.618033988749895
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_WEIGHTS = tuple(PHI**k for k in range(len(TONGUES)))
_MAX_TRIPLET_STD = float(np.std(np.array([0.0, 0.0, 1.0], dtype=np.float32)))
_MAX_BRIDGE_NORM = math.sqrt(3.0)


@dataclass(frozen=True)
class ColorTriplet:
    ir: float
    visible: float
    uv: float

    @property
    def values(self) -> Tuple[float, float, float]:
        return (self.ir, self.visible, self.uv)

    def matches(self, other: "ColorTriplet", tolerance: float = 0.15) -> Tuple[bool, bool, bool]:
        return (
            abs(self.ir - other.ir) < tolerance,
            abs(self.visible - other.visible) < tolerance,
            abs(self.uv - other.uv) < tolerance,
        )


@dataclass(frozen=True)
class TongueTriplet:
    tongue: str
    color: ColorTriplet
    phi_weight: float


@dataclass(frozen=True)
class TrichromaticState:
    tongues: Tuple[TongueTriplet, ...]
    bridges: Dict[str, Tuple[float, float, float]]
    vector: Tuple[float, ...]
    state_hash: str


@dataclass(frozen=True)
class TrichromaticScores:
    triplet_coherence_score: float
    lattice_energy_score: float
    whole_state_anomaly_score: float
    risk_score: float
    strongest_bridge: str
    strongest_bridge_norm: float


@dataclass(frozen=True)
class ForgeryMatchReport:
    ir_match: int
    visible_match: int
    uv_match: int
    full_match: int
    strongest_bridge_delta: float


class TrichromaticGovernanceEngine:
    """Computes hidden-band state and risk scores from RuntimeGate outputs."""

    def __init__(
        self,
        *,
        tongues: Sequence[str] = TONGUES,
        phi_weights: Sequence[float] = TONGUE_WEIGHTS,
        anomaly_scale: float = 0.20,
        coherence_weight: float = 0.45,
        lattice_weight: float = 0.25,
        anomaly_weight: float = 0.30,
    ) -> None:
        self._tongues = tuple(tongues)
        self._phi_weights = tuple(phi_weights)
        self._anomaly_scale = max(0.05, float(anomaly_scale))
        self._coherence_weight = float(coherence_weight)
        self._lattice_weight = float(lattice_weight)
        self._anomaly_weight = float(anomaly_weight)
        self._state_centroid: Optional[np.ndarray] = None
        self._state_count = 0

    def reset(self) -> None:
        self._state_centroid = None
        self._state_count = 0

    def build_state(
        self,
        coords: Sequence[float],
        cost: float,
        spin_magnitude: int,
        trust_history: Sequence[int],
        cumulative_cost: float,
        session_query_count: int,
    ) -> TrichromaticState:
        coord_list = [float(c) for c in coords]
        tongue_triplets: List[TongueTriplet] = []
        for idx, tongue in enumerate(self._tongues):
            visible = max(0.0, min(1.0, coord_list[idx]))
            ir = self._compute_ir_band(idx, trust_history, cumulative_cost, session_query_count)
            uv = self._compute_uv_band(idx, visible, coord_list, spin_magnitude, cost)
            tongue_triplets.append(
                TongueTriplet(
                    tongue=tongue,
                    color=ColorTriplet(
                        ir=round(ir, 4),
                        visible=round(visible, 4),
                        uv=round(uv, 4),
                    ),
                    phi_weight=self._phi_weights[idx],
                )
            )

        bridges: Dict[str, Tuple[float, float, float]] = {}
        for i, left in enumerate(tongue_triplets):
            for j in range(i + 1, len(tongue_triplets)):
                right = tongue_triplets[j]
                phi_bridge = PHI ** abs(i - j)
                ir_bridge = abs(left.color.ir * right.color.visible + right.color.ir * left.color.visible) * phi_bridge
                vis_bridge = abs(left.color.visible * right.color.uv + right.color.visible * left.color.uv) * phi_bridge
                uv_bridge = abs(left.color.uv * right.color.ir + right.color.uv * left.color.ir) * phi_bridge
                max_bridge = PHI**5
                bridges[f"{left.tongue}-{right.tongue}"] = (
                    round(min(1.0, ir_bridge / max_bridge), 4),
                    round(min(1.0, vis_bridge / max_bridge), 4),
                    round(min(1.0, uv_bridge / max_bridge), 4),
                )

        vector: List[float] = []
        for tongue_triplet in tongue_triplets:
            vector.extend(tongue_triplet.color.values)
        for key in sorted(bridges):
            vector.extend(bridges[key])

        state_str = json.dumps(
            {
                "triplets": [(t.tongue, t.color.values) for t in tongue_triplets],
                "bridges": {key: bridges[key] for key in sorted(bridges)},
            },
            sort_keys=True,
        )

        return TrichromaticState(
            tongues=tuple(tongue_triplets),
            bridges=bridges,
            vector=tuple(vector),
            state_hash=hashlib.blake2s(state_str.encode(), digest_size=16).hexdigest(),
        )

    def score_state(self, state: TrichromaticState) -> TrichromaticScores:
        triplet_scores: List[float] = []
        triplet_weights: List[float] = []
        for tongue_triplet in state.tongues:
            values = np.asarray(tongue_triplet.color.values, dtype=np.float32)
            coherence = 1.0 - (float(np.std(values)) / _MAX_TRIPLET_STD)
            triplet_scores.append(max(0.0, min(1.0, coherence)))
            triplet_weights.append(tongue_triplet.phi_weight)

        normalized_weights = np.asarray(triplet_weights, dtype=np.float64)
        normalized_weights /= float(np.sum(normalized_weights))
        triplet_coherence = float(np.dot(triplet_scores, normalized_weights))

        strongest_bridge = "none"
        strongest_bridge_norm = 0.0
        bridge_norms: List[float] = []
        for key, bands in state.bridges.items():
            norm = float(np.linalg.norm(np.asarray(bands, dtype=np.float32)) / _MAX_BRIDGE_NORM)
            bridge_norms.append(norm)
            if norm > strongest_bridge_norm:
                strongest_bridge_norm = norm
                strongest_bridge = key
        lattice_energy_score = float(np.mean(bridge_norms)) if bridge_norms else 0.0

        if self._state_centroid is None:
            whole_state_anomaly = 0.0
        else:
            vec = np.asarray(state.vector, dtype=np.float32)
            dist = float(np.linalg.norm(vec - self._state_centroid) / math.sqrt(len(vec)))
            whole_state_anomaly = min(1.0, dist / self._anomaly_scale)

        risk_score = min(
            1.0,
            self._coherence_weight * (1.0 - triplet_coherence)
            + self._lattice_weight * lattice_energy_score
            + self._anomaly_weight * whole_state_anomaly,
        )

        return TrichromaticScores(
            triplet_coherence_score=triplet_coherence,
            lattice_energy_score=lattice_energy_score,
            whole_state_anomaly_score=whole_state_anomaly,
            risk_score=risk_score,
            strongest_bridge=strongest_bridge,
            strongest_bridge_norm=strongest_bridge_norm,
        )

    def update_baseline(self, state: TrichromaticState) -> None:
        vec = np.asarray(state.vector, dtype=np.float32)
        if self._state_centroid is None:
            self._state_centroid = vec.copy()
            self._state_count = 1
            return

        n = self._state_count + 1
        self._state_centroid = self._state_centroid * ((n - 1) / n) + vec / n
        self._state_count = n

    def visible_only_forgery_report(
        self, state: TrichromaticState, *, seed: int = 42, tolerance: float = 0.15
    ) -> ForgeryMatchReport:
        rng = np.random.default_rng(seed)
        ir_match = 0
        visible_match = 0
        uv_match = 0
        full_match = 0

        for tongue_triplet in state.tongues:
            forged = ColorTriplet(
                ir=round(float(rng.uniform(0.0, 1.0)), 4),
                visible=tongue_triplet.color.visible,
                uv=round(float(rng.uniform(0.0, 1.0)), 4),
            )
            ir_ok, vis_ok, uv_ok = tongue_triplet.color.matches(forged, tolerance=tolerance)
            if ir_ok:
                ir_match += 1
            if vis_ok:
                visible_match += 1
            if uv_ok:
                uv_match += 1
            if ir_ok and vis_ok and uv_ok:
                full_match += 1

        forged_triplets = [
            TongueTriplet(
                tongue=t.tongue,
                color=ColorTriplet(
                    ir=round(float(rng.uniform(0.0, 1.0)), 4),
                    visible=t.color.visible,
                    uv=round(float(rng.uniform(0.0, 1.0)), 4),
                ),
                phi_weight=t.phi_weight,
            )
            for t in state.tongues
        ]
        real_bridge = self._strongest_bridge_norm(state.bridges)
        forged_bridges = self._build_bridges(forged_triplets)
        forged_bridge = self._strongest_bridge_norm(forged_bridges)
        forged_bridge_delta = abs(real_bridge - forged_bridge)

        return ForgeryMatchReport(
            ir_match=ir_match,
            visible_match=visible_match,
            uv_match=uv_match,
            full_match=full_match,
            strongest_bridge_delta=forged_bridge_delta,
        )

    def _compute_ir_band(
        self,
        tongue_idx: int,
        trust_history: Sequence[int],
        cumulative_cost: float,
        session_query_count: int,
    ) -> float:
        if trust_history:
            recent = trust_history[-10:]
            trust_momentum = (sum(recent) + len(recent)) / (2 * len(recent))
        else:
            trust_momentum = 0.5

        cost_pressure = min(1.0, cumulative_cost / 500.0)
        depth_signal = min(1.0, session_query_count / 50.0)
        phi_mod = (PHI**tongue_idx) / (PHI**5)
        ir = 0.4 * trust_momentum + 0.3 * (1.0 - cost_pressure) + 0.2 * depth_signal + 0.1 * phi_mod
        return max(0.0, min(1.0, ir))

    def _compute_uv_band(
        self,
        tongue_idx: int,
        visible_coord: float,
        coords_all: Sequence[float],
        spin_magnitude: int,
        cost: float,
    ) -> float:
        mean_coord = float(np.mean(coords_all))
        spike = abs(visible_coord - mean_coord)
        coord_std = float(np.std(coords_all))
        null_space = max(0.0, 1.0 - coord_std * 10.0)
        spin_energy = min(1.0, spin_magnitude / 6.0)
        cost_harmonic = abs(math.sin(cost * PHI))
        adjacent_idx = (tongue_idx + 1) % len(self._tongues)
        interference = visible_coord * float(coords_all[adjacent_idx])
        uv = 0.25 * spike + 0.2 * null_space + 0.2 * spin_energy + 0.2 * cost_harmonic + 0.15 * interference
        return max(0.0, min(1.0, uv))

    def _build_bridges(self, tongue_triplets: Sequence[TongueTriplet]) -> Dict[str, Tuple[float, float, float]]:
        bridges: Dict[str, Tuple[float, float, float]] = {}
        for i, left in enumerate(tongue_triplets):
            for j in range(i + 1, len(tongue_triplets)):
                right = tongue_triplets[j]
                phi_bridge = PHI ** abs(i - j)
                ir_bridge = abs(left.color.ir * right.color.visible + right.color.ir * left.color.visible) * phi_bridge
                vis_bridge = abs(left.color.visible * right.color.uv + right.color.visible * left.color.uv) * phi_bridge
                uv_bridge = abs(left.color.uv * right.color.ir + right.color.uv * left.color.ir) * phi_bridge
                max_bridge = PHI**5
                bridges[f"{left.tongue}-{right.tongue}"] = (
                    round(min(1.0, ir_bridge / max_bridge), 4),
                    round(min(1.0, vis_bridge / max_bridge), 4),
                    round(min(1.0, uv_bridge / max_bridge), 4),
                )
        return bridges

    @staticmethod
    def _strongest_bridge_norm(bridges: Dict[str, Tuple[float, float, float]]) -> float:
        strongest = 0.0
        for bands in bridges.values():
            norm = float(np.linalg.norm(np.asarray(bands, dtype=np.float32)) / _MAX_BRIDGE_NORM)
            if norm > strongest:
                strongest = norm
        return strongest


# ---------------------------------------------------------------------------
# Cone-extended scoring
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrichromaticConeScores:
    """Extended scoring blob that combines per-tongue band scoring with
    the tri-chromatic cone reading from ``python.scbe.tri_cone_embedding``.

    Carries both component readings plus a unified governance verdict
    so a single decision surface can be wired into the gate without the
    caller having to know about both sub-systems.
    """

    band_scores: TrichromaticScores
    cone_governance: str
    positive_membership_count: int
    shadow_membership_count: int
    cone_interference: float
    cone_plateau_imbalance: float
    cone_triple_intersection_score: float
    cone_triple_shadow_score: float
    cone_risk_score: float
    unified_governance: str
    unified_risk_score: float


def _cone_risk_score(
    band_risk: float,
    interference: float,
    plateau_imbalance: float,
) -> float:
    """Blend the existing band risk with cone-derived risk signals.

    - Band risk (the existing coherence/lattice/anomaly weighted score)
      contributes its full magnitude in [0, 1].
    - Positive interference (lit and shadow simultaneously inside their
      respective cones) is the classic adversarial-tension signal —
      contributes ``max(0, interference)`` capped at 0.3 so it cannot
      single-handedly dominate the verdict.
    - Plateau imbalance (lopsided cone activations) contributes 0.2 of
      its [0, 1] magnitude — uneven soap bubbles are uneven governance.
    """

    interference_term = min(0.3, max(0.0, float(interference)))
    plateau_term = 0.2 * max(0.0, min(1.0, float(plateau_imbalance)))
    return min(1.0, float(band_risk) + interference_term + plateau_term)


def _unified_governance(
    cone_governance: str, unified_risk: float
) -> str:
    """Pick the more conservative of (cone reading, band-risk threshold).

    The cone reading is the primary verdict. The band-risk score acts
    as a safety override: if it is high, escalate the decision toward
    QUARANTINE / DENY even when the cone reading would have been more
    permissive. This matches the SCBE convention that the tighter of
    several governance signals always wins.
    """

    # Pre-existing risk thresholds inherited from the trichromatic
    # forgery-resistance article: 0.40 = drift, 0.70 = block.
    if cone_governance == "DENY" or unified_risk >= 0.70:
        return "DENY"
    if cone_governance == "QUARANTINE" or unified_risk >= 0.40:
        return "QUARANTINE"
    if cone_governance == "ESCALATE":
        return "ESCALATE"
    return "ALLOW"


def score_state_with_cones(
    band_scores: TrichromaticScores,
    cone_signature,  # python.scbe.tri_cone_embedding.TriConeSignature
) -> TrichromaticConeScores:
    """Combine per-tongue band scoring with a tri-chromatic cone signature.

    Decoupled from ``TrichromaticGovernanceEngine`` so callers that
    already have a ``TrichromaticScores`` (e.g. from ``score_state``)
    can layer cone semantics on top without rebuilding the band state.
    The cone signature parameter is loosely typed to avoid a hard
    cross-package import; runtime duck-typing is sufficient because
    ``TriConeSignature`` is a dataclass with stable field names.
    """

    unified_risk = _cone_risk_score(
        band_scores.risk_score,
        cone_signature.interference_score,
        cone_signature.plateau_imbalance,
    )
    return TrichromaticConeScores(
        band_scores=band_scores,
        cone_governance=cone_signature.cone_governance,
        positive_membership_count=int(cone_signature.positive_membership_count),
        shadow_membership_count=int(cone_signature.shadow_membership_count),
        cone_interference=float(cone_signature.interference_score),
        cone_plateau_imbalance=float(cone_signature.plateau_imbalance),
        cone_triple_intersection_score=float(cone_signature.triple_intersection_score),
        cone_triple_shadow_score=float(cone_signature.triple_shadow_score),
        cone_risk_score=unified_risk,
        unified_governance=_unified_governance(cone_signature.cone_governance, unified_risk),
        unified_risk_score=unified_risk,
    )
