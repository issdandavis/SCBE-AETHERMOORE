#!/usr/bin/env python3
"""Benchmark and leaderboard harness for tenreary run artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GLOB = "artifacts/tenreary/*/tenreary-run-*.json"
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "tenreary" / "benchmarks"
MONEY_KEYWORDS = {
    "shopify",
    "stripe",
    "lead",
    "outreach",
    "checkout",
    "conversion",
    "pricing",
    "offer",
    "revenue",
    "sales",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _is_success_status(status: str) -> bool:
    return status in {"ok", "skipped"}


def _latency_bucket_score(avg_step_elapsed_ms: float) -> float:
    if avg_step_elapsed_ms <= 1500:
        return 100.0
    if avg_step_elapsed_ms <= 3000:
        return 80.0
    if avg_step_elapsed_ms <= 6000:
        return 60.0
    if avg_step_elapsed_ms <= 10000:
        return 40.0
    return 20.0


def _analysis_keyword_hits(analysis_payload: Dict[str, Any]) -> int:
    analysis = analysis_payload.get("analysis", {})
    counts = analysis.get("keyword_counts", {})
    if not isinstance(counts, dict):
        return 0
    hits = 0
    for key, value in counts.items():
        if str(key).lower() in MONEY_KEYWORDS and _safe_float(value, 0.0) > 0:
            hits += 1
    return hits


def _step_has_required_fields(step: Dict[str, Any]) -> bool:
    required = ("id", "type", "status", "started_at", "elapsed_ms")
    return all(field in step for field in required)


@dataclass
class RunScore:
    artifact_path: str
    tenreary_name: str
    ok: bool
    steps_total: int
    steps_ok: int
    steps_failed: int
    reliability_score: float
    governance_score: float
    latency_score: float
    cash_signal_score: float
    dual_lane_success_rate: float
    overall_score: float
    elite_ready: bool
    truth_assessment: str
    total_elapsed_ms: float
    avg_step_elapsed_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_path": self.artifact_path,
            "tenreary_name": self.tenreary_name,
            "ok": self.ok,
            "steps_total": self.steps_total,
            "steps_ok": self.steps_ok,
            "steps_failed": self.steps_failed,
            "reliability_score": round(self.reliability_score, 2),
            "governance_score": round(self.governance_score, 2),
            "latency_score": round(self.latency_score, 2),
            "cash_signal_score": round(self.cash_signal_score, 2),
            "dual_lane_success_rate": round(self.dual_lane_success_rate, 2),
            "overall_score": round(self.overall_score, 2),
            "elite_ready": self.elite_ready,
            "truth_assessment": self.truth_assessment,
            "total_elapsed_ms": round(self.total_elapsed_ms, 2),
            "avg_step_elapsed_ms": round(self.avg_step_elapsed_ms, 2),
        }


def _truth_label(*, elite_ready: bool, reliability: float, governance: float, cash: float) -> str:
    if elite_ready:
        return "validated_outperforming_candidate"
    if reliability < 95.0:
        return "good_direction_reliability_gap"
    if governance < 90.0:
        return "good_direction_governance_gap"
    if cash < 70.0:
        return "good_direction_cash_signal_gap"
    return "good_direction_not_yet_validated"


def score_run(payload: Dict[str, Any], artifact_path: str) -> RunScore:
    results = payload.get("results", [])
    steps = [row for row in results if isinstance(row, dict)] if isinstance(results, list) else []

    steps_total = int(payload.get("steps_total", len(steps)))
    if steps_total <= 0:
        steps_total = len(steps)

    success_count = sum(1 for row in steps if _is_success_status(str(row.get("status", "")).lower()))
    error_count = sum(1 for row in steps if str(row.get("status", "")).lower() == "error")

    elapsed_values = [_safe_float(row.get("elapsed_ms"), 0.0) for row in steps]
    total_elapsed = sum(elapsed_values)
    avg_elapsed = total_elapsed / max(len(elapsed_values), 1)

    reliability_score = (success_count / max(steps_total, 1)) * 100.0
    latency_score = _latency_bucket_score(avg_elapsed)

    run_checks = 4
    run_check_passes = 0
    if payload.get("generated_at"):
        run_check_passes += 1
    if isinstance(payload.get("results"), list):
        run_check_passes += 1
    if int(payload.get("steps_total", len(steps))) == len(steps):
        run_check_passes += 1
    if int(payload.get("steps_ok", success_count)) + int(payload.get("steps_failed", error_count)) == len(steps):
        run_check_passes += 1

    step_required = sum(1 for row in steps if _step_has_required_fields(row))
    governance_score = ((run_check_passes + step_required) / max(run_checks + len(steps), 1)) * 100.0

    cash_signal = 0.0
    if "monet" in str(payload.get("tenreary_name", "")).lower() or "revenue" in str(
        payload.get("tenreary_name", "")
    ).lower():
        cash_signal += 10.0

    analysis_steps = [row for row in steps if str(row.get("type", "")).lower() == "analysis.content"]
    if analysis_steps:
        cash_signal += 20.0
        if any(_analysis_keyword_hits(row.get("data", {})) > 0 for row in analysis_steps):
            cash_signal += 20.0

    emit_steps = [row for row in steps if str(row.get("type", "")).lower() == "automation.emit"]
    if emit_steps and any(str(row.get("status", "")).lower() == "ok" for row in emit_steps):
        cash_signal += 25.0
        any_channel_success = False
        for row in emit_steps:
            data = row.get("data", {})
            if not isinstance(data, dict):
                continue
            for channel in data.values():
                if isinstance(channel, dict) and bool(channel.get("success")):
                    any_channel_success = True
                    break
            if any_channel_success:
                break
        if any_channel_success:
            cash_signal += 10.0

    connector_steps = [row for row in steps if str(row.get("type", "")).lower() == "connector.execute"]
    if connector_steps and any(bool(row.get("data", {}).get("success")) for row in connector_steps if isinstance(row.get("data"), dict)):
        cash_signal += 15.0

    cash_signal_score = min(cash_signal, 100.0)

    secondary_steps = [row for row in steps if "secondary" in str(row.get("id", "")).lower()]
    if secondary_steps:
        secondary_ok = sum(1 for row in secondary_steps if _is_success_status(str(row.get("status", "")).lower()))
        dual_lane_success_rate = (secondary_ok / len(secondary_steps)) * 100.0
    else:
        dual_lane_success_rate = 0.0

    overall_score = (
        (0.40 * reliability_score)
        + (0.25 * governance_score)
        + (0.20 * cash_signal_score)
        + (0.15 * latency_score)
    )

    elite_ready = reliability_score >= 95.0 and governance_score >= 90.0 and cash_signal_score >= 70.0 and overall_score >= 85.0
    truth_assessment = _truth_label(
        elite_ready=elite_ready,
        reliability=reliability_score,
        governance=governance_score,
        cash=cash_signal_score,
    )

    return RunScore(
        artifact_path=artifact_path,
        tenreary_name=str(payload.get("tenreary_name", "unknown")),
        ok=bool(payload.get("ok", False)),
        steps_total=steps_total,
        steps_ok=success_count,
        steps_failed=max(steps_total - success_count, 0),
        reliability_score=reliability_score,
        governance_score=governance_score,
        latency_score=latency_score,
        cash_signal_score=cash_signal_score,
        dual_lane_success_rate=dual_lane_success_rate,
        overall_score=overall_score,
        elite_ready=elite_ready,
        truth_assessment=truth_assessment,
        total_elapsed_ms=total_elapsed,
        avg_step_elapsed_ms=avg_elapsed,
    )


def load_runs(paths: Sequence[Path]) -> List[RunScore]:
    scores: List[RunScore] = []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        scores.append(score_run(payload, artifact_path=str(path)))
    return scores


def leaderboard(scores: Sequence[RunScore]) -> List[Dict[str, Any]]:
    ranked = sorted(scores, key=lambda row: row.overall_score, reverse=True)
    return [row.to_dict() for row in ranked]


def build_report(scores: Sequence[RunScore], source_glob: str) -> Dict[str, Any]:
    ranked = leaderboard(scores)
    elite_count = sum(1 for row in ranked if bool(row.get("elite_ready")))
    avg_reliability = sum(float(row.get("reliability_score", 0.0)) for row in ranked) / max(len(ranked), 1)
    avg_overall = sum(float(row.get("overall_score", 0.0)) for row in ranked) / max(len(ranked), 1)
    return {
        "generated_at": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_glob": source_glob,
        "runs_considered": len(ranked),
        "elite_ready_count": elite_count,
        "avg_reliability_score": round(avg_reliability, 2),
        "avg_overall_score": round(avg_overall, 2),
        "leaderboard": ranked,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark tenreary run artifacts and generate leaderboard scores.")
    parser.add_argument("--glob", default=DEFAULT_GLOB, help="Glob pattern for run artifacts.")
    parser.add_argument("--latest", type=int, default=20, help="Use only N most recent artifacts (0 for all).")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR), help="Directory for benchmark report output.")
    parser.add_argument("--json", action="store_true", help="Print full JSON report to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pattern = args.glob.strip() or DEFAULT_GLOB
    files = sorted(REPO_ROOT.glob(pattern), key=lambda p: p.stat().st_mtime)
    if args.latest > 0:
        files = files[-args.latest :]

    scores = load_runs(files)
    report = build_report(scores, source_glob=pattern)

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"tenreary-benchmark-{_stamp()}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        top = report["leaderboard"][0] if report["leaderboard"] else {}
        print(f"[tenreary-benchmark] runs={report['runs_considered']} elite={report['elite_ready_count']}")
        if top:
            print(
                "[tenreary-benchmark] top="
                f"{top.get('tenreary_name')} score={top.get('overall_score')} "
                f"reliability={top.get('reliability_score')}"
            )
        print(f"[tenreary-benchmark] artifact={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
