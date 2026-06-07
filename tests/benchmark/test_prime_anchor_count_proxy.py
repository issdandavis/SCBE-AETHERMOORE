from scripts.research.audit_prime_anchor_count_proxy import (
    PeakConfig,
    circular_residue_distance,
    evaluate_clusters,
    local_peak_indices,
    non_max_suppress_by_scan_gap,
    percentile_cutoff,
    rr_sqrt1_exact_score,
    rr_sqrt1_near_score,
    sqrt1_residues,
)


def test_local_peak_indices_respects_cutoff_and_neighbors() -> None:
    rows = [{"scan_idx": index} for index in range(5)]
    scores = [0.0, 2.0, 1.0, 3.0, 0.0]

    peaks = local_peak_indices(rows, scores, cutoff=1.5)

    assert peaks == [1, 3]


def test_non_max_suppress_by_scan_gap_keeps_stronger_nearby_peak() -> None:
    rows = [{"scan_idx": 10}, {"scan_idx": 14}, {"scan_idx": 30}]
    scores = [1.0, 3.0, 2.0]

    selected = non_max_suppress_by_scan_gap(rows, scores, [0, 1, 2], radius=6)

    assert selected == [1, 2]


def test_evaluate_clusters_counts_false_missed_and_duplicate_terms() -> None:
    rows = [
        {
            "scan_idx": 1,
            "scan_prime": 11,
            "future_anchor": True,
            "first_anchor_idx": 100,
            "first_anchor_prime": 101,
            "lead_steps": 4,
        },
        {
            "scan_idx": 2,
            "scan_prime": 13,
            "future_anchor": False,
            "first_anchor_idx": None,
            "first_anchor_prime": None,
            "lead_steps": None,
        },
        {
            "scan_idx": 3,
            "scan_prime": 17,
            "future_anchor": True,
            "first_anchor_idx": 100,
            "first_anchor_prime": 101,
            "lead_steps": 2,
        },
        {
            "scan_idx": 4,
            "scan_prime": 19,
            "future_anchor": False,
            "first_anchor_idx": None,
            "first_anchor_prime": None,
            "lead_steps": None,
        },
        {
            "scan_idx": 10,
            "scan_prime": 31,
            "future_anchor": False,
            "first_anchor_idx": None,
            "first_anchor_prime": None,
            "lead_steps": None,
        },
        {
            "scan_idx": 11,
            "scan_prime": 37,
            "future_anchor": False,
            "first_anchor_idx": None,
            "first_anchor_prime": None,
            "lead_steps": None,
        },
        {
            "scan_idx": 20,
            "scan_prime": 71,
            "future_anchor": True,
            "first_anchor_idx": 200,
            "first_anchor_prime": 211,
            "lead_steps": 1,
        },
    ]
    scores = [4.0, 0.0, 3.0, 0.0, 2.0, 0.0, 1.0]

    result = evaluate_clusters(rows, scores, PeakConfig("frozen", percentile=0.0, radius=1))

    assert result["predicted_clusters"] == 4
    assert result["actual_unique_anchors"] == 2
    assert result["unique_anchor_hits"] == 2
    assert result["false_clusters"] == 1
    assert result["duplicate_clusters"] == 1
    assert result["missed_anchors"] == 0
    assert result["count_error"] == 2


def test_percentile_cutoff_uses_upper_rank() -> None:
    assert percentile_cutoff([1.0, 2.0, 3.0, 4.0], 0.75) == 3.0


def test_sqrt1_residues_match_crt_boundary_count() -> None:
    residues = sqrt1_residues((3, 5, 7))

    assert len(residues) == 8
    assert all((residue * residue) % (3 * 5 * 7) == 1 for residue in residues)


def test_circular_residue_distance_wraps_modulus() -> None:
    assert circular_residue_distance(0, (1, 34, 76), 105) == 1


def test_rr_sqrt1_exact_scores_boundary_alignment() -> None:
    assert rr_sqrt1_exact_score(29) > rr_sqrt1_exact_score(23)


def test_rr_sqrt1_near_scores_are_bounded() -> None:
    score = rr_sqrt1_near_score(101)

    assert 0.0 <= score <= 1.0
