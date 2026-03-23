"""Langues Metric Dispersal — 6D Bit Spin for Holistic Storage Routing
=====================================================================

Fuses the Langues Metric Tensor (6×6 diagonal φ-weighted) with a
6D spin quantization to compute a dispersal rate that tells each
fusion surface how to distribute records.

Core idea:
  Each record's 6D tongue vector is quantized to a spin triplet
  per dimension: +1 (above centroid), 0 (near centroid), -1 (below).
  The spin pattern, weighted by the langues metric tensor, determines
  the record's "dispersal signature" — a 6-trit code that routes it
  to the correct zone (hemisphere vs cone), tongue sector, and
  Chladni access mode.

The dispersal rate D measures how evenly records spread across
the 6D spin space, weighted by the langues metric:

  D = (1/N) Σᵢ Σₗ G_ll · |s_l(i)| · |x_l(i) - μ_l|

Where:
  - G_ll = φ^l (langues metric tensor diagonal)
  - s_l(i) = spin of record i in dimension l (+1, 0, -1)
  - x_l(i) = tongue coordinate of record i in dimension l
  - μ_l = centroid of all records in dimension l

High D → records are spread far from centroid with strong spin
Low D → records cluster near centroid with weak spin

The entropy of the spin distribution H_spin tells us if all 6 tongues
are being used evenly (high entropy) or degenerate (low entropy).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Golden ratio
PHI = (1 + math.sqrt(5)) / 2

# Langues metric tensor: diagonal with φ^k weights
TONGUE_NAMES = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_WEIGHTS = tuple(PHI ** k for k in range(6))

# Tongue phases: 60° apart
TONGUE_PHASES = tuple(2.0 * math.pi * k / 6 for k in range(6))

# Tongue harmonic frequencies (musical intervals)
TONGUE_FREQUENCIES = (1.0, 9 / 8, 5 / 4, 4 / 3, 3 / 2, 5 / 3)


def build_metric_tensor() -> np.ndarray:
    """Build the 6×6 langues metric tensor G_ij = diag(φ^0, φ^1, ..., φ^5)."""
    return np.diag(TONGUE_WEIGHTS)


# =========================================================================== #
#  6D Spin Quantization
# =========================================================================== #

@dataclass(frozen=True)
class SpinVector:
    """6D spin triplet: one trit per tongue dimension."""
    spins: Tuple[int, ...]  # length 6, each in {-1, 0, +1}

    @property
    def code(self) -> str:
        """Compact string representation: e.g. '+0-+0+'."""
        return "".join({1: "+", 0: "0", -1: "-"}[s] for s in self.spins)

    @property
    def magnitude(self) -> int:
        """Count of non-zero spins."""
        return sum(abs(s) for s in self.spins)

    def metric_weighted_norm(self) -> float:
        """||s||_G = sqrt(Σ G_ll · s_l²)."""
        return math.sqrt(sum(
            TONGUE_WEIGHTS[l] * self.spins[l] ** 2
            for l in range(6)
        ))


def quantize_spin(
    tongue_coords: List[float],
    centroid: List[float],
    threshold: float = 0.05,
) -> SpinVector:
    """Quantize a 6D tongue vector to a spin triplet relative to centroid.

    Args:
        tongue_coords: 6D vector [KO, AV, RU, CA, UM, DR]
        centroid: 6D centroid of the record set
        threshold: dead zone around centroid → spin 0

    Returns:
        SpinVector with 6 trits
    """
    spins = []
    for l in range(6):
        diff = tongue_coords[l] - centroid[l]
        if diff > threshold:
            spins.append(1)
        elif diff < -threshold:
            spins.append(-1)
        else:
            spins.append(0)
    return SpinVector(spins=tuple(spins))


# =========================================================================== #
#  Dispersal Rate
# =========================================================================== #

@dataclass
class DispersalReport:
    """Results of dispersal analysis over a set of records."""
    record_count: int
    centroid: List[float]
    dispersal_rate: float       # D — metric-weighted spread
    spin_entropy: float         # H — entropy of spin code distribution [0, 1]
    dominant_tongue: str        # which tongue has highest weighted deviation
    spin_distribution: Dict[str, int]  # spin code → count
    tongue_dispersals: Dict[str, float]  # per-tongue dispersal contribution
    effective_dimension: float  # how many tongues are "active" (non-zero spin)


def compute_dispersal(
    tongue_vectors: List[List[float]],
    threshold: float = 0.05,
) -> DispersalReport:
    """Compute the holistic dispersal rate for a set of records.

    D = (1/N) Σᵢ Σₗ G_ll · |s_l(i)| · |x_l(i) - μ_l|

    Also computes spin entropy and per-tongue breakdown.
    """
    n = len(tongue_vectors)
    if n == 0:
        return DispersalReport(
            record_count=0, centroid=[0.0] * 6, dispersal_rate=0.0,
            spin_entropy=0.0, dominant_tongue="KO",
            spin_distribution={}, tongue_dispersals={},
            effective_dimension=0.0,
        )

    mat = np.array(tongue_vectors, dtype=float)
    centroid = mat.mean(axis=0).tolist()

    # Quantize all records to spin vectors
    spins = [quantize_spin(tv, centroid, threshold) for tv in tongue_vectors]

    # Dispersal rate: metric-weighted deviation * spin magnitude
    G = build_metric_tensor()
    dispersal_sum = 0.0
    tongue_sums = [0.0] * 6

    for i, (tv, sv) in enumerate(zip(tongue_vectors, spins)):
        for l in range(6):
            contrib = G[l, l] * abs(sv.spins[l]) * abs(tv[l] - centroid[l])
            dispersal_sum += contrib
            tongue_sums[l] += contrib

    dispersal_rate = dispersal_sum / n

    # Per-tongue dispersal
    tongue_dispersals = {
        TONGUE_NAMES[l]: round(tongue_sums[l] / n, 6)
        for l in range(6)
    }

    # Dominant tongue: highest per-tongue dispersal
    dominant_idx = tongue_sums.index(max(tongue_sums))
    dominant_tongue = TONGUE_NAMES[dominant_idx]

    # Spin distribution: count unique spin codes
    spin_codes: Dict[str, int] = {}
    for sv in spins:
        code = sv.code
        spin_codes[code] = spin_codes.get(code, 0) + 1

    # Spin entropy (normalized to [0, 1])
    # Maximum entropy = log(n_unique_codes) if all codes equally likely
    if len(spin_codes) <= 1:
        spin_entropy = 0.0
    else:
        probs = [count / n for count in spin_codes.values()]
        raw_entropy = -sum(p * math.log(p + 1e-15) for p in probs)
        max_entropy = math.log(len(spin_codes))
        spin_entropy = raw_entropy / max(max_entropy, 1e-15)

    # Effective dimension: how many tongues have non-zero spin in most records
    tongue_active_counts = [0] * 6
    for sv in spins:
        for l in range(6):
            if sv.spins[l] != 0:
                tongue_active_counts[l] += 1
    effective_dimension = sum(
        c / n for c in tongue_active_counts
    )

    return DispersalReport(
        record_count=n,
        centroid=[round(c, 6) for c in centroid],
        dispersal_rate=round(dispersal_rate, 6),
        spin_entropy=round(spin_entropy, 4),
        dominant_tongue=dominant_tongue,
        spin_distribution=spin_codes,
        tongue_dispersals=tongue_dispersals,
        effective_dimension=round(effective_dimension, 4),
    )


# =========================================================================== #
#  Dispersal-Routed Insert
# =========================================================================== #

def dispersal_route(
    tongue_coords: List[float],
    centroid: List[float],
    threshold: float = 0.05,
) -> Dict[str, Any]:
    """Route a single record based on its spin vector.

    Returns routing advice:
      - zone: 'hemisphere' (low spin magnitude) or 'cone' (high spin magnitude)
      - dominant_tongue: which tongue to use for Chladni mode
      - spin_code: the 6-trit code
      - dispersal_cost: metric-weighted deviation
    """
    sv = quantize_spin(tongue_coords, centroid, threshold)
    G = build_metric_tensor()

    # Per-record dispersal cost
    cost = sum(
        G[l, l] * abs(sv.spins[l]) * abs(tongue_coords[l] - centroid[l])
        for l in range(6)
    )

    # Route decision: high magnitude → cone, low → hemisphere
    if sv.magnitude >= 4:
        zone = "cone"
    elif sv.magnitude <= 2:
        zone = "hemisphere"
    else:
        zone = "cone" if cost > 0.5 else "hemisphere"

    # Dominant tongue: highest weighted spin deviation
    weighted_devs = [
        TONGUE_WEIGHTS[l] * abs(sv.spins[l]) * abs(tongue_coords[l] - centroid[l])
        for l in range(6)
    ]
    dominant_idx = weighted_devs.index(max(weighted_devs))

    return {
        "zone": zone,
        "dominant_tongue": TONGUE_NAMES[dominant_idx],
        "spin_code": sv.code,
        "spin_magnitude": sv.magnitude,
        "dispersal_cost": round(cost, 6),
        "spin_vector": list(sv.spins),
    }
