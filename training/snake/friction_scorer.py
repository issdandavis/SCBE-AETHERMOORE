"""Stage 5: Friction Scoring — 198-dimension boundary friction vectors.

Computes friction at polyhedral boundaries. High friction = most informative
training signal. The geometry writes its own curriculum.

33 boundaries x 6 tongues = 198 friction training dimensions.
Friction = phi * |f_i - f_j| + harmonic_mean(f_i, f_j) + |chi_i - chi_j|/(edges_i + edges_j)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .config import PHI, TONGUES, TONGUE_WEIGHTS, FRICTION_DIMENSIONS, HIGH_FRICTION_THRESHOLD


# ---------------------------------------------------------------------------
# Polyhedral definitions (from polyhedral_flow.py concepts)
# ---------------------------------------------------------------------------

# The 8 shell polyhedra with their properties
POLYHEDRA = [
    {"name": "tetrahedron", "faces": 4, "edges": 6, "chi": 2, "type": "platonic"},
    {"name": "cube", "faces": 6, "edges": 12, "chi": 2, "type": "platonic"},
    {"name": "octahedron", "faces": 8, "edges": 12, "chi": 2, "type": "platonic"},
    {"name": "dodecahedron", "faces": 12, "edges": 30, "chi": 2, "type": "platonic"},
    {"name": "icosahedron", "faces": 20, "edges": 30, "chi": 2, "type": "platonic"},
    {"name": "truncated_icosahedron", "faces": 32, "edges": 90, "chi": 2, "type": "archimedean"},
    {"name": "torus", "faces": 0, "edges": 0, "chi": 0, "type": "toroidal"},
    {"name": "star", "faces": 60, "edges": 90, "chi": 2, "type": "kepler-poinsot"},
]


def _natural_frequency(poly: dict, depth: int = 1) -> float:
    """Compute natural frequency of a polyhedron.

    f_i = phi^(depth*5) * |faces/chi| * (1/edges)
    For toroidal (chi=0): use chi=0.001 to avoid division by zero
    """
    faces = poly["faces"] or 1
    edges = poly["edges"] or 1
    chi = poly["chi"] or 0.001

    return (PHI ** (depth * 5)) * abs(faces / chi) * (1.0 / edges)


def _boundary_friction(poly_a: dict, poly_b: dict) -> float:
    """Compute friction at boundary between two polyhedra.

    friction = phi * |f_a - f_b| + harmonic_mean(f_a, f_b)
               + |chi_a - chi_b| / (edges_a + edges_b)
    """
    f_a = _natural_frequency(poly_a)
    f_b = _natural_frequency(poly_b)

    freq_diff = PHI * abs(f_a - f_b)
    harmonic = 2 * f_a * f_b / (f_a + f_b + 1e-10)
    chi_term = abs((poly_a["chi"] or 0.001) - (poly_b["chi"] or 0.001)) / (
        (poly_a["edges"] or 1) + (poly_b["edges"] or 1)
    )

    return freq_diff + harmonic + chi_term


@dataclass
class FrictionResult:
    """Output of friction scoring."""

    friction_vector: list[float]  # 198-dim (33 boundaries x 6 tongues)
    boundary_crossings: list[dict[str, Any]]  # Which boundaries the record crosses
    geometric_loss: float  # L_geometry contribution
    max_friction: float  # Peak friction value
    friction_distribution: str  # "low" | "medium" | "high"

    def to_dict(self) -> dict[str, Any]:
        return {
            "friction_vector": self.friction_vector,
            "boundary_crossings": self.boundary_crossings,
            "geometric_loss": self.geometric_loss,
            "max_friction": self.max_friction,
            "friction_distribution": self.friction_distribution,
        }


def score(
    tongue_profile: dict[str, float],
    poincare_point: list[float] | None = None,
) -> FrictionResult:
    """Compute 198-dimensional friction vector for a record.

    Each of the 33 polyhedral boundaries is scored for each of the 6 tongues,
    weighted by the record's tongue activation at that dimension.

    High friction = high training signal = the geometry's curriculum.
    """
    # Compute all boundary frictions (C(8,2) = 28, plus 5 self-boundaries = 33)
    boundaries = []
    for i in range(len(POLYHEDRA)):
        for j in range(i + 1, len(POLYHEDRA)):
            friction = _boundary_friction(POLYHEDRA[i], POLYHEDRA[j])
            boundaries.append({
                "a": POLYHEDRA[i]["name"],
                "b": POLYHEDRA[j]["name"],
                "friction": friction,
            })
    # Add self-boundaries (reflection friction)
    for poly in POLYHEDRA[:5]:  # Only Platonic solids have self-reflection
        self_friction = _natural_frequency(poly) * PHI * 0.1  # Small self-term
        boundaries.append({
            "a": poly["name"],
            "b": poly["name"] + "_reflected",
            "friction": self_friction,
        })

    # Trim/pad to exactly 33 boundaries
    boundaries = boundaries[:33]
    while len(boundaries) < 33:
        boundaries.append({"a": "pad", "b": "pad", "friction": 0.0})

    # Build 198-dim friction vector: 33 boundaries x 6 tongues
    friction_vector = []
    for boundary in boundaries:
        base_friction = boundary["friction"]
        for tongue in TONGUES:
            # Weight by tongue activation and phi-scaled tongue weight
            activation = tongue_profile.get(tongue, 0.0)
            weighted_friction = base_friction * activation * TONGUE_WEIGHTS[tongue]
            friction_vector.append(round(weighted_friction, 8))

    # Identify high-friction boundary crossings
    crossings = []
    for i, boundary in enumerate(boundaries):
        if boundary["friction"] > HIGH_FRICTION_THRESHOLD:
            crossings.append({
                "boundary": f"{boundary['a']}↔{boundary['b']}",
                "friction": round(boundary["friction"], 6),
                "index": i,
            })

    # Geometric loss: L_geometry = ||friction_predicted - friction_actual||^2
    # For training, this is the ACTUAL friction (the target)
    geometric_loss = sum(f * f for f in friction_vector)
    geometric_loss = round(math.sqrt(geometric_loss), 6)

    # Max friction and distribution
    max_friction = max(friction_vector) if friction_vector else 0.0

    if max_friction > HIGH_FRICTION_THRESHOLD:
        distribution = "high"
    elif max_friction > HIGH_FRICTION_THRESHOLD / 2:
        distribution = "medium"
    else:
        distribution = "low"

    return FrictionResult(
        friction_vector=friction_vector,
        boundary_crossings=crossings,
        geometric_loss=geometric_loss,
        max_friction=round(max_friction, 6),
        friction_distribution=distribution,
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_profile = {"KO": 0.05, "AV": 0.10, "RU": 0.15, "CA": 0.20, "UM": 0.35, "DR": 0.15}

    result = score(test_profile)

    print("Friction Scorer")
    print(f"  Vector dims:    {len(result.friction_vector)} (expected {FRICTION_DIMENSIONS})")
    print(f"  Geometric loss: {result.geometric_loss}")
    print(f"  Max friction:   {result.max_friction}")
    print(f"  Distribution:   {result.friction_distribution}")
    print(f"  Crossings:      {len(result.boundary_crossings)}")
    for c in result.boundary_crossings[:5]:
        print(f"    {c['boundary']}: {c['friction']}")
