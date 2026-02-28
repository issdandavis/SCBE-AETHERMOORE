"""
Quasicrystal Authentication System for SCBE-AETHERMOORE

Icosahedral quasicrystal lattice verification with tri-manifold governance.

This module implements a post-quantum authentication layer that projects 6D SCBE
gate vectors into an icosahedral quasicrystal lattice (6D -> 3D via cut-and-project)
and applies balanced-ternary governance decisions through a federated multi-tier
evaluation matrix.

Key components:
    - QuasicrystalLattice: 6D -> 3D icosahedral projection with acceptance radius
      validation, entropy-driven phason rekeying, and FFT-based crystalline defect
      detection.
    - TriManifoldState: Balanced ternary governance state derived from paired SCBE
      gate dimensions via negabinary -> balanced ternary conversion.
    - FederatedMatrix / FederatedNode: Multi-tier governance evaluation where any
      DENY at any tier vetoes the entire request.

Mathematical basis:
    - Icosahedral projection uses the golden ratio (PHI) to generate aperiodic
      tilings in physical space (E_parallel) with an acceptance window in
      perpendicular space (E_perp).
    - Phason rekeying shifts the acceptance window using SHA-256 derived entropy,
      invalidating previously valid lattice points.
    - Crystalline defect detection uses Hanning-windowed FFT to identify periodic
      (non-quasicrystalline) patterns in gate history that signal replay attacks.

@module pqc.quasicrystal_auth
@layer Layer 5 (Hyperbolic), Layer 9 (Spectral), Layer 13 (Governance)
@version 1.0.0
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.fft import fft, fftfreq

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI: float = (1.0 + np.sqrt(5.0)) / 2.0
"""Golden ratio (1.6180339887...)."""

TAU: float = 2.0 * np.pi
"""Full circle in radians."""


# ---------------------------------------------------------------------------
# QuasicrystalLattice
# ---------------------------------------------------------------------------


class QuasicrystalLattice:
    """SCBE v3.0: Icosahedral Quasicrystal Verification System.

    Projects 6D integer gate vectors through parallel (E_par) and perpendicular
    (E_perp) icosahedral basis matrices.  A gate vector is *valid* when its
    perpendicular-space projection falls within the acceptance radius of the
    current phason strain origin.

    Attributes:
        a: Lattice constant (default 1.0).
        acceptance_radius: Maximum allowed perpendicular-space distance.
        phason_strain: Current 3D phason strain offset (shifted by rekeying).
        M_par: 3x6 parallel-space projection matrix.
        M_perp: 3x6 perpendicular-space projection matrix.
    """

    def __init__(self, lattice_constant: float = 1.0) -> None:
        self.a: float = lattice_constant
        self.acceptance_radius: float = 1.5 * self.a
        self.phason_strain: np.ndarray = np.zeros(3)
        self.M_par: np.ndarray
        self.M_perp: np.ndarray
        self.M_par, self.M_perp = self._generate_basis_matrices()

    # -- internal helpers --------------------------------------------------

    def _generate_basis_matrices(self) -> Tuple[np.ndarray, np.ndarray]:
        """Build the 3x6 icosahedral projection matrices.

        Returns:
            Tuple of (M_par, M_perp) each with shape (3, 6).
        """
        norm: float = 1.0 / np.sqrt(1.0 + PHI ** 2)

        e_par: np.ndarray = (
            np.array(
                [
                    [1, PHI, 0],
                    [-1, PHI, 0],
                    [0, 1, PHI],
                    [0, -1, PHI],
                    [PHI, 0, 1],
                    [PHI, 0, -1],
                ]
            ).T
            * norm
        )

        e_perp: np.ndarray = (
            np.array(
                [
                    [1, -1.0 / PHI, 0],
                    [-1, -1.0 / PHI, 0],
                    [0, 1, -1.0 / PHI],
                    [0, -1, -1.0 / PHI],
                    [-1.0 / PHI, 0, 1],
                    [-1.0 / PHI, 0, -1],
                ]
            ).T
            * norm
        )

        return e_par, e_perp

    # -- public API --------------------------------------------------------

    def map_gates_to_lattice(
        self, gate_vector: List[int]
    ) -> Tuple[np.ndarray, np.ndarray, bool]:
        """Project a 6D gate vector into the quasicrystal lattice.

        Args:
            gate_vector: Six integer gate values (one per SCBE tongue dimension).

        Returns:
            Tuple of (r_physical, r_perpendicular, is_valid) where:
                - r_physical: 3D physical-space projection.
                - r_perpendicular: 3D perpendicular-space projection (raw).
                - is_valid: True if the perp distance from the phason strain
                  origin is within the acceptance radius.
        """
        n: np.ndarray = np.array(gate_vector, dtype=float)
        r_phys: np.ndarray = self.M_par @ n
        r_perp_raw: np.ndarray = self.M_perp @ n
        distance: float = float(np.linalg.norm(r_perp_raw - self.phason_strain))
        is_valid: bool = distance < self.acceptance_radius
        return r_phys, r_perp_raw, is_valid

    def apply_phason_rekey(self, entropy_seed: bytes) -> None:
        """Shift the acceptance window using SHA-256 derived entropy.

        After rekeying, previously valid lattice points may become invalid
        because the phason strain origin has moved.

        Args:
            entropy_seed: Arbitrary bytes used as SHA-256 input.
        """
        h: bytes = hashlib.sha256(entropy_seed).digest()
        v: np.ndarray = np.array(
            [
                int.from_bytes(h[0:4], "big") / (2 ** 32) * 2 - 1,
                int.from_bytes(h[4:8], "big") / (2 ** 32) * 2 - 1,
                int.from_bytes(h[8:12], "big") / (2 ** 32) * 2 - 1,
            ]
        )
        self.phason_strain = v * self.acceptance_radius * 2.0

    def detect_crystalline_defects(
        self, history_vectors: List[List[int]]
    ) -> float:
        """Detect periodic (crystalline) patterns in gate history via FFT.

        Quasicrystalline (aperiodic) gate sequences are expected; periodic
        repetition signals a replay or brute-force attack.

        Args:
            history_vectors: List of 6D gate vectors observed over time.

        Returns:
            Defect score in [0.0, 1.0].  Higher values indicate stronger
            periodic (non-quasicrystalline) structure.  Returns 0.0 if
            fewer than 32 samples are provided.
        """
        if len(history_vectors) < 32:
            return 0.0

        norms: np.ndarray = np.array(
            [np.linalg.norm(v) for v in history_vectors]
        )
        N: int = len(norms)
        window: np.ndarray = np.hanning(N)
        windowed_norms: np.ndarray = norms * window

        yf: np.ndarray = fft(windowed_norms)
        xf: np.ndarray = fftfreq(N, 1)

        power_spectrum: np.ndarray = np.abs(yf[1 : N // 2]) ** 2
        frequencies: np.ndarray = xf[1 : N // 2]

        if len(power_spectrum) == 0 or np.sum(power_spectrum) == 0:
            return 0.0

        dominant_freq_idx: int = int(np.argmax(power_spectrum))
        dominant_frequency: float = float(frequencies[dominant_freq_idx])
        dominant_power: float = float(power_spectrum[dominant_freq_idx])
        total_power: float = float(np.sum(power_spectrum))
        normalized_dominant_power: float = dominant_power / total_power

        crystallinity_threshold_freq: float = 0.1
        crystallinity_threshold_power: float = 0.5

        defect_score: float = 0.0
        if (
            dominant_frequency > 0
            and dominant_frequency < crystallinity_threshold_freq
            and normalized_dominant_power > crystallinity_threshold_power
        ):
            defect_score = min(1.0, normalized_dominant_power * 1.5)

        return defect_score


# ---------------------------------------------------------------------------
# Negabinary / Balanced Ternary converters
# ---------------------------------------------------------------------------


def int_to_negabinary(n: int) -> str:
    """Convert an integer to its negabinary (base -2) string representation.

    Every integer has a unique negabinary form using digits {0, 1} with no
    explicit sign bit.

    Args:
        n: Integer to convert.

    Returns:
        MSB-first string of '0' and '1' characters.
    """
    if n == 0:
        return "0"
    result: str = ""
    while n != 0:
        n, remainder = divmod(n, -2)
        if remainder < 0:
            n += 1
            remainder += 2
        result = str(remainder) + result
    return result


def negabinary_to_balanced_ternary(negabin_str: str) -> List[int]:
    """Convert a negabinary string to balanced ternary trits.

    Performs negabinary -> integer -> balanced ternary conversion.

    Args:
        negabin_str: MSB-first negabinary string (digits '0' and '1').

    Returns:
        List of trits in {-1, 0, +1}, MSB-first.  Returns [0] for zero.
    """
    if not negabin_str:
        return [0]

    # Decode negabinary to integer
    n: int = 0
    for i, digit in enumerate(reversed(negabin_str)):
        if digit == "1":
            n += (-2) ** i

    if n == 0:
        return [0]

    # Encode integer as balanced ternary (LSB-first, then reverse)
    trits: List[int] = []
    while n != 0:
        remainder: int = n % 3
        if remainder == 2:
            trits.append(-1)
            n = (n + 1) // 3
        else:
            trits.append(remainder)
            n //= 3

    return trits[::-1]


# ---------------------------------------------------------------------------
# TriManifoldState
# ---------------------------------------------------------------------------


@dataclass
class TriManifoldState:
    """Balanced ternary governance state across three manifold dimensions.

    Each trit encodes a governance signal: +1 (positive), 0 (neutral), -1 (negative).

    Attributes:
        t1: First manifold dimension trit (gates 0+1).
        t2: Second manifold dimension trit (gates 2+3).
        t3: Third manifold dimension trit (gates 4+5).  Acts as security override:
            t3 == -1 forces DENY regardless of other dimensions.
    """

    t1: int
    t2: int
    t3: int


def map_gates_to_trimanifold(gate_vector: List[int]) -> TriManifoldState:
    """Map a 6D SCBE gate vector to a tri-manifold governance state.

    Gates are paired into three dimensions:
        d1 = gate[0] + gate[1]   (KO + AV)
        d2 = gate[2] + gate[3]   (RU + CA)
        d3 = gate[4] + gate[5]   (UM + DR)

    Each dimension value is converted through negabinary -> balanced ternary,
    and the most significant trit is taken as the manifold coordinate.

    Args:
        gate_vector: Six integer gate values.

    Returns:
        TriManifoldState with trits derived from each dimension pair.
    """
    d1_val: int = gate_vector[0] + gate_vector[1]
    d2_val: int = gate_vector[2] + gate_vector[3]
    d3_val: int = gate_vector[4] + gate_vector[5]

    dims: List[int] = [d1_val, d2_val, d3_val]
    state_trits: List[int] = []

    for val in dims:
        nb_str: str = int_to_negabinary(val)
        trits: List[int] = negabinary_to_balanced_ternary(nb_str)
        if not trits or (len(trits) == 1 and trits[0] == 0):
            state_trits.append(0)
        else:
            state_trits.append(trits[0])  # Most significant trit

    return TriManifoldState(t1=state_trits[0], t2=state_trits[1], t3=state_trits[2])


def apply_tri_manifold_governance(state: TriManifoldState) -> str:
    """Apply governance logic to a tri-manifold state.

    Decision rules:
        1. If t3 == -1: always DENY (security override dimension).
        2. If sum(t1, t2, t3) > 0: ALLOW.
        3. If sum(t1, t2, t3) < 0: DENY.
        4. If sum == 0: QUARANTINE.

    Args:
        state: Tri-manifold governance state.

    Returns:
        One of "ALLOW", "QUARANTINE", or "DENY".
    """
    if state.t3 == -1:
        return "DENY"

    score: int = state.t1 + state.t2 + state.t3
    if score > 0:
        return "ALLOW"
    elif score < 0:
        return "DENY"
    else:
        return "QUARANTINE"


# ---------------------------------------------------------------------------
# TriManifoldMatrix / FederatedMatrix
# ---------------------------------------------------------------------------


class TriManifoldMatrix:
    """A named governance evaluation tier.

    Each tier independently evaluates a TriManifoldState using the standard
    tri-manifold governance rules.

    Attributes:
        name: Human-readable tier identifier (e.g. "local", "regional", "global").
    """

    def __init__(self, name: str) -> None:
        self.name: str = name

    def evaluate(self, state: TriManifoldState) -> str:
        """Evaluate the tri-manifold state through this tier.

        Args:
            state: Governance state to evaluate.

        Returns:
            One of "ALLOW", "QUARANTINE", or "DENY".
        """
        return apply_tri_manifold_governance(state)


class FederatedMatrix:
    """Multi-tier federated governance evaluator.

    Aggregates decisions from multiple TriManifoldMatrix tiers.  A single DENY
    from any tier vetoes the request; a single QUARANTINE triggers quarantine
    unless overridden by a DENY elsewhere.

    Attributes:
        tiers: Ordered list of governance evaluation tiers.
    """

    def __init__(self) -> None:
        self.tiers: List[TriManifoldMatrix] = []

    def add_tier(self, tier: TriManifoldMatrix) -> None:
        """Append a governance tier to the federation.

        Args:
            tier: Governance tier to add.
        """
        self.tiers.append(tier)

    def evaluate_all(self, state: TriManifoldState) -> List[str]:
        """Evaluate the state through every tier.

        Args:
            state: Governance state to evaluate.

        Returns:
            List of decisions, one per tier, in registration order.
        """
        return [tier.evaluate(state) for tier in self.tiers]


# ---------------------------------------------------------------------------
# FederatedNode / analyze_federated_6d
# ---------------------------------------------------------------------------


@dataclass
class FederatedNode:
    """A node in the federated governance network.

    Attributes:
        node_id: Unique identifier for this node.
        gate_vector: 6D SCBE gate vector for this node's current state.
    """

    node_id: str
    gate_vector: List[int]


def analyze_federated_6d(
    nodes: List[FederatedNode], federation: FederatedMatrix
) -> Dict[str, str]:
    """Run full 6D federated governance analysis across all nodes.

    For each node:
        1. Map the 6D gate vector to a tri-manifold state.
        2. Evaluate through every federation tier.
        3. Apply consensus: any DENY -> DENIED, any QUARANTINE -> QUARANTINED,
           else ALLOWED.

    Args:
        nodes: List of federated nodes to evaluate.
        federation: Multi-tier federation evaluator.

    Returns:
        Dict mapping node_id -> consensus decision string
        ("ALLOWED", "QUARANTINED", or "DENIED").
    """
    results_summary: Dict[str, str] = {}

    for node in nodes:
        manifold_state: TriManifoldState = map_gates_to_trimanifold(node.gate_vector)
        tier_decisions: List[str] = federation.evaluate_all(manifold_state)

        if "DENY" in tier_decisions:
            final_consensus: str = "DENIED"
        elif "QUARANTINE" in tier_decisions:
            final_consensus = "QUARANTINED"
        else:
            final_consensus = "ALLOWED"

        results_summary[node.node_id] = final_consensus

    return results_summary
