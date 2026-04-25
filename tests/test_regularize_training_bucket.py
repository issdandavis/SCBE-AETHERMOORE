from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "regularize_training_bucket.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("regularize_training_bucket", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_normalize_instruction_response_to_messages() -> None:
    module = _load_module()
    row = module.normalize_record(
        {"instruction": "Write add.", "response": "def add(a, b): return a + b", "metadata": {"quality": "seed"}},
        {
            "path": "training-data/sft/example.jsonl",
            "sha256": "abc",
            "purpose": "coding_model",
            "split_hint": "train",
            "regularization_status": "ready_prompt_response",
        },
        7,
    )

    assert row is not None
    assert row["messages"][0]["role"] == "user"
    assert row["messages"][1]["role"] == "assistant"
    assert row["metadata"]["source_path"] == "training-data/sft/example.jsonl"
    assert row["metadata"]["source_record_index"] == 7
    assert len(row["metadata"]["dedupe_key"]) == 64


def test_build_bucket_dedupes_and_preserves_eval(tmp_path: Path) -> None:
    module = _load_module()
    train = tmp_path / "coding_train.jsonl"
    holdout = tmp_path / "coding_holdout.jsonl"
    record = {"messages": [{"role": "user", "content": "Add."}, {"role": "assistant", "content": "Use +."}]}
    train.write_text(json.dumps(record) + "\n" + json.dumps(record) + "\n", encoding="utf-8")
    holdout.write_text(json.dumps({"instruction": "Guard divide.", "response": "Check denominator."}) + "\n", encoding="utf-8")
    inventory = tmp_path / "inventory.json"
    inventory.write_text(
        json.dumps(
            {
                "local_datasets": [
                    {
                        "path": str(train),
                        "sha256": "trainhash",
                        "purpose": "coding_model",
                        "extension": ".jsonl",
                        "regularization_status": "ready_messages",
                        "split_hint": "train",
                    },
                    {
                        "path": str(holdout),
                        "sha256": "evalhash",
                        "purpose": "coding_model",
                        "extension": ".jsonl",
                        "regularization_status": "ready_prompt_response",
                        "split_hint": "eval",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    manifest = module.build_bucket(inventory, "coding_model", tmp_path / "out")

    assert manifest["train_records"] == 1
    assert manifest["eval_records"] == 1
    assert manifest["duplicates_removed"] == 1
    assert Path(manifest["outputs"]["train"]).exists()
    assert Path(manifest["outputs"]["eval"]).exists()
