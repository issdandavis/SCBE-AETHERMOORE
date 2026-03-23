from __future__ import annotations

from scripts.system import colab_notebook_soak as soak


def test_select_notebooks_filters_by_name_and_category() -> None:
    payloads = soak._select_notebooks(
        names=["finetune", "pivot"],
        categories=["training"],
        limit=0,
        include_missing=False,
    )

    names = [row["name"] for row in payloads]
    assert names == ["scbe-finetune-free", "scbe-pivot-v2"]


def test_classify_result_marks_runtime_and_smoke_success() -> None:
    result = {
        "notebook": {"name": "scbe-finetune-free", "category": "training"},
        "cells_before": {"cell_count": 19},
        "connect_result": {"clicked": True},
        "runtime_after_connect": {"usage_visible": False, "kernel_state": "connected"},
        "smoke_result": {
            "success": True,
            "stage": "output",
            "output_result": {"execution_count": 1, "output_count": 1},
        },
        "artifact_path": "artifact.json",
        "screenshot_path": "page.png",
    }

    row = soak._classify_result(result)

    assert row["opened"] is True
    assert row["runtime_attached"] is True
    assert row["smoke_success"] is True
    assert row["execution_count"] == 1
