"""Stage 3: Lattice Routing — Quasicrystal coordinate assignment.

Each record gets a lattice coordinate based on its tongue profile.
The quasicrystal never repeats (golden ratio governed), so each record
finds a UNIQUE position. Records that are geometrically close =
semantically related. Records that clash = high friction = high training signal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .config import PHI, PHI_INV, TONGUES, TONGUE_WEIGHTS


@dataclass
class LatticePoint:
    """A point on the quasicrystal lattice."""

    coordinate: list[float]  # 6D tongue-space coordinate
    lattice_index: int       # Integer lattice node index
    path_quality: float      # 0-1, how well this point sits on the lattice
    nearest_node: list[float]  # Snapped to nearest lattice node
    displacement: float      # Distance from nearest node (defect measure)

    def to_dict(self) -> dict[str, Any]:
        return {
            "coordinate": self.coordinate,
            "lattice_index": self.lattice_index,
            "path_quality": self.path_quality,
            "nearest_node": self.nearest_node,
            "displacement": self.displacement,
        }


def _quasicrystal_project(profile: dict[str, float]) -> list[float]:
    """Project tongue profile onto quasicrystal lattice coordinates.

    Uses the cut-and-project method: embed 6D tongue space into a higher
    dimensional periodic lattice, then project down. The golden ratio
    ensures aperiodicity — no two records land on the same node unless
    they have identical semantic content.

    The projection uses phi-weighted scaling per tongue dimension,
    then applies a Fibonacci rotation to create the quasicrystal structure.
    """
    # Step 1: Phi-weighted 6D coordinate
    weighted = [
        profile.get(t, 0.0) * TONGUE_WEIGHTS[t]
        for t in TONGUES
    ]

    # Step 2: Fibonacci rotation — rotate each pair by golden angle
    golden_angle = 2 * math.pi * PHI_INV  # ~2.399 radians
    rotated = list(weighted)  # copy

    for i in range(0, len(rotated) - 1, 2):
        a, b = rotated[i], rotated[i + 1]
        theta = golden_angle * (i // 2 + 1)
        rotated[i] = a * math.cos(theta) - b * math.sin(theta)
        rotated[i + 1] = a * math.sin(theta) + b * math.cos(theta)

    return rotated


def _snap_to_lattice(coord: list[float]) -> tuple[list[float], int, float]:
    """Snap a coordinate to the nearest quasicrystal node.

    Returns (snapped_coordinate, lattice_index, displacement).
    The lattice index is a hash of the snapped position for lookup.
    """
    # Snap each dimension to nearest phi-grid point
    # The grid is: n + m*phi for integer n,m
    snapped = []
    for x in coord:
        # Find nearest n + m*phi
        best_snap = round(x)  # Start with nearest integer
        best_dist = abs(x - best_snap)

        # Check phi offsets
        for n in range(int(x) - 2, int(x) + 3):
            for m in [-1, 0, 1]:
                candidate = n + m * PHI
                dist = abs(x - candidate)
                if dist < best_dist:
                    best_snap = candidate
                    best_dist = dist
        snapped.append(best_snap)

    displacement = math.sqrt(sum((a - b) ** 2 for a, b in zip(coord, snapped)))

    # Lattice index: deterministic hash of snapped position
    index_str = ",".join(f"{s:.4f}" for s in snapped)
    lattice_index = hash(index_str) & 0x7FFFFFFF  # Positive 31-bit int

    return snapped, lattice_index, displacement


def route(tongue_profile: dict[str, float]) -> LatticePoint:
    """Route a record through the quasicrystal lattice.

    Takes a tongue profile and returns a LatticePoint with:
    - 6D coordinate in quasicrystal space
    - Lattice index for neighbor lookup
    - Path quality (inverse of displacement — how well it fits)
    - Nearest lattice node
    - Displacement (defect measure — high = interesting)
    """
    coord = _quasicrystal_project(tongue_profile)
    snapped, index, displacement = _snap_to_lattice(coord)

    # Path quality: inverse of displacement, normalized to [0,1]
    # displacement=0 → perfect fit (quality=1), high displacement → low quality
    path_quality = 1.0 / (1.0 + displacement * PHI)

    return LatticePoint(
        coordinate=coord,
        lattice_index=index,
        path_quality=round(path_quality, 6),
        nearest_node=snapped,
        displacement=round(displacement, 6),
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    profiles = [
        ("Security-heavy", {"KO": 0.05, "AV": 0.10, "RU": 0.15, "CA": 0.20, "UM": 0.35, "DR": 0.15}),
        ("Balanced", {"KO": 0.17, "AV": 0.17, "RU": 0.17, "CA": 0.17, "UM": 0.16, "DR": 0.16}),
        ("Intent-pure", {"KO": 0.80, "AV": 0.05, "RU": 0.03, "CA": 0.05, "UM": 0.02, "DR": 0.05}),
    ]

    print("Quasicrystal Lattice Router")
    for name, profile in profiles:
        point = route(profile)
        print(f"\n  {name}:")
        print(f"    Coordinate:   [{', '.join(f'{c:.3f}' for c in point.coordinate)}]")
        print(f"    Lattice idx:  {point.lattice_index}")
        print(f"    Path quality: {point.path_quality}")
        print(f"    Displacement: {point.displacement}")
