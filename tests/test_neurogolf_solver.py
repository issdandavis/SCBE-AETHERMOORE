from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from neurogolf.arc_io import load_arc_task
from neurogolf.family_lattice import task_topology
from neurogolf.move_family import prefilter_moves, solve_by_move_algebra
from neurogolf.solver import execute_program, synthesize_program


def test_synthesize_color_remap_program(tmp_path):
    task_path = tmp_path / "task101.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {"input": [[1, 2], [2, 1]], "output": [[3, 4], [4, 3]]},
                    {"input": [[2, 1]], "output": [[4, 3]]},
                ],
                "test": [{"input": [[1, 2]]}],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    solution = synthesize_program(task)

    assert solution.family == "color_remap"
    assert solution.program.steps[0].op == "color_remap"
    predicted = execute_program(task.test_inputs[0], solution.program)
    assert np.array_equal(predicted, np.array([[3, 4]]))


def test_synthesize_shift_then_color_remap_program(tmp_path):
    task_path = tmp_path / "task102.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {
                        "input": [[1, 0, 0], [0, 2, 0], [0, 0, 0]],
                        "output": [[0, 0, 0], [5, 0, 0], [0, 6, 0]],
                    }
                ],
                "test": [{"input": [[1, 0, 0], [0, 2, 0], [0, 0, 0]]}],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    solution = synthesize_program(task)

    assert solution.family == "shift_then_color_remap"
    assert [step.op for step in solution.program.steps] == ["shift", "color_remap"]
    predicted = execute_program(task.test_inputs[0], solution.program)
    assert np.array_equal(predicted, task.train[0].output)


def test_synthesize_flip_x_then_color_remap_program(tmp_path):
    task_path = tmp_path / "task103.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {
                        "input": [[1, 2, 0], [3, 0, 0]],
                        "output": [[0, 7, 8], [0, 0, 9]],
                    }
                ],
                "test": [{"input": [[1, 2, 0], [3, 0, 0]]}],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    solution = synthesize_program(task)

    assert solution.family == "flip_x_then_color_remap"
    assert [step.op for step in solution.program.steps] == ["flip_x", "color_remap"]
    predicted = execute_program(task.test_inputs[0], solution.program)
    assert np.array_equal(predicted, task.train[0].output)


def test_synthesize_dominant_component_shift_program(tmp_path):
    task_path = tmp_path / "task104.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {
                        "input": [
                            [1, 1, 0, 0],
                            [1, 0, 0, 2],
                            [0, 0, 0, 2],
                            [0, 0, 0, 0],
                        ],
                        "output": [
                            [0, 0, 0, 0],
                            [0, 1, 1, 2],
                            [0, 1, 0, 2],
                            [0, 0, 0, 0],
                        ],
                    }
                ],
                "test": [
                    {
                        "input": [
                            [1, 1, 0, 0],
                            [1, 0, 0, 2],
                            [0, 0, 0, 2],
                            [0, 0, 0, 0],
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    solution = synthesize_program(task)

    assert solution.family == "dominant_component_shift"
    assert solution.program.steps[0].op == "shift_color"
    predicted = execute_program(task.test_inputs[0], solution.program)
    assert np.array_equal(predicted, task.train[0].output)


def test_synthesize_dominant_component_copy_program(tmp_path):
    task_path = tmp_path / "task105.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {
                        "input": [
                            [1, 1, 0, 0],
                            [1, 0, 0, 2],
                            [0, 0, 0, 2],
                            [0, 0, 0, 0],
                        ],
                        "output": [
                            [1, 1, 0, 0],
                            [1, 1, 1, 2],
                            [0, 1, 0, 2],
                            [0, 0, 0, 0],
                        ],
                    }
                ],
                "test": [
                    {
                        "input": [
                            [1, 1, 0, 0],
                            [1, 0, 0, 2],
                            [0, 0, 0, 2],
                            [0, 0, 0, 0],
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    solution = synthesize_program(task)

    assert solution.family == "dominant_component_copy"
    assert solution.program.steps[0].op == "copy_color"
    predicted = execute_program(task.test_inputs[0], solution.program)
    assert np.array_equal(predicted, task.train[0].output)


def test_synthesize_multi_unique_color_shift_program(tmp_path):
    task_path = tmp_path / "task106.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {
                        "input": [
                            [1, 0, 0, 2],
                            [1, 0, 0, 2],
                            [0, 0, 0, 0],
                            [0, 0, 0, 0],
                        ],
                        "output": [
                            [0, 0, 0, 0],
                            [1, 0, 2, 0],
                            [1, 0, 2, 0],
                            [0, 0, 0, 0],
                        ],
                    }
                ],
                "test": [
                    {
                        "input": [
                            [1, 0, 0, 2],
                            [1, 0, 0, 2],
                            [0, 0, 0, 0],
                            [0, 0, 0, 0],
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    solution = synthesize_program(task)

    assert solution.family == "multi_unique_color_shift"
    assert [step.op for step in solution.program.steps] == ["shift_color", "shift_color"]
    predicted = execute_program(task.test_inputs[0], solution.program)
    assert np.array_equal(predicted, task.train[0].output)


def test_synthesize_fill_enclosed_uses_broad_color_candidates(tmp_path):
    task_path = tmp_path / "task_fill_enclosed_broad.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {
                        "input": [
                            [1, 1, 1, 1],
                            [1, 0, 0, 1],
                            [1, 0, 0, 1],
                            [1, 1, 1, 1],
                        ],
                        "output": [
                            [1, 1, 1, 1],
                            [1, 1, 1, 1],
                            [1, 1, 1, 1],
                            [1, 1, 1, 1],
                        ],
                    },
                    {
                        "input": [
                            [1, 1, 1],
                            [1, 1, 1],
                            [1, 1, 1],
                        ],
                        "output": [
                            [1, 1, 1],
                            [1, 1, 1],
                            [1, 1, 1],
                        ],
                    },
                ],
                "test": [{"input": [[1, 1], [1, 1]]}],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    solution = synthesize_program(task)

    assert solution.family == "fill_enclosed"
    assert solution.program.steps[0].op == "fill_enclosed"


def test_move_algebra_crop_then_tile_mirror_program(tmp_path):
    task_path = tmp_path / "task_crop_tile_mirror.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {
                        "input": [
                            [0, 0, 0, 0],
                            [0, 1, 2, 0],
                            [0, 3, 4, 0],
                            [0, 0, 0, 0],
                        ],
                        "output": [
                            [1, 2, 2, 1],
                            [3, 4, 4, 3],
                            [3, 4, 4, 3],
                            [1, 2, 2, 1],
                        ],
                    }
                ],
                "test": [
                    {
                        "input": [
                            [0, 0, 0, 0],
                            [0, 1, 2, 0],
                            [0, 3, 4, 0],
                            [0, 0, 0, 0],
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    program = solve_by_move_algebra(task, task_topology(task), top_k=12, max_depth=2)

    assert program is not None
    assert program.name == "crop+tile_mirror_2x2"
    assert [step.op for step in program.steps] == ["crop", "tile_mirror_2x2"]
    predicted = execute_program(task.test_inputs[0], program)
    assert np.array_equal(predicted, task.train[0].output)


def test_prefilter_forces_select_and_crop_on_shrink_like_tasks(tmp_path):
    task_path = tmp_path / "task_select_crop_prefilter.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {
                        "input": [
                            [1, 1, 0, 0],
                            [1, 0, 0, 0],
                            [0, 0, 0, 2],
                        ],
                        "output": [
                            [2],
                        ],
                    }
                ],
                "test": [
                    {
                        "input": [
                            [1, 1, 0, 0],
                            [1, 0, 0, 0],
                            [0, 0, 0, 2],
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    candidates = prefilter_moves(task_topology(task), top_k=1, forced_move_names=())
    baseline = {move.name for move in candidates}
    widened = solve_by_move_algebra(task, task_topology(task), top_k=1, max_depth=2)

    assert "crop" not in baseline or "select_minority_color" not in baseline
    assert widened is not None
    assert widened.name == "select_minority_color+crop"


def test_prefilter_forces_crop_on_any_size_change(tmp_path):
    task_path = tmp_path / "task_crop_size_change_prefilter.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {
                        "input": [
                            [0, 0, 0, 0],
                            [0, 1, 2, 0],
                            [0, 3, 4, 0],
                            [0, 0, 0, 0],
                        ],
                        "output": [
                            [1, 2, 2, 1],
                            [3, 4, 4, 3],
                            [3, 4, 4, 3],
                            [1, 2, 2, 1],
                        ],
                    }
                ],
                "test": [{"input": [[0, 0], [0, 0]]}],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    baseline = {move.name for move in prefilter_moves(task_topology(task), top_k=1, forced_move_names=())}
    program = solve_by_move_algebra(task, task_topology(task), top_k=1, max_depth=2)

    assert "crop" not in baseline
    assert program is not None
    assert program.name == "crop+tile_mirror_2x2"


def test_synthesize_connect_aligned_pairs_program(tmp_path):
    task_path = tmp_path / "task_connect_pairs.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {
                        "input": [
                            [0, 2, 0, 0, 0],
                            [0, 0, 0, 0, 0],
                            [3, 0, 0, 0, 3],
                            [0, 0, 0, 0, 0],
                            [0, 2, 0, 0, 0],
                        ],
                        "output": [
                            [0, 2, 0, 0, 0],
                            [0, 2, 0, 0, 0],
                            [3, 2, 3, 3, 3],
                            [0, 2, 0, 0, 0],
                            [0, 2, 0, 0, 0],
                        ],
                    }
                ],
                "test": [
                    {
                        "input": [
                            [0, 4, 0],
                            [5, 0, 5],
                            [0, 4, 0],
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    solution = synthesize_program(task)

    assert solution.family == "connect_aligned_pairs"
    assert solution.program.steps[0].op == "connect_aligned_pairs"
    predicted = execute_program(task.test_inputs[0], solution.program)
    assert np.array_equal(predicted, np.array([[0, 4, 0], [5, 4, 5], [0, 4, 0]]))


def test_eval_regression_connect_aligned_pairs_070dd51e():
    task_path = Path("artifacts/arc-data/ARC-AGI-master/data/evaluation/070dd51e.json")
    task = load_arc_task(task_path)
    expected = json.loads(task_path.read_text(encoding="utf-8"))["test"][0]["output"]
    solution = synthesize_program(task)

    assert solution is not None
    assert solution.family == "connect_aligned_pairs"
    predicted = execute_program(task.test_inputs[0], solution.program)
    assert np.array_equal(predicted, np.array(expected))


def test_synthesize_corner_legend_row_swap_program(tmp_path):
    task_path = tmp_path / "task_corner_legend_row_swap.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {
                        "input": [
                            [1, 2, 0, 0],
                            [3, 4, 2, 0],
                            [0, 0, 3, 1],
                            [0, 0, 4, 2],
                        ],
                        "output": [
                            [1, 2, 0, 0],
                            [3, 4, 1, 0],
                            [0, 0, 4, 2],
                            [0, 0, 3, 1],
                        ],
                    }
                ],
                "test": [
                    {
                        "input": [
                            [5, 6, 0, 0],
                            [7, 8, 6, 0],
                            [0, 0, 7, 5],
                            [0, 0, 8, 6],
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    solution = synthesize_program(task)

    assert solution.family == "corner_legend_row_swap"
    assert solution.program.steps[0].op == "corner_legend_row_swap"
    predicted = execute_program(task.test_inputs[0], solution.program)
    assert np.array_equal(
        predicted,
        np.array(
            [
                [5, 6, 0, 0],
                [7, 8, 5, 0],
                [0, 0, 8, 6],
                [0, 0, 7, 5],
            ]
        ),
    )


def test_eval_regression_corner_legend_row_swap_0becf7df():
    task_path = Path("artifacts/arc-data/ARC-AGI-master/data/evaluation/0becf7df.json")
    task = load_arc_task(task_path)
    expected = json.loads(task_path.read_text(encoding="utf-8"))["test"][0]["output"]
    solution = synthesize_program(task)

    assert solution is not None
    assert solution.family == "corner_legend_row_swap"
    predicted = execute_program(task.test_inputs[0], solution.program)
    assert np.array_equal(predicted, np.array(expected))


def test_synthesize_panel_consensus_tile_program(tmp_path):
    task_path = tmp_path / "task_panel_consensus_tile.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {
                        "input": [
                            [0, 0, 0, 0, 0, 0, 0],
                            [0, 1, 2, 0, 1, 0, 0],
                            [0, 3, 4, 0, 3, 4, 0],
                            [0, 0, 0, 0, 0, 0, 0],
                            [0, 1, 2, 0, 1, 2, 0],
                            [0, 0, 4, 0, 3, 4, 0],
                            [0, 0, 0, 0, 0, 0, 0],
                        ],
                        "output": [
                            [0, 0, 0, 0, 0, 0, 0],
                            [0, 1, 2, 0, 1, 2, 0],
                            [0, 3, 4, 0, 3, 4, 0],
                            [0, 0, 0, 0, 0, 0, 0],
                            [0, 1, 2, 0, 1, 2, 0],
                            [0, 3, 4, 0, 3, 4, 0],
                            [0, 0, 0, 0, 0, 0, 0],
                        ],
                    }
                ],
                "test": [
                    {
                        "input": [
                            [0, 0, 0, 0, 0, 0, 0],
                            [0, 1, 2, 0, 1, 0, 0],
                            [0, 3, 0, 0, 3, 4, 0],
                            [0, 0, 0, 0, 0, 0, 0],
                            [0, 1, 2, 0, 1, 2, 0],
                            [0, 3, 4, 0, 3, 4, 0],
                            [0, 0, 0, 0, 0, 0, 0],
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    solution = synthesize_program(task)

    assert solution is not None
    assert solution.family == "panel_consensus_tile"
    assert solution.program.steps[0].op == "panel_consensus_tile"
    predicted = execute_program(task.test_inputs[0], solution.program)
    assert np.array_equal(
        predicted,
        np.array(
            [
                [0, 0, 0, 0, 0, 0, 0],
                [0, 1, 2, 0, 1, 2, 0],
                [0, 3, 4, 0, 3, 4, 0],
                [0, 0, 0, 0, 0, 0, 0],
                [0, 1, 2, 0, 1, 2, 0],
                [0, 3, 4, 0, 3, 4, 0],
                [0, 0, 0, 0, 0, 0, 0],
            ]
        ),
    )


def test_eval_regression_panel_consensus_tile_0607ce86():
    task_path = Path("artifacts/arc-data/ARC-AGI-master/data/evaluation/0607ce86.json")
    task = load_arc_task(task_path)
    expected = json.loads(task_path.read_text(encoding="utf-8"))["test"][0]["output"]
    solution = synthesize_program(task)

    assert solution is not None
    assert solution.family == "panel_consensus_tile"
    predicted = execute_program(task.test_inputs[0], solution.program)
    assert np.array_equal(predicted, np.array(expected))


def test_synthesize_select_unique_object_crop_program(tmp_path):
    task_path = tmp_path / "task_select_unique_object_crop.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {
                        "input": [
                            [1, 2, 0, 1, 2, 0, 4, 5],
                            [2, 1, 0, 2, 1, 0, 5, 5],
                        ],
                        "output": [
                            [4, 5],
                            [5, 5],
                        ],
                    }
                ],
                "test": [
                    {
                        "input": [
                            [1, 2, 0, 1, 2, 0, 4, 5],
                            [2, 1, 0, 2, 1, 0, 5, 5],
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    solution = synthesize_program(task)

    assert solution is not None
    assert solution.family == "select_unique_object+crop"
    assert [step.op for step in solution.program.steps] == ["select", "crop"]
    predicted = execute_program(task.test_inputs[0], solution.program)
    assert np.array_equal(predicted, np.array([[4, 5], [5, 5]]))


def test_eval_regression_select_unique_object_crop_cd3c21df():
    task_path = Path("artifacts/arc-data/ARC-AGI-master/data/evaluation/cd3c21df.json")
    task = load_arc_task(task_path)
    expected = json.loads(task_path.read_text(encoding="utf-8"))["test"][0]["output"]
    solution = synthesize_program(task)

    assert solution is not None
    assert solution.family == "select_unique_object+crop"
    predicted = execute_program(task.test_inputs[0], solution.program)
    assert np.array_equal(predicted, np.array(expected))
