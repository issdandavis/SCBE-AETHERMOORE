from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "training_data" / "build_geoseal_industry_commands_sft.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_geoseal_industry_commands_sft", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _assistant_payload(row: dict) -> dict:
    payload = json.loads(row["messages"][-1]["content"])
    assert isinstance(payload, dict)
    return payload


def test_records_cover_specific_and_non_specific_command_use_cases() -> None:
    module = _load_module()

    rows = module.build_records()

    assert len(rows) >= 16
    intent_classes = {row["metadata"]["intent_class"] for row in rows}
    assert intent_classes == {"specific", "non_specific"}
    families = {row["metadata"]["command_family"] for row in rows}
    assert {"auth", "models", "factory", "sandbox", "bench", "train", "release", "github"}.issubset(families)


def test_assistant_rows_distinguish_existing_from_planned_commands() -> None:
    module = _load_module()

    rows = module.build_records()
    factory_specific = next(row for row in rows if row["metadata"]["scenario"] == "specific_factory_compare_sandcastle")
    auth_ambiguous = next(row for row in rows if row["metadata"]["scenario"] == "ambiguous_auth_before_remote")

    factory_payload = _assistant_payload(factory_specific)
    auth_payload = _assistant_payload(auth_ambiguous)

    assert factory_payload["decision"] == "RUN_EXISTING_COMMAND"
    assert factory_payload["command_status"] == "existing_repo_command"
    assert "--software-factory" in factory_payload["primary_command"]
    assert auth_payload["decision"] == "PLAN_COMMAND"
    assert auth_payload["command_status"] == "planned_cli_surface"
    assert auth_payload["primary_command"] == "geoseal auth status"


def test_rows_require_receipts_and_block_fake_publish_paths() -> None:
    module = _load_module()

    rows = module.build_records()

    for row in rows:
        payload = _assistant_payload(row)
        assert "command" in payload["receipts_required"]
        assert "returncode" in payload["receipts_required"]
        assert "no_raw_secrets" in payload["safety_checks"]
        assert "do_not_publish_or_merge_without_promotion_gate" in payload["safety_checks"]
        assert payload["fallback"]["if_command_missing"]


def test_write_outputs_and_copy_kaggle(tmp_path: Path) -> None:
    module = _load_module()
    out_dir = tmp_path / "sft"
    kaggle_dir = tmp_path / "kaggle"

    result = module.write_outputs(out_dir, copy_kaggle=True, kaggle_dir=kaggle_dir)

    assert result["ok"] is True
    assert result["train_records"] > result["eval_records"] >= 1
    assert (out_dir / module.TRAIN_NAME).exists()
    assert (out_dir / module.EVAL_NAME).exists()
    assert (out_dir / module.MANIFEST_NAME).exists()
    assert (kaggle_dir / module.TRAIN_NAME).exists()
    assert (kaggle_dir / module.EVAL_NAME).exists()
    assert (kaggle_dir / module.MANIFEST_NAME).exists()

    manifest = json.loads((out_dir / module.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "geoseal_industry_commands_manifest_v1"
    assert manifest["specific_records"] >= 8
    assert manifest["non_specific_records"] >= 8
    assert "fake_execution_claims" in manifest["gate"]["blocked"]
