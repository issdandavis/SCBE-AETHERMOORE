"""GeoSeed orbital-shell model for the six Sacred Tongues.

This module is a deterministic geometry model, not a claim that SCBE models
actual electron orbitals. It maps the six tongue anchors onto a Poincare-ball
phi ladder and then annotates each shell with the familiar orbital sequence
s/p/d/f/g/h. The useful invariant is structural: adjacent phi shells are
uniformly spaced in hyperbolic distance while their Euclidean radii compress
toward the boundary.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any

PHI = (1.0 + math.sqrt(5.0)) / 2.0
SACRED_EGG_COUNT = 21

TONGUES: tuple[dict[str, Any], ...] = (
    {"name": "Kor'aelin", "abbr": "KO", "phi_index": 0, "l": 0, "orbital": "s"},
    {"name": "Avali", "abbr": "AV", "phi_index": 1, "l": 1, "orbital": "p"},
    {"name": "Runethic", "abbr": "RU", "phi_index": 2, "l": 2, "orbital": "d"},
    {"name": "Cassisivadan", "abbr": "CA", "phi_index": 3, "l": 3, "orbital": "f"},
    {"name": "Umbroth", "abbr": "UM", "phi_index": 4, "l": 4, "orbital": "g"},
    {"name": "Draumric", "abbr": "DR", "phi_index": 5, "l": 5, "orbital": "h"},
)


def phi_to_hyperbolic_rho(phi_index: int) -> float:
    """Map phi index n to hyperbolic radial depth rho = n * ln(phi)."""

    if phi_index < 0:
        raise ValueError("phi_index must be non-negative")
    return float(phi_index) * math.log(PHI)


def phi_to_poincare_r(phi_index: int) -> float:
    """Map phi index n to Euclidean radius inside the Poincare ball.

    The Poincare radial coordinate is r = tanh(rho / 2). For n=3, this
    simplifies to 1 / phi, which is the Cassisivadan f-shell checkpoint.
    """

    return math.tanh(phi_to_hyperbolic_rho(phi_index) / 2.0)


def hyperbolic_distance(r1: float, r2: float) -> float:
    """Collinear geodesic distance between two Poincare-ball radii."""

    if not (0.0 <= r1 < 1.0 and 0.0 <= r2 < 1.0):
        raise ValueError("Poincare radii must be in [0, 1)")
    numerator = abs(r1 - r2)
    denominator = 1.0 - r1 * r2
    if numerator == 0.0:
        return 0.0
    return 2.0 * math.atanh(numerator / denominator)


def laplace_beltrami_shell_value(l_value: int) -> float:
    """Simple shell label derived from the hyperbolic angular ladder.

    Full hyperbolic Schrodinger problems require a Hamiltonian and boundary
    conditions. For this model, -(l+1)^2 is only a stable shell label for the
    Laplace-Beltrami analogy, not a physical energy prediction.
    """

    if l_value < 0:
        raise ValueError("l_value must be non-negative")
    return -float((l_value + 1) ** 2)


def radial_standing_wave(rho: float, l_value: int, radial_mode: int = 1) -> float:
    """Dependency-free standing-wave proxy on a hyperbolic radial coordinate."""

    if rho < 0.0:
        raise ValueError("rho must be non-negative")
    if radial_mode < 1:
        raise ValueError("radial_mode must be at least 1")
    if rho == 0.0 and l_value > 0:
        return 0.0

    envelope = (math.sinh(rho) ** l_value) * math.exp(-rho / (l_value + radial_mode))
    oscillation = math.sin(radial_mode * math.pi * rho / (rho + 1.0))
    return envelope * oscillation


def radial_density(rho: float, l_value: int, radial_mode: int = 1) -> float:
    """Density proxy including the H3 volume element sinh(rho)^2."""

    wave = radial_standing_wave(rho, l_value, radial_mode)
    volume = math.sinh(rho) ** 2
    return wave * wave * volume


def sacred_egg_nodes(phi_index: int, count: int = SACRED_EGG_COUNT) -> list[tuple[float, float, float]]:
    """Return deterministic Fibonacci-lattice nodes on a shell sphere."""

    if count < 2:
        raise ValueError("count must be at least 2")
    radius = phi_to_poincare_r(phi_index)
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    nodes: list[tuple[float, float, float]] = []
    for index in range(count):
        y = 1.0 - (2.0 * index / (count - 1))
        ring_radius = math.sqrt(max(0.0, 1.0 - y * y))
        theta = golden_angle * index
        x = math.cos(theta) * ring_radius
        z = math.sin(theta) * ring_radius
        nodes.append((radius * x, radius * y, radius * z))
    return nodes


@dataclass(frozen=True)
class GeoSeedOrbital:
    """One tongue shell in the GeoSeed orbital analogy."""

    tongue: str
    abbr: str
    phi_index: int
    phi_weight: float
    l_value: int
    orbital_type: str
    poincare_r: float
    hyperbolic_rho: float
    shell_value: float
    m_states: int
    egg_nodes: tuple[tuple[float, float, float], ...] = field(repr=False)

    def density_profile(self, samples: int = 32, radial_mode: int = 1) -> list[dict[str, float]]:
        """Sample a compact radial density profile for visualization."""

        if samples < 2:
            raise ValueError("samples must be at least 2")
        rho_max = max(self.hyperbolic_rho * 3.0, 1.0)
        profile: list[dict[str, float]] = []
        for index in range(samples):
            rho = rho_max * index / (samples - 1)
            profile.append(
                {
                    "rho": round(rho, 9),
                    "density": round(radial_density(rho, self.l_value, radial_mode), 12),
                }
            )
        return profile

    def to_dict(self) -> dict[str, Any]:
        return {
            "tongue": self.tongue,
            "abbr": self.abbr,
            "phi_index": self.phi_index,
            "phi_weight": round(self.phi_weight, 9),
            "l": self.l_value,
            "orbital_type": self.orbital_type,
            "poincare_r": round(self.poincare_r, 9),
            "hyperbolic_rho": round(self.hyperbolic_rho, 9),
            "shell_value": self.shell_value,
            "m_states": self.m_states,
            "egg_node_count": len(self.egg_nodes),
        }


def build_geoseed_orbitals() -> list[GeoSeedOrbital]:
    """Construct the six GeoSeed orbital shells."""

    orbitals: list[GeoSeedOrbital] = []
    for tongue in TONGUES:
        phi_index = int(tongue["phi_index"])
        l_value = int(tongue["l"])
        rho = phi_to_hyperbolic_rho(phi_index)
        radius = phi_to_poincare_r(phi_index)
        orbitals.append(
            GeoSeedOrbital(
                tongue=str(tongue["name"]),
                abbr=str(tongue["abbr"]),
                phi_index=phi_index,
                phi_weight=PHI**phi_index,
                l_value=l_value,
                orbital_type=str(tongue["orbital"]),
                poincare_r=radius,
                hyperbolic_rho=rho,
                shell_value=laplace_beltrami_shell_value(l_value),
                m_states=2 * l_value + 1,
                egg_nodes=tuple(sacred_egg_nodes(phi_index)),
            )
        )
    return orbitals


def inter_shell_geodesic(orbitals: list[GeoSeedOrbital] | None = None) -> list[dict[str, Any]]:
    """Return adjacent shell distances and phi ratios."""

    shells = orbitals or build_geoseed_orbitals()
    gaps: list[dict[str, Any]] = []
    for left, right in zip(shells, shells[1:]):
        gaps.append(
            {
                "from": left.abbr,
                "to": right.abbr,
                "geodesic_distance": round(hyperbolic_distance(left.poincare_r, right.poincare_r), 9),
                "expected_ln_phi": round(math.log(PHI), 9),
                "phi_ratio": round(right.phi_weight / left.phi_weight, 9),
            }
        )
    return gaps


def orbital_summary(include_profiles: bool = False) -> dict[str, Any]:
    """Build a JSON-serializable summary of the GeoSeed orbital model."""

    orbitals = build_geoseed_orbitals()
    ca = orbitals[3]
    result: dict[str, Any] = {
        "schema_version": "geoseed_orbital_v1",
        "model_scope": "structural analogy; not a physical atomic-orbital claim",
        "manifold": "Poincare_ball_H3",
        "phi": round(PHI, 12),
        "uniform_gap": {
            "hyperbolic_distance": round(math.log(PHI), 9),
            "reason": "rho(n+1)-rho(n) = ln(phi)",
        },
        "golden_ratio_checkpoint": {
            "tongue": "Cassisivadan",
            "abbr": "CA",
            "poincare_r": round(ca.poincare_r, 9),
            "expected_1_over_phi": round(1.0 / PHI, 9),
            "exact_within_1e_12": abs(ca.poincare_r - (1.0 / PHI)) < 1e-12,
        },
        "orbitals": [orbital.to_dict() for orbital in orbitals],
        "inter_shell_gaps": inter_shell_geodesic(orbitals),
        "total_m_states": sum(orbital.m_states for orbital in orbitals),
    }
    if include_profiles:
        result["density_profiles"] = {
            orbital.abbr: orbital.density_profile(samples=32, radial_mode=2) for orbital in orbitals
        }
    return result


def main() -> None:
    """Print the model summary as JSON."""

    print(json.dumps(orbital_summary(include_profiles=True), indent=2))


if __name__ == "__main__":
    main()
