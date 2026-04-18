from __future__ import annotations

import json

from src.neurogolf.arc_io import load_arc_task
from src.neurogolf.triadic_anchor import explain_anchors, extract_anchors, rank_families_by_anchor


def _write_task(tmp_path, name: str, payload: dict) -> object:
    task_path = tmp_path / f"{name}.json"
    task_path.write_text(json.dumps(payload), encoding="utf-8")
    return load_arc_task(task_path)


def test_extract_anchors_returns_stable_triplets_for_multi_example_task(tmp_path):
    task = _write_task(
        tmp_path,
        "tile_self_train",
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
                },
                {
                    "input": [[2, 0], [0, 2]],
                    "output": [
                        [2, 0, 0, 0],
                        [0, 2, 0, 0],
                        [0, 0, 2, 0],
                        [0, 0, 0, 2],
                    ],
                },
            ],
            "test": [{"input": [[1, 0], [0, 1]]}],
        },
    )

    anchors = extract_anchors(task)
    assert anchors
    assert all(anchor.stability >= 0.8 for anchor in anchors)
    assert all(all(sign != 0 for sign in anchor.sign_pattern) for anchor in anchors[:3])


def test_rank_families_by_anchor_puts_tile_self_first(tmp_path):
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

    ranked = rank_families_by_anchor(task)
    assert ranked[0] == "tile_self"


def test_color_remap_anchor_keeps_color_family_near_top(tmp_path):
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

    ranked = rank_families_by_anchor(task)
    assert "color_remap" in ranked[:5]


def test_explain_anchors_returns_usable_payload(tmp_path):
    task = _write_task(
        tmp_path,
        "shift_color",
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

    payload = explain_anchors(task)
    assert set(payload["overall_topology"]) == {
        "shape",
        "motion",
        "color",
        "scope",
        "topology",
        "composition",
    }
    assert "n_anchors" in payload
    assert "top_anchors" in payload
