from __future__ import annotations

import pytest

from scripts.eval.residue_dynamo_escape_probe import run_probe, score_number


def test_escape_corridor_separates_primes_from_composite_wells() -> None:
    result, _scores = run_probe(limit=600, band_count=8, null_runs=40, seed=173)

    assert result.verdict == "ESCAPE_CORRIDOR_SEPARATES_PRIMES"
    assert (
        result.mean_scores["composites"]["raw_dynamo_score"]
        > result.mean_scores["primes"]["raw_dynamo_score"]
    )
    assert (
        result.mean_scores["primes"]["escape_score"]
        > result.mean_scores["composites"]["escape_score"]
    )
    assert result.composite_coherence_auc.beats_null95 is True
    assert result.prime_escape_auc.beats_null95 is True


def test_bridge_lane_is_reported_separately_and_does_not_inherit_prime_signal() -> None:
    result, _scores = run_probe(limit=600, band_count=8, null_runs=40, seed=173)

    assert result.bridge.count > 0
    assert result.bridge.current_escape_large_gap_auc.beats_null95 is False
    assert result.bridge.current_coherence_large_gap_auc.beats_null95 is False


def test_band_prime_is_not_counted_as_composite_collision() -> None:
    score = score_number(7, [2, 3, 5, 7], is_prime=True)

    assert score.hit_count == 0
    assert score.nonzero_fraction == 1.0
    assert score.escape_score > score.composite_coherence


def test_probe_rejects_underpowered_settings() -> None:
    with pytest.raises(ValueError, match="limit must be >= 100"):
        run_probe(limit=50)

    with pytest.raises(ValueError, match="band_count must be >= 4"):
        run_probe(band_count=3)

    with pytest.raises(ValueError, match="null_runs must be >= 40"):
        run_probe(null_runs=10)
