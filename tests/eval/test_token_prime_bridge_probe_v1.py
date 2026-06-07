from __future__ import annotations

import pytest

from scripts.eval.token_prime_bridge_probe_v1 import run_probe


def test_prime_structure_beats_monotone_index_on_real_gap_bucket_gate() -> None:
    result = run_probe(prime_count=1500, null_runs=40)

    assert result.verdict == "PRIME_STRUCTURE_ADDS_SIGNAL"
    assert result.feature_dim["prime"] == result.feature_dim["monotone"]
    assert result.prime_structure_score.balanced_accuracy > result.prime_shuffled_null.balanced_accuracy_p95
    assert result.delta_prime_minus_monotone > result.null_noise_margin
    assert result.prime_structure_score.balanced_accuracy > result.majority_floor.balanced_accuracy
    assert result.leakage_audit["dims_equal"] is True
    assert result.leakage_audit["target_name_absent_from_prime_features"] is True
    assert result.leakage_audit["monotone_has_no_prime_derived_columns"] is True


def test_prime_bridge_v1_rejects_underpowered_settings() -> None:
    with pytest.raises(ValueError, match="prime_count must be >= 500"):
        run_probe(prime_count=100, null_runs=40)

    with pytest.raises(ValueError, match="null_runs must be >= 40"):
        run_probe(prime_count=1500, null_runs=20)
