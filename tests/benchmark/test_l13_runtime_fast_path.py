from scripts.benchmark.l13_runtime_fast_path import SCHEMA, run_benchmark


def test_l13_runtime_fast_path_p95_under_100ms() -> None:
    report = run_benchmark(iterations=120)

    assert report["schema_version"] == SCHEMA
    assert report["status"] == "PASS"
    assert report["summary"]["p95_ms"] < 100.0


def test_l13_runtime_fast_path_samples_all_guard_lanes() -> None:
    report = run_benchmark(iterations=120)

    assert report["summary"]["lane_counts"] == {
        "destructive_reroute": 30,
        "immune_deny": 30,
        "safe_reflex_allow": 30,
        "secret_reroute": 30,
    }
    assert report["summary"]["decision_counts"]["ALLOW"] >= 30
    assert report["summary"]["decision_counts"]["DENY"] >= 30
    assert report["summary"]["decision_counts"]["REROUTE"] >= 60
    assert report["evidence"]["reflex_hits"] >= 30
    assert report["evidence"]["immune_hits"] >= 30
    assert report["evidence"]["high_confidence_matches"] >= 60
