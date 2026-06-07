from __future__ import annotations

import pytest

from scripts.eval.token_prime_bridge_structure_probe import run_probe


def test_prime_structure_does_not_beat_monotone_index_control() -> None:
    result = run_probe(samples=384, null_runs=40)

    assert result.verdict == "PRIME_STRUCTURE_NOT_SUPPORTED_OVER_MONOTONE_INDEX"
    assert result.monotone_index.top1 > result.monotone_index_null.top1_p95
    assert result.prime_residual.top1 <= result.prime_residual_null.top1_p95
    assert result.monotone_plus_prime.top1 < result.monotone_index.top1
    assert result.comparison["prime_adds_over_monotone"] is False


def test_prime_structure_probe_rejects_underpowered_settings() -> None:
    with pytest.raises(ValueError, match="samples must be >= 160"):
        run_probe(samples=80, null_runs=40)

    with pytest.raises(ValueError, match="null_runs must be >= 40"):
        run_probe(samples=384, null_runs=20)
