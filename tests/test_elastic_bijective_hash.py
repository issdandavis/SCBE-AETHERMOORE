"""Tests for the bijective double-hash map compatibility module."""

from __future__ import annotations

import random

from python.scbe.elastic_bijective_hash import (
    MODULE_SCOPE_NOTE,
    BijectiveDoubleHashMap,
    ElasticBijectiveHash,
    benchmark_probe_tails,
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
        h = BijectiveDoubleHashMap(bits=12, seed=1)
        keys = [f"note-{i}" for i in range(3000)]
        for i, k in enumerate(keys):
            h.put(k, i)
        # every value recovered exactly -> bijective round-trip
        assert sorted(v for _, v in h.items()) == list(range(3000))
        assert all(h.get(k) == i for i, k in enumerate(keys))

    def test_mixed_key_types(self) -> None:
        h = BijectiveDoubleHashMap(bits=8)
        h.put(42, "int")
        h.put("str-key", "str")
        h.put(b"bytes-key", "bytes")
        assert h.get(42) == "int"
        assert h.get("str-key") == "str"
        assert h.get(b"bytes-key") == "bytes"
        assert h.get("missing") is None

    def test_update_in_place(self) -> None:
        h = BijectiveDoubleHashMap(bits=8)
        h.put("k", 1)
        h.put("k", 2)
        assert h.get("k") == 2
        assert h.count == 1


class TestDoubleHashHighLoad:
    def test_fits_and_fast_at_99pct(self) -> None:
        bits = 14
        h = BijectiveDoubleHashMap(bits=bits, seed=7)
        n = int(h.size * 0.99)
        keys = [f"k-{i}-{random.getrandbits(32)}" for i in range(n)]
        for i, k in enumerate(keys):
            h.put(k, i)
        assert h.count == n
        # double-hash probe orbit: avg insert probes stay small in this fixture
        assert h.avg_probes() < 15.0
        # still fully recoverable
        assert all(h.get(k) == i for i, k in enumerate(keys))

    def test_contains(self) -> None:
        h = BijectiveDoubleHashMap(bits=8)
        h.put("present")
        assert "present" in h
        assert "absent" not in h

    def test_legacy_alias_still_points_to_canonical_class(self) -> None:
        assert ElasticBijectiveHash is BijectiveDoubleHashMap

    def test_scope_note_rejects_elastic_hashing_claim(self) -> None:
        assert "not the Elastic Hashing construction" in MODULE_SCOPE_NOTE

    def test_probe_tail_benchmark_reports_round_trip_and_tails(self) -> None:
        records = benchmark_probe_tails(bits=10, loads=(0.50, 0.90), seed=123)
        assert [record.load for record in records] == [0.50, 0.90]
        assert all(record.round_trip_ok for record in records)
        assert all(record.max_insert_probes >= record.avg_insert_probes >= 1.0 for record in records)
        assert all(record.max_lookup_probes >= record.avg_lookup_probes >= 1.0 for record in records)

    def test_probe_tail_benchmark_rejects_invalid_loads(self) -> None:
        try:
            benchmark_probe_tails(bits=8, loads=(1.0,))
        except ValueError as exc:
            assert "between 0 and 1" in str(exc)
        else:
            raise AssertionError("invalid load was accepted")
