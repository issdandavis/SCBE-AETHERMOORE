"""Tests for HYDRA branch orchestrator (ChoiceScript + council)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hydra.branch_orchestrator import (
    graph_choicescript,
    list_graph_templates,
    list_strategies,
    run_branch_workflow,
)


def test_list_strategies_contains_expected_modes() -> None:
    strategies = list_strategies()
    assert "all_paths" in strategies
    assert "first_match" in strategies
    assert "scored" in strategies


def test_list_graph_templates_contains_research_pipeline() -> None:
    templates = list_graph_templates()
    names = [template["name"] for template in templates]
    assert "research_pipeline" in names
    assert "content_publisher" in names
    assert "training_funnel" in names


def test_graph_choicescript_export_contains_title() -> None:
    export = graph_choicescript("research_pipeline", topic="swarm safety")
    assert "*title research_pipeline" in export
    assert "*choice" in export


def test_run_branch_workflow_returns_paths_and_best_path() -> None:
    payload = run_branch_workflow(
        graph_name="research_pipeline",
        topic="swarm safety",
        strategy="all_paths",
        providers=["claude", "gpt", "gemini"],
    )
    assert payload["graph_name"] == "research_pipeline"
    assert payload["paths_explored"] > 0
    assert payload["best_path"] is not None
    assert payload["coverage"] > 0
    assert payload["council"] is not None
    assert payload["council"]["winner_path_id"] is not None


def test_run_branch_workflow_path_ids_are_unique() -> None:
    payload = run_branch_workflow(
        graph_name="research_pipeline",
        topic="swarm safety",
        strategy="all_paths",
    )
    path_ids = [path["id"] for path in payload["all_paths"]]
    assert len(path_ids) == len(set(path_ids))


def test_run_branch_workflow_can_disable_council() -> None:
    payload = run_branch_workflow(
        graph_name="training_funnel",
        strategy="first_match",
        enable_council=False,
    )
    assert payload["council"] is None


def test_run_branch_workflow_exports_files(tmp_path: Path) -> None:
    n8n_path = tmp_path / "branch.workflow.json"
    cs_path = tmp_path / "branch.choicescript.txt"
    payload = run_branch_workflow(
        graph_name="content_publisher",
        strategy="all_paths",
        export_n8n_path=str(n8n_path),
        export_choicescript_path=str(cs_path),
    )
    assert n8n_path.exists()
    assert cs_path.exists()
    assert payload["exports"]["n8n_workflow"].endswith("branch.workflow.json")
    assert payload["exports"]["choicescript"].endswith("branch.choicescript.txt")


def test_run_branch_workflow_rejects_unknown_graph() -> None:
    with pytest.raises(ValueError):
        run_branch_workflow(graph_name="unknown_graph")
