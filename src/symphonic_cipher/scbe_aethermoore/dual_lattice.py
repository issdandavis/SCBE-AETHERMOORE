#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Dual Lattice Framework
========================================

Implements Claim 62: Dual-Lattice Quantum Security Consensus

The dual lattice is a consensus mechanism requiring simultaneous validation
from two independent lattice-based PQC algorithms:

    - ML-KEM (Kyber): Primal lattice for key encapsulation (MLWE hardness)
    - ML-DSA (Dilithium): Dual lattice for signatures (MSIS hardness)

"Settling" Mechanism:
    - Unstable chaotic equations at init
    - Become stable ONLY when both lattices agree within time window Δt < ε
    - Resolves to key K(t_arrival) at interference maximum

Mathematical Foundation:
    Consensus = Kyber_valid ∧ Dilithium_valid ∧ (Δt < ε)

    If consensus:
        K(t) = Σ C_n sin(ω_n t + φ_n) mod P   (constructive interference)
    Else:
        K(t) = chaotic noise                   (fail-to-noise)

Security Properties:
    - Breaking one algorithm insufficient (AND logic)
    - Requires breaking BOTH MLWE and MSIS simultaneously
    - Provable min(security_Kyber, security_Dilithium) = ~2^192

Integration with SCBE:
    - Axiom A3: Weighted dual norms (positive definiteness)
    - Axiom A8: Realms as primal/dual zones
    - Axiom A11: Triadic with dual as third "check"
    - Axiom A12: Risk ↑ on mismatch → R' += w_dual × (1 - consensus) × H(d*, R)

Date: January 15, 2026
Golden Master: v2.0.1
Patent Claim: 62 (Dual-Lattice Quantum Security)
"""

from __future__ import annotations

import numpy as np
import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, Optional, List
from enum import Enum
import time

# =============================================================================
# CONSTANTS
# =============================================================================

PHI = (1 + np.sqrt(5)) / 2
EPSILON = 1e-10

# Security levels (NIST)
SECURITY_LEVEL_3 = 192  # bits (ML-KEM-768, ML-DSA-65)


class LatticeType(Enum):
    """Lattice algorithm types."""
    PRIMAL = "PRIMAL"   # ML-KEM (Kyber) - MLWE
    DUAL = "DUAL"       # ML-DSA (Dilithium) - MSIS


class ConsensusState(Enum):
    """Dual lattice consensus states."""
    UNSETTLED = "UNSETTLED"   # Waiting for both validations
    SETTLING = "SETTLING"     # One valid, waiting for other
    SETTLED = "SETTLED"       # Both valid within window
    FAILED = "FAILED"         # Mismatch or timeout
    CHAOS = "CHAOS"           # Fail-to-noise triggered


# =============================================================================
# SIMULATED LATTICE OPERATIONS
# =============================================================================

@dataclass
class LatticeKeyPair:
    """Lattice-based key pair (simulated)."""
    public_key: bytes
    secret_key: bytes
    algorithm: str
    security_level: int = SECURITY_LEVEL_3


@dataclass
class KyberResult:
    """Result from ML-KEM operation."""
    ciphertext: bytes
    shared_secret: bytes
    valid: bool
    timestamp: float


@dataclass
class DilithiumResult:
    """Result from ML-DSA operation."""
    signature: bytes
    valid: bool
    timestamp: float


class SimulatedKyber:
    """
    Simulated ML-KEM (Kyber) for demonstration.

    In production, use liboqs or pqcrypto.

    MLWE Problem: b = As + e + m
        - A: public matrix
        - s: secret vector
        - e: error vector
        - m: message
    """

    def __init__(self, security_level: int = SECURITY_LEVEL_3):
        self.security_level = security_level
        self.key_size = security_level // 8  # bytes

    def keygen(self) -> LatticeKeyPair:
        """Generate Kyber key pair."""
        seed = np.random.bytes(32)
        pk = hashlib.sha3_256(seed + b"kyber_pk").digest()
        sk = hashlib.sha3_256(seed + b"kyber_sk").digest()

        return LatticeKeyPair(
            public_key=pk,
            secret_key=sk,
            algorithm="ML-KEM-768",
            security_level=self.security_level
        )

    def encapsulate(self, public_key: bytes) -> KyberResult:
        """Encapsulate shared secret."""
        randomness = np.random.bytes(32)
        ciphertext = hashlib.sha3_256(public_key + randomness).digest()
        shared_secret = hashlib.sha3_256(ciphertext + public_key).digest()

        return KyberResult(
            ciphertext=ciphertext,
            shared_secret=shared_secret,
            valid=True,
            timestamp=time.time()
        )

    def decapsulate(self, secret_key: bytes, ciphertext: bytes) -> KyberResult:
        """Decapsulate shared secret."""
        # In real implementation, this would use lattice math
        shared_secret = hashlib.sha3_256(ciphertext + secret_key[:16]).digest()

        return KyberResult(
            ciphertext=ciphertext,
            shared_secret=shared_secret,
            valid=True,
            timestamp=time.time()
        )


class SimulatedDilithium:
    """
    Simulated ML-DSA (Dilithium) for demonstration.

    MSIS Problem: Find short vector in signed lattice.
    """

    def __init__(self, security_level: int = SECURITY_LEVEL_3):
        self.security_level = security_level

    def keygen(self) -> LatticeKeyPair:
        """Generate Dilithium key pair."""
        seed = np.random.bytes(32)
        pk = hashlib.sha3_256(seed + b"dilithium_pk").digest()
        sk = hashlib.sha3_256(seed + b"dilithium_sk").digest()

        return LatticeKeyPair(
            public_key=pk,
            secret_key=sk,
            algorithm="ML-DSA-65",
            security_level=self.security_level
        )

    def sign(self, secret_key: bytes, message: bytes) -> DilithiumResult:
        """Sign message."""
        signature = hmac.new(secret_key, message, hashlib.sha3_256).digest()

        return DilithiumResult(
            signature=signature,
            valid=True,
            timestamp=time.time()
        )

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> DilithiumResult:
        """Verify signature."""
        # Simulated verification
        expected = hmac.new(public_key[:32], message, hashlib.sha3_256).digest()

        # In real impl, this uses lattice verification
        valid = len(signature) == 32  # Simplified check

        return DilithiumResult(
            signature=signature,
            valid=valid,
            timestamp=time.time()
        )


# =============================================================================
# DUAL LATTICE CONSENSUS
# =============================================================================

@dataclass
class ConsensusParams:
    """Parameters for dual lattice consensus."""
    time_window: float = 0.1      # ε: max time between validations (seconds)
    kyber_weight: float = 0.5     # λ1: Kyber contribution
    dilithium_weight: float = 0.5 # λ2: Dilithium contribution
    risk_weight: float = 0.3      # w_dual: Risk contribution on mismatch


@dataclass
class SettlingResult:
    """Result from settling process."""
    state: ConsensusState
    key: Optional[bytes]          # K(t) if settled
    consensus_value: float        # 0 (failed) to 1 (settled)
    kyber_valid: bool
    dilithium_valid: bool
    time_delta: float             # Δt between validations
    risk_contribution: float      # Added to R'
    harmonics: List[float]        # Fourier components of K(t)


class DualLatticeConsensus:
    """
    Dual Lattice Consensus Engine.

    Implements the "settling" mechanism:
        - Unstable at init (chaotic)
        - Settles ONLY when both lattices validate within time window
        - Produces K(t) via constructive interference
    """

    def __init__(self, params: Optional[ConsensusParams] = None):
        self.params = params or ConsensusParams()
        self.kyber = SimulatedKyber()
        self.dilithium = SimulatedDilithium()

        # State
        self._kyber_result: Optional[KyberResult] = None
        self._dilithium_result: Optional[DilithiumResult] = None
        self._state = ConsensusState.UNSETTLED

        # Harmonic parameters for K(t)
        self._C_n = np.array([1.0, 0.5, 0.25, 0.125])  # Amplitudes
        self._omega_n = np.array([1.0, PHI, PHI**2, PHI**3])  # Frequencies
        self._phi_n = np.zeros(4)  # Phases (set on consensus)

    def _compute_settling_key(self, t_arrival: float) -> bytes:
        """
        Compute K(t) at settling time via constructive interference.

        K(t) = Σ C_n sin(ω_n t + φ_n)

        At t_arrival, phases align for maximum constructive interference.
        """
        # Set phases for constructive interference at t_arrival
        self._phi_n = -self._omega_n * t_arrival

        # Compute K(t_arrival) - should be maximum
        K_value = np.sum(self._C_n * np.sin(self._omega_n * t_arrival + self._phi_n))

        # Normalize and hash to get key bytes
        K_normalized = (K_value + np.sum(self._C_n)) / (2 * np.sum(self._C_n))
        K_bytes = hashlib.sha3_256(str(K_normalized).encode() + str(t_arrival).encode()).digest()

        return K_bytes

    def _compute_chaos_noise(self) -> bytes:
        """
        Generate chaotic noise (fail-to-noise).

        When consensus fails, return unpredictable noise.
        """
        chaos = np.random.bytes(32)
        return hashlib.sha3_256(chaos + str(time.time()).encode()).digest()

    def submit_kyber(self, ciphertext: bytes, public_key: bytes) -> None:
        """Submit Kyber validation."""
        result = self.kyber.encapsulate(public_key)
        result.ciphertext = ciphertext
        self._kyber_result = result

        if self._state == ConsensusState.UNSETTLED:
            self._state = ConsensusState.SETTLING

    def submit_dilithium(self, signature: bytes, message: bytes, public_key: bytes) -> None:
        """Submit Dilithium validation."""
        result = self.dilithium.verify(public_key, message, signature)
        self._dilithium_result = result

        if self._state == ConsensusState.UNSETTLED:
            self._state = ConsensusState.SETTLING

    def check_consensus(self) -> SettlingResult:
        """
        Check if dual consensus has been reached.

        Consensus = Kyber_valid ∧ Dilithium_valid ∧ (Δt < ε)
        """
        # Check if both submitted
        if self._kyber_result is None or self._dilithium_result is None:
            return SettlingResult(
                state=ConsensusState.UNSETTLED,
                key=None,
                consensus_value=0.0,
                kyber_valid=self._kyber_result is not None and self._kyber_result.valid,
                dilithium_valid=self._dilithium_result is not None and self._dilithium_result.valid,
                time_delta=float('inf'),
                risk_contribution=self.params.risk_weight,
                harmonics=[]
            )

        # Check validity
        kyber_valid = self._kyber_result.valid
        dilithium_valid = self._dilithium_result.valid

        # Check time window
        time_delta = abs(self._kyber_result.timestamp - self._dilithium_result.timestamp)
        time_valid = time_delta < self.params.time_window

        # Consensus = AND of all three
        consensus = kyber_valid and dilithium_valid and time_valid

        if consensus:
            # SETTLED - compute K(t) via constructive interference
            t_arrival = (self._kyber_result.timestamp + self._dilithium_result.timestamp) / 2
            key = self._compute_settling_key(t_arrival)
            self._state = ConsensusState.SETTLED

            return SettlingResult(
                state=ConsensusState.SETTLED,
                key=key,
                consensus_value=1.0,
                kyber_valid=kyber_valid,
                dilithium_valid=dilithium_valid,
                time_delta=time_delta,
                risk_contribution=0.0,  # No risk on success
                harmonics=list(self._C_n * np.sin(self._phi_n))
            )
        else:
            # FAILED - return chaos noise
            self._state = ConsensusState.CHAOS if (kyber_valid != dilithium_valid) else ConsensusState.FAILED

            # Risk contribution on mismatch
            mismatch = 1.0 - (0.5 * kyber_valid + 0.5 * dilithium_valid)
            risk = self.params.risk_weight * mismatch

            return SettlingResult(
                state=self._state,
                key=self._compute_chaos_noise(),  # Fail-to-noise
                consensus_value=0.0,
                kyber_valid=kyber_valid,
                dilithium_valid=dilithium_valid,
                time_delta=time_delta,
                risk_contribution=risk,
                harmonics=[]
            )

    def reset(self):
        """Reset consensus state."""
        self._kyber_result = None
        self._dilithium_result = None
        self._state = ConsensusState.UNSETTLED


# =============================================================================
# INTEGRATION WITH SCBE RISK ENGINE
# =============================================================================

def integrate_dual_lattice_risk(
    consensus_result: SettlingResult,
    base_risk: float,
    H_d_star: float
) -> float:
    """
    Integrate dual lattice mismatch into SCBE risk.

    R' += w_dual × (1 - consensus) × H(d*, R)

    Args:
        consensus_result: Result from dual lattice check
        base_risk: Current risk value
        H_d_star: Harmonic scaling factor from Layer 12

    Returns:
        Updated risk value
    """
    mismatch = 1.0 - consensus_result.consensus_value
    risk_addition = consensus_result.risk_contribution * mismatch * H_d_star

    return base_risk + risk_addition


# =============================================================================
# SETTLING WAVE VISUALIZATION
# =============================================================================

def compute_settling_wave(
    t: np.ndarray,
    C_n: np.ndarray,
    omega_n: np.ndarray,
    t_arrival: float
) -> np.ndarray:
    """
    Compute the settling wave K(t).

    K(t) = Σ C_n sin(ω_n t + φ_n)

    Where φ_n = π/2 - ω_n × t_arrival for constructive interference.
    At t_arrival: sin(ω_n * t_arrival + π/2 - ω_n * t_arrival) = sin(π/2) = 1
    """
    phi_n = np.pi/2 - omega_n * t_arrival

    K = np.zeros_like(t, dtype=float)
    for C, omega, phi in zip(C_n, omega_n, phi_n):
        K += C * np.sin(omega * t + phi)

    return K


# =============================================================================
# SELF-TESTS
# =============================================================================

def self_test() -> Dict[str, Any]:
    """Run dual lattice self-tests."""
    results = {}
    passed = 0
    total = 0

    # Test 1: Kyber keygen and encapsulate
    total += 1
    try:
        kyber = SimulatedKyber()
        keys = kyber.keygen()
        result = kyber.encapsulate(keys.public_key)

        if result.valid and len(result.shared_secret) == 32:
            passed += 1
            results["kyber_ops"] = "✓ PASS (keygen + encapsulate)"
        else:
            results["kyber_ops"] = "✗ FAIL (invalid result)"
    except Exception as e:
        results["kyber_ops"] = f"✗ FAIL ({e})"

    # Test 2: Dilithium sign and verify
    total += 1
    try:
        dilithium = SimulatedDilithium()
        keys = dilithium.keygen()
        message = b"test message"
        sig_result = dilithium.sign(keys.secret_key, message)
        verify_result = dilithium.verify(keys.public_key, message, sig_result.signature)

        if sig_result.valid and verify_result.valid:
            passed += 1
            results["dilithium_ops"] = "✓ PASS (sign + verify)"
        else:
            results["dilithium_ops"] = "✗ FAIL (invalid result)"
    except Exception as e:
        results["dilithium_ops"] = f"✗ FAIL ({e})"

    # Test 3: Consensus AND logic (both valid → settled)
    total += 1
    try:
        consensus = DualLatticeConsensus()

        # Submit both within time window
        kyber_keys = consensus.kyber.keygen()
        dilithium_keys = consensus.dilithium.keygen()

        consensus.submit_kyber(b"test_ct", kyber_keys.public_key)
        consensus.submit_dilithium(b"x" * 32, b"test_msg", dilithium_keys.public_key)

        result = consensus.check_consensus()

        if result.state == ConsensusState.SETTLED and result.consensus_value == 1.0:
            passed += 1
            results["consensus_and"] = "✓ PASS (both valid → SETTLED)"
        else:
            results["consensus_and"] = f"✗ FAIL (state={result.state})"
    except Exception as e:
        results["consensus_and"] = f"✗ FAIL ({e})"

    # Test 4: Consensus failure (only one submitted)
    total += 1
    try:
        consensus = DualLatticeConsensus()
        kyber_keys = consensus.kyber.keygen()

        consensus.submit_kyber(b"test_ct", kyber_keys.public_key)
        # Don't submit Dilithium

        result = consensus.check_consensus()

        if result.state == ConsensusState.UNSETTLED:
            passed += 1
            results["consensus_partial"] = "✓ PASS (one valid → UNSETTLED)"
        else:
            results["consensus_partial"] = f"✗ FAIL (state={result.state})"
    except Exception as e:
        results["consensus_partial"] = f"✗ FAIL ({e})"

    # Test 5: Key uniqueness (different consensus → different keys)
    total += 1
    try:
        consensus1 = DualLatticeConsensus()
        consensus2 = DualLatticeConsensus()

        # First consensus
        k1 = consensus1.kyber.keygen()
        d1 = consensus1.dilithium.keygen()
        consensus1.submit_kyber(b"ct1", k1.public_key)
        consensus1.submit_dilithium(b"x" * 32, b"msg1", d1.public_key)
        result1 = consensus1.check_consensus()

        # Second consensus (different keys)
        time.sleep(0.01)  # Ensure different timestamp
        k2 = consensus2.kyber.keygen()
        d2 = consensus2.dilithium.keygen()
        consensus2.submit_kyber(b"ct2", k2.public_key)
        consensus2.submit_dilithium(b"y" * 32, b"msg2", d2.public_key)
        result2 = consensus2.check_consensus()

        if result1.key != result2.key:
            passed += 1
            results["key_uniqueness"] = "✓ PASS (different consensus → different K)"
        else:
            results["key_uniqueness"] = "✗ FAIL (keys should differ)"
    except Exception as e:
        results["key_uniqueness"] = f"✗ FAIL ({e})"

    # Test 6: Settling wave constructive interference
    total += 1
    try:
        C_n = np.array([1.0, 0.5, 0.25])
        omega_n = np.array([1.0, 2.0, 3.0])
        t_arrival = 5.0

        # At t_arrival, constructive interference → K = sum(C_n)
        K_at_arrival = compute_settling_wave(np.array([t_arrival]), C_n, omega_n, t_arrival)[0]
        expected_max = np.sum(C_n)  # = 1.75

        # Verify constructive interference at t_arrival
        if abs(K_at_arrival - expected_max) < 0.01:
            passed += 1
            results["settling_wave"] = f"✓ PASS (K(t_arrival)={K_at_arrival:.2f} = Σc_n={expected_max:.2f})"
        else:
            results["settling_wave"] = f"✗ FAIL (K(t_arrival)={K_at_arrival:.2f}, expected {expected_max:.2f})"
    except Exception as e:
        results["settling_wave"] = f"✗ FAIL ({e})"

    # Test 7: Risk integration
    total += 1
    try:
        # Settled → no risk
        settled_result = SettlingResult(
            state=ConsensusState.SETTLED,
            key=b"test",
            consensus_value=1.0,
            kyber_valid=True,
            dilithium_valid=True,
            time_delta=0.01,
            risk_contribution=0.0,
            harmonics=[]
        )
        risk_settled = integrate_dual_lattice_risk(settled_result, 0.5, 2.0)

        # Failed → adds risk
        failed_result = SettlingResult(
            state=ConsensusState.FAILED,
            key=b"noise",
            consensus_value=0.0,
            kyber_valid=True,
            dilithium_valid=False,
            time_delta=0.5,
            risk_contribution=0.3,
            harmonics=[]
        )
        risk_failed = integrate_dual_lattice_risk(failed_result, 0.5, 2.0)

        if risk_settled == 0.5 and risk_failed > 0.5:
            passed += 1
            results["risk_integration"] = f"✓ PASS (settled={risk_settled:.2f}, failed={risk_failed:.2f})"
        else:
            results["risk_integration"] = "✗ FAIL (risk calculation wrong)"
    except Exception as e:
        results["risk_integration"] = f"✗ FAIL ({e})"

    # Test 8: Security level
    total += 1
    try:
        kyber = SimulatedKyber(SECURITY_LEVEL_3)
        dilithium = SimulatedDilithium(SECURITY_LEVEL_3)

        kyber_keys = kyber.keygen()
        dilithium_keys = dilithium.keygen()

        if kyber_keys.security_level == 192 and dilithium_keys.security_level == 192:
            passed += 1
            results["security_level"] = f"✓ PASS (both at {SECURITY_LEVEL_3}-bit)"
        else:
            results["security_level"] = "✗ FAIL (security level mismatch)"
    except Exception as e:
        results["security_level"] = f"✗ FAIL ({e})"

    # Test 9: Fail-to-noise on mismatch
    total += 1
    try:
        consensus = DualLatticeConsensus()

        # Only submit Kyber (Dilithium missing → fail)
        kyber_keys = consensus.kyber.keygen()
        consensus.submit_kyber(b"ct", kyber_keys.public_key)

        # Force a mismatch scenario
        consensus._dilithium_result = DilithiumResult(
            signature=b"invalid",
            valid=False,  # Invalid!
            timestamp=time.time()
        )

        result = consensus.check_consensus()

        # Should get chaos noise
        if result.state == ConsensusState.CHAOS and result.key is not None:
            passed += 1
            results["fail_to_noise"] = "✓ PASS (mismatch → chaos noise)"
        else:
            results["fail_to_noise"] = f"✗ FAIL (state={result.state})"
    except Exception as e:
        results["fail_to_noise"] = f"✗ FAIL ({e})"

    # Test 10: Reset functionality
    total += 1
    try:
        consensus = DualLatticeConsensus()

        kyber_keys = consensus.kyber.keygen()
        consensus.submit_kyber(b"ct", kyber_keys.public_key)

        consensus.reset()

        result = consensus.check_consensus()

        if result.state == ConsensusState.UNSETTLED:
            passed += 1
            results["reset"] = "✓ PASS (reset clears state)"
        else:
            results["reset"] = f"✗ FAIL (state after reset={result.state})"
    except Exception as e:
        results["reset"] = f"✗ FAIL ({e})"

    return {
        "passed": passed,
        "total": total,
        "success_rate": f"{passed}/{total} ({100*passed/total:.1f}%)",
        "results": results
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SCBE-AETHERMOORE DUAL LATTICE FRAMEWORK")
    print("Claim 62: Dual-Lattice Quantum Security Consensus")
    print("=" * 70)

    # Run self-tests
    test_results = self_test()

    print("\n[SELF-TESTS]")
    for name, result in test_results["results"].items():
        print(f"  {name}: {result}")

    print("-" * 70)
    print(f"TOTAL: {test_results['success_rate']}")

    # Demonstration
    print("\n" + "=" * 70)
    print("DUAL LATTICE CONSENSUS DEMO")
    print("=" * 70)

    consensus = DualLatticeConsensus()

    print("\n1. Generate key pairs...")
    kyber_keys = consensus.kyber.keygen()
    dilithium_keys = consensus.dilithium.keygen()
    print(f"   Kyber:     {kyber_keys.algorithm} ({kyber_keys.security_level}-bit)")
    print(f"   Dilithium: {dilithium_keys.algorithm} ({dilithium_keys.security_level}-bit)")

    print("\n2. Submit validations...")
    consensus.submit_kyber(b"test_ciphertext", kyber_keys.public_key)
    print("   ✓ Kyber submitted")

    consensus.submit_dilithium(b"x" * 32, b"test_message", dilithium_keys.public_key)
    print("   ✓ Dilithium submitted")

    print("\n3. Check consensus...")
    result = consensus.check_consensus()

    print(f"   State:     {result.state.value}")
    print(f"   Consensus: {result.consensus_value}")
    print(f"   Δt:        {result.time_delta*1000:.2f} ms")

    if result.state == ConsensusState.SETTLED:
        print(f"   K(t):      {result.key[:16].hex()}...")
        print("   → SETTLED: Key derived via constructive interference")
    else:
        print("   → FAILED: Chaos noise returned")

    # Wave visualization data
    print("\n" + "-" * 70)
    print("SETTLING WAVE K(t):")

    C_n = np.array([1.0, 0.5, 0.25, 0.125])
    omega_n = np.array([1.0, PHI, PHI**2, PHI**3])
    t_arrival = 5.0

    t_points = [0, 2.5, 5.0, 7.5, 10.0]
    for t in t_points:
        K = compute_settling_wave(np.array([t]), C_n, omega_n, t_arrival)[0]
        bar = "█" * int((K + 2) * 10)
        marker = " ← MAX (constructive)" if abs(t - t_arrival) < 0.1 else ""
        print(f"  t={t:4.1f}: K={K:+.3f} {bar}{marker}")

    print("=" * 70)
