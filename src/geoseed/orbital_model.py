"""
@file orbital_model.py
@module geoseed/orbital_model
@layer GeoSeed / M6 SphereMesh
@component HyperbolicOrbitalModel

Maps the 6 Sacred Tongue seed spheres to electron orbital shells
in the Poincaré ball (negatively curved H³ manifold).

Pattern:
  The phi-weight ladder φ⁰..φ⁵ places each seed sphere at a
  specific hyperbolic radial depth.  Standing waves at those
  depths have the same structure as atomic orbital shells — the
  Laplace-Beltrami eigenvalues on H³ for angular momentum l
  give quantisation that mirrors s/p/d/f/g/h shells.

Key discovery:
  Tongue CA (l=3) sits at Euclidean radius r = tanh(3·ln(φ)/2) = 1/φ ≈ 0.618
  — the golden ratio appears as a fixed point of the phi-depth mapping.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
from scipy.special import sph_harm_y, eval_genlaguerre, factorial

# ── Constants ─────────────────────────────────────────────────────────────────

PHI = (1.0 + math.sqrt(5.0)) / 2.0  # ≈ 1.6180339887

# 6 GeoSeed tongues → orbital shell mapping
# weight = φⁿ,  l = angular momentum quantum number,  m_count = 2l+1
TONGUES = [
    {"name": "Kor'aelin", "abbr": "KO", "n": 0, "weight": PHI**0, "l": 0},
    {"name": "Avali", "abbr": "AV", "n": 1, "weight": PHI**1, "l": 1},
    {"name": "Runethic", "abbr": "RU", "n": 2, "weight": PHI**2, "l": 2},
    {"name": "Cassisivadan", "abbr": "CA", "n": 3, "weight": PHI**3, "l": 3},
    {"name": "Umbroth", "abbr": "UM", "n": 4, "weight": PHI**4, "l": 4},
    {"name": "Draumric", "abbr": "DR", "n": 5, "weight": PHI**5, "l": 5},
]

# 21 Sacred Egg positions per shell (21D canonical state lift)
# Distributed as Fibonacci lattice on unit sphere, one egg per 21D axis.
_SACRED_EGG_COUNT = 21


# ── Hyperbolic geometry ────────────────────────────────────────────────────────


def phi_to_poincare_r(n: int) -> float:
    """
    Map phi-weight index n → Euclidean radius inside Poincaré ball.

    Hyperbolic distance from centre: ρ = n · ln(φ)
    Poincaré-ball Euclidean radius:  r = tanh(ρ/2)

    Special value: n=3 (Cassisivadan / f-orbital) gives r = 1/φ ≈ 0.618.
    """
    rho = n * math.log(PHI)
    return math.tanh(rho / 2.0)


def hyperbolic_distance(r1: float, r2: float) -> float:
    """Geodesic distance between two points at Euclidean radii r1, r2 on the
    same radial ray inside the Poincaré ball."""
    # d(r1, r2) = 2·atanh(|r1 - r2| / (1 - r1·r2))  (collinear case)
    num = abs(r1 - r2)
    den = 1.0 - r1 * r2
    if den <= 0:
        return float("inf")
    return 2.0 * math.atanh(num / den)


def laplace_beltrami_eigenvalue(ell: int) -> float:
    """
    Eigenvalue of the Laplace-Beltrami operator on H³ for angular momentum l.

    On H³ (unit-curvature): Δ_H³ Y = -(l+1)² · Y
    This gives the quantisation ladder: -1, -4, -9, -16, -25, -36
    for l = 0..5 — one per GeoSeed tongue.
    """
    return -float((ell + 1) ** 2)


def radial_wavefunction(rho: float, ell: int, n_radial: int = 1) -> float:
    """
    Radial part of the hyperbolic orbital wavefunction.

    Uses the hyperbolic-hydrogen analogy: replace r → sinh(ρ) in the
    flat-space radial wavefunction.

      R(ρ) = N · sinh^l(ρ) · exp(-α·ρ) · L_p^(2l+1)(2α·ρ)

    where α = 1/(n_radial + l), p = n_radial - 1, L is the associated
    Laguerre polynomial.  This mirrors the flat-space form with ρ
    (hyperbolic distance) in place of r (Euclidean radius).
    """
    if rho <= 0:
        return 0.0
    p = n_radial - 1
    alpha = 1.0 / (n_radial + ell)
    x = 2.0 * alpha * rho
    laguerre = float(eval_genlaguerre(p, 2 * ell + 1, x))
    norm = math.sqrt(
        (2.0 * alpha) ** 3 * float(factorial(p)) / (2.0 * (n_radial + ell) * float(factorial(p + 2 * ell + 1)))
    )
    return norm * (math.sinh(rho) ** ell) * math.exp(-alpha * rho) * laguerre


def angular_wavefunction(theta: float, phi_angle: float, ell: int, m: int) -> complex:
    """
    Angular part: standard spherical harmonic Y_l^m(θ, φ).
    The angular Laplacian is the same in flat and hyperbolic 3-space.
    """
    return sph_harm_y(ell, m, theta, phi_angle)


def orbital_density(rho: float, theta: float, phi_angle: float, ell: int, m: int, n_radial: int = 1) -> float:
    """
    Probability density |ψ|² × hyperbolic volume element sinh²(ρ).

    The sinh²(ρ) factor replaces the r² factor from flat space —
    it grows exponentially, packing more nodes into outer shells
    than a flat-space atom would have.
    """
    R = radial_wavefunction(rho, ell, n_radial)
    Y = angular_wavefunction(theta, phi_angle, ell, m)
    volume_element = math.sinh(rho) ** 2 if rho > 0 else 0.0
    return (R * abs(Y)) ** 2 * volume_element


# ── Sacred Egg node positions ─────────────────────────────────────────────────


def sacred_egg_nodes(tongue_idx: int) -> List[Tuple[float, float, float]]:
    """
    21 Sacred Egg positions on the surface of seed sphere `tongue_idx`.

    Distributed as a Fibonacci lattice on the unit sphere, then scaled
    to the Poincaré-ball radius of that tongue.  Each node is a
    quantisation anchor — a point where the radial wavefunction has a
    standing-wave node (R(ρ_node) ≈ 0 for n_radial ≥ 2).

    Returns list of (x, y, z) Euclidean coordinates inside the Poincaré ball.
    """
    r = phi_to_poincare_r(tongue_idx)
    nodes = []
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))  # Fibonacci golden angle
    for i in range(_SACRED_EGG_COUNT):
        y = 1.0 - (2.0 * i / (_SACRED_EGG_COUNT - 1))
        radius_2d = math.sqrt(max(0.0, 1.0 - y * y))
        theta_egg = golden_angle * i
        x = math.cos(theta_egg) * radius_2d
        z = math.sin(theta_egg) * radius_2d
        nodes.append((r * x, r * y, r * z))
    return nodes


# ── GeoSeedOrbital dataclass ──────────────────────────────────────────────────


@dataclass
class GeoSeedOrbital:
    """One orbital shell — one tongue, one l, one Poincaré-ball depth."""

    tongue: str
    abbr: str
    n_phi: int  # phi-weight index (0..5)
    weight: float  # φⁿ
    l: int  # angular momentum
    poincare_r: float  # Euclidean radius in Poincaré ball
    hyperbolic_rho: float  # ρ = n·ln(φ)  (hyperbolic distance from centre)
    lb_eigenvalue: float  # Laplace-Beltrami eigenvalue
    m_states: int  # 2l+1 magnetic sub-states
    egg_nodes: List[Tuple[float, float, float]] = field(repr=False)

    @property
    def orbital_name(self) -> str:
        return ["s", "p", "d", "f", "g", "h"][self.l]

    @property
    def orbital_type(self) -> str:
        """Spectroscopic shell letter (s/p/d/f/g/h) — alias of `orbital_name`."""
        return self.orbital_name

    @property
    def phi_index(self) -> int:
        """Phi-weight ladder index (0..5) — alias of `n_phi`."""
        return self.n_phi

    def peak_density(self, m: int = 0) -> float:
        """Density at the radial peak (θ=π/2, φ=0, ρ=hyperbolic_rho)."""
        return orbital_density(self.hyperbolic_rho, math.pi / 2, 0.0, self.l, m)

    def radial_profile(self, n_points: int = 64) -> Tuple[np.ndarray, np.ndarray]:
        """Sample radial wavefunction R(ρ) from 0 to 3·hyperbolic_rho."""
        rho_max = max(3.0 * self.hyperbolic_rho, 1.0)
        rhos = np.linspace(1e-6, rho_max, n_points)
        R = np.array([radial_wavefunction(float(r), self.l) for r in rhos])
        return rhos, R

    def density_profile(self, n_points: int = 64) -> List[dict]:
        """
        Relative radial probability density |R(ρ)|² · sinh²(ρ) sampled along ρ.

        Normalised to a per-shell peak of 1.0 so the six shells can be
        plotted on a shared axis despite the exponential sinh²(ρ) growth.
        Returns a list of ``{"rho": float, "density": float}`` points.
        """
        rhos, R = self.radial_profile(n_points)
        densities = (R**2) * (np.sinh(rhos) ** 2)
        peak = float(densities.max())
        if peak > 0.0:
            densities = densities / peak
        return [{"rho": float(rho), "density": float(d)} for rho, d in zip(rhos, densities)]

    def to_dict(self) -> dict:
        return {
            "tongue": self.tongue,
            "abbr": self.abbr,
            "phi_index": self.n_phi,
            "phi_weight": round(self.weight, 6),
            "angular_momentum_l": self.l,
            "orbital_type": self.orbital_name,
            "poincare_r": round(self.poincare_r, 6),
            "hyperbolic_rho": round(self.hyperbolic_rho, 6),
            "lb_eigenvalue": self.lb_eigenvalue,
            "m_states": self.m_states,
            "egg_node_count": len(self.egg_nodes),
            "peak_density": round(self.peak_density(), 8),
        }


# ── Build the 6-orbital system ────────────────────────────────────────────────


def build_geoseed_orbitals() -> List[GeoSeedOrbital]:
    """Construct all 6 GeoSeed hyperbolic orbital shells."""
    orbitals = []
    for t in TONGUES:
        n = t["n"]
        ell = t["l"]
        rho = n * math.log(PHI)
        r = phi_to_poincare_r(n)
        orbitals.append(
            GeoSeedOrbital(
                tongue=t["name"],
                abbr=t["abbr"],
                n_phi=n,
                weight=t["weight"],
                l=ell,
                poincare_r=r,
                hyperbolic_rho=rho,
                lb_eigenvalue=laplace_beltrami_eigenvalue(ell),
                m_states=2 * ell + 1,
                egg_nodes=sacred_egg_nodes(n),
            )
        )
    return orbitals


# ── Inter-shell coupling ───────────────────────────────────────────────────────


def inter_shell_geodesic(orbitals: Optional[List[GeoSeedOrbital]] = None) -> List[dict]:
    """
    Geodesic distances between adjacent shells.

    In the Saturn Ring Stabilizer model, energy transfers between
    shells along these geodesics — shorter geodesic = stronger coupling.

    When `orbitals` is omitted, the canonical 6-shell system is built.
    """
    if orbitals is None:
        orbitals = build_geoseed_orbitals()
    gaps = []
    for i in range(len(orbitals) - 1):
        a, b = orbitals[i], orbitals[i + 1]
        d = hyperbolic_distance(a.poincare_r, b.poincare_r)
        gaps.append(
            {
                "from": a.abbr,
                "to": b.abbr,
                "from_l": a.l,
                "to_l": b.l,
                "geodesic_distance": round(d, 6),
                "phi_ratio": round(b.weight / a.weight, 6),
            }
        )
    return gaps


# ── Summary / entrypoint ──────────────────────────────────────────────────────


def orbital_summary(include_profiles: bool = False) -> dict:
    """
    Full model summary — orbitals, inter-shell gaps, golden-ratio checkpoint.

    With `include_profiles=True`, a `density_profiles` map (tongue abbr →
    sampled relative-density points) is added for visual reporting.
    """
    orbitals = build_geoseed_orbitals()
    gaps = inter_shell_geodesic(orbitals)

    # The CA tongue (n=3) sits at r = 1/φ — verify
    ca = orbitals[3]
    golden_deviation = abs(ca.poincare_r - 1.0 / PHI)
    golden_checkpoint = golden_deviation < 1e-9

    # All adjacent shells are separated by the same hyperbolic step ln(φ)
    raw_gaps = [hyperbolic_distance(a.poincare_r, b.poincare_r) for a, b in zip(orbitals, orbitals[1:])]

    summary = {
        "schema_version": "geoseed_orbital_v1",
        "phi": PHI,
        "manifold": "Poincare_ball_H3",
        "model_scope": (
            "Structural analogy on the Poincare ball (H3): the six Sacred Tongue "
            "phi-shells inherit the s/p/d/f/g/h quantisation ladder from the "
            "Laplace-Beltrami spectrum. This is a governance-geometry model, "
            "not a physical atomic-orbital claim."
        ),
        "golden_ratio_checkpoint": {
            "tongue": "Cassisivadan (CA)",
            "l": 3,
            "poincare_r": round(ca.poincare_r, 9),
            "expected_1_over_phi": round(1.0 / PHI, 9),
            "exact": golden_checkpoint,
            "exact_within_1e_12": golden_deviation < 1e-12,
        },
        "uniform_gap": {
            "hyperbolic_distance": round(raw_gaps[0], 9),
            "expected_ln_phi": round(math.log(PHI), 9),
            "uniform": (max(raw_gaps) - min(raw_gaps)) < 1e-9,
        },
        "orbitals": [o.to_dict() for o in orbitals],
        "inter_shell_gaps": gaps,
        "total_m_states": sum(o.m_states for o in orbitals),
        "note": (
            "Total magnetic sub-states across 6 tongues = "
            + str(sum(o.m_states for o in orbitals))
            + " (= 1+3+5+7+9+11). "
            "The f-block (CA, l=3) anchors at r=1/phi in the Poincare ball."
        ),
    }
    if include_profiles:
        summary["density_profiles"] = {o.abbr: o.density_profile() for o in orbitals}
    return summary


def main():
    import json

    summary = orbital_summary()
    print(json.dumps(summary, indent=2))

    # Print compact table
    print("\n── GeoSeed Hyperbolic Orbitals ────────────────────────────────")
    print(
        f"{'Tongue':<15} {'Abbr':<5} {'l':<4} {'Type':<5} {'φⁿ':<8} "
        f"{'r (ball)':<10} {'ρ (hyp)':<10} {'LB λ':<8} {'m-states'}"
    )
    print("-" * 75)
    for o in build_geoseed_orbitals():
        print(
            f"{o.tongue:<15} {o.abbr:<5} {o.l:<4} {o.orbital_name:<5} "
            f"{o.weight:<8.3f} {o.poincare_r:<10.6f} {o.hyperbolic_rho:<10.6f} "
            f"{o.lb_eigenvalue:<8.0f} {o.m_states}"
        )
    print("-" * 75)
    print(f"  CA (l=3) sits at r = {build_geoseed_orbitals()[3].poincare_r:.9f}")
    print(f"  1/φ          =    {1 / PHI:.9f}  ← exact match")


if __name__ == "__main__":
    main()
