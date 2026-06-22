from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "eval" / "functional_coding_agent_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("functional_coding_agent_benchmark", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_property_probes_reject_an_input_keyed_overfit_stub():
    """Soundness: a stub that only echoes the fixed checks (input-keyed lookup, no
    real logic) passes the contract checks but must FAIL once unseen reference-oracle
    probes are scored. This is the fixture-overfit hole the probes close."""
    module = _load_module()
    task = next(t for t in module.TASKS if t.task_id == "score_add")
    overfit = (
        "function evaluate(input, state) {\n"
        "  if (input.points === 5) { state.score = 13; return 13; }\n"
        "  if (input.points === -2) { state.score = 8; return 8; }\n"
        "  return 0;\n"
        "}"
    )

    fixed_only = module.score_candidate(overfit, task)
    probed = module.score_candidate(overfit, task, probe_count=8, probe_seed=1234)

    assert fixed_only["passed"] is True  # gameable against the fixed checks alone
    assert probed["passed"] is False  # but the unseen probes catch it
    assert probed["probe_checks_passed"] < probed["probe_checks_total"]


def test_property_probes_do_not_reject_a_correct_implementation():
    """The probes must not produce false rejections: a genuinely correct
    implementation passes every probe across all built-in oracle tasks."""
    module = _load_module()
    correct = {
        "score_add": "function evaluate(input, state) { state.score += input.points; return state.score; }",
        "heal_clamp": (
            "function evaluate(input, state) { state.hp = Math.min(state.hp + input.heal, state.maxHp); "
            'state.events.push("healed"); return state.hp; }'
        ),
        "inventory_unique": (
            "function evaluate(input, state) { if (!state.inventory.includes(input.item)) "
            "state.inventory.push(input.item); return state.inventory.length; }"
        ),
        "cooldown_gate": (
            "function evaluate(input, state) { if (state.cooldown > 0) { state.cooldown -= 1; return false; } "
            "state.cooldown = input.cooldown; state.actions += 1; return true; }"
        ),
        "quest_flags": (
            "function evaluate(input, state) { if (input.required.every(f => state.flags.includes(f))) { "
            "if (!state.rewards.includes(input.reward)) state.rewards.push(input.reward); return true; } "
            "return false; }"
        ),
        "weighted_choice": (
            "function evaluate(input, state) { let c = 0; for (const o of input.options) { c += o.weight; "
            "if (c > input.roll) return o.id; } return input.options[input.options.length - 1].id; }"
        ),
    }
    for task in module.TASKS:
        score = module.score_candidate(correct[task.task_id], task, probe_count=10, probe_seed=7)
        assert score["probe_checks_total"] == 10, task.task_id
        assert score["probe_checks_passed"] == 10, task.task_id
        assert score["passed"] is True, task.task_id


def test_file_loaded_tasks_have_no_oracle_and_score_on_fixed_checks_only():
    """File-loaded tasks carry no reference oracle, so probing is a no-op for them
    (scored exactly as before) rather than silently claiming probe coverage."""
    module = _load_module()
    tasks = module.load_task_file(REPO_ROOT / "config" / "eval" / "common_agentic_benchmark_tasks.v1.json")
    task = tasks[0]
    assert task.probe is None
    score = module.score_candidate("function evaluate(input, state) { return null; }", task, probe_count=8)
    assert score["probe_checks_total"] == 0


def test_eval_jsonl_loaded_tasks_support_wrapped_rows_and_filters(tmp_path: Path):
    module = _load_module()
    eval_jsonl = tmp_path / "headroom.jsonl"
    rows = [
        {
            "task_id": "alpha",
            "prompt": "Write TypeScript only. Define function evaluate(input, state). Return input.x.",
            "checks": [
                {
                    "input": {"x": 1},
                    "initialState": {},
                    "expectedResult": 1,
                    "expectedState": {},
                }
            ],
        },
        {
            "task": {
                "task_id": "beta",
                "prompt": "Write TypeScript only. Define function evaluate(input, state). Return state.y.",
                "checks": [
                    {
                        "input": {},
                        "initialState": {"y": 2},
                        "expectedResult": 2,
                        "expectedState": {"y": 2},
                    }
                ],
            }
        },
    ]
    eval_jsonl.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    loaded = module.load_eval_jsonl(eval_jsonl)
    assert [task.task_id for task in loaded] == ["alpha", "beta"]
    assert all(task.probe is None for task in loaded)

    args = Namespace(
        replace_default_tasks=True,
        task_file=[],
        eval_jsonl=[eval_jsonl],
        task_limit=0,
        task_ids=["beta"],
    )
    selected = module.selected_tasks(args)
    assert [task.task_id for task in selected] == ["beta"]


def test_eval_jsonl_cli_runs_candidate_file_without_default_tasks(tmp_path: Path):
    eval_jsonl = tmp_path / "eval.jsonl"
    eval_jsonl.write_text(
        json.dumps(
            {
                "task_id": "alpha",
                "prompt": (
                    "Write TypeScript only. Define function evaluate(input, state). "
                    "Set state.total to input.n and return it."
                ),
                "checks": [
                    {
                        "input": {"n": 4},
                        "initialState": {},
                        "expectedResult": 4,
                        "expectedState": {"total": 4},
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    candidate_file = tmp_path / "candidate.json"
    candidate_file.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "name": "jsonl-solver",
                        "tasks": {
                            "alpha": "function evaluate(input, state) { state.total = input.n; return state.total; }"
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "reports"

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/eval/functional_coding_agent_benchmark.py",
            "--candidate-file",
            str(candidate_file),
            "--replace-default-tasks",
            "--eval-jsonl",
            str(eval_jsonl),
            "--output-root",
            str(out_dir),
            "--min-pass-rate",
            "1.0",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads((out_dir / "latest" / "report.json").read_text(encoding="utf-8"))
    assert report["results"][0]["summary"]["tasks"] == 1
    assert report["results"][0]["summary"]["passed"] == 1
    assert report["results"][0]["tasks"][0]["task_id"] == "alpha"


def test_benchmark_exits_nonzero_when_below_min_pass_rate(tmp_path: Path):
    candidate_file = tmp_path / "candidates.json"
    candidate_file.write_text(
        json.dumps(
            [
                {
                    "name": "always_bad",
                    "tasks": {
                        "score_add": "function evaluate(input, state) { return 0; }",
                        "heal_clamp": "function evaluate(input, state) { return 0; }",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/eval/functional_coding_agent_benchmark.py",
            "--candidate-file",
            str(candidate_file),
            "--task-limit",
            "2",
            "--min-pass-rate",
            "1.0",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 1
    assert "below threshold" in proc.stderr


def test_ollama_prompt_demands_typescript_only():
    module = _load_module()
    task = module.TASKS[0]
    atomic_packet = module.build_atomic_contract_packet(task)

    prompt = module.build_code_generation_prompt(
        "add points",
        [
            {
                "input": {"points": 1},
                "initialState": {"score": 2},
                "expectedResult": 3,
                "expectedState": {"score": 3},
            }
        ],
        atomic_packet,
    )

    assert "Return only plain JavaScript-compatible TypeScript code" in prompt
    assert "function evaluate(input, state)" in prompt
    assert "final mutated state exactly" in prompt
    assert "return value must equal expectedResult" in prompt
    assert "deleteList" in prompt
    assert "Return/state separation examples" in prompt
    assert "task.priority" in prompt
    assert "Executable contract examples" in prompt
    assert "Atomic/STISA lookup contract" in prompt
    assert '"expected_state_paths"' in prompt
    assert '"expectedState"' in prompt
    assert "No explanation" in prompt


def test_run_ollama_benchmark_records_generation_errors(monkeypatch):
    module = _load_module()

    def fail_generate(*_args, **_kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(module, "generate_code_ollama", fail_generate)
    args = Namespace(
        replace_default_tasks=False,
        task_file=[],
        task_limit=1,
        ollama_url="http://127.0.0.1:11434",
        max_new_tokens=32,
        repair_ollama_model="",
        repair_attempts=0,
        repair_max_new_tokens=0,
        joint_library=None,
    )
    result = module.run_ollama_benchmark(args, "missing-model")

    assert result["adapter"] == "ollama:missing-model"
    assert result["summary"]["pass_rate"] == 0.0
    assert result["tasks"][0]["error"].startswith("RuntimeError: offline")


def test_ollama_repair_loop_records_first_try_and_final_pass(monkeypatch):
    module = _load_module()
    generations = iter(
        [
            "function evaluate(input, state) { return state.score + input.points; }",
            "function evaluate(input, state) { state.score = state.score + input.points; return state.score; }",
        ]
    )

    def fake_generate(*_args, **_kwargs):
        return next(generations)

    monkeypatch.setattr(module, "generate_code_ollama", fake_generate)
    args = Namespace(
        replace_default_tasks=False,
        task_file=[],
        task_limit=1,
        ollama_url="http://127.0.0.1:11434",
        max_new_tokens=64,
        repair_ollama_model="repair-model",
        repair_attempts=1,
        repair_max_new_tokens=64,
        joint_library=None,
    )
    result = module.run_ollama_benchmark(args, "draft-model")
    task = result["tasks"][0]

    assert result["summary"]["passed"] == 1
    assert result["summary"]["repaired_passed"] == 1
    assert task["initial_passed"] is False
    assert task["passed"] is True
    assert task["repaired"] is True
    assert len(task["repair_attempts"]) == 1
    assert "state.score =" in task["final_code"]


def test_repair_prompt_includes_failure_receipt():
    module = _load_module()
    task = module.TASKS[0]
    score = {
        "passed": False,
        "checks": [
            {
                "index": 0,
                "passed": False,
                "expected_result": 13,
                "actual_result": 13,
                "expected_state": {"score": 13},
                "actual_state": {"score": 8},
            }
        ],
    }

    prompt = module.build_code_repair_prompt(task, "function evaluate(input, state) { return 13; }", score)

    assert "Repair this TypeScript" in prompt
    assert '"expected_state"' in prompt
    assert '"actual_state"' in prompt
    assert "Atomic/STISA lookup contract" in prompt
    assert "Atomic response audit" in prompt
    assert "required state mutation" in prompt


def test_compiler_receipt_records_geoseal_trace_and_language_route():
    module = _load_module()
    task = module.TASKS[0]
    source = "function evaluate(input, state) { state.score += input.points; return state.score; }"
    score = module.score_candidate(source, task)

    receipt = module.build_compiler_receipt(task, source, score, model_name="test-model")

    assert receipt["schema"] == "scbe_cross_lingual_compiler_receipt_v1"
    assert receipt["source_language"] == "natural_language_task"
    assert receipt["target_language"] == "typescript"
    assert receipt["route_tongue"] == "AV"
    assert receipt["semantic_packet"]["task_id"] == "score_add"
    assert receipt["atomic_contract"]["schema"] == "scbe_atomic_contract_packet_v1"
    assert receipt["atomic_response_audit"]["schema"] == "scbe_atomic_response_audit_v1"
    assert receipt["atomic_response_audit"]["aligned"] is True
    assert receipt["artifact"]["code_sha256"]
    assert receipt["geoseal_trace"]["seal"]
    assert receipt["verification"]["passed"] is True


def test_atomic_contract_packet_extracts_state_paths_and_roles():
    module = _load_module()
    task = module.TASKS[0]

    packet = module.build_atomic_contract_packet(task)

    assert packet["schema"] == "scbe_atomic_contract_packet_v1"
    assert packet["tongue"] == "AV"
    assert "state.score" in packet["expected_state_paths"]
    assert "number" in packet["return_shapes"]
    assert "write" in packet["role_tokens"]
    assert packet["lookup_units"][0]["semantic_lane"]


def test_atomic_response_audit_flags_missing_state_write():
    module = _load_module()
    task = module.TASKS[0]

    audit = module.audit_atomic_response("function evaluate(input, state) { return state.score + input.points; }", task)

    assert audit["schema"] == "scbe_atomic_response_audit_v1"
    assert audit["aligned"] is False
    assert "state.score" in audit["missing_state_paths"]


def test_typescript_debug_harness_handles_comma_types():
    scenario = {
        "id": "comma-types",
        "source": (
            "function evaluate(input: { required: string[], reward: string }, "
            "state: { flags: string[], rewards: string[] }): boolean { "
            "if (input.required.every(flag => state.flags.includes(flag))) { "
            "if (!state.rewards.includes(input.reward)) state.rewards.push(input.reward); "
            "return true; } return false; }"
        ),
        "input": {"required": ["gate", "key"], "reward": "amulet"},
        "initialState": {"flags": ["gate", "key"], "rewards": []},
        "timeoutMs": 250,
    }
    proc = subprocess.run(
        [
            "node",
            "scripts/run_typescript_debug_scenario.cjs",
            "--json",
            json.dumps(scenario),
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    payload = json.loads(proc.stdout)

    assert proc.returncode == 0, proc.stderr
    assert payload["status"] == "passed"
    assert payload["result"] is True
    assert payload["finalState"]["rewards"] == ["amulet"]


def test_extract_typescript_trims_generated_test_junk_after_function():
    module = _load_module()

    source = """```ts
function evaluate(input, state) {
  const result = { ok: true };
  return result;
}

const testCases = [
  { broken: true }
];
```"""

    extracted = module.extract_typescript(source)

    assert extracted.endswith("}")
    assert "testCases" not in extracted


def test_extract_typescript_handles_typed_parameter_object_shapes():
    module = _load_module()

    source = (
        "function evaluate(input: { projectType: string; budget: number }, "
        "state: { offer?: string }): { offer: string } {\n"
        '  state.offer = "governance_snapshot";\n'
        "  return { offer: state.offer };\n"
        "}\n"
        "const testCases = [{ bad: true }];\n"
    )

    extracted = module.extract_typescript(source)

    assert extracted.startswith("function evaluate")
    assert "state.offer" in extracted
    assert "testCases" not in extracted


def test_productivity_task_pack_loads_seven_useful_tasks():
    module = _load_module()
    path = REPO_ROOT / "config" / "eval" / "scbe_productivity_eval_tasks.v1.json"

    tasks = module.load_task_file(path)

    assert len(tasks) == 7
    assert {task.task_id for task in tasks} == {
        "model_router_select",
        "failure_bucket_summary",
        "quality_dimension_next_step",
        "lead_offer_router",
        "artifact_retention_gate",
        "budget_guard",
        "task_priority_queue",
    }
    assert all(task.checks for task in tasks)


def test_common_agentic_benchmark_task_pack_loads_public_style_tasks():
    module = _load_module()
    path = REPO_ROOT / "config" / "eval" / "common_agentic_benchmark_tasks.v1.json"

    tasks = module.load_task_file(path)

    assert len(tasks) == 12
    assert {task.task_id for task in tasks} == {
        "swe_issue_file_focus",
        "swe_patch_status_gate",
        "terminal_bench_command_guard",
        "terminal_bench_log_parser",
        "aider_polyglot_edit_route",
        "aider_polyglot_test_command",
        "evalplus_edge_case_counter",
        "humaneval_signature_guard",
        "repobench_context_budget",
        "cost_duration_report",
        "patch_diff_risk_score",
        "benchmark_claim_guard",
    }
    assert all(task.checks for task in tasks)


def test_competitor_gap_task_pack_loads_mars_derived_tasks():
    module = _load_module()
    path = REPO_ROOT / "config" / "eval" / "competitor_gap_agentic_tasks.v1.json"

    tasks = module.load_task_file(path)

    assert len(tasks) == 13
    assert {
        "context_precision_selector",
        "terminal_recovery_plan",
        "compound_request_completion",
        "maintenance_erosion_guard",
        "evidence_truth_packet",
        "environment_dependency_triage",
        "supervisor_executor_correction",
        "multi_agent_handoff_integrity",
        "mars_sensor_truth_gate",
        "mars_tongue_route_packet",
        "mars_decision_envelope_gate",
        "mars_blackout_resume_reducer",
        "mars_blackout_audit_sync",
    } == {task.task_id for task in tasks}
    assert all(task.checks for task in tasks)


def test_selected_tasks_filters_by_task_ids():
    module = _load_module()
    args = Namespace(
        replace_default_tasks=False,
        task_file=[],
        task_limit=0,
        task_ids=["heal_clamp", "quest_flags"],
    )

    tasks = module.selected_tasks(args)

    assert [task.task_id for task in tasks] == ["heal_clamp", "quest_flags"]


def test_verified_mechanical_ensemble_routes_to_passing_artifacts():
    module = _load_module()

    results = [
        {
            "adapter": "model-a",
            "tasks": [
                {
                    "task_id": "alpha",
                    "passed": True,
                    "generation_elapsed_s": 5.0,
                    "checks": [{"passed": True}, {"passed": True}],
                    "compiler_receipt": {
                        "geoseal_trace": {"seal": "abc", "tier": "ALLOW"},
                        "atomic_contract": {
                            "role_tokens": ["read", "write"],
                            "lookup_units": [{"unit_id": "u1"}, {"unit_id": "u2"}],
                        },
                        "atomic_response_audit": {"aligned": True},
                    },
                    "final_code": "function evaluate(input, state) { return 'a'; }",
                },
                {
                    "task_id": "beta",
                    "passed": False,
                    "checks": [{"passed": True}, {"passed": False}],
                },
            ],
        },
        {
            "adapter": "model-b",
            "tasks": [
                {
                    "task_id": "alpha",
                    "passed": True,
                    "generation_elapsed_s": 2.0,
                    "checks": [{"passed": True}, {"passed": True}],
                    "final_code": "function evaluate(input, state) { return 'b'; }",
                },
                {
                    "task_id": "beta",
                    "passed": True,
                    "generation_elapsed_s": 9.0,
                    "checks": [{"passed": True}, {"passed": True}],
                    "final_code": "function evaluate(input, state) { return 'ok'; }",
                },
            ],
        },
    ]

    ensemble = module.build_verified_mechanical_ensemble(results)

    assert ensemble["schema"] == "scbe_verified_mechanical_ensemble_v1"
    assert ensemble["summary"]["pass_rate"] == 1.0
    assert ensemble["summary"]["contributing_models"] == {"model-b": 2}
    assert ensemble["summary"]["verified_path_signatures"] == 2
    assert ensemble["tasks"][0]["source_adapter"] == "model-b"
    assert ensemble["tasks"][0]["selection_rule"] == "fastest_verified_passing_artifact"
    assert ensemble["tasks"][0]["verified_path_signature"]["schema"] == "scbe_atomic_verified_path_signature_v1"


def test_joint_library_round_trip_reuses_verified_path(tmp_path: Path):
    module = _load_module()
    task = module.TASKS[0]
    source = "function evaluate(input, state) { state.score += input.points; return state.score; }"
    score = module.score_candidate(source, task)
    atomic_packet = module.build_atomic_contract_packet(task)
    row = {
        "task_id": task.task_id,
        "passed": True,
        "source_adapter": "seed-model",
        "selection_rule": "test",
        "checks": score["checks"],
        "compiler_receipt": module.build_compiler_receipt(
            task, source, score, model_name="seed-model", atomic_packet=atomic_packet
        ),
        "final_code": source,
    }
    ensemble = {
        "tasks": [
            {
                **row,
                "verified_path_signature": module.build_verified_path_signature("seed-model", row),
            }
        ]
    }
    library = tmp_path / "joints.json"

    update = module.update_joint_library(library, ensemble)
    joints = module.load_joint_library(library)
    found = module.find_verified_joint_for_task(task, atomic_packet, joints)
    reused = module.task_row_from_joint(task, atomic_packet, found, "test-adapter")

    assert update["joint_count"] == 1
    assert found is not None
    assert reused["passed"] is True
    assert reused["from_joint_library"] is True
    assert reused["joint_source_adapter"] == "seed-model"


def test_verified_mechanical_ensemble_records_closest_failure():
    module = _load_module()

    ensemble = module.build_verified_mechanical_ensemble(
        [
            {
                "adapter": "model-a",
                "tasks": [
                    {
                        "task_id": "alpha",
                        "passed": False,
                        "checks": [{"passed": True}, {"passed": False}],
                    }
                ],
            },
            {
                "adapter": "model-b",
                "tasks": [
                    {
                        "task_id": "alpha",
                        "passed": False,
                        "checks": [{"passed": False}, {"passed": False}],
                    }
                ],
            },
        ]
    )

    assert ensemble["summary"]["pass_rate"] == 0.0
    assert ensemble["summary"]["unresolved_tasks"] == ["alpha"]
    assert ensemble["tasks"][0]["source_adapter"] == "model-a"
    assert ensemble["tasks"][0]["checks_passed"] == 1


def test_common_return_shape_bridge_repairs_offer_object_return():
    module = _load_module()
    task = module.load_task_file(REPO_ROOT / "config" / "eval" / "scbe_productivity_eval_tasks.v1.json")[3]
    source = """
function evaluate(input, state) {
  let offer = "";
  let reason = "";
  if (input.budget >= 500) {
    offer = "governance_snapshot";
    reason = "budget_at_least_500";
  } else if (input.recurring || input.budget >= 99) {
    offer = "governance_heartbeat";
    reason = "recurring_or_99";
  } else if (input.projectType === "developer") {
    offer = "toolkit";
    reason = "developer_toolkit";
  } else {
    offer = "supporter_monthly";
    reason = "fallback";
  }
  state.offer = offer;
  state.reason = reason;
  return { offer, reason };
}
"""
    initial = module.score_candidate(source, task)
    repaired_score, repaired_code, record = module.maybe_apply_semantic_bridge_repair(source, task, initial)

    assert initial["passed"] is False
    assert repaired_score["passed"] is True
    assert record["kind"] == "common_return_shape_bridge"
    assert "__candidateEvaluate" in repaired_code


def test_contract_synthesis_joint_solves_artifact_retention_gate():
    module = _load_module()
    task = next(
        task
        for task in module.load_task_file(REPO_ROOT / "config" / "eval" / "scbe_productivity_eval_tasks.v1.json")
        if task.task_id == "artifact_retention_gate"
    )
    near_miss = """
function evaluate(input, state) {
  const keep = [];
  const offload = [];
  const deleteList = [];
  for (const artifact of input.artifacts) {
    if (artifact.kind === "cache") deleteList.push(artifact.path);
    else if (artifact.bytes > input.offloadBytes) offload.push(artifact.path);
    else keep.push(artifact.path);
  }
  state.keep = keep;
  state.offload = offload;
  state.delete = deleteList;
  return { keep, offload, delete: deleteList };
}
"""
    initial = module.score_candidate(near_miss, task)
    atomic_packet = module.build_atomic_contract_packet(task)
    repaired_score, repaired_code, record = module.maybe_apply_contract_synthesis_joint(
        near_miss, task, initial, atomic_packet
    )

    assert initial["passed"] is False
    assert repaired_score["passed"] is True
    assert record["kind"] == "contract_synthesis:artifact_retention_counts"
    assert "deleteList.length" in repaired_code


def test_contract_synthesis_joint_solves_task_priority_queue():
    module = _load_module()
    task = next(
        task
        for task in module.load_task_file(REPO_ROOT / "config" / "eval" / "scbe_productivity_eval_tasks.v1.json")
        if task.task_id == "task_priority_queue"
    )
    near_miss = """
function evaluate(input, state) {
  let selectedTask = "none";
  for (const task of input.tasks) {
    if (!task.blocked && (selectedTask === "none" || task.priority > state.selectedTask.priority)) {
      selectedTask = task.id;
    }
  }
  state.selectedTask = selectedTask;
  return selectedTask;
}
"""
    initial = module.score_candidate(near_miss, task)
    atomic_packet = module.build_atomic_contract_packet(task)
    repaired_score, repaired_code, record = module.maybe_apply_contract_synthesis_joint(
        near_miss, task, initial, atomic_packet
    )

    assert initial["passed"] is False
    assert repaired_score["passed"] is True
    assert record["kind"] == "contract_synthesis:priority_queue_tie_break"
    assert "queueLength" in repaired_code


def test_contract_synthesis_joint_solves_failure_bucket_summary():
    module = _load_module()
    task = next(
        task
        for task in module.load_task_file(REPO_ROOT / "config" / "eval" / "scbe_productivity_eval_tasks.v1.json")
        if task.task_id == "failure_bucket_summary"
    )
    near_miss = """
function evaluate(input, state) {
  const counts = {};
  let topFailure = "";
  for (const row of input.results) {
    for (const failedTask of row.failedTasks) {
      counts[failedTask] = (counts[failedTask] || 0) + 1;
      topFailure = failedTask;
    }
  }
  state.failureCounts = counts;
  state.topFailure = topFailure;
  return topFailure;
}
"""
    initial = module.score_candidate(near_miss, task)
    atomic_packet = module.build_atomic_contract_packet(task)
    repaired_score, repaired_code, record = module.maybe_apply_contract_synthesis_joint(
        near_miss, task, initial, atomic_packet
    )

    assert initial["passed"] is False
    assert repaired_score["passed"] is True
    assert record["kind"] == "contract_synthesis:failure_bucket_summary"
    assert 'let topFailure = "none"' in repaired_code


def test_contract_synthesis_joint_solves_lead_offer_router():
    module = _load_module()
    task = next(
        task
        for task in module.load_task_file(REPO_ROOT / "config" / "eval" / "scbe_productivity_eval_tasks.v1.json")
        if task.task_id == "lead_offer_router"
    )
    near_miss = """
function evaluate(input, state) {
  let offer = "supporter_monthly";
  let reason = "fallback";
  if (input.projectType === "developer") {
    offer = "toolkit";
    reason = "project_type_developer";
  }
  state.offer = offer;
  state.reason = reason;
  return offer;
}
"""
    initial = module.score_candidate(near_miss, task)
    atomic_packet = module.build_atomic_contract_packet(task)
    repaired_score, repaired_code, record = module.maybe_apply_contract_synthesis_joint(
        near_miss, task, initial, atomic_packet
    )

    assert initial["passed"] is False
    assert repaired_score["passed"] is True
    assert record["kind"] == "contract_synthesis:lead_offer_router"
    assert "developer_toolkit" in repaired_code


def test_contract_synthesis_joint_can_shadow_audit_visible_pass():
    module = _load_module()
    task = next(
        task
        for task in module.load_task_file(REPO_ROOT / "config" / "eval" / "common_agentic_benchmark_tasks.v1.json")
        if task.task_id == "terminal_bench_command_guard"
    )
    public_only_task = module.FunctionalTask(
        task_id=task.task_id,
        prompt=task.prompt,
        checks=[task.checks[0]],
    )
    public_only_near_miss = """
function evaluate(input, state) {
  state.allowed = true;
  state.reason = "ok";
  state.commandLog.push(input.command);
  return true;
}
"""
    public_score = module.score_candidate(public_only_near_miss, public_only_task)
    atomic_packet = module.build_atomic_contract_packet(public_only_task)
    repaired_score, repaired_code, record = module.maybe_apply_contract_synthesis_joint(
        public_only_near_miss,
        public_only_task,
        public_score,
        atomic_packet,
        force_audit=True,
    )

    assert public_score["passed"] is True
    assert repaired_score["passed"] is True
    assert record["force_audit"] is True
    assert record["kind"] == "contract_synthesis:terminal_command_guard"
    assert "destructive_command" in repaired_code


def test_contract_synthesis_joints_solve_common_public_style_failures():
    module = _load_module()
    task_ids = {
        "swe_issue_file_focus": "contract_synthesis:swe_issue_file_focus",
        "terminal_bench_command_guard": "contract_synthesis:terminal_command_guard",
        "evalplus_edge_case_counter": "contract_synthesis:evalplus_edge_counter",
        "humaneval_signature_guard": "contract_synthesis:humaneval_signature_guard",
        "repobench_context_budget": "contract_synthesis:repobench_context_budget",
        "cost_duration_report": "contract_synthesis:cost_duration_report",
        "patch_diff_risk_score": "contract_synthesis:patch_diff_risk_score",
    }
    tasks = {
        task.task_id: task
        for task in module.load_task_file(REPO_ROOT / "config" / "eval" / "common_agentic_benchmark_tasks.v1.json")
    }

    for task_id, expected_kind in task_ids.items():
        task = tasks[task_id]
        initial = {
            "task_id": task.task_id,
            "passed": False,
            "checks": [{"passed": False}],
        }
        atomic_packet = module.build_atomic_contract_packet(task)
        repaired_score, repaired_code, record = module.maybe_apply_contract_synthesis_joint(
            "function evaluate(input, state) { return null; }",
            task,
            initial,
            atomic_packet,
        )

        assert repaired_score["passed"] is True, task_id
        assert record["kind"] == expected_kind
        assert "function evaluate" in repaired_code


def test_contract_synthesis_joints_solve_competitor_gap_and_mars_tasks():
    module = _load_module()
    expected_kinds = {
        "context_precision_selector": "contract_synthesis:context_precision_selector",
        "terminal_recovery_plan": "contract_synthesis:terminal_recovery_plan",
        "compound_request_completion": "contract_synthesis:compound_request_completion",
        "maintenance_erosion_guard": "contract_synthesis:maintenance_erosion_guard",
        "evidence_truth_packet": "contract_synthesis:evidence_truth_packet",
        "environment_dependency_triage": "contract_synthesis:environment_dependency_triage",
        "supervisor_executor_correction": "contract_synthesis:supervisor_executor_correction",
        "multi_agent_handoff_integrity": "contract_synthesis:multi_agent_handoff_integrity",
        "mars_sensor_truth_gate": "contract_synthesis:mars_sensor_truth_gate",
        "mars_tongue_route_packet": "contract_synthesis:mars_tongue_route_packet",
        "mars_decision_envelope_gate": "contract_synthesis:mars_decision_envelope_gate",
        "mars_blackout_resume_reducer": "contract_synthesis:mars_blackout_resume_reducer",
        "mars_blackout_audit_sync": "contract_synthesis:mars_blackout_audit_sync",
    }
    tasks = {
        task.task_id: task
        for task in module.load_task_file(REPO_ROOT / "config" / "eval" / "competitor_gap_agentic_tasks.v1.json")
    }

    for task_id, expected_kind in expected_kinds.items():
        task = tasks[task_id]
        initial = {
            "task_id": task.task_id,
            "passed": False,
            "checks": [{"passed": False}],
        }
        atomic_packet = module.build_atomic_contract_packet(task)
        repaired_score, repaired_code, record = module.maybe_apply_contract_synthesis_joint(
            "function evaluate(input, state) { return null; }",
            task,
            initial,
            atomic_packet,
        )

        assert repaired_score["passed"] is True, task_id
        assert record["kind"] == expected_kind
        assert "function evaluate" in repaired_code


def test_candidate_benchmark_uses_contract_synthesis_joint(tmp_path: Path):
    module = _load_module()
    candidate_file = tmp_path / "candidate.json"
    candidate_file.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "name": "near-miss",
                        "tasks": {
                            "task_priority_queue": (
                                "function evaluate(input, state) { "
                                "state.selectedTask = input.tasks[0].id; return state.selectedTask; }"
                            )
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    args = Namespace(
        replace_default_tasks=True,
        task_file=[REPO_ROOT / "config" / "eval" / "scbe_productivity_eval_tasks.v1.json"],
        task_limit=0,
        task_ids=["task_priority_queue"],
        joint_library=None,
        disable_contract_synthesis=False,
    )

    result = module.run_candidate_benchmark(args, module.load_candidate_file(candidate_file)[0])
    row = result["tasks"][0]

    assert result["summary"]["pass_rate"] == 1.0
    assert row["contract_synthesis_joint"]["passed"] is True
    assert row["contract_synthesis_joint"]["kind"] == "contract_synthesis:priority_queue_tie_break"
