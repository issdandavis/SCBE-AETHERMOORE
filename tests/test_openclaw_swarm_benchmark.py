import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "benchmark" / "openclaw_swarm_benchmark.py"


def load_module():
    spec = importlib.util.spec_from_file_location("_openclaw_swarm_benchmark_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_semantic_task_variables_mark_internal_claim_not_public_benchmark():
    module = load_module()

    row = module.build_semantic_task_variables(
        {
            "case": {
                "case_id": "case-a",
                "task": "Track internal variables.",
                "persona": "internal_ai_lane",
                "output_contract": "evidence",
                "constraint_mode": "strict",
                "allowed_paths": "scripts/",
                "focus_paths": "scripts/system/openclaw_swarm.py",
                "agents": "openclaw",
            },
            "exit_code": 0,
            "wall_seconds": 1.0,
            "stdout_json": {
                "run_dir": "artifacts/run",
                "lanes": ["01-verification"],
                "models": ["openclaw:latest"],
                "successful_lanes": 1,
                "promotable_lanes": 0,
                "blocked_lanes": 1,
                "failed_lanes": 0,
            },
            "routing": {
                "quality_flag_counts": {"evidence_symbol_not_found": 2},
                "next_action": "run_helper_guard_cycle_before_escalation",
                "next_cycle": "helper_collect_file_evidence_then_guard_review",
                "assurance_packet": {"mean_applicability_score": 50.0},
            },
        }
    )

    assert row["gate_state"]["completion_state"] == "blocked_correctly"
    assert row["interpretation"]["public_benchmark_claim"] == "not_public_benchmark"
    assert row["gate_state"]["quality_flags"]["evidence_symbol_not_found"] == 2


def test_weakness_loop_maps_symbol_flags_to_patch_direction():
    module = load_module()

    loop = module.build_weakness_loop(
        {
            "cases": [
                {
                    "routing": {
                        "quality_flag_counts": {
                            "evidence_symbol_not_found": 3,
                            "symbol_not_found": 1,
                        }
                    }
                }
            ]
        }
    )

    weakness_names = {item["weakness"] for item in loop["weaknesses"]}
    target_names = {item["name"] for item in loop["public_benchmark_targets"]}

    assert "model_invented_evidence_symbols" in weakness_names
    assert "patch_targets_fake_or_stale_symbols" in weakness_names
    assert "SWE-bench Verified" in target_names
    assert loop["claim_boundary"].startswith("Internal harness score only")


def test_weakness_loop_maps_common_quality_flags_to_specific_repairs():
    module = load_module()

    loop = module.build_weakness_loop(
        {
            "cases": [
                {
                    "routing": {
                        "quality_flag_counts": {
                            "placeholder_diff_index": 1,
                            "verification_mutates_git_state": 1,
                        }
                    }
                }
            ]
        }
    )

    weakness_names = {item["weakness"] for item in loop["weaknesses"]}

    assert "placeholder_patch_metadata" in weakness_names
    assert "unsafe_verification_command" in weakness_names
    assert not any(name.startswith("unmapped_quality_flag") for name in weakness_names)


def test_weakness_loop_maps_lane_failure_to_specific_repair():
    module = load_module()

    loop = module.build_weakness_loop(
        {
            "cases": [
                {
                    "routing": {
                        "quality_flag_counts": {
                            "lane_failed": 1,
                        }
                    }
                }
            ]
        }
    )

    weakness_names = {item["weakness"] for item in loop["weaknesses"]}

    assert "model_lane_runtime_failure" in weakness_names
    assert not any(name.startswith("unmapped_quality_flag") for name in weakness_names)


def test_weakness_loop_maps_blacklisted_path_to_specific_repair():
    module = load_module()

    loop = module.build_weakness_loop(
        {
            "cases": [
                {
                    "routing": {
                        "quality_flag_counts": {
                            "blacklisted_path": 1,
                        }
                    }
                }
            ]
        }
    )

    weakness_names = {item["weakness"] for item in loop["weaknesses"]}
    patch_directions = " ".join(item["patch_direction"] for item in loop["weaknesses"])

    assert "blacklisted_path_reference" in weakness_names
    assert "nearest allowed implementation path" in patch_directions
    assert not any(name.startswith("unmapped_quality_flag") for name in weakness_names)


def test_score_case_penalizes_failed_lanes_even_with_valid_artifact_shape():
    module = load_module()

    score = module.score_case(
        {
            "ok": True,
            "agents": ["pi"],
            "models": ["gemma3:1b"],
            "promotable_lanes": 0,
            "blocked_lanes": 1,
            "failed_lanes": 1,
        },
        {
            "schema": "scbe_swarm_routing_v1",
            "next_action": "run_helper_guard_cycle_before_escalation",
            "correction_guide": [],
            "quality_flag_counts": {"lane_failed": 1},
        },
        0,
    )

    assert score["points"] == 65
    assert score["grade"] == "weak"


def test_score_case_accepts_safe_apply_verified_action():
    module = load_module()

    score = module.score_case(
        {
            "ok": True,
            "agents": ["safe_apply"],
            "models": ["deterministic_patch"],
            "promotable_lanes": 1,
            "blocked_lanes": 0,
        },
        {
            "schema": "scbe_swarm_routing_v1",
            "next_action": "safe_apply_verified",
            "correction_guide": [],
            "quality_flag_counts": {},
        },
        0,
    )

    assert score["points"] == 100
    assert score["grade"] == "pass"


def test_quality_vector_grades_how_well_case_passed():
    module = load_module()

    item = {
        "wall_seconds": 1.2,
        "score": {"points": 100},
        "stdout_json": {
            "ok": True,
            "run_dir": "artifacts/run",
            "promotable_lanes": 1,
            "blocked_lanes": 0,
        },
        "routing": {
            "schema": "scbe_swarm_routing_v1",
            "next_action": "safe_apply_verified",
            "quality_flag_counts": {},
            "assurance_packet": {"mean_applicability_score": 100.0},
        },
    }

    vector = module.build_quality_vector(item)

    assert vector["schema"] == "scbe_swarm_case_quality_vector_v1"
    assert vector["quality_score"] == 100.0
    assert vector["pass_depth"] == "exceptional_pass"
    assert vector["dimensions"]["traceability"] == 100.0


def test_quality_vector_exposes_thin_pass_with_low_traceability():
    module = load_module()

    item = {
        "wall_seconds": 20.0,
        "score": {"points": 100},
        "stdout_json": {
            "ok": True,
            "run_dir": "artifacts/run",
            "promotable_lanes": 1,
            "blocked_lanes": 0,
        },
        "routing": {
            "schema": "scbe_swarm_routing_v1",
            "next_action": "review_promotable_lane",
            "quality_flag_counts": {"evidence_symbol_not_found": 1},
            "assurance_packet": {"mean_applicability_score": 50.0},
        },
    }

    vector = module.build_quality_vector(item)

    assert vector["quality_score"] < 85.0
    assert vector["pass_depth"] == "thin_pass"
    assert vector["dimensions"]["evidence_integrity"] == 85.0
    assert vector["dimensions"]["patch_readiness"] == 50.0


def test_summary_includes_quality_score_and_depth_counts():
    module = load_module()

    results = [
        {
            "wall_seconds": 1.0,
            "score": {"points": 100},
            "stdout_json": {
                "ok": True,
                "run_dir": "artifacts/run",
                "promotable_lanes": 1,
                "blocked_lanes": 0,
                "failed_lanes": 0,
            },
            "routing": {
                "schema": "scbe_swarm_routing_v1",
                "next_action": "safe_apply_verified",
                "quality_flag_counts": {},
                "assurance_packet": {"mean_applicability_score": 100.0},
            },
        }
    ]

    summary = module.build_summary(results)

    assert summary["average_score"] == 100.0
    assert summary["average_quality_score"] == 100.0
    assert summary["quality_summary"]["pass_depth_counts"] == {"exceptional_pass": 1}
    assert results[0]["quality_vector"]["quality_score"] == 100.0


def test_trust_ladder_report_decays_on_runtime_failure():
    module = load_module()

    report = {
        "semantic_task_variables": [
            {
                "task_id": "clean",
                "gate_state": {
                    "completion_state": "promotable_signal",
                    "quality_flags": {},
                },
            },
            {
                "task_id": "failed",
                "gate_state": {
                    "completion_state": "runtime_failed",
                    "quality_flags": {"lane_failed": 1},
                },
            },
        ]
    }

    trust = module.build_trust_ladder_report(report)

    assert trust["schema"] == "scbe_fibonacci_trust_ladder_report_v1"
    assert trust["source_note"] == "notes/theory/fibonacci-trust-ladder.md"
    assert trust["betrayal_count"] == 1
    assert trust["state"] == "trust_repair_needed"


def test_geometric_consensus_is_advisory_not_a_score_gate():
    module = load_module()

    report = {
        "semantic_task_variables": [
            {
                "task_id": "case-a",
                "task_intent": "Do a thing.",
                "persona": "internal_ai_lane",
                "output_contract": "evidence",
                "constraint_mode": "strict",
                "allowed_paths": "scripts/",
                "focus_paths": "scripts/file.py",
                "agent_set": "openclaw",
                "cloud_policy": {"allow_ollama_cloud": False},
                "runtime": {
                    "models": ["openclaw:latest"],
                    "lanes": ["01-verification"],
                    "run_dir": "artifacts/run",
                },
                "gate_state": {
                    "completion_state": "blocked_correctly",
                    "quality_flags": {"evidence_symbol_not_found": 1},
                    "next_cycle": "helper_collect_file_evidence_then_guard_review",
                },
                "interpretation": {"public_benchmark_claim": "not_public_benchmark"},
            }
        ]
    }

    consensus = module.build_geometric_consensus(report)

    assert consensus["schema"] == "scbe_geometric_consensus_v1"
    assert consensus["geometry"] == "hexagonal_half-dodecahedral_consensus_graph"
    assert consensus["declaration_coverage"] == 1.0
    assert "consensus_state" not in consensus
    assert "consensus_confidence" not in consensus
    assert "completion_agreement" not in consensus
    assert consensus["hexagonal_faces"]["path_scope"]["coverage"] == 1.0
    assert consensus["result_focus"]["dominant_completion"] == "blocked_correctly"
    assert "not a consensus score" in consensus["result_focus"]["note"]
    assert "must not block production by itself" in consensus["note"]
    assert consensus["code_5w"][0]["who"]["persona"] == "internal_ai_lane"
    assert consensus["code_5w"][0]["what"]["output_contract"] == "evidence"
    assert consensus["code_5w"][0]["where"]["focus_paths"] == "scripts/file.py"
    assert consensus["code_5w"][0]["why"]["quality_flags"] == {"evidence_symbol_not_found": 1}
    assert consensus["information_ray_trace"]["ray_model"] == "non_light_information_object_paths"
    assert consensus["information_ray_trace"]["rays"][0]["source_face"] == "evidence_trace"


def test_public_parallel_cases_are_registered():
    module = load_module()

    case_ids = {case.case_id for case in module.PUBLIC_PARALLEL_CASES}

    assert "public_swebench_verified_adapter" in case_ids
    assert "public_terminal_bench_adapter" in case_ids
    assert "public_vexp_swebench_adapter" in case_ids


def test_safe_apply_patch_probe_uses_delete_me_test_path():
    module = load_module()

    patch = module.build_safe_apply_patch("tests/_safe_apply_benchmark_probe_TEST_DELETE_ME.txt")

    assert "diff --git a/tests/_safe_apply_benchmark_probe_TEST_DELETE_ME.txt" in patch
    assert "--- /dev/null" in patch
    assert "+scbe safe-apply benchmark probe" in patch


def test_allocate_output_dir_is_unique_for_same_run_id(tmp_path):
    module = load_module()

    first = module.allocate_output_dir(tmp_path, "20260511T000000Z")
    second = module.allocate_output_dir(tmp_path, "20260511T000000Z")

    assert first.name == "20260511T000000Z"
    assert second.name == "20260511T000000Z-001"
    assert first.exists()
    assert second.exists()


def test_self_cli_functional_command_uses_scbe_task_pack_and_ollama_models(tmp_path):
    module = load_module()

    command = module.build_self_cli_functional_command(
        tmp_path,
        ("openclaw:latest", "qwen3-coder:480b-cloud"),
        task_limit=2,
        repair_model="qwen2.5:7b-instruct",
        repair_attempts=1,
    )

    assert str(module.FUNCTIONAL_CODING_BENCH) in command
    assert "--ollama-models" in command
    assert "openclaw:latest" in command
    assert "qwen3-coder:480b-cloud" in command
    assert "--task-file" in command
    assert str(module.SELF_CLI_TASK_FILE) in command
    assert "--replace-default-tasks" in command
    assert "--repair-ollama-model" in command


def test_functional_score_from_report_judges_executed_code_pass_rate():
    module = load_module()

    score = module._functional_score_from_report(
        {
            "results": [
                {"summary": {"tasks": 4, "passed": 3, "pass_rate": 0.75}},
                {"summary": {"tasks": 4, "passed": 1, "pass_rate": 0.25}},
            ]
        }
    )

    assert score["points"] == 50.0
    assert score["grade"] == "weak"
    assert "executable TypeScript" in score["reason"]


def test_self_cli_case_is_framed_as_compiler_not_verifier(tmp_path, monkeypatch):
    module = load_module()
    functional_dir = tmp_path / "functional" / "latest"
    functional_dir.mkdir(parents=True)
    (functional_dir / "report.json").write_text(
        '{"results":[{"adapter":"ollama:test","summary":{"tasks":1,"passed":1,"pass_rate":1.0}}]}',
        encoding="utf-8",
    )

    class Completed:
        returncode = 0
        stdout = f"Report JSON: {functional_dir / 'report.json'}\n"
        stderr = ""

    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: Completed())

    item = module.run_self_cli_functional_case(tmp_path, ("ollama:test",), task_limit=1)

    assert item["case"]["output_contract"] == "cross-lingual-compiler-artifact"
    assert "Compile SCBE productivity tasks" in item["case"]["task"]
    requirements = item["routing"]["assurance_packet"]["requirements"]
    assert "compiler_trace" in requirements
    assert item["score"]["points"] == 100.0


def test_build_single_case_report_includes_trust_and_consensus(tmp_path):
    module = load_module()

    item = {
        "case": module.asdict(
            module.BenchmarkCase(
                case_id="safe_apply_sandbox_patch_probe",
                persona="safe_apply_gate",
                task="probe",
                agents="safe_apply",
                timeout=90,
                max_workers=1,
            )
        ),
        "exit_code": 0,
        "wall_seconds": 0.1,
        "ok": True,
        "stdout_json": {
            "ok": True,
            "run_dir": str(tmp_path),
            "agents": ["safe_apply"],
            "models": ["deterministic_patch"],
            "promotable_lanes": 1,
            "blocked_lanes": 0,
            "failed_lanes": 0,
        },
        "routing": {
            "schema": "scbe_swarm_routing_v1",
            "quality_flag_counts": {},
            "next_action": "safe_apply_verified",
            "assurance_packet": {"mean_applicability_score": 100.0},
        },
        "score": {"points": 100, "max_points": 100, "grade": "pass", "reason": "test"},
    }

    report = module.build_single_case_report("run", "safe-apply", tmp_path, item)

    assert report["summary"]["average_score"] == 100.0
    assert report["trust_ladder_report"]["state"] == "trust_accruing"
    assert report["geometric_consensus"]["schema"] == "scbe_geometric_consensus_v1"
    assert report["kaggle_winner_loop"]["schema"] == "scbe_kaggle_winner_improvement_loop_v1"


def test_kaggle_winner_loop_groups_stage_quality_and_cloud_policy():
    module = load_module()

    results = [
        {
            "case": module.asdict(module.QUICK_CASES[1]),
            "wall_seconds": 1.0,
            "score": {"points": 100},
            "stdout_json": {
                "ok": True,
                "run_dir": "artifacts/run",
                "models": ["openclaw:latest"],
                "promotable_lanes": 1,
                "blocked_lanes": 0,
                "failed_lanes": 0,
            },
            "routing": {
                "schema": "scbe_swarm_routing_v1",
                "next_action": "review_promotable_lane",
                "quality_flag_counts": {},
                "assurance_packet": {"mean_applicability_score": 95.0},
            },
            "exit_code": 0,
        },
        {
            "case": module.asdict(module.OLLAMA_CLOUD_CASES[1]),
            "wall_seconds": 12.0,
            "score": {"points": 85},
            "stdout_json": {
                "ok": True,
                "run_dir": "artifacts/run",
                "models": ["qwen3-coder:cloud"],
                "promotable_lanes": 0,
                "blocked_lanes": 1,
                "failed_lanes": 0,
            },
            "routing": {
                "schema": "scbe_swarm_routing_v1",
                "next_action": "run_helper_guard_cycle_before_escalation",
                "quality_flag_counts": {"evidence_symbol_not_found": 1},
                "assurance_packet": {"mean_applicability_score": 65.0},
            },
            "exit_code": 0,
        },
    ]
    module.build_summary(results)
    report = {
        "cases": results,
        "weakness_loop": module.build_weakness_loop({"cases": results}),
    }

    loop = module.build_kaggle_winner_loop(report)

    assert loop["schema"] == "scbe_kaggle_winner_improvement_loop_v1"
    assert loop["weakest_stage"] == "ensemble_consensus"
    assert loop["ollama_cloud"]["enabled_case_count"] == 1
    assert loop["ollama_cloud"]["models_seen"] == ["qwen3-coder:cloud"]
    assert any(stage["stage"] == "baseline" and stage["case_count"] == 1 for stage in loop["stages"])
