from __future__ import annotations

from pathlib import Path

from scripts.system.build_model_score_coordination_matrix import (
    build_matrix,
    write_outputs,
)


def test_model_score_matrix_names_three_real_score_movers() -> None:
    matrix = build_matrix()
    levers = {item["id"]: item for item in matrix["levers"]}

    assert matrix["schema_version"] == "scbe_model_score_coordination_matrix_v1"
    assert set(levers) == {"dataset_floor", "quality_metric", "promotion_gate"}
    assert "hf_dataset_floor" in levers["dataset_floor"]["scorecard_line"]
    assert "kaggle_quality_metric" in levers["quality_metric"]["scorecard_line"]
    assert "adapter_promoted" in levers["promotion_gate"]["scorecard_line"]
    assert "+----------------------+" in matrix["box_graph"]


def test_model_score_matrix_writes_json_and_markdown(tmp_path: Path) -> None:
    matrix = build_matrix()
    paths = write_outputs(matrix, tmp_path / "matrix.json", tmp_path / "matrix.md")

    assert Path(paths["json"]).exists()
    markdown = Path(paths["markdown"]).read_text(encoding="utf-8")
    assert "Model Score Coordination Matrix" in markdown
    assert "dataset_floor" in markdown
