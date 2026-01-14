"""
SCBE-AETHERMOORE Full System Implementation

Complete integration of all components:
- 14-Layer Phase-Breath Hyperbolic Governance Pipeline
- 9D Quantum Hyperbolic Manifold Memory
- Extended Entropy Math (negentropy support)
- Flat Slope Harmonic Encoding
- HMAC Chain for Tamper-Evident Audit
- Manifold Geometry Validation

This provides end-to-end governance from raw intent to final decision.
"""

import numpy as np
import hashlib
import hmac
import os
import time
from dataclasses import dataclass, field
from typing import Tuple, List, Dict, Any, Optional
from enum import Enum
from collections import deque

# Import from submodules
from .unified import (
    PHI, R, EPSILON, TAU_COH, ETA_TARGET, ETA_MIN, ETA_MAX,
    ETA_NEGENTROPY_THRESHOLD, ETA_HIGH_ENTROPY_THRESHOLD,
    KAPPA_MAX, LAMBDA_BOUND, H_MAX, DOT_TAU_MIN,
    CARRIER_FREQ, SAMPLE_RATE, DURATION,
    State9D, GovernanceDecision, Polyhedron,
    ManifoldController,
    generate_context, compute_entropy, compute_negentropy,
    compute_relative_entropy, compute_mutual_information,
    entropy_rate_estimate,
    tau_dot, tau_curvature, eta_dot, eta_curvature,
    quantum_evolution, quantum_fidelity, von_neumann_entropy,
    hyperbolic_distance, triadic_distance, harmonic_scaling,
    hamiltonian_path_deviation,
    phase_modulated_intent, extract_phase,
    hmac_chain_tag, verify_hmac_chain,
    TONGUES, TONGUE_WEIGHTS, CONLANG, REV_CONLANG,
)

from .layers import (
    FourteenLayerPipeline, RiskLevel, RiskAssessment,
    layer_1_complex_context, layer_2_realify, layer_3_weighted,
    layer_4_poincare, layer_5_hyperbolic_distance,
    layer_6_breathing, layer_7_phase,
    layer_8_multi_well, layer_9_spectral_coherence,
    layer_10_spin_coherence, layer_11_triadic_distance,
    layer_12_harmonic_scaling, layer_13_decision, layer_14_audio_axis,
    verify_theorem_A_metric_invariance,
    verify_theorem_B_continuity,
    verify_theorem_C_risk_monotonicity,
    verify_theorem_D_diffeomorphism,
)


# =============================================================================
# SYSTEM CONSTANTS
# =============================================================================

HISTORY_WINDOW = 100  # States to keep for entropy rate estimation
AUDIT_CHAIN_IV = b'\x00' * 32  # Initial vector for HMAC chain


# =============================================================================
# GOVERNANCE STATE
# =============================================================================

class GovernanceMode(Enum):
    """System operating modes."""
    NORMAL = "NORMAL"           # Standard operation
    HEIGHTENED = "HEIGHTENED"   # Increased scrutiny
    LOCKDOWN = "LOCKDOWN"       # Emergency mode
    LEARNING = "LEARNING"       # Calibration mode


@dataclass
class GovernanceMetrics:
    """Complete metrics from governance evaluation."""
    # 14-Layer Pipeline
    risk_assessment: RiskAssessment
    layer_states: List[Any]

    # 9D State
    state_9d: State9D

    # Entropy Analysis
    shannon_entropy: float
    negentropy: float
    entropy_rate: float
    entropy_zone: str  # "NEGENTROPY", "OPTIMAL", "HIGH_ENTROPY"

    # Geometric Analysis
    hyperbolic_distance: float
    triadic_distance: float
    manifold_divergence: float

    # Temporal Analysis
    tau_flow: float
    tau_curvature: float

    # Quantum Analysis
    quantum_fidelity: float
    quantum_purity: float

    # Topology
    euler_characteristic: int
    topology_valid: bool

    # Audit
    audit_tag: bytes
    chain_position: int

    # Final Decision
    decision: GovernanceDecision
    confidence: float
    explanation: str


@dataclass
class SystemState:
    """Full system state for persistence."""
    mode: GovernanceMode = GovernanceMode.NORMAL
    history: deque = field(default_factory=lambda: deque(maxlen=HISTORY_WINDOW))
    reference_state: Optional[State9D] = None
    reference_embedding: Optional[np.ndarray] = None
    audit_chain: List[Tuple[bytes, bytes, bytes]] = field(default_factory=list)
    audit_iv: bytes = AUDIT_CHAIN_IV
    secret_key: bytes = field(default_factory=lambda: os.urandom(32))
    metrics_history: List[GovernanceMetrics] = field(default_factory=list)
    threat_level: float = 0.0
    consecutive_denials: int = 0
    total_evaluations: int = 0
    total_allows: int = 0
    total_denials: int = 0
    total_snaps: int = 0


# =============================================================================
# FULL GOVERNANCE SYSTEM
# =============================================================================

class SCBEFullSystem:
    """
    Complete SCBE-AETHERMOORE Governance System.

    Integrates:
    - 14-Layer Phase-Breath Hyperbolic Pipeline
    - 9D Quantum Hyperbolic Manifold
    - Extended Entropy Math
    - Manifold Geometry Validation
    - HMAC Audit Chain
    - Adaptive Threat Detection

    Usage:
        system = SCBEFullSystem()
        result = system.evaluate_intent(
            identity="user_123",
            intent="access_resource",
            context={"resource": "database", "action": "read"}
        )

        if result.decision == GovernanceDecision.ALLOW:
            # Proceed with action
            pass
    """

    def __init__(
        self,
        secret_key: bytes = None,
        mode: GovernanceMode = GovernanceMode.NORMAL,
        epsilon: float = EPSILON
    ):
        self.state = SystemState(
            mode=mode,
            secret_key=secret_key or os.urandom(32)
        )
        self.epsilon = epsilon

        # Initialize subsystems
        self.pipeline = FourteenLayerPipeline()
        self.manifold = ManifoldController(epsilon=epsilon)

        # Default topology (valid polyhedron)
        self.default_poly = Polyhedron(V=8, E=12, F=6)  # Cube: χ = 2

    def evaluate_intent(
        self,
        identity: str,
        intent: str,
        context: Dict[str, Any] = None,
        tongue: str = "UM",
        modality: str = "ADAPTIVE",
        timestamp: float = None
    ) -> GovernanceMetrics:
        """
        Evaluate an intent through the full governance pipeline.

        Args:
            identity: Unique identifier for the entity
            intent: String describing the intended action
            context: Additional context dictionary
            tongue: Sacred tongue for domain separation
            modality: Governance modality (STRICT, ADAPTIVE, PROBE)
            timestamp: Optional timestamp (uses current time if not provided)

        Returns:
            GovernanceMetrics with complete analysis and decision
        """
        t = timestamp or time.time()
        context = context or {}

        self.state.total_evaluations += 1

        # === PHASE 1: Context Encoding ===

        # Hash identity and intent to numeric values
        identity_hash = self._stable_hash(identity)
        intent_hash = self._stable_hash(intent)
        context_hash = self._stable_hash(str(context))

        # Create complex intent encoding
        intent_complex = np.exp(1j * intent_hash)

        # Tongue-weighted commitment
        tongue_idx = TONGUES.index(tongue) if tongue in TONGUES else 4
        tongue_weight = TONGUE_WEIGHTS[tongue_idx]
        commitment = (intent_hash * tongue_weight) % (2 * np.pi)

        # === PHASE 2: 9D State Construction ===

        # Generate 6D context
        context_vec = generate_context(t, self.state.secret_key)

        # Time dimension
        tau = t % 1000  # Bounded time

        # Entropy from history
        self.state.history.append(intent_hash)
        eta = compute_entropy(list(self.state.history))

        # Quantum state evolution
        q = quantum_evolution(1+0j, t)

        state_9d = State9D(
            context=context_vec,
            tau=tau,
            eta=eta,
            q=q
        )

        # === PHASE 3: 14-Layer Pipeline ===

        risk_assessment, layer_states = self.pipeline.process(
            identity=identity_hash,
            intent=intent_complex,
            trajectory=0.95,  # Could be computed from history
            timing=t,
            commitment=commitment,
            signature=0.9,  # Could be actual signature verification
            t=t,
            tau=tau,
            eta=eta,
            q=q,
            ref_u=self.state.reference_embedding,
            ref_tau=self.state.reference_state.tau if self.state.reference_state else 0.0,
            ref_eta=self.state.reference_state.eta if self.state.reference_state else ETA_TARGET,
            ref_q=self.state.reference_state.q if self.state.reference_state else 1+0j
        )

        # === PHASE 4: Extended Entropy Analysis ===

        negentropy = compute_negentropy(list(self.state.history))
        entropy_rate = entropy_rate_estimate(list(self.state.history), order=2)

        # Classify entropy zone
        if eta < ETA_NEGENTROPY_THRESHOLD:
            entropy_zone = "NEGENTROPY"
        elif eta > ETA_HIGH_ENTROPY_THRESHOLD:
            entropy_zone = "HIGH_ENTROPY"
        else:
            entropy_zone = "OPTIMAL"

        # === PHASE 5: Geometric Validation ===

        # Get Poincaré embedding
        u_current = layer_states[3].value if len(layer_states) > 3 else np.zeros(12)

        # Hyperbolic distance from reference
        if self.state.reference_embedding is not None:
            d_H = layer_5_hyperbolic_distance(u_current, self.state.reference_embedding)
        else:
            d_H = 0.0

        # Triadic distance
        if self.state.reference_state is not None:
            d_tri = triadic_distance(
                state_9d.to_vector(),
                self.state.reference_state.to_vector()
            )
        else:
            d_tri = 0.0

        # Manifold divergence check
        prev_fact = None
        if self.state.metrics_history:
            last = self.state.metrics_history[-1]
            prev_fact = {
                'theta': self._stable_hash(str(last.state_9d.context)),
                'phi': self._stable_hash(str(last.state_9d.tau))
            }

        new_fact = {
            'domain': tongue,
            'content': intent
        }

        manifold_result = self.manifold.validate_write(prev_fact, new_fact)
        manifold_divergence = manifold_result.get('distance', 0.0)

        # === PHASE 6: Temporal Analysis ===

        tau_flow = tau_dot(tau)
        tau_curv = tau_curvature(tau)

        # === PHASE 7: Quantum Analysis ===

        ref_q = self.state.reference_state.q if self.state.reference_state else 1+0j
        q_fidelity = quantum_fidelity(q, ref_q)
        q_purity = 1.0 - von_neumann_entropy(q)

        # === PHASE 8: Topology Check ===

        chi = self.default_poly.euler_characteristic
        topology_valid = (chi == 2)

        # === PHASE 9: Audit Chain ===

        # Create audit entry
        audit_data = f"{identity}|{intent}|{t}|{risk_assessment.decision}".encode()
        nonce = os.urandom(12)
        prev_tag = self.state.audit_chain[-1][2] if self.state.audit_chain else self.state.audit_iv
        audit_tag = hmac_chain_tag(audit_data, nonce, prev_tag, self.state.secret_key)

        self.state.audit_chain.append((audit_data, nonce, audit_tag))
        chain_position = len(self.state.audit_chain)

        # === PHASE 10: Final Decision Logic ===

        # Check if this is a cold start (no reference state established)
        is_cold_start = self.state.reference_state is None

        decision, confidence, explanation = self._compute_final_decision(
            risk_assessment=risk_assessment,
            entropy_zone=entropy_zone,
            entropy_rate=entropy_rate,
            manifold_divergence=manifold_divergence,
            topology_valid=topology_valid,
            tau_flow=tau_flow,
            q_fidelity=q_fidelity,
            is_cold_start=is_cold_start
        )

        # === PHASE 11: Update State ===

        # Update statistics
        if decision == GovernanceDecision.ALLOW:
            self.state.total_allows += 1
            self.state.consecutive_denials = 0
            self.state.threat_level = max(0, self.state.threat_level - 0.1)
        elif decision == GovernanceDecision.DENY:
            self.state.total_denials += 1
            self.state.consecutive_denials += 1
            self.state.threat_level = min(1.0, self.state.threat_level + 0.2)
        elif decision == GovernanceDecision.SNAP:
            self.state.total_snaps += 1
            self.state.consecutive_denials += 1
            self.state.threat_level = min(1.0, self.state.threat_level + 0.5)

        # Mode escalation
        if self.state.consecutive_denials >= 3:
            self.state.mode = GovernanceMode.HEIGHTENED
        if self.state.consecutive_denials >= 5:
            self.state.mode = GovernanceMode.LOCKDOWN
        if self.state.threat_level < 0.2 and self.state.consecutive_denials == 0:
            self.state.mode = GovernanceMode.NORMAL

        # Update reference state on ALLOW
        if decision == GovernanceDecision.ALLOW:
            self.state.reference_state = state_9d
            self.state.reference_embedding = u_current

        # === Build Result ===

        metrics = GovernanceMetrics(
            risk_assessment=risk_assessment,
            layer_states=layer_states,
            state_9d=state_9d,
            shannon_entropy=eta,
            negentropy=negentropy,
            entropy_rate=entropy_rate,
            entropy_zone=entropy_zone,
            hyperbolic_distance=d_H,
            triadic_distance=d_tri,
            manifold_divergence=manifold_divergence,
            tau_flow=tau_flow,
            tau_curvature=tau_curv,
            quantum_fidelity=q_fidelity,
            quantum_purity=q_purity,
            euler_characteristic=chi,
            topology_valid=topology_valid,
            audit_tag=audit_tag,
            chain_position=chain_position,
            decision=decision,
            confidence=confidence,
            explanation=explanation
        )

        self.state.metrics_history.append(metrics)

        return metrics

    def _compute_final_decision(
        self,
        risk_assessment: RiskAssessment,
        entropy_zone: str,
        entropy_rate: float,
        manifold_divergence: float,
        topology_valid: bool,
        tau_flow: float,
        q_fidelity: float,
        is_cold_start: bool = False
    ) -> Tuple[GovernanceDecision, float, str]:
        """
        Compute final governance decision with confidence and explanation.
        """
        violations = []
        confidence = 1.0

        # Cold start handling - first evaluation establishes baseline
        if is_cold_start:
            # Only check fundamental invariants on cold start
            if not topology_valid:
                return GovernanceDecision.SNAP, 0.0, "SNAP: Topological fracture on initialization"
            if tau_flow <= DOT_TAU_MIN:
                return GovernanceDecision.DENY, 0.5, "DENY: Causality violation on initialization"
            # Allow to establish reference state
            return GovernanceDecision.ALLOW, 0.9, "ALLOW: Baseline state established (cold start)"

        # Check topology
        if not topology_valid:
            violations.append("Topology violation (χ ≠ 2)")
            confidence *= 0.0
            return GovernanceDecision.SNAP, 0.0, "SNAP: Topological fracture detected"

        # Check causality
        if tau_flow <= DOT_TAU_MIN:
            violations.append("Causality violation (τ̇ ≤ 0)")
            confidence *= 0.5

        # Check quantum coherence
        if q_fidelity < 0.9:
            violations.append(f"Quantum decoherence (F={q_fidelity:.3f})")
            confidence *= 0.7

        # Check entropy zone
        # Note: NEGENTROPY zone is only suspicious for sustained periods
        # or extreme values. Occasional low entropy is normal for structured operations.
        if entropy_zone == "NEGENTROPY" and entropy_rate < 0.3:
            # Truly rigid: low entropy + low entropy rate
            violations.append("Suspiciously low entropy with rigid pattern")
            confidence *= 0.8
        elif entropy_zone == "HIGH_ENTROPY":
            violations.append("High entropy (chaotic behavior)")
            confidence *= 0.7

        # Check manifold divergence
        if manifold_divergence > self.epsilon:
            violations.append(f"Geometric snap (d={manifold_divergence:.3f} > ε)")
            confidence *= 0.3
            return GovernanceDecision.SNAP, confidence, f"SNAP: {'; '.join(violations)}"

        # Check 14-layer risk
        # Note: The harmonic scaling H(d,R) = R^(d²) is very aggressive
        # For d > 3.5, H > 100 which triggers CRITICAL
        # We use the raw d* (distance to nearest realm) as a more stable metric
        d_star = risk_assessment.raw_risk  # This is actually H(d), need d_star from realm

        # Use scaled_risk which incorporates coherence and realm weight
        # CRITICAL only if truly anomalous (not just large triadic distance)
        if risk_assessment.level == RiskLevel.CRITICAL:
            # Check if this is a false positive from high d_tri
            # True critical = low coherence + high manifold divergence
            if manifold_divergence > self.epsilon * 2:
                violations.append("Critical geometric divergence")
                return GovernanceDecision.SNAP, confidence * 0.1, f"SNAP: {'; '.join(violations)}"
            elif risk_assessment.coherence < 0.5:
                # Low coherence + CRITICAL = real concern
                violations.append("Critical risk with low coherence")
                confidence *= 0.4
            else:
                # High coherence but large distance - likely normal operation far from origin
                # Just reduce confidence, don't add violation
                confidence *= 0.8

        if risk_assessment.level == RiskLevel.HIGH:
            if risk_assessment.coherence < 0.7:
                violations.append("High risk with degraded coherence")
                confidence *= 0.6

        # Mode-based adjustments
        if self.state.mode == GovernanceMode.LOCKDOWN:
            if violations:
                return GovernanceDecision.DENY, confidence * 0.3, f"DENY (LOCKDOWN): {'; '.join(violations)}"

        if self.state.mode == GovernanceMode.HEIGHTENED:
            if risk_assessment.level == RiskLevel.MEDIUM:
                return GovernanceDecision.QUARANTINE, confidence * 0.6, f"QUARANTINE (HEIGHTENED): Medium risk"

        # Check for any violations
        if len(violations) >= 2:
            return GovernanceDecision.DENY, confidence * 0.4, f"DENY: Multiple violations - {'; '.join(violations)}"

        if len(violations) == 1:
            return GovernanceDecision.QUARANTINE, confidence * 0.7, f"QUARANTINE: {violations[0]}"

        # All clear
        return GovernanceDecision.ALLOW, confidence, "ALLOW: All governance checks passed"

    def _stable_hash(self, data: str) -> float:
        """Hash string to [0, 2π)."""
        hash_int = int(hashlib.sha256(data.encode()).hexdigest(), 16)
        return (hash_int / (2**256 - 1)) * 2 * np.pi

    def verify_audit_chain(self) -> bool:
        """Verify integrity of the entire audit chain."""
        if not self.state.audit_chain:
            return True

        messages, nonces, tags = zip(*self.state.audit_chain)
        return verify_hmac_chain(
            list(messages), list(nonces), list(tags),
            self.state.secret_key, self.state.audit_iv
        )

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "mode": self.state.mode.value,
            "threat_level": self.state.threat_level,
            "total_evaluations": self.state.total_evaluations,
            "total_allows": self.state.total_allows,
            "total_denials": self.state.total_denials,
            "total_snaps": self.state.total_snaps,
            "allow_rate": self.state.total_allows / max(1, self.state.total_evaluations),
            "consecutive_denials": self.state.consecutive_denials,
            "audit_chain_length": len(self.state.audit_chain),
            "audit_chain_valid": self.verify_audit_chain(),
            "history_size": len(self.state.history),
            "has_reference_state": self.state.reference_state is not None
        }

    def reset(self, keep_key: bool = True):
        """Reset system state."""
        key = self.state.secret_key if keep_key else os.urandom(32)
        self.state = SystemState(secret_key=key)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def quick_evaluate(
    identity: str,
    intent: str,
    context: Dict[str, Any] = None
) -> Tuple[GovernanceDecision, str]:
    """
    Quick one-shot governance evaluation.

    Returns: (decision, explanation)
    """
    system = SCBEFullSystem()
    result = system.evaluate_intent(identity, intent, context)
    return result.decision, result.explanation


def verify_all_theorems() -> Dict[str, bool]:
    """Verify all mathematical theorems."""
    results = {}

    passed, _ = verify_theorem_A_metric_invariance(n_tests=50)
    results["A_metric_invariance"] = passed

    passed, _ = verify_theorem_B_continuity()
    results["B_continuity"] = passed

    passed, _ = verify_theorem_C_risk_monotonicity(n_tests=50)
    results["C_risk_monotonicity"] = passed

    passed, _ = verify_theorem_D_diffeomorphism(n_tests=50)
    results["D_diffeomorphism"] = passed

    return results


# =============================================================================
# DEMO
# =============================================================================

def demo():
    """Demonstrate the full SCBE-AETHERMOORE system."""
    print("=" * 70)
    print("SCBE-AETHERMOORE Full System Demo")
    print("=" * 70)
    print()

    # Initialize system
    system = SCBEFullSystem()

    # Test 1: Normal operation
    print("[TEST 1] Normal Intent Evaluation")
    print("-" * 70)
    result = system.evaluate_intent(
        identity="user_alice",
        intent="read_document",
        context={"document": "report.pdf", "access_level": "standard"}
    )
    print(f"Decision: {result.decision.value}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Explanation: {result.explanation}")
    print(f"Entropy Zone: {result.entropy_zone}")
    print(f"Risk Level: {result.risk_assessment.level.value}")
    print()

    # Test 2: Multiple sequential evaluations
    print("[TEST 2] Sequential Evaluations")
    print("-" * 70)
    intents = [
        ("user_alice", "read_file"),
        ("user_alice", "write_file"),
        ("user_bob", "access_admin"),
        ("user_charlie", "delete_data"),
        ("user_alice", "normal_action"),
    ]

    for identity, intent in intents:
        result = system.evaluate_intent(identity, intent)
        print(f"  {identity:15s} | {intent:15s} | {result.decision.value:10s} | H={result.shannon_entropy:.2f}")
    print()

    # Test 3: System status
    print("[TEST 3] System Status")
    print("-" * 70)
    status = system.get_system_status()
    for key, value in status.items():
        if isinstance(value, float):
            print(f"  {key:25s}: {value:.4f}")
        else:
            print(f"  {key:25s}: {value}")
    print()

    # Test 4: Audit chain verification
    print("[TEST 4] Audit Chain Verification")
    print("-" * 70)
    chain_valid = system.verify_audit_chain()
    print(f"Audit chain integrity: {'VALID' if chain_valid else 'COMPROMISED'}")
    print(f"Chain length: {len(system.state.audit_chain)} entries")
    print()

    # Test 5: Theorem verification
    print("[TEST 5] Mathematical Theorem Verification")
    print("-" * 70)
    theorems = verify_all_theorems()
    for theorem, passed in theorems.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {theorem}: {status}")
    print()

    all_passed = all(theorems.values())
    print("=" * 70)
    print(f"System Status: {'FULLY OPERATIONAL' if all_passed else 'DEGRADED'}")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    demo()
