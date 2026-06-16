"""Canonical import path for the SCBE bijective double-hash map."""

from __future__ import annotations

from .elastic_bijective_hash import (
    BijectiveDoubleHashMap,
    ElasticBijectiveHash,
    encode_key_with_tongue,
    splitmix64,
    splitmix64_inverse,
)

__all__ = [
    "BijectiveDoubleHashMap",
    "ElasticBijectiveHash",
    "encode_key_with_tongue",
    "splitmix64",
    "splitmix64_inverse",
]
