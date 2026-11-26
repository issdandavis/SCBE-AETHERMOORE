"""Canonical import path for the SCBE bijective double-hash map."""

from __future__ import annotations

from .elastic_bijective_hash import (
    BijectiveDoubleHashMap,
    ElasticBijectiveHash,
    ProbeTailRecord,
    benchmark_probe_tails,
    encode_key_with_tongue,
    splitmix64,
    splitmix64_inverse,
)

__all__ = [
    "BijectiveDoubleHashMap",
    "ElasticBijectiveHash",
    "ProbeTailRecord",
    "benchmark_probe_tails",
    "encode_key_with_tongue",
    "splitmix64",
    "splitmix64_inverse",
]
