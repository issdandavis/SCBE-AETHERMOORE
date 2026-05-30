"""Tests for bench_scorer.py normalizer (Lane 10)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.benchmark.bench_scorer import BenchScore, score_report


def _report(schema: str, summary: dict, **kwargs) -> dict:
    return {"schema_version": schema, "summary": summary, **kwargs}


def test_hard_agentic_schema():
    report = _report(
        "scbe_hard_agentic_benchmark_pretest_v1",
        {"target_count": 14, "ready_or_pass": 12, "blocked_or_failed": 2, "decision": "READY"},
        generated_at_utc="2026-05-29T00:00:00Z",
        claim_boundary="local readiness lanes",
    )
    s = score_report(report)
    assert s.lane == "hard-agentic"
    assert s.pass_count == 12
    assert s.total == 14
    assert abs(s.pass_rate - 12 / 14) < 1e-6
    assert s.decision == "READY"
    assert s.boundary == "local readiness lanes"


def test_research_schema():
    report = _report(
        "scbe_research_agent_fixture_benchmark_v1",
        {"total": 10, "passed": 7, "failed": 3, "decision": "PASS"},
        claim_boundary="local BrowseComp-style fixtures",
    )
    s = score_report(report)
    assert s.lane == "research"
    assert s.pass_count == 7
    assert s.pass_rate == 7 / 10


def test_rubix_schema():
    report = _report(
        "scbe_rubix_browser_hypercube_benchmark_v1",
        {"total_paths": 5, "valid_paths": 5, "decision": "PASS"},
    )
    s = score_report(report)
    assert s.lane == "rubix-browser"
    assert s.pass_rate == 1.0


def test_arc_style_grid_schema():
    report = _report(
        "scbe_arc_style_grid_benchmark_v1",
        {"total": 8, "passed": 6, "decision": "PASS"},
    )
    s = score_report(report)
    assert s.lane == "arc-style-grid"
    assert s.pass_count == 6


def test_generic_fallback():
    report = {"schema_version": "unknown_v99", "summary": {"total": 5, "passed": 3}}
    s = score_report(report, artifact_path="/tmp/foo.json")
    assert s.total == 5
    assert s.pass_count == 3
    assert s.artifact_path == "/tmp/foo.json"


def test_zero_total_no_divide():
    report = _report("scbe_research_agent_fixture_benchmark_v1", {"total": 0, "passed": 0, "failed": 0})
    s = score_report(report)
    assert s.pass_rate == 0.0


def test_list_claim_boundary_flattened():
    report = _report(
        "scbe_hard_agentic_benchmark_pretest_v1",
        {"target_count": 2, "ready_or_pass": 2, "blocked_or_failed": 0},
        claim_boundary=["first line", "second line"],
    )
    s = score_report(report)
    assert s.boundary == "first line"


