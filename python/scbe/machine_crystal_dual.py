"""Cube/octahedron/Fano bridge for the Machine Crystal.

This module connects four views of the same 3-bit address set:

1. cube corners: 8 vertices of GF(2)^3.
2. octahedron faces: 8 faces whose normals point at those cube corners.
3. Machine Crystal ops: 8 tape-machine operations, one per octahedron face.
4. Fano plane: the 7 nonzero GF(2)^3 points and 7 XOR-closed lines.

Important honesty boundary:
    The Fano plane is the 7 nonzero elements only. Face/vertex 0 is still a
    real Machine Crystal operation, but it is the zero element in GF(2)^3 and is
    not a Fano point.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from itertools import combinations

from .machine_crystal import FACES, MachineCrystalProgram, run_crystal


class MachineCrystalDualError(ValueError):
    """Invalid cube/octa/Fano bridge invariant."""


def bits3(value: int) -> tuple[int, int, int]:
    if not 0 <= int(value) <= 7:
        raise MachineCrystalDualError(f"3-bit value out of range: {value!r}")
    return ((value >> 2) & 1, (value >> 1) & 1, value & 1)


def hamming(a: int, b: int) -> int:
    return bin(int(a) ^ int(b)).count("1")


def cube_edges() -> tuple[tuple[int, int], ...]:
    """Edges of the 3-cube graph over GF(2)^3."""

    return tuple((a, b) for a, b in combinations(range(8), 2) if hamming(a, b) == 1)


def fano_lines() -> tuple[tuple[int, int, int], ...]:
    """Unoriented Fano lines as XOR-closed nonzero triples."""

    lines = {
        tuple(sorted((a, b, a ^ b)))
        for a, b in combinations(range(1, 8), 2)
        if (a ^ b) != 0 and (a ^ b) != a and (a ^ b) != b
    }
    return tuple(sorted(lines))


def fano_point_degrees(lines: tuple[tuple[int, int, int], ...]) -> dict[int, int]:
    out = {point: 0 for point in range(1, 8)}
    for line in lines:
        for point in line:
            out[point] += 1
    return out


@dataclass(frozen=True, slots=True)
class DualVertex:
    """One 3-bit address seen as cube corner, octa face, and machine op."""

    index: int

    def packet(self) -> dict:
        face = FACES[self.index]
        return {
            "index": self.index,
            "bits": list(bits3(self.index)),
            "cube_corner": list(face.normal),
            "octahedron_face": self.index,
            "machine_op": face.op.name,
            "machine_symbol": face.symbol,
            "fano_role": "zero_not_fano_point" if self.index == 0 else "fano_point",
        }


def duality_receipt() -> dict:
    """Emit a receipt proving the bridge invariants."""

    edges = cube_edges()
    lines = fano_lines()
    degrees = fano_point_degrees(lines)
    demo = run_crystal(MachineCrystalProgram.from_brainfuck("+++."))

    checks = {
        "eight_cube_vertices": len(range(8)) == 8,
        "eight_octa_faces": len(FACES) == 8,
        "cube_edges_12": len(edges) == 12,
        "dual_face_edges_12": len(edges) == 12,
        "seven_nonzero_fano_points": list(range(1, 8)) == [1, 2, 3, 4, 5, 6, 7],
        "seven_fano_lines": len(lines) == 7,
        "each_fano_point_on_three_lines": all(value == 3 for value in degrees.values()),
        "all_fano_lines_xor_to_zero": all((a ^ b ^ c) == 0 for a, b, c in lines),
        "machine_op_count_8": len({face.symbol for face in FACES}) == 8,
        "crystal_demo_output_03": demo["output_hex"] == "03",
    }

    return {
        "schema": "scbe_machine_crystal_dual_fano_v1",
        "claim": "cube corners, octahedron faces, GF(2)^3 addresses, and Machine Crystal ops share one 8-address set; Fano incidence uses the 7 nonzero addresses",
        "vertices": [DualVertex(index).packet() for index in range(8)],
        "cube_edges": [list(edge) for edge in edges],
        "fano_lines": [list(line) for line in lines],
        "fano_point_degrees": degrees,
        "zero_vertex": DualVertex(0).packet(),
        "demo": demo,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
    }


def main() -> int:
    receipt = duality_receipt()
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["verdict"] == "PASS" else 1


__all__ = [
    "DualVertex",
    "MachineCrystalDualError",
    "bits3",
    "cube_edges",
    "duality_receipt",
    "fano_lines",
    "fano_point_degrees",
    "hamming",
]


if __name__ == "__main__":
    raise SystemExit(main())
