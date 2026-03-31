from __future__ import annotations

import json
from pathlib import Path

from scripts.system import shard_training_dataset as shard


def test_stage_dataset_repo_shards_large_jsonl_and_writes_manifest(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    large = input_dir / "large.jsonl"
    rows = [json.dumps({"id": idx, "text": "x" * 40}) for idx in range(20)]
    large.write_text("\n".join(rows) + "\n", encoding="utf-8")

    output_root = tmp_path / "staged"
    manifest = shard.stage_dataset_repo(
        inputs=[str(input_dir)],
        output_root=output_root,
        max_bytes=300,
        dataset_repo="issdandavis/scbe-aethermoore-training-data",
    )

    assert manifest["counts"]["source_files"] == 1
    assert manifest["counts"]["rows"] == 20
    assert manifest["files"][0]["mode"] == "sharded"
    outputs = manifest["files"][0]["outputs"]
    assert len(outputs) > 1
    assert all(item["bytes"] <= 300 for item in outputs)

    rebuilt_rows = []
    for item in outputs:
        shard_path = output_root / item["path"]
        rebuilt_rows.extend([line for line in shard_path.read_text(encoding="utf-8").splitlines() if line.strip()])
    assert rebuilt_rows == rows

    manifest_path = output_root / "manifests" / "training_dataset_manifest.json"
    assert manifest_path.exists()
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert loaded["dataset_repo"] == "issdandavis/scbe-aethermoore-training-data"

    readme = (output_root / "README.md").read_text(encoding="utf-8")
    assert "SCBE Training Data Staging Repo" in readme


def test_stage_dataset_repo_copies_small_jsonl_preserving_tree(tmp_path: Path) -> None:
    input_dir = tmp_path / "training-data" / "sft"
    input_dir.mkdir(parents=True)
    source = input_dir / "tiny.jsonl"
    source.write_text('{"prompt":"a","response":"b"}\n', encoding="utf-8")

    output_root = tmp_path / "staged"
    manifest = shard.stage_dataset_repo(inputs=[str(tmp_path / "training-data")], output_root=output_root, max_bytes=1024)

    file_record = manifest["files"][0]
    assert file_record["mode"] == "copied"
    copied_rel = file_record["outputs"][0]["path"]
    copied = output_root / copied_rel
    assert copied.exists()
    assert copied.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_stage_dataset_repo_routes_generated_inputs_to_generated_namespace(tmp_path: Path) -> None:
    generated = tmp_path / "_staging" / "training-data-build" / "generated"
    generated.mkdir(parents=True)
    source = generated / "claude_export_lore_01.jsonl"
    source.write_text('{"prompt":"a","response":"b"}\n', encoding="utf-8")

    output_root = tmp_path / "staged"
    manifest = shard.stage_dataset_repo(inputs=[str(source)], output_root=output_root, max_bytes=1024)

    file_record = manifest["files"][0]
    assert file_record["source_path"].endswith("_staging/training-data-build/generated/claude_export_lore_01.jsonl")
    copied_rel = file_record["outputs"][0]["path"]
    assert copied_rel == "data/generated/claude_export_lore_01.jsonl"
    copied = output_root / copied_rel
    assert copied.exists()
    assert copied.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_stage_dataset_repo_excludes_matching_globs_and_skips_empty_files(tmp_path: Path) -> None:
    input_dir = tmp_path / "training-data" / "sft"
    input_dir.mkdir(parents=True)
    keep = input_dir / "keep.jsonl"
    keep.write_text('{"prompt":"a","response":"b"}\n', encoding="utf-8")
    empty = input_dir / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    excluded = input_dir / "book_drafts_sft.jsonl"
    excluded.write_text('{"prompt":"bad","response":"bad"}\n', encoding="utf-8")

    output_root = tmp_path / "staged"
    manifest = shard.stage_dataset_repo(
        inputs=[str(tmp_path / "training-data")],
        output_root=output_root,
        max_bytes=1024,
        exclude_globs=["training-data/sft/book_drafts_sft.jsonl"],
    )

    assert manifest["counts"]["source_files"] == 1
    assert manifest["counts"]["rows"] == 1
    assert manifest["files"][0]["source_path"].endswith("training-data/sft/keep.jsonl")
