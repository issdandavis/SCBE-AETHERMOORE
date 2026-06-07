from scripts.research.audit_prime_anchor_count_proxy import PeakConfig
from scripts.research.audit_prime_anchor_replacement import (
    ClusterSet,
    fixed_swap,
    joint_score_select,
    oracle_swap_capacity,
    selected_metrics,
)


def _row(scan_idx: int, future_anchor: bool, anchor: int | None) -> dict:
    return {
        "scan_idx": scan_idx,
        "scan_prime": scan_idx * 10 + 1,
        "future_anchor": future_anchor,
        "first_anchor_idx": anchor,
        "first_anchor_prime": anchor,
        "lead_steps": 1 if future_anchor else None,
    }


def test_selected_metrics_counts_bijection_terms() -> None:
    rows = [
        _row(1, True, 100),
        _row(2, True, 100),
        _row(3, False, None),
        _row(4, True, 200),
    ]

    metrics = selected_metrics(rows, [0, 1, 2])

    assert metrics["predicted_clusters"] == 3
    assert metrics["actual_unique_anchors"] == 2
    assert metrics["unique_anchor_hits"] == 1
    assert metrics["duplicate_clusters"] == 1
    assert metrics["false_clusters"] == 1
    assert metrics["missed_anchors"] == 1


def test_fixed_swap_preserves_density_budget_and_inserts_rr_candidate() -> None:
    rows = [
        _row(1, False, None),
        _row(10, True, 100),
        _row(20, True, 200),
        _row(30, True, 300),
    ]
    density = ClusterSet(PeakConfig("frozen", 0.5, 1), (0, 1), {})
    rr = ClusterSet(PeakConfig("rr_sqrt1", 0.5, 1), (2, 3), {})
    density_scores = [0.1, 0.9, 0.2, 0.3]
    rr_scores = [0.0, 0.1, 0.9, 0.8]

    result = fixed_swap(rows, density, rr, density_scores, rr_scores, swap_fraction=0.5)

    assert result["predicted_clusters"] == 2
    assert result["inserted_count"] == 1
    assert result["unique_anchor_hits"] == 2


def test_joint_score_select_preserves_density_budget() -> None:
    rows = [
        _row(1, False, None),
        _row(10, True, 100),
        _row(20, True, 200),
        _row(30, True, 300),
    ]
    density = ClusterSet(PeakConfig("frozen", 0.5, 1), (0, 1), {})
    rr = ClusterSet(PeakConfig("rr_sqrt1", 0.5, 1), (2, 3), {})
    density_scores = [0.9, 0.8, 0.1, 0.0]
    rr_scores = [0.0, 0.1, 0.9, 1.0]

    result = joint_score_select(rows, density, rr, density_scores, rr_scores, alpha=4.0)

    assert result["predicted_clusters"] == 2
    assert result["unique_anchor_hits"] == 2


def test_oracle_swap_capacity_replaces_known_false_cluster() -> None:
    rows = [
        _row(1, False, None),
        _row(10, True, 100),
        _row(20, True, 200),
    ]
    density = ClusterSet(PeakConfig("frozen", 0.5, 1), (0, 1), {})
    rr = ClusterSet(PeakConfig("rr_sqrt1", 0.5, 1), (2,), {})

    result = oracle_swap_capacity(rows, density, rr)

    assert result["predicted_clusters"] == 2
    assert result["inserted_count"] == 1
    assert result["unique_anchor_hits"] == 2
