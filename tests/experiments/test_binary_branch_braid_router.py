from __future__ import annotations

from scripts.experiments.binary_branch_braid_router import (
    DEFAULT_INPUT,
    binary_fingerprint,
    route_family_from_pattern,
    run,
)


def test_binary_fingerprint_is_deterministic() -> None:
    feature = {"a": 0.1, "b": 0.9, "c": -0.4, "d": 0.2}
    keys = ["a", "b", "c", "d"]

    assert binary_fingerprint(feature, keys, bits=4) == binary_fingerprint(feature, keys, bits=4)
    assert len(binary_fingerprint(feature, keys, bits=4)) == 4


def test_route_family_from_pattern_is_deterministic() -> None:
    assert route_family_from_pattern("11110001", "imperative_code") == "imperative_code"
    assert route_family_from_pattern("0000111", "imperative_code") == "symbolic_functional"
    assert route_family_from_pattern("1000001", "imperative_code") == "prose_bridge"
    assert route_family_from_pattern("1000100", "imperative_code") == "prose_bridge"


def test_binary_branch_router_outputs_measured_routes(tmp_path) -> None:
    report = run(DEFAULT_INPUT, tmp_path)

    assert report["version"] == "binary-branch-braid-router-v1"
    assert report["sample_count"] == 84
    assert report["best_feature"] in report["features"]
    for feature_report in report["features"].values():
        assert feature_report["route_count"] == 84
        assert 0.0 <= feature_report["closure_accuracy"] <= 1.0
        assert feature_report["fingerprint_hash"]
    assert (tmp_path / "binary_branch_braid_router.json").exists()
