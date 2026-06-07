from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.eval.governance_tower_defense_eval import render_markdown, run_eval


def test_tower_defense_eval_reports_all_defenses() -> None:
    report = run_eval([])
    assert set(report["summary"]) == {
        "always_allow",
        "always_block",
        "cheap_keyword",
        "scbe_regex",
        "scbe_stream_state",
        "scbe_trajectory_gate",
    }


def test_tower_defense_eval_scores_hidden_labels() -> None:
    from scripts.eval.governance_tower_defense_eval import _episodes

    report = run_eval(_episodes())
    always_allow = report["summary"]["always_allow"]
    always_block = report["summary"]["always_block"]
    stream = report["summary"]["scbe_stream_state"]
    trajectory = report["summary"]["scbe_trajectory_gate"]

    assert always_allow["event_false_allow"]["k"] == always_allow["event_false_allow"]["n"]
    assert always_block["event_false_block"]["k"] == always_block["event_false_block"]["n"]
    assert stream["episode_detection"]["k"] >= report["summary"]["scbe_regex"]["episode_detection"]["k"]
    assert trajectory["episode_detection"]["k"] >= report["summary"]["scbe_regex"]["episode_detection"]["k"]


def test_tower_defense_markdown_renders_headline() -> None:
    from scripts.eval.governance_tower_defense_eval import _episodes

    md = render_markdown(run_eval(_episodes()))
    assert "# Governance Tower-Defense Stream Eval" in md
    assert "`scbe_stream_state`" in md
    assert "`scbe_trajectory_gate`" in md
    assert "Event false-allow" in md
