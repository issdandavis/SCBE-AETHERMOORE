from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.benchmark.harness_research_matrix import build_research_matrix, render_research_text

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_research_matrix_covers_required_harness_lanes() -> None:
    matrix = build_research_matrix()
    lane_ids = {lane["lane_id"] for lane in matrix["lanes"]}

    assert matrix["schema_version"] == "scbe_harness_research_matrix_v1"
    assert matrix["source_routes"]["route_count"] >= 9
    assert {
        "terminal-bench-shape",
        "swe-bench-shape",
        "agent-cli-competition",
        "sealed-small-context-handoff",
        "agentic-ladder",
        "terminus-analog-actions",
        "m4-manifest-interop",
        "hydra-dry-run",
        "kaggle-config-readiness",
    }.issubset(lane_ids)
    assert matrix["lane_count"] == len(matrix["lanes"])


def test_research_matrix_does_not_claim_external_parity_or_training_data() -> None:
    matrix = build_research_matrix()

    external = [lane for lane in matrix["lanes"] if lane["family"] in {"terminal_bench", "swe_bench"}]
    assert external
    assert all(lane["parity_claim"] == "not_claimed" for lane in external)
    assert any("not copied into training corpora" in note for note in matrix["notes"])
    assert any("Research-source routes feed RAG" in note for note in matrix["notes"])


def test_research_matrix_commands_are_explicit_and_local_first() -> None:
    matrix = build_research_matrix()

    for lane in matrix["lanes"]:
        assert lane["local_command"]
        assert isinstance(lane["local_command"], list)
        assert all(isinstance(part, str) and part for part in lane["local_command"])
        assert lane["promotion_gate"]
        assert lane["cost"] > 0

    text = render_research_text(matrix)
    assert "GeoSeal Harness Research Matrix" in text
    assert "hydra-dry-run" in text
    assert "m4-manifest-interop" in text
    assert "Research Source Routes" in text
    assert "academic_papers" in text


def test_research_matrix_cli_json_output() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/benchmark/harness_research_matrix.py", "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    matrix = json.loads(proc.stdout)
    assert matrix["lane_count"] >= 8
    assert matrix["families"]["m4_mesh"] == 1
    assert matrix["source_routes"]["families"]["tor"] == 1


def test_geoseal_cli_harness_research_passthrough() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "src.geoseal_cli", "harness-research", "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    matrix = json.loads(proc.stdout)
    assert "hydra_swarm" in matrix["families"]
