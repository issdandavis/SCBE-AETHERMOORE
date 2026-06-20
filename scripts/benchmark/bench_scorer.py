"""Normalizes any SCBE lane artifact JSON into a standard BenchScore envelope.

Usage:
    python scripts/benchmark/bench_scorer.py artifacts/benchmarks/hard_agentic_pretest/latest_report.json
    python scripts/benchmark/bench_scorer.py artifacts/benchmarks/research_agent_fixtures/latest_report.json --json

Reads any lane's latest_report.json and outputs a unified BenchScore so
tooling and the bench index can compare across heterogeneous schemas.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class BenchScore:
    schema_version: str = "scbe_bench_score_v1"
    lane: str = ""
    pass_count: int = 0
    fail_count: int = 0
    blocked_count: int = 0
    total: int = 0
    pass_rate: float = 0.0
    decision: Optional[str] = None
    generated_at_utc: Optional[str] = None
    latency_ms: Optional[int] = None
    cost_usd: Optional[float] = None
    artifact_path: Optional[str] = None
    boundary: Optional[str] = None
    raw_schema: Optional[str] = None


def _extract_boundary(report: dict[str, Any]) -> Optional[str]:
    cb = report.get("claim_boundary") or report.get("payload", {}).get("claim_boundary")
    if isinstance(cb, list):
        return cb[0] if cb else None
    return cb


def _score_hard_agentic(report: dict[str, Any]) -> BenchScore:
    payload = report.get("payload", report)
    summary = payload.get("summary", {})
    total = summary.get("target_count", 0)
    ready = summary.get("ready_or_pass", 0)
    blocked = summary.get("blocked_or_failed", 0)
    fail = total - ready - blocked
    return BenchScore(
        lane="hard-agentic",
        pass_count=ready,
        fail_count=max(0, fail),
        blocked_count=blocked,
        total=total,
        pass_rate=ready / total if total else 0.0,
        decision=summary.get("decision"),
        generated_at_utc=report.get("generated_at_utc"),
        latency_ms=summary.get("elapsed_ms"),
        boundary=_extract_boundary(report),
        raw_schema=report.get("schema_version"),
    )


def _score_research(report: dict[str, Any]) -> BenchScore:
    summary = report.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    return BenchScore(
        lane="research",
        pass_count=passed,
        fail_count=failed,
        total=total,
        pass_rate=passed / total if total else 0.0,
        decision=summary.get("decision"),
        generated_at_utc=report.get("generated_at_utc"),
        boundary=_extract_boundary(report),
        raw_schema=report.get("schema_version"),
    )


def _score_rubix(report: dict[str, Any]) -> BenchScore:
    summary = report.get("summary", {})
    total = summary.get("total_paths", summary.get("total", 0))
    passed = summary.get("valid_paths", summary.get("passed", 0))
    return BenchScore(
        lane="rubix-browser",
        pass_count=passed,
        fail_count=total - passed,
        total=total,
        pass_rate=passed / total if total else 0.0,
        decision=summary.get("decision"),
        generated_at_utc=report.get("generated_at_utc"),
        boundary=_extract_boundary(report),
        raw_schema=report.get("schema_version"),
    )


def _score_arc(report: dict[str, Any], lane: str) -> BenchScore:
    summary = report.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", summary.get("correct", 0))
    return BenchScore(
        lane=lane,
        pass_count=passed,
        fail_count=total - passed,
        total=total,
        pass_rate=passed / total if total else 0.0,
        decision=summary.get("decision"),
        generated_at_utc=report.get("generated_at_utc"),
        boundary=_extract_boundary(report),
        raw_schema=report.get("schema_version"),
    )


def _score_generic(report: dict[str, Any], lane: str = "") -> BenchScore:
    """Best-effort extraction from an unknown schema."""
    summary = report.get("summary", {})
    total = summary.get("total", summary.get("target_count", 0))
    passed = summary.get("passed", summary.get("pass_count", summary.get("ready_or_pass", 0)))
    failed = summary.get("failed", summary.get("fail_count", total - passed))
    return BenchScore(
        lane=lane,
        pass_count=passed,
        fail_count=failed,
        total=total,
        pass_rate=passed / total if total else 0.0,
        decision=summary.get("decision"),
        generated_at_utc=report.get("generated_at_utc"),
        boundary=_extract_boundary(report),
        raw_schema=report.get("schema_version"),
    )


_SCHEMA_DISPATCH: dict[str, Any] = {
    "scbe_hard_agentic_benchmark_pretest_v1": _score_hard_agentic,
    "scbe_research_agent_fixture_benchmark_v1": _score_research,
    "scbe_rubix_browser_hypercube_benchmark_v1": _score_rubix,
    "scbe_arc_style_grid_benchmark_v1": lambda r: _score_arc(r, "arc-style-grid"),
    "scbe_arc_agi2_local_benchmark_v1": lambda r: _score_arc(r, "arc-agi2"),
    "scbe_swe_local_benchmark_v1": lambda r: _score_generic(r, "swe-local"),
    "scbe_cli_competitive_benchmark_v1": lambda r: _score_generic(r, "cli-competitive"),
}


def score_report(report: dict[str, Any], artifact_path: Optional[str] = None) -> BenchScore:
    """Dispatch to the right scorer based on schema_version."""
    schema = report.get("schema_version", "")
    scorer = _SCHEMA_DISPATCH.get(schema, lambda r: _score_generic(r))
    result = scorer(report)
    if artifact_path:
        result.artifact_path = str(artifact_path)
    return result


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    as_json = "--json" in flags

    if not args:
        print("Usage: bench_scorer.py <latest_report.json> [--json]", file=sys.stderr)
        sys.exit(2)

    path = Path(args[0])
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    report = json.loads(path.read_text(encoding="utf-8"))
    score = score_report(report, artifact_path=str(path))

    if as_json:
        print(json.dumps(asdict(score), indent=2))
    else:
        print(f"lane: {score.lane or '(unknown)'}")
        print(f"pass: {score.pass_count}/{score.total}  rate: {score.pass_rate:.1%}")
        if score.decision:
            print(f"decision: {score.decision}")
        if score.boundary:
            print(f"boundary: {score.boundary}")


if __name__ == "__main__":
    main()
