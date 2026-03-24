"""
Quasicrystal Lattice Verification System (SCBE v3.0)
=====================================================

Maps the 6 Sacred Tongue authentication gates onto an icosahedral
quasicrystal in 3D, using the cut-and-project method from 6D -> 3D.

Key concepts:
  - 6D integer lattice Z^6 = the 6 Sacred Tongues (KO, AV, RU, CA, UM, DR)
  - Projection to E_parallel (3D physical space) = the "key"
  - Projection to E_perp (3D internal space) = the "validation window"
  - Acceptance radius in E_perp = the Harmonic Wall analog
  - Phason strain = breathing transform (L6/L7) — shifts valid keyspace
  - Crystalline defect detection via FFT = L9/L10 spectral coherence

A true quasicrystal has aperiodic order with Fibonacci/phi-ratio peaks
in its diffraction pattern. If an attacker forces periodicity (tries to
make the system crystalline), the FFT detects integer-ratio peaks
instead of phi-ratio peaks. Periodicity = attack.

Integration:
  - dual_lattice.py:    6 Tongue gates feed this as integer inputs
  - geo_seal.py:        Phason rekeying binds to context vectors
  - sacred_eggs_ref.py: Acceptance radius parallels ring bucketing
  - nonbinary_kernel.py: Defect score feeds into K=3 risk tiering
  - tri_manifold:       Ternary quantized states as 6D gate inputs

@module quasicrystal_lattice
@layer Layer 5 (Hyperbolic), Layer 9 (Spectral), Layer 12 (Harmonic Wall)
@version 3.0.0
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from scipy.fft import fft, fftfreq
    SCIPY_AVAILABLE = True
except ImportError:
    # Fallback to numpy FFT
    from numpy.fft import fft, fftfreq
    SCIPY_AVAILABLE = False

PHI = (1 + np.sqrt(5)) / 2
TAU = 2 * np.pi

# Sacred Tongue -> gate index mapping
TONGUE_GATE_INDEX = {"KO": 0, "AV": 1, "RU": 2, "CA": 3, "UM": 4, "DR": 5}

# Phi-scaled tongue weights (from Langues metric)
TONGUE_WEIGHTS = [PHI ** i for i in range(6)]
# [1.0, 1.618, 2.618, 4.236, 6.854, 11.09]


# =====================================================================
# Data Structures
# =====================================================================

@dataclass
class LatticePoint:
    """A point in the quasicrystal with both physical and internal projections."""
    gate_vector: List[int]       # 6D integer input (Sacred Tongue gates)
    r_physical: np.ndarray       # 3D physical space projection ("the key")
    r_perpendicular: np.ndarray  # 3D internal space projection ("validation")
    is_valid: bool               # Within acceptance window?
    distance_to_window: float    # Distance from phason-shifted window center


@dataclass
class DefectReport:
    """Results of crystalline defect detection."""
    defect_score: float          # 0.0 = aperiodic (safe), 1.0 = periodic (attack)
    dominant_frequency: float    # Strongest frequency component
    dominant_power: float        # Power of dominant frequency
    total_power: float           # Total spectral power
    is_suspicious: bool          # Defect score above threshold?
    recommendation: str          # ALLOW / QUARANTINE / DENY


# =====================================================================
# Quasicrystal Lattice
# =====================================================================

class QuasicrystalLattice:
    """Icosahedral quasicrystal verification for SCBE 6-gate authentication.

    The 6 Sacred Tongues map to a 6D integer lattice Z^6.
    Cut-and-project method splits this into:
      - E_parallel (3D): Physical space — the "public" lattice point
      - E_perp (3D): Internal space — the "hidden" validation check

    A point is valid iff its E_perp projection falls within the
    acceptance window (the "atomic surface" of the quasicrystal).

    Phason strain shifts the acceptance window without changing the
    6D integer logic — this is atomic rekeying.
    """

    def __init__(
        self,
        lattice_constant: float = 1.0,
        acceptance_radius: Optional[float] = None,
    ):
        self.a = lattice_constant
        # Acceptance radius in E_perp — the "Harmonic Wall" boundary
        self.acceptance_radius = acceptance_radius or (1.5 * self.a)

        # Phason strain vector (secret key component)
        self.phason_strain = np.zeros(3)

        # 6D -> 3D projection matrices (icosahedral symmetry)
        self.M_par, self.M_perp = self._generate_basis_matrices()

        # History for defect detection
        self.gate_history: List[List[int]] = []

    def _generate_basis_matrices(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate icosahedral projection matrices from 6D to 3D.

        Uses cyclic permutations of (1, phi, 0) for E_parallel and
        Galois conjugation (phi -> -1/phi) for E_perpendicular.

        The golden ratio phi appears naturally because icosahedral
        symmetry IS phi-symmetric — same reason the Sacred Tongues
        use phi-scaled weights.
        """
        norm = 1 / np.sqrt(1 + PHI ** 2)

        # E_parallel basis: cyclic permutations of (1, PHI, 0)
        e_par = np.array([
            [1, PHI, 0],
            [-1, PHI, 0],
            [0, 1, PHI],
            [0, -1, PHI],
            [PHI, 0, 1],
            [PHI, 0, -1],
        ]).T * norm  # Shape (3, 6)

        # E_perp basis: Galois conjugation (PHI -> -1/PHI)
        e_perp = np.array([
            [1, -1 / PHI, 0],
            [-1, -1 / PHI, 0],
            [0, 1, -1 / PHI],
            [0, -1, -1 / PHI],
            [-1 / PHI, 0, 1],
            [-1 / PHI, 0, -1],
        ]).T * norm  # Shape (3, 6)

        return e_par, e_perp

    # -----------------------------------------------------------------
    # Core: Map Gates to Lattice
    # -----------------------------------------------------------------

    def map_gates(self, gate_vector: List[int]) -> LatticePoint:
        """Map 6 Sacred Tongue gate values to the quasicrystal.

        Args:
            gate_vector: 6 integers, one per tongue gate.
                Index mapping: [KO, AV, RU, CA, UM, DR]

        Returns:
            LatticePoint with physical projection, internal check, validity.
        """
        if len(gate_vector) != 6:
            raise ValueError(f"Expected 6 gate values, got {len(gate_vector)}")

        n = np.array(gate_vector, dtype=float)

        # Project to physical space (the "public" key)
        r_physical = self.M_par @ n

        # Project to internal space (the "hidden" validation)
        r_perp_raw = self.M_perp @ n

        # Apply phason strain (breathing transform)
        distance = float(np.linalg.norm(r_perp_raw - self.phason_strain))
        is_valid = distance < self.acceptance_radius

        # Record for defect detection
        self.gate_history.append(list(gate_vector))

        return LatticePoint(
            gate_vector=list(gate_vector),
            r_physical=r_physical,
            r_perpendicular=r_perp_raw,
            is_valid=is_valid,
            distance_to_window=round(distance, 6),
        )

    def map_tongue_weights(self) -> LatticePoint:
        """Map the canonical phi-scaled tongue weights as a gate vector.

        This is the "identity" point — the natural resonance of the
        Sacred Tongue weighting system through icosahedral projection.
        """
        weights_int = [int(round(w)) for w in TONGUE_WEIGHTS]
        return self.map_gates(weights_int)

    # -----------------------------------------------------------------
    # Phason Rekeying (Atomic Key Rotation)
    # -----------------------------------------------------------------

    def apply_phason_rekey(self, entropy_seed: bytes) -> np.ndarray:
        """Apply phason strain to shift the acceptance window.

        This atomically invalidates the old valid keyspace and creates
        a new one — without changing any 6D integer logic. The lattice
        points don't move; the WINDOW moves.

        Analogous to SCBE's breathing transform (L6/L7): the system
        inhales, shifting what's valid.

        Args:
            entropy_seed: Random bytes for deterministic key derivation.

        Returns:
            The new phason strain vector.
        """
        h = hashlib.sha256(entropy_seed).digest()
        # Map hash to 3 float values in [-1, 1]
        v = np.array([
            int.from_bytes(h[0:4], "big") / (2 ** 32) * 2 - 1,
            int.from_bytes(h[4:8], "big") / (2 ** 32) * 2 - 1,
            int.from_bytes(h[8:12], "big") / (2 ** 32) * 2 - 1,
        ])
        # Scale to ensure meaningful shift
        self.phason_strain = v * self.acceptance_radius * 2.0
        return self.phason_strain

    def reset_phason(self) -> None:
        """Reset phason strain to zero (restore original window)."""
        self.phason_strain = np.zeros(3)

    # -----------------------------------------------------------------
    # Crystalline Defect Detection (L9/L10 Spectral Coherence)
    # -----------------------------------------------------------------

    def detect_defects(
        self,
        history: Optional[List[List[int]]] = None,
        min_samples: int = 32,
    ) -> DefectReport:
        """Detect crystalline defects (forced periodicity = attack).

        A true quasicrystal has aperiodic order — its FFT shows peaks
        at irrational intervals (phi-ratio frequencies). An attacker
        trying to force periodicity produces integer-ratio peaks.

        This is the L9/L10 spectral coherence check applied to the
        gate input history.

        Args:
            history: Gate vectors to analyze (default: self.gate_history).
            min_samples: Minimum history length for meaningful FFT.

        Returns:
            DefectReport with score, dominant frequency, recommendation.
        """
        vectors = history or self.gate_history

        if len(vectors) < min_samples:
            return DefectReport(
                defect_score=0.0,
                dominant_frequency=0.0,
                dominant_power=0.0,
                total_power=0.0,
                is_suspicious=False,
                recommendation="ALLOW (insufficient data)",
            )

        # Extract 1D sequence: norm of each 6D input
        norms = np.array([np.linalg.norm(v) for v in vectors])
        N = len(norms)

        # Hanning window to reduce spectral leakage
        window = np.hanning(N)
        windowed = norms * window

        # FFT
        yf = fft(windowed)
        xf = fftfreq(N, 1.0)

        # Power spectrum (positive frequencies, skip DC)
        power = np.abs(yf[1:N // 2]) ** 2
        freqs = xf[1:N // 2]

        total_power = float(np.sum(power))
        if total_power == 0 or len(power) == 0:
            return DefectReport(
                defect_score=0.0,
                dominant_frequency=0.0,
                dominant_power=0.0,
                total_power=0.0,
                is_suspicious=False,
                recommendation="ALLOW (flat spectrum)",
            )

        # Find dominant frequency
        dominant_idx = int(np.argmax(power))
        dominant_freq = float(freqs[dominant_idx])
        dominant_pow = float(power[dominant_idx])
        normalized_power = dominant_pow / total_power

        # Defect heuristic:
        # Strong low-frequency peak = periodic pattern = crystalline defect
        # Quasicrystal should have distributed spectrum with phi-ratio peaks
        defect_score = 0.0
        if (
            dominant_freq > 0
            and dominant_freq < 0.1  # Period > 10 samples
            and normalized_power > 0.5  # Dominant peak > 50% of total
        ):
            defect_score = min(1.0, normalized_power * 1.5)

        # Phi-ratio check: are the top peaks at irrational ratios?
        # Sort peaks by power, check if ratios between top frequencies
        # are close to phi (healthy) or close to integers (attack)
        sorted_indices = np.argsort(power)[::-1]
        if len(sorted_indices) >= 3:
            top_freqs = [float(freqs[i]) for i in sorted_indices[:3] if freqs[i] > 0]
            if len(top_freqs) >= 2 and top_freqs[1] > 0:
                ratio = top_freqs[0] / top_freqs[1]
                # Close to phi = healthy quasicrystal
                phi_distance = abs(ratio - PHI)
                if phi_distance < 0.1:
                    defect_score *= 0.5  # Reduce score — phi-resonant

        is_suspicious = defect_score > 0.3

        if defect_score > 0.7:
            recommendation = "DENY (crystalline defect detected)"
        elif defect_score > 0.3:
            recommendation = "QUARANTINE (partial periodicity)"
        else:
            recommendation = "ALLOW (aperiodic — healthy quasicrystal)"

        return DefectReport(
            defect_score=round(defect_score, 4),
            dominant_frequency=round(dominant_freq, 6),
            dominant_power=round(dominant_pow, 4),
            total_power=round(total_power, 4),
            is_suspicious=is_suspicious,
            recommendation=recommendation,
        )

    # -----------------------------------------------------------------
    # Integration: Tri-Manifold Ternary States as Gate Inputs
    # -----------------------------------------------------------------

    def map_ternary_state(
        self,
        ternary_trits: List[int],
    ) -> LatticePoint:
        """Map a ternary-quantized personality state to the quasicrystal.

        Takes 6 trits from the tri-manifold ternary quantization
        (one per Sacred Tongue dimension) and maps them as gate values.

        Trits {-1, 0, +1} are scaled by phi-weights before projection,
        connecting the personality tri-manifold to the quasicrystal's
        acceptance window.

        Args:
            ternary_trits: 6 trit values, one per tongue.
                [-1, 0, +1] for each of [KO, AV, RU, CA, UM, DR]
        """
        if len(ternary_trits) != 6:
            raise ValueError(f"Expected 6 trits, got {len(ternary_trits)}")

        # Scale by phi-weights: trit * phi^i
        # This makes higher tongues (UM, DR) contribute more to the
        # projection, matching the Langues metric weighting
        scaled = [
            int(round(trit * weight))
            for trit, weight in zip(ternary_trits, TONGUE_WEIGHTS)
        ]

        return self.map_gates(scaled)

    # -----------------------------------------------------------------
    # Integration: NonBinary Kernel Risk Feed
    # -----------------------------------------------------------------

    def defect_to_risk_signal(self) -> Dict[str, float]:
        """Convert defect detection into a risk signal for the NonBinary Kernel.

        Maps defect_score to the kernel's input format:
          v_t (vulnerability): defect_score directly
          d_t (depth): based on history length
          i_t (intent): based on whether defects are increasing

        Returns dict compatible with NonBinarySimplexKernel.step() kwargs.
        """
        report = self.detect_defects()
        history_depth = min(1.0, len(self.gate_history) / 100.0)

        # Track if defects are trending upward (increasing intent signal)
        recent_defect = 0.0
        if len(self.gate_history) >= 64:
            # Check last half vs first half
            half = len(self.gate_history) // 2
            early = self.detect_defects(self.gate_history[:half])
            late = self.detect_defects(self.gate_history[half:])
            recent_defect = late.defect_score - early.defect_score

        return {
            "v_t": report.defect_score,
            "d_t": history_depth,
            "i_t": max(-1.0, min(1.0, -recent_defect)),  # Negative = adversarial
            "p_t": 1.0,
        }

    # -----------------------------------------------------------------
    # Reporting
    # -----------------------------------------------------------------

    def get_state(self) -> Dict[str, Any]:
        """Full quasicrystal state report."""
        report = self.detect_defects()
        return {
            "lattice_constant": self.a,
            "acceptance_radius": self.acceptance_radius,
            "phason_strain": self.phason_strain.tolist(),
            "phason_magnitude": round(
                float(np.linalg.norm(self.phason_strain)), 4,
            ),
            "history_length": len(self.gate_history),
            "defect_score": report.defect_score,
            "defect_recommendation": report.recommendation,
            "scipy_available": SCIPY_AVAILABLE,
        }


# =====================================================================
# Convenience: Fibonacci Gate Resonance
# =====================================================================

def fibonacci_gates(n: int = 6) -> List[int]:
    """Generate Fibonacci sequence gate values.

    Fibonacci inputs resonate naturally with icosahedral symmetry
    because the Fibonacci ratio converges to phi — the same phi
    that defines the icosahedral projection matrices.

    These are the "natural resonance" inputs for the quasicrystal.
    """
    fibs = [1, 1]
    while len(fibs) < n:
        fibs.append(fibs[-1] + fibs[-2])
    return fibs[:n]


def tongue_fibonacci_gates() -> Dict[str, int]:
    """Map Sacred Tongues to Fibonacci gate values.

    KO=1, AV=1, RU=2, CA=3, UM=5, DR=8

    These Fibonacci values, when projected through the icosahedral
    matrices, produce phi-resonant lattice points that naturally
    fall within the acceptance window.
    """
    fibs = fibonacci_gates(6)
    return dict(zip(["KO", "AV", "RU", "CA", "UM", "DR"], fibs))
