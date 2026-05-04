from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "system" / "dispatch_coding_agent_dpo_hf_job.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("dispatch_coding_agent_dpo_hf_job", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_dpo_render_supports_base_adapter_continuation() -> None:
    module = _load_module()

    script = module.render_uv_dpo_script(
        {
            "profile_id": "test-dpo",
            "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
            "dataset": {"train_files": ["rows.jsonl"]},
            "training": {"base_adapter_repo": "owner/source-adapter"},
            "hub": {
                "dataset_repo": "owner/dataset",
                "adapter_repo": "owner/output-adapter",
            },
            "evaluation": {"constrained_gate_scaffold": True},
        }
    )

    assert "base_adapter_load" in script
    assert "PeftModel.from_pretrained(model, base_adapter_repo" in script
    assert "owner/source-adapter" in script


def test_dpo_constrained_gate_prefix_avoids_forbidden_token_collision() -> None:
    module = _load_module()

    script = module.render_uv_dpo_script(
        {
            "profile_id": "test-dpo",
            "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
            "dataset": {"train_files": ["rows.jsonl"]},
            "training": {},
            "hub": {
                "dataset_repo": "owner/dataset",
                "adapter_repo": "owner/output-adapter",
            },
            "evaluation": {"constrained_gate_scaffold": True},
        }
    )

    assert "required-items:" in script
    assert "required-tokens:" not in script
    assert "constrained gate prefix would trigger forbidden marker" in script
