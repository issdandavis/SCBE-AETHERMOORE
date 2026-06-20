#!/usr/bin/env python3
"""SCBE benchmark improvement circuit.

The circuit is intentionally not a leaderboard claim. It is an operating loop:
test one high-value benchmark surface, isolate the failure, improve the system,
then cross-test on a different benchmark so we do not overfit one arena.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "artifacts" / "benchmarks" / "scbe_benchmark_circuit"


@dataclass(frozen=True)
class CircuitLane:
    rank: int
    lane_id: str
    benchmark: str
    company_value: str
    local_probe: str
    latest_json: str
    fail_origin: str
    obstacle: str
    improve_target: str
    cross_test: str
    claim_boundary: str


CIRCUIT: list[CircuitLane] = [
    CircuitLane(
        rank=1,
        lane_id="terminal-bench-adapter",
        benchmark="Terminal-Bench",
        company_value="CLI agents that can finish real shell, repo, script, and debugging tasks",
        local_probe="python scripts/benchmark/terminal_bench_adapter.py",
        latest_json="artifacts/benchmarks/terminal_bench_adapter/latest_report.json",
        fail_origin="official Terminal-Bench harness access",
        obstacle="local answer-file adapter exists; official tb runner still needs to call the same contract",
        improve_target=(
            "map official Terminal-Bench task import to the local setup/execute/answer/verifier/receipt adapter"
        ),
        cross_test="real-patch-tasks",
        claim_boundary="adapter/readiness work only until official Terminal-Bench tasks run",
    ),
    CircuitLane(
        rank=2,
        lane_id="bfcl-tool-call-adapter",
        benchmark="BFCL",
        company_value="tool routing, JSON/schema correctness, API-call reliability, argument discipline",
        local_probe="scbe bench full",
        latest_json="artifacts/benchmarks/scbe_full_system/latest_report.json",
        fail_origin="tools.json is governed but not exported in BFCL function-call eval format",
        obstacle="missing schema normalizer, argument verifier, and multi-turn tool-call transcript scorer",
        improve_target=(
            "convert packages/agent-bus/tools.json into BFCL-compatible schemas and replay fixtures against local "
            "tool calls"
        ),
        cross_test="tau-bench-policy",
        claim_boundary="local BFCL adapter fixture until official BFCL runner executes",
    ),
    CircuitLane(
        rank=3,
        lane_id="mle-bench-kaggle-mini",
        benchmark="MLE-bench",
        company_value="autonomous ML engineering: data prep, training, scoring, notebook/submission loop",
        local_probe="kaggle kernels status issacizrealdavis/scbe-longform-chain-integrity-benchmark",
        latest_json=(
            "artifacts/kaggle/scbe-longform-chain-integrity/remote-output-v3/longform_chain_integrity_latest.json"
        ),
        fail_origin="Kaggle execution loop exists for custom kernels, but not yet competition tasks",
        obstacle="needs competition dataset selection, scorer wiring, time budget, and submission artifact contract",
        improve_target=(
            "start with one small Kaggle dataset lane: download, train baseline, score, write receipt, compare to "
            "public baseline"
        ),
        cross_test="terminal-bench-adapter",
        claim_boundary="custom Kaggle kernel evidence until official MLE-bench competition subset runs",
    ),
    CircuitLane(
        rank=4,
        lane_id="browsergym-webarena-adapter",
        benchmark="WebArena / BrowserGym / VisualWebArena",
        company_value="real browser automation with state, permissions, forms, visual ambiguity, and recovery",
        local_probe="scbe bench rubix-browser --json",
        latest_json="artifacts/benchmarks/rubix_browser_hypercube/latest_report.json",
        fail_origin="Rubix permission geometry exists locally; official browser task APIs are not bridged",
        obstacle="missing observation adapter, action adapter, login/session policy, and official success verifier",
        improve_target=(
            "map Rubix faces to browser actions: observe, click, type, wait, backtrack, permission-veto, receipt"
        ),
        cross_test="osworld-adapter",
        claim_boundary="local Rubix Browser fixture until official browser benchmarks run",
    ),
    CircuitLane(
        rank=5,
        lane_id="swe-multilingual-aider-polyglot",
        benchmark="SWE-bench Multilingual / Aider Polyglot",
        company_value="cross-language repair and translation with tests, patches, and scoped edits",
        local_probe="python scripts/benchmark/real_patch_task_benchmark.py",
        latest_json="artifacts/benchmarks/real_patch_tasks/latest_report.json",
        fail_origin="local patch fixtures pass, but official multilingual issue/task import is not wired",
        obstacle="needs repo checkout sandbox, language-specific test runners, patch extraction, and result scorer",
        improve_target=(
            "add one polyglot lane per language: Python, JS/TS, Rust, Go, Java, C++ with same repair contract"
        ),
        cross_test="bfcl-tool-call-adapter",
        claim_boundary="local deterministic repair fixtures until public multilingual suites run",
    ),
    CircuitLane(
        rank=6,
        lane_id="tau-bench-policy",
        benchmark="tau-bench / Tau2-bench",
        company_value="business workflows: policy compliance, multi-turn state, customer ops, refunds/orders/bookings",
        local_probe="scbe bench full",
        latest_json="artifacts/benchmarks/scbe_full_system/latest_report.json",
        fail_origin="SCBE has governance and tool receipts, but not a retail/airline user-policy simulator",
        obstacle="missing domain database, policy document parser, user simulator, and action legality grader",
        improve_target="create a local retail policy microbench using Polly receipts and agent-bus tool calls",
        cross_test="bfcl-tool-call-adapter",
        claim_boundary="local tau-style policy fixture until official tau benchmark runs",
    ),
    CircuitLane(
        rank=7,
        lane_id="osworld-adapter",
        benchmark="OSWorld",
        company_value="desktop computer-use agents across files, apps, browser, office tools, and recovery",
        local_probe="python scripts/benchmark/hard_agentic_benchmark_pretest.py --filter osworld",
        latest_json="artifacts/benchmarks/hard_agentic_pretest/latest_report.json",
        fail_origin="desktop adapter needs stable observation/action boundary and environment reset",
        obstacle=(
            "official OSWorld environment not running; local control needs screenshot, action, receipt, and "
            "rollback loop"
        ),
        improve_target="add SCBE desktop-control contract: observe_screen, act, verify_state, rollback, receipt",
        cross_test="browsergym-webarena-adapter",
        claim_boundary="adapter/readiness work only until official OSWorld tasks run",
    ),
    CircuitLane(
        rank=8,
        lane_id="browsecomp-gaia-research",
        benchmark="BrowseComp / GAIA",
        company_value="deep research, citation discipline, file handling, multimodal/tool use",
        local_probe="scbe bench research --json",
        latest_json="artifacts/benchmarks/research_agent_fixtures/latest_report.json",
        fail_origin="local fixtures pass, but official question sets and answer validators are not wired",
        obstacle="needs official task import, source receipts, answer verifier, and anti-hallucination scorer",
        improve_target=(
            "build source-backed answer packet: query plan, fetched sources, citations, final answer, verifier"
        ),
        cross_test="mle-bench-kaggle-mini",
        claim_boundary="local BrowseComp/GAIA-style fixtures until official sets run",
    ),
    CircuitLane(
        rank=9,
        lane_id="arc-neurogolf-reasoning",
        benchmark="ARC-AGI-2 / NeuroGolf",
        company_value="hard abstract reasoning and grid/program synthesis research",
        local_probe="python scripts/benchmark/arc_style_grid_benchmark.py",
        latest_json="artifacts/benchmarks/arc_style_grid/latest_report.json",
        fail_origin="partial local grid solving; official/private generalization remains unproven",
        obstacle=(
            "needs broader primitive families, rejection tests, blind split discipline, and anti-overfit reporting"
        ),
        improve_target=(
            "add one primitive family at a time, with positive, negative, malformed, and neighboring task tests"
        ),
        cross_test="swe-multilingual-aider-polyglot",
        claim_boundary="local/synthetic grid evidence unless submitted to official competition or held-out split",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_commit() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"_parse_error": f"invalid JSON: {path}"}


def score_from_report(report: dict[str, Any] | None) -> tuple[float | None, str]:
    if not report:
        return None, "artifact missing"
    if report.get("_parse_error"):
        return None, report["_parse_error"]
    score = report.get("score")
    if isinstance(score, dict):
        if isinstance(score.get("percent"), (int, float)):
            return float(score["percent"]) / 100.0, "score.percent"
        if isinstance(score.get("score_percent"), (int, float)):
            return float(score["score_percent"]) / 100.0, "score.score_percent"
        if isinstance(score.get("score"), (int, float)):
            return float(score["score"]), "score.score"
    summary = report.get("summary")
    if isinstance(summary, dict):
        for key in ("pass_rate", "scbe_pass_rate", "neurogolf_pass_rate"):
            if isinstance(summary.get(key), (int, float)):
                return float(summary[key]), f"summary.{key}"
        if summary.get("decision") == "PASS":
            return 1.0, "summary.decision=PASS"
    if isinstance(report.get("validation_ok"), (int, float)) and isinstance(report.get("tasks_total"), (int, float)):
        total = float(report["tasks_total"])
        if total:
            return float(report["validation_ok"]) / total, "validation_ok/tasks_total"
    return None, "score not extracted"


def status_for(score: float | None, artifact_exists: bool) -> str:
    if not artifact_exists:
        return "NEEDS_FIRST_ARTIFACT"
    if score is None:
        return "NEEDS_SCORER"
    if score >= 0.999:
        return "PASS_LOCAL"
    if score >= 0.5:
        return "PARTIAL_LOCAL"
    return "LOW_LOCAL"


def build_report() -> dict[str, Any]:
    lanes = []
    for lane in CIRCUIT:
        artifact = REPO_ROOT / lane.latest_json
        report = read_json(artifact)
        score, score_basis = score_from_report(report)
        status = status_for(score, artifact.exists())
        lanes.append(
            {
                "rank": lane.rank,
                "lane_id": lane.lane_id,
                "benchmark": lane.benchmark,
                "company_value": lane.company_value,
                "local_probe": lane.local_probe,
                "latest_json": lane.latest_json,
                "artifact_exists": artifact.exists(),
                "status": status,
                "score": round(score, 4) if score is not None else None,
                "score_basis": score_basis,
                "fail_origin": lane.fail_origin,
                "obstacle": lane.obstacle,
                "improve_target": lane.improve_target,
                "cross_test": lane.cross_test,
                "claim_boundary": lane.claim_boundary,
            }
        )

    next_lane = next(
        (
            lane
            for lane in lanes
            if lane["status"] in {"NEEDS_FIRST_ARTIFACT", "NEEDS_SCORER", "PARTIAL_LOCAL", "LOW_LOCAL"}
        ),
        lanes[0],
    )
    return {
        "schema_version": "scbe_benchmark_circuit_v1",
        "generated_at_utc": utc_now(),
        "commit": git_commit(),
        "method": [
            "Test one lane.",
            "Identify failure origin and obstacle.",
            "Make one scoped improvement.",
            "Cross-test on a different benchmark lane.",
            "Only claim what the artifact proves.",
        ],
        "summary": {
            "lanes_total": len(lanes),
            "pass_local": sum(1 for lane in lanes if lane["status"] == "PASS_LOCAL"),
            "partial_local": sum(1 for lane in lanes if lane["status"] == "PARTIAL_LOCAL"),
            "needs_scorer": sum(1 for lane in lanes if lane["status"] == "NEEDS_SCORER"),
            "needs_first_artifact": sum(1 for lane in lanes if lane["status"] == "NEEDS_FIRST_ARTIFACT"),
            "next_lane": next_lane["lane_id"],
            "next_improve_target": next_lane["improve_target"],
            "next_cross_test": next_lane["cross_test"],
        },
        "lanes": lanes,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# SCBE Benchmark Circuit",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Commit: `{report['commit']}`",
        f"- Next lane: `{report['summary']['next_lane']}`",
        f"- Next cross-test: `{report['summary']['next_cross_test']}`",
        "",
        "## Circuit Rule",
        "",
        "Test one lane, isolate the failure, make one scoped improvement, then test a different "
        "lane so the system gets stronger instead of overfitting.",
        "",
        "## Ordered Lanes",
        "",
        "| # | Lane | Benchmark | Status | Score | Failure Origin | Improve Target | Cross-Test |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for lane in report["lanes"]:
        score = "n/a" if lane["score"] is None else f"{lane['score']:.1%}"
        lines.append(
            "| {rank} | {lane_id} | {benchmark} | {status} | {score} | {origin} | {target} | {cross} |".format(
                rank=lane["rank"],
                lane_id=lane["lane_id"],
                benchmark=lane["benchmark"],
                status=lane["status"],
                score=score,
                origin=lane["fail_origin"],
                target=lane["improve_target"],
                cross=lane["cross_test"],
            )
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "This circuit is an engineering map, not a public leaderboard claim. Each lane must "
            "cite its command, artifact, commit, and claim boundary before being used in public copy.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args()

    report = build_report()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"scbe_benchmark_circuit_{stamp}.json"
    md_path = out_dir / f"scbe_benchmark_circuit_{stamp}.md"
    latest_json = out_dir / "latest_report.json"
    latest_md = out_dir / "LATEST.md"
    payload = json.dumps(report, indent=2)
    json_path.write_text(payload, encoding="utf-8")
    latest_json.write_text(payload, encoding="utf-8")
    write_markdown(report, md_path)
    write_markdown(report, latest_md)

    if args.json:
        print(payload)
    else:
        summary = report["summary"]
        print(
            "scbe benchmark circuit: "
            f"pass={summary['pass_local']} partial={summary['partial_local']} "
            f"needs_scorer={summary['needs_scorer']} next={summary['next_lane']} "
            f"cross_test={summary['next_cross_test']}"
        )
        print(f"report={latest_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
