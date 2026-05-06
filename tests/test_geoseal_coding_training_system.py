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
    assert "coding-agent-qwen-ca-opcode-exact-repair-v2" in ids
    assert "coding-agent-qwen-ca-geoseal-combined-repair-v3" in ids
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

    exact_repair = next(
        item for item in profiles["profiles"] if item["profile_id"] == "coding-agent-qwen-ca-opcode-exact-repair-v2"
    )
    assert exact_repair["stage"] == "ca_opcode_exact_repair"
    assert exact_repair["exists"] is True

    combined_repair = next(
        item for item in profiles["profiles"] if item["profile_id"] == "coding-agent-qwen-ca-geoseal-combined-repair-v3"
    )
    assert combined_repair["stage"] == "ca_geoseal_combined_repair"
    assert combined_repair["exists"] is True


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


def test_dispatcher_renders_constrained_gate_scaffold_when_profile_requests_it() -> None:
    dispatcher_path = ROOT / "scripts" / "system" / "dispatch_coding_agent_hf_job.py"
    spec = importlib.util.spec_from_file_location("dispatch_coding_agent_hf_job", dispatcher_path)
    assert spec and spec.loader
    dispatcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dispatcher)
    profile = json.loads(
        (ROOT / "config" / "model_training" / "coding-agent-qwen-command-harmony-v5-signal-repair-v1.json").read_text(
            encoding="utf-8"
        )
    )

    script = dispatcher.render_uv_training_script(profile)

    assert "CONSTRAINED_GATE_SCAFFOLD = bool" in script
    assert "CONSTRAINED_PROMPT_PREFIX = bool" in script
    assert '"constrained_gate_scaffold": true' in script
    assert "def _gate_required_prefix(prompt):" in script
    assert "REQUIRED_MARKERS=" in script
    assert "def _prompt_with_required_prefix(prompt):" in script
    assert "Your first line must be exactly: REQUIRED_MARKERS=" in script
    assert "Never include these forbidden strings in your answer" not in script
    assert "Some boundary strings are hidden by the evaluator" in script
    assert "raw_pass_rate" in script
    assert "raw_missing_required" in script
    assert "constrained gate prefix would trigger forbidden token" in script
    assert "raw_response = _gate_generate(prompt" in script
    assert "def _scaffolded_gate_response(prompt, raw_response):" in script
    assert "raw model output stored in raw_response" in script


def test_chemistry_profile_has_non_empty_hf_promotion_contract() -> None:
    dispatcher_path = ROOT / "scripts" / "system" / "dispatch_coding_agent_hf_job.py"
    spec = importlib.util.spec_from_file_location("dispatch_coding_agent_hf_job", dispatcher_path)
    assert spec and spec.loader
    dispatcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dispatcher)

    profile = json.loads(
        (ROOT / "config" / "model_training" / "scbe-chemistry-0.5b-qlora.json").read_text(encoding="utf-8")
    )
    contract_path = ROOT / profile["evaluation"]["contract_path"]
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    script = dispatcher.render_uv_training_script(profile)

    assert contract["contract_id"] == "chemistry_verification_unseen_eval_v1"
    assert len(contract["prompts"]) >= 5
    assert "chem_eval_pentavalent_carbon_reject" in contract["thresholds"]["must_pass"]
    assert "chemistry_verification_unseen_eval_v1" in script
    assert '"n_prompts": 0' not in script
    assert "chem_eval_ethanol_route" in script
    assert 'PROFILE.get("system_prompt"' in script
    assert "Run the chemistry path explicitly" in script


def test_dispatcher_honors_explicit_warmup_steps_without_deprecated_ratio() -> None:
    dispatcher_path = ROOT / "scripts" / "system" / "dispatch_coding_agent_hf_job.py"
    spec = importlib.util.spec_from_file_location("dispatch_coding_agent_hf_job", dispatcher_path)
    assert spec and spec.loader
    dispatcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dispatcher)

    profile = json.loads(
        (ROOT / "config" / "model_training" / "scbe-chemistry-0.5b-qlora.json").read_text(encoding="utf-8")
    )
    script = dispatcher.render_uv_training_script(profile)

    assert 'if "warmup_steps" in train_cfg:' in script
    assert 'warmup_kwargs["warmup_steps"]' in script
    assert "warmup_ratio=float(train_cfg.get" not in script


def test_dispatcher_defaults_to_l4x1_and_carries_idempotency_key(tmp_path: Path) -> None:
    dispatcher_path = ROOT / "scripts" / "system" / "dispatch_coding_agent_hf_job.py"
    spec = importlib.util.spec_from_file_location("dispatch_coding_agent_hf_job", dispatcher_path)
    assert spec and spec.loader
    dispatcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dispatcher)

    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "idempotency-test",
                "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
                "dataset": {"root": "training-data/sft", "train_files": [], "eval_files": []},
                "hub": {"adapter_repo": "owner/adapter", "token_env": "HF_TOKEN"},
                "training": {},
                "execution": {},
            }
        ),
        encoding="utf-8",
    )

    packet = dispatcher.build_packet(profile_path=profile_path, artifact_root=tmp_path / "runs")

    assert packet["hf"]["flavor"] == "l4x1"
    assert len(packet["idempotency_key"]) == 64
    assert f"SCBE_IDEMPOTENCY_KEY={packet['idempotency_key']}" in packet["command"]


def test_dispatcher_idempotency_marker_skips_duplicate_job(tmp_path: Path) -> None:
    dispatcher_path = ROOT / "scripts" / "system" / "dispatch_coding_agent_hf_job.py"
    spec = importlib.util.spec_from_file_location("dispatch_coding_agent_hf_job", dispatcher_path)
    assert spec and spec.loader
    dispatcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dispatcher)

    run_dir = tmp_path / "runs" / "profile" / "20260506T000000Z"
    run_dir.mkdir(parents=True)
    key = "a" * 64
    marker_dir = tmp_path / "runs" / "_idempotency"
    marker_dir.mkdir()
    (marker_dir / f"{key}.json").write_text(
        json.dumps({"packet_path": "previous/job_packet.json", "dispatch": {"job_id": "job-12345678"}}),
        encoding="utf-8",
    )
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps({"profile_id": "profile", "hub": {}}), encoding="utf-8")
    packet = {
        "hf": {"cli": "hf", "token_present": True},
        "profile_path": str(profile_path),
        "run_dir": str(run_dir),
        "idempotency_key": key,
    }

    out = dispatcher.dispatch_packet(packet)

    assert out["dispatch"]["idempotent_skip"] is True
    assert out["dispatch"]["job_id"] == "job-12345678"
    assert out["dataset_uploads"] == []


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
    assert plan["system_prompt"] == "You are an SCBE-AETHERMOORE GeoSeal coding agent. Preserve route/slot semantics."
    assert plan["max_new_tokens"] == 220
    assert plan["constrained_gate_scaffold"] is False
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
    assert plan["system_prompt"] == "You are an SCBE-AETHERMOORE GeoSeal coding agent. Preserve route/slot semantics."
    assert plan["eval_contract"]["contract_id"] == "stage6_contract_test"
    assert plan["prompts"][0]["id"] == "unseen_task"
    assert plan["promotion_gate"]["must_pass"] == ["unseen_task"]


def test_smoke_eval_plan_carries_constrained_scaffold_flag(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    manifest = module.load_manifest(MANIFEST_PATH)
    profile_path = tmp_path / "config" / "model_training" / "coding-agent-qwen-geoshell-pair-agent-v1.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "coding-agent-qwen-geoshell-pair-agent-v1",
                "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
                "hub": {"adapter_repo": "owner/geoshell"},
                "evaluation": {"constrained_gate_scaffold": True, "constrained_prompt_prefix": True},
            }
        ),
        encoding="utf-8",
    )
    for item in manifest["profiles"]:
        if item["profile_id"] == "coding-agent-qwen-geoshell-pair-agent-v1":
            item["profile_path"] = "config/model_training/coding-agent-qwen-geoshell-pair-agent-v1.json"
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    plan = module.smoke_eval_plan(manifest, "coding-agent-qwen-geoshell-pair-agent-v1", "")
    script = module.render_smoke_eval_uv_script(plan)

    assert plan["constrained_gate_scaffold"] is True
    assert plan["constrained_prompt_prefix"] is True
    assert "def _gate_required_prefix(item: dict) -> str:" in script
    assert "def _prompt_with_required_prefix(item: dict) -> str:" in script
    assert "required-items:" in script
    assert "Your first line must be exactly: REQUIRED_MARKERS=" in script
    assert "Your second line must be exactly: REQUIRED_CHECKLIST=" in script
    assert "Do not translate, rename, pluralize, omit, or replace any REQUIRED_MARKERS value." in script
    assert "raw_response" in script
    assert "raw_pass_rate" in script
    assert "raw_missing_required" in script
    assert "scaffolded" in script
    assert "constrained gate prefix would trigger forbidden token" in script


def test_smoke_eval_plan_prefers_profile_evaluation_token_budget(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    manifest = module.load_manifest(MANIFEST_PATH)
    profile_path = tmp_path / "config" / "model_training" / "coding-agent-qwen-budget-test.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "coding-agent-qwen-budget-test",
                "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
                "training": {"max_new_tokens": 220},
                "hub": {"adapter_repo": "owner/budget-test"},
                "evaluation": {"max_new_tokens": 180},
            }
        ),
        encoding="utf-8",
    )
    manifest["profiles"].append(
        {
            "profile_id": "coding-agent-qwen-budget-test",
            "profile_path": "config/model_training/coding-agent-qwen-budget-test.json",
        }
    )
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    plan = module.smoke_eval_plan(manifest, "coding-agent-qwen-budget-test", "")
    script = module.render_smoke_eval_uv_script(plan)

    assert plan["max_new_tokens"] == 180
    assert "max_new_tokens=max_new_tokens" in script
    assert 'max_new_tokens=int(PLAN.get("max_new_tokens", 220))' not in script


def test_scale16_gate_profile_uses_v3_contract() -> None:
    module = _load_module()
    manifest = module.load_manifest(MANIFEST_PATH)

    plan = module.smoke_eval_plan(manifest, "coding-agent-qwen-geoshell-pair-agent-dpo-v4-scale16-gate", "")

    assert plan["eval_contract"]["contract_id"] == "geoshell_pair_agent_eval_v3_scale16"
    assert plan["constrained_prompt_prefix"] is True
    assert plan["max_new_tokens"] == 220
    assert len(plan["prompts"]) == 16
    assert plan["promotion_gate"]["minimum_pass_rate"] == 1.0
    assert "release_readiness_packet" in plan["promotion_gate"]["must_pass"]


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


def test_extract_gate_report_and_boss_retry_plan_target_failed_mechanics(tmp_path: Path) -> None:
    module = _load_module()
    log_text = """
noise
{"event": "gate_report", "report": {"contract_id": "stage6_atomic_workflow_unseen_eval_v1", "n_total": 5, "n_pass": 2, "pass_rate": 0.4, "minimum_pass_rate": 0.8, "must_pass_results": {"stage6_unseen_hex_trace": false}, "results": [{"id": "stage6_unseen_hex_trace", "ok": false, "missing_required": ["compute"]}, {"id": "stage6_unseen_cost_propagation", "ok": false, "missing_required": ["sample_soil", "send_digest"]}, {"id": "stage6_unseen_lane_separation", "ok": true}]}}
"""

    report = module.extract_gate_report(log_text)
    assert report is not None
    plan = module.build_boss_retry_plan(report, profile_id="coding-agent-qwen-stage6-repair-v12")

    assert plan["schema_version"] == "geoseal_stage6_boss_retry_plan_v1"
    assert plan["score"]["promotion_ready"] is False
    assert plan["strategy"] == "constrained_decoding_plus_targeted_dpo"
    targets = {item["id"]: item for item in plan["repair_targets"]}
    assert targets["stage6_unseen_hex_trace"]["kind"] == "byte_hex_compute_trace"
    assert targets["stage6_unseen_hex_trace"]["must_pass"] is True
    assert targets["stage6_unseen_cost_propagation"]["recommended_rows"] == 48
    assert "aggregate micro-skill evidence" in plan["experience_model"]["definition"]
    assert "Do not copy held-out prompt text into training data." in plan["next_actions"]

    out = tmp_path / "boss_retry.json"
    wrapped = tmp_path / "gate_report.json"
    wrapped.write_text(json.dumps({"event": "gate_report", "report": report}), encoding="utf-8")
    written = module.boss_retry_plan_from_report(wrapped, profile_id="coding-agent-qwen-stage6-repair-v12", output=out)
    assert out.exists()
    assert written["output_path"] == str(out)


def test_extract_smoke_eval_event_parses_pretty_json_and_summarizes_failures() -> None:
    module = _load_module()
    log_text = """
startup noise
{
  "event": "smoke_eval_complete",
  "summary": {
    "base_model": "Qwen/base",
    "adapter_repo": "owner/adapter",
    "scaffolded": true,
    "raw_passed": 1,
    "raw_pass_rate": 0.5,
    "passed": 2,
    "total": 2,
    "pass_rate": 1.0,
    "must_pass_ok": true,
    "promotion_ready": true
  },
  "results": [
    {
      "id": "ok_case",
      "raw_passed": true,
      "passed": true,
      "raw_missing_required": [],
      "raw_present_forbidden": [],
      "missing_required": [],
      "present_forbidden": []
    },
    {
      "id": "repair_case",
      "raw_passed": false,
      "passed": true,
      "raw_missing_required": ["ownership"],
      "raw_present_forbidden": [],
      "missing_required": [],
      "present_forbidden": []
    }
  ]
}
tail noise
"""

    event = module.extract_smoke_eval_event(log_text)
    assert event is not None
    summary = module.summarize_smoke_eval_event(event)

    assert summary["adapter_repo"] == "owner/adapter"
    assert summary["constrained_prompt_prefix"] is False
    assert summary["raw_passed"] == 1
    assert summary["raw_total"] == 2
    assert summary["raw_pass_rate"] == 0.5
    assert summary["raw_failures"] == [
        {
            "id": "repair_case",
            "raw_missing_required": ["ownership"],
            "raw_present_forbidden": [],
        }
    ]
    assert summary["scaffold_failures"] == []
    assert summary["next_action"] == "repair_raw_failures_before_promotion"


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


def test_assess_job_health_marks_running_loss_signal_as_safe_to_continue() -> None:
    module = _load_module()

    health = module.assess_job_health(
        {"stage": "RUNNING"},
        {
            "returncode": 0,
            "tail": "",
            "summary": {
                "latest_loss": {"loss": 1.737, "epoch": 0.1667},
                "progress": {"step": 57, "max_steps": 420, "percent": 14},
            },
        },
    )

    assert health["state"] == "running_with_training_signal"
    assert health["safe_for_full_train"] is True
    assert "terminal gate" in health["recommendation"]


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
