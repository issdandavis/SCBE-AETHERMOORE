from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.eval.aether_programmer_index import DEFAULT_CONFIG, score_run

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "eval" / "aether_programmer_index.v1.json"
DOC = ROOT / "docs" / "benchmarks" / "AETHER_PROGRAMMER_INDEX.md"
SCRIPT = ROOT / "scripts" / "eval" / "aether_programmer_index.py"


def _config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_programmer_index_config_weights_are_valid() -> None:
    data = _config()

    assert data["schema_version"] == "aether_programmer_index_v1"
    assert data["status"] == "owned_index_not_external_standard"
    assert sum(track["weight"] for track in data["tracks"]) == 100
    assert sum(dim["weight"] for dim in data["quality_dimensions"]) == 100
    assert data["entry_gate"]["failed_task_score"] == 0
    assert data["entry_gate"]["failure_output"] == "procedural_solution_triage"
    assert set(data["entry_gate"]["required_checks"]) == {"tests_passed", "policy_clean", "artifact_complete"}
    assert data["failure_refinement_loop"]["candidate_solution_budget"] == 100
    assert data["failure_refinement_loop"]["trend_control"]["allowed_single_turn_negative_delta"] == -0.1
    assert data["failure_refinement_loop"]["trend_control"]["recovery_required_below_floor"] is True
    assert "Exploration is complete" in data["failure_refinement_loop"]["trend_control"]["completion_rule"]
    stage_ids = {stage["id"] for stage in data["failure_refinement_loop"]["stages"]}
    assert {"web_research", "multi_model_deliberation", "security_check", "rerun", "improvement_ledger"}.issubset(
        stage_ids
    )


def test_programmer_index_doc_carries_claim_guardrail() -> None:
    text = DOC.read_text(encoding="utf-8")

    assert "SCBE/AetherMoore-owned index" in text
    assert "not an external standard" in text
    assert "up to 100 candidate solutions" in text
    assert "Security-check candidate changes before implementation" in text
    assert "lake dive" in text


def test_score_run_binary_entry_then_quality() -> None:
    packet = {
        "schema_version": "aether_programmer_run_v1",
        "run_id": "unit-test",
        "evidence_level": "reproducible_subset_run",
        "tasks": [
            {
                "task_id": "terminal.pass",
                "track_id": "terminal_execution",
                "passed": True,
                "checks": {"tests_passed": True, "policy_clean": True, "artifact_complete": True},
                "quality": {
                    "correctness": 1.0,
                    "verification": 1.0,
                    "usability": 0.8,
                    "minimality": 0.8,
                    "governance": 1.0,
                    "cost_time": 0.6,
                },
            },
            {
                "task_id": "terminal.fail",
                "track_id": "terminal_execution",
                "passed": False,
                "checks": {"tests_passed": False, "policy_clean": True, "artifact_complete": True},
                "failure_mode": "tests failed",
                "proposed_solution": "fix command parser and rerun terminal subset",
                "quality": {
                    "correctness": 1.0,
                    "verification": 1.0,
                    "usability": 1.0,
                    "minimality": 1.0,
                    "governance": 1.0,
                    "cost_time": 1.0,
                },
            },
        ],
    }

    report = score_run(packet, _config())

    assert report["evidence_multiplier"] == 0.6
    assert report["solution_backlog"] == [
        {
            "task_id": "terminal.fail",
            "track_id": "terminal_execution",
            "failure_mode": "tests failed",
            "proposed_solution": "fix command parser and rerun terminal subset",
            "candidate_solution_budget": 100,
            "rerun_strategy": "100-agentic-solution-triage",
            "required_stages": [
                "context_quality_scan",
                "solution_space_generation",
                "web_research",
                "web_research_refinement",
                "multi_model_deliberation",
                "security_check",
                "implementation",
                "rerun",
                "improvement_ledger",
            ],
        }
    ]
    terminal = next(track for track in report["tracks"] if track["track_id"] == "terminal_execution")
    assert terminal["pass_rate"] == 0.5
    assert terminal["average_pass_quality"] == 0.91
    assert terminal["score"] == 4.095
    assert report["trend"]["status"] == "no_history"


def test_trend_allows_exploratory_negative_delta_with_cause_and_recovery() -> None:
    packet = {
        "schema_version": "aether_programmer_run_v1",
        "run_id": "trend-test",
        "evidence_level": "smoke_or_plumbing_run",
        "history": [
            {"turn": 1, "score": 0.9},
            {"turn": 2, "score": 0.8, "cause_note": "tested stricter parser"},
            {"turn": 3, "score": 0.7, "recovery_attempted": True},
        ],
        "tasks": [],
    }

    report = score_run(packet, _config())

    assert report["trend"]["status"] == "controlled_decline"
    assert report["trend"]["above_true_negative_floor"] is True
    assert report["trend"]["requires_recovery"] is False
    assert report["trend"]["exploration_complete"] is True


def test_trend_requires_recovery_for_unexplained_multi_turn_decline() -> None:
    packet = {
        "schema_version": "aether_programmer_run_v1",
        "run_id": "trend-fail",
        "evidence_level": "smoke_or_plumbing_run",
        "history": [
            {"turn": 1, "score": 0.9},
            {"turn": 2, "score": 0.8},
            {"turn": 3, "score": 0.7},
        ],
        "tasks": [],
    }

    report = score_run(packet, _config())

    assert report["trend"]["status"] == "recovery_required"
    assert report["trend"]["requires_recovery"] is True
    assert report["trend"]["exploration_complete"] is False


def test_programmer_index_cli_writes_report(tmp_path: Path) -> None:
    packet = {
        "schema_version": "aether_programmer_run_v1",
        "run_id": "cli-test",
        "evidence_level": "smoke_or_plumbing_run",
        "tasks": [],
    }
    packet_path = tmp_path / "packet.json"
    out_path = tmp_path / "report.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(packet_path), "--config", str(DEFAULT_CONFIG), "--out", str(out_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == ""
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == "aether_programmer_index_report_v1"
    assert report["run_id"] == "cli-test"
