"""Tests for the Elastic Bijective Hash (python/scbe/elastic_bijective_hash.py)."""

from __future__ import annotations

import random

from python.scbe.elastic_bijective_hash import (
    ElasticBijectiveHash,
    splitmix64,
    splitmix64_inverse,
)


class TestSplitmixBijection:
    def test_splitmix_is_reversible(self) -> None:
        for x in [0, 1, 2, (1 << 64) - 1] + [random.getrandbits(64) for _ in range(2000)]:
            assert splitmix64_inverse(splitmix64(x)) == x

    def test_splitmix_distinct(self) -> None:
        outs = {splitmix64(i) for i in range(5000)}
        assert len(outs) == 5000  # injective on a contiguous range


class TestBijectiveRoundTrip:
    def test_lossless_recovery(self) -> None:
        h = ElasticBijectiveHash(bits=12, seed=1)
        keys = [f"note-{i}" for i in range(3000)]
        for i, k in enumerate(keys):
            h.put(k, i)
        # every value recovered exactly -> bijective round-trip
        assert sorted(v for _, v in h.items()) == list(range(3000))
        assert all(h.get(k) == i for i, k in enumerate(keys))

    def test_mixed_key_types(self) -> None:
        h = ElasticBijectiveHash(bits=8)
        h.put(42, "int")
        h.put("str-key", "str")
        h.put(b"bytes-key", "bytes")
        assert h.get(42) == "int"
        assert h.get("str-key") == "str"
        assert h.get(b"bytes-key") == "bytes"
        assert h.get("missing") is None

    def test_update_in_place(self) -> None:
        h = ElasticBijectiveHash(bits=8)
        h.put("k", 1)
        h.put("k", 2)
        assert h.get("k") == 2
        assert h.count == 1


class TestElasticHighLoad:
    def test_fits_and_fast_at_99pct(self) -> None:
        bits = 14
        h = ElasticBijectiveHash(bits=bits, seed=7)
        n = int(h.size * 0.99)
        keys = [f"k-{i}-{random.getrandbits(32)}" for i in range(n)]
        for i, k in enumerate(keys):
            h.put(k, i)
        assert h.count == n
        # double-hash firebreak: avg insert probes stay small even at 99% load
        assert h.avg_probes() < 15.0
        # still fully recoverable
        assert all(h.get(k) == i for i, k in enumerate(keys))

    def test_contains(self) -> None:
        h = ElasticBijectiveHash(bits=8)
        h.put("present")
        assert "present" in h
        assert "absent" not in h
