from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.terminal.geoseal_harness_terminal import build_terminal_state, render_terminal_text
from scripts.terminal.analog_action_primitives import build_default_action_deck, build_domino_workflow

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_harness_terminal_state_reports_roundabout_signals() -> None:
    state = build_terminal_state(
        model_refs=["ollama:a", "deepseek:b", "ollama:c"],
        probe_health=False,
    )

    assert state["schema_version"] == "scbe_geoseal_harness_terminal_v1"
    assert state["summary"]["models"] == 3
    assert state["summary"]["signal_required_pairs"] >= 1
    assert state["summary"]["analog_actions"] >= 6
    assert state["summary"]["research_lanes"] >= 8
    assert state["summary"]["research_source_routes"] >= 9
    assert state["summary"]["lane_grid_columns"] == 3
    assert state["summary"]["lane_grid_final_decision"] == "advance"
    assert state["summary"]["control_panel_verdict"] in {"HOLD", "PROMOTE", "INCUBATE", "ESCALATE"}
    assert state["control_panel_brain"]["schema_version"] == "scbe_geoseal_control_panel_turn_v1"
    assert state["lane_grid"]["schema_version"] == "scbe_lane_grid_scheduler_v1"
    assert state["bridge"]["error"] == "not_probed"

    text = render_terminal_text(state)
    assert "GeoSeal Harness Terminal" in text
    assert "Provider Lanes" in text
    assert "Lane Switches" in text
    assert "Release Gates" in text
    assert "Analog Actions" in text
    assert "Lane Grid" in text
    assert "-0 HOLD" in text
    assert "Control Panel Brain" in text
    assert "Research Benchmarks" in text
    assert "Research Source Routes" in text
    assert "terminal-bench-shape" in text
    assert "harness_live_smoke.py" in text
    assert "scripts/ci/harness_release_readiness.py" in text
    assert "provider-pair:ollama->deepseek:benchmark" in text


def test_harness_terminal_script_json_output() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/terminal/geoseal_harness_terminal.py",
            "--models",
            "ollama:a,deepseek:b",
            "--goal",
            "benchmark training eval",
            "--no-health",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    state = json.loads(proc.stdout)
    assert state["summary"]["models"] == 2
    assert state["summary"]["blocked_without_signal_pairs"] == 1
    assert state["lane_grid"]["world_write_rule"].startswith("DR plus two other lanes")
    assert state["control_panel_brain"]["intent"] == "training_eval"
    assert state["research_benchmarks"]["families"]["terminal_bench"] == 1
    assert any("harness_live_smoke.py" in command for command in state["controls"]["release_gate_commands"])


def test_geoseal_cli_harness_terminal_passthrough() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "harness-terminal",
            "--models",
            "ollama:a,deepseek:b",
            "--no-health",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert "GeoSeal Harness Terminal" in proc.stdout
    assert "Lane Switches" in proc.stdout
    assert "Lane Grid" in proc.stdout


def test_geoseal_cli_lane_grid_json() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "lane-grid",
            "--goal",
            "route github workflows",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    state = json.loads(proc.stdout)
    assert state["schema_version"] == "scbe_lane_grid_scheduler_v1"
    assert state["final_decision"] == "advance"
    assert state["motion_rules"]["-0"].startswith("abstain-hold")


def test_analog_action_deck_has_resettable_domino_primitives() -> None:
    deck = build_default_action_deck()
    ids = {action.action_id for action in deck}

    assert {"observe-room", "move-lane", "inspect-object", "solve-checkpoint", "verify-evidence", "reset-run"}.issubset(
        ids
    )
    assert all(action.symbol for action in deck)
    assert all(action.multi_encoding["terminal"] for action in deck)

    workflow = build_domino_workflow(
        goal="prove packet graph",
        provider_pair=["ollama:a", "deepseek:b"],
    )
    assert workflow["lane_signal"] == "provider-pair:ollama->deepseek:workflow"
    assert [step["action_id"] for step in workflow["steps"]] == [
        "observe-room",
        "inspect-object",
        "move-lane",
        "solve-checkpoint",
        "verify-evidence",
        "reset-run",
    ]
