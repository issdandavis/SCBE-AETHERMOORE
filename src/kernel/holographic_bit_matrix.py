"""
Holographic Bit-Matrix Architecture
=====================================

Binary substrate with holographically distributed multi-state encoding,
routed through geometric layers. Sits UNDER the ScatteredAttentionSphere
as Layer 0 — the structural foundation.

Architecture stack:
  Layer 0 — Bit Matrix (binary substrate, deterministic, fast)
  Layer 1 — Trit Modulation (tongue activation/null encoding, -1/0/+1)
  Layer 2 — Holographic Scatter Field (distributed wave encoding)
  Layer 3 — Geometric Routing (hyperbolic + tongues via ScatteredAttentionSphere)
  Layer Omega — Decision (GovernanceCoin + harmonic wall)

Key insight: each bit is NOT just 0/1 — it's an entry point into a
distributed holographic field. Information is reconstructed from patterns,
not stored locally. This gives:
  - Speed (binary hardware substrate)
  - Flexibility (holographic distributed encoding)
  - Robustness (no single point of failure)
  - Absence awareness (null tongues encoded structurally)

References:
  - Grok session analysis (April 3, 2026)
  - HQNN + Polyhedral Light-Path Router research
  - Tensor Network Integration Analysis
  - docs/specs/GEOMETRIC_THOUGHT_EFFICIENCY_TRAINING.md
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

PHI = 1.618033988749895

# Sacred Tongue longitudes match scattered_sphere.py
TONGUE_LONGITUDES = {
    "KO": 0.0,
    "AV": math.pi / 3,
    "RU": 2 * math.pi / 3,
    "CA": math.pi,
    "UM": 4 * math.pi / 3,
    "DR": 5 * math.pi / 3,
}

TONGUE_WEIGHTS = {
    "KO": 1.0,
    "AV": PHI,
    "RU": PHI ** 2,
    "CA": PHI ** 3,
    "UM": PHI ** 4,
    "DR": PHI ** 5,
}

TONGUE_KEYS = list(TONGUE_LONGITUDES.keys())


@dataclass
class HoloState:
    """Complete state of the holographic bit-matrix at a moment."""
    bit_density: float
    trit_distribution: dict[str, int]
    holo_energy: float
    tongue_activation: dict[str, float]
    tongues_active: list[str]
    tongues_null: list[str]
    mera_level: int
    reconstruction_error: float
    governance_cost: float


class HolographicBitMatrix:
    """
    Binary substrate with holographically distributed state encoding.

    The bit matrix is Layer 0 — the structural bones.
    The trit overlay is Layer 1 — tongue activation/null patterns.
    The holographic field is Layer 2 — distributed meaning.

    Connects to ScatteredAttentionSphere (Layer 3) via the encode/decode
    interface: sphere.scatter() accepts the reconstructed weight matrix
    from this layer.
    """

    def __init__(self, size: int = 32):
        self.size = size

        # L0: Binary substrate — deterministic seed, not random
        self.bit_matrix = np.zeros((size, size), dtype=np.int8)
        self._init_bit_substrate()

        # L1: Trit modulation — tongue activation overlay
        self.trit_matrix = np.zeros((size, size), dtype=np.int8)

        # L2: Holographic field — distributed complex encoding
        self.holo_field = np.zeros((size, size), dtype=np.complex128)

        # Tongue activation state
        self.tongue_activation: dict[str, float] = {t: 0.0 for t in TONGUE_KEYS}

        # MERA compression level (0=full, 3=maximally compressed)
        self.mera_level: int = 2

    def _init_bit_substrate(self) -> None:
        """Initialize bit matrix with golden-angle structured pattern.

        Not random — uses the golden angle (137.5 deg) to create a
        quasi-uniform coverage pattern. Same math as sunflower spirals
        and the existing golden angle scatter in ScatteredAttentionSphere.
        """
        golden_angle = 137.5 * math.pi / 180
        for i in range(self.size):
            for j in range(self.size):
                # Deterministic: bit is 1 if position falls on golden spiral
                angle = (i * self.size + j) * golden_angle
                radius = math.sqrt(i * self.size + j + 1) / self.size
                # Threshold: ~61.8% ones (golden ratio)
                self.bit_matrix[i, j] = 1 if (math.sin(angle) * radius) > -0.118 else 0

    # ── Layer 1: Trit Modulation ──

    def modulate_tongues(self, active_tongues: list[str]) -> None:
        """Apply tongue activation as trit overlay on bit matrix.

        Active tongues get +1, null tongues get -1, uncertain get 0.
        This IS the absence encoding — the null pattern is baked in.
        """
        self.tongue_activation = {t: 0.0 for t in TONGUE_KEYS}

        for tongue in active_tongues:
            if tongue in TONGUE_WEIGHTS:
                self.tongue_activation[tongue] = TONGUE_WEIGHTS[tongue]

        # Map tongue activation to spatial trit pattern
        for i in range(self.size):
            for j in range(self.size):
                tongue_idx = (i * self.size + j) % 6
                tongue = TONGUE_KEYS[tongue_idx]

                if tongue in active_tongues:
                    self.trit_matrix[i, j] = 1  # active
                else:
                    self.trit_matrix[i, j] = -1  # null (absence signal)

    # ── Layer 2: Holographic Scatter ──

    def encode(self, signal: np.ndarray) -> None:
        """Encode a signal vector into the holographic field.

        Each signal element creates a wave that scatters across the
        entire matrix — information is distributed, not local.
        Uses hyperbolic phase instead of linear (Grok's upgrade path).

        Args:
            signal: 1D array of values to encode holographically
        """
        self.holo_field = np.zeros((self.size, self.size), dtype=np.complex128)

        for k, val in enumerate(signal):
            if abs(val) < 1e-10:
                continue

            # Base angle from signal position
            base_angle = 2 * math.pi * k / len(signal)

            # Map to nearest tongue for directional encoding
            tongue_idx = k % 6
            tongue = TONGUE_KEYS[tongue_idx]
            tongue_weight = TONGUE_WEIGHTS[tongue]
            tongue_long = TONGUE_LONGITUDES[tongue]

            for i in range(self.size):
                for j in range(self.size):
                    # Hyperbolic phase (not linear) — distance grows exponentially
                    # from center, matching Poincare ball geometry
                    cx, cy = self.size / 2, self.size / 2
                    dx, dy = (i - cx) / self.size, (j - cy) / self.size
                    r_sq = dx * dx + dy * dy

                    # Poincare-inspired: phase increases near boundary
                    if r_sq < 1.0:
                        hyper_factor = 1.0 / (1.0 - r_sq + 0.01)
                    else:
                        hyper_factor = 100.0

                    phase = base_angle + tongue_long + hyper_factor * 0.01

                    # Trit modulation: active tongues amplify, null tongues dampen
                    trit = float(self.trit_matrix[i, j])
                    amplitude = val * (1.0 + 0.3 * trit) / tongue_weight

                    self.holo_field[i, j] += amplitude * np.exp(1j * phase)

    def decode(self, signal_length: int = 16) -> np.ndarray:
        """Reconstruct signal from holographic field.

        Projects the distributed field back into a 1D signal.
        The reconstruction quality depends on how many tongues
        are active — null tongues create intentional gaps.
        """
        result = np.zeros(signal_length)

        for k in range(signal_length):
            base_angle = 2 * math.pi * k / signal_length
            tongue_long = TONGUE_LONGITUDES[TONGUE_KEYS[k % 6]]

            # Project: sum field values that align with this signal's phase
            projection = 0.0
            for i in range(self.size):
                for j in range(self.size):
                    cx, cy = self.size / 2, self.size / 2
                    dx, dy = (i - cx) / self.size, (j - cy) / self.size
                    r_sq = dx * dx + dy * dy
                    if r_sq < 1.0:
                        hyper_factor = 1.0 / (1.0 - r_sq + 0.01)
                    else:
                        hyper_factor = 100.0

                    phase = base_angle + tongue_long + hyper_factor * 0.01
                    projection += np.real(self.holo_field[i, j] * np.exp(-1j * phase))

            result[k] = projection / (self.size * self.size)

        return result

    # ── MERA Compression ──

    def mera_compress(self, level: int = 2) -> np.ndarray:
        """Compress the holographic field using MERA-style renormalization.

        Level 0: Full 6-channel (size x size)
        Level 1: 3-channel paired (size/2 x size/2)
        Level 2: 3-abstract (size/4 x size/4)
        Level 3: 1-decision (size/8 x size/8)
        """
        self.mera_level = level
        field = np.abs(self.holo_field)

        for _ in range(level):
            if field.shape[0] < 4 or field.shape[1] < 4:
                break
            # Isometry: average 2x2 blocks (disentangle + contract)
            h, w = field.shape
            field = (
                field[0:h:2, 0:w:2]
                + field[1:h:2, 0:w:2]
                + field[0:h:2, 1:w:2]
                + field[1:h:2, 1:w:2]
            ) / 4.0

        return field

    # ── Combined State ──

    def combine(self) -> np.ndarray:
        """Combine all three layers into a single field.

        bit_matrix * 0.5 + trit_matrix * 0.3 + |holo_field| * 0.2

        This is the pre-decision state that feeds into the
        ScatteredAttentionSphere for geometric routing.
        """
        holo_mag = np.abs(self.holo_field)
        # Normalize holographic magnitude to [0, 1]
        holo_max = np.max(holo_mag)
        if holo_max > 0:
            holo_mag = holo_mag / holo_max

        combined = (
            self.bit_matrix.astype(np.float64) * 0.5
            + self.trit_matrix.astype(np.float64) * 0.3
            + holo_mag * 0.2
        )
        return combined

    def to_weight_matrix(self) -> np.ndarray:
        """Convert combined state to a weight matrix for ScatteredAttentionSphere.

        This is the bridge: HolographicBitMatrix -> ScatteredAttentionSphere.
        The combined field becomes a weight matrix that the sphere fractalizes.
        """
        return self.combine()

    # ── Governance ──

    def governance_cost(self) -> float:
        """Total governance cost from active tongue weights."""
        return sum(
            w for t, w in self.tongue_activation.items() if w > 0
        )

    def harmonic_wall(self, drift: float = 0.0) -> float:
        """H(d, R) = R^(d^2) where R = governance_cost, d = drift."""
        r = max(self.governance_cost(), 1.0)
        return r ** (drift * drift) if drift > 0 else 1.0

    # ── State Inspection ──

    def state(self) -> HoloState:
        """Full state snapshot."""
        active = [t for t, w in self.tongue_activation.items() if w > 0]
        null = [t for t, w in self.tongue_activation.items() if w == 0]

        trit_flat = self.trit_matrix.flatten()
        trit_dist = {
            "-1": int(np.sum(trit_flat == -1)),
            "0": int(np.sum(trit_flat == 0)),
            "+1": int(np.sum(trit_flat == 1)),
        }

        return HoloState(
            bit_density=float(np.mean(self.bit_matrix)),
            trit_distribution=trit_dist,
            holo_energy=float(np.mean(np.abs(self.holo_field))),
            tongue_activation=dict(self.tongue_activation),
            tongues_active=active,
            tongues_null=null,
            mera_level=self.mera_level,
            reconstruction_error=0.0,  # computed on demand
            governance_cost=self.governance_cost(),
        )

    def reconstruction_error(self, original: np.ndarray) -> float:
        """Measure how well the holographic field preserves the original signal."""
        decoded = self.decode(len(original))
        if len(decoded) != len(original):
            return 1.0
        mse = float(np.mean((original - decoded) ** 2))
        signal_power = float(np.mean(original ** 2))
        if signal_power < 1e-10:
            return 0.0
        return mse / signal_power


# ── Integration with ScatteredAttentionSphere ──

def holographic_scatter_pipeline(
    signal: np.ndarray,
    active_tongues: list[str],
    matrix_size: int = 32,
    mera_level: int = 2,
) -> dict[str, Any]:
    """Full pipeline: signal -> bit matrix -> holographic field -> weight matrix.

    Returns a dict with the weight matrix (for ScatteredAttentionSphere.scatter()),
    state snapshot, and reconstruction error.
    """
    hbm = HolographicBitMatrix(size=matrix_size)

    # L1: Apply tongue modulation
    hbm.modulate_tongues(active_tongues)

    # L2: Encode signal holographically
    hbm.encode(signal)

    # MERA compress
    compressed = hbm.mera_compress(level=mera_level)

    # Get weight matrix for sphere
    weight_matrix = hbm.to_weight_matrix()

    # Measure reconstruction quality
    recon_error = hbm.reconstruction_error(signal)

    state = hbm.state()
    state.reconstruction_error = recon_error

    return {
        "weight_matrix": weight_matrix,
        "compressed_field": compressed,
        "state": state,
        "matrix_size": matrix_size,
        "mera_level": mera_level,
        "active_tongues": active_tongues,
        "reconstruction_error": recon_error,
    }


# ── Demo ──

if __name__ == "__main__":
    print("Holographic Bit-Matrix Architecture")
    print("=" * 50)

    # Create matrix
    hbm = HolographicBitMatrix(size=32)
    print(f"\nL0 Bit substrate: {hbm.size}x{hbm.size}")
    print(f"  Density: {np.mean(hbm.bit_matrix):.3f} (target ~0.618 = 1/phi)")

    # Modulate with active tongues (simulate a KO+CA query)
    hbm.modulate_tongues(["KO", "CA"])
    state = hbm.state()
    print(f"\nL1 Tongue modulation:")
    print(f"  Active: {state.tongues_active}")
    print(f"  Null: {state.tongues_null}")
    print(f"  Trit distribution: {state.trit_distribution}")

    # Encode a signal
    signal = np.array([0.5, -0.3, 0.8, 0.1, -0.6, 0.4,
                        0.2, -0.1, 0.7, -0.5, 0.3, 0.0,
                        -0.4, 0.6, -0.2, 0.9])
    hbm.encode(signal)
    print(f"\nL2 Holographic field:")
    print(f"  Energy: {np.mean(np.abs(hbm.holo_field)):.6f}")
    print(f"  Max amplitude: {np.max(np.abs(hbm.holo_field)):.6f}")

    # MERA compress
    for level in range(4):
        compressed = hbm.mera_compress(level)
        print(f"\n  MERA Level {level}: {compressed.shape} ({compressed.size} values)")

    # Combine layers
    combined = hbm.combine()
    print(f"\nCombined field: {combined.shape}")
    print(f"  Range: [{combined.min():.3f}, {combined.max():.3f}]")
    print(f"  Mean: {combined.mean():.3f}")

    # Reconstruction
    decoded = hbm.decode(len(signal))
    recon_err = hbm.reconstruction_error(signal)
    print(f"\nReconstruction:")
    print(f"  Original:  {signal[:6]}")
    print(f"  Decoded:   {decoded[:6]}")
    print(f"  Error (MSE/signal): {recon_err:.6f}")

    # Governance
    print(f"\nGovernance:")
    print(f"  Cost: {hbm.governance_cost():.3f}")
    print(f"  Harmonic wall (d=0): {hbm.harmonic_wall(0.0):.3f}")
    print(f"  Harmonic wall (d=1): {hbm.harmonic_wall(1.0):.3f}")
    print(f"  Harmonic wall (d=2): {hbm.harmonic_wall(2.0):.3f}")

    # Full pipeline
    print(f"\n{'=' * 50}")
    print("Full pipeline test:")
    result = holographic_scatter_pipeline(
        signal=signal,
        active_tongues=["KO", "CA"],
        matrix_size=16,
        mera_level=2,
    )
    print(f"  Weight matrix: {result['weight_matrix'].shape}")
    print(f"  Compressed field: {result['compressed_field'].shape}")
    print(f"  Reconstruction error: {result['reconstruction_error']:.6f}")
    print(f"  State: active={result['state'].tongues_active}, null={result['state'].tongues_null}")
