#!/usr/bin/env python3
"""Local ARC-style grid benchmark for NeuroGolf/SCBE.

This is a pre-ARC lane, not an official ARC-AGI-2 score. It uses synthetic
ARC-shaped tasks with train examples, hidden expected test outputs, restricted
IR synthesis, and receipt hashes so we can measure execution before wiring the
official dataset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from neurogolf.arc_io import load_arc_task  # noqa: E402
from neurogolf.family_lattice import task_topology  # noqa: E402
from neurogolf.solver import execute_program, synthesize_program  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "artifacts" / "benchmarks" / "arc_style_grid"

PATENT_PROVENANCE_REFS = (
    {
        "path": "docs/PATENT_DETAILED_DESCRIPTION.md",
        "claim_family": "geometric state evaluation and bounded decision gates",
        "tie": (
            "The benchmark records topology vectors, restricted programs, pass/fail results, and "
            "receipt hashes as executable evidence of state-to-decision processing."
        ),
    },
    {
        "path": "docs/specs/EVALUATION_CONTRACT_v1.md",
        "claim_family": "reproducible evaluation envelope",
        "tie": (
            "The report emits a stable JSON schema with summary, per-task lanes, hidden expected "
            "comparison, and artifact paths."
        ),
    },
    {
        "path": "docs/legal/patent-workbench/claim_support_scan.md",
        "claim_family": "claim-support provenance",
        "tie": (
            "This local lane supplies a code-backed benchmark artifact that can be cited as "
            "implementation evidence, not as a new legal conclusion."
        ),
    },
    {
        "path": "docs/benchmarks/HARD_AGENTIC_BENCHMARK_PRETEST.md",
        "claim_family": "hard benchmark readiness and non-leaky assistance",
        "tie": (
            "The ARC-style lane closes one blocker from the hard benchmark pretest by adding a local "
            "grid-reasoning execution surface before official ARC-AGI-2 runs."
        ),
    },
)


Grid = list[list[int]]


@dataclass(frozen=True)
class ArcStyleFixture:
    task_id: str
    expected_family: str
    train: tuple[dict[str, Grid], ...]
    test_input: Grid
    expected_output: Grid
    why_hard: str
    non_leaky_assist: tuple[str, ...]
    constructive_branch: str
    defender_branch: str


@dataclass(frozen=True)
class LaneResult:
    task_id: str
    lane: str
    passed: bool
    family: str
    program_name: str
    duration_ms: int
    topology: list[float]
    predicted: Grid
    expected: Grid
    receipt_hash: str
    error: str = ""


FIXTURES: tuple[ArcStyleFixture, ...] = (
    ArcStyleFixture(
        task_id="arc_local_color_remap",
        expected_family="color_remap",
        train=(
            {
                "input": [[1, 2, 0], [2, 1, 0]],
                "output": [[3, 4, 0], [4, 3, 0]],
            },
            {
                "input": [[2, 1], [0, 2]],
                "output": [[4, 3], [0, 4]],
            },
        ),
        test_input=[[1, 0, 2], [2, 1, 0]],
        expected_output=[[3, 0, 4], [4, 3, 0]],
        why_hard="Requires inducing a color mapping from examples instead of copying the input shape.",
        non_leaky_assist=("List observed color pairs.", "Check that zero/background remains stable."),
        constructive_branch=(
            "Infer a total color substitution table from train input/output pairs, then apply it to the held-out grid."
        ),
        defender_branch=(
            "Reject mappings that alter background, collide inconsistently, or only fit one train occurrence."
        ),
    ),
    ArcStyleFixture(
        task_id="arc_local_shift_color_remap",
        expected_family="shift_then_color_remap",
        train=(
            {
                "input": [[1, 0, 0], [0, 2, 0], [0, 0, 0]],
                "output": [[0, 0, 0], [5, 0, 0], [0, 6, 0]],
            },
        ),
        test_input=[[0, 1, 0], [0, 0, 2], [0, 0, 0]],
        expected_output=[[0, 0, 0], [0, 5, 0], [0, 0, 6]],
        why_hard="Requires separating motion from recoloring and preserving both in the held-out grid.",
        non_leaky_assist=("Expose candidate translation vectors.", "Validate remap after geometric move."),
        constructive_branch="Search small translations, then infer the color remap after the translated shape aligns.",
        defender_branch=(
            "Reject any branch where remapping before motion fits train but changes spatial causality "
            "on held-out structure."
        ),
    ),
    ArcStyleFixture(
        task_id="arc_local_flip_x_color_remap",
        expected_family="flip_x_then_color_remap",
        train=(
            {
                "input": [[1, 2, 0], [3, 0, 0]],
                "output": [[0, 7, 8], [0, 0, 9]],
            },
        ),
        test_input=[[0, 1, 2], [0, 3, 0]],
        expected_output=[[7, 8, 0], [0, 9, 0]],
        why_hard="Requires detecting a left-right symmetry before applying color semantics.",
        non_leaky_assist=("Try dihedral transforms as hypotheses.", "Score hypotheses on train examples only."),
        constructive_branch=(
            "Try left-right reflection as the geometric carrier, then bind reflected source colors to output colors."
        ),
        defender_branch="Reject transforms that explain colors but fail the reflected coordinate relationship.",
    ),
    ArcStyleFixture(
        task_id="arc_local_crop_bbox",
        expected_family="crop_bbox",
        train=(
            {
                "input": [[0, 0, 0, 0], [0, 2, 2, 0], [0, 2, 0, 0], [0, 0, 0, 0]],
                "output": [[2, 2], [2, 0]],
            },
        ),
        test_input=[[0, 0, 0, 0, 0], [0, 0, 4, 4, 0], [0, 0, 4, 0, 0], [0, 0, 0, 0, 0]],
        expected_output=[[4, 4], [4, 0]],
        why_hard="Requires object boundary extraction and output shape change.",
        non_leaky_assist=("Expose non-zero bounding boxes.", "Allow shape-changing programs with explicit receipts."),
        constructive_branch="Locate the foreground component and reduce the output to its minimal bounding box.",
        defender_branch="Reject crops that depend on absolute position instead of object extent.",
    ),
    ArcStyleFixture(
        task_id="arc_local_tile_mirror",
        expected_family="tile_mirror_2x2",
        train=(
            {
                "input": [[1, 0], [0, 2]],
                "output": [[1, 0, 0, 1], [0, 2, 2, 0], [0, 1, 1, 0], [2, 0, 0, 2]],
            },
        ),
        test_input=[[3, 0], [0, 4]],
        expected_output=[[3, 0, 0, 3], [0, 4, 4, 0], [0, 3, 3, 0], [4, 0, 0, 4]],
        why_hard="Requires inferring a composed tiling pattern rather than a same-size transform.",
        non_leaky_assist=("Expose candidate tiling factors.", "Validate quadrant symmetries on train examples."),
        constructive_branch=(
            "Infer a 2x2 tiling operation where quadrants are generated by mirrored variants of the input."
        ),
        defender_branch="Reject tile hypotheses unless all quadrants are explained by one reusable dihedral rule.",
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def git_head() -> str:
    try:
        import subprocess

        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
        )
        return proc.stdout.strip() if proc.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def grid_to_list(grid: np.ndarray) -> Grid:
    return [[int(value) for value in row] for row in grid.tolist()]


def write_fixture(root: Path, fixture: ArcStyleFixture) -> Path:
    path = root / f"{fixture.task_id}.json"
    payload = {
        "train": list(fixture.train),
        "test": [{"input": fixture.test_input}],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def run_identity_baseline(path: Path, fixture: ArcStyleFixture) -> LaneResult:
    task = load_arc_task(path)
    start = time.perf_counter()
    predicted_np = task.test_inputs[0].copy()
    duration_ms = int((time.perf_counter() - start) * 1000)
    predicted = grid_to_list(predicted_np)
    expected = fixture.expected_output
    passed = predicted == expected
    topology = [round(float(value), 4) for value in task_topology(task).tolist()]
    receipt = {
        "task_id": fixture.task_id,
        "lane": "identity_baseline",
        "predicted": predicted,
        "expected": expected,
        "passed": passed,
        "topology": topology,
    }
    return LaneResult(
        task_id=fixture.task_id,
        lane="identity_baseline",
        passed=passed,
        family="identity",
        program_name="identity",
        duration_ms=duration_ms,
        topology=topology,
        predicted=predicted,
        expected=expected,
        receipt_hash=sha256_json(receipt),
    )


def run_neurogolf_lane(path: Path, fixture: ArcStyleFixture) -> LaneResult:
    task = load_arc_task(path)
    start = time.perf_counter()
    try:
        solution = synthesize_program(task)
        predicted_np = execute_program(task.test_inputs[0], solution.program)
        duration_ms = int((time.perf_counter() - start) * 1000)
        predicted = grid_to_list(predicted_np)
        expected = fixture.expected_output
        passed = predicted == expected
        topology = [round(float(value), 4) for value in task_topology(task).tolist()]
        receipt = {
            "task_id": fixture.task_id,
            "lane": "neurogolf_restricted_ir",
            "family": solution.family,
            "program": solution.program.name,
            "steps": [step.__dict__ for step in solution.program.steps],
            "predicted": predicted,
            "expected": expected,
            "passed": passed,
            "topology": topology,
        }
        return LaneResult(
            task_id=fixture.task_id,
            lane="neurogolf_restricted_ir",
            passed=passed,
            family=solution.family,
            program_name=solution.program.name,
            duration_ms=duration_ms,
            topology=topology,
            predicted=predicted,
            expected=expected,
            receipt_hash=sha256_json(receipt),
        )
    except Exception as exc:  # pragma: no cover - exercised by future failures
        duration_ms = int((time.perf_counter() - start) * 1000)
        topology = [round(float(value), 4) for value in task_topology(task).tolist()]
        receipt = {
            "task_id": fixture.task_id,
            "lane": "neurogolf_restricted_ir",
            "error": f"{type(exc).__name__}: {exc}",
            "topology": topology,
        }
        return LaneResult(
            task_id=fixture.task_id,
            lane="neurogolf_restricted_ir",
            passed=False,
            family="error",
            program_name="error",
            duration_ms=duration_ms,
            topology=topology,
            predicted=[],
            expected=fixture.expected_output,
            receipt_hash=sha256_json(receipt),
            error=f"{type(exc).__name__}: {exc}",
        )


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# ARC-Style Grid Benchmark",
        "",
        f"Generated: `{report['generated_at_utc']}`",
        f"Decision: `{summary['decision']}`",
        f"Claim boundary: `{report['claim_boundary']}`",
        "",
        "## Summary",
        "",
        "| Lane | Passes | Pass rate |",
        "| --- | ---: | ---: |",
        f"| Identity baseline | `{summary['identity_passes']} / {summary['task_count']}` "
        f"| `{summary['identity_pass_rate']}` |",
        f"| NeuroGolf restricted IR | `{summary['neurogolf_passes']} / {summary['task_count']}` "
        f"| `{summary['neurogolf_pass_rate']}` |",
        "",
        "## Per-Task Results",
        "",
        "| Task | Expected family | Solver family | Passed | Receipt |",
        "| --- | --- | --- | --- | --- |",
    ]
    fixtures = {item["task_id"]: item for item in report["fixtures"]}
    solver_by_task = {item["task_id"]: item for item in report["neurogolf_results"]}
    for task_id, fixture in fixtures.items():
        result = solver_by_task[task_id]
        lines.append(
            f"| `{task_id}` | `{fixture['expected_family']}` | `{result['family']}` "
            f"| `{result['passed']}` | `{result['receipt_hash'][:12]}` |"
        )
    lines.extend(
        [
            "",
            "## Missing-Link Assistance",
            "",
            "These are acceptable supports because they expose process structure "
            "without revealing hidden test outputs.",
            "",
        ]
    )
    for fixture in report["fixtures"]:
        lines.append(f"### {fixture['task_id']}")
        lines.append("")
        lines.append(f"- Why hard: {fixture['why_hard']}")
        lines.append(f"- Constructive branch: {fixture['bifurcated_reasoning']['constructive_branch']}")
        lines.append(f"- Defender branch: {fixture['bifurcated_reasoning']['defender_branch']}")
        lines.append(f"- Merge rule: {fixture['bifurcated_reasoning']['merge_rule']}")
        flow = fixture["bifurcated_reasoning"]["flow_model"]
        lines.append(
            f"- Flow model: {flow['source']} -> {flow['branch_a']} / {flow['branch_b']} "
            f"-> {flow['merge']} -> {flow['sink']}"
        )
        for item in fixture["non_leaky_assist"]:
            lines.append(f"- Assist: {item}")
        lines.append("")
    lines.extend(
        [
            "## Patent Provenance Links",
            "",
            "These are evidence links only. They do not assert patentability or legal sufficiency.",
            "",
            "| Local reference | Claim family | Evidence tie |",
            "| --- | --- | --- |",
        ]
    )
    for ref in report["patent_provenance"]["refs"]:
        lines.append(f"| `{ref['path']}` | {ref['claim_family']} | {ref['tie']} |")
    return "\n".join(lines)


def build_report(out_dir: Path) -> dict[str, Any]:
    fixture_dir = out_dir / "fixtures"
    identity_results: list[LaneResult] = []
    neurogolf_results: list[LaneResult] = []
    for fixture in FIXTURES:
        path = write_fixture(fixture_dir, fixture)
        identity_results.append(run_identity_baseline(path, fixture))
        neurogolf_results.append(run_neurogolf_lane(path, fixture))
    task_count = len(FIXTURES)
    identity_passes = sum(1 for result in identity_results if result.passed)
    neurogolf_passes = sum(1 for result in neurogolf_results if result.passed)
    summary = {
        "decision": "PASS" if neurogolf_passes == task_count and identity_passes < neurogolf_passes else "HOLD",
        "task_count": task_count,
        "identity_passes": identity_passes,
        "identity_pass_rate": round(identity_passes / task_count, 4),
        "neurogolf_passes": neurogolf_passes,
        "neurogolf_pass_rate": round(neurogolf_passes / task_count, 4),
        "avg_solver_ms": round(sum(result.duration_ms for result in neurogolf_results) / task_count, 2),
        "unresolved_tasks": [result.task_id for result in neurogolf_results if not result.passed],
    }
    report = {
        "schema_version": "scbe_arc_style_grid_benchmark_v1",
        "generated_at_utc": utc_now(),
        "claim_boundary": "synthetic_arc_style_local_pretest_not_official_arc_agi_2",
        "repo_head": git_head(),
        "patent_provenance": {
            "legal_boundary": (
                "implementation evidence only; support found/missing still requires patent workbench review"
            ),
            "proof_goal_split": {
                "proof_layer": (
                    "the auditable steps: fixtures, synthesized IR, topology vectors, "
                    "hidden-output comparison, receipt hashes, and reports"
                ),
                "goal_layer": (
                    "the capability destination: a generalizable grid-reasoning agent that can "
                    "improve from failures and later run official ARC-AGI-2 tasks"
                ),
                "boundary": "proof supports the path taken; it does not by itself prove the end goal has been reached",
            },
            "chain_of_provenance": [
                "synthetic ARC-style fixture JSON written under artifacts",
                "restricted NeuroGolf IR synthesized from train examples",
                "hidden expected output compared outside the prompt/task file",
                "per-lane receipt hash generated from prediction, expected output, topology, and program metadata",
                "stable report JSON and Markdown emitted for audit review",
            ],
            "refs": list(PATENT_PROVENANCE_REFS),
        },
        "summary": summary,
        "fixtures": [
            {
                "task_id": fixture.task_id,
                "expected_family": fixture.expected_family,
                "why_hard": fixture.why_hard,
                "non_leaky_assist": list(fixture.non_leaky_assist),
                "bifurcated_reasoning": {
                    "constructive_branch": fixture.constructive_branch,
                    "defender_branch": fixture.defender_branch,
                    "merge_rule": (
                        "accept only when the constructive program passes train examples and the "
                        "defender branch finds no scope or invariant violation"
                    ),
                    "flow_model": {
                        "source": "train examples",
                        "branch_a": "constructive hypothesis flow",
                        "branch_b": "defender falsification flow",
                        "merge": "restricted IR program plus receipt hash",
                        "sink": "hidden expected-output comparison",
                    },
                },
            }
            for fixture in FIXTURES
        ],
        "identity_results": [asdict(result) for result in identity_results],
        "neurogolf_results": [asdict(result) for result in neurogolf_results],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "latest_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "LATEST.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.out_dir)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "arc-style grid benchmark: "
            f"decision={summary['decision']} "
            f"identity={summary['identity_passes']}/{summary['task_count']} "
            f"neurogolf={summary['neurogolf_passes']}/{summary['task_count']}"
        )
        print(f"report={args.out_dir / 'latest_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
