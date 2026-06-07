from __future__ import annotations

from scripts.research.gilbreath_multiface_shape_probe import (
    FACE_NAMES,
    build_vertices,
    difference_triangle,
    leading_one_prefix,
    null_prefix_distribution,
    random_wheel_line,
    run_probe,
    transform_face,
)


def test_abs_difference_triangle_starts_with_gilbreath_prefix() -> None:
    rows = difference_triangle([2, 3, 5, 7, 11, 13], depth=5, mode="abs")

    assert rows[1] == [1.0, 2.0, 2.0, 4.0, 2.0]
    assert leading_one_prefix(rows) >= 3


def test_signed_and_negative_faces_preserve_negative_motion() -> None:
    sequence = [2, 5, 7, 11, 13]
    abs_rows = difference_triangle(sequence, depth=4, mode="abs")
    signed_rows = difference_triangle(sequence, depth=4, mode="signed")
    negative_rows = transform_face(abs_rows, signed_rows, "negative_abs")

    assert any(value < 0 for row in signed_rows for value in row)
    assert negative_rows[1] == [-value for value in abs_rows[1]]


def test_random_wheel_line_preserves_admissible_regions_after_seed() -> None:
    import random

    line = random_wheel_line(length=30, max_value=500, rng=random.Random(2))

    assert line[:3] == [2, 3, 5]
    assert len(line) == 30
    assert all(value % 30 in {1, 7, 11, 13, 17, 19, 23, 29} for value in line[3:])


def test_null_prefix_distribution_returns_trial_counts() -> None:
    prefixes = null_prefix_distribution(
        length=40, max_value=300, depth=20, trials=5, seed=4
    )

    assert len(prefixes) == 5
    assert all(prefix >= 0 for prefix in prefixes)


def test_build_vertices_creates_all_faces() -> None:
    abs_rows = difference_triangle([2, 3, 5, 7, 11, 13], depth=5, mode="abs")
    signed_rows = difference_triangle([2, 3, 5, 7, 11, 13], depth=5, mode="signed")
    face_rows = {
        face: transform_face(abs_rows, signed_rows, face) for face in FACE_NAMES
    }
    vertices = build_vertices(face_rows, max_rows=5)

    assert {vertex.face for vertex in vertices} == set(FACE_NAMES)
    assert all(vertex.z >= 0.0 for vertex in vertices)


def test_run_probe_reports_quarantine_decision() -> None:
    result = run_probe(n_primes=80, depth=30, null_trials=10, seed=6)

    assert result["n_primes"] == 80
    assert result["depth"] == 30
    assert result["decision_record"]["promotion"] == "QUARANTINE_RESEARCH_ONLY"
    assert result["decision_record"]["verdict"] in {
        "GILBREATH_SEAM_SURVIVES_ALL_NULLS",
        "ORDER_SIGNAL_WHEEL_NULL_MATCHES",
        "GILBREATH_SEAM_SURVIVES_WHEEL_NULL",
        "GILBREATH_SEAM_COLLAPSES",
    }
