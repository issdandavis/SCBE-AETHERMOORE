"""
Adaptive Hyperbolic Navigator - Dynamic Geometry for Intent Validation

@layer Layer 5, Layer 6, Layer 7, Layer 9, Layer 13
@version 1.0.0
@since 2026-02-06

SCBE Adaptive Hyperbolic Navigator - Dynamic geometry that evolves with intent validation.

Key Innovation: The Poincaré ball becomes a "living manifold" where:
- Harmonic scaling R(t) varies with coherence: R(t) = R_base + λ(1 - C)
- Curvature κ(t) can adapt: κ(t) = -1 * exp(γ(1 - C))
- ODE-based drift with attraction/repulsion modulated by trust

Mathematical Foundation:
- Generalized Poincaré metric with variable curvature
- Distance formula: d_κ(u,v) = (1/√|κ|) arccosh(1 + (2|κ|‖u-v‖²)/((1-|κ|‖u‖²)(1-|κ|‖v‖²)))
- Harmonic wall: H(d,R) = R^(d²) where R adapts to coherence

Integration:
- Layer 9/10: Spectral coherence feeds into C ∈ [0,1]
- Layer 13: Intent validation modulates drift velocity
- HYDRA: Swarm consensus can trigger geometry evolution

Research Validation:
- Grok Analysis (2026-02-05): Variable curvature preserves containment theorems
- Proof sketch: Generalized Poincaré metric supports κ ≠ -1 with scaled radius
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math
import numpy as np
from scipy.integrate import odeint

# Constants
EPSILON = 1e-10
PHI = (1 + math.sqrt(5)) / 2  # Golden ratio

# Sacred Tongue realm centers (6D)
REALM_CENTERS: Dict[str, np.ndarray] = {
    'KO': np.array([0.3, 0.0, 0.0, 0.0, 0.0, 0.0]),  # Knowledge
    'AV': np.array([0.0, 0.3, 0.0, 0.0, 0.0, 0.0]),  # Avatara
    'RU': np.array([0.0, 0.0, 0.3, 0.0, 0.0, 0.0]),  # Runes
    'CA': np.array([0.0, 0.0, 0.0, 0.3, 0.0, 0.0]),  # Cascade
    'UM': np.array([0.0, 0.0, 0.0, 0.0, 0.3, 0.0]),  # Umbra
    'DR': np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.3]),  # Draconic
}

# Tongue weights (golden ratio based)
TONGUE_WEIGHTS: Dict[str, float] = {
    'KO': 1.0,
    'AV': 1 / PHI,
    'RU': 1 / (PHI ** 2),
    'CA': 1 / (PHI ** 3),
    'UM': 1 / (PHI ** 4),
    'DR': 1 / (PHI ** 5),
}


@dataclass
class AdaptiveNavigatorConfig:
    """Configuration for the Adaptive Hyperbolic Navigator."""
    base_R: float = 1.5           # Base harmonic scaling factor
    lambda_penalty: float = 1.0   # Penalty multiplier for low coherence
    chaos: float = 0.1            # Chaos amplitude for Lorenz perturbations
    gamma: float = 0.5            # Curvature adaptation rate
    dimension: int = 6            # Dimension of Poincaré ball
    max_history: int = 1000       # Maximum trajectory history length
    boundary_threshold: float = 0.98  # Ball boundary threshold


@dataclass
class NavigatorState:
    """State of the navigator after an update."""
    position: np.ndarray
    velocity: np.ndarray
    coherence: float
    current_R: float
    current_kappa: float
    penalty: float
    timestamp: float


class AdaptiveHyperbolicNavigator:
    """
    Adaptive Hyperbolic Navigator with dynamic geometry.

    A "living manifold" navigator where the Poincaré ball geometry
    evolves based on intent validation coherence.

    Example:
        nav = AdaptiveHyperbolicNavigator()

        # Update with intent and coherence from Layer 9/13
        result = nav.update(['KO', 'AV'], coherence=0.85)

        # Check adaptive penalty
        if result.penalty > 10:
            print('High deviation detected')
    """

    def __init__(
        self,
        config: Optional[AdaptiveNavigatorConfig] = None,
        initial_position: Optional[np.ndarray] = None
    ):
        self.config = config or AdaptiveNavigatorConfig()
        self.position = (
            np.array(initial_position) if initial_position is not None
            else np.zeros(self.config.dimension)
        )
        self.velocity = np.zeros(self.config.dimension)
        self.history: List[np.ndarray] = [self.position.copy()]
        self.coherence_history: List[float] = [1.0]

    # ═══════════════════════════════════════════════════════════════
    # Adaptive Geometry Parameters
    # ═══════════════════════════════════════════════════════════════

    def get_current_R(self, coherence: float) -> float:
        """
        Compute adaptive harmonic scaling R(t) based on coherence.

        R(t) = R_base + λ(1 - C)

        Low coherence → higher R → harsher exponential penalties

        Args:
            coherence: Intent validation coherence [0, 1]

        Returns:
            Adaptive R value
        """
        c = max(0, min(1, coherence))
        return self.config.base_R + self.config.lambda_penalty * (1 - c)

    def get_current_kappa(self, coherence: float) -> float:
        """
        Compute adaptive curvature κ(t) based on coherence.

        κ(t) = -1 * exp(γ(1 - C))

        Low coherence → more negative curvature → distances explode faster

        Args:
            coherence: Intent validation coherence [0, 1]

        Returns:
            Adaptive curvature value (negative)
        """
        c = max(0, min(1, coherence))
        return -1 * math.exp(self.config.gamma * (1 - c))

    # ═══════════════════════════════════════════════════════════════
    # Hyperbolic Distance with Variable Curvature
    # ═══════════════════════════════════════════════════════════════

    def hyperbolic_distance_kappa(
        self,
        u: np.ndarray,
        v: np.ndarray,
        kappa: float
    ) -> float:
        """
        Hyperbolic distance with variable curvature.

        d_κ(u,v) = (1/√|κ|) arccosh(1 + (2|κ|‖u-v‖²)/((1-|κ|‖u‖²)(1-|κ|‖v‖²)))

        Args:
            u: First point
            v: Second point
            kappa: Curvature (negative for hyperbolic)

        Returns:
            Hyperbolic distance
        """
        abs_kappa = abs(kappa)
        sqrt_kappa = math.sqrt(abs_kappa)

        diff = u - v
        diff_norm_sq = np.dot(diff, diff)
        u_norm_sq = np.dot(u, u)
        v_norm_sq = np.dot(v, v)

        u_factor = max(EPSILON, 1 - abs_kappa * u_norm_sq)
        v_factor = max(EPSILON, 1 - abs_kappa * v_norm_sq)

        arg = 1 + (2 * abs_kappa * diff_norm_sq) / (u_factor * v_factor)

        return math.acosh(max(1, arg)) / sqrt_kappa

    def hyperbolic_distance(self, u: np.ndarray, v: np.ndarray) -> float:
        """Standard hyperbolic distance (κ = -1)."""
        return self.hyperbolic_distance_kappa(u, v, -1)

    # ═══════════════════════════════════════════════════════════════
    # ODE Drift Dynamics
    # ═══════════════════════════════════════════════════════════════

    def _compute_drift(
        self,
        pos: np.ndarray,
        targets: List[str],
        coherence: float,
        mutations: float
    ) -> np.ndarray:
        """
        Compute drift vector for ODE integration.

        Combines:
        - Attraction to target realm centers (scaled by coherence and R)
        - Repulsion/mutations (amplified by low coherence)
        - Chaos term (Lorenz-like, modulated by coherence)
        """
        R = self.get_current_R(coherence)
        dim = self.config.dimension

        # Attraction to target realms
        attraction = np.zeros(dim)
        for tongue in targets:
            center = REALM_CENTERS.get(tongue)
            if center is not None:
                weight = TONGUE_WEIGHTS.get(tongue, 1.0)
                delta = center - pos
                # Stronger pull when trusted (high coherence)
                attraction += delta * coherence * weight * R

        # Repulsion/mutations (amplified by low coherence)
        repulsion = np.zeros(dim)
        if mutations > 0:
            repulsion = np.random.randn(dim) * mutations * (1 - coherence)

        # Chaos term (Lorenz-like attractor simplified to 6D)
        chaos = np.zeros(dim)
        if self.config.chaos > 0:
            sigma = 10
            rho = 28
            beta = 8 / 3
            chaos_scale = self.config.chaos * (1 - coherence)

            if dim >= 6:
                chaos[0] = chaos_scale * sigma * (pos[1] - pos[0])
                chaos[1] = chaos_scale * (pos[0] * (rho - pos[2]) - pos[1])
                chaos[2] = chaos_scale * (pos[0] * pos[1] - beta * pos[2])
                chaos[3] = chaos_scale * sigma * (pos[4] - pos[3])
                chaos[4] = chaos_scale * (pos[3] * (rho - pos[5]) - pos[4])
                chaos[5] = chaos_scale * (pos[3] * pos[4] - beta * pos[5])

        return attraction + repulsion + chaos

    def _drift_ode(
        self,
        pos: np.ndarray,
        t: float,
        targets: List[str],
        coherence: float,
        mutations: float
    ) -> np.ndarray:
        """ODE system for scipy.integrate.odeint."""
        return self._compute_drift(pos, targets, coherence, mutations)

    # ═══════════════════════════════════════════════════════════════
    # Main Update Method
    # ═══════════════════════════════════════════════════════════════

    def update(
        self,
        intent_tongues: List[str],
        coherence: float = 1.0,
        mutations: float = 0,
        dt: float = 0.1
    ) -> NavigatorState:
        """
        Update navigator position with intent and coherence.

        This is the main integration point:
        - Layer 9/10: coherence = spectral coherence C ∈ [0,1]
        - Layer 13: coherence = 1 - risk' from intent validation
        - mutations: from EvolvingLexicon mutation rate

        Args:
            intent_tongues: Target Sacred Tongue realms
            coherence: Intent validation coherence [0, 1]
            mutations: Mutation rate (default 0)
            dt: Time step (default 0.1)

        Returns:
            NavigatorState after update
        """
        c = max(0, min(1, coherence))

        # Integrate ODE
        t = np.linspace(0, dt, 10)
        trajectory = odeint(
            self._drift_ode,
            self.position,
            t,
            args=(intent_tongues, c, mutations)
        )
        pos = trajectory[-1]

        # Soft projection back to ball
        norm = np.linalg.norm(pos)
        if norm > self.config.boundary_threshold:
            pos = pos * (self.config.boundary_threshold / norm)

        # Update velocity (for momentum tracking)
        self.velocity = pos - self.position
        self.position = pos

        # Record history
        self.history.append(pos.copy())
        self.coherence_history.append(c)

        # Trim history if too long
        if len(self.history) > self.config.max_history:
            self.history.pop(0)
            self.coherence_history.pop(0)

        # Compute adaptive parameters
        current_R = self.get_current_R(c)
        current_kappa = self.get_current_kappa(c)

        # Compute distance to origin
        d_center = self.hyperbolic_distance_kappa(
            pos, np.zeros(self.config.dimension), current_kappa
        )

        # Harmonic penalty: H(d, R) = R^(d²)
        penalty = current_R ** (d_center ** 2)

        return NavigatorState(
            position=pos,
            velocity=self.velocity,
            coherence=c,
            current_R=current_R,
            current_kappa=current_kappa,
            penalty=penalty,
            timestamp=float(np.datetime64('now', 'ms').astype(int))
        )

    # ═══════════════════════════════════════════════════════════════
    # Analysis Methods
    # ═══════════════════════════════════════════════════════════════

    def distance_to_realm(
        self,
        tongue: str,
        coherence: Optional[float] = None
    ) -> float:
        """Get distance to a specific realm center."""
        center = REALM_CENTERS.get(tongue)
        if center is None:
            return float('inf')

        kappa = self.get_current_kappa(coherence) if coherence else -1
        return self.hyperbolic_distance_kappa(self.position, center, kappa)

    def closest_realm(
        self,
        coherence: Optional[float] = None
    ) -> Tuple[str, float]:
        """Get the closest realm to current position."""
        min_dist = float('inf')
        closest = 'KO'

        kappa = self.get_current_kappa(coherence) if coherence else -1

        for tongue, center in REALM_CENTERS.items():
            dist = self.hyperbolic_distance_kappa(self.position, center, kappa)
            if dist < min_dist:
                min_dist = dist
                closest = tongue

        return closest, min_dist

    def trajectory_entropy(self) -> float:
        """Compute trajectory entropy (measure of chaotic behavior)."""
        if len(self.history) < 10:
            return 0.0

        # Compute displacement histogram
        displacements = []
        for i in range(1, len(self.history)):
            d = np.linalg.norm(self.history[i] - self.history[i - 1])
            displacements.append(d)

        # Bin displacements
        bins = 20
        max_d = max(displacements) + EPSILON
        counts = [0] * bins

        for d in displacements:
            bin_idx = min(bins - 1, int((d / max_d) * bins))
            counts[bin_idx] += 1

        # Compute entropy
        entropy = 0.0
        total = len(displacements)
        for count in counts:
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)

        return entropy / math.log2(bins)  # Normalize to [0, 1]

    def coherence_stability(self, window: int = 50) -> float:
        """Compute coherence stability (variance over recent history)."""
        recent = self.coherence_history[-window:]
        if len(recent) < 2:
            return 1.0

        mean = sum(recent) / len(recent)
        variance = sum((c - mean) ** 2 for c in recent) / len(recent)

        return max(0, 1 - math.sqrt(variance))

    def detect_anomaly(
        self,
        thresholds: Optional[Dict[str, float]] = None
    ) -> Dict:
        """Detect potential attack pattern."""
        thresholds = thresholds or {
            'coherence': 0.3,
            'entropy': 0.7,
            'stability': 0.4
        }

        indicators = []
        score = 0.0

        recent = self.coherence_history[-20:]
        avg_coherence = sum(recent) / len(recent) if recent else 1.0

        if avg_coherence < thresholds['coherence']:
            indicators.append('low_coherence')
            score += 0.4

        entropy = self.trajectory_entropy()
        if entropy > thresholds['entropy']:
            indicators.append('high_entropy')
            score += 0.3

        stability = self.coherence_stability()
        if stability < thresholds['stability']:
            indicators.append('unstable_coherence')
            score += 0.3

        return {
            'is_anomaly': score >= 0.7,
            'score': score,
            'indicators': indicators
        }

    # ═══════════════════════════════════════════════════════════════
    # State Access
    # ═══════════════════════════════════════════════════════════════

    def get_position(self) -> np.ndarray:
        return self.position.copy()

    def get_velocity(self) -> np.ndarray:
        return self.velocity.copy()

    def get_history(self) -> List[np.ndarray]:
        return [p.copy() for p in self.history]

    def get_coherence_history(self) -> List[float]:
        return self.coherence_history.copy()

    def reset(self, initial_position: Optional[np.ndarray] = None):
        """Reset navigator to initial state."""
        self.position = (
            np.array(initial_position) if initial_position is not None
            else np.zeros(self.config.dimension)
        )
        self.velocity = np.zeros(self.config.dimension)
        self.history = [self.position.copy()]
        self.coherence_history = [1.0]


# ═══════════════════════════════════════════════════════════════
# Factory and Integration Functions
# ═══════════════════════════════════════════════════════════════

def create_adaptive_navigator(
    config: Optional[AdaptiveNavigatorConfig] = None,
    initial_position: Optional[np.ndarray] = None
) -> AdaptiveHyperbolicNavigator:
    """Create an adaptive navigator with sensible defaults."""
    return AdaptiveHyperbolicNavigator(config, initial_position)


def compute_coherence(
    spectral_coherence: float,
    spin_coherence: float = 1.0
) -> float:
    """
    Compute coherence from Layer 9/10 spectral analysis.

    Args:
        spectral_coherence: Raw coherence from spectral analysis
        spin_coherence: Spin coherence from consensus

    Returns:
        Combined coherence score (geometric mean)
    """
    return math.sqrt(spectral_coherence * spin_coherence)


def risk_to_coherence(risk_score: float) -> float:
    """
    Compute coherence from Layer 13 risk score.

    Args:
        risk_score: Risk' from intent validation [0, 1]

    Returns:
        Coherence as complement of risk
    """
    return 1 - max(0, min(1, risk_score))


# ═══════════════════════════════════════════════════════════════
# Swarm Integration for HYDRA
# ═══════════════════════════════════════════════════════════════

class SwarmNavigator:
    """
    Multi-agent swarm navigator for HYDRA integration.

    Manages multiple AdaptiveHyperbolicNavigator instances
    with collective coherence computation.
    """

    def __init__(self, num_agents: int = 5):
        self.agents: List[AdaptiveHyperbolicNavigator] = [
            AdaptiveHyperbolicNavigator() for _ in range(num_agents)
        ]
        self.collective_coherence: float = 1.0

    def update_all(
        self,
        intent_tongues: List[str],
        individual_coherences: Optional[List[float]] = None,
        mutations: float = 0,
        dt: float = 0.1
    ) -> List[NavigatorState]:
        """Update all agents in the swarm."""
        if individual_coherences is None:
            individual_coherences = [self.collective_coherence] * len(self.agents)

        results = []
        for agent, coherence in zip(self.agents, individual_coherences):
            result = agent.update(intent_tongues, coherence, mutations, dt)
            results.append(result)

        # Update collective coherence as mean of individual
        self.collective_coherence = sum(r.coherence for r in results) / len(results)

        return results

    def detect_byzantine(self, threshold: float = 2.0) -> List[int]:
        """
        Detect potential Byzantine agents (outliers in position space).

        Returns indices of suspicious agents.
        """
        positions = [agent.position for agent in self.agents]
        centroid = np.mean(positions, axis=0)

        distances = [np.linalg.norm(p - centroid) for p in positions]
        mean_dist = np.mean(distances)
        std_dist = np.std(distances) + EPSILON

        byzantine = []
        for i, d in enumerate(distances):
            if (d - mean_dist) / std_dist > threshold:
                byzantine.append(i)

        return byzantine

    def get_consensus_position(self) -> np.ndarray:
        """Get consensus position (centroid of all agents)."""
        return np.mean([agent.position for agent in self.agents], axis=0)
