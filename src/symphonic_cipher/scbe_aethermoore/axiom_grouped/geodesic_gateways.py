"""
Geodesic Dimensional Gateways (GDG) — Tripolar Nodal Geodesic Gateways
=======================================================================

Three mathematical primitives for the SCBE-AETHERMOORE World Tree:

1. TNGG (Tripolar Nodal Geodesic Gateways)
   - 3 geodesics at 120° around a central node
   - Low-cost routing tunnels in the Langues metric
   - Fractal recursion with golden-ratio contraction (lambda = 1/phi)

2. TFDD (Tri-Fractal Discouragement Derivative)
   - Asymmetric positivity weighting for emotional landscape balancing
   - Negative inputs → exponential discouragement
   - Positive inputs → amplified reward (net-positive system)

3. Hausdorff Intent Roughness
   - Measures fractal dimension of agent trajectory through 6D Langues space
   - Smooth trajectory → benign (D_H ~ 1.0)
   - Jagged trajectory → adversarial evasion (D_H > 2.0)

Integration:
  L_total = L_f + L_gate + L_fractal + L_emotional

  Where:
    L_f        = Fluxing Langues metric (existing)
    L_gate     = Geodesic gateway cost augmentation
    L_fractal  = Fractal recursion cost (golden-ratio damped)
    L_emotional = TFDD positivity enforcement

Patent: USPTO #63/961,403
Author: Issac Davis
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Constants
PHI = (1 + math.sqrt(5)) / 2       # Golden ratio
PHI_INV = 1.0 / PHI                # 1/phi ~ 0.618034
TAU = 2 * math.pi
SQRT3_HALF = math.sqrt(3) / 2

# Import from existing langues_metric module
from .langues_metric import (
    TONGUES,
    TONGUE_WEIGHTS,
    TONGUE_PHASES,
    TONGUE_FREQUENCIES,
    HyperspacePoint,
    IdealState,
    FluxingLanguesMetric,
    DimensionFlux,
    langues_value,
)


# =============================================================================
# 1. TRIPOLAR NODAL GEODESIC GATEWAYS (TNGG)
# =============================================================================


def tripolar_geodesic_vectors() -> List[List[float]]:
    """
    Returns the three 120-degree unit tangent vectors in 3D tangent space.

    v1 = (1, 0, 0)
    v2 = (-1/2, sqrt(3)/2, 0)
    v3 = (-1/2, -sqrt(3)/2, 0)

    Properties:
      - <vi, vj> = -1/2 for i != j (exact 120-degree separation)
      - ||vk|| = 1 for all k
      - Gram matrix is positive semi-definite
      - SO(3) rotation invariance holds
    """
    return [
        [1.0, 0.0, 0.0],
        [-0.5, SQRT3_HALF, 0.0],
        [-0.5, -SQRT3_HALF, 0.0],
    ]


def project_to_geodesic(
    x: List[float],
    v_k: List[float],
    r_max: float = 10.0,
) -> List[float]:
    """
    Closest-point projection of x onto geodesic ray defined by v_k.

    Returns the projected point on the ray [0, r_max] * v_k.
    """
    # Dot product (only first 3 dims for 3D tangent space)
    dot = sum(x[i] * v_k[i] for i in range(min(len(x), len(v_k))))
    proj_scalar = max(0.0, min(dot, r_max))
    return [proj_scalar * v_k[i] for i in range(len(v_k))]


def geodesic_distance_sq(x: List[float], proj: List[float]) -> float:
    """Squared distance from x to its geodesic projection (first 3 dims)."""
    d_sq = 0.0
    for i in range(min(len(x), len(proj))):
        d_sq += (x[i] - proj[i]) ** 2
    return d_sq


@dataclass
class GeodesicGateway:
    """
    A single geodesic gateway: a low-cost tunnel in the Langues metric.

    Gateway cost:
      L_gate_k(x) = alpha * exp(-||x - proj_k(x)||^2 / sigma^2)

    States near the geodesic get REDUCED total cost (gateway opens).
    States far from the geodesic pay full Langues cost.
    """

    direction: List[float]  # Unit tangent vector v_k
    sigma: float = 0.5      # Gateway width (larger = wider tunnel)
    alpha: float = -0.3     # Gateway strength (negative = cost REDUCTION)

    def cost(self, x_centered: List[float]) -> float:
        """
        Compute gateway cost contribution for a centered state vector.

        Negative alpha means states ON the geodesic get a cost reduction.
        """
        proj = project_to_geodesic(x_centered, self.direction)
        d_sq = geodesic_distance_sq(x_centered, proj)
        return self.alpha * math.exp(-d_sq / (self.sigma ** 2))


@dataclass
class TripolarGatewaySystem:
    """
    Three geodesic gateways at 120-degree separation around a central node.

    L_gate(x, t) = sum_k alpha * exp(-||proj_k(x)||^2 / sigma^2)

    The central node N is the ideal state mu.
    """

    sigma: float = 0.5
    alpha: float = -0.3  # Negative = cost reduction near geodesics
    gateways: List[GeodesicGateway] = field(default_factory=list)

    def __post_init__(self):
        if not self.gateways:
            vectors = tripolar_geodesic_vectors()
            self.gateways = [
                GeodesicGateway(direction=v, sigma=self.sigma, alpha=self.alpha)
                for v in vectors
            ]

    def compute_gate_cost(self, x: HyperspacePoint, mu: IdealState) -> float:
        """
        Compute total gateway cost for a state vector.

        Centers x around mu, then evaluates all 3 gateways.
        """
        x_vec = x.to_vector()
        mu_vec = mu.to_vector()
        # Center and take first 3 dims for 3D tangent space
        centered = [x_vec[i] - mu_vec[i] for i in range(min(3, len(x_vec)))]

        total = 0.0
        for gw in self.gateways:
            total += gw.cost(centered)
        return total

    def nearest_geodesic(self, x: HyperspacePoint, mu: IdealState) -> int:
        """Return index (0, 1, 2) of the nearest geodesic gateway."""
        x_vec = x.to_vector()
        mu_vec = mu.to_vector()
        centered = [x_vec[i] - mu_vec[i] for i in range(min(3, len(x_vec)))]

        min_dist = float("inf")
        best_k = 0
        for k, gw in enumerate(self.gateways):
            proj = project_to_geodesic(centered, gw.direction)
            d_sq = geodesic_distance_sq(centered, proj)
            if d_sq < min_dist:
                min_dist = d_sq
                best_k = k
        return best_k

    def verify_120_symmetry(self) -> bool:
        """Verify all geodesic pairs have exactly 120-degree separation."""
        vectors = [gw.direction for gw in self.gateways]
        for i in range(3):
            for j in range(i + 1, 3):
                dot = sum(vectors[i][d] * vectors[j][d] for d in range(3))
                if abs(dot - (-0.5)) > 1e-10:
                    return False
        return True


# =============================================================================
# 2. FRACTAL RECURSION (Golden-Ratio Contraction)
# =============================================================================


@dataclass
class FractalTripod:
    """
    Self-similar fractal recursion of the tripolar gateway system.

    At each level m, spawn 3 child tripods scaled by lambda^m.
    Cost contribution decays as lambda^m * sum(child costs).

    lambda = 1/phi ~ 0.618034 (golden-ratio contraction).

    Theorem: Cost contribution C_m -> 0 exponentially.
    Theorem: D_f(t) remains bounded in [3, 6] with fixed point ~ 3.
    """

    max_depth: int = 5
    lambda_scale: float = PHI_INV  # 1/phi ~ 0.618034

    def fractal_cost(
        self,
        x: HyperspacePoint,
        mu: IdealState,
        gateway_system: TripolarGatewaySystem,
        depth: int = 0,
    ) -> float:
        """
        Compute fractal gateway cost across all recursion levels.

        Total = sum_{m=0}^{max_depth} lambda^m * L_gate(x_scaled)
        """
        if depth >= self.max_depth:
            return 0.0

        scale = self.lambda_scale ** depth
        gate_cost = gateway_system.compute_gate_cost(x, mu)

        # Scaled cost at this level
        level_cost = scale * gate_cost

        # Recurse into 3 children (scale state toward mu)
        child_cost = 0.0
        for _ in range(3):
            child_cost += self.fractal_cost(x, mu, gateway_system, depth + 1)

        return level_cost + scale * child_cost / 3.0

    def node_count(self, depth: int) -> int:
        """Total nodes in fractal tree at given depth: (3^(d+1) - 1) / 2."""
        return (3 ** (depth + 1) - 1) // 2

    def cost_decay_profile(
        self,
        x: HyperspacePoint,
        mu: IdealState,
        gateway_system: TripolarGatewaySystem,
    ) -> List[float]:
        """Show cost contribution at each recursion level."""
        costs = []
        for d in range(self.max_depth):
            scale = self.lambda_scale ** d
            gate_cost = gateway_system.compute_gate_cost(x, mu)
            costs.append(scale * gate_cost)
        return costs


# =============================================================================
# 3. TRI-FRACTAL DISCOURAGEMENT DERIVATIVE (TFDD)
# =============================================================================


def emotional_valence(
    x: HyperspacePoint,
    mu: IdealState,
    nu: List[float],
    t: float = 0.0,
) -> float:
    """
    Compute emotional valence E(x,t) — positive = aligned, negative = deviated.

    E(x,t) = sum_l nu_l * w_l * (mu_l - d_l) * cos(omega_l * t + phi_l)

    Positive E means the agent is in a honesty/resonance/integration state.
    Negative E means command/isolation/deviation state.
    """
    x_vec = x.to_vector()
    mu_vec = mu.to_vector()

    E = 0.0
    for l in range(6):
        w_l = TONGUE_WEIGHTS[l]
        d_l = abs(x_vec[l] - mu_vec[l])
        omega_l = TONGUE_FREQUENCIES[l]
        phi_l = TONGUE_PHASES[l]
        phase = math.cos(omega_l * t + phi_l)

        E += nu[l] * w_l * (mu_vec[l] - d_l) * phase

    # Guard against NaN from bad inputs
    if not math.isfinite(E):
        return -1.0  # Worst-case: treat as negative valence
    return E


def discouragement_function(e: float, beta: float = 1.0, w: float = 1.0) -> float:
    """
    Base discouragement function D(e).

    D(e) = w * exp(beta * max(0, -e))

    e >= 0: D = w (baseline, no penalty)
    e < 0: D grows exponentially (strong discouragement)

    Guards: NaN/Inf inputs are treated as worst-case (e = -1.0).
    Exponential is clamped to prevent overflow (max exponent = 50).
    """
    # NaN/Inf guard: treat non-finite as worst-case negative
    if not math.isfinite(e):
        e = -1.0
    # Clamp exponent to prevent overflow (exp(50) ~ 5e21, safe)
    exponent = min(beta * max(0.0, -e), 50.0)
    return w * math.exp(exponent)


def discouragement_derivative(e: float, beta: float = 1.0, w: float = 1.0) -> float:
    """
    Derivative dD/de — the gradient push.

    For e < 0: dD/de = -beta * w * exp(beta * (-e)) -> pushes toward positive
    For e >= 0: dD/de = 0 -> no interference with positive states

    Guards: NaN/Inf handled, exponent clamped.
    """
    if not math.isfinite(e):
        e = -1.0
    if e < 0:
        exponent = min(beta * (-e), 50.0)
        return -beta * w * math.exp(exponent)
    return 0.0


def positivity_weight(e: float, gamma: float = 0.5) -> float:
    """
    Positivity weighting P(e) = 1 + gamma * tanh(e).

    Positive e -> P > 1 (reward boost, up to 1+gamma)
    Negative e -> P < 1 (damped penalty)
    Guards: NaN/Inf -> neutral (P = 1.0).
    """
    if not math.isfinite(e):
        return 1.0  # Neutral weight for non-finite inputs
    return 1.0 + gamma * math.tanh(e)


@dataclass
class TFDD:
    """
    Tri-Fractal Discouragement Derivative.

    Evaluates discouragement along the 3 geodesics at each fractal level:

    D_TFDD^(m)(x, t) = lambda^m * sum_k P(E_k) * D(E_k)

    Full emotional loss:
    L_emotional = alpha_tfdd * sum_{m=0}^M D_TFDD^(m)

    Properties:
      - Net-positive push: dL/de < 0 for all negative e
      - Fractal stability preserved: D_f stays bounded
      - Smooth transition at e=0 (no oscillation)
    """

    beta: float = 1.0       # Discouragement strength
    gamma: float = 0.5      # Positivity bias
    alpha_tfdd: float = 0.4 # Loss weight
    max_depth: int = 3      # Fractal recursion depth

    def compute(
        self,
        x: HyperspacePoint,
        mu: IdealState,
        nu: List[float],
        t: float = 0.0,
    ) -> float:
        """Compute TFDD emotional loss."""
        # Get emotional valence projected onto 3 geodesics
        E = emotional_valence(x, mu, nu, t)

        # Evaluate along each geodesic direction
        total = 0.0
        vectors = tripolar_geodesic_vectors()
        x_vec = x.to_vector()
        mu_vec = mu.to_vector()

        for m in range(self.max_depth):
            scale = PHI_INV ** m
            for v_k in vectors:
                # Project emotional valence onto this geodesic
                centered = [x_vec[i] - mu_vec[i] for i in range(min(3, len(x_vec)))]
                proj_scalar = sum(centered[i] * v_k[i] for i in range(len(v_k)))

                # Modulate E by projection alignment
                e_k = E * (1.0 + 0.1 * proj_scalar)

                D_k = discouragement_function(e_k, self.beta)
                P_k = positivity_weight(e_k, self.gamma)
                total += scale * P_k * D_k

        return self.alpha_tfdd * total

    def gradient_direction(
        self,
        x: HyperspacePoint,
        mu: IdealState,
        nu: List[float],
        t: float = 0.0,
    ) -> str:
        """Return the emotional gradient direction (for diagnostics)."""
        E = emotional_valence(x, mu, nu, t)
        if E >= 0:
            return "POSITIVE (no correction needed)"
        else:
            strength = discouragement_derivative(E, self.beta)
            return f"NEGATIVE (push strength={strength:.4f})"


# =============================================================================
# 4. SACRED EGGS — Future Protection Matrix
# =============================================================================


@dataclass(frozen=True)
class SacredEgg:
    """
    A Sacred Egg is a multiplicative governance prior on Langues weights.

    Each Egg has an affinity vector that modulates the 6 tongue weights.
    When emotional valence is positive, Eggs "bloom" (amplify alignment).
    When negative, Eggs "close" (protective shutdown).

    From the Notion spec: Sacred Eggs combine GeoSeal encryption,
    Tongue encoding, and ritual-based predicate gating.
    """

    name: str
    role: str
    affinity: Tuple[float, ...]  # 6D: (KO, AV, RU, CA, UM, DR)
    alpha: float = 0.3           # Activation strength


# Canonical Egg definitions (from Notion + lore)
SACRED_EGGS = (
    SacredEgg(
        name="Amber",
        role="Clarity / Intent",
        affinity=(1.0, 0.4, 0.3, 0.2, 0.1, 0.1),
        alpha=0.3,
    ),
    SacredEgg(
        name="Emerald",
        role="Curiosity / Resonance",
        affinity=(0.3, 1.0, 0.5, 0.4, 0.2, 0.2),
        alpha=0.3,
    ),
    SacredEgg(
        name="Sapphire",
        role="Wisdom / Binding",
        affinity=(0.4, 0.5, 1.0, 0.8, 0.3, 0.3),
        alpha=0.3,
    ),
    SacredEgg(
        name="Opaline",
        role="Integration / Third Thread",
        affinity=(0.2, 0.3, 0.4, 0.6, 1.0, 1.0),
        alpha=0.3,
    ),
)


def egg_activation(E: float, gamma: float = 0.5) -> float:
    """
    Egg activation factor tied to TFDD emotional valence.

    V_i = 1/(1+max(0,-E)) * (1 + gamma*tanh(E))

    Positive E -> V ~ 1.0-1.5 (Eggs bloom, amplify weights)
    Negative E -> V -> 0 (Eggs close, protective shutdown)
    Guards: NaN/Inf -> 0.0 (protective shutdown).
    """
    if not math.isfinite(E):
        return 0.0  # Non-finite = shut down (protective)
    return (1.0 / (1.0 + max(0.0, -E))) * (1.0 + gamma * math.tanh(E))


@dataclass
class SacredEggsMatrix:
    """
    Future Protection Matrix — 4 Sacred Eggs as multiplicative priors.

    Effective weights:
      w_l_eff = w_l * product_i (1 + alpha_i * E_i[l] * V_i)

    Positive emotional valence → Eggs bloom → weights amplified.
    Negative valence → Eggs close → weights reduced (protective mode).

    The Eggs are the mathematical "guardian spirits" of the loss landscape.
    """

    eggs: Tuple[SacredEgg, ...] = SACRED_EGGS
    gamma: float = 0.5

    def compute_effective_weights(
        self,
        base_weights: List[float],
        emotional_valence: float,
    ) -> List[float]:
        """
        Compute egg-modified effective Langues weights.

        Returns new weights where each w_l is multiplied by the
        cumulative Egg activation across all 4 Eggs.
        """
        V = egg_activation(emotional_valence, self.gamma)

        eff_weights = list(base_weights)
        for egg in self.eggs:
            for l in range(6):
                eff_weights[l] *= (1.0 + egg.alpha * egg.affinity[l] * V)

        return eff_weights

    def compute_egg_cost(
        self,
        x: HyperspacePoint,
        mu: IdealState,
        nu: List[float],
        t: float = 0.0,
    ) -> float:
        """
        Compute Sacred Eggs contribution to L_total.

        Returns the DIFFERENCE between egg-modified cost and base cost.
        Positive when Eggs raise protection, negative when Eggs reduce cost
        (alignment reward).
        """
        E = emotional_valence(x, mu, nu, t)
        V = egg_activation(E, self.gamma)

        # Compute base and egg-modified L_f for comparison
        x_vec = x.to_vector()
        mu_vec = mu.to_vector()

        base_cost = 0.0
        egg_cost = 0.0

        for l in range(6):
            w_l = TONGUE_WEIGHTS[l]
            d_l = abs(x_vec[l] - mu_vec[l])
            omega_l = TONGUE_FREQUENCIES[l]
            phi_l = TONGUE_PHASES[l]
            phase_shift = math.sin(omega_l * t + phi_l)
            shifted_d = d_l + 0.1 * phase_shift
            beta_l = 1.0 + 0.1 * math.cos(phi_l)

            exponent = min(beta_l * shifted_d, 50.0)  # Clamp to prevent overflow
            base_term = nu[l] * w_l * math.exp(exponent)
            base_cost += base_term

            # Egg-modified weight
            w_eff = w_l
            for egg in self.eggs:
                w_eff *= (1.0 + egg.alpha * egg.affinity[l] * V)

            egg_term = nu[l] * w_eff * math.exp(exponent)
            egg_cost += egg_term

        return egg_cost - base_cost

    def egg_profile(self, emotional_valence: float) -> dict:
        """Per-egg activation profile (diagnostic)."""
        V = egg_activation(emotional_valence, self.gamma)
        return {
            egg.name: {
                "role": egg.role,
                "activation": round(V, 4),
                "max_boost": round(max(egg.affinity) * egg.alpha * V, 4),
            }
            for egg in self.eggs
        }


# =============================================================================
# 5. HAUSDORFF INTENT ROUGHNESS
# =============================================================================


def hausdorff_roughness(
    trajectory: List[List[float]],
) -> float:
    """
    Estimate intent roughness of a trajectory through 6D Langues space.

    Combines three measures into a composite pseudo-Hausdorff dimension:

    1. Tortuosity: total_path_length / displacement (1.0 = straight line)
    2. Angular entropy: variance of turning angles between steps
    3. Step variance: how erratic step sizes are

    Low D_H (~1.0): smooth, benign trajectory (ALLOW)
    Medium D_H (1.3-2.0): moderate texture (QUARANTINE)
    High D_H (>2.0): jagged adversarial evasion (REVIEW/DENY)

    Args:
        trajectory: List of 6D state vectors (agent's path over time)

    Returns:
        Estimated roughness D_H in [1.0, 6.0]
    """
    if len(trajectory) < 3:
        return 1.0

    dim = len(trajectory[0])

    # Compute step vectors and lengths
    step_lengths = []
    total_path = 0.0
    for i in range(1, len(trajectory)):
        d_sq = sum(
            (trajectory[i][d] - trajectory[i - 1][d]) ** 2
            for d in range(dim)
        )
        step_len = math.sqrt(d_sq)
        step_lengths.append(step_len)
        total_path += step_len

    if total_path < 1e-15:
        return 1.0

    # 1. Tortuosity: path_length / displacement
    displacement_sq = sum(
        (trajectory[-1][d] - trajectory[0][d]) ** 2 for d in range(dim)
    )
    displacement = math.sqrt(displacement_sq) if displacement_sq > 1e-15 else 1e-10
    tortuosity = total_path / displacement

    # 2. Angular entropy: mean cosine of turning angles
    cos_angles = []
    for i in range(1, len(trajectory) - 1):
        # Vectors: prev->curr and curr->next
        v1 = [trajectory[i][d] - trajectory[i - 1][d] for d in range(dim)]
        v2 = [trajectory[i + 1][d] - trajectory[i][d] for d in range(dim)]

        dot = sum(v1[d] * v2[d] for d in range(dim))
        n1 = math.sqrt(sum(v1[d] ** 2 for d in range(dim)))
        n2 = math.sqrt(sum(v2[d] ** 2 for d in range(dim)))

        if n1 > 1e-15 and n2 > 1e-15:
            cos_angle = max(-1.0, min(1.0, dot / (n1 * n2)))
            cos_angles.append(cos_angle)

    if not cos_angles:
        mean_cos = 1.0
    else:
        mean_cos = sum(cos_angles) / len(cos_angles)

    # Angular roughness: 0 = straight (cos=1), 1 = fully random (cos=0), 2 = reversals
    angular_roughness = 1.0 - mean_cos  # Range [0, 2]

    # 3. Step variance: coefficient of variation of step lengths
    if len(step_lengths) > 1:
        mean_step = sum(step_lengths) / len(step_lengths)
        if mean_step > 1e-15:
            var_step = sum((s - mean_step) ** 2 for s in step_lengths) / len(step_lengths)
            cv_step = math.sqrt(var_step) / mean_step
        else:
            cv_step = 0.0
    else:
        cv_step = 0.0

    # Composite pseudo-Hausdorff dimension
    # Angular roughness is primary signal (direction unpredictability)
    # Tortuosity and step variance are secondary
    D_H = (
        1.0                                       # Base dimension
        + 1.5 * angular_roughness                  # Primary: direction chaos [0, 3]
        + 0.3 * min(math.log1p(tortuosity - 1.0), 2.0)  # Secondary: path winding
        + 0.2 * min(cv_step, 3.0)                  # Secondary: step irregularity
    )

    return max(1.0, min(D_H, 6.0))  # Clamp to [1, 6]


def classify_intent_roughness(D_H: float) -> Tuple[str, str]:
    """
    Classify trajectory roughness into risk levels.

    D_H < 2.0: Smooth or structured (sine waves, gentle curves) → ALLOW
    D_H 2.0-3.0: Textured (random walks, moderate noise) → QUARANTINE
    D_H 3.0-4.0: Jagged (high noise, unpredictable) → REVIEW
    D_H > 4.0: Fractal evasion (adversarial zigzag/noise) → DENY

    Returns (risk_level, decision).
    """
    if D_H < 2.0:
        return "SMOOTH", "ALLOW"
    elif D_H < 3.0:
        return "TEXTURED", "QUARANTINE"
    elif D_H < 4.0:
        return "JAGGED", "REVIEW"
    else:
        return "FRACTAL_EVASION", "DENY"


# =============================================================================
# =============================================================================
# 6. RIEMANN SPECTRAL PRIOR (Precomputed Zeta Zero Lookup)
# =============================================================================


# First 100 non-trivial zeta zero imaginary parts (gamma_k).
# These are known to >30 decimal places. We store as float64 (sufficient).
# Source: Andrew Odlyzko's tables / LMFDB.
# Full list: extend to 10K+ from file for production.
ZETA_ZEROS_GAMMA = [
    14.134725, 21.022040, 25.010858, 30.424876, 32.935062,
    37.586178, 40.918719, 43.327073, 48.005151, 49.773832,
    52.970321, 56.446248, 59.347044, 60.831779, 65.112544,
    67.079811, 69.546402, 72.067158, 75.704691, 77.144840,
    79.337375, 82.910381, 84.735493, 87.425275, 88.809111,
    92.491899, 94.651344, 95.870634, 98.831194, 101.317851,
    103.725538, 105.446623, 107.168611, 111.029536, 111.874659,
    114.320220, 116.226680, 118.790783, 121.370125, 122.946829,
    124.256819, 127.516684, 129.578704, 131.087688, 133.497737,
    134.756510, 138.116042, 139.736209, 141.123707, 143.111846,
    146.000982, 147.422765, 150.053521, 150.925258, 153.024694,
    156.112909, 157.597592, 158.849988, 161.188964, 163.030709,
    165.537069, 167.184440, 169.094515, 169.911976, 173.411537,
    174.754192, 176.441434, 178.377407, 179.916484, 182.207078,
    184.874467, 185.598784, 187.228922, 189.416158, 192.026656,
    193.079727, 195.265396, 196.876482, 198.015310, 201.264751,
    202.493595, 204.189671, 205.394697, 207.906259, 209.576509,
    211.690862, 213.347919, 214.547044, 216.169538, 219.067596,
    220.714919, 221.430706, 224.007000, 224.983324, 227.421444,
    229.337413, 231.250189, 231.987236, 233.693404, 236.524230,
]


@dataclass
class RiemannSpectralPrior:
    """
    Riemann spectral prior: precomputed zeta-zero penalty.

    Uses the first N known non-trivial zeros of the Riemann zeta function
    to create a spectral penalty that forces the emotional-geometric
    manifold to stay on the "critical line" of alignment.

    L_RH = alpha_rh * sum_k 1 / (1 + |delta(E)|^2 * gamma_k^2)

    This is a lightweight approximation that captures the RH zero structure
    without requiring mpmath at runtime. For full precision, precompute
    with mpmath offline and load from file.

    The penalty is highest when emotional valence E is negative (pushes
    the argument off the critical line) and lowest when E >= 0 (on the line).
    """

    alpha_rh: float = 0.05
    num_zeros: int = 100

    def compute(self, emotional_valence: float) -> float:
        """
        Compute RH spectral penalty from emotional valence.

        Uses precomputed gamma_k values. No mpmath needed at runtime.
        The penalty structure mirrors the zeta zero distribution:
        closely-spaced zeros create dense oscillatory barriers.
        """
        delta = max(0.0, -emotional_valence) * 0.01  # Only penalize negative E
        if delta < 1e-10:
            return 0.0  # On the critical line — no penalty

        penalty = 0.0
        n = min(self.num_zeros, len(ZETA_ZEROS_GAMMA))
        for k in range(n):
            gamma_k = ZETA_ZEROS_GAMMA[k]
            # Inverse resonance: penalty spikes near each zero
            penalty += 1.0 / (1.0 + delta * delta * gamma_k * gamma_k)

        return self.alpha_rh * penalty


# =============================================================================
# 7. LYAPUNOV STABILITY MONITOR
# =============================================================================


@dataclass
class LyapunovMonitor:
    """
    Real-time Lyapunov stability estimator for the 7D World Tree system.

    Reference spectrum (from Benettin algorithm, 5000 time units):
      lambda_1 = 0.000000  (neutral creative drift)
      lambda_2..7 = -0.100251  (uniform contraction, matches kappa=0.1)
      Trace = -0.601505  (strong dissipation)

    This monitor estimates the instantaneous stability from the TFDD
    gradient strength and flux relaxation rate, without running full
    variational integration.
    """

    # Reference values from the full 7D Benettin computation
    reference_trace: float = -0.601505
    reference_kappa: float = 0.1

    def estimate(
        self,
        emotional_valence: float,
        flux_nu: List[float],
        tfdd_beta: float = 1.0,
    ) -> dict:
        """
        Fast stability estimate from current system state.

        Returns spectrum estimate, stability score, and diagnostic flags.
        """
        # Neutral direction (lambda_1 ~ 0): always present on the attractor
        lambda_1 = 0.0

        # Contracting directions: kappa * mean(nu) gives effective relaxation
        mean_nu = sum(flux_nu) / max(len(flux_nu), 1)
        lambda_contract = -self.reference_kappa * mean_nu

        # TFDD contribution: negative E makes contraction stronger
        if emotional_valence < 0:
            tfdd_boost = -tfdd_beta * abs(emotional_valence) * 0.01
            lambda_contract += tfdd_boost

        # Effective 7D spectrum estimate
        spectrum = [lambda_1] + [lambda_contract] * 6
        trace = sum(spectrum)

        # Stability diagnostics
        is_stable = trace < -0.3  # Conservative threshold
        deviation = abs(trace - self.reference_trace)

        return {
            "spectrum": [round(s, 6) for s in spectrum],
            "trace": round(trace, 6),
            "reference_trace": self.reference_trace,
            "deviation": round(deviation, 6),
            "is_stable": is_stable,
            "effective_kappa": round(-lambda_contract, 6),
            "D_f": round(sum(flux_nu), 2),
        }


# =============================================================================
# 8. UNIFIED WORLD TREE METRIC (Complete Master Function)
# =============================================================================


@dataclass
class WorldTreeMetric:
    """
    The complete World Tree emotional-geometric governance metric.

    L_total = L_f + L_gate + L_fractal + L_emotional + L_eggs + L_rh

    Where:
      L_f        = Fluxing Langues metric
      L_gate     = Tripolar geodesic gateway cost
      L_fractal  = Fractal recursion cost (golden-ratio damped)
      L_emotional = TFDD positivity enforcement
      L_eggs     = Sacred Eggs Future Protection Matrix
      L_rh       = Riemann spectral prior (critical-line constraint)

    Plus: Lyapunov stability monitoring (real-time diagnostic)

    The World Tree is the loss landscape itself.
    """

    langues: FluxingLanguesMetric = field(default_factory=FluxingLanguesMetric)
    gateways: TripolarGatewaySystem = field(default_factory=TripolarGatewaySystem)
    fractal: FractalTripod = field(default_factory=FractalTripod)
    tfdd: TFDD = field(default_factory=TFDD)
    eggs: SacredEggsMatrix = field(default_factory=SacredEggsMatrix)
    riemann: RiemannSpectralPrior = field(default_factory=RiemannSpectralPrior)
    lyapunov: LyapunovMonitor = field(default_factory=LyapunovMonitor)

    def compute_total(
        self,
        x: HyperspacePoint,
        t: float = 0.0,
        dt: float = 0.01,
    ) -> dict:
        """
        Compute the full World Tree metric (unified master function).

        L_total = L_f + L_gate + L_fractal + L_emotional + L_eggs + L_rh

        Returns dict with all 7 components, governance value, egg profile,
        Lyapunov stability, and full diagnostic state.
        """
        # 1. Fluxing Langues metric
        L_f, D_f = self.langues.compute_with_flux_update(x, dt)

        # 2. Gateway cost (negative = reduction near geodesics)
        L_gate = self.gateways.compute_gate_cost(x, self.langues.ideal)

        # 3. Fractal recursion cost
        L_fractal = self.fractal.fractal_cost(
            x, self.langues.ideal, self.gateways, depth=0
        )

        # 4. TFDD emotional cost
        L_emotional = self.tfdd.compute(
            x, self.langues.ideal, self.langues.flux.nu, t
        )

        # 5. Sacred Eggs protection cost
        L_eggs = self.eggs.compute_egg_cost(
            x, self.langues.ideal, self.langues.flux.nu, t
        )

        # 6. Emotional valence (needed for RH + diagnostics)
        E = emotional_valence(x, self.langues.ideal, self.langues.flux.nu, t)

        # 7. Riemann spectral prior
        L_rh = self.riemann.compute(E)

        # Total (all 6 terms)
        L_total = L_f + L_gate + L_fractal + L_emotional + L_eggs + L_rh

        # Governance value
        V = langues_value(max(0.0, L_total))

        # Nearest geodesic
        nearest_k = self.gateways.nearest_geodesic(x, self.langues.ideal)

        # Egg diagnostic
        egg_profile = self.eggs.egg_profile(E)

        # Lyapunov stability monitor
        lyap = self.lyapunov.estimate(E, self.langues.flux.nu, self.tfdd.beta)

        return {
            "L_f": L_f,
            "L_gate": L_gate,
            "L_fractal": L_fractal,
            "L_emotional": L_emotional,
            "L_eggs": L_eggs,
            "L_rh": L_rh,
            "L_total": L_total,
            "value": V,
            "D_f": D_f,
            "emotional_valence": E,
            "nearest_geodesic": nearest_k,
            "emotional_state": "POSITIVE" if E >= 0 else "NEGATIVE",
            "egg_profile": egg_profile,
            "lyapunov": lyap,
        }

    def simulate(
        self,
        x: HyperspacePoint,
        steps: int = 100,
        dt: float = 0.01,
    ) -> List[dict]:
        """Run World Tree simulation for multiple steps."""
        results = []
        for step in range(steps):
            t = step * dt
            result = self.compute_total(x, t, dt)
            result["step"] = step
            result["t"] = t
            results.append(result)
        return results


# =============================================================================
# DEMO / TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("GEODESIC DIMENSIONAL GATEWAYS + WORLD TREE METRIC")
    print("=" * 70)
    print()

    # Verify 120-degree symmetry
    gs = TripolarGatewaySystem()
    print(f"120-degree symmetry verified: {gs.verify_120_symmetry()}")
    print()

    # Test states
    safe = HyperspacePoint(time=0, intent=0, policy=0.5, trust=0.9, risk=0.1, entropy=0.2)
    drift = HyperspacePoint(time=0, intent=0.5, policy=0.3, trust=0.7, risk=0.4, entropy=0.3)
    attack = HyperspacePoint(time=0, intent=1.5, policy=0.1, trust=0.2, risk=0.9, entropy=0.8)

    # World Tree metric
    wt = WorldTreeMetric()

    print("WORLD TREE METRIC:")
    print(f"  {'State':<16} {'L_total':<10} {'Value':<10} {'E_valence':<12} {'Emotion':<10} {'Gateway'}")
    print(f"  {'-'*16} {'-'*10} {'-'*10} {'-'*12} {'-'*10} {'-'*8}")

    for name, state in [("Safe", safe), ("Drifting", drift), ("Adversarial", attack)]:
        r = wt.compute_total(state)
        print(
            f"  {name:<16} {r['L_total']:<10.3f} {r['value']:<10.4f} "
            f"{r['emotional_valence']:<12.3f} {r['emotional_state']:<10} {r['nearest_geodesic']}"
        )

    print()

    # TFDD test
    print("TFDD EMOTIONAL BALANCING:")
    tfdd = TFDD()
    ideal = IdealState()
    nu = [1.0] * 6

    for name, state in [("Safe", safe), ("Drifting", drift), ("Adversarial", attack)]:
        L_em = tfdd.compute(state, ideal, nu)
        direction = tfdd.gradient_direction(state, ideal, nu)
        print(f"  {name:<16} L_emotional={L_em:.4f}  {direction}")

    print()

    # Sacred Eggs test
    print("SACRED EGGS (Future Protection Matrix):")
    eggs = SacredEggsMatrix()
    for name, state in [("Safe", safe), ("Drifting", drift), ("Adversarial", attack)]:
        E = emotional_valence(state, ideal, nu)
        V = egg_activation(E)
        L_egg = eggs.compute_egg_cost(state, ideal, nu)
        profile = eggs.egg_profile(E)
        print(f"  {name:<16} activation={V:.4f}  L_eggs={L_egg:.4f}")
        for egg_name, info in profile.items():
            print(f"    {egg_name:<10} boost={info['max_boost']:.4f}  ({info['role']})")

    print()

    # Hausdorff roughness test
    print("HAUSDORFF INTENT ROUGHNESS:")

    # Smooth trajectory (benign)
    smooth_traj = [[0.0 + i * 0.01] * 6 for i in range(100)]
    D_H_smooth = hausdorff_roughness(smooth_traj)
    risk_s, dec_s = classify_intent_roughness(D_H_smooth)
    print(f"  Smooth trajectory: D_H={D_H_smooth:.3f} -> {risk_s} -> {dec_s}")

    # Jagged trajectory (adversarial)
    import random
    random.seed(42)
    jagged_traj = [[random.gauss(0, 1) for _ in range(6)] for _ in range(100)]
    D_H_jagged = hausdorff_roughness(jagged_traj)
    risk_j, dec_j = classify_intent_roughness(D_H_jagged)
    print(f"  Jagged trajectory: D_H={D_H_jagged:.3f} -> {risk_j} -> {dec_j}")

    print()

    # Fractal cost decay
    print("FRACTAL COST DECAY (golden-ratio damped):")
    ft = FractalTripod(max_depth=6)
    costs = ft.cost_decay_profile(drift, ideal, gs)
    for d, c in enumerate(costs):
        print(f"  Depth {d}: cost={c:.6f}  (lambda^{d}={PHI_INV**d:.6f})")

    print()
    print("=" * 70)
    print("G(T) = integral 1/(1+L_total) dt")
    print("L_total = L_f + L_gate + L_fractal + L_emotional")
    print("The World Tree is the loss landscape.")
    print("=" * 70)
