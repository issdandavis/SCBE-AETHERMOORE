from __future__ import annotations

from src.spiralverse.semantic_atomic_braid import (
    evaluate_semantic_atomic_braid,
    sample_ops_for_tongue,
)


def test_sample_ops_for_tongue_returns_requested_count() -> None:
    ops = sample_ops_for_tongue("ko", count=3)
    assert len(ops) == 3
    assert all(isinstance(op, str) and op for op in ops)


def test_aligned_braid_scores_above_mismatched_lane() -> None:
    payload = b"conlang braid packet"
    aligned_ops = sample_ops_for_tongue("ko", count=4)
    mismatched_ops = sample_ops_for_tongue("av", count=4)

    aligned = evaluate_semantic_atomic_braid(payload, semantic_tongue="ko", op_tongue="ko", ops=aligned_ops)
    mismatched = evaluate_semantic_atomic_braid(payload, semantic_tongue="ko", op_tongue="av", ops=mismatched_ops)

    assert aligned.roundtrip_ok
    assert mismatched.roundtrip_ok
    assert aligned.semantic_alignment == 1.0
    assert mismatched.semantic_alignment == 0.0
    assert aligned.atomic_home_alignment == 1.0
    assert aligned.overall_score > mismatched.overall_score


def test_misaligned_phi_underlay_reduces_score() -> None:
    payload = b"phi underlay check"
    ko_report = evaluate_semantic_atomic_braid(payload, semantic_tongue="ko", op_tongue="ko")
    dr_report = evaluate_semantic_atomic_braid(payload, semantic_tongue="ko", op_tongue="dr")

    assert ko_report.phi_underlay_alignment > dr_report.phi_underlay_alignment
    assert ko_report.overall_score > dr_report.overall_score
