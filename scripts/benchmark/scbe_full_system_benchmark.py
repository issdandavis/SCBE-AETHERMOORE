#!/usr/bin/env python3
"""SCBE full-system benchmark evidence matrix.

This script does not pretend local fixtures are public leaderboard scores.
It builds a reproducible map of:
  - executable local lanes with latest artifacts,
  - custom Kaggle-backed evidence where available,
  - external benchmark targets that are blocked or still need adapters.

Use:
    python scripts/benchmark/scbe_full_system_benchmark.py --json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "artifacts" / "benchmarks" / "scbe_full_system"


@dataclass(frozen=True)
class LaneSpec:
    lane_id: str
    domain: str
    command: str
    latest_json: str
    claim_boundary: str
    target: str
    local: bool = True
    run_in_quick: bool = False
    status_if_missing: str = "MISSING_ARTIFACT"
    score_hint: str | None = None
    notes: list[str] = field(default_factory=list)


LANES: list[LaneSpec] = [
    LaneSpec(
        lane_id="longform-chain-integrity",
        domain="durable context / audit integrity",
        command="python scripts/benchmark/longform_chain_integrity.py",
        latest_json="artifacts/benchmarks/longform_chain_integrity_latest.json",
        claim_boundary="custom SCBE chain-integrity benchmark; not a public leaderboard score",
        target="multi-session agent memory durability",
        run_in_quick=True,
    ),
    LaneSpec(
        lane_id="longform-cli",
        domain="durable CLI workflows",
        command="python scripts/benchmark/longform_cli_benchmark.py",
        latest_json="artifacts/benchmarks/longform_cli_benchmark_latest.json",
        claim_boundary="local CLI fixture for Longform Bridge commands",
        target="session-resume and landing command usability",
    ),
    LaneSpec(
        lane_id="arc-style-grid",
        domain="abstract grid reasoning",
        command="python scripts/benchmark/arc_style_grid_benchmark.py",
        latest_json="artifacts/benchmarks/arc_style_grid/latest_report.json",
        claim_boundary="synthetic ARC-style local pretest; not official ARC-AGI-2",
        target="ARC-AGI / abstract grid tasks",
    ),
    LaneSpec(
        lane_id="arc-agi2-local",
        domain="abstract grid readiness",
        command="python scripts/benchmark/arc_agi2_local_benchmark.py",
        latest_json="artifacts/benchmarks/arc_agi2_local/latest_report.json",
        claim_boundary="local ARC-AGI-2 harness readiness/baseline floor; not official ARC Prize submission",
        target="ARC-AGI-2",
    ),
    LaneSpec(
        lane_id="neurogolf-blind-submission",
        domain="blind grid solving",
        command="python scripts/benchmark/neurogolf_blind_submission.py",
        latest_json="artifacts/benchmarks/neurogolf_blind_submission/latest_report.json",
        claim_boundary="local blind NeuroGolf submission harness; only claim the emitted local score",
        target="blind Kaggle-style grid tasks",
    ),
    LaneSpec(
        lane_id="real-patch-tasks",
        domain="code repair / patch execution",
        command="python scripts/benchmark/real_patch_task_benchmark.py",
        latest_json="artifacts/benchmarks/real_patch_tasks/latest_report.json",
        claim_boundary="deterministic local patch fixtures; not SWE-bench Verified",
        target="SWE-bench style code repair",
    ),
    LaneSpec(
        lane_id="research-fixtures",
        domain="research QA",
        command="python scripts/benchmark/research_agent_fixture_benchmark.py",
        latest_json="artifacts/benchmarks/research_agent_fixtures/latest_report.json",
        claim_boundary="local BrowseComp/GAIA-style fixtures; not public BrowseComp or GAIA score",
        target="BrowseComp / GAIA",
    ),
    LaneSpec(
        lane_id="rubix-browser",
        domain="browser control / permission geometry",
        command="python scripts/benchmark/rubix_browser_hypercube_benchmark.py",
        latest_json="artifacts/benchmarks/rubix_browser_hypercube/latest_report.json",
        claim_boundary="local browser-control geometry fixture; not WebArena, BrowserGym, OSWorld, or VisualWebArena",
        target="WebArena / BrowserGym / OSWorld",
    ),
    LaneSpec(
        lane_id="hard-agentic-pretest",
        domain="external-suite readiness",
        command="python scripts/benchmark/hard_agentic_benchmark_pretest.py",
        latest_json="artifacts/benchmarks/hard_agentic_pretest/latest_report.json",
        claim_boundary="local readiness/pretest matrix; not a public benchmark leaderboard score",
        target="Terminal-Bench, SWE-bench Verified, WebArena, OSWorld, MLE-bench",
    ),
    LaneSpec(
        lane_id="l13-runtime-fast-path",
        domain="runtime latency",
        command="python scripts/benchmark/l13_runtime_fast_path.py",
        latest_json="artifacts/benchmarks/l13_runtime_fast_path/latest_report.json",
        claim_boundary="local runtime-gate latency measurement; not a hardware-independent public benchmark",
        target="NASA/AF autonomy latency target p95 < 100 ms",
    ),
    LaneSpec(
        lane_id="nasa-usaf-target-matrix",
        domain="autonomy readiness target mapping",
        command="python scripts/benchmark/nasa_usaf_autonomy_target_matrix.py",
        latest_json="artifacts/benchmarks/nasa_usaf_autonomy_target_matrix/latest_report.json",
        claim_boundary="target gap map only; not certification evidence",
        target="NASA Class C / DO-178C style readiness planning",
    ),
]


EXTERNAL_TARGETS: list[dict[str, Any]] = [
    {
        "suite": "SWE-bench Verified",
        "domain": "real GitHub issue repair",
        "status": "BLOCKED_HARNESS",
        "blocker": "Linux/Docker harness requirement on this Windows run surface",
        "missing_link": "run official containerized harness and publish instance-level results",
    },
    {
        "suite": "Terminal-Bench",
        "domain": "terminal task execution",
        "status": "BLOCKED_HARNESS",
        "blocker": "official tb CLI not available through this local package set",
        "missing_link": "install official harness and map SCBE shell protocol to task runner",
    },
    {
        "suite": "WebArena / BrowserGym / VisualWebArena",
        "domain": "browser automation",
        "status": "ADAPTER_TARGET",
        "blocker": "local Rubix Browser fixture exists; official website task adapters still needed",
        "missing_link": "bridge permission-hypercube routes to official browser task APIs",
    },
    {
        "suite": "OSWorld",
        "domain": "desktop control",
        "status": "ADAPTER_TARGET",
        "blocker": "pyautogui/pretest ready, official environment not running here",
        "missing_link": "connect SCBE action receipts to official OSWorld execution loop",
    },
    {
        "suite": "MLE-bench",
        "domain": "Kaggle ML competition tasks",
        "status": "READY_PRETEST",
        "blocker": "requires selected competition data and budgeted runtime per task",
        "missing_link": "wire notebook/data download and score submission loop",
    },
    {
        "suite": "BrowseComp / GAIA",
        "domain": "deep research QA",
        "status": "LOCAL_FIXTURES_READY",
        "blocker": "local fixtures are not official held-out benchmark scoring",
        "missing_link": "run official/public question sets with source receipts and answer verifier",
    },
    {
        "suite": "BFCL",
        "domain": "tool/function calling",
        "status": "ADAPTER_TARGET",
        "blocker": "SCBE tool bus exists; BFCL-compatible adapter not yet emitted",
        "missing_link": "map tools.json schema to BFCL function-call eval format",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"_parse_error": f"invalid JSON in {path}"}


def git_commit() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def run_lane(spec: LaneSpec, timeout_s: int) -> dict[str, Any]:
    args = spec.command.split()
    proc = subprocess.run(
        args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    return {
        "lane_id": spec.lane_id,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-1200:],
        "stderr_tail": proc.stderr[-1200:],
    }


def extract_score(report: dict[str, Any] | None) -> tuple[float | None, str]:
    if not report:
        return None, "no artifact"
    if report.get("_parse_error"):
        return None, report["_parse_error"]

    score = report.get("score")
    if isinstance(score, dict):
        if isinstance(score.get("percent"), (int, float)):
            return float(score["percent"]) / 100.0, f"{score.get('earned', '?')}/{score.get('max', score.get('total', '?'))}"
        if isinstance(score.get("score_percent"), (int, float)):
            return float(score["score_percent"]) / 100.0, "score_percent"
        if isinstance(score.get("score"), (int, float)):
            return float(score["score"]), "score.score"
        if isinstance(score.get("earned"), (int, float)) and isinstance(score.get("max"), (int, float)) and score["max"]:
            return float(score["earned"]) / float(score["max"]), f"{score['earned']}/{score['max']}"

    summary = report.get("summary")
    if isinstance(summary, dict):
        for key in (
            "solve_rate",
            "neurogolf_pass_rate",
            "pass_rate",
            "scbe_pass_rate",
            "hypercube_completion_rate",
        ):
            if isinstance(summary.get(key), (int, float)):
                return float(summary[key]), key
        if summary.get("decision") == "PASS":
            return 1.0, "decision=PASS"
        if summary.get("decision") == "HOLD":
            return None, "decision=HOLD"
        if isinstance(summary.get("ready_or_pass"), (int, float)) and isinstance(summary.get("target_count"), (int, float)):
            total = float(summary["target_count"])
            if total:
                return float(summary["ready_or_pass"]) / total, f"{summary['ready_or_pass']}/{summary['target_count']}"

    if report.get("all_passed") is True:
        return 1.0, "all_passed"
    if report.get("ok") is True:
        return 1.0, "ok=true"
    if report.get("status") == "PASS":
        return 1.0, "status=PASS"
    if isinstance(report.get("validation_ok"), (int, float)) and isinstance(report.get("tasks_total"), (int, float)):
        total = float(report["tasks_total"])
        if total:
            return float(report["validation_ok"]) / total, f"{report['validation_ok']}/{report['tasks_total']}"
    if isinstance(report.get("results"), list) and report["results"]:
        statuses = [str(item.get("current_status", "")).upper() for item in report["results"] if isinstance(item, dict)]
        if statuses:
            pass_like = sum(1 for status in statuses if status in {"PASS", "PARTIAL"})
            return pass_like / len(statuses), f"{pass_like}/{len(statuses)} pass-or-partial"
    return None, "score not found"


def classify_lane(spec: LaneSpec, report: dict[str, Any] | None) -> dict[str, Any]:
    path = REPO_ROOT / spec.latest_json
    score, score_label = extract_score(report)
    status = "ARTIFACT_READY" if report and not report.get("_parse_error") else spec.status_if_missing
    if score is not None:
        if score >= 0.999:
            status = "PASS"
        elif score >= 0.5:
            status = "PARTIAL"
        else:
            status = "LOW_SCORE"
    return {
        "id": spec.lane_id,
        "domain": spec.domain,
        "target": spec.target,
        "command": spec.command,
        "latest_json": spec.latest_json,
        "artifact_exists": path.exists(),
        "status": status,
        "score": round(score, 4) if score is not None else None,
        "score_label": score_label,
        "claim_boundary": spec.claim_boundary,
        "notes": spec.notes,
    }


def build_report(run_local: bool, quick_only: bool, timeout_s: int) -> dict[str, Any]:
    run_results = []
    if run_local:
        for spec in LANES:
            if quick_only and not spec.run_in_quick:
                continue
            run_results.append(run_lane(spec, timeout_s))

    lanes = []
    for spec in LANES:
        report = read_json(REPO_ROOT / spec.latest_json)
        lanes.append(classify_lane(spec, report))

    artifact_ready = sum(1 for lane in lanes if lane["artifact_exists"])
    passed = sum(1 for lane in lanes if lane["status"] == "PASS")
    partial = sum(1 for lane in lanes if lane["status"] == "PARTIAL")
    missing = sum(1 for lane in lanes if not lane["artifact_exists"])
    blocked = sum(1 for target in EXTERNAL_TARGETS if str(target["status"]).startswith("BLOCKED"))

    return {
        "schema_version": "scbe_full_system_benchmark_matrix_v1",
        "generated_at_utc": utc_now(),
        "commit": git_commit(),
        "claim_boundary": [
            "This is an evidence matrix across local SCBE benchmark lanes.",
            "It is not a single official public leaderboard score.",
            "Each lane carries its own claim boundary and latest artifact path.",
        ],
        "summary": {
            "decision": "EVIDENCE_PACKET_READY" if artifact_ready >= 6 else "PARTIAL_EVIDENCE",
            "lanes_total": len(lanes),
            "artifact_ready": artifact_ready,
            "passed": passed,
            "partial": partial,
            "missing_artifacts": missing,
            "external_targets": len(EXTERNAL_TARGETS),
            "blocked_external_targets": blocked,
        },
        "lanes": lanes,
        "external_targets": EXTERNAL_TARGETS,
        "run_results": run_results,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# SCBE Full-System Benchmark Matrix",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Commit: `{report['commit']}`",
        f"- Decision: `{report['summary']['decision']}`",
        "",
        "## Local Evidence Lanes",
        "",
        "| Lane | Domain | Status | Score | Target | Claim Boundary |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for lane in report["lanes"]:
        score = "n/a" if lane["score"] is None else f"{lane['score']:.1%}"
        lines.append(
            "| {id} | {domain} | {status} | {score} | {target} | {claim} |".format(
                id=lane["id"],
                domain=lane["domain"],
                status=lane["status"],
                score=score,
                target=lane["target"],
                claim=lane["claim_boundary"],
            )
        )

    lines.extend(
        [
            "",
            "## External Targets",
            "",
            "| Suite | Domain | Status | Blocker | Missing Link |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for target in report["external_targets"]:
        lines.append(
            "| {suite} | {domain} | {status} | {blocker} | {missing} |".format(
                suite=target["suite"],
                domain=target["domain"],
                status=target["status"],
                blocker=target["blocker"],
                missing=target["missing_link"],
            )
        )

    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "Use this report as a routing and proof packet for what is already executable, what has latest artifacts, and what needs official harness work. Do not describe local fixture scores as public leaderboard results.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print full JSON report")
    parser.add_argument("--run-local", action="store_true", help="run local benchmark lanes before aggregation")
    parser.add_argument("--quick", action="store_true", help="with --run-local, run only quick lanes")
    parser.add_argument("--timeout", type=int, default=120, help="per-lane timeout in seconds")
    parser.add_argument("--out-dir", default=str(OUT_DIR), help="artifact output directory")
    args = parser.parse_args()

    report = build_report(run_local=args.run_local, quick_only=args.quick, timeout_s=args.timeout)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"scbe_full_system_{stamp}.json"
    md_path = out_dir / f"scbe_full_system_{stamp}.md"
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
            "scbe full-system benchmark: "
            f"decision={summary['decision']} "
            f"artifacts={summary['artifact_ready']}/{summary['lanes_total']} "
            f"pass={summary['passed']} partial={summary['partial']} "
            f"blocked_external={summary['blocked_external_targets']}"
        )
        print(f"report={latest_md}")

    return 0 if report["summary"]["artifact_ready"] >= 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
