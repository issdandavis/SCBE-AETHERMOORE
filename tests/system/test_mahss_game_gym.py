from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "system" / "mahss_game_gym.py"


def load_module():
    spec = importlib.util.spec_from_file_location("_mahss_game_gym_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_pacman_plan_completes_build_verify_ship_without_hazard() -> None:
    module = load_module()

    report = module.plan_pacman()

    assert report["schema"] == "scbe_mahss_pacman_plan_v1"
    assert report["complete"] is True
    top = report["plans"][0]
    assert top["goals_collected"] == ["build", "ship", "verify"]
    assert top["hazard_hits"] == 0
    assert top["path"][0] == "DOWN"


def test_tetris_lock_routes_models_through_facility_and_rejects_direct_llm() -> None:
    module = load_module()

    report = module.plan_tetris()

    assert report["schema"] == "scbe_mahss_tetris_lock_v1"
    assert report["complete"] is True
    assert [lock["piece_id"] for lock in report["locks"]] == [
        "receiver_model",
        "router_model",
        "tool_executor",
        "verifier_model",
        "manager_model",
    ]
    rejected = report["rejected_examples"][0]
    assert rejected["piece_id"] == "unsafe_direct_llm"
    assert rejected["locked"] is False
    assert any("risk" in reason for reason in rejected["reasons"])


def test_combined_report_declares_model_proposes_system_scores_policy() -> None:
    module = load_module()

    report = module.build_report("all")

    assert report["schema"] == "scbe_mahss_game_gym_report_v1"
    assert report["policy"]["model_role"] == "propose moves"
    assert report["policy"]["system_role"].startswith("score legal moves")
    assert report["policy"]["no_model_calls"] is True
    assert {item["game"] for item in report["reports"]} == {"pacman", "tetris", "world"}


def test_world_loop_has_depthful_npc_workflow_ticks_and_receipts() -> None:
    module = load_module()

    report = module.simulate_world()

    assert report["schema"] == "scbe_mahss_world_loop_v1"
    assert report["complete"] is True
    assert report["depth_metrics"]["tick_count"] == 5
    assert report["depth_metrics"]["receipt_count"] == 5
    assert report["loop"] == [
        "world_state",
        "actor_observation",
        "intent_selection",
        "policy_gate",
        "action_resolution",
        "world_delta",
        "memory_update",
        "receipt",
        "next_tick",
    ]
    assert report["final_state"]["workspace"]["tests_green"] is True
    assert report["final_state"]["workspace"]["receipt_written"] is True


def test_world_loop_ticks_emit_godot_game_event_payloads() -> None:
    module = load_module()

    report = module.simulate_world()

    assert report["godot_bridge"]["project"] == "game/godot/project.godot"
    assert report["godot_bridge"]["endpoints"]["event_log"] == "/api/game/events/log"
    first_tick = report["ticks"][0]
    event = first_tick["memory"]["godot_event"]
    assert event["godot_bridge"]["source_script"] == "game/godot/scripts/scbe/scbe_client.gd"
    assert event["godot_bridge"]["post_endpoint"] == "/api/game/events/log"
    assert event["event_type"] == "exploration_action"
    assert event["context"]["formation_type"] == "factory_line"
    assert event["outcome"]["success"] is True
