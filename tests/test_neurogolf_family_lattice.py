from __future__ import annotations

import json

from src.neurogolf.arc_io import load_arc_task
from src.neurogolf.family_lattice import (
    FAMILY_TOPOLOGIES,
    FLAT_FAMILY_ORDER,
    rank_families_by_charge_path,
    rank_families_by_lattice,
    task_topology,
)


def _write_task(tmp_path, name: str, payload: dict) -> object:
    task_path = tmp_path / f"{name}.json"
    task_path.write_text(json.dumps(payload), encoding="utf-8")
    return load_arc_task(task_path)


def test_family_topologies_cover_current_solver_order():
    assert set(FAMILY_TOPOLOGIES) == set(FLAT_FAMILY_ORDER)


def test_color_remap_task_ranks_color_family_near_top(tmp_path):
    task = _write_task(
        tmp_path,
        "color_remap",
        {
            "train": [
                {"input": [[1, 2], [2, 1]], "output": [[3, 4], [4, 3]]},
                {"input": [[2, 1]], "output": [[4, 3]]},
            ],
            "test": [{"input": [[1, 2]]}],
        },
    )

    lattice = rank_families_by_lattice(task)
    charge = rank_families_by_charge_path(task)

    assert "color_remap" in lattice[:3]
    assert "color_remap" in charge[:5]


def test_tile_self_task_ranks_tile_self_first(tmp_path):
    task = _write_task(
        tmp_path,
        "tile_self",
        {
            "train": [
                {
                    "input": [[1, 0], [0, 1]],
                    "output": [
                        [1, 0, 0, 0],
                        [0, 1, 0, 0],
                        [0, 0, 1, 0],
                        [0, 0, 0, 1],
                    ],
                }
            ],
            "test": [{"input": [[1, 0], [0, 1]]}],
        },
    )

    topology = task_topology(task)
    lattice = rank_families_by_lattice(task)
    charge = rank_families_by_charge_path(task)

    assert topology[0] > 0.9
    assert topology[4] > 0.9
    assert lattice[0] == "tile_self"
    assert charge[0] == "tile_self"


def test_shift_then_color_remap_prefers_composed_family(tmp_path):
    task = _write_task(
        tmp_path,
        "shift_then_color_remap",
        {
            "train": [
                {
                    "input": [[1, 0, 0], [0, 2, 0], [0, 0, 0]],
                    "output": [[0, 0, 0], [5, 0, 0], [0, 6, 0]],
                }
            ],
            "test": [{"input": [[1, 0, 0], [0, 2, 0], [0, 0, 0]]}],
        },
    )

    topology = task_topology(task)
    lattice = rank_families_by_lattice(task)
    charge = rank_families_by_charge_path(task)

    assert topology[1] > 0.5
    assert topology[2] > 0.85
    assert topology[5] > 0.0
    assert lattice[:2] == ["multi_unique_color_shift", "shift_then_color_remap"]
    assert charge[0] == "shift_then_color_remap"
