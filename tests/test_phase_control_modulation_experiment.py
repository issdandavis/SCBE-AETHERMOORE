from pathlib import Path

from src.experimental.phase_control import (
    BASE_PHASES,
    aperiodic_snapshot,
    base_coupling_matrix,
    build_report,
    periodic_snapshot,
)


def test_base_coupling_matrix_is_square_and_symmetric():
    matrix = base_coupling_matrix(BASE_PHASES)
    assert len(matrix) == 6
    for idx, row in enumerate(matrix):
        assert len(row) == 6
        assert row[idx] == 1.0
        for jdx, value in enumerate(row):
            assert value == matrix[jdx][idx]


def test_periodic_snapshot_repeats_at_period():
    first = periodic_snapshot(step=0, period=6)
    repeat = periodic_snapshot(step=6, period=6)
    assert first.matrix == repeat.matrix


def test_aperiodic_snapshot_does_not_repeat_on_period_boundary():
    first = aperiodic_snapshot(step=0)
    later = aperiodic_snapshot(step=6)
    assert first.matrix != later.matrix


def test_build_report_contains_n8n_hint_and_comparison_flags(tmp_path: Path):
    out = build_report(steps=8, period=6)
    assert out["n8n_payload_hint"]["workflow_kind"] == "phase-control-modulation"
    assert out["comparisons"]["periodic_repeats_at_period"] is True
    assert out["comparisons"]["aperiodic_repeats_at_period"] is False
