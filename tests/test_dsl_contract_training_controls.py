from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_kernel_template_has_contract_weighted_loss_and_gpu_gate() -> None:
    source = (ROOT / "scripts" / "kaggle_auto" / "kernel_template.py").read_text(encoding="utf-8")

    assert "REQUIRE_GPU" in source
    assert "Refusing CPU/P100 tiny-run" in source
    assert "class WeightedDslSFTTrainer" in source
    assert "torch.isin" in source
    assert "SELECTOR_TOKEN_WEIGHT" in source
    assert "DSL_PRIMITIVE_TOKEN_WEIGHT" in source
    assert "REPAIR_LANE_FILES" in source
    assert "REPAIR_LANE_WEIGHT" in source
    assert "BALANCE_CATEGORIES" in source


def test_launch_forwards_contract_training_levers() -> None:
    source = (ROOT / "scripts" / "kaggle_auto" / "launch.py").read_text(encoding="utf-8")

    for key in (
        "require_gpu",
        "balance_categories",
        "selector_token_weight",
        "dsl_primitive_token_weight",
        "max_sample_multiplier",
        "repair_lane_files",
        "repair_lane_weight",
    ):
        assert f'"{key}": config.get("{key}"' in source or f'"{key}": True' in source

    assert '"bijective_dsl_v5_holdout.sft.jsonl"' in source
    assert '"contract_repair_v3_train.sft.jsonl"' in source


def test_v5_holdout_builder_and_audit_pass() -> None:
    subprocess.run([sys.executable, "scripts/dsl/build_v5_holdout.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/dsl/audit_v5_holdout.py"], cwd=ROOT, check=True)

    report = json.loads((ROOT / "artifacts" / "dsl_eval_reports" / "v5_holdout_gate.json").read_text())
    assert report["verdict"] == "PASS"
    assert report["repair_v3_train_overlap"] == 0
    assert report["translate_one_cap"]["within_cap"] is True
    assert not report["floor_check"]["violations"]
