from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "system" / "consolidate_ai_training.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "consolidate_ai_training", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_purposes_rejects_unknown_bucket() -> None:
    module = _load_module()

    try:
        module._parse_purposes("coding_model,unknown")
    except ValueError as exc:
        assert "unknown" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_build_specialist_plan_normalizes_merge_weights(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_module()
    regularization = {
        "model_sets": {
            "coding_model": {"eval_gate": "coding gate"},
            "aligned_foundations": {"eval_gate": "aligned gate"},
        }
    }
    merge_profile = {
        "merge_id": "merge-v1",
        "base_model": "base-model",
        "output_model_repo": "owner/out",
    }
    reg_path = tmp_path / "regularization.json"
    merge_path = tmp_path / "merge.json"
    reg_path.write_text(json.dumps(regularization), encoding="utf-8")
    merge_path.write_text(json.dumps(merge_profile), encoding="utf-8")
    monkeypatch.setattr(module, "REGULARIZATION_CONFIG", reg_path)
    monkeypatch.setattr(module, "MERGE_PROFILE", merge_path)

    inventory = {
        "summary": {
            "local_file_count": 2,
            "local_jsonl_file_count": 2,
            "local_known_jsonl_records": 12,
        }
    }
    regularized = {
        "coding_model": {
            "outputs": {"train": "coding-train.jsonl", "eval": "coding-eval.jsonl"},
            "train_records": 10,
            "eval_records": 2,
            "duplicates_removed": 1,
            "skipped_records": 0,
        },
        "aligned_foundations": {
            "outputs": {"train": "aligned-train.jsonl", "eval": "aligned-eval.jsonl"},
            "train_records": 7,
            "eval_records": 1,
            "duplicates_removed": 0,
            "skipped_records": 1,
        },
    }

    plan = module.build_specialist_plan(
        inventory, regularized, ("coding_model", "aligned_foundations")
    )

    assert plan["schema_version"] == "scbe_ai_training_consolidation_plan_v1"
    assert plan["final_merge"]["merge_id"] == "merge-v1"
    assert plan["specialists"][0]["eval_gate"] == "coding gate"
    assert sum(item["normalized_merge_weight"] for item in plan["specialists"]) == 1.0
    assert plan["specialists"][0]["status"] == "ready_for_training"


def test_render_report_includes_specialists() -> None:
    module = _load_module()
    plan = {
        "generated_at_utc": "2026-04-25T00:00:00+00:00",
        "core_rule": "train specialists first",
        "local_inventory_summary": {
            "local_file_count": 1,
            "local_jsonl_file_count": 1,
            "local_known_jsonl_records": 5,
        },
        "specialists": [
            {
                "specialist_id": "coding_primary_specialist",
                "train_records": 4,
                "eval_records": 1,
                "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
                "normalized_merge_weight": 1.0,
                "status": "ready_for_training",
            }
        ],
        "training_method_ladder": ["SFT first"],
        "promotion_checks": ["test before merge"],
    }

    report = module.render_report(plan)

    assert "coding_primary_specialist" in report
    assert "SFT first" in report
    assert "test before merge" in report


def test_specialist_defaults_include_unblocked_bucket_profiles() -> None:
    module = _load_module()

    assert (
        "config/model_training/operator-agent-bus-qwen-primary.json"
        in module.SPECIALIST_DEFAULTS["operator_agent_bus"]["profile_candidates"]
    )
    assert (
        "config/model_training/governance-security-qwen-primary.json"
        in module.SPECIALIST_DEFAULTS["governance_security"]["profile_candidates"]
    )
    assert (
        "config/model_training/research-bridge-qwen-primary.json"
        in module.SPECIALIST_DEFAULTS["research_bridge"]["profile_candidates"]
    )
