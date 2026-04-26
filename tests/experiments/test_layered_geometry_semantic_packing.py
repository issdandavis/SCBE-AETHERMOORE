from __future__ import annotations

from scripts.experiments.layered_geometry_semantic_packing import (
    DEFAULT_FEATURES,
    baseline_token_shape,
    build_benchmark,
    evaluate_shape,
    optimize_token_shape,
    regular_polygon_vertices,
    sat_overlap,
    write_report,
)


def test_sat_overlap_detects_separated_polygons() -> None:
    left = regular_polygon_vertices(4, 0.2, center=(0.0, 0.0))
    right = regular_polygon_vertices(4, 0.2, center=(1.0, 0.0))

    assert sat_overlap(left, left) is True
    assert sat_overlap(left, right) is False


def test_optimized_shape_beats_flat_baseline_for_callable() -> None:
    optimized = evaluate_shape(optimize_token_shape("CALLABLE", 6, DEFAULT_FEATURES["CALLABLE"]))
    baseline = evaluate_shape(baseline_token_shape("CALLABLE", 6, DEFAULT_FEATURES["CALLABLE"]))

    assert optimized.semantic_loss == 0.0
    assert optimized.fit_score > baseline.fit_score
    assert optimized.octave_link_count > 0


def test_benchmark_reports_lift_without_claiming_semantics_as_geometry() -> None:
    report = build_benchmark()

    assert report.passed is True
    assert report.aggregate["fit_score_lift"] > 0
    assert report.aggregate["avg_semantic_loss"] == 0.0
    assert report.source["implementation"].startswith("independent SCBE")
    assert "outer hull identity" in report.source["boundary"]


def test_write_report_outputs_json(tmp_path) -> None:
    output = tmp_path / "layered_geometry.json"
    report = write_report(output)

    assert output.exists()
    assert report.passed is True
    assert "CALLABLE" in output.read_text(encoding="utf-8")
