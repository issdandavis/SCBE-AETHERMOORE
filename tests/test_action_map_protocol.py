from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.training import action_map_protocol as mod


def test_action_map_round_trip_writes_compiled_outputs(tmp_path: Path) -> None:
    start = mod.start_run(
        tmp_path,
        task="repo cleanup telemetry smoke",
        summary="Opened cleanup run.",
        tags=["cleanup"],
        skills=["development-flow-loop"],
    )
    run_id = start["run_id"]

    mod.append_step(
        tmp_path,
        run_id=run_id,
        summary="Mapped dirty roots and categorized archive pressure.",
        touched_layers=["control-plane", "storage"],
        changed_files=["docs/FAST_ACCESS_GUIDE.md"],
        tool="repo_ordering",
        next_action="compile cleanup map",
    )
    mod.close_run(
        tmp_path,
        run_id=run_id,
        summary="Closed cleanup run after generating ownership map.",
        status="completed",
        artifacts=["training/runs/action_maps/example/action_map.json"],
    )

    summary = mod.build_action_map(tmp_path, run_id)
    action_map = json.loads(
        (tmp_path / run_id / "action_map.json").read_text(encoding="utf-8")
    )
    rows = (
        (tmp_path / run_id / "training_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )

    assert summary["terminal_status"] == "completed"
    assert summary["training_rows"] == 2
    assert len(summary["workflow_signature"]) == 16
    assert action_map["task"] == "repo cleanup telemetry smoke"
    assert action_map["summary"]["step_count"] == 1
    assert action_map["timeline"][1]["tool"] == "repo_ordering"
    assert action_map["cleanup_focus"]["task_matches_cleanup"] is True
    assert len(rows) == 2


def test_append_step_requires_existing_run(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        mod.append_step(tmp_path, run_id="missing-run", summary="Should fail.")
