from scripts.research.run_prime_search_engine_bench import (
    NEG_INF,
    add_tie_break,
    metrics_for_scores,
    split_ordered_rows,
)


def test_metrics_excludes_negative_infinity_rows_from_top_list() -> None:
    rows = [
        {"scan_idx": 1, "scan_ratio": 0.1, "future_anchor": True, "lead_steps": 1, "region_kind": "a"},
        {"scan_idx": 2, "scan_ratio": 0.2, "future_anchor": False, "lead_steps": None, "region_kind": "b"},
        {"scan_idx": 3, "scan_ratio": 0.3, "future_anchor": True, "lead_steps": 2, "region_kind": "c"},
    ]
    scores = {id(rows[0]): NEG_INF, id(rows[1]): 2.0, id(rows[2]): 1.0}

    metrics = metrics_for_scores(rows, scores, top_n=3)

    assert metrics["top_n"] == 2
    assert metrics["top_hits"] == 1
    assert [row["scan_idx"] for row in metrics["top_rows"]] == [2, 3]


def test_tie_break_preserves_exclusions() -> None:
    ranked = add_tie_break([1.0, 1.0, NEG_INF], [0.0, 5.0, 99.0])

    assert ranked[1] > ranked[0]
    assert ranked[2] == NEG_INF


def test_split_ordered_rows_uses_scan_index_order() -> None:
    rows = [{"scan_idx": 30}, {"scan_idx": 10}, {"scan_idx": 20}, {"scan_idx": 40}]

    fit_rows, select_rows = split_ordered_rows(rows, fit_fraction=0.5)

    assert [row["scan_idx"] for row in fit_rows] == [10, 20]
    assert [row["scan_idx"] for row in select_rows] == [30, 40]
