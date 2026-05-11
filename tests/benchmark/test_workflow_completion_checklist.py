from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "workflow_completion_checklist.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("workflow_completion_checklist", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_completion_checklist_captures_known_fail_and_help_plan(tmp_path: Path) -> None:
    module = _load_module()
    artifact_root = tmp_path / "artifacts"
    diagnostics = artifact_root / "diagnostics"
    diagnostics.mkdir(parents=True)
    (artifact_root / "latest_stats.yml").write_text(
        """
- dirname: demo
  test_cases: 1
  model: openai/Qwen/Qwen2.5-Coder-32B-Instruct
  edit_format: whole
  pass_rate_1: 0.0
  pass_rate_2: 0.0
  prompt_tokens: 100
  completion_tokens: 50
  date: 2026-05-11
""",
        encoding="utf-8",
    )
    (diagnostics / "javascript_exercises_practice_rectangles.results.json").write_text(
        json.dumps(
            {
                "testcase": "rectangles",
                "model": "openai/Qwen/Qwen2.5-Coder-32B-Instruct",
                "edit_format": "whole",
                "tests_outcomes": [False, False],
                "syntax_errors": 0,
                "indentation_errors": 0,
                "num_malformed_responses": 0,
                "test_timeouts": 0,
            }
        ),
        encoding="utf-8",
    )
    (diagnostics / "javascript_exercises_practice_rectangles.chat.history.md").write_text(
        """
Expected: 60
Received: 70
TypeError: diagram[0].length is not a function
""",
        encoding="utf-8",
    )

    report = module.build_checklist(artifact_root=artifact_root, output_root=tmp_path / "out")
    payload = report["payload"]

    assert payload["completion_status"] == "blocked_known_fails"
    assert payload["known_failure_count"] == 1
    failure = payload["known_failures"][0]
    assert failure["task"] == "rectangles"
    assert failure["language"] == "javascript"
    assert "language_api_confusion" in failure["failure_classes"]
    assert "edge_case_over_or_under_count" in failure["failure_classes"]
    assert failure["help_plan"]["web_search_queries"]
    assert failure["retry_cycle"]["schema_version"] == "scbe_known_fail_retry_cycle_v1"
    assert failure["retry_cycle"]["anti_consensus_rule"]
    assert payload["workingness_policy"]["consensus_role"] == "advisory_only"
    assert payload["workingness_policy"]["failure_role"] == "learning_packet_for_retry"
    assert Path(report["json"]).exists()
    assert Path(report["markdown"]).exists()


def test_completion_checklist_ready_when_no_failures(tmp_path: Path) -> None:
    module = _load_module()
    artifact_root = tmp_path / "artifacts"
    diagnostics = artifact_root / "diagnostics"
    diagnostics.mkdir(parents=True)
    (diagnostics / "python_exercises_practice_two_fer.results.json").write_text(
        json.dumps({"tests_outcomes": [True, True], "syntax_errors": 0, "num_malformed_responses": 0}),
        encoding="utf-8",
    )

    report = module.build_checklist(artifact_root=artifact_root, output_root=tmp_path / "out")
    payload = report["payload"]

    assert payload["completion_status"] == "ready_to_claim_done"
    assert payload["known_failure_count"] == 0
    assert all(item["status"] in {"pass", "not_needed"} for item in payload["completion_checklist"])
