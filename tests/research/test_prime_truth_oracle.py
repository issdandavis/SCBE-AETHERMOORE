import json
from pathlib import Path

import pytest

from scripts.research.prime_truth_oracle import (
    is_prime_u64,
    next_prime_at_or_after,
    prime_indices_for_values,
    previous_prime_at_or_before,
    prime_stream,
    segmented_primes,
    verify_artifact_anchor_primes,
    verify_artifact_anchor_superprimes,
)


def test_is_prime_u64_known_values():
    primes = [2, 3, 5, 37, 101, 531_983_927, 2_147_483_647]
    composites = [0, 1, 4, 9, 341, 561, 600_000_000, 2_147_483_647 * 3]

    for value in primes:
        assert is_prime_u64(value), value
    for value in composites:
        assert not is_prime_u64(value), value


def test_prime_navigation_helpers():
    assert next_prime_at_or_after(100) == 101
    assert next_prime_at_or_after(101) == 101
    assert previous_prime_at_or_before(100) == 97
    assert previous_prime_at_or_before(2) == 2
    assert previous_prime_at_or_before(1) is None
    assert prime_stream(100, 5) == [101, 103, 107, 109, 113]


def test_segmented_primes_half_open_interval():
    assert segmented_primes(0, 30) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
    assert segmented_primes(100, 114) == [101, 103, 107, 109, 113]
    assert segmented_primes(10, 10) == []


def test_prime_indices_for_values():
    assert prime_indices_for_values([3, 5, 11, 12, 109], segment_size=1024) == {
        3: 2,
        5: 3,
        11: 5,
        109: 29,
    }


def test_verify_artifact_anchor_primes(tmp_path: Path):
    artifact = {
        "hidden_numbers": [
            {"anchor_prime": 101},
            {"anchor_prime": 103},
        ],
        "ip_new_anchors": [107, 109],
        "total_anchors": 999,
    }
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    checks = verify_artifact_anchor_primes(path)

    assert [check.value for check in checks] == [101, 103, 107, 109]
    assert all(check.is_prime for check in checks)


def test_verify_artifact_anchor_superprimes(tmp_path: Path):
    artifact = {
        "hidden_numbers": [
            {"anchor_prime": 3},
            {"anchor_prime": 7},
        ],
        "new_anchors_under_prediction": [11, 12],
    }
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    checks = verify_artifact_anchor_superprimes(path)
    by_value = {check.value: check for check in checks}

    assert by_value[3].is_superprime
    assert by_value[11].is_superprime
    assert not by_value[7].is_superprime
    assert not by_value[12].is_prime
    assert by_value[12].prime_index is None


def test_rejects_out_of_u64():
    with pytest.raises(ValueError):
        is_prime_u64(1 << 64)
