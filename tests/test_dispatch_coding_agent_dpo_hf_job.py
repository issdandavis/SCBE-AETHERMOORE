from __future__ import annotations

import importlib.util
import json
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


def test_dpo_build_packet_defaults_to_l4x1_and_carries_idempotency_key(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "_load_env_file", lambda *args, **kwargs: None)
    monkeypatch.setenv("HF_TOKEN", "unit-token")
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "dpo-idempotency-test",
                "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
                "dataset": {"train_files": ["rows.jsonl"]},
                "training": {},
                "hub": {
                    "dataset_repo": "owner/dataset",
                    "adapter_repo": "owner/output-adapter",
                },
                "execution": {"timeout": "30m"},
            }
        ),
        encoding="utf-8",
    )

    packet = module.build_packet(profile_path=profile_path, artifact_root=tmp_path / "runs")

    assert packet["hf"]["flavor"] == "l4x1"
    assert len(packet["idempotency_key"]) == 64
    assert f"SCBE_IDEMPOTENCY_KEY={packet['idempotency_key']}" in packet["command"]


def test_dpo_dispatch_idempotency_marker_skips_duplicate_job(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "_load_env_file", lambda *args, **kwargs: None)
    monkeypatch.setenv("HF_TOKEN", "unit-token")
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "dpo-skip-test",
                "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
                "dataset": {"train_files": ["rows.jsonl"]},
                "training": {},
                "hub": {
                    "dataset_repo": "owner/dataset",
                    "adapter_repo": "owner/output-adapter",
                },
            }
        ),
        encoding="utf-8",
    )
    packet = module.build_packet(profile_path=profile_path, artifact_root=tmp_path / "runs")
    packet["hf"]["cli"] = "hf"
    key = packet["idempotency_key"]
    marker_dir = tmp_path / "runs" / "_idempotency"
    marker_dir.mkdir(parents=True)
    (marker_dir / f"{key}.json").write_text(
        json.dumps(
            {
                "idempotency_key": key,
                "packet_path": "previous/job_packet.json",
                "dispatch": {"job_id": "previous-job-123"},
            }
        ),
        encoding="utf-8",
    )

    result = module.dispatch_packet(packet)

    assert result["dispatched"] is False
    assert result["dispatch"]["idempotent_skip"] is True
    assert result["dispatch"]["job_id"] == "previous-job-123"
    assert result["dataset_uploads"] == []
