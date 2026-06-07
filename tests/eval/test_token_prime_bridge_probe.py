from __future__ import annotations

import pytest

from scripts.eval.token_prime_bridge_probe import run_probe


def test_token_prime_bridge_recovers_controlled_sidecar_relation() -> None:
    result = run_probe(samples=160, null_runs=40)

    assert result.verdict == "CONTROLLED_BRIDGE_RECOVERS_SIDECAR_RELATION"
    assert result.token_to_prime_sidecar.top1 > result.token_to_prime_null.top1_p95
    assert result.prime_to_token_sidecar.top1 > result.prime_to_token_null.top1_p95
    assert result.token_to_prime_id_only.top1 <= result.token_to_prime_null.top1_p95
    assert result.token_to_prime_sidecar.top5 > 0.70


def test_token_prime_bridge_rejects_underpowered_probe() -> None:
    with pytest.raises(ValueError, match="samples must be >= 80"):
        run_probe(samples=40, null_runs=40)

    with pytest.raises(ValueError, match="null_runs must be >= 20"):
        run_probe(samples=120, null_runs=5)
