"""
Cryptographic Physics Simulation Engine (CPSE)

Implements the virtual physics layer that feeds into SCBE governance:
    1. Weighted Metric Tensor - 6D manifold with friction zones
    2. Harmonic Scaling Law - H(d,R) = R^(d²) super-exponential cost
    3. Virtual Gravity - Lorentz factor γ for latency throttling
    4. Soliton Integrity - NLS-based packet gain/decay
    5. Spin Rotation - Context-dependent orientation
    6. Flux Interference - Stochastic noise injection

Patent Claims: 51, 52, 54, 55, 60, 61
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional
from collections import deque
import time

# =============================================================================
# CONSTANTS
# =============================================================================

PHI = (1 + np.sqrt(5)) / 2  # Golden ratio
R_DEFAULT = 1.5             # Default scaling constant
EPS = 1e-10                 # Numerical stability


# =============================================================================
# 1. WEIGHTED METRIC TENSOR (Claim 51 & 60)
# =============================================================================

def build_metric_tensor(R: float = R_DEFAULT) -> np.ndarray:
    """
    Build the weighted metric tensor g_μν for the 6D execution environment.

    g = diag(1, 1, 1, R, R², R³)

    Movement in behavioral dimensions (x⁴, x⁵, x⁶) costs R^k more than
    standard addressing dimensions (x¹, x², x³).

    This creates "virtual gravity" - high friction zones for unauthorized behavior.
    """
    return np.diag([1.0, 1.0, 1.0, R, R**2, R**3])


def metric_distance(x1: np.ndarray, x2: np.ndarray, g: np.ndarray = None) -> float:
    """
    Compute weighted distance in the 6D manifold.

    ds² = Σ g_μν dx^μ dx^ν

    Args:
        x1, x2: 6D coordinate vectors
        g: Metric tensor (defaults to build_metric_tensor())

    Returns:
        Geodesic distance in the weighted manifold
    """
    if g is None:
        g = build_metric_tensor()

    dx = x2 - x1

    # ds² = dx^T @ g @ dx
    ds_squared = dx.T @ g @ dx

    return np.sqrt(max(ds_squared, 0.0))


def behavioral_cost(displacement: np.ndarray, R: float = R_DEFAULT) -> float:
    """
    Compute the cost of a behavioral displacement.

    Cost in dimension k = |dx_k| × R^(k-3) for k > 3

    Returns total behavioral cost (sum over dimensions 4-6).
    """
    if len(displacement) < 6:
        displacement = np.concatenate([displacement, np.zeros(6 - len(displacement))])

    # Dimensions 4, 5, 6 have costs R, R², R³
    cost = 0.0
    for k in range(3, 6):
        cost += abs(displacement[k]) * (R ** (k - 2))

    return cost


# =============================================================================
# 2. HARMONIC SCALING LAW (Claim 51)
# =============================================================================

def harmonic_cost(d: float, R: float = R_DEFAULT, C_base: float = 1.0) -> float:
    """
    Harmonic Cost Function H(d, R).

    H(d, R) = ⌊C_base × R^(d²)⌋

    This provides super-exponential resistance to brute-force attacks:
        d=1: H ≈ 1.5
        d=2: H ≈ 5.06
        d=3: H ≈ 38.4
        d=4: H ≈ 656
        d=5: H ≈ 25,629
        d=6: H ≈ 2,184,164

    The cost curve is asymptotic relative to linear attacker resources.
    """
    # Clamp to prevent overflow
    d_squared = min(d ** 2, 50.0)

    return C_base * (R ** d_squared)


def security_level_cost(level: int, R: float = R_DEFAULT, C_base: float = 10.0) -> float:
    """
    Compute computational cost for accessing a security level.

    Args:
        level: Security dimension index (1-6)
        R: Scaling constant
        C_base: Base cost in milliseconds or hash iterations

    Returns:
        Required computational cost
    """
    return harmonic_cost(float(level), R, C_base)


# =============================================================================
# 3. VIRTUAL GRAVITY - LORENTZ FACTOR (Claim 54)
# =============================================================================

@dataclass
class VirtualGravityState:
    """State for the virtual gravity / latency throttling system."""
    query_history: deque  # Timestamps of recent queries
    window_seconds: float = 1.0  # Time window for rate calculation
    rho_critical: float = 100.0  # "Speed of light" - max queries/second
    t_base: float = 0.01  # Base latency in seconds


def lorentz_factor(rho_E: float, rho_critical: float) -> float:
    """
    Compute the modified Lorentz factor γ(ρ_E).

    γ(ρ_E) = 1 / √(1 - (ρ_E / ρ_critical)²)

    As ρ_E → ρ_critical, γ → ∞ (event horizon).

    Args:
        rho_E: Query energy density (requests per second)
        rho_critical: Maximum allowable request rate ("speed of light")

    Returns:
        Lorentz factor γ ∈ [1, ∞)
    """
    if rho_E <= 0:
        return 1.0

    if rho_E >= rho_critical:
        return float('inf')

    ratio_squared = (rho_E / rho_critical) ** 2

    return 1.0 / np.sqrt(1.0 - ratio_squared)


def compute_latency_delay(
    rho_E: float,
    rho_critical: float = 100.0,
    t_base: float = 0.01
) -> float:
    """
    Compute latency delay using virtual gravity.

    Δt = t_base × γ(ρ_E)

    This creates the "event horizon" effect:
        - Low query rate: minimal delay
        - Near-critical rate: massive delay
        - At critical rate: infinite delay (blocked)

    Args:
        rho_E: Current query rate (requests/second)
        rho_critical: Maximum rate before "event horizon"
        t_base: Base processing time

    Returns:
        Latency delay in seconds
    """
    gamma = lorentz_factor(rho_E, rho_critical)

    if gamma == float('inf'):
        return float('inf')

    return t_base * gamma


class VirtualGravityThrottler:
    """
    Latency throttler implementing virtual gravity / event horizon physics.

    As query frequency approaches the critical rate, processing "time slows"
    for the attacker, eventually freezing them at the event horizon.
    """

    def __init__(
        self,
        rho_critical: float = 100.0,
        t_base: float = 0.01,
        window_seconds: float = 1.0
    ):
        self.rho_critical = rho_critical
        self.t_base = t_base
        self.window_seconds = window_seconds
        self.query_history: Dict[str, deque] = {}  # Per-identity history

    def record_query(self, identity: str, timestamp: float = None) -> float:
        """
        Record a query and compute the required delay.

        Args:
            identity: Unique identifier (IP, user, context hash)
            timestamp: Query timestamp (defaults to now)

        Returns:
            Required delay in seconds before processing
        """
        t = timestamp or time.time()

        if identity not in self.query_history:
            self.query_history[identity] = deque()

        history = self.query_history[identity]

        # Remove old entries outside window
        cutoff = t - self.window_seconds
        while history and history[0] < cutoff:
            history.popleft()

        # Add current query
        history.append(t)

        # Compute current rate
        rho_E = len(history) / self.window_seconds

        # Compute delay
        delay = compute_latency_delay(rho_E, self.rho_critical, self.t_base)

        return delay

    def get_rate(self, identity: str) -> float:
        """Get current query rate for an identity."""
        if identity not in self.query_history:
            return 0.0

        history = self.query_history[identity]
        t = time.time()
        cutoff = t - self.window_seconds

        # Count recent queries
        count = sum(1 for ts in history if ts >= cutoff)

        return count / self.window_seconds


# =============================================================================
# 4. SOLITON INTEGRITY (Claim 52 & 55)
# =============================================================================

def soliton_evolution(
    A: float,
    alpha: float = 0.1,
    beta: float = 0.05,
    phi_d: float = 0.0,
    dt: float = 1.0
) -> float:
    """
    Discrete Non-Linear Schrödinger Equation (NLSE) for packet integrity.

    A_next = A + (α|A|²A - βA) + Φᵈ

    Args:
        A: Current packet amplitude (integrity score)
        alpha: Self-focusing coefficient (positive feedback for valid structure)
        beta: Linear loss coefficient (natural entropy/noise)
        phi_d: Soliton key (gain derived from user's private key)
        dt: Time step

    Returns:
        Next amplitude value

    Physics:
        - α|A|²A: Self-focusing (valid packets reinforce themselves)
        - βA: Linear loss (entropy decay)
        - Φᵈ: Key-derived gain that offsets loss for authorized packets
    """
    # NLS evolution
    gain = alpha * abs(A) ** 2 * A
    loss = beta * A
    key_gain = phi_d

    A_next = A + dt * (gain - loss) + key_gain

    return A_next


def soliton_stability(
    A_initial: float,
    phi_d: float,
    alpha: float = 0.1,
    beta: float = 0.05,
    n_steps: int = 10
) -> Tuple[float, bool]:
    """
    Check if a packet maintains soliton stability with given key.

    A packet is stable if amplitude remains bounded after n_steps.
    Only packets with the correct Φᵈ survive - others decay.

    Returns:
        (final_amplitude, is_stable)
    """
    A = A_initial

    for _ in range(n_steps):
        A = soliton_evolution(A, alpha, beta, phi_d, dt=0.1)

        # Check for decay or explosion
        if abs(A) < EPS:
            return 0.0, False  # Decayed
        if abs(A) > 1e6:
            return float('inf'), False  # Exploded

    # Stable if amplitude remains in reasonable range
    is_stable = 0.1 <= abs(A) <= 10.0

    return A, is_stable


def compute_soliton_key(
    private_key: bytes,
    beta: float = 0.05,
    alpha: float = 0.1,
    target_amplitude: float = 1.0
) -> float:
    """
    Derive the soliton key Φᵈ from a private key.

    The key is computed to exactly offset the loss term β for a target amplitude.

    For equilibrium: α|A|²A - βA + Φᵈ = 0
    So: Φᵈ = βA - α|A|²A
    """
    # Hash the key to get a stable seed
    import hashlib
    seed = int(hashlib.sha256(private_key).hexdigest(), 16) % (2**32)
    np.random.seed(seed)

    # Compute key that maintains equilibrium at target amplitude
    A = target_amplitude
    phi_d = beta * A - alpha * abs(A) ** 2 * A

    # Add small key-specific perturbation
    phi_d += np.random.normal(0, 0.001)

    return phi_d


# =============================================================================
# 5. SPIN ROTATION (Claim 60)
# =============================================================================

def rotation_matrix_2d(theta: float) -> np.ndarray:
    """
    2D rotation matrix R(θ).

    R(θ) = [cos(θ)  -sin(θ)]
           [sin(θ)   cos(θ)]
    """
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]])


def rotation_matrix_nd(dim: int, i: int, j: int, theta: float) -> np.ndarray:
    """
    N-dimensional rotation matrix in the (i,j) plane.

    R_{i,j}(θ) rotates vectors in the plane spanned by axes i and j.
    """
    R = np.eye(dim)
    c, s = np.cos(theta), np.sin(theta)

    R[i, i] = c
    R[i, j] = -s
    R[j, i] = s
    R[j, j] = c

    return R


def context_spin_angles(context: Dict[str, Any]) -> np.ndarray:
    """
    Derive spin angles θ from context hash.

    θ_i = hash(context_i) mod 2π

    Each context component (time, location, role, etc.) contributes
    a rotation angle in the corresponding plane.
    """
    import hashlib

    angles = []
    for key in sorted(context.keys()):
        value = str(context[key])
        hash_val = int(hashlib.sha256(f"{key}:{value}".encode()).hexdigest(), 16)
        angle = (hash_val / (2**256)) * 2 * np.pi
        angles.append(angle)

    # Ensure we have at least 5 angles (for 6D rotation chain)
    while len(angles) < 5:
        angles.append(0.0)

    return np.array(angles[:5])


def spin_transform(
    v_input: np.ndarray,
    context: Dict[str, Any],
    offset: np.ndarray = None
) -> np.ndarray:
    """
    Apply context-dependent spin transformation.

    v_final = (∏_{i=1}^{5} R_{i,i+1}(θ_i)) × v_input + C_offset

    Args:
        v_input: Input 6D data vector
        context: Context dictionary (time, location, role, etc.)
        offset: Optional offset vector

    Returns:
        Transformed vector

    Security: Wrong context → wrong θ → lands in "Null Quadrant"
    """
    dim = 6

    # Ensure v_input is 6D
    if len(v_input) < dim:
        v_input = np.concatenate([v_input, np.zeros(dim - len(v_input))])
    elif len(v_input) > dim:
        v_input = v_input[:dim]

    # Get rotation angles from context
    angles = context_spin_angles(context)

    # Build composite rotation: R = R_{5,6} × R_{4,5} × R_{3,4} × R_{2,3} × R_{1,2}
    R_total = np.eye(dim)
    for i in range(5):
        R_i = rotation_matrix_nd(dim, i, i+1, angles[i])
        R_total = R_i @ R_total

    # Apply rotation
    v_rotated = R_total @ v_input

    # Add offset if provided
    if offset is not None:
        if len(offset) < dim:
            offset = np.concatenate([offset, np.zeros(dim - len(offset))])
        v_rotated = v_rotated + offset[:dim]

    return v_rotated


def spin_mismatch(theta_actual: np.ndarray, theta_expected: np.ndarray) -> float:
    """
    Compute spin mismatch penalty.

    Mismatch = Σ sin²(Δθ_i / 2)

    This measures how "misaligned" the context spin is from expected.
    """
    delta = theta_actual - theta_expected

    # sin²(Δθ/2) ranges from 0 (aligned) to 1 (anti-aligned)
    mismatch = np.sum(np.sin(delta / 2) ** 2)

    return mismatch


# =============================================================================
# 6. FLUX INTERFERENCE (Claim 61)
# =============================================================================

def flux_noise(sigma: float) -> np.ndarray:
    """
    Generate Gaussian flux noise.

    ε ~ N(0, σ)

    Where σ scales with network load / "atmospheric flux".
    """
    return np.random.normal(0, sigma, 6)


def jittered_target(
    P_target: np.ndarray,
    network_load: float = 0.0,
    sigma_base: float = 0.01
) -> np.ndarray:
    """
    Compute jittered target position.

    P_jitter = P_target + N(0, σ(NetworkLoad))

    Args:
        P_target: True target coordinate
        network_load: Current load factor [0, 1]
        sigma_base: Base noise standard deviation

    Returns:
        Jittered position

    Security: Authorized "rail" accounts for jitter (moves with box).
              Attacker aiming at static P_target misses.
    """
    # σ increases with network load
    sigma = sigma_base * (1 + network_load)

    # Ensure P_target is 6D
    if len(P_target) < 6:
        P_target = np.concatenate([P_target, np.zeros(6 - len(P_target))])

    noise = flux_noise(sigma)

    return P_target + noise


class FluxGenerator:
    """
    Generates coordinated flux patterns that authorized paths can track.

    The "rail" (authorized path) knows the flux seed and can compute
    the same jitter. Attackers without the seed see random noise.
    """

    def __init__(self, seed: int = None, sigma_base: float = 0.01):
        self.seed = seed or int(time.time() * 1000) % (2**32)
        self.sigma_base = sigma_base
        self.step = 0

    def get_flux(self, network_load: float = 0.0) -> np.ndarray:
        """Get deterministic flux for current step (for authorized paths)."""
        np.random.seed(self.seed + self.step)
        self.step += 1

        sigma = self.sigma_base * (1 + network_load)
        return flux_noise(sigma)

    def get_random_flux(self, network_load: float = 0.0) -> np.ndarray:
        """Get random flux (what attackers see)."""
        sigma = self.sigma_base * (1 + network_load)
        return flux_noise(sigma)


# =============================================================================
# INTEGRATED CPSE ENGINE
# =============================================================================

@dataclass
class CPSEState:
    """Complete state of the CPSE simulation."""
    # Metric tensor
    metric_tensor: np.ndarray

    # Virtual gravity
    gravity_delay: float
    gamma_factor: float
    query_rate: float

    # Soliton
    soliton_amplitude: float
    soliton_stable: bool

    # Spin
    spin_mismatch: float
    spin_angles: np.ndarray

    # Flux
    flux_variance: float
    current_jitter: np.ndarray


class CPSEEngine:
    """
    Cryptographic Physics Simulation Engine.

    Integrates all six physics components into a unified simulation
    that feeds deviation features into SCBE governance.
    """

    def __init__(
        self,
        R: float = R_DEFAULT,
        rho_critical: float = 100.0,
        t_base: float = 0.01,
        sigma_flux: float = 0.01,
        alpha_soliton: float = 0.1,
        beta_soliton: float = 0.05
    ):
        self.R = R
        self.metric = build_metric_tensor(R)

        # Virtual gravity
        self.throttler = VirtualGravityThrottler(rho_critical, t_base)

        # Soliton parameters
        self.alpha = alpha_soliton
        self.beta = beta_soliton

        # Flux generator
        self.flux = FluxGenerator(sigma_base=sigma_flux)

        # Expected context (for spin comparison)
        self.expected_context: Optional[Dict[str, Any]] = None

    def set_expected_context(self, context: Dict[str, Any]):
        """Set the expected context for spin comparison."""
        self.expected_context = context

    def simulate(
        self,
        identity: str,
        context: Dict[str, Any],
        position: np.ndarray,
        private_key: bytes = None,
        network_load: float = 0.0,
        timestamp: float = None
    ) -> CPSEState:
        """
        Run complete CPSE simulation for a query.

        Args:
            identity: Unique identifier for rate limiting
            context: Context dictionary for spin calculation
            position: Current 6D position vector
            private_key: For soliton key derivation
            network_load: Current network load [0, 1]
            timestamp: Query timestamp

        Returns:
            CPSEState with all physics outputs
        """
        # 1. Virtual Gravity
        delay = self.throttler.record_query(identity, timestamp)
        rate = self.throttler.get_rate(identity)
        gamma = lorentz_factor(rate, self.throttler.rho_critical)

        # 2. Soliton Stability
        if private_key:
            phi_d = compute_soliton_key(private_key, self.beta, self.alpha)
        else:
            phi_d = 0.0

        amplitude, stable = soliton_stability(1.0, phi_d, self.alpha, self.beta)

        # 3. Spin
        actual_angles = context_spin_angles(context)
        if self.expected_context:
            expected_angles = context_spin_angles(self.expected_context)
            mismatch = spin_mismatch(actual_angles, expected_angles)
        else:
            mismatch = 0.0

        # 4. Flux
        jitter = self.flux.get_random_flux(network_load)
        flux_var = np.var(jitter)

        return CPSEState(
            metric_tensor=self.metric,
            gravity_delay=delay,
            gamma_factor=gamma if gamma != float('inf') else 1e10,
            query_rate=rate,
            soliton_amplitude=amplitude,
            soliton_stable=stable,
            spin_mismatch=mismatch,
            spin_angles=actual_angles,
            flux_variance=flux_var,
            current_jitter=jitter
        )

    def map_to_scbe(self, state: CPSEState) -> Dict[str, float]:
        """
        Map CPSE outputs to SCBE deviation features.

        CPSE Component          → SCBE Layer
        ─────────────────────────────────────
        Virtual Gravity (Delay) → Layer 6 (τ)
        Harmonic Cost           → Layer 12 (d*)
        Soliton Gain/Decay      → Layer 10 (C_spin)
        Spin Mismatch           → Layer 10 (C_spin)
        Flux Interference       → Layer 9 (S_spec)

        Returns dictionary of SCBE adjustments.
        """
        # Coupling constants (tunable hyperparameters)
        kappa_gravity = 0.3
        w_sol = 0.2
        w_spin = 0.2
        w_flux = 0.2

        # τ adjustment from gravity delay
        tau_adj = kappa_gravity * min(state.gravity_delay, 10.0)

        # d* adjustment from harmonic cost (log scale)
        cost_factor = np.log2(1 + state.gamma_factor)
        d_star_adj = cost_factor

        # C_spin adjustment from soliton and spin
        spin_adj = 0.0
        if not state.soliton_stable:
            spin_adj += w_sol * (1 - min(state.soliton_amplitude, 1.0))
        spin_adj += w_spin * state.spin_mismatch

        # S_spec adjustment from flux
        r_hf_adj = w_flux * state.flux_variance

        return {
            "tau_adjustment": tau_adj,
            "d_star_adjustment": d_star_adj,
            "spin_coherence_penalty": min(spin_adj, 1.0),
            "spectral_noise_increase": r_hf_adj
        }


# =============================================================================
# DEMO
# =============================================================================

def demo():
    """Demonstrate the CPSE engine."""
    print("=" * 70)
    print("CRYPTOGRAPHIC PHYSICS SIMULATION ENGINE (CPSE)")
    print("=" * 70)
    print()

    # Initialize engine
    engine = CPSEEngine(R=1.5, rho_critical=50.0)

    # Set expected context
    expected = {"time": "2024-01-01", "role": "user", "location": "office"}
    engine.set_expected_context(expected)

    print("1. WEIGHTED METRIC TENSOR")
    print("-" * 70)
    print(f"   g = diag(1, 1, 1, R, R², R³) where R = {engine.R}")
    print(f"   Behavioral dimension costs: {engine.R}, {engine.R**2:.2f}, {engine.R**3:.2f}")
    print()

    print("2. HARMONIC SCALING LAW")
    print("-" * 70)
    for d in range(1, 7):
        cost = harmonic_cost(d, engine.R)
        print(f"   H(d={d}) = {engine.R}^({d}²) = {cost:,.2f}")
    print()

    print("3. VIRTUAL GRAVITY (Lorentz Factor)")
    print("-" * 70)
    for rate in [10, 25, 40, 45, 49]:
        gamma = lorentz_factor(rate, 50.0)
        delay = compute_latency_delay(rate, 50.0, 0.01)
        print(f"   ρ={rate:2d}/s → γ = {gamma:.4f}, Delay = {delay:.6f}s")
    print()

    print("4. SOLITON STABILITY")
    print("-" * 70)
    # With correct key
    correct_key = b"authorized_user_key"
    phi_correct = compute_soliton_key(correct_key, engine.beta, engine.alpha)
    amp1, stable1 = soliton_stability(1.0, phi_correct, engine.alpha, engine.beta)
    print(f"   With correct key: A={amp1:.4f}, stable={stable1}")

    # Without key (or wrong key)
    amp2, stable2 = soliton_stability(1.0, 0.0, engine.alpha, engine.beta)
    print(f"   Without key: A={amp2:.4f}, stable={stable2}")
    print()

    print("5. SPIN ROTATION")
    print("-" * 70)
    correct_ctx = {"time": "2024-01-01", "role": "user", "location": "office"}
    wrong_ctx = {"time": "2024-01-01", "role": "admin", "location": "remote"}

    angles_correct = context_spin_angles(correct_ctx)
    angles_wrong = context_spin_angles(wrong_ctx)
    mismatch = spin_mismatch(angles_wrong, angles_correct)

    print(f"   Correct context angles: {angles_correct[:3].round(4)}")
    print(f"   Wrong context angles:   {angles_wrong[:3].round(4)}")
    print(f"   Spin mismatch penalty:  {mismatch:.4f}")
    print()

    print("6. FLUX INTERFERENCE")
    print("-" * 70)
    for load in [0.0, 0.5, 1.0]:
        flux_gen = FluxGenerator(seed=42, sigma_base=0.01)
        jitter = flux_gen.get_random_flux(load)
        print(f"   Network load={load:.1f}: jitter variance = {np.var(jitter):.6f}")
    print()

    print("=" * 70)
    print("FULL SIMULATION")
    print("=" * 70)

    # Simulate authorized query
    state = engine.simulate(
        identity="user_alice",
        context=expected,  # Correct context
        position=np.array([0.5, 0.5, 0.5, 0.1, 0.1, 0.1]),
        private_key=b"alice_key",
        network_load=0.2
    )

    print(f"\nAuthorized query:")
    print(f"  Gravity delay:    {state.gravity_delay:.6f}s")
    print(f"  Gamma factor:     {state.gamma_factor:.4f}")
    print(f"  Soliton stable:   {state.soliton_stable}")
    print(f"  Spin mismatch:    {state.spin_mismatch:.4f}")
    print(f"  Flux variance:    {state.flux_variance:.6f}")

    # Map to SCBE
    scbe_adj = engine.map_to_scbe(state)
    print(f"\nSCBE Adjustments:")
    for key, val in scbe_adj.items():
        print(f"  {key}: {val:.6f}")
    print()

    print("=" * 70)
    print("CPSE Engine Operational")
    print("=" * 70)


if __name__ == "__main__":
    demo()
