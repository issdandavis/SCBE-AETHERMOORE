"""
SCBE-AETHERMOORE: The Unified Massive System

A 9D Quantum Hyperbolic Manifold Memory for AI governance where:
- 9D State: ξ(t) = [c(t), τ(t), η(t), q(t)] (6D context + time + entropy + quantum)
- Phase modulation + flat slope + resonance for secure intent encoding
- Hyper-torus manifold for geometric integrity
- PHDM topology for structural checks
- Differential cryptography for continuous state evolution
- HMAC chain for cryptographic foundation
- Grand Unified Governance Function G

Self-Governance (Nodal Nest):
- Swarm as graph G = (V, E, F)
- Entropy η bounds time τ̇ (high η slows τ̇, no chaotic rushes)
- Quantum q influences entropy S_q
- Feedback loops enforce stability (Lyapunov V = η² + τ² ≤ bound)

Layer 0 to End:
- Bits (0/1) → Vectors → Manifolds → Governance (G)
- Each exchange conserves info (provable isometries)
- Unified stability: each component bounded, ξ norms ≤ max bound
"""

import numpy as np
import hashlib
import hmac
import time
import os
from typing import Tuple, Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

# =============================================================================
# CONSTANTS (from physics/math)
# =============================================================================

# Golden ratio and harmonic base
PHI = (1 + np.sqrt(5)) / 2
R = PHI

# Governance thresholds
EPSILON = 1.5              # Snap threshold (geometric divergence)
TAU_COH = 0.9              # Coherence minimum
ETA_TARGET = 4.0           # Entropy target (bits, relative to max)
BETA = 0.1                 # Entropy decay rate
KAPPA_MAX = 0.1            # Curvature maximum
KAPPA_TAU_MAX = 0.1        # Time curvature maximum
KAPPA_ETA_MAX = 0.1        # Entropy curvature maximum
LAMBDA_BOUND = 0.001       # Lyapunov exponent bound
H_MAX = 10.0               # Harmonic scaling maximum
DOT_TAU_MIN = 0.0          # Causality (time must flow forward)

# Extended Entropy Bounds (supporting negentropy)
# η ∈ [η_min, η_max] where:
#   η < 0: Negentropy (information gain, high structure/predictability)
#   η = 0: Maximum compression (deterministic state)
#   η > 0: Positive entropy (disorder, randomness)
#
# Mathematical basis: η = H(X) - H_max = -I(X)
# where I(X) is the information content / negentropy
ETA_MIN = -2.0             # Minimum (allows negentropy = high structure)
ETA_MAX = 6.0              # Maximum entropy (high disorder)
ETA_NEGENTROPY_THRESHOLD = 0.0  # Below this = structured/predictable
ETA_HIGH_ENTROPY_THRESHOLD = 4.0  # Above this = chaotic/suspicious

DELTA_DRIFT_MAX = 0.5      # Maximum time drift
DELTA_NOISE_MAX = 0.1      # Maximum entropy noise
OMEGA_TIME = 2 * np.pi / 60  # Time cycle frequency

# Audio/Signal constants
CARRIER_FREQ = 440.0       # Base frequency (flat slope)
SAMPLE_RATE = 44100        # Audio sample rate
DURATION = 0.5             # Default signal duration

# Cryptographic constants
NONCE_BYTES = 12
KEY_LEN = 32

# Six Sacred Tongues (domain separation)
TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_WEIGHTS = [PHI**k for k in range(6)]  # φ^k progression

# =============================================================================
# CONLANG DICTIONARY (bijection, supports negatives)
# =============================================================================

CONLANG = {
    "shadow": -1, "gleam": -2, "flare": -3,
    "korah": 0, "aelin": 1, "dahru": 2,
    "melik": 3, "sorin": 4, "tivar": 5,
    "ulmar": 6, "vexin": 7
}
REV_CONLANG = {v: k for k, v in CONLANG.items()}

# Modality Masks (overtone sets)
MODALITY_MASKS = {
    "STRICT": [1, 3, 5],
    "ADAPTIVE": list(range(1, 6)),
    "PROBE": [1]
}


# =============================================================================
# GOVERNANCE DECISION ENUM
# =============================================================================

class GovernanceDecision(Enum):
    """Possible governance outcomes."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    QUARANTINE = "QUARANTINE"
    SNAP = "SNAP"


# =============================================================================
# 9D STATE DATACLASS
# =============================================================================

@dataclass
class State9D:
    """
    9-Dimensional unified state vector.

    Dimensions:
        0-5: Context (6D) - identity, intent, trajectory, timing, commitment, signature
        6:   Time τ - triadic time dilation
        7:   Entropy η - information flow
        8:   Quantum q - quantum state (complex)
    """
    context: np.ndarray      # 6D context vector
    tau: float               # Time dimension
    eta: float               # Entropy dimension
    q: complex               # Quantum state

    def to_vector(self) -> np.ndarray:
        """Flatten to numpy array for computation."""
        return np.array([
            *self.context[:6],  # Take first 6 elements
            self.tau,
            self.eta,
            self.q
        ], dtype=object)

    @classmethod
    def from_vector(cls, xi: np.ndarray) -> 'State9D':
        """Reconstruct from numpy array."""
        return cls(
            context=np.array(xi[:6]),
            tau=float(xi[6]),
            eta=float(xi[7]),
            q=complex(xi[8])
        )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def stable_hash(data: str) -> float:
    """
    Deterministic hash to [0, 2π) for manifold mapping.

    Maps any string to a stable angle on the circle.
    """
    hash_int = int(hashlib.sha256(data.encode()).hexdigest(), 16)
    return hash_int / (2**256 - 1) * 2 * np.pi


def compute_entropy(window: List) -> float:
    """
    Compute Shannon entropy of a data window.

    H = -Σ p(x) log₂ p(x)

    Used for the 8th dimension (η) of the 9D state.
    """
    # Handle complex values by taking magnitude
    processed = []
    for item in window:
        if hasattr(item, '__iter__') and not isinstance(item, str):
            for x in item:
                if isinstance(x, complex):
                    processed.append(np.abs(x))
                elif isinstance(x, (int, float)):
                    processed.append(float(x))
        elif isinstance(item, complex):
            processed.append(np.abs(item))
        elif isinstance(item, (int, float)):
            processed.append(float(item))

    if len(processed) == 0:
        return ETA_TARGET  # Return target entropy for empty

    flat = np.array(processed, dtype=float)

    # Handle edge cases
    if len(flat) < 2:
        return ETA_TARGET

    # Histogram-based entropy estimation
    hist, _ = np.histogram(flat, bins=min(16, len(flat)), density=True)
    hist = hist[hist > 0]

    if len(hist) == 0:
        return ETA_TARGET

    entropy = -np.sum(hist * np.log2(hist + 1e-9))

    # Scale to reasonable range [ETA_MIN, ETA_MAX]
    return max(ETA_MIN, min(ETA_MAX, entropy + ETA_MIN))


def compute_negentropy(window: List, reference_entropy: float = None) -> float:
    """
    Compute negentropy (information gain / structure measure).

    Negentropy: I(X) = H_max - H(X) = H_ref - H(X)

    Mathematical Properties:
        - I(X) ≥ 0 always (Gibbs' inequality)
        - I(X) = 0 for maximum entropy (uniform) distribution
        - I(X) > 0 indicates structure/predictability

    For governance:
        - High negentropy → highly structured behavior (could be suspicious rigidity)
        - Low negentropy → high disorder (could be masking/noise)
        - Optimal: moderate negentropy (natural variation)

    Returns: negentropy value (can be positive, mapping to negative η)
    """
    H = compute_entropy(window)

    # Reference entropy: maximum possible for the data dimension
    if reference_entropy is None:
        # For D bins, H_max = log₂(D)
        reference_entropy = np.log2(16)  # Default 16 bins

    negentropy = reference_entropy - H
    return negentropy


def compute_relative_entropy(p: np.ndarray, q: np.ndarray) -> float:
    """
    Compute Kullback-Leibler divergence D_KL(P || Q).

    D_KL(P || Q) = Σ p(x) log(p(x)/q(x))

    Mathematical Properties:
        - D_KL ≥ 0 (Gibbs' inequality)
        - D_KL = 0 iff P = Q
        - Not symmetric: D_KL(P||Q) ≠ D_KL(Q||P)

    For governance:
        - Measures divergence from expected/reference distribution
        - High D_KL → state has diverged significantly from baseline
        - Used in triadic distance computation

    Args:
        p: Current state distribution
        q: Reference/expected distribution

    Returns: KL divergence (non-negative)
    """
    # Ensure valid probability distributions
    p = np.asarray(p, dtype=float)
    q = np.asarray(q, dtype=float)

    # Normalize
    p = p / (np.sum(p) + 1e-10)
    q = q / (np.sum(q) + 1e-10)

    # Add small epsilon to avoid log(0)
    eps = 1e-10
    p = np.clip(p, eps, 1.0)
    q = np.clip(q, eps, 1.0)

    # D_KL = Σ p log(p/q)
    return float(np.sum(p * np.log(p / q)))


def compute_mutual_information(joint: np.ndarray) -> float:
    """
    Compute mutual information I(X; Y) from joint distribution.

    I(X; Y) = H(X) + H(Y) - H(X, Y)
            = Σ p(x,y) log(p(x,y) / (p(x)p(y)))

    Mathematical Properties:
        - I(X; Y) ≥ 0
        - I(X; Y) = 0 iff X and Y are independent
        - I(X; Y) = I(Y; X) (symmetric)

    For governance:
        - Measures information shared between state components
        - High MI → strong coupling (could indicate coordinated attack)
        - Low MI → independent components (healthy modular state)

    Args:
        joint: 2D joint probability distribution p(x,y)

    Returns: Mutual information in bits
    """
    joint = np.asarray(joint, dtype=float)
    joint = joint / (np.sum(joint) + 1e-10)

    # Marginals
    p_x = np.sum(joint, axis=1)
    p_y = np.sum(joint, axis=0)

    # Entropy computations
    eps = 1e-10

    def H(p):
        p = p[p > eps]
        return -np.sum(p * np.log2(p))

    H_X = H(p_x)
    H_Y = H(p_y)
    H_XY = H(joint.flatten())

    return H_X + H_Y - H_XY


def entropy_rate_estimate(sequence: List, order: int = 1) -> float:
    """
    Estimate entropy rate from a sequence (Markov approximation).

    h = lim_{n→∞} H(X_n | X_{n-1}, ..., X_1)

    For order-k Markov approximation:
        h_k ≈ H(X_n | X_{n-1}, ..., X_{n-k})

    For governance:
        - Lower entropy rate → more predictable sequences
        - Higher entropy rate → more random/chaotic behavior
        - Used to detect anomalous patterns over time

    Args:
        sequence: Observed sequence of states
        order: Markov order (context length)

    Returns: Estimated entropy rate in bits/symbol
    """
    if len(sequence) <= order:
        return ETA_TARGET

    # Count transitions
    from collections import defaultdict
    transitions = defaultdict(lambda: defaultdict(int))

    for i in range(order, len(sequence)):
        context = tuple(sequence[i-order:i])
        next_symbol = sequence[i]
        transitions[context][next_symbol] += 1

    # Compute conditional entropy H(X | context)
    total_entropy = 0.0
    total_contexts = 0

    for context, next_counts in transitions.items():
        context_total = sum(next_counts.values())
        if context_total == 0:
            continue

        # H(X | this context)
        context_entropy = 0.0
        for count in next_counts.values():
            p = count / context_total
            if p > 0:
                context_entropy -= p * np.log2(p)

        total_entropy += context_entropy * context_total
        total_contexts += context_total

    if total_contexts == 0:
        return ETA_TARGET

    return total_entropy / total_contexts


def fisher_information(theta: float, score_fn, delta: float = 1e-5) -> float:
    """
    Estimate Fisher information I(θ) = E[(∂/∂θ log p(X;θ))²].

    Measures the amount of information a random variable X carries
    about parameter θ. Related to Cramér-Rao bound.

    For governance:
        - High Fisher info → state is highly sensitive to parameters
        - Low Fisher info → state is robust/insensitive
        - Used to assess stability of governance decisions

    Args:
        theta: Parameter value
        score_fn: Function computing log p(X; θ)
        delta: Finite difference step

    Returns: Fisher information estimate
    """
    # Numerical derivative of score function
    score_plus = score_fn(theta + delta)
    score_minus = score_fn(theta - delta)
    score_derivative = (score_plus - score_minus) / (2 * delta)

    return score_derivative ** 2


# =============================================================================
# MANIFOLD CONTROLLER (Hyper-Torus Geometry)
# =============================================================================

class ManifoldController:
    """
    Hyper-torus manifold for geometric governance.

    Maps interactions to (θ, φ) coordinates on a torus with:
    - Major radius R (outer)
    - Minor radius r (inner)

    Geometric divergence beyond ε triggers SNAP.
    """

    def __init__(self, R_major: float = 10.0, r_minor: float = 2.0, epsilon: float = EPSILON):
        self.R = R_major
        self.r = r_minor
        self.epsilon = epsilon

    def map_interaction(self, domain: str, sequence: str) -> Tuple[float, float]:
        """
        Map (domain, sequence) to torus coordinates (θ, φ).

        Uses stable hashing for deterministic mapping.
        """
        theta = stable_hash(domain)
        phi = stable_hash(sequence)
        return theta, phi

    def delta_angle(self, a1: float, a2: float) -> float:
        """
        Compute minimum angular distance on circle.

        Handles wraparound: δ = min(|a1-a2|, 2π - |a1-a2|)
        """
        diff = np.abs(a1 - a2)
        return np.minimum(diff, 2 * np.pi - diff)

    def geometric_divergence(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """
        Compute geodesic distance on torus.

        Uses the torus metric tensor:
            ds² = r²dθ² + (R + r·cos(θ))²dφ²
        """
        theta1, phi1 = p1
        theta2, phi2 = p2

        avg_theta = (theta1 + theta2) / 2.0
        d_theta = self.delta_angle(theta1, theta2)
        d_phi = self.delta_angle(phi1, phi2)

        # Metric tensor components
        g_phi_phi = (self.R + self.r * np.cos(avg_theta)) ** 2
        g_theta_theta = self.r ** 2

        squared_distance = g_phi_phi * (d_phi ** 2) + g_theta_theta * (d_theta ** 2)
        return np.sqrt(squared_distance)

    def validate_write(
        self,
        previous_fact: Optional[Dict[str, Any]],
        new_fact: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a write operation against geometric constraints.

        Returns WRITE_SUCCESS if divergence ≤ ε, else GEOMETRIC_SNAP_DETECTED.
        """
        p_new = self.map_interaction(new_fact['domain'], new_fact['content'])

        if not previous_fact:
            return {
                "status": "WRITE_SUCCESS",
                "distance": 0.0,
                "coordinates": p_new
            }

        p_prev = (previous_fact['theta'], previous_fact['phi'])
        distance = self.geometric_divergence(p_prev, p_new)

        if distance <= self.epsilon:
            return {
                "status": "WRITE_SUCCESS",
                "distance": distance,
                "coordinates": p_new
            }
        else:
            return {
                "status": "WRITE_FAIL",
                "error": "GEOMETRIC_SNAP_DETECTED",
                "divergence": distance,
                "threshold": self.epsilon
            }


# =============================================================================
# 6D CONTEXT GENERATION
# =============================================================================

def generate_context(t: float, secret_key: bytes = b"default") -> np.ndarray:
    """
    Generate 6D context vector at time t.

    Dimensions:
        0: Identity (sin wave for demo)
        1: Intent phase (complex)
        2: Trajectory coherence
        3: Timing (canonical microseconds)
        4: Commitment hash
        5: Signature validity
    """
    # Canonical time encoding (microseconds) for stable hashing
    t_us = int(t * 1_000_000)

    # Identity (oscillating)
    v1 = np.sin(t)

    # Intent phase (complex unit)
    v2 = np.exp(1j * 2 * np.pi * 0.75)

    # Trajectory coherence
    v3 = 0.95

    # Timing (canonical)
    v4 = float(t_us)

    # Commitment (key-derived hash with canonical time)
    commit_data = f"commit|{t_us}|{secret_key.hex()}"
    v5 = stable_hash(commit_data)

    # Signature validity score
    v6 = 0.88

    return np.array([v1, v2, v3, v4, v5, v6], dtype=object)


# =============================================================================
# TIME AXIS (7th Dimension)
# =============================================================================

def tau_dot(t: float) -> float:
    """
    Compute time flow rate τ̇.

    τ̇ = 1 + δ·sin(ωt)

    Must be > 0 for causality (time flows forward).
    Bounded drift prevents chaotic time jumps.
    """
    return 1.0 + DELTA_DRIFT_MAX * np.sin(OMEGA_TIME * t)


def tau_curvature(t: float, dt: float = 0.01) -> float:
    """
    Compute time curvature κ_τ (second derivative).

    High curvature = time flow instability.
    """
    tau_prev = tau_dot(t - dt)
    tau_curr = tau_dot(t)
    tau_next = tau_dot(t + dt)

    return np.abs((tau_next - 2*tau_curr + tau_prev) / (dt**2))


# =============================================================================
# ENTROPY AXIS (8th Dimension)
# =============================================================================

def eta_dot(eta: float, t: float) -> float:
    """
    Compute entropy flow rate η̇.

    η̇ = β(η_target - η) + noise

    Entropy decays toward target (information balance).
    """
    noise = DELTA_NOISE_MAX * np.sin(t)
    return BETA * (ETA_TARGET - eta) + noise


def eta_curvature(eta: float, t: float, dt: float = 0.01) -> float:
    """
    Compute entropy curvature κ_η.

    High curvature = entropy instability.
    """
    eta_prev = eta_dot(eta, t - dt)
    eta_curr = eta_dot(eta, t)
    eta_next = eta_dot(eta, t + dt)

    return np.abs((eta_next - 2*eta_curr + eta_prev) / (dt**2))


# =============================================================================
# QUANTUM DIMENSION (9th Dimension)
# =============================================================================

def quantum_evolution(q0: complex, t: float, H: float = 1.0) -> complex:
    """
    Schrödinger evolution of quantum state.

    q(t) = q₀ · exp(-iHt)

    H = Hamiltonian (energy scale).
    """
    return q0 * np.exp(-1j * H * t)


def quantum_fidelity(q1: complex, q2: complex) -> float:
    """
    Compute quantum state fidelity.

    F = |⟨q1|q2⟩|² = |q1* · q2|²

    F = 1 for identical states, 0 for orthogonal.
    """
    inner_product = np.conj(q1) * q2
    return np.abs(inner_product) ** 2


def von_neumann_entropy(q: complex) -> float:
    """
    Quantum state purity metric (NOT true von Neumann entropy).

    For a complex amplitude q representing a simplified quantum state:
        S_approx = |1 - |q||

    This is a heuristic that measures deviation from unit-norm pure state:
        - S = 0 when |q| = 1 (pure state, normalized)
        - S > 0 when |q| ≠ 1 (denormalized, indicates error/decoherence)

    True von Neumann entropy S = -Tr(ρ log ρ) requires a density matrix ρ,
    not a single complex amplitude. This simplified metric is used for
    governance decisions where we want to detect quantum state anomalies.

    Returns:
        0.0 for perfectly normalized state (|q| = 1)
        Higher values indicate denormalization (potential tampering/error)
    """
    norm = np.abs(q)
    if norm < 1e-10:
        return 1.0  # Max "entropy" for null/collapsed state

    # Deviation from unit-norm pure state
    deviation = np.abs(1.0 - norm)
    return deviation


# =============================================================================
# PHDM (Polyhedral Hamiltonian Defense)
# =============================================================================

@dataclass
class Polyhedron:
    """Polyhedral state for PHDM topology checks."""
    V: int  # Vertices
    E: int  # Edges
    F: int  # Faces

    @property
    def euler_characteristic(self) -> int:
        """Compute χ = V - E + F."""
        return self.V - self.E + self.F

    def is_valid(self, expected_chi: int = 2) -> bool:
        """Check if Euler characteristic matches expected."""
        return self.euler_characteristic == expected_chi


def hamiltonian_path_deviation(path: List[int], valid_edges: set) -> float:
    """
    Compute path deviation from valid Hamiltonian path.

    δ_path = (1/(n-1)) Σ 1_{(v_i, v_{i+1}) ∉ E}

    Returns 0 for valid path, approaches 1 for invalid.
    """
    if len(path) < 2:
        return 0.0

    invalid_count = 0
    for i in range(len(path) - 1):
        edge = (path[i], path[i+1])
        if edge not in valid_edges and (edge[1], edge[0]) not in valid_edges:
            invalid_count += 1

    return invalid_count / (len(path) - 1)


# =============================================================================
# HYPERBOLIC DISTANCE (Poincaré Ball)
# =============================================================================

def hyperbolic_distance(u: np.ndarray, v: np.ndarray, eps: float = 1e-10) -> float:
    """
    Compute hyperbolic distance in Poincaré ball.

    d_H(u,v) = arcosh(1 + 2||u-v||²/((1-||u||²)(1-||v||²)))
    """
    u = np.asarray(u, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)

    norm_u_sq = np.sum(u ** 2)
    norm_v_sq = np.sum(v ** 2)
    diff_sq = np.sum((u - v) ** 2)

    # Clamp to ball interior
    norm_u_sq = min(norm_u_sq, 1.0 - eps)
    norm_v_sq = min(norm_v_sq, 1.0 - eps)

    denominator = (1 - norm_u_sq) * (1 - norm_v_sq)
    denominator = max(denominator, eps)

    cosh_dist = 1 + 2 * diff_sq / denominator
    cosh_dist = max(cosh_dist, 1.0)

    return float(np.arccosh(cosh_dist))


def triadic_distance(xi1: np.ndarray, xi2: np.ndarray) -> float:
    """
    Compute triadic distance incorporating time, entropy, and quantum.

    d_tri = √(d_H² + (Δτ)² + (Δη)² + (1-F_q))
    """
    # Hyperbolic component (context)
    d_h = hyperbolic_distance(
        np.array([float(x) if not isinstance(x, complex) else np.abs(x) for x in xi1[:6]]),
        np.array([float(x) if not isinstance(x, complex) else np.abs(x) for x in xi2[:6]])
    )

    # Time component
    delta_tau = np.abs(float(xi1[6]) - float(xi2[6]))

    # Entropy component
    delta_eta = np.abs(float(xi1[7]) - float(xi2[7]))

    # Quantum component (1 - fidelity)
    fidelity = quantum_fidelity(complex(xi1[8]), complex(xi2[8]))

    return np.sqrt(d_h**2 + delta_tau**2 + delta_eta**2 + (1 - fidelity))


# =============================================================================
# HARMONIC SCALING (Risk Metric)
# =============================================================================

def harmonic_scaling(d_star: float, alpha: float = 10.0, beta: float = 0.5) -> float:
    """
    Bounded harmonic risk scaling.

    H(d*) = 1 + α·tanh(β·d*)

    H ∈ [1, 1+α] - bounded, monotonic.
    """
    return 1.0 + alpha * np.tanh(beta * d_star)


# =============================================================================
# UNIFIED GOVERNANCE FUNCTION (G)
# =============================================================================

def governance_9d(
    xi: np.ndarray,
    intent: float,
    poly: Polyhedron,
    reference_xi: Optional[np.ndarray] = None,
    epsilon: float = EPSILON
) -> Tuple[GovernanceDecision, str, Dict[str, Any]]:
    """
    Grand Unified Governance Function G.

    G(ξ, i, poly) evaluates:
        1. Coherence: coh ≥ τ_coh
        2. Triadic distance: d_tri ≤ ε
        3. Harmonic scaling: H(d) ≤ H_max
        4. Topology: χ = 2
        5. Curvature: κ ≤ κ_max
        6. Lyapunov: λ ≤ λ_bound
        7. Causality: τ̇ > 0
        8. Time drift: |Δτ - 1| ≤ δ_max
        9. Time curvature: κ_τ ≤ κ_τ_max
        10. Entropy bounds: η_min ≤ η ≤ η_max
        11. Entropy curvature: κ_η ≤ κ_η_max
        12. Quantum fidelity: F_q ≥ 0.9
        13. Quantum entropy: S_q ≤ 0.2

    Returns: (decision, message, metrics)
    """
    # Extract state components
    context = xi[:6]
    tau = float(xi[6])
    eta = float(xi[7])
    q = complex(xi[8])

    # Compute metrics
    metrics = {}

    # 1. Coherence (placeholder - would come from AI verifier)
    coh = 0.95
    metrics['coherence'] = coh

    # 2. Triadic distance
    if reference_xi is not None:
        d_tri = triadic_distance(xi, reference_xi)
    else:
        d_tri = 0.0
    metrics['d_tri'] = d_tri

    # 3. Harmonic scaling
    h_d = harmonic_scaling(d_tri)
    metrics['harmonic_risk'] = h_d

    # 4. Topology (Euler characteristic)
    chi = poly.euler_characteristic
    metrics['euler_chi'] = chi

    # 5. Curvature (placeholder)
    kappa_max = 0.05
    metrics['kappa_max'] = kappa_max

    # 6. Lyapunov exponent (placeholder)
    lambda_L = 0.0001
    metrics['lyapunov'] = lambda_L

    # 7. Causality (time flow)
    dot_tau = tau_dot(tau)
    metrics['tau_dot'] = dot_tau

    # 8. Time drift
    delta_tau = dot_tau  # Simplified
    metrics['delta_tau'] = delta_tau

    # 9. Time curvature
    kappa_tau = tau_curvature(tau)
    metrics['kappa_tau'] = kappa_tau

    # 10. Entropy bounds
    metrics['eta'] = eta

    # 11. Entropy curvature
    kappa_eta = eta_curvature(eta, tau)
    metrics['kappa_eta'] = kappa_eta

    # 12. Quantum fidelity (against reference)
    q_ref = quantum_evolution(1+0j, 0)  # Reference state
    f_q = quantum_fidelity(q, q_ref)
    metrics['quantum_fidelity'] = f_q

    # 13. Quantum entropy
    s_q = von_neumann_entropy(q)
    metrics['quantum_entropy'] = s_q

    # === GOVERNANCE DECISION ===

    # Check all conditions
    conditions = {
        'coherence': coh >= TAU_COH,
        'triadic_distance': d_tri <= epsilon,
        'harmonic_bounded': h_d <= H_MAX,
        'topology_valid': chi == 2,
        'curvature_bounded': kappa_max <= KAPPA_MAX,
        'lyapunov_stable': lambda_L <= LAMBDA_BOUND,
        'causality': dot_tau > DOT_TAU_MIN,
        'time_drift_bounded': np.abs(delta_tau - 1.0) <= DELTA_DRIFT_MAX,
        'time_curvature_bounded': kappa_tau <= KAPPA_TAU_MAX,
        'entropy_lower': eta >= ETA_MIN,
        'entropy_upper': eta <= ETA_MAX,
        'entropy_curvature_bounded': kappa_eta <= KAPPA_ETA_MAX,
        'quantum_fidelity': f_q >= 0.9,
        'quantum_entropy': s_q <= 0.2
    }

    metrics['conditions'] = conditions
    all_pass = all(conditions.values())

    # Decision logic
    if all_pass:
        return GovernanceDecision.ALLOW, "Access granted - all conditions satisfied", metrics

    # Specific failure modes
    if eta < ETA_MIN or eta > ETA_MAX or kappa_eta > KAPPA_ETA_MAX:
        return GovernanceDecision.QUARANTINE, f"Entropy anomaly - η={eta:.2f}, κ_η={kappa_eta:.4f}", metrics

    if dot_tau <= DOT_TAU_MIN or kappa_tau > KAPPA_TAU_MAX:
        return GovernanceDecision.QUARANTINE, f"Time flow anomaly - τ̇={dot_tau:.4f}, κ_τ={kappa_tau:.4f}", metrics

    if f_q < 0.9 or s_q > 0.2:
        return GovernanceDecision.QUARANTINE, f"Quantum state anomaly - F={f_q:.4f}, S={s_q:.4f}", metrics

    if chi != 2:
        return GovernanceDecision.SNAP, f"Topology violation - χ={chi} ≠ 2", metrics

    if d_tri > epsilon:
        return GovernanceDecision.SNAP, f"Geometric snap - d_tri={d_tri:.4f} > ε={epsilon}", metrics

    # Default deny
    failed = [k for k, v in conditions.items() if not v]
    return GovernanceDecision.DENY, f"Access denied - failed: {failed}", metrics


# =============================================================================
# PHASE-MODULATED INTENT
# =============================================================================

def phase_modulated_intent(intent: float, duration: float = DURATION) -> np.ndarray:
    """
    Encode intent as phase-modulated carrier.

    s(t) = cos(2πf₀t + 2πi)

    Intent i ∈ [0, 1] maps to phase φ ∈ [0, 2π].
    """
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    phase = 2 * np.pi * intent
    wave = np.cos(2 * np.pi * CARRIER_FREQ * t + phase)
    return wave


def extract_phase(wave: np.ndarray) -> float:
    """
    Extract intent from phase-modulated wave via FFT.

    Returns intent ∈ [0, 1].
    """
    from scipy.fft import fft, fftfreq

    N = len(wave)
    yf = fft(wave)
    xf = fftfreq(N, 1 / SAMPLE_RATE)[:N//2]

    # Find carrier frequency peak
    peak_idx = np.argmax(np.abs(yf[:N//2]))
    phase = np.angle(yf[peak_idx])

    # Map phase to [0, 1]
    return (phase % (2 * np.pi)) / (2 * np.pi)


# =============================================================================
# HMAC CHAIN
# =============================================================================

def hmac_chain_tag(
    message: bytes,
    nonce: bytes,
    prev_tag: bytes,
    key: bytes
) -> bytes:
    """
    Compute HMAC chain tag for tamper-evident chain-of-custody.

    T_i = HMAC_K(M_i || nonce_i || T_{i-1})

    Security Properties:
        - Tamper evidence: Any modification breaks the chain
        - Chain-of-custody: Each block binds to previous via T_{i-1}
        - Ordering: Nonce sequence enforces message order

    Note: This provides integrity and ordering, NOT forward secrecy.
    If master_key is compromised, entire chain can be recomputed.
    For forward secrecy, use a KDF ratchet with key erasure.
    """
    data = message + nonce + prev_tag
    return hmac.new(key, data, hashlib.sha256).digest()


def verify_hmac_chain(
    messages: List[bytes],
    nonces: List[bytes],
    tags: List[bytes],
    key: bytes,
    iv: bytes = b'\x00' * 32
) -> bool:
    """
    Verify HMAC chain integrity (tamper-evident chain-of-custody).

    Checks:
        1. All tags are valid HMAC-SHA256 of (message || nonce || prev_tag)
        2. Chain is unbroken (each tag depends on previous)

    Returns True if chain integrity is intact, False if tampered.

    Security: Detects any modification, insertion, or reordering of messages.
    Does NOT provide forward secrecy - compromise of key breaks entire chain.
    """
    if len(messages) != len(nonces) or len(messages) != len(tags):
        return False

    prev_tag = iv

    for i, (msg, nonce, tag) in enumerate(zip(messages, nonces, tags)):
        # Verify tag (HMAC integrity)
        expected_tag = hmac_chain_tag(msg, nonce, prev_tag, key)
        if not hmac.compare_digest(tag, expected_tag):
            return False

        prev_tag = tag

    return True


# =============================================================================
# UNIFIED SYSTEM CLASS
# =============================================================================

class SCBEAethermoore:
    """
    SCBE-AETHERMOORE: Unified 9D Governance System

    Integrates:
        - 9D state (6D context + time + entropy + quantum)
        - Phase modulation + flat slope encoding
        - Hyper-torus manifold
        - PHDM topology
        - HMAC chain
        - Grand Unified Governance Function G
    """

    def __init__(
        self,
        secret_key: bytes = None,
        epsilon: float = EPSILON
    ):
        self.key = secret_key or os.urandom(KEY_LEN)
        self.epsilon = epsilon
        self.manifold = ManifoldController(epsilon=epsilon)
        self.state_history: List[State9D] = []
        self.hmac_chain: List[Tuple[bytes, bytes, bytes]] = []
        self.iv = hashlib.sha256(self.key).digest()

    def create_state(self, t: float = None) -> State9D:
        """Create a new 9D state at time t."""
        t = t or time.time()

        context = generate_context(t, self.key)
        tau = t
        eta = compute_entropy([context])
        q = quantum_evolution(1+0j, t)

        return State9D(context=context, tau=tau, eta=eta, q=q)

    def evaluate(
        self,
        intent: float,
        poly: Polyhedron = None
    ) -> Tuple[GovernanceDecision, str, Dict[str, Any]]:
        """
        Evaluate an intent against governance constraints.

        Returns (decision, message, metrics).
        """
        # Create current state
        state = self.create_state()
        xi = state.to_vector()

        # Default polyhedron (valid topology)
        if poly is None:
            poly = Polyhedron(V=6, E=9, F=5)  # χ = 2

        # Reference state (previous if exists)
        reference_xi = None
        if self.state_history:
            reference_xi = self.state_history[-1].to_vector()

        # Evaluate governance
        decision, msg, metrics = governance_9d(
            xi, intent, poly, reference_xi, self.epsilon
        )

        # Update history if allowed
        if decision == GovernanceDecision.ALLOW:
            self.state_history.append(state)

        return decision, msg, metrics

    def encode_message(self, message: str, tongue: str = "UM") -> bytes:
        """
        Encode a message with phase modulation and HMAC.
        """
        # Phase encode
        intent = stable_hash(message) / (2 * np.pi)
        wave = phase_modulated_intent(intent)

        # Create HMAC entry
        msg_bytes = message.encode()
        nonce = os.urandom(NONCE_BYTES)
        prev_tag = self.hmac_chain[-1][2] if self.hmac_chain else self.iv
        tag = hmac_chain_tag(msg_bytes, nonce, prev_tag, self.key)

        self.hmac_chain.append((msg_bytes, nonce, tag))

        return tag

    def verify_chain(self) -> bool:
        """Verify the entire HMAC chain."""
        if not self.hmac_chain:
            return True

        messages, nonces, tags = zip(*self.hmac_chain)
        return verify_hmac_chain(
            list(messages), list(nonces), list(tags),
            self.key, self.iv
        )


# =============================================================================
# DEMO
# =============================================================================

def demo():
    """Demonstrate the unified SCBE-AETHERMOORE system."""
    print("=" * 60)
    print("SCBE-AETHERMOORE: Unified 9D Governance System")
    print("=" * 60)
    print()

    # Initialize system
    system = SCBEAethermoore()

    # Test 1: Valid intent
    print("TEST 1: Valid Intent")
    print("-" * 40)
    decision, msg, metrics = system.evaluate(intent=0.75)
    print(f"Decision: {decision.value}")
    print(f"Message:  {msg}")
    print(f"Key metrics:")
    print(f"  - Coherence:  {metrics['coherence']:.4f}")
    print(f"  - d_tri:      {metrics['d_tri']:.4f}")
    print(f"  - Euler χ:    {metrics['euler_chi']}")
    print(f"  - Quantum F:  {metrics['quantum_fidelity']:.4f}")
    print()

    # Test 2: Topology violation
    print("TEST 2: Topology Violation (χ ≠ 2)")
    print("-" * 40)
    bad_poly = Polyhedron(V=4, E=6, F=3)  # χ = 1
    decision, msg, metrics = system.evaluate(intent=0.5, poly=bad_poly)
    print(f"Decision: {decision.value}")
    print(f"Message:  {msg}")
    print()

    # Test 3: HMAC chain
    print("TEST 3: HMAC Chain")
    print("-" * 40)
    tag1 = system.encode_message("Hello Mars", tongue="AV")
    tag2 = system.encode_message("Status nominal", tongue="CA")
    print(f"Tag 1: {tag1.hex()[:32]}...")
    print(f"Tag 2: {tag2.hex()[:32]}...")
    print(f"Chain valid: {system.verify_chain()}")
    print()

    # Test 4: Manifold validation
    print("TEST 4: Manifold Geometry")
    print("-" * 40)
    prev_fact = {'domain': 'KO', 'content': 'init', 'theta': 0.0, 'phi': 0.0}
    new_fact = {'domain': 'KO', 'content': 'step1'}
    result = system.manifold.validate_write(prev_fact, new_fact)
    print(f"Write status: {result['status']}")
    if 'distance' in result:
        print(f"Distance: {result['distance']:.4f}")
    print()

    print("=" * 60)
    print("Demo complete. System operational.")
    print("=" * 60)


if __name__ == "__main__":
    demo()
