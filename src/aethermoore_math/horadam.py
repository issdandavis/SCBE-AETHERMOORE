#!/usr/bin/env python3
"""
AETHERMOORE Horadam Transcript - Drift Telemetry
=================================================
Per-tongue Horadam/Fibonacci sequences for drift detection and telemetry.

The Horadam recurrence H_n = H_{n-1} + H_{n-2} (mod 2^64) with tongue-specific
initial conditions creates a "rhythmic fingerprint" that amplifies any
perturbation exponentially - making it a sensitive early-warning system.

Integration Points:
- Layer 3 (Langues weighting): Dynamic weights from H^(i)_n
- Layer 10 (Triadic verification): Invariants Delta_ijk
- Layer 11 (Omega decision): Drift thresholds
- Layer 12 (PQC): Seeds derived from ML-KEM secret
- Layer 13 (Self-healing): Reroute high-drift tongues

Security Note:
These sequences are deterministic post-processing of PQC secrets.
They do NOT provide cryptographic hardness - all security reduces
to ML-KEM and ML-DSA primitives.

Date: January 2026
"""

from __future__ import annotations

import hmac
import hashlib
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from .constants import COX_CONSTANT

# =============================================================================
# CONSTANTS
# =============================================================================

PHI = (1 + np.sqrt(5)) / 2  # Golden ratio ~1.618
MOD = 2**64  # uint64 modulus
NUM_TONGUES = 6
TONGUES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']
DEFAULT_NUM_BREATHS = 32  # Default sequence length
DEFAULT_PERTURB_FACTOR = 0.01  # 1% perturbation for simulation

# Drift thresholds for governance decisions
DRIFT_THRESHOLD_LOW = 1e3  # Below: SAFE
DRIFT_THRESHOLD_MED = 1e6  # Below: SUSPICIOUS
DRIFT_THRESHOLD_HIGH = 1e12  # Below: QUARANTINE, Above: DENY


class DriftLevel(Enum):
    """Drift classification levels."""
    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    QUARANTINE = "QUARANTINE"
    DENY = "DENY"


# =============================================================================
# HKDF PROXY
# =============================================================================

def hkdf_proxy(secret: bytes, info: bytes, length: int = 8) -> int:
    """
    Simple HKDF proxy using HMAC-SHA256.

    In production, use cryptography.hazmat.primitives.kdf.hkdf.HKDF
    with proper salt and info separation.

    Args:
        secret: The secret key material (e.g., ML-KEM shared secret)
        info: Context/application-specific info string
        length: Number of bytes to extract (default 8 for uint64)

    Returns:
        Integer from first `length` bytes of HMAC output
    """
    digest = hmac.new(secret, info, hashlib.sha256).digest()
    return int.from_bytes(digest[:length], "big")


# =============================================================================
# LANGUES COORDINATES
# =============================================================================

# Default Langues coordinates (6D one-hot basis vectors)
# In production: use actual 6D geometric embeddings from Langues manifold
DEFAULT_LANGUES_COORDS = np.eye(6, dtype=np.float64)


@dataclass
class LanguesCoordinates:
    """6D coordinates for each Sacred Tongue in the Langues manifold."""
    coords: np.ndarray = field(default_factory=lambda: DEFAULT_LANGUES_COORDS.copy())

    def get_coord(self, tongue_idx: int) -> np.ndarray:
        """Get coordinate vector for a tongue by index."""
        return self.coords[tongue_idx]

    def get_coord_by_name(self, tongue: str) -> np.ndarray:
        """Get coordinate vector for a tongue by name."""
        idx = TONGUES.index(tongue.upper())
        return self.coords[idx]


# =============================================================================
# HORADAM SEQUENCE
# =============================================================================

@dataclass
class HoradamSequence:
    """
    Single Horadam sequence for one Sacred Tongue.

    H_0 = alpha, H_1 = beta
    H_n = H_{n-1} + H_{n-2} (mod 2^64)
    """
    tongue: str
    alpha: int  # H_0
    beta: int   # H_1
    sequence: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.uint64))

    def compute(self, n_breaths: int) -> np.ndarray:
        """Compute sequence up to n_breaths terms."""
        self.sequence = np.zeros(n_breaths, dtype=np.uint64)

        if n_breaths > 0:
            self.sequence[0] = self.alpha % MOD
        if n_breaths > 1:
            self.sequence[1] = self.beta % MOD

        for n in range(2, n_breaths):
            self.sequence[n] = (
                int(self.sequence[n-1]) + int(self.sequence[n-2])
            ) % MOD

        return self.sequence

    def get(self, n: int) -> int:
        """Get H_n value."""
        if n >= len(self.sequence):
            self.compute(n + 1)
        return int(self.sequence[n])


# =============================================================================
# DRIFT TELEMETRY
# =============================================================================

@dataclass
class DriftVector:
    """
    6D drift vector at a specific breath n.

    delta_i(n) = |H_observed(n) - H_expected(n)| / phi^n
    """
    breath: int
    values: np.ndarray  # 6D vector
    norm: float = 0.0
    level: DriftLevel = DriftLevel.SAFE

    def __post_init__(self):
        self.norm = float(np.linalg.norm(self.values))
        self.level = self._classify()

    def _classify(self) -> DriftLevel:
        """Classify drift level based on norm."""
        if self.norm < DRIFT_THRESHOLD_LOW:
            return DriftLevel.SAFE
        elif self.norm < DRIFT_THRESHOLD_MED:
            return DriftLevel.SUSPICIOUS
        elif self.norm < DRIFT_THRESHOLD_HIGH:
            return DriftLevel.QUARANTINE
        else:
            return DriftLevel.DENY


@dataclass
class DriftTelemetry:
    """
    Complete drift telemetry for a session.

    Tracks expected vs observed sequences for all 6 tongues
    and computes drift vectors for governance decisions.
    """
    session_id: str
    n_breaths: int
    expected: Dict[str, HoradamSequence] = field(default_factory=dict)
    observed: Dict[str, HoradamSequence] = field(default_factory=dict)
    drift_vectors: List[DriftVector] = field(default_factory=list)

    def compute_drift(self) -> List[DriftVector]:
        """Compute drift vectors for all breaths."""
        self.drift_vectors = []

        for n in range(self.n_breaths):
            values = np.zeros(NUM_TONGUES, dtype=np.float64)
            phi_n = PHI ** n if n > 0 else 1.0

            for i, tongue in enumerate(TONGUES):
                if tongue in self.expected and tongue in self.observed:
                    exp_val = self.expected[tongue].get(n)
                    obs_val = self.observed[tongue].get(n)
                    diff = abs(int(obs_val) - int(exp_val))
                    values[i] = diff / phi_n

            self.drift_vectors.append(DriftVector(breath=n, values=values))

        return self.drift_vectors

    def get_max_drift(self) -> Tuple[int, float, DriftLevel]:
        """Get maximum drift across all breaths."""
        if not self.drift_vectors:
            return 0, 0.0, DriftLevel.SAFE

        max_dv = max(self.drift_vectors, key=lambda dv: dv.norm)
        return max_dv.breath, max_dv.norm, max_dv.level

    def get_tongue_drift(self, tongue: str) -> List[float]:
        """Get drift history for a specific tongue."""
        idx = TONGUES.index(tongue.upper())
        return [dv.values[idx] for dv in self.drift_vectors]


# =============================================================================
# HORADAM TRANSCRIPT ENGINE
# =============================================================================

class HoradamTranscript:
    """
    Main engine for Horadam drift telemetry.

    Seeds 6 tongue-specific sequences from a session secret + Langues coords,
    tracks expected vs observed values, and produces drift telemetry.

    Usage:
        transcript = HoradamTranscript(
            session_secret=mlkem_shared_secret,
            session_nonce=envelope_nonce
        )

        # Compute expected sequences
        transcript.initialize()

        # In Layer 11, check drift at each breath:
        drift = transcript.get_drift_at(n)
        if drift.level == DriftLevel.QUARANTINE:
            omega_decision = "QUARANTINE"
    """

    def __init__(
        self,
        session_secret: bytes,
        session_nonce: bytes = b'\x00' * 12,
        langues_coords: Optional[LanguesCoordinates] = None,
        n_breaths: int = DEFAULT_NUM_BREATHS,
    ):
        """
        Initialize Horadam transcript engine.

        Args:
            session_secret: Session key material (e.g., ML-KEM shared secret)
            session_nonce: Session nonce (e.g., from RWP envelope)
            langues_coords: 6D coordinates for each tongue
            n_breaths: Number of sequence terms to compute
        """
        self.session_secret = session_secret
        self.session_nonce = session_nonce
        self.langues_coords = langues_coords or LanguesCoordinates()
        self.n_breaths = n_breaths

        self.expected_sequences: Dict[str, HoradamSequence] = {}
        self.observed_sequences: Dict[str, HoradamSequence] = {}
        self.telemetry: Optional[DriftTelemetry] = None

    def _derive_initial_conditions(self, tongue_idx: int) -> Tuple[int, int]:
        """
        Derive alpha_i, beta_i for tongue from session secret + Langues coords.

        Uses HKDF proxy with tongue-specific info strings.
        Scales by PHI for golden-ratio rhythm.
        """
        tongue = TONGUES[tongue_idx]
        coord = self.langues_coords.get_coord(tongue_idx)
        coord_bytes = coord.astype(np.float64).tobytes()

        # Derive alpha
        alpha_info = b'alpha|' + tongue.encode() + b'|' + coord_bytes + self.session_nonce
        alpha_raw = hkdf_proxy(self.session_secret, alpha_info)
        alpha = int(alpha_raw * PHI) % MOD

        # Derive beta
        beta_info = b'beta|' + tongue.encode() + b'|' + coord_bytes + self.session_nonce
        beta_raw = hkdf_proxy(self.session_secret, beta_info)
        beta = int(beta_raw * PHI) % MOD

        return alpha, beta

    def initialize(self) -> None:
        """Initialize expected sequences for all tongues."""
        for i, tongue in enumerate(TONGUES):
            alpha, beta = self._derive_initial_conditions(i)

            seq = HoradamSequence(tongue=tongue, alpha=alpha, beta=beta)
            seq.compute(self.n_breaths)

            self.expected_sequences[tongue] = seq

    def set_observed(
        self,
        tongue: str,
        values: np.ndarray,
    ) -> None:
        """Set observed sequence for a tongue (from live system)."""
        if len(values) < 2:
            raise ValueError("Need at least 2 values for Horadam sequence")

        seq = HoradamSequence(
            tongue=tongue.upper(),
            alpha=int(values[0]),
            beta=int(values[1]),
        )
        seq.sequence = values.astype(np.uint64)
        self.observed_sequences[tongue.upper()] = seq

    def simulate_observed(self, perturb_factor: float = DEFAULT_PERTURB_FACTOR) -> None:
        """
        Simulate observed sequences with perturbation (for testing).

        Args:
            perturb_factor: Fraction to perturb initial conditions (0.01 = 1%)
        """
        for i, tongue in enumerate(TONGUES):
            alpha, beta = self._derive_initial_conditions(i)

            # Perturb starts
            alpha_obs = int(alpha * (1.0 + perturb_factor)) % MOD
            beta_obs = int(beta * (1.0 + perturb_factor)) % MOD

            seq = HoradamSequence(tongue=tongue, alpha=alpha_obs, beta=beta_obs)
            seq.compute(self.n_breaths)

            self.observed_sequences[tongue] = seq

    def compute_telemetry(self, session_id: str = "default") -> DriftTelemetry:
        """Compute full drift telemetry."""
        self.telemetry = DriftTelemetry(
            session_id=session_id,
            n_breaths=self.n_breaths,
            expected=self.expected_sequences,
            observed=self.observed_sequences,
        )
        self.telemetry.compute_drift()
        return self.telemetry

    def get_drift_at(self, breath: int) -> DriftVector:
        """Get drift vector at specific breath."""
        if self.telemetry is None:
            self.compute_telemetry()

        if breath >= len(self.telemetry.drift_vectors):
            raise IndexError(f"Breath {breath} out of range")

        return self.telemetry.drift_vectors[breath]

    def get_omega_contribution(self) -> Tuple[float, DriftLevel]:
        """
        Get drift contribution for Layer 11 Omega decision.

        Returns:
            (max_norm, max_level) for integration into Omega scoring
        """
        if self.telemetry is None:
            self.compute_telemetry()

        _, max_norm, max_level = self.telemetry.get_max_drift()
        return max_norm, max_level

    def print_telemetry(self) -> None:
        """Print drift telemetry (for debugging/demo)."""
        if self.telemetry is None:
            self.compute_telemetry()

        print(f"Drift Telemetry over {self.n_breaths} Breaths (n=0..{self.n_breaths-1})")
        print("=" * 70)

        for dv in self.telemetry.drift_vectors:
            print(f"\nBreath {dv.breath:2d}: ||delta|| = {dv.norm:.4e} [{dv.level.value}]")
            for i, tongue in enumerate(TONGUES):
                print(f"  {tongue}: delta_i = {dv.values[i]:.4e}")


# =============================================================================
# TRIADIC INVARIANTS (Layer 10)
# =============================================================================

def compute_triadic_invariant(
    transcript: HoradamTranscript,
    tongue_i: str,
    tongue_j: str,
    tongue_k: str,
    breath: int,
) -> int:
    """
    Compute triadic invariant Delta_ijk(n) = H^i_n + H^j_n - H^k_n (mod 2^64).

    Used in Layer 10 triadic verification for consensus checks.
    """
    seq_i = transcript.expected_sequences.get(tongue_i.upper())
    seq_j = transcript.expected_sequences.get(tongue_j.upper())
    seq_k = transcript.expected_sequences.get(tongue_k.upper())

    if not all([seq_i, seq_j, seq_k]):
        raise ValueError("Missing sequences for triadic computation")

    h_i = seq_i.get(breath)
    h_j = seq_j.get(breath)
    h_k = seq_k.get(breath)

    return (h_i + h_j - h_k) % MOD


def verify_triadic_bounds(
    transcript: HoradamTranscript,
    breath: int,
    threshold: int = 2**32,
) -> Dict[str, bool]:
    """
    Verify all triadic invariants stay within bounds.

    Returns dict of triad -> pass/fail for Layer 10 consensus.
    """
    results = {}

    # Check all unique triads
    triads = [
        ('KO', 'AV', 'RU'),
        ('CA', 'UM', 'DR'),
        ('KO', 'CA', 'UM'),
        ('AV', 'RU', 'DR'),
    ]

    for triad in triads:
        inv = compute_triadic_invariant(transcript, *triad, breath)
        # Invariant should be stable (close to expected value)
        # For now, check if it's within threshold of midpoint
        passed = inv < threshold or inv > (MOD - threshold)
        results[f"{triad[0]}_{triad[1]}_{triad[2]}"] = passed

    return results


# =============================================================================
# SELF-TESTS
# =============================================================================

def self_test() -> Dict[str, str]:
    """Run Horadam transcript self-tests."""
    results = {}

    # Test 1: HKDF proxy produces deterministic output
    try:
        val1 = hkdf_proxy(b"secret", b"info")
        val2 = hkdf_proxy(b"secret", b"info")
        if val1 == val2 and val1 != 0:
            results["hkdf_deterministic"] = "PASS"
        else:
            results["hkdf_deterministic"] = "FAIL"
    except Exception as e:
        results["hkdf_deterministic"] = f"FAIL: {e}"

    # Test 2: Sequence computation (Fibonacci-like growth)
    try:
        seq = HoradamSequence(tongue="KO", alpha=1, beta=1)
        seq.compute(10)
        # Should be Fibonacci: 1, 1, 2, 3, 5, 8, 13, 21, 34, 55
        if seq.get(9) == 55:
            results["sequence_fibonacci"] = "PASS"
        else:
            results["sequence_fibonacci"] = f"FAIL: got {seq.get(9)}"
    except Exception as e:
        results["sequence_fibonacci"] = f"FAIL: {e}"

    # Test 3: Drift amplification (small perturbation → large drift)
    try:
        transcript = HoradamTranscript(
            session_secret=b'\x00' * 32,
            n_breaths=20,
        )
        transcript.initialize()
        transcript.simulate_observed(perturb_factor=0.01)
        telemetry = transcript.compute_telemetry()

        drift_0 = telemetry.drift_vectors[0].norm
        drift_10 = telemetry.drift_vectors[10].norm
        drift_19 = telemetry.drift_vectors[19].norm

        # Drift should amplify significantly
        if drift_19 > drift_10 > drift_0:
            results["drift_amplification"] = "PASS"
        else:
            results["drift_amplification"] = "FAIL"
    except Exception as e:
        results["drift_amplification"] = f"FAIL: {e}"

    # Test 4: Triadic invariant computation
    try:
        transcript = HoradamTranscript(session_secret=b'\x01' * 32, n_breaths=10)
        transcript.initialize()

        inv = compute_triadic_invariant(transcript, 'KO', 'AV', 'RU', 5)
        if isinstance(inv, int) and 0 <= inv < MOD:
            results["triadic_invariant"] = "PASS"
        else:
            results["triadic_invariant"] = "FAIL"
    except Exception as e:
        results["triadic_invariant"] = f"FAIL: {e}"

    # Test 5: Drift classification
    try:
        dv_safe = DriftVector(breath=0, values=np.array([1.0] * 6))
        dv_sus = DriftVector(breath=5, values=np.array([1e4] * 6))
        dv_quar = DriftVector(breath=10, values=np.array([1e8] * 6))
        dv_deny = DriftVector(breath=15, values=np.array([1e15] * 6))

        if (dv_safe.level == DriftLevel.SAFE and
            dv_sus.level == DriftLevel.SUSPICIOUS and
            dv_quar.level == DriftLevel.QUARANTINE and
            dv_deny.level == DriftLevel.DENY):
            results["drift_classification"] = "PASS"
        else:
            results["drift_classification"] = "FAIL"
    except Exception as e:
        results["drift_classification"] = f"FAIL: {e}"

    return results


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("AETHERMOORE HORADAM TRANSCRIPT - DRIFT TELEMETRY")
    print("=" * 70)

    # Run self-tests
    print("\n[SELF-TESTS]")
    test_results = self_test()
    for name, result in test_results.items():
        status = "+" if result == "PASS" else "x"
        print(f"  [{status}] {name}: {result}")

    # Demo
    print("\n" + "=" * 70)
    print("DEMO: 32-breath drift telemetry")
    print("=" * 70)

    transcript = HoradamTranscript(
        session_secret=b'\x00' * 32,
        session_nonce=b'\x01' * 12,
        n_breaths=32,
    )

    transcript.initialize()
    transcript.simulate_observed(perturb_factor=0.01)
    transcript.print_telemetry()

    # Summary
    max_norm, max_level = transcript.get_omega_contribution()
    print("\n" + "-" * 70)
    print(f"OMEGA CONTRIBUTION: max_norm={max_norm:.4e}, level={max_level.value}")
    print("=" * 70)
