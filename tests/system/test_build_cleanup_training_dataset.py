from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "system" / "build_cleanup_training_dataset.py"
KAGGLE_SCRIPT = REPO_ROOT / "scripts" / "kaggle" / "scbe_kaggle.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_public_path_scrubs_user_home_and_secrets(builder=None) -> None:
    builder = builder or _load_module(SCRIPT, "_cleanup_training_builder")
    home = Path.home()
    text = str(home / "SCBE-AETHERMOORE" / "x") + " token=hf_abcdefghijklmnopqrstuvwxyz"
    scrubbed = builder.public_path(text)
    assert str(home) not in scrubbed
    assert "hf_abcdefghijklmnopqrstuvwxyz" not in scrubbed
    assert "%USERPROFILE%" in scrubbed or "%REPO%" in scrubbed


def test_model_decision_map_keeps_core_models() -> None:
    builder = _load_module(SCRIPT, "_cleanup_training_builder_models")
    assert builder.MODEL_DECISIONS["qwen2.5-coder:1.5b"]["decision"] == "keep"
    assert builder.MODEL_DECISIONS["openclaw:latest"]["decision"] == "keep"
    assert builder.MODEL_DECISIONS["llama-guard3:1b"]["decision"] == "review"


def test_build_record_is_metadata_only_and_redacted() -> None:
    builder = _load_module(SCRIPT, "_cleanup_training_builder_record")
    row = builder.InventoryRow(
        label="HF token=hf_abcdefghijklmnopqrstuvwxyz",
        path="%USERPROFILE%\\.cache",
        size_bytes=1024,
        source_kind="cleanup_candidate",
        decision="cleanup_candidate",
        risk="low",
        reason="Regenerable token=hf_abcdefghijklmnopqrstuvwxyz cache",
    )
    record = builder.build_record(row, "2026-05-12T00:00:00Z")
    blob = json.dumps(record)
    assert "hf_abcdefghijklmnopqrstuvwxyz" not in blob
    assert record["privacy"] == "metadata_only"
    assert record["messages"][2]["content"].startswith("Decision: cleanup_candidate")


def test_build_dataset_writes_kaggle_valid_metadata(tmp_path, monkeypatch) -> None:
    builder = _load_module(SCRIPT, "_cleanup_training_builder_dataset")
    kaggle = _load_module(KAGGLE_SCRIPT, "_scbe_kaggle_for_cleanup_training")
    monkeypatch.setattr(
        builder,
        "collect_inventory",
        lambda: [
            builder.InventoryRow(
                label="SCBE cache temp",
                path="%SCBE_CACHE%\\temp",
                size_bytes=4096,
                source_kind="cleanup_candidate",
                decision="cleanup_candidate",
                risk="low",
                reason="Regenerable temporary workspace.",
            )
        ],
    )
    out_dir = tmp_path / "hf"
    kaggle_dir = tmp_path / "kaggle"
    builder.build_dataset(out_dir, kaggle_dir, "issacizrealdavis/scbe-system-hygiene-training")

    records = (out_dir / "records.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(records) == 1
    metadata = json.loads((kaggle_dir / "dataset-metadata.json").read_text(encoding="utf-8"))
    validation = kaggle.validate_metadata(metadata)
    assert validation.ok, validation.errors
    assert (out_dir / "README.md").exists()
