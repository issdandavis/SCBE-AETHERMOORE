from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "kaggle_auto" / "launch.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("kaggle_auto_launch", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _extract_kernel_config(script: str) -> dict:
    marker = "KERNEL_CONFIG = '"
    start = script.index(marker) + len(marker)
    end = script.index("'\n# ==================================================", start)
    return json.loads(script[start:end])


def test_geoseal_stage6_repair_round_targets_profile_dataset_and_repo() -> None:
    module = _load_module()
    config = module.ROUNDS["geoseal-stage6-repair-v7"]

    assert config["base_model"] == "Qwen/Qwen2.5-Coder-0.5B-Instruct"
    assert config["hf_dataset_repo"] == "issdandavis/scbe-coding-agent-sft-stage6-repair-v7"
    assert config["hf_repo"] == "issdandavis/scbe-coding-agent-qwen-stage6-repair-v7-kaggle"
    assert "atomic_workflow_stage6_repair_train.sft.jsonl" in config["files"]


def test_generated_kernel_config_preserves_t4_safe_stage6_settings() -> None:
    module = _load_module()

    script = module.generate_kernel_script("geoseal-stage6-repair-v7", module.ROUNDS["geoseal-stage6-repair-v7"])
    payload = _extract_kernel_config(script)

    assert payload["hf_dataset_repo"] == "issdandavis/scbe-coding-agent-sft-stage6-repair-v7"
    assert payload["batch_size"] == 1
    assert payload["grad_accum"] == 16
    assert payload["max_length"] == 768
    assert payload["max_steps"] == 360
    assert payload["learning_rate"] == 8e-5
    assert payload["max_records"] == 3950
