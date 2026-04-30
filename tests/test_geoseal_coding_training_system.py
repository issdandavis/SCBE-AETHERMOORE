from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "system" / "geoseal_coding_training_system.py"
MANIFEST_PATH = ROOT / "config" / "model_training" / "geoseal_coding_training_manifest.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("geoseal_coding_training_system", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manifest_lists_dedicated_geoseal_coding_profiles() -> None:
    module = _load_module()
    manifest = module.load_manifest(MANIFEST_PATH)
    profiles = module.list_profiles(manifest)

    ids = {item["profile_id"] for item in profiles["profiles"]}
    assert "coding-agent-qwen-smoke" in ids
    assert "coding-agent-qwen-online-v2" in ids
    assert "coding-agent-qwen-atomic-workflow-stage6" in ids
    assert "coding-agent-qwen-ca-geoseal-smoke-repair-v1" in ids
    assert profiles["schema_version"] == "geoseal_coding_training_profiles_v1"

    stage6 = next(
        item for item in profiles["profiles"] if item["profile_id"] == "coding-agent-qwen-atomic-workflow-stage6"
    )
    assert stage6["stage"] == "atomic_workflow_resource_decay"
    assert stage6["exists"] is True

    repair = next(
        item for item in profiles["profiles"] if item["profile_id"] == "coding-agent-qwen-ca-geoseal-smoke-repair-v1"
    )
    assert repair["stage"] == "ca_geoseal_smoke_repair"
    assert repair["exists"] is True


def test_stage6_profile_is_t4_safe_after_oom_hardening() -> None:
    profile = json.loads(
        (ROOT / "config" / "model_training" / "coding-agent-qwen-atomic-workflow-stage6.json").read_text()
    )
    training = profile["training"]

    assert training["max_seq_length"] <= 768
    assert training["batch_size"] == 1
    assert training["gradient_accumulation_steps"] >= 16
    assert training["gradient_checkpointing"] is True


def test_repair_profile_does_not_inherit_stage6_contract_by_default() -> None:
    dispatcher_path = ROOT / "scripts" / "system" / "dispatch_coding_agent_hf_job.py"
    spec = importlib.util.spec_from_file_location("dispatch_coding_agent_hf_job", dispatcher_path)
    assert spec and spec.loader
    dispatcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dispatcher)
    profile = json.loads(
        (ROOT / "config" / "model_training" / "coding-agent-qwen-ca-geoseal-smoke-repair-v1.json").read_text()
    )

    script = dispatcher.render_uv_training_script(profile)

    assert '"contract_id": ""' in script
    assert '"prompts": []' in script
    assert "pass_rate = (n_pass / n_total) if n_total else 1.0" in script


def test_smoke_eval_plan_carries_geoseal_cli_gates(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    manifest = module.load_manifest(MANIFEST_PATH)
    profile_path = tmp_path / "config" / "model_training" / "coding-agent-qwen-online-v2.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "coding-agent-qwen-online-v2",
                "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
                "hub": {"adapter_repo": "owner/default-adapter"},
            }
        ),
        encoding="utf-8",
    )
    for item in manifest["profiles"]:
        if item["profile_id"] == "coding-agent-qwen-online-v2":
            item["profile_path"] = "config/model_training/coding-agent-qwen-online-v2.json"
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    plan = module.smoke_eval_plan(manifest, "coding-agent-qwen-online-v2", "owner/adapter")

    prompts = {item["id"]: item for item in plan["prompts"]}
    assert plan["adapter_repo"] == "owner/adapter"
    assert "geoseal_execution_shell_task" in prompts
    assert "portal-box" in prompts["polly_portal_stream_task"]["required"]
    assert "def is_even" in prompts["ko_python_to_ru_rust"]["forbidden"]
    assert (Path(plan["output_dir"]) / "smoke_eval_plan.json").exists()


def test_stage6_smoke_eval_plan_uses_frozen_unseen_contract(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    manifest = module.load_manifest(MANIFEST_PATH)
    contract_path = tmp_path / "config" / "model_training" / "stage6_atomic_workflow_eval_contract.json"
    profile_path = tmp_path / "config" / "model_training" / "coding-agent-qwen-atomic-workflow-stage6.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text(
        json.dumps(
            {
                "schema_version": "scbe_stage_eval_contract_v1",
                "contract_id": "stage6_contract_test",
                "thresholds": {
                    "minimum_pass_rate": 0.8,
                    "must_pass": ["unseen_task"],
                    "decision_rule": "test rule",
                },
                "failure_modes": [{"id": "lane_conflation"}],
                "prompts": [
                    {
                        "id": "unseen_task",
                        "prompt": "Explain token-to-hex fallback.",
                        "required": ["hex"],
                        "forbidden": ["real atoms"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "coding-agent-qwen-atomic-workflow-stage6",
                "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
                "hub": {"adapter_repo": "owner/stage6"},
                "evaluation": {"contract_path": "config/model_training/stage6_atomic_workflow_eval_contract.json"},
            }
        ),
        encoding="utf-8",
    )
    for item in manifest["profiles"]:
        if item["profile_id"] == "coding-agent-qwen-atomic-workflow-stage6":
            item["profile_path"] = "config/model_training/coding-agent-qwen-atomic-workflow-stage6.json"
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    plan = module.smoke_eval_plan(manifest, "coding-agent-qwen-atomic-workflow-stage6", "")

    assert plan["adapter_repo"] == "owner/stage6"
    assert plan["eval_contract"]["contract_id"] == "stage6_contract_test"
    assert plan["prompts"][0]["id"] == "unseen_task"
    assert plan["promotion_gate"]["must_pass"] == ["unseen_task"]


def test_score_smoke_report_enforces_required_and_forbidden_markers(tmp_path: Path) -> None:
    module = _load_module()
    manifest = module.load_manifest(MANIFEST_PATH)
    report = {
        "responses": [
            {"id": "python_slot_map", "response": "def add(a, b):\n    return a + b\n\nslot map"},
            {"id": "ko_python_to_ru_rust", "response": "fn is_even(n: i32) -> bool { n % 2 == 0 }"},
        ]
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    score = module.score_smoke_report(report_path, manifest)

    assert score["passed"] == 2
    assert score["total"] == 2
    assert score["must_pass_ok"] is False
    assert score["promotion_ready"] is False


def test_reward_smoke_report_exports_rule_based_rlvr_signal(tmp_path: Path) -> None:
    module = _load_module()
    manifest = module.load_manifest(MANIFEST_PATH)
    report = {
        "profile_id": "coding-agent-qwen-atomic-workflow-stage6",
        "prompts": [
            {
                "id": "stage6_unseen_hex_trace",
                "prompt": "Trace crc_patch.",
                "required": ["crc_patch", "hex", "compute", "re-advance"],
                "forbidden": ["palindrome"],
            }
        ],
        "promotion_gate": {
            "minimum_pass_rate": 0.8,
            "must_pass": ["stage6_unseen_hex_trace"],
        },
        "responses": [
            {
                "id": "stage6_unseen_hex_trace",
                "response": "crc_patch uses a byte and hex trace, checks compute, then can re-advance.",
            }
        ],
    }
    report_path = tmp_path / "stage6_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    reward = module.reward_smoke_report(report_path, manifest)

    assert reward["schema_version"] == "geoseal_coding_training_reward_report_v1"
    assert reward["mean_reward"] == 1.0
    assert reward["promotion_ready"] is True
    assert reward["items"][0]["required_score"] == 1.0
    assert reward["items"][0]["forbidden_penalty"] == 0.0


def test_summarize_training_log_parses_pretty_completion_json() -> None:
    module = _load_module()
    summary = module.summarize_training_log("""
{'loss': '0.1773', 'grad_norm': '0.8329', 'learning_rate': '7.018e-07', 'epoch': '1.105'}
100%|██████████| 180/180 [14:32<00:00,  4.51s/it]
{
  "event": "training_complete",
  "summary": {
    "profile_id": "coding-agent-qwen-online-v2",
    "global_step": 180,
    "training_loss": 0.7010909987820519,
    "pushed_adapter": true
  }
}
""")

    assert summary["latest_loss"]["loss"] == 0.1773
    assert summary["progress"]["step"] == 180
    assert summary["training_complete"]["global_step"] == 180
    assert summary["training_complete"]["pushed_adapter"] is True


def test_render_smoke_eval_script_scores_geoseal_gates(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    manifest = module.load_manifest(MANIFEST_PATH)
    profile_path = tmp_path / "config" / "model_training" / "coding-agent-qwen-online-v2.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "coding-agent-qwen-online-v2",
                "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
                "hub": {"adapter_repo": "owner/default-adapter"},
            }
        ),
        encoding="utf-8",
    )
    for item in manifest["profiles"]:
        if item["profile_id"] == "coding-agent-qwen-online-v2":
            item["profile_path"] = "config/model_training/coding-agent-qwen-online-v2.json"
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    plan = module.smoke_eval_plan(manifest, "coding-agent-qwen-online-v2", "owner/adapter")

    script = module.render_smoke_eval_uv_script(plan)

    assert "PeftModel.from_pretrained" in script
    assert "smoke_eval_complete" in script
    assert "promotion_ready" in script
    assert "def is_even" in script
