"""Check whether adjacent integer encodings stay adjacent after ML-KEM's G step.

FIPS 203 K-PKE.KeyGen computes (rho, sigma) = G(d || k), where G is SHA3-512.
This probe samples that exact expansion boundary.  It does not generate ML-KEM
keys and does not estimate ML-KEM security.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random


def hamming(left: bytes, right: bytes) -> int:
    return sum((a ^ b).bit_count() for a, b in zip(left, right, strict=True))


def expand(seed: int, parameter_k: int) -> bytes:
    return hashlib.sha3_512(seed.to_bytes(32, "big") + bytes([parameter_k])).digest()


def scaled_deviation(values: list[int]) -> tuple[int, int]:
    count = len(values)
    total = sum(values)
    return sum((count * value - total) ** 2 for value in values), count**3


def run(pairs: int, parameter_k: int) -> dict[str, object]:
    if pairs < 2:
        raise ValueError("at least two pairs are required")
    if parameter_k not in (2, 3, 4):
        raise ValueError("ML-KEM parameter k must be 2, 3, or 4")

    adjacent = [hamming(expand(seed, parameter_k), expand(seed + 1, parameter_k)) for seed in range(pairs)]
    rng = random.Random(203204)
    random_pairs = []
    for _ in range(pairs):
        left = rng.getrandbits(256)
        right = rng.getrandbits(256)
        while right == left:
            right = rng.getrandbits(256)
        random_pairs.append(hamming(expand(left, parameter_k), expand(right, parameter_k)))

    adjacent_deviation, deviation_denominator = scaled_deviation(adjacent)
    random_deviation, _ = scaled_deviation(random_pairs)
    mean_difference_numerator = sum(adjacent) - sum(random_pairs)
    return {
        "schema": "scbe.mlkem-g-seed-locality-probe.v1",
        "status": "FIPS_203_BOUNDARY_PROBE_NOT_SECURITY_ESTIMATE",
        "operation": "SHA3-512(d || k), corresponding to FIPS 203 K-PKE.KeyGen G expansion",
        "pairs": pairs,
        "parameter_k": parameter_k,
        "output_bits": 512,
        "adjacent_integer_seeds": {
            "mean_hamming": {"numerator": sum(adjacent), "denominator": pairs},
            "minimum": min(adjacent),
            "maximum": max(adjacent),
        },
        "random_seed_pairs": {
            "mean_hamming": {"numerator": sum(random_pairs), "denominator": pairs},
            "minimum": min(random_pairs),
            "maximum": max(random_pairs),
        },
        "adjacent_minus_random_mean": {"numerator": mean_difference_numerator, "denominator": pairs},
        "absolute_effect_exceeds_two_pooled_population_sd": mean_difference_numerator
        * mean_difference_numerator
        * pairs
        > 2 * (adjacent_deviation + random_deviation),
        "exact_variance_accounting": {
            "adjacent_scaled_squared_deviations": adjacent_deviation,
            "random_scaled_squared_deviations": random_deviation,
            "shared_denominator": deviation_denominator,
        },
        "interpretation": (
            "Integer adjacency at the seed input did not imply adjacency " "at this cryptographic expansion boundary."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=int, default=4096)
    parser.add_argument("--parameter-k", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.pairs, args.parameter_k)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
