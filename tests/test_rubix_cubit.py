"""Prove the Rubix-Cubit geometry: twists are exact permutations, receipts are
deterministic, and a full turn is the identity."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.rubix_cubit import TesseractRubixCubit  # noqa: E402


def test_sixteen_distinct_vertices() -> None:
    cube = TesseractRubixCubit()
    assert len(cube.cubits) == 16
    assert len(set(cube.cubits)) == 16
    assert all(all(c in (-1, 1) for c in coord) for coord in cube.cubits)


def test_receipt_is_deterministic() -> None:
    assert TesseractRubixCubit().receipt() == TesseractRubixCubit().receipt()


def test_one_twist_changes_state() -> None:
    cube = TesseractRubixCubit().set_cubit((1, 1, 1, 1), payload="x", role="gate")
    assert cube.twist(("x", "y")).receipt() != cube.receipt()


def test_four_quarter_turns_is_identity() -> None:
    cube = TesseractRubixCubit().set_cubit((1, 1, 1, 1), payload="x", role="gate")
    assert cube.twist(("x", "y"), turns=4).receipt() == cube.receipt()


def test_twist_is_a_permutation() -> None:
    cube = TesseractRubixCubit()
    twisted = cube.twist(("z", "w"))
    assert set(twisted.cubits) == set(cube.cubits)  # same 16 vertices, rearranged
    assert len(twisted.cubits) == 16


def test_inverse_twist_restores() -> None:
    cube = TesseractRubixCubit().set_cubit((-1, 1, -1, 1), payload="p", role="verifier")
    once = cube.twist(("x", "w"), turns=1)
    back = once.twist(("x", "w"), turns=3)  # -1 mod 4
    assert back.receipt() == cube.receipt()


def test_layer_twist_leaves_other_layer_fixed() -> None:
    cube = TesseractRubixCubit()
    twisted = cube.twist(("x", "y"), layer_axis="w", layer_sign=1)
    # w=-1 cubits must be untouched (same coord -> same face/payload/role)
    for coord, cubit in cube.cubits.items():
        if coord[3] == -1:
            assert twisted.cubits[coord] == cubit
