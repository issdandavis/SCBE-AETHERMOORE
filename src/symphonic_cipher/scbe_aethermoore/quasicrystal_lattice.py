"""
Icosahedral Quasicrystal Verification System
=============================================
SCBE v3.0: Maps 6-dimensional authentication gates onto a 3D aperiodic
lattice using the cut-and-project method from quasicrystal physics.

The 6 SCBE gates (Sacred Tongues: KO, AV, RU, CA, UM, DR) form integer
coordinates in Z^6.  An icosahedral projection decomposes each point into:

    - E_parallel  (Physical Space)  : the observable "key"
    - E_perp      (Internal Space)  : the hidden validation check

A point is accepted iff its E_perp component falls inside a shifted
acceptance window (the "Atomic Surface").  Phason strain shifts this
window, atomically rekeying the entire lattice without changing the
6D integer logic.

Crystalline Defect Detection uses FFT analysis to flag attackers who
try to force periodic patterns — a true quasicrystal has peaks only
at irrational (Fibonacci / PHI) intervals.

Author: Issac Davis / SpiralVerse OS
Patent: USPTO #63/961,403
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

# FFT: prefer scipy, fall back to numpy
try:
    from scipy.fft import fft, fftfreq
except ImportError:
    from numpy.fft import fft, fftfreq

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI: float = (1 + math.sqrt(5)) / 2  # Golden Ratio
TAU: float = 2 * math.pi


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LatticePoint:
    """Result of projecting a 6D gate vector onto the quasicrystal."""

    gate_vector: List[int]
    r_physical: np.ndarray       # 3D position in E_parallel
    r_perpendicular: np.ndarray  # 3D position in E_perp
    perp_distance: float         # ||r_perp - phason_strain||
    is_valid: bool               # Inside acceptance window?


@dataclass
class DefectAnalysis:
    """Result of crystalline defect detection."""

    score: float                 # 0.0 = aperiodic (safe), 1.0 = periodic (attack)
    dominant_frequency: float
    dominant_power_ratio: float
    sample_count: int


# ---------------------------------------------------------------------------
# QuasicrystalLattice
# ---------------------------------------------------------------------------

class QuasicrystalLattice:
    """
    Icosahedral Quasicrystal Verification System.

    Maps 6-dimensional authentication gates onto a 3D aperiodic lattice.
    The acceptance criterion in perpendicular space enforces that only
    geometrically valid gate combinations are authorised.

    Phason strain provides atomic rekeying: shifting the acceptance
    window invalidates all previously-valid keys without changing the
    6D integer gate logic.
    """

    def __init__(self, lattice_constant: float = 1.0):
        self.a = lattice_constant
        # Acceptance radius in E_perp — defines the Atomic Surface
        self.acceptance_radius: float = 1.5 * self.a
        # Current phason strain vector (secret key component)
        self.phason_strain: np.ndarray = np.zeros(3)
        # Projection matrices (6D -> 3D)
        self.M_par, self.M_perp = self._generate_basis_matrices()

    # ------------------------------------------------------------------
    # Projection basis
    # ------------------------------------------------------------------

    def _generate_basis_matrices(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build projection matrices from Z^6 → E_parallel and E_perp
        using standard icosahedral vertex orientations.

        Basis vectors are cyclic permutations of (1, PHI, 0) normalised
        by 1/sqrt(1 + PHI^2).  E_perp uses the Galois conjugate
        (PHI → -1/PHI).
        """
        norm = 1.0 / np.sqrt(1.0 + PHI ** 2)

        # Physical-space basis  (shape 3×6)
        e_par = np.array([
            [1,  PHI, 0],
            [-1, PHI, 0],
            [0,  1,   PHI],
            [0, -1,   PHI],
            [PHI, 0,  1],
            [PHI, 0, -1],
        ]).T * norm

        # Internal-space basis  (shape 3×6)  — Galois conjugation
        inv_phi = -1.0 / PHI
        e_perp = np.array([
            [1,       inv_phi, 0],
            [-1,      inv_phi, 0],
            [0,       1,       inv_phi],
            [0,      -1,       inv_phi],
            [inv_phi, 0,       1],
            [inv_phi, 0,      -1],
        ]).T * norm

        return e_par, e_perp

    # ------------------------------------------------------------------
    # Gate mapping
    # ------------------------------------------------------------------

    def map_gates_to_lattice(
        self, gate_vector: List[int]
    ) -> LatticePoint:
        """
        Project 6 integer gate inputs onto the quasicrystal.

        Args:
            gate_vector: 6 integers representing the state of the
                         6 SCBE gates (e.g. quantised KO/AV/RU/CA/UM/DR).

        Returns:
            LatticePoint with physical/perpendicular projections and
            validity flag.
        """
        if len(gate_vector) != 6:
            raise ValueError(f"gate_vector must have 6 elements, got {len(gate_vector)}")

        n = np.array(gate_vector, dtype=float)

        r_phys = self.M_par @ n
        r_perp = self.M_perp @ n

        distance = float(np.linalg.norm(r_perp - self.phason_strain))
        is_valid = distance < self.acceptance_radius

        return LatticePoint(
            gate_vector=list(gate_vector),
            r_physical=r_phys,
            r_perpendicular=r_perp,
            perp_distance=distance,
            is_valid=is_valid,
        )

    # ------------------------------------------------------------------
    # Phason rekeying
    # ------------------------------------------------------------------

    def apply_phason_rekey(self, entropy_seed: bytes) -> np.ndarray:
        """
        Apply a phason deformation — atomically invalidate the previous
        valid keyspace and instantiate a new one.

        Args:
            entropy_seed: Arbitrary bytes used to derive the 3D shift.

        Returns:
            The new phason_strain vector.
        """
        h = hashlib.sha256(entropy_seed).digest()
        v = np.array([
            int.from_bytes(h[0:4], "big") / (2 ** 32) * 2 - 1,
            int.from_bytes(h[4:8], "big") / (2 ** 32) * 2 - 1,
            int.from_bytes(h[8:12], "big") / (2 ** 32) * 2 - 1,
        ])
        self.phason_strain = v * self.acceptance_radius * 2.0
        return self.phason_strain.copy()

    # ------------------------------------------------------------------
    # Crystalline defect detection
    # ------------------------------------------------------------------

    def detect_crystalline_defects(
        self, history_vectors: List[List[int]], min_samples: int = 32
    ) -> DefectAnalysis:
        """
        Detect forced periodicity (Crystalline Defect) in gate history.

        A true quasicrystal DFT shows peaks at irrational intervals
        (Fibonacci ratios).  Strong peaks at low rational frequencies
        indicate an attacker forcing a periodic pattern.

        Args:
            history_vectors: Sequence of 6D gate vectors over time.
            min_samples: Minimum history length for meaningful FFT.

        Returns:
            DefectAnalysis with a score in [0, 1].
        """
        n_samples = len(history_vectors)
        if n_samples < min_samples:
            return DefectAnalysis(
                score=0.0,
                dominant_frequency=0.0,
                dominant_power_ratio=0.0,
                sample_count=n_samples,
            )

        norms = np.array([np.linalg.norm(v) for v in history_vectors])
        N = len(norms)

        # Hanning window to reduce spectral leakage
        window = np.hanning(N)
        windowed = norms * window

        yf = fft(windowed)
        xf = fftfreq(N, 1)

        power = np.abs(yf[1 : N // 2]) ** 2
        freqs = xf[1 : N // 2]

        if len(power) == 0 or np.sum(power) == 0:
            return DefectAnalysis(
                score=0.0,
                dominant_frequency=0.0,
                dominant_power_ratio=0.0,
                sample_count=N,
            )

        dominant_idx = int(np.argmax(power))
        dominant_freq = float(freqs[dominant_idx])
        total_power = float(np.sum(power))
        dominant_ratio = float(power[dominant_idx]) / total_power

        # Heuristic: strong peak at low frequency → forced periodicity
        score = 0.0
        if 0 < dominant_freq < 0.1 and dominant_ratio > 0.5:
            score = min(1.0, dominant_ratio * 1.5)

        return DefectAnalysis(
            score=score,
            dominant_frequency=dominant_freq,
            dominant_power_ratio=dominant_ratio,
            sample_count=N,
        )

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return diagnostic info about the lattice state."""
        return {
            "lattice_constant": self.a,
            "acceptance_radius": self.acceptance_radius,
            "phason_strain": self.phason_strain.tolist(),
            "phason_norm": float(np.linalg.norm(self.phason_strain)),
            "projection_shape_par": list(self.M_par.shape),
            "projection_shape_perp": list(self.M_perp.shape),
        }
