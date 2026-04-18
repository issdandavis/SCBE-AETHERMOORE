from __future__ import annotations

import json

from neurogolf.arc_io import grid_to_one_hot, load_arc_task, pad_grid


def test_load_arc_task_and_static_padding(tmp_path):
    task_path = tmp_path / "task001.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {"input": [[1, 2], [3, 4]], "output": [[4, 3], [2, 1]]},
                ],
                "test": [{"input": [[0, 1, 2]]}],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    assert task.task_id == "task001"
    assert task.train[0].input.shape == (2, 2)
    assert task.test_inputs[0].shape == (1, 3)

    padded = pad_grid(task.train[0].input, target_size=5)
    assert padded.shape == (5, 5)
    assert padded[0, 0] == 1
    assert padded[4, 4] == 0

    one_hot = grid_to_one_hot(task.train[0].input, target_size=5)
    assert one_hot.shape == (10, 5, 5)
    assert one_hot[1, 0, 0] == 1.0
    assert one_hot[0, 4, 4] == 1.0
