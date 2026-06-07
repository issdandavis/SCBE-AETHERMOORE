from __future__ import annotations

import pytest

from scripts.eval.token_prime_bridge_probe_v2_residual import run_probe


def test_wheel_admissibility_explains_v1_prime_signal_under_residual_gate() -> None:
    result = run_probe(prime_count=1500, null_runs=40)

    assert result.verdict == "WHEEL_ADMISSIBILITY_EXPLAINS_SIGNAL"
    assert result.feature_dim["monotone_index"] == result.feature_dim["wheel_admissibility"]
    assert result.feature_dim["wheel_admissibility"] == result.feature_dim["full_residual"]
    assert result.wheel_admissibility_score.balanced_accuracy > result.monotone_index_score.balanced_accuracy
    assert result.full_residual_score.balanced_accuracy > result.full_shuffled_null.balanced_accuracy_p95
    assert result.delta_full_minus_wheel <= result.paired_delta_null.delta_p95
    assert result.leakage_audit["dims_equal"] is True
    assert result.leakage_audit["target_name_absent_from_full_features"] is True
    assert result.leakage_audit["wheel_baseline_has_no_residual_columns"] is True


def test_prime_bridge_v2_residual_rejects_underpowered_settings() -> None:
    with pytest.raises(ValueError, match="prime_count must be >= 500"):
        run_probe(prime_count=100, null_runs=40)

    with pytest.raises(ValueError, match="null_runs must be >= 40"):
        run_probe(prime_count=1500, null_runs=20)
