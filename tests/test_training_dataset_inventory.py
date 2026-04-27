from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "training_dataset_inventory.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("training_dataset_inventory", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_classify_purpose_keeps_coding_separate() -> None:
    module = _load_module()

    assert module.classify_purpose("training-data/sft/coding_system_full_v1_train.sft.jsonl") == "coding_model"
    assert module.classify_purpose("training-data/sft/governance_deep_v2.jsonl") == "governance_security"
    assert module.classify_purpose("training-data/lore_sessions/everweave_canon.jsonl") == "story_lore"
    assert module.classify_purpose("training-data/hand_tune/commerce/stripe_haggle.jsonl") == "commerce_product"


def test_jsonl_stats_and_regularization_status(tmp_path: Path) -> None:
    module = _load_module()
    path = tmp_path / "coding_system_full_v1_train.sft.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {"instruction": "Explain add.", "response": "Use a deterministic add function.", "metadata": {}}
                ),
                json.dumps({"instruction": "Explain guard.", "response": "Reject divide by zero.", "metadata": {}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    row = module.inspect_file(path, "test")

    assert row["purpose"] == "coding_model"
    assert row["record_count"] == 2
    assert row["prompt_response_records"] == 2
    assert row["regularization_status"] == "ready_prompt_response"


def test_lfs_pointer_jsonl_is_not_reported_as_malformed(tmp_path: Path) -> None:
    module = _load_module()
    path = tmp_path / "old_dataset.jsonl"
    path.write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:5c814931342aecdb0b3e8ee943ac2fa181041d06c5bf8e3eefa7a6ecbbd84790\n"
        "size 4323\n",
        encoding="utf-8",
    )

    row = module.inspect_file(path, "test")

    assert row["lfs_pointer"] is True
    assert row["regularization_status"] == "lfs_pointer_needs_pull"


def test_build_merge_plan_preserves_eval_split() -> None:
    module = _load_module()
    rows = [
        {
            "path": "training-data/sft/coding_system_full_v1_train.sft.jsonl",
            "purpose": "coding_model",
            "regularization_status": "ready_prompt_response",
            "split_hint": "train",
            "record_count": 48,
        },
        {
            "path": "training-data/sft/coding_system_full_v1_holdout.sft.jsonl",
            "purpose": "coding_model",
            "regularization_status": "ready_prompt_response",
            "split_hint": "eval",
            "record_count": 8,
        },
    ]

    plan = module.build_merge_plan(rows, {})
    coding = plan["model_sets"]["coding_model"]

    assert coding["ready_train_file_count"] == 1
    assert coding["eval_file_count"] == 1
    assert coding["train_candidates"] == ["training-data/sft/coding_system_full_v1_train.sft.jsonl"]
    assert coding["eval_candidates"] == ["training-data/sft/coding_system_full_v1_holdout.sft.jsonl"]
