from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "eval" / "aether_external_task_lanes.v1.json"
DOC = ROOT / "docs" / "benchmarks" / "OPEN_SOURCE_AGENT_TASK_LANES.md"
PROGRAMMER_INDEX = ROOT / "docs" / "benchmarks" / "AETHER_PROGRAMMER_INDEX.md"


def _config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_external_task_lanes_are_public_and_actionable() -> None:
    data = _config()

    assert data["schema_version"] == "aether_external_task_lanes_v1"
    assert "open-source task pools" in data["purpose"].lower()
    assert len(data["lanes"]) >= 10
    for lane in data["lanes"]:
        assert lane["lane_id"]
        assert lane["track_id"]
        assert lane["source_name"]
        assert lane["source_url"].startswith("https://")
        assert lane["task_pool"]
        assert lane["first_run_plan"]
        assert lane["completion_rule"]
        assert lane["why_it_matters"]


def test_external_task_lanes_cover_core_programmer_index_tracks() -> None:
    data = _config()

    covered = {lane["track_id"] for lane in data["lanes"]}
    assert {
        "real_repo_repair",
        "terminal_execution",
        "multi_language_editing",
        "function_correctness",
        "fresh_algorithmic_coding",
        "security_governance",
        "browser_desktop_operation",
    }.issubset(covered)


def test_strong_assistant_model_names_non_model_layers() -> None:
    data = _config()

    model = data["strong_coding_assistant_model"]
    assert "base_model" in model
    assert "context_system" in model
    assert "task_harness" in model
    assert "tool_runtime" in model
    assert "verification_loop" in model
    assert "governance_layer" in model


def test_model_orchestration_uses_leader_worker_harness_split() -> None:
    data = _config()

    orchestration = data["model_orchestration"]
    assert "strongest available model as leader" in orchestration["principle"]
    assert "assign worker agents" in orchestration["leader_role"]
    assert "generate candidate fixes" in orchestration["worker_role"]
    assert "3-1000 agents" in orchestration["scaling_rule"]
    assert "No model is completion authority" in orchestration["completion_authority"]


def test_retrieval_stack_includes_mvp_and_sourcegraph_path() -> None:
    data = _config()

    tools = {tool["tool"]: tool for tool in data["retrieval_stack"]}
    assert "ripgrep" in tools
    assert "universal-ctags" in tools
    assert "tree-sitter" in tools
    assert tools["tree-sitter"]["source_url"].startswith("https://")
    assert "SCIP" in tools
    assert "Sourcegraph-style" in tools["SCIP"]["mvp_use"]


def test_optional_external_tools_are_tools_not_judges() -> None:
    data = _config()

    tools = {tool["tool"]: tool for tool in data["optional_external_tools"]}
    assert "GitHub Copilot coding agent" in tools
    assert "SCBE remains the verifier" in tools["GitHub Copilot coding agent"]["use"]
    assert "Sourcegraph/Cody or open-source code search stack" in tools


def test_docs_link_external_task_lanes_and_guard_claims() -> None:
    doc = DOC.read_text(encoding="utf-8")
    index = PROGRAMMER_INDEX.read_text(encoding="utf-8")

    assert "What Makes A Strong Coding Assistant" in doc
    assert "Model Orchestration" in doc
    assert "highest-context model should be the leader" in doc
    assert "Sourcegraph-Style Context" in doc
    assert "GitHub good first issues" in doc
    assert "external tools can propose" in doc.lower()
    assert "SCBE decides completion" in doc
    assert "Not allowed yet" in doc
    assert "OPEN_SOURCE_AGENT_TASK_LANES.md" in index
