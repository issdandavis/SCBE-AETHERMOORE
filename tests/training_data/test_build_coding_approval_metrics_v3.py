from __future__ import annotations

import json

from scripts.training_data.build_coding_approval_metrics_v3 import (
    EVAL_NAME,
    MANIFEST_NAME,
    TRAIN_NAME,
    build_packet_trace_records,
    build_residue_records,
    build_task_flow_records,
    write_outputs,
)


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_builders_use_existing_sources() -> None:
    flow = build_task_flow_records(limit=6)
    traces = build_packet_trace_records()
    residues = build_residue_records()

    assert len(flow) == 6
    assert traces
    assert residues
    assert any("Draumric" in row["messages"][1]["content"] for row in flow)
    assert any("packet fingerprint" in row["messages"][2]["content"] for row in traces)
    assert any("INCUBATE" in row["messages"][2]["content"] for row in residues)


def test_write_outputs_creates_train_eval_manifest_and_kaggle_copy(tmp_path) -> None:
    out_dir = tmp_path / "sft"
    kaggle_dir = tmp_path / "kaggle"

    manifest = write_outputs(out_dir, copy_kaggle=True, kaggle_dir=kaggle_dir)

    train = _read_jsonl(out_dir / TRAIN_NAME)
    eval_rows = _read_jsonl(out_dir / EVAL_NAME)
    manifest_disk = json.loads((out_dir / MANIFEST_NAME).read_text(encoding="utf-8"))

    assert manifest["train_count"] == len(train)
    assert manifest["eval_count"] == len(eval_rows)
    assert manifest["train_count"] > manifest["eval_count"] > 0
    assert manifest_disk["sacred_tongue_names"]["KO"] == "Kor'aelin"
    assert manifest_disk["source_counts"]["markdown_task_flow"] > manifest_disk["source_counts"]["training_residue"]
    assert (kaggle_dir / TRAIN_NAME).is_file()
    assert (kaggle_dir / EVAL_NAME).is_file()
    assert (kaggle_dir / MANIFEST_NAME).is_file()


def test_records_keep_non_binary_verdicts(tmp_path) -> None:
    write_outputs(tmp_path)
    rows = _read_jsonl(tmp_path / TRAIN_NAME) + _read_jsonl(tmp_path / EVAL_NAME)
    assistants = "\n".join(row["messages"][2]["content"] for row in rows)

    assert "verdict=HOLD" in assistants
    assert "verdict=PROMOTE" in assistants
    assert "verdict=INCUBATE" in assistants
    assert "return_horizon=long" in assistants
