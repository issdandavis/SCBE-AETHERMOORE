from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "known_fail_retry_prompts.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("known_fail_retry_prompts", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_retry_prompt_bundle_turns_known_fail_into_bounded_prompt(tmp_path: Path) -> None:
    module = _load_module()
    checklist = tmp_path / "latest_completion_checklist.json"
    checklist.write_text(
        json.dumps(
            {
                "payload": {
                    "known_failures": [
                        {
                            "id": "javascript_exercises_practice_rectangles",
                            "task": "rectangles",
                            "language": "javascript",
                            "model": "openai/Qwen/Qwen2.5-Coder-32B-Instruct",
                            "edit_format": "whole",
                            "failure_classes": ["tests_failed", "edge_case_over_or_under_count"],
                            "evidence": {"failure_lines": ["Expected: 60", "Received: 70"]},
                            "five_w": {
                                "what": "rectangle counter overcounted an edge case",
                                "where": "diagnostics/javascript_exercises_practice_rectangles.results.json",
                                "when": "after retry",
                                "who": "coding agent",
                                "why": "corner invariant was missed",
                                "how_to_retry": "preserve passing tests and repair only rectangle counting invariant",
                            },
                            "help_plan": {
                                "allowed_help_sources": ["official language documentation", "exercise tests"],
                                "web_search_queries": ["javascript rectangles coding kata edge cases"],
                                "retry_prompt": "Preserve passing tests, patch smallest invariant, rerun exact tests.",
                            },
                            "retry_cycle": {
                                "schema_version": "scbe_known_fail_retry_cycle_v1",
                                "stages": [
                                    {
                                        "id": "problem",
                                        "goal": "Freeze exact failing task.",
                                        "done_when": "evidence exists.",
                                    },
                                    {
                                        "id": "workingness_gate",
                                        "goal": "Judge by executable workingness.",
                                        "done_when": "tests pass.",
                                    },
                                ],
                                "free_first_model_rotation": ["local small model: classify failure"],
                                "next_retry_prompt": "Explain invariant, patch, rerun.",
                            },
                        }
                    ],
                    "workingness_policy": {
                        "consensus_role": "advisory_only",
                        "success_gate": "executable_tests_and_artifact_evidence",
                        "failure_role": "learning_packet_for_retry",
                        "retry_shape": (
                            "problem + retry_with_knowledge + multi_agent_research + bigger_agent_confirmation"
                        ),
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    bundle = module.build_retry_prompt_bundle(checklist_path=checklist, output_root=tmp_path / "out")

    assert bundle["status"] == "prompts_ready"
    assert bundle["prompt_count"] == 1
    prompt_path = Path(bundle["prompts"][0]["prompt_path"])
    prompt = prompt_path.read_text(encoding="utf-8")
    assert "Failure is a learning packet" in prompt
    assert "Do not chase model consensus" in prompt
    assert "executable_tests_and_artifact_evidence" in prompt
    assert "Expected: 60" in prompt
    assert "failure_invariant" in prompt
    assert "verification_command" in prompt
    assert Path(bundle["bundle_path"]).exists()
    assert Path(bundle["markdown_path"]).exists()


def test_retry_prompt_bundle_noops_without_known_fails(tmp_path: Path) -> None:
    module = _load_module()
    checklist = tmp_path / "latest_completion_checklist.json"
    checklist.write_text(
        json.dumps({"payload": {"known_failures": [], "workingness_policy": {"consensus_role": "advisory_only"}}}),
        encoding="utf-8",
    )

    bundle = module.build_retry_prompt_bundle(checklist_path=checklist, output_root=tmp_path / "out")

    assert bundle["status"] == "no_known_fails"
    assert bundle["prompt_count"] == 0
    assert Path(bundle["bundle_path"]).exists()
    assert Path(bundle["markdown_path"]).exists()
