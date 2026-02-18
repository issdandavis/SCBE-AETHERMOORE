#!/usr/bin/env python3
"""
Harmonic Scaling Law - The Vertical Wall

This module implements the core harmonic scaling functions that make
SCBE-AETHERMOORE geometrically impossible to attack.

Key Functions:
- H(d*) = exp(d*^2) : The vertical wall - risk explodes exponentially
- Psi(P) = 1 + (max-1) * tanh(beta * P) : Anti-fragile stiffness
- breathing_transform() : Space contracts/expands based on threat

Patent Claims: 61, 62, 16
Author: Isaac Davis / SpiralVerse OS
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, List

# Constants
PHI = (1 + np.sqrt(5)) / 2  # Golden Ratio


# =============================================================================
# THE VERTICAL WALL: H(d*) = exp(d*^2)
# =============================================================================


def harmonic_scaling(d_star: float) -> float:
    """
    The Harmonic Scaling Function H(d*) = exp(d*^2)

    This creates the "vertical wall" - risk amplification that grows
    exponentially as distance from the trusted center increases.

    Args:
        d_star: Normalized hyperbolic distance from trusted center

    Returns:
        Risk multiplier H(d*)

    Examples:
        d* = 0.0 -> H = 1.00         (at center, normal risk)
        d* = 1.0 -> H = 2.72         (getting far, elevated)
        d* = 2.0 -> H = 54.60        (danger zone)
        d* = 3.0 -> H = 8,103.08     (near boundary, catastrophic)
        d* = 4.0 -> H = 8,886,110.52 (impossible to reach)
    """
    return float(np.exp(d_star**2))


def harmonic_scaling_derivative(d_star: float) -> float:
    """Derivative dH/d(d*) = 2*d* * exp(d*^2)"""
    return 2.0 * d_star * np.exp(d_star**2)


# =============================================================================
# ANTI-FRAGILE STIFFNESS: Psi(P) (Claim 61)
# =============================================================================


def anti_fragile_stiffness(
    pressure: float, psi_max: float = 2.0, beta: float = 3.0
) -> float:
    """
    Anti-Fragile Living Metric Stiffness (Claim 61)

    Psi(P) = 1 + (psi_max - 1) * tanh(beta * P)

    The system gets STRONGER under attack, like a non-Newtonian fluid:
    - Walk slowly -> feet sink in
    - Run fast -> surface becomes SOLID

    Args:
        pressure: Attack pressure P in [0, 1]
        psi_max: Maximum stiffness multiplier (default 2.0)
        beta: Sensitivity parameter (default 3.0)

    Returns:
        Stiffness multiplier Psi in [1, psi_max]

    Examples:
        P = 0.0 -> Psi = 1.00 (normal operation)
        P = 0.3 -> Psi = 1.72 (light attack, hardening)
        P = 0.5 -> Psi = 1.91 (medium attack, harder)
        P = 0.7 -> Psi = 1.97 (heavy attack, nearly max)
        P = 1.0 -> Psi = 2.00 (maximum attack, 2x stronger)
    """
    return 1.0 + (psi_max - 1.0) * np.tanh(beta * pressure)


# =============================================================================
# BREATHING TRANSFORM (Claim 62)
# =============================================================================


def breathing_transform(
    point: np.ndarray, breath_factor: float, eps: float = 1e-6
) -> np.ndarray:
    """
    Breathing Transform - Space contracts/expands based on threat level.

    The Poincare ball "breathes":
    - b < 1: Contract (low threat, easier to reach targets)
    - b = 1: Identity (no change)
    - b > 1: Expand (high threat, harder to reach targets)

    Uses the formula: u' = u * tanh(b * arctanh(||u||)) / ||u||

    Args:
        point: Point in Poincare ball (||point|| < 1)
        breath_factor: Breathing parameter b
        eps: Small epsilon for numerical stability

    Returns:
        Transformed point, still inside the ball
    """
    norm = np.linalg.norm(point)

    if norm < eps:
        return point  # Origin stays at origin

    # Clamp to open ball
    if norm >= 1.0 - eps:
        point = point * (1.0 - eps) / norm
        norm = 1.0 - eps

    # Breathing transform
    arctanh_norm = np.arctanh(norm)
    new_norm = np.tanh(breath_factor * arctanh_norm)

    return point * (new_norm / norm)


# =============================================================================
# FRACTIONAL FLUX ODE (Claim 16)
# =============================================================================


def fractional_flux_step(
    nu: float,
    nu_bar: float,
    kappa: float = 0.1,
    sigma: float = 0.05,
    omega: float = 1.0,
    t: float = 0.0,
    dt: float = 0.01,
) -> float:
    """
    Fractional Flux ODE: nu_dot = kappa*(nu_bar - nu) + sigma*sin(Omega*t)

    Dimensions "breathe" via ODE dynamics.

    Args:
        nu: Current fractional dimension
        nu_bar: Target dimension
        kappa: Convergence rate
        sigma: Oscillation amplitude
        omega: Oscillation frequency
        t: Current time
        dt: Time step

    Returns:
        Updated nu value
    """
    nu_dot = kappa * (nu_bar - nu) + sigma * np.sin(omega * t)
    return np.clip(nu + nu_dot * dt, 0.0, 1.0)


# =============================================================================
# SETTLING WAVE K(t) (Claim 62)
# =============================================================================


def settling_wave(
    t: float, coefficients: List[Tuple[float, float, float]] = None
) -> float:
    """
    Settling Wave: K(t) = Sum of C_n * sin(omega_n * t + phi_n)

    Key only materializes at t_arrival.

    Args:
        t: Time parameter
        coefficients: List of (C_n, omega_n, phi_n) tuples

    Returns:
        K(t) value
    """
    if coefficients is None:
        # Default: Constructive interference at t=0, 1, 2, ...
        coefficients = [
            (1.0, 2 * np.pi, 0.0),
            (0.5, 4 * np.pi, 0.0),
            (0.25, 6 * np.pi, 0.0),
        ]

    return sum(C * np.sin(omega * t + phi) for C, omega, phi in coefficients)


# =============================================================================
# COMPOSITE RISK (Lemma 13.1)
# =============================================================================


@dataclass
class RiskFactors:
    behavioral: float  # B: Base behavioral risk [0, 1]
    distance: float  # d*: Hyperbolic distance
    temporal: float  # T: Time penalty factor >= 1
    intent: float  # I: Intent suspicion factor >= 1


def composite_risk(factors: RiskFactors) -> Tuple[float, str]:
    """
    Composite Risk Calculation (Lemma 13.1)

    Risk' = B * H(d*) * T * I

    All factors are multiplicative - any single bad factor
    can trigger rejection.

    Args:
        factors: RiskFactors dataclass

    Returns:
        (risk_score, decision) tuple
    """
    H = harmonic_scaling(factors.distance)
    risk = factors.behavioral * H * factors.temporal * factors.intent

    if risk < 1.0:
        decision = "ALLOW"
    elif risk < 2.0:
        decision = "WARN"
    else:
        decision = "DENY"

    return risk, decision


# =============================================================================
# TRUST TUBE PROJECTION (Crystal Cranium Section 6.3)
# =============================================================================
#
# Rail family R = {γ_i} defines trusted trajectories through the Poincaré
# ball. The Trust Tube of radius ε wraps each rail, and points outside
# the tube are projected back via closest-point projection.
#
# project_to_tube(x, rail, ε) → x' ∈ Tube(rail, ε)
#
# This extends the breathing transform: breathing contracts/expands the
# ball, while tube projection constrains to specific rails.


TUBE_RADIUS = 0.15  # ε = 0.15 per spec


@dataclass
class TrustRail:
    """
    A trusted trajectory through the Poincaré ball.

    A rail γ(t) is defined by a sequence of waypoints in the ball,
    with cubic Hermite interpolation between them.
    """
    name: str
    waypoints: np.ndarray  # Shape (N, D) — waypoints in D-dimensional ball
    phi_weights: np.ndarray = None  # φ-scaled weights per segment

    def __post_init__(self):
        if self.phi_weights is None:
            n = len(self.waypoints) - 1
            self.phi_weights = np.array([PHI ** k for k in range(max(1, n))])

    def evaluate(self, t: float) -> np.ndarray:
        """
        Evaluate rail position γ(t) at parameter t ∈ [0, 1].

        Uses smoothstep interpolation between waypoints.
        """
        n = len(self.waypoints) - 1
        if n < 1:
            return self.waypoints[0].copy()

        t = np.clip(t, 0.0, 1.0)
        segment_t = t * n
        idx = int(np.floor(segment_t))
        idx = min(idx, n - 1)
        alpha = segment_t - idx

        # Smoothstep for C1 continuity
        alpha_smooth = alpha * alpha * (3 - 2 * alpha)

        p0 = self.waypoints[idx]
        p1 = self.waypoints[idx + 1]
        return (1 - alpha_smooth) * p0 + alpha_smooth * p1

    def closest_point(self, x: np.ndarray, n_samples: int = 100) -> Tuple[np.ndarray, float]:
        """
        Find the closest point on the rail to x.

        Returns (closest_point, parameter_t).
        """
        best_dist = float('inf')
        best_point = self.waypoints[0].copy()
        best_t = 0.0

        for i in range(n_samples + 1):
            t = i / n_samples
            p = self.evaluate(t)
            dist = np.linalg.norm(x - p)
            if dist < best_dist:
                best_dist = dist
                best_point = p
                best_t = t

        return best_point, best_t

    def segment_energy(self, segment_idx: int) -> float:
        """Energy cost for traversing a segment, φ-weighted."""
        if 0 <= segment_idx < len(self.phi_weights):
            return float(self.phi_weights[segment_idx])
        return 1.0


@dataclass
class TrustTube:
    """
    Trust Tube wrapping a rail family R = {γ_i}.

    Any point x in the Poincaré ball can be projected onto the closest
    tube. Points inside a tube are "on-rail" (trusted). Points outside
    are projected back, incurring an energy penalty proportional to
    the deviation distance scaled by the Harmonic Wall.
    """
    rails: List[TrustRail]
    epsilon: float = TUBE_RADIUS  # Tube radius ε = 0.15

    def is_on_rail(self, x: np.ndarray) -> Tuple[bool, int, float]:
        """
        Check if point x is within any trust tube.

        Returns:
            (is_inside, closest_rail_index, deviation_distance)
        """
        best_rail = 0
        best_dist = float('inf')

        for i, rail in enumerate(self.rails):
            closest, _ = rail.closest_point(x)
            dist = np.linalg.norm(x - closest)
            if dist < best_dist:
                best_dist = dist
                best_rail = i

        return best_dist <= self.epsilon, best_rail, best_dist

    def project_to_tube(self, x: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Project point x onto the closest trust tube.

        Crystal Cranium Section 6.3:
            x' = closest_rail_point + ε * (x - closest) / ||x - closest||

        If x is already inside a tube, returns x unchanged.

        Returns:
            (projected_point, energy_penalty)

        The energy penalty is:
            penalty = H(deviation) where H(d*) = exp(d*²)
        """
        is_inside, rail_idx, deviation = self.is_on_rail(x)

        if is_inside:
            return x.copy(), 0.0

        # Find closest point on closest rail
        rail = self.rails[rail_idx]
        closest, t_param = rail.closest_point(x)

        # Project to tube surface
        direction = x - closest
        dir_norm = np.linalg.norm(direction)
        if dir_norm < 1e-10:
            return closest.copy(), 0.0

        projected = closest + self.epsilon * direction / dir_norm

        # Ensure we stay in the Poincaré ball
        proj_norm = np.linalg.norm(projected)
        if proj_norm >= 1.0:
            projected = projected * 0.95 / proj_norm

        # Energy penalty from the Harmonic Wall
        penalty = harmonic_scaling(deviation)

        return projected, penalty

    def total_path_energy(self, points: List[np.ndarray]) -> float:
        """
        Compute total energy for a trajectory of points.

        Each point incurs a tube projection penalty, plus segment
        traversal energy from the closest rail's φ-weights.
        """
        total = 0.0
        for x in points:
            _, penalty = self.project_to_tube(x)
            total += penalty
        return total


def build_default_rails(
    n_rails: int = 3, dimensions: int = 6, n_waypoints: int = 8
) -> List[TrustRail]:
    """
    Build default trust rails using φ-distributed waypoints.

    Creates n_rails rails in dimensions-D space, each with n_waypoints
    waypoints distributed via golden-angle spacing.
    """
    rails = []
    for r in range(n_rails):
        waypoints = []
        for w in range(n_waypoints):
            # Golden-angle distribution in D dimensions
            t = w / max(1, n_waypoints - 1)
            angles = np.array([
                (r * PHI + w * PHI ** k) % (2 * np.pi)
                for k in range(1, dimensions + 1)
            ])
            point = np.cos(angles) * t * 0.7  # Stay well inside ball
            waypoints.append(point)
        rails.append(TrustRail(
            name=f"rail_{r}",
            waypoints=np.array(waypoints),
        ))
    return rails


# =============================================================================
# BONE DENSITY: H(d, R) = R^(d²) (Crystal Cranium Section 2.1)
# =============================================================================

def bone_density(d: float, R: float = 1.0) -> float:
    """
    Crystal Cranium bone density function.

    H(d, R) = R^(d²)

    This is the skull wall: computation becomes exponentially expensive
    as radial distance d approaches the boundary R.

    For R=1 this reduces to exp(d² * ln(R)) = 1 for all d, so we use
    the generalized form with the 14-layer depth as base:

    H(d, depth=14) = exp(d² * depth)

    Args:
        d: Radial distance in Poincaré ball (0 ≤ d < 1)
        R: Effective radius (default 1.0)

    Returns:
        Energy cost at distance d
    """
    depth = 14  # 14-layer pipeline depth
    return float(np.exp(d ** 2 * depth))


# =============================================================================
# DEMONSTRATION
# =============================================================================


def demonstrate_vertical_wall():
    """Visualize the vertical wall effect."""
    print("THE VERTICAL WALL: H(d*) = exp(d*^2)")
    print("=" * 50)

    distances = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

    for d in distances:
        H = harmonic_scaling(d)
        bar = "#" * min(40, int(np.log10(H + 1) * 10))
        print(f"d* = {d:.1f} -> H = {H:>12.2f} {bar}")

    print()
    print("Risk EXPLODES exponentially near the boundary!")


def demonstrate_anti_fragile():
    """Visualize anti-fragile behavior."""
    print("\nANTI-FRAGILE STIFFNESS: Psi(P)")
    print("=" * 50)

    for p in np.arange(0, 1.1, 0.1):
        psi = anti_fragile_stiffness(p)
        bar = "#" * int(psi * 20)
        status = "CALM" if p < 0.3 else "ELEVATED" if p < 0.7 else "CRITICAL"
        print(f"P={p:.1f} -> Psi={psi:.4f} [{bar:<40}] {status}")

    print()
    print("System gets STRONGER under attack!")


def demonstrate_trust_tube():
    """Visualize Trust Tube projection."""
    print("\nTRUST TUBE PROJECTION: project_to_tube(x, rail, epsilon)")
    print("=" * 50)

    # Build a simple rail in 6D
    rails = build_default_rails(n_rails=1, dimensions=6, n_waypoints=5)
    tube = TrustTube(rails=rails, epsilon=TUBE_RADIUS)

    # Test points at various distances from the rail
    rail_point = rails[0].evaluate(0.5)
    print(f"Rail midpoint: ||x|| = {np.linalg.norm(rail_point):.4f}")

    for offset in [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50]:
        test_point = rail_point + offset * np.ones(6) / np.sqrt(6)
        on_rail, _, dev = tube.is_on_rail(test_point)
        _, penalty = tube.project_to_tube(test_point)
        status = "ON-RAIL" if on_rail else "OFF-RAIL"
        print(f"  offset={offset:.2f} dev={dev:.4f} {status:8s} penalty={penalty:.2f}")


if __name__ == "__main__":
    print("SCBE-AETHERMOORE Harmonic Scaling Law Demo")
    print("=" * 60)

    demonstrate_vertical_wall()
    demonstrate_anti_fragile()
    demonstrate_trust_tube()

    print("\n" + "=" * 60)
    print("Demo complete. These are the mathematical foundations")
    print("that make attacks geometrically impossible.")
