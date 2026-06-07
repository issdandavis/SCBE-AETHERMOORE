"""Controlled token-prime bridge probe (v0).

Question
--------
Can a token lookup and a prime lookup be connected by a learned bridge if both
sides carry truthful sidecar coordinates?

This is a CONTROLLED positive/negative test, not a language-model capability
claim. We inject a known smooth relationship:

    token sidecar coordinates -> prime index/log-scale address

Then we train a one-layer ridge bridge on part of the pairs and ask whether the
held-out token can retrieve its paired prime from a candidate set. The null
keeps the same token and prime inventories but shuffles the training pairing.

Important boundary:

    raw token_id = dictionary address only
    token sidecar = meaningful occurrence/address coordinates

So the expected result is:

    sidecar bridge beats null
    raw-token-id-only bridge does not

Run:
    python scripts/eval/token_prime_bridge_probe.py
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

RNG_SEED = 20260606
DEFAULT_SAMPLES = 384
DEFAULT_NULLS = 200


@dataclass(frozen=True)
class BridgeMetrics:
    top1: float
    top5: float
    mrr: float
    median_rank: float
    candidate_count: int


@dataclass(frozen=True)
class NullMetrics:
    top1_mean: float
    top1_p95: float
    top1_max: float
    p_value: float
    runs: int


@dataclass(frozen=True)
class BridgeProbeResult:
    schema_version: str
    verdict: str
    scope: str
    samples: int
    train_count: int
    test_count: int
    null_runs: int
    token_to_prime_sidecar: BridgeMetrics
    token_to_prime_id_only: BridgeMetrics
    prime_to_token_sidecar: BridgeMetrics
    token_to_prime_null: NullMetrics
    prime_to_token_null: NullMetrics
    control_contract: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        return data


def _primes_upto(limit: int) -> list[int]:
    if limit < 2:
        return []
    sieve = bytearray([1]) * (limit + 1)
    sieve[0] = sieve[1] = 0
    for factor in range(2, int(limit**0.5) + 1):
        if sieve[factor]:
            sieve[factor * factor :: factor] = bytearray(
                len(sieve[factor * factor :: factor])
            )
    return [n for n in range(limit + 1) if sieve[n]]


def _first_primes(count: int) -> list[int]:
    if count < 1:
        return []
    if count <= 6:
        limit = 20
    else:
        limit = int(count * (math.log(count) + math.log(math.log(count)) + 3))
    while True:
        primes = _primes_upto(limit)
        if len(primes) >= count:
            return primes[:count]
        limit *= 2


def _one_hot(index: int, width: int) -> list[float]:
    values = [0.0] * width
    values[index] = 1.0
    return values


def _phase(value: int, modulus: int) -> tuple[float, float]:
    angle = 2.0 * math.pi * (value % modulus) / modulus
    return math.sin(angle), math.cos(angle)


def _zscore_fit(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = values.mean(axis=0)
    scale = values.std(axis=0)
    scale[scale < 1e-9] = 1.0
    return mean, scale


def _ridge_bridge(
    source: np.ndarray, target: np.ndarray, alpha: float = 1e-2
) -> np.ndarray:
    xtx = source.T @ source + alpha * np.eye(source.shape[1])
    return np.linalg.solve(xtx, source.T @ target)


def _rank_retrieval(predicted: np.ndarray, candidates: np.ndarray) -> BridgeMetrics:
    pred_norm = predicted / (np.linalg.norm(predicted, axis=1, keepdims=True) + 1e-12)
    cand_norm = candidates / (np.linalg.norm(candidates, axis=1, keepdims=True) + 1e-12)
    scores = pred_norm @ cand_norm.T
    ranks: list[int] = []
    for row in range(scores.shape[0]):
        order = np.argsort(-scores[row])
        ranks.append(int(np.where(order == row)[0][0]) + 1)
    rank_arr = np.asarray(ranks, dtype=float)
    return BridgeMetrics(
        top1=float(np.mean(rank_arr == 1)),
        top5=float(np.mean(rank_arr <= 5)),
        mrr=float(np.mean(1.0 / rank_arr)),
        median_rank=float(np.median(rank_arr)),
        candidate_count=int(scores.shape[1]),
    )


def _evaluate_bridge(
    source_all: np.ndarray,
    target_all: np.ndarray,
    train_idx: Sequence[int],
    test_idx: Sequence[int],
    train_target_permutation: np.ndarray | None = None,
) -> BridgeMetrics:
    train_source = source_all[list(train_idx)]
    train_target = target_all[list(train_idx)]
    if train_target_permutation is not None:
        train_target = train_target[train_target_permutation]

    source_mean, source_scale = _zscore_fit(train_source)
    target_mean, target_scale = _zscore_fit(train_target)

    source_train_z = (train_source - source_mean) / source_scale
    target_train_z = (train_target - target_mean) / target_scale
    bridge = _ridge_bridge(source_train_z, target_train_z)

    predicted = ((source_all[list(test_idx)] - source_mean) / source_scale) @ bridge
    candidates = (target_all[list(test_idx)] - target_mean) / target_scale
    return _rank_retrieval(predicted, candidates)


def _build_controlled_inventory(
    samples: int,
    seed: int = RNG_SEED,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, int]]]:
    """Create aligned token-sidecar and prime-address inventories.

    The raw token ids are deliberately randomized so a bridge using only token_id
    has no stable path. The sidecar carries the controlled relationship.
    """
    rng = random.Random(seed)
    sector_count = 8
    role_count = 5
    ring_count = math.ceil(samples / sector_count)

    token_ids = list(range(10_000, 10_000 + samples))
    rng.shuffle(token_ids)

    max_prime_index = 50 + ring_count * 19 + sector_count * 7 + role_count * 3 + 20
    primes = _first_primes(max_prime_index + 5)

    token_sidecars: list[np.ndarray] = []
    token_id_only: list[np.ndarray] = []
    prime_addresses: list[np.ndarray] = []
    records: list[dict[str, int]] = []

    for row in range(samples):
        sector = row % sector_count
        ring = row // sector_count
        role = (sector * 2 + ring) % role_count
        token_id = token_ids[row]

        ring_norm = ring / max(1, ring_count - 1)
        token_features: list[float] = []
        token_features.extend(_one_hot(sector, sector_count))
        token_features.extend(_one_hot(role, role_count))
        token_features.extend([ring_norm, ring_norm * ring_norm])
        for modulus in (5, 7, 11, 13):
            token_features.extend(_phase(ring, modulus))
        token_features.append(((sector * 3 + role * 5 + ring % 9) % 17) / 16.0)

        id_features = [
            token_id / 20_000.0,
            math.sin(token_id),
            math.cos(token_id),
            (token_id % 7) / 6.0,
            (token_id % 11) / 10.0,
        ]

        # Controlled bridge target. This is intentionally based on prime INDEX
        # and log-scale coordinates, not pseudorandom exact prime residues/gaps.
        prime_index = 50 + ring * 19 + sector * 7 + role * 3 + (ring % 5) * 2
        prime_value = primes[prime_index - 1]
        prime_features = [
            math.log(prime_index),
            prime_index / max_prime_index,
            math.log(prime_value),
            sector / max(1, sector_count - 1),
            role / max(1, role_count - 1),
        ]
        for modulus in (5, 7, 11, 13):
            prime_features.extend(_phase(prime_index, modulus))

        token_sidecars.append(np.asarray(token_features, dtype=float))
        token_id_only.append(np.asarray(id_features, dtype=float))
        prime_addresses.append(np.asarray(prime_features, dtype=float))
        records.append(
            {
                "token_id": token_id,
                "sector": sector,
                "role": role,
                "ring": ring,
                "prime_index": prime_index,
                "prime_value": prime_value,
            }
        )

    return (
        np.vstack(token_sidecars),
        np.vstack(token_id_only),
        np.vstack(prime_addresses),
        records,
    )


def _train_test_split(
    samples: int, train_fraction: float, seed: int = RNG_SEED + 1
) -> tuple[list[int], list[int]]:
    rng = random.Random(seed)
    indices = list(range(samples))
    rng.shuffle(indices)
    cut = int(samples * train_fraction)
    return indices[:cut], indices[cut:]


def _null_metrics(
    source_all: np.ndarray,
    target_all: np.ndarray,
    train_idx: Sequence[int],
    test_idx: Sequence[int],
    real_top1: float,
    null_runs: int,
    seed: int,
) -> NullMetrics:
    rng = np.random.default_rng(seed)
    top1_values: list[float] = []
    train_count = len(train_idx)
    for _ in range(null_runs):
        permutation = rng.permutation(train_count)
        top1_values.append(
            _evaluate_bridge(
                source_all,
                target_all,
                train_idx,
                test_idx,
                train_target_permutation=permutation,
            ).top1
        )
    arr = np.asarray(top1_values, dtype=float)
    p_value = (1.0 + float(np.sum(arr >= real_top1))) / (null_runs + 1.0)
    return NullMetrics(
        top1_mean=float(np.mean(arr)),
        top1_p95=float(np.quantile(arr, 0.95)),
        top1_max=float(np.max(arr)),
        p_value=float(p_value),
        runs=null_runs,
    )


def run_probe(
    samples: int = DEFAULT_SAMPLES,
    null_runs: int = DEFAULT_NULLS,
    train_fraction: float = 0.65,
    seed: int = RNG_SEED,
) -> BridgeProbeResult:
    if samples < 80:
        raise ValueError("samples must be >= 80 for a stable held-out retrieval probe")
    if null_runs < 20:
        raise ValueError("null_runs must be >= 20")
    if not 0.2 <= train_fraction <= 0.8:
        raise ValueError("train_fraction must be between 0.2 and 0.8")

    token_sidecar, token_id_only, prime_address, _records = _build_controlled_inventory(
        samples, seed=seed
    )
    train_idx, test_idx = _train_test_split(samples, train_fraction, seed=seed + 1)

    token_to_prime = _evaluate_bridge(token_sidecar, prime_address, train_idx, test_idx)
    token_id_to_prime = _evaluate_bridge(
        token_id_only, prime_address, train_idx, test_idx
    )
    prime_to_token = _evaluate_bridge(prime_address, token_sidecar, train_idx, test_idx)

    token_to_prime_null = _null_metrics(
        token_sidecar,
        prime_address,
        train_idx,
        test_idx,
        token_to_prime.top1,
        null_runs,
        seed + 2,
    )
    prime_to_token_null = _null_metrics(
        prime_address,
        token_sidecar,
        train_idx,
        test_idx,
        prime_to_token.top1,
        null_runs,
        seed + 3,
    )

    if (
        token_to_prime.top1 > token_to_prime_null.top1_p95
        and prime_to_token.top1 > prime_to_token_null.top1_p95
        and token_id_to_prime.top1 <= token_to_prime_null.top1_p95
    ):
        verdict = "CONTROLLED_BRIDGE_RECOVERS_SIDECAR_RELATION"
    else:
        verdict = "NO_CONTROLLED_BRIDGE_SIGNAL"

    return BridgeProbeResult(
        schema_version="token_prime_bridge_probe_v0",
        verdict=verdict,
        scope=(
            "Controlled synthetic bridge only: proves a sidecar token-prime membrane can carry "
            "a known relation; does not prove real-tokenizer or LLM capability improvement."
        ),
        samples=samples,
        train_count=len(train_idx),
        test_count=len(test_idx),
        null_runs=null_runs,
        token_to_prime_sidecar=token_to_prime,
        token_to_prime_id_only=token_id_to_prime,
        prime_to_token_sidecar=prime_to_token,
        token_to_prime_null=token_to_prime_null,
        prime_to_token_null=prime_to_token_null,
        control_contract={
            "token_id": "dictionary address only; randomized in this probe",
            "token_sidecar": "meaningful controlled occurrence coordinates",
            "prime_address": "prime index/log-scale address coordinates",
            "bridge": "one-layer ridge bridge trained on held-out-safe split",
            "null": "same inventories, shuffled training pairings",
        },
    )


def _print_summary(result: BridgeProbeResult) -> None:
    print(result.verdict)
    print(
        f"samples={result.samples} train={result.train_count} test={result.test_count} nulls={result.null_runs}"
    )
    print(
        "token->prime sidecar: "
        f"top1={result.token_to_prime_sidecar.top1:.3f} "
        f"top5={result.token_to_prime_sidecar.top5:.3f} "
        f"mrr={result.token_to_prime_sidecar.mrr:.3f}"
    )
    print(
        "token->prime id_only: "
        f"top1={result.token_to_prime_id_only.top1:.3f} "
        f"top5={result.token_to_prime_id_only.top5:.3f} "
        f"mrr={result.token_to_prime_id_only.mrr:.3f}"
    )
    print(
        "token->prime null: "
        f"mean={result.token_to_prime_null.top1_mean:.3f} "
        f"p95={result.token_to_prime_null.top1_p95:.3f} "
        f"p={result.token_to_prime_null.p_value:.4f}"
    )
    print(
        "prime->token sidecar: "
        f"top1={result.prime_to_token_sidecar.top1:.3f} "
        f"top5={result.prime_to_token_sidecar.top5:.3f} "
        f"mrr={result.prime_to_token_sidecar.mrr:.3f}"
    )
    print(
        "prime->token null: "
        f"mean={result.prime_to_token_null.top1_mean:.3f} "
        f"p95={result.prime_to_token_null.top1_p95:.3f} "
        f"p={result.prime_to_token_null.p_value:.4f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--null-runs", type=int, default=DEFAULT_NULLS)
    parser.add_argument("--train-fraction", type=float, default=0.65)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=Path("artifacts/eval/token_prime_bridge_probe_v0.json"),
    )
    args = parser.parse_args()

    result = run_probe(
        samples=args.samples,
        null_runs=args.null_runs,
        train_fraction=args.train_fraction,
    )
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )
    _print_summary(result)
    print(f"artifact={args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
