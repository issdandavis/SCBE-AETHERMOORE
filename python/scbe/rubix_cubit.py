#!/usr/bin/env python3
"""rubix_cubit.py

Deterministic 4D CodeCube / Tesseract / Rubix-Cubit primitive.

- CodeCube : a software planning cube (the idea).
- Tesseract: 4D state container, 16 vertices in {-1, +1}^4.
- Rubix    : twist operations = controlled, auditable transforms.
- Cubit    : the smallest addressable code-state unit (one tesseract vertex).

Concretely:
- 16 vertices of a tesseract: coordinates in {-1, +1}^4.
- 8 cubic cells / faces: x+, x-, y+, y-, z+, z-, w+, w- (a vertex belongs to four).
- A "cubit" is one addressable code-state unit at a tesseract vertex.
- A "twist" is a signed coordinate-plane rotation (a quarter turn maps (a, b) -> (-b, a));
  because coordinates are only +/-1, every twist is an exact permutation of vertices.
- A "receipt" is the SHA-256 of the canonical cubit state — it proves exact state.

This is a software planning / governance primitive, not a physics claim.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Dict, Iterable, List, Literal, Tuple

Axis = Literal["x", "y", "z", "w"]
Sign = Literal[-1, 1]
Coord4 = Tuple[int, int, int, int]

AXES: Tuple[Axis, ...] = ("x", "y", "z", "w")
AXIS_INDEX: Dict[Axis, int] = {"x": 0, "y": 1, "z": 2, "w": 3}


@dataclass(frozen=True)
class Cubit:
    """One code-addressable unit at a tesseract vertex.

    coord:   one of the 16 tesseract vertices, e.g. (-1, +1, -1, +1)
    face:    the cell label this vertex sits on (frontend/backend/tests/deploy/core)
    payload: the content attached to this cubit (a task, a spec fragment, ...)
    role:    governance role for this cubit (e.g. empty, builder, verifier, gate)
    """

    coord: Coord4
    face: str
    payload: str
    role: str

    def canonical(self) -> Dict[str, Any]:
        return {
            "coord": list(self.coord),
            "face": self.face,
            "payload": self.payload,
            "role": self.role,
        }


class TesseractRubixCubit:
    """A 4D state container of 16 cubits.

    The important part:
    - geometry gives deterministic addressing (each cubit has an exact vertex),
    - twists give auditable transformations (signed-coordinate rotations / permutations),
    - receipts prove exact state (a hash anyone can recompute).
    """

    def __init__(self, cubits: Iterable[Cubit] | None = None) -> None:
        self.cubits: Dict[Coord4, Cubit] = {}
        if cubits is None:
            for coord in self.vertices():
                self.cubits[coord] = Cubit(
                    coord=coord,
                    face=self.cell_name(coord),
                    payload="",
                    role="empty",
                )
        else:
            for cubit in cubits:
                self.cubits[cubit.coord] = cubit
            missing = set(self.vertices()) - set(self.cubits)
            if missing:
                raise ValueError(f"missing cubits for coordinates: {sorted(missing)}")

    @staticmethod
    def vertices() -> List[Coord4]:
        out: List[Coord4] = []
        for x in (-1, 1):
            for y in (-1, 1):
                for z in (-1, 1):
                    for w in (-1, 1):
                        out.append((x, y, z, w))
        return out

    @staticmethod
    def cell_name(coord: Coord4) -> str:
        """A simple, deterministic default face/cell label for a vertex."""
        x, y, z, w = coord
        if w == 1:
            return "deploy"
        if z == 1:
            return "tests"
        if y == 1:
            return "backend"
        if x == 1:
            return "frontend"
        return "core"

    def set_cubit(self, coord: Coord4, *, payload: str, role: str) -> "TesseractRubixCubit":
        """Attach content/role to a vertex (returns self for chaining)."""
        if coord not in self.cubits:
            raise KeyError(f"not a tesseract vertex: {coord}")
        old = self.cubits[coord]
        self.cubits[coord] = Cubit(coord=coord, face=old.face, payload=payload, role=role)
        return self

    def to_dict(self) -> Dict[str, Any]:
        ordered = [self.cubits[c].canonical() for c in sorted(self.cubits)]
        return {
            "schema": "tesseract_rubix_cubit_v1",
            "vertices": 16,
            "axes": list(AXES),
            "cubits": ordered,
        }

    def receipt(self) -> str:
        blob = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return sha256(blob.encode("utf-8")).hexdigest()

    def twist(
        self,
        plane: Tuple[Axis, Axis],
        *,
        layer_axis: Axis | None = None,
        layer_sign: Sign | None = None,
        turns: int = 1,
    ) -> "TesseractRubixCubit":
        """Rotate cubits in a coordinate plane and return a NEW container.

        A quarter turn in plane (a, b) maps (coord[a], coord[b]) -> (-coord[b], coord[a]).
        Because coordinates are only +/-1, every twist is an exact permutation, so:
          - 4 quarter turns in the same plane = identity,
          - the inverse of `turns` is `-turns` (mod 4).

        Optionally restrict the twist to one layer: only cubits whose `layer_axis`
        coordinate equals `layer_sign` are rotated; the rest stay put.
        """
        a, b = plane
        if a == b:
            raise ValueError("plane axes must be different")
        if a not in AXIS_INDEX or b not in AXIS_INDEX:
            raise ValueError(f"plane axes must be in {AXES}, got {plane!r}")
        turns %= 4
        if turns == 0:
            return TesseractRubixCubit(self.cubits.values())

        ai, bi = AXIS_INDEX[a], AXIS_INDEX[b]
        layer_i = AXIS_INDEX[layer_axis] if layer_axis is not None else None

        moved: Dict[Coord4, Cubit] = {}
        for coord, cubit in self.cubits.items():
            in_layer = layer_i is None or coord[layer_i] == layer_sign
            if not in_layer:
                moved[coord] = cubit
                continue
            new = list(coord)
            for _ in range(turns):
                va, vb = new[ai], new[bi]
                new[ai], new[bi] = -vb, va
            new_coord: Coord4 = (new[0], new[1], new[2], new[3])
            moved[new_coord] = Cubit(
                coord=new_coord,
                face=self.cell_name(new_coord),
                payload=cubit.payload,
                role=cubit.role,
            )
        return TesseractRubixCubit(moved.values())


def _demo() -> int:
    cube = TesseractRubixCubit()
    cube.set_cubit((1, 1, 1, 1), payload="ship the release", role="gate")
    cube.set_cubit((-1, -1, -1, -1), payload="core invariant", role="verifier")
    before = cube.receipt()
    twisted = cube.twist(("x", "y"))
    once = twisted.receipt()
    full = cube.twist(("x", "y"), turns=4).receipt()
    print(f"vertices            : {len(cube.cubits)}")
    print(f"receipt (start)     : {before}")
    print(f"receipt (1 twist)   : {once}")
    print(f"1 twist changed it  : {once != before}")
    print(f"4 twists == identity: {full == before}")
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tesseract Rubix-Cubit: 4D code-state cube")
    parser.add_argument("--twist", help="comma plane, e.g. x,y", default=None)
    parser.add_argument("--turns", type=int, default=1)
    parser.add_argument("--layer-axis", default=None)
    parser.add_argument("--layer-sign", type=int, choices=[-1, 1], default=None)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    if args.twist is None and not args.as_json:
        return _demo()

    cube = TesseractRubixCubit()
    if args.twist:
        a, b = (s.strip() for s in args.twist.split(","))
        cube = cube.twist((a, b), layer_axis=args.layer_axis, layer_sign=args.layer_sign, turns=args.turns)
    if args.as_json:
        print(json.dumps({"receipt": cube.receipt(), **cube.to_dict()}, indent=2))
    else:
        print(cube.receipt())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
