from __future__ import annotations

import json
from pathlib import Path

from scripts.governance_gated_agent_loop import CodeRunner, GovernanceGatedAgent


def test_validate_candidate_restores_failed_change(tmp_path: Path):
    repo_root = tmp_path
    target = repo_root / "sample.py"
    target.write_text("print('original')\n", encoding="utf-8")

    runner = CodeRunner(repo_root)

    result = runner.validate_candidate(
        "sample.py",
        "print('candidate')\n",
        test_cmd=["python", "-c", "import sys; sys.exit(1)"],
        timeout=10,
    )

    assert result["applied"] is False
    assert result["restored"] is True
    assert target.read_text(encoding="utf-8") == "print('original')\n"


def test_run_task_logs_sft_only_after_success(tmp_path: Path, monkeypatch):
    repo_root = tmp_path
    target = repo_root / "sample.py"
    target.write_text("print('original')\n", encoding="utf-8")

    agent = GovernanceGatedAgent(repo_root=repo_root, max_retries=1, max_hours=1.0, strict=True)

    monkeypatch.setattr(agent, "_generate_code", lambda task, target_file, rejection: "print('candidate')\n")
    monkeypatch.setattr(
        agent.gate,
        "evaluate",
        lambda code, context=None: {
            "decision": "ALLOW",
            "h_score": 0.99,
            "theoretical_cost": 1.0,
            "distance": 0.0,
            "phase_deviation": 0.0,
            "risks": {},
            "tongue_profile": {"KO": 0.3, "AV": 0.3, "RU": 0.3, "CA": 0.3, "UM": 0.3, "DR": 0.3},
            "reason_codes": [],
            "governance_scalars": {
                "mm_coherence": 0.9,
                "mm_conflict": 0.05,
                "mm_drift": 0.05,
                "wall_cost": 0.1,
                "trust_level": "T0",
            },
            "proof": {"decision": "ALLOW"},
            "timestamp": "2026-04-01T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        agent.runner,
        "run_tests",
        lambda test_cmd="python -m pytest tests/ -x -q --tb=short", timeout=120: {
            "passed": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0,
        },
    )

    result = agent.run_task("update sample", "sample.py")

    assert result["success"] is True
    assert target.read_text(encoding="utf-8") == "print('candidate')\n"
    sft_file = repo_root / "training-data" / "governance_agent" / "governance_sft.jsonl"
    lines = sft_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["category"] == "governance_approved"
    attempt_file = repo_root / "training-data" / "governance_agent" / "governance_loop_attempts.jsonl"
    metric_file = repo_root / "training-data" / "governance_agent" / "governance_loop_metrics.jsonl"
    attempt_record = json.loads(attempt_file.read_text(encoding="utf-8").strip().splitlines()[0])
    metric_record = json.loads(metric_file.read_text(encoding="utf-8").strip().splitlines()[0])
    assert attempt_record["approved_after_attempt"] is True
    assert attempt_record["test_passed"] is True
    assert metric_record["final_status"] == "approved"
    assert metric_record["primary_metrics"]["post_approval_integrity"] is True


def test_run_task_does_not_log_sft_when_tests_fail(tmp_path: Path, monkeypatch):
    repo_root = tmp_path
    target = repo_root / "sample.py"
    original = "print('original')\n"
    target.write_text(original, encoding="utf-8")

    agent = GovernanceGatedAgent(repo_root=repo_root, max_retries=1, max_hours=1.0, strict=True)

    monkeypatch.setattr(agent, "_generate_code", lambda task, target_file, rejection: "print('candidate')\n")
    monkeypatch.setattr(
        agent.gate,
        "evaluate",
        lambda code, context=None: {
            "decision": "ALLOW",
            "h_score": 0.99,
            "theoretical_cost": 1.0,
            "distance": 0.0,
            "phase_deviation": 0.0,
            "risks": {},
            "tongue_profile": {"KO": 0.3, "AV": 0.3, "RU": 0.3, "CA": 0.3, "UM": 0.3, "DR": 0.3},
            "reason_codes": [],
            "governance_scalars": {
                "mm_coherence": 0.9,
                "mm_conflict": 0.05,
                "mm_drift": 0.05,
                "wall_cost": 0.1,
                "trust_level": "T0",
            },
            "proof": {"decision": "ALLOW"},
            "timestamp": "2026-04-01T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        agent.runner,
        "run_tests",
        lambda test_cmd="python -m pytest tests/ -x -q --tb=short", timeout=120: {
            "passed": False,
            "stdout": "",
            "stderr": "forced failure",
            "returncode": 1,
        },
    )

    result = agent.run_task("update sample", "sample.py")

    assert result["success"] is False
    assert target.read_text(encoding="utf-8") == original
    sft_file = repo_root / "training-data" / "governance_agent" / "governance_sft.jsonl"
    assert not sft_file.exists()
    attempt_file = repo_root / "training-data" / "governance_agent" / "governance_loop_attempts.jsonl"
    metric_file = repo_root / "training-data" / "governance_agent" / "governance_loop_metrics.jsonl"
    attempt_record = json.loads(attempt_file.read_text(encoding="utf-8").strip().splitlines()[0])
    metric_record = json.loads(metric_file.read_text(encoding="utf-8").strip().splitlines()[0])
    assert attempt_record["approved_after_attempt"] is False
    assert attempt_record["test_passed"] is False
    assert metric_record["final_status"] == "max_retries"
    assert metric_record["primary_metrics"]["post_approval_integrity"] is False
