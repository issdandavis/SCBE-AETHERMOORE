"""Tests for elastic_probe_bench -- the probe-length distribution (tail, not just mean) of the hash map.

Pins: the run is deterministic (seeded); every key is found (lookup_probe_lengths asserts it internally);
the TAIL is real (max >> mean) and grows with load while p50 stays small -- the honest point that the
average reported by _bench_at hides the worst case.
"""

from __future__ import annotations

from python.helm.elastic_probe_bench import compare, distribution, lookup_probe_lengths, run


def test_is_deterministic_same_seed_same_distribution():
    assert run(bits=12, loads=(0.9,), seed=3) == run(bits=12, loads=(0.9,), seed=3)


def test_every_inserted_key_is_found():
    # lookup_probe_lengths asserts get(k)==i internally; a returned list of the right length means all found
    lengths = lookup_probe_lengths(bits=12, load=0.95, seed=7)
    assert len(lengths) == int((1 << 12) * 0.95)
    assert all(x >= 1 for x in lengths)  # a successful lookup probes at least once


def test_tail_exceeds_mean_and_grows_with_load():
    lo = distribution(bits=14, load=0.5, seed=7)
    hi = distribution(bits=14, load=0.999, seed=7)
    assert hi["max"] > hi["mean"] * 5  # the worst case is far above the average at high load
    assert hi["max"] > lo["max"] * 5  # ...and the tail grows sharply with load
    assert hi["tail_over_mean"] > 10.0  # max is many multiples of the mean


def test_p50_stays_small_even_at_high_load():
    # the honest shape: most lookups are cheap (p50 ~1-2) even when the tail is catastrophic
    hi = distribution(bits=14, load=0.99, seed=7)
    assert hi["p50"] <= 3
    assert hi["p99"] > hi["p50"]  # the distribution is heavy-tailed, not flat


def test_double_hashing_tames_the_tail_vs_linear_probing():
    # the comparative "why double-hashing" claim: at high load the linear-probe baseline's primary clustering
    # makes its tail MUCH worse than the coprime-stride double-hash map's, at the same load.
    c = compare(bits=14, loads=(0.99,), seed=7)
    row = c["rows"][0]
    assert row["linear_probe"]["max"] > row["double_hash"]["max"] * 2  # linear tail far heavier
    assert row["linear_probe"]["mean"] > row["double_hash"]["mean"]  # ...and a worse average too
    assert row["linear_tail_penalty"] > 2.0  # reported as a multiple


def test_run_structure():
    s = run(bits=12, loads=(0.5, 0.9), seed=1)
    assert s["bits"] == 12 and len(s["rows"]) == 2
    assert set(s["rows"][0]) == {"load", "keys", "mean", "p50", "p90", "p99", "p999", "max", "tail_over_mean"}
