"""
Tests for the SCBE Full System Bench v1 aggregation harness.

These tests are model-independent and do not depend on any heavyweight
optional dependency. The bench harness itself degrades gracefully when a
lane's local source is missing, so the suite asserts structural and
consistency invariants of the scorecard rather than specific lane scores
(which legitimately vary with the local environment).

Like tests/geoseed/test_orbital_model.py, the import is guarded so the
module skips cleanly rather than erroring if the package is unavailable.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _import():
    """Import the bench harness; skip the suite if it is unavailable."""
    try:
        from src.bench import full_bench  # type: ignore

        return full_bench
    except ImportError as exc:  # pragma: no cover - environment guard
        pytest.skip(f"src.bench.full_bench unavailable: {exc}")


# Expected stable lane keys, in canonical order.
EXPECTED_LANE_KEYS = [
    "cli_ops",
    "repo_repair",
    "cross_language",
    "browser_control",
    "research",
    "kaggle_ml",
    "abstract_reasoning",
    "safety_governance",
    "longform_memory",
    "pathfinding",
]

# External suites that must be flagged as blocked / not-yet-wired.
KNOWN_BLOCKED = {"SWE-bench", "Terminal-Bench", "WebArena"}


@pytest.fixture(scope="module")
def report():
    full_bench = _import()
    return full_bench.run_full_bench()


# ── Schema + structure ────────────────────────────────────────────────────────


def test_schema_version(report):
    assert report["schema_version"] == "scbe_full_bench_v1"


def test_exactly_ten_lanes_with_correct_keys(report):
    lanes = report["lanes"]
    assert isinstance(lanes, list)
    assert len(lanes) == 10
    keys = [lane["lane"] for lane in lanes]
    assert keys == EXPECTED_LANE_KEYS


def test_lane_key_module_constant_matches(report):
    full_bench = _import()
    assert list(full_bench.LANE_KEYS) == EXPECTED_LANE_KEYS


def test_every_lane_has_required_fields(report):
    required = {"lane", "measures", "status", "local_pass_rate", "artifacts", "first_target", "notes"}
    for lane in report["lanes"]:
        assert required.issubset(lane.keys()), f"missing fields in {lane.get('lane')}"


def test_every_lane_has_valid_status(report):
    full_bench = _import()
    for lane in report["lanes"]:
        assert lane["status"] in full_bench.STATUS_VALUES, f"{lane['lane']} has invalid status {lane['status']!r}"


def test_every_lane_has_first_target(report):
    for lane in report["lanes"]:
        assert isinstance(lane["first_target"], str) and lane["first_target"], f"{lane['lane']} missing first_target"


# ── Count consistency ───────────────────────────────────────────────────────


def test_completed_lanes_in_range(report):
    assert 0 <= report["completed_lanes"] <= 10


def test_external_ready_lanes_in_range(report):
    assert 0 <= report["external_ready_lanes"] <= 10
    # Every completed (pass) lane is also external-ready (pass or partial).
    assert report["completed_lanes"] <= report["external_ready_lanes"]


def test_reproducible_artifacts_equals_total_listed(report):
    total = sum(len(lane["artifacts"]) for lane in report["lanes"])
    assert report["reproducible_artifacts"] == total


def test_completed_lanes_matches_pass_count(report):
    pass_count = sum(1 for lane in report["lanes"] if lane["status"] == "pass")
    assert report["completed_lanes"] == pass_count


def test_local_pass_rate_in_unit_interval(report):
    assert 0.0 <= report["local_pass_rate"] <= 1.0
    for lane in report["lanes"]:
        rate = lane["local_pass_rate"]
        if rate is not None:
            assert 0.0 <= rate <= 1.0, f"{lane['lane']} rate out of range: {rate}"


# ── Blocked external suites ───────────────────────────────────────────────────


def test_blocked_external_suites_non_empty_and_known(report):
    suites = report["blocked_external_suites"]
    assert isinstance(suites, list)
    assert len(suites) > 0
    assert KNOWN_BLOCKED.issubset(set(suites)), f"expected {KNOWN_BLOCKED} within {suites}"


# ── Graceful degradation ──────────────────────────────────────────────────────


def test_runs_without_raising_when_sources_absent(monkeypatch, tmp_path):
    """With REPO_ROOT pointed at an empty dir, every lane must degrade
    gracefully (blocked_external / not_implemented / partial) without
    raising, and the scorecard must still be well-formed with 10 lanes."""
    full_bench = _import()
    monkeypatch.setattr(full_bench, "REPO_ROOT", Path(tmp_path))

    degraded = full_bench.run_full_bench()

    assert degraded["schema_version"] == "scbe_full_bench_v1"
    assert len(degraded["lanes"]) == 10
    assert [lane["lane"] for lane in degraded["lanes"]] == EXPECTED_LANE_KEYS
    for lane in degraded["lanes"]:
        assert lane["status"] in full_bench.STATUS_VALUES
    # Artifact count stays internally consistent even when files are missing.
    total = sum(len(lane["artifacts"]) for lane in degraded["lanes"])
    assert degraded["reproducible_artifacts"] == total
    assert 0.0 <= degraded["local_pass_rate"] <= 1.0
    assert len(degraded["blocked_external_suites"]) > 0


def test_run_full_bench_is_idempotent_in_shape(report):
    """A second run yields the same structural shape (keys/lanes/counts fields)."""
    full_bench = _import()
    again = full_bench.run_full_bench()
    assert set(again.keys()) == set(report.keys())
    assert [lane["lane"] for lane in again["lanes"]] == [lane["lane"] for lane in report["lanes"]]
