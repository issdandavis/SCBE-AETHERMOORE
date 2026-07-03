"""Bhargava-cube overlay for the Machine Crystal.

Manjul Bhargava's cube law places eight integers on the corners of a 2x2x2
cube. From the three pairs of opposite faces, it constructs three binary
quadratic forms with the same discriminant.

This module applies the *discriminant overlay* to the Machine Crystal's
8-address cube/octahedron object. It does not implement Gauss composition or
class-group arithmetic. It only validates the load-bearing invariant we can
compute locally:

    one 8-corner cube -> three forms -> equal discriminants
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from math import gcd
from pathlib import Path
from typing import Iterable

from .machine_crystal_dual import DualVertex, duality_receipt


class BhargavaCrystalError(ValueError):
    """Invalid Bhargava cube data."""


def _det2(m: tuple[tuple[int, int], tuple[int, int]]) -> int:
    return m[0][0] * m[1][1] - m[0][1] * m[1][0]


@dataclass(frozen=True, slots=True)
class BinaryQuadraticForm:
    """Integer binary quadratic form ax^2 + bxy + cy^2."""

    a: int
    b: int
    c: int
    axis: str

    def discriminant(self) -> int:
        return self.b * self.b - 4 * self.a * self.c

    def primitive_gcd(self) -> int:
        return gcd(gcd(abs(self.a), abs(self.b)), abs(self.c))

    def packet(self) -> dict:
        return {
            "axis": self.axis,
            "coefficients": {"a": self.a, "b": self.b, "c": self.c},
            "discriminant": self.discriminant(),
            "primitive_gcd": self.primitive_gcd(),
        }


@dataclass(frozen=True, slots=True)
class BhargavaCube:
    """Eight cube-corner integer entries ordered by Machine Crystal index 0..7."""

    entries: tuple[int, int, int, int, int, int, int, int]

    @classmethod
    def from_iterable(cls, values: Iterable[int]) -> "BhargavaCube":
        vals = tuple(int(v) for v in values)
        if len(vals) != 8:
            raise BhargavaCrystalError("Bhargava cube requires exactly 8 integers")
        return cls(vals)  # type: ignore[arg-type]

    @classmethod
    def machine_index_cube(cls) -> "BhargavaCube":
        """The simplest Machine Crystal overlay: entries are indices 0..7."""

        return cls(tuple(range(8)))  # type: ignore[arg-type]

    def forms(self) -> tuple[BinaryQuadraticForm, BinaryQuadraticForm, BinaryQuadraticForm]:
        """Return Bhargava's three binary quadratic forms.

        Entry naming follows the standard cube notation:

            a b
            c d

            e f
            g h

        Q_i = -det(M_i x + N_i y), so coefficients are
        (-det(M_i), -cross_i, -det(N_i)).
        """

        a, b, c, d, e, f, g, h = self.entries
        m1 = ((a, b), (c, d))
        n1 = ((e, f), (g, h))
        m2 = ((a, c), (e, g))
        n2 = ((b, d), (f, h))
        m3 = ((a, e), (b, f))
        n3 = ((c, g), (d, h))

        q1_cross = a * h + e * d - b * g - f * c
        q2_cross = a * h + b * g - f * c - e * d
        q3_cross = a * h + f * c - e * d - b * g

        return (
            BinaryQuadraticForm(-_det2(m1), -q1_cross, -_det2(n1), "axis_1_abcd_efgh"),
            BinaryQuadraticForm(-_det2(m2), -q2_cross, -_det2(n2), "axis_2_aceg_bdfh"),
            BinaryQuadraticForm(-_det2(m3), -q3_cross, -_det2(n3), "axis_3_aebf_cgdh"),
        )

    def discriminants(self) -> tuple[int, int, int]:
        return tuple(form.discriminant() for form in self.forms())

    def equal_discriminants(self) -> bool:
        d1, d2, d3 = self.discriminants()
        return d1 == d2 == d3

    def packet(self) -> dict:
        return {
            "entries_by_machine_index": list(self.entries),
            "vertices": [
                {
                    **DualVertex(index).packet(),
                    "bhargava_entry": self.entries[index],
                }
                for index in range(8)
            ],
            "forms": [form.packet() for form in self.forms()],
            "equal_discriminants": self.equal_discriminants(),
        }


def _deterministic_cube(seed: int) -> BhargavaCube:
    values = []
    for i in range(8):
        # Small signed deterministic values; avoids randomness in receipts.
        values.append(((seed + 3) * (i + 1) + seed * seed + 2 * i * i) % 23 - 11)
    return BhargavaCube.from_iterable(values)


def bhargava_crystal_receipt(case_count: int = 128) -> dict:
    """Benchmark the equal-discriminant invariant across deterministic cubes."""

    machine_cube = BhargavaCube.machine_index_cube()
    cases = []
    failures = []
    for seed in range(case_count):
        cube = _deterministic_cube(seed)
        ok = cube.equal_discriminants()
        item = {
            "seed": seed,
            "entries": list(cube.entries),
            "discriminants": list(cube.discriminants()),
            "ok": ok,
        }
        cases.append(item)
        if not ok:
            failures.append(item)

    bridge = duality_receipt()
    checks = {
        "machine_cube_equal_discriminants": machine_cube.equal_discriminants(),
        "case_count": len(cases) == case_count,
        "all_cases_equal_discriminants": len(failures) == 0,
        "dual_bridge_passes": bridge["verdict"] == "PASS",
    }
    return {
        "schema": "scbe_machine_crystal_bhargava_overlay_v1",
        "claim": "Machine Crystal's 8-address cube can carry Bhargava-cube integer overlays; the three associated binary quadratic forms have equal discriminants.",
        "machine_index_cube": machine_cube.packet(),
        "case_count": case_count,
        "failures": failures,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
    }


def main() -> int:
    receipt = bhargava_crystal_receipt()
    out_dir = Path("artifacts/machine_crystal")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "bhargava_cube_overlay.json"
    out_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["verdict"] == "PASS" else 1


__all__ = [
    "BhargavaCrystalError",
    "BhargavaCube",
    "BinaryQuadraticForm",
    "bhargava_crystal_receipt",
]


if __name__ == "__main__":
    raise SystemExit(main())
