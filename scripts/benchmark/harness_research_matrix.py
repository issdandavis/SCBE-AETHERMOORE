#!/usr/bin/env python3
"""Research-backed benchmark/readiness lanes for the GeoSeal harness.

This module keeps benchmark lessons executable without copying benchmark tasks
into training data or claiming public leaderboard parity. Each lane records the
local command that proves the SCBE surface and the external benchmark shape it
was inspired by.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research.geoseal_research_routes import build_research_route_matrix  # noqa: E402

SCHEMA_VERSION = "scbe_harness_research_matrix_v1"


@dataclass(frozen=True)
class ResearchLane:
    lane_id: str
    family: str
    finding: str
    local_command: list[str]
    evidence_target: str
    promotion_gate: str
    cost: int
    risk: str
    parity_claim: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_research_lanes() -> list[ResearchLane]:
    """Return compact, executable benchmark lanes for the terminal harness."""

    return [
        ResearchLane(
            lane_id="terminal-bench-shape",
            family="terminal_bench",
            finding="Terminal agents should be graded by final state and verifier tests, not prose confidence.",
            local_command=[
                "python",
                "scripts/benchmark/external_agentic_eval_driver.py",
                "--manifest",
                "config/eval/external_agentic_eval_tasks.sample.json",
                "--validate-only",
            ],
            evidence_target="config/eval/external_agentic_eval_tasks.sample.json",
            promotion_gate="manifest validates; no benchmark data enters training corpora",
            cost=3,
            risk="benchmark_contamination",
            parity_claim="not_claimed",
            source="https://www.tbench.ai/",
        ),
        ResearchLane(
            lane_id="swe-bench-shape",
            family="swe_bench",
            finding="Coding-agent evals should preserve issue, patch, regression test, and sandbox evidence.",
            local_command=[
                "python",
                "scripts/benchmark/external_agentic_eval_driver.py",
                "--manifest",
                "config/eval/external_agentic_eval_tasks.sample.json",
                "--validate-only",
            ],
            evidence_target="artifacts/external_agentic_eval/latest_report.json",
            promotion_gate="adapter validates; official SWE-bench parity remains off until official runner is wired",
            cost=3,
            risk="false_leaderboard_claim",
            parity_claim="not_claimed",
            source="https://github.com/swe-bench",
        ),
        ResearchLane(
            lane_id="agent-cli-competition",
            family="coding_agent_cli",
            finding="CLI assistants need help/version/doctor, machine JSON, permissions, workflow state, and extension points.",
            local_command=[
                "python",
                "scripts/benchmark/cli_competitive_benchmark.py",
            ],
            evidence_target="artifacts/benchmarks/cli_competitive/cli_competitive_benchmark_latest.json",
            promotion_gate="local CLI criteria score updates without hiding gaps",
            cost=2,
            risk="surface_regression",
            parity_claim="local_surface_only",
            source="https://code.claude.com/docs/en/cli-reference",
        ),
        ResearchLane(
            lane_id="sealed-small-context-handoff",
            family="codex_style_handoff",
            finding="Small context packets should carry task, route, evidence refs, and decode agreement without replaying full prose.",
            local_command=[
                "python",
                "-m",
                "pytest",
                "tests/agent_comms/test_secure_handoff.py",
                "-q",
            ],
            evidence_target="src/agent_comms/secure_handoff.py",
            promotion_gate="sealed handoff round-trip, tamper rejection, and shadow metadata tests pass",
            cost=2,
            risk="handoff_secret_leak",
            parity_claim="repo_secure_handoff_only",
            source="repo-native",
        ),
        ResearchLane(
            lane_id="agentic-ladder",
            family="scbe_agentic_ladder",
            finding="Repo-native agent work needs multi-level gates: smoke, tasks, CLI surface, and coding-agent readiness.",
            local_command=[
                "python",
                "scripts/benchmark/agentic_benchmark_ladder.py",
                "run",
                "--max-level",
                "1",
            ],
            evidence_target="benchmarks/scbe_agentic_v1/tasks",
            promotion_gate="level 0 and level 1 pass before external-style claims",
            cost=4,
            risk="overbroad_gate",
            parity_claim="local_ladder_only",
            source="repo-native",
        ),
        ResearchLane(
            lane_id="terminus-analog-actions",
            family="terminal_game_training",
            finding="Analog terminal actions can reduce prompt tokens by making repeated workflow moves explicit primitives.",
            local_command=[
                "python",
                "-m",
                "src.geoseal_cli",
                "terminus-training",
                "--mode",
                "benchmark",
                "--out-dir",
                "artifacts/terminus_training/smoke",
                "--json",
            ],
            evidence_target="artifacts/terminus_training/smoke",
            promotion_gate="checkpoint runner produces deterministic solved/failed verdicts",
            cost=2,
            risk="toy_task_overfit",
            parity_claim="local_training_game_only",
            source="external/cli-quests/terminus",
        ),
        ResearchLane(
            lane_id="m4-manifest-interop",
            family="m4_mesh",
            finding="M4 artifacts need stable manifests, deterministic waves, and explicit interop tests before training use.",
            local_command=[
                "python",
                "-m",
                "pytest",
                "tests/interop/test_m4_manifest_roundtrip.py",
                "tests/interop/test_m4_wave_determinism.py",
                "tests/interop/test_m4_smear_operator.py",
                "tests/interop/test_m4_scbe_graph.py",
                "-q",
            ],
            evidence_target="src/m4mesh",
            promotion_gate="focused M4 interop tests pass",
            cost=5,
            risk="mesh_drift",
            parity_claim="repo_interop_only",
            source="repo-native",
        ),
        ResearchLane(
            lane_id="hydra-dry-run",
            family="hydra_swarm",
            finding="HYDRA should expose swarm plans as dry-run JSON before multi-agent execution mutates files.",
            local_command=[
                "python",
                "-m",
                "hydra.cli_swarm",
                "review harness terminal",
                "--dry-run",
            ],
            evidence_target="hydra/cli_swarm.py",
            promotion_gate="dry-run swarm contract emits deterministic JSON",
            cost=2,
            risk="unbounded_agent_fanout",
            parity_claim="local_swarm_contract_only",
            source="repo-native",
        ),
        ResearchLane(
            lane_id="kaggle-config-readiness",
            family="kaggle_remote_compute",
            finding="Kaggle is useful as a remote lane only after launch configs validate locally.",
            local_command=[
                "python",
                "-m",
                "pytest",
                "tests/test_kaggle_auto_launch.py",
                "-q",
            ],
            evidence_target="config/kaggle",
            promotion_gate="Kaggle launch config tests pass before remote execution",
            cost=3,
            risk="remote_compute_sprawl",
            parity_claim="config_readiness_only",
            source="repo-native",
        ),
    ]


def build_research_matrix() -> dict[str, Any]:
    lanes = build_research_lanes()
    source_routes = build_research_route_matrix()
    risks: dict[str, int] = {}
    families: dict[str, int] = {}
    for lane in lanes:
        risks[lane.risk] = risks.get(lane.risk, 0) + 1
        families[lane.family] = families.get(lane.family, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "lane_count": len(lanes),
        "families": families,
        "risks": risks,
        "lanes": [lane.to_dict() for lane in lanes],
        "source_routes": {
            "schema_version": source_routes["schema_version"],
            "route_count": source_routes["route_count"],
            "families": source_routes["families"],
            "safety_tiers": source_routes["safety_tiers"],
            "global_policy": source_routes["global_policy"],
        },
        "notes": [
            "Benchmark tasks are not copied into training corpora.",
            "External benchmark parity is not claimed until official runners are wired and isolated.",
            "Local lanes are promotion gates for harness readiness, not model intelligence scores.",
            "Research-source routes feed RAG/evidence workflows, but live operational sources remain quarantine-first.",
        ],
    }


def render_research_text(matrix: dict[str, Any]) -> str:
    lines = [
        "GeoSeal Harness Research Matrix",
        "=" * 34,
        f"Lanes: {matrix['lane_count']} | Families: {len(matrix['families'])}",
        "",
    ]
    for lane in matrix["lanes"]:
        command = " ".join(lane["local_command"])
        if len(command) > 96:
            command = f"{command[:93]}..."
        lines.append(f"- {lane['lane_id']} [{lane['family']}] cost={lane['cost']} risk={lane['risk']}")
        lines.append(f"  gate: {lane['promotion_gate']}")
        lines.append(f"  run:  {command}")
    if matrix.get("source_routes"):
        source_routes = matrix["source_routes"]
        lines.extend(["", "Research Source Routes", "-" * 34])
        lines.append(
            f"routes={source_routes['route_count']} families={len(source_routes['families'])} "
            f"safety_tiers={len(source_routes['safety_tiers'])}"
        )
        for family, count in sorted(source_routes["families"].items()):
            lines.append(f"- {family}: {count}")
    lines.append("")
    lines.extend(f"- {note}" for note in matrix["notes"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable research matrix")
    args = parser.parse_args(argv)
    matrix = build_research_matrix()
    if args.json:
        print(json.dumps(matrix, indent=2, sort_keys=True))
    else:
        print(render_research_text(matrix))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
