from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_stage6_boss_dpo.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_stage6_boss_dpo", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_boss_dpo_rows_have_preference_shape_and_targets():
    module = load_module()
    plan = json.loads((ROOT / "artifacts" / "model_training" / "stage6-v12-boss-retry-plan.json").read_text())
    contract = json.loads(
        (ROOT / "config" / "model_training" / "stage6_atomic_workflow_eval_contract.json").read_text()
    )

    rows = module.build_rows(plan, contract)

    assert len(rows) == 168
    assert all({"prompt", "chosen", "rejected", "system", "meta"} <= set(row) for row in rows)
    assert any(row["meta"]["failure_kind"] == "byte_hex_compute_trace" for row in rows)
    assert any(row["meta"]["failure_kind"] == "multi_budget_cost_propagation" for row in rows)
    assert any(row["meta"]["failure_kind"] == "heldout_boundary_pollution_control" for row in rows)
    assert any("compute" in row["chosen"] and "hold" in row["chosen"] for row in rows)
    assert any("power | compute | time | comms | wear" in row["chosen"] for row in rows)
    assert any("held-out" in row["chosen"] and "pollution" in row["chosen"] for row in rows)


def test_boss_dpo_rows_do_not_copy_frozen_eval_prompts():
    module = load_module()
    plan = json.loads((ROOT / "artifacts" / "model_training" / "stage6-v12-boss-retry-plan.json").read_text())
    contract = json.loads(
        (ROOT / "config" / "model_training" / "stage6_atomic_workflow_eval_contract.json").read_text()
    )
    frozen_prompts = [item["prompt"] for item in contract["prompts"]]

    rows = module.build_rows(plan, contract)
    blob = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)

    for prompt in frozen_prompts:
        assert prompt not in blob


def test_boss_dpo_manifest_counts_rows_by_failure_kind(tmp_path):
    module = load_module()
    plan = json.loads((ROOT / "artifacts" / "model_training" / "stage6-v12-boss-retry-plan.json").read_text())
    contract = json.loads(
        (ROOT / "config" / "model_training" / "stage6_atomic_workflow_eval_contract.json").read_text()
    )
    rows = module.build_rows(plan, contract)

    manifest = module.build_manifest(rows, plan, tmp_path / "train.jsonl")

    assert manifest["row_count"] == 168
    assert manifest["rows_by_failure_kind"]["byte_hex_compute_trace"] == 72
    assert manifest["rows_by_failure_kind"]["multi_budget_cost_propagation"] == 48
    assert manifest["rows_by_failure_kind"]["heldout_boundary_pollution_control"] == 48
    assert "Frozen" not in manifest["training_boundary"]["rule"]
