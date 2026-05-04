from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.evaluate_geoshell_pair_agent_dataset import evaluate_dataset
from scripts.training_data import build_geoshell_pair_agent_sft as builder


def test_geoshell_pair_agent_dataset_eval_passes_generated_rows(tmp_path: Path) -> None:
    dataset = builder.build_dataset(population_multiplier=2)
    paths = builder.write_outputs(dataset, tmp_path / "sft", tmp_path / "events.json")

    report = evaluate_dataset(Path(paths["train"]), Path(paths["holdout"]))

    assert report["ok"] is True
    assert report["row_count"] == 30
    assert report["population_context_count"] == 2
    assert report["base_task_count"] == 15
    assert report["primary_tongue_counts"]["CA"] > 0
    assert report["primary_tongue_counts"]["DR"] > 0


def test_geoshell_pair_agent_dataset_eval_rejects_missing_alignment(
    tmp_path: Path,
) -> None:
    dataset = builder.build_dataset(population_multiplier=1)
    row = dataset["train"][0]
    assistant = json.loads(row["messages"][-1]["content"])
    assistant.pop("tokenizer_alignment")
    row["messages"][-1]["content"] = json.dumps(assistant)
    train_path = tmp_path / "train.jsonl"
    holdout_path = tmp_path / "holdout.jsonl"
    train_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    holdout_path.write_text("", encoding="utf-8")

    report = evaluate_dataset(train_path, holdout_path)

    assert report["ok"] is False
    assert report["errors"][0]["error"] == "missing_tokenizer_alignment"
