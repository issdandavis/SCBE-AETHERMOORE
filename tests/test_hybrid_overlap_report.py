from benchmarks.scbe.reports.hybrid_overlap import (
    hybrid_union_bucket,
    overlap_key,
    summarize_lane,
)


def test_overlap_key_tracks_component_subsets() -> None:
    assert overlap_key(False, False, False) == "none"
    assert overlap_key(True, False, False) == "classifier"
    assert overlap_key(False, True, True) == "gate+trichromatic"
    assert overlap_key(True, True, True) == "classifier+gate+trichromatic"


def test_hybrid_union_bucket_labels_disagreements() -> None:
    assert hybrid_union_bucket(True, True) == "both_detect"
    assert hybrid_union_bucket(True, False) == "union_only"
    assert hybrid_union_bucket(False, True) == "hybrid_only"
    assert hybrid_union_bucket(False, False) == "neither"


def test_summarize_lane_counts_per_category() -> None:
    summary = summarize_lane(
        [
            {"class": "a", "detected": True},
            {"class": "a", "detected": False},
            {"class": "b", "detected": True},
        ]
    )
    assert summary["total"] == 3
    assert summary["detected"] == 2
    assert summary["per_category"]["a"]["detected"] == 1
    assert summary["per_category"]["a"]["total"] == 2
    assert summary["per_category"]["b"]["rate"] == 1.0
