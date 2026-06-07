"""Token-prime bridge structure probe (v1).

v0 proved the bridge wiring can recover an injected smooth relation:

    token sidecar -> prime index/log-scale address

Advisor critique, accepted: that does not prove anything prime-specific. A
monotone index address would behave the same. This v1 gate asks the sharper
question:

    Do prime-specific residual fields add signal beyond a monotone index?

Targets:

    monotone_index      - smooth powers/logs of the paired index
    prime_residual      - residues/gaps/factor counts with index/log removed
    monotone_plus_prime - both together

The target is not allowed to include prime_index, log(prime), or any direct
scale coordinate in the prime_residual block.

Run:
    python scripts/eval/token_prime_bridge_structure_probe.py
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.eval.token_prime_bridge_probe import (
    RNG_SEED,
    BridgeMetrics,
    NullMetrics,
    _build_controlled_inventory,
    _evaluate_bridge,
    _first_primes,
    _null_metrics,
    _phase,
    _train_test_split,
)

DEFAULT_SAMPLES = 384
DEFAULT_NULLS = 200


@dataclass(frozen=True)
class StructureProbeResult:
    schema_version: str
    verdict: str
    scope: str
    samples: int
    train_count: int
    test_count: int
    null_runs: int
    monotone_index: BridgeMetrics
    prime_residual: BridgeMetrics
    monotone_plus_prime: BridgeMetrics
    monotone_index_null: NullMetrics
    prime_residual_null: NullMetrics
    monotone_plus_prime_null: NullMetrics
    comparison: dict[str, float | bool | str]
    control_contract: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _divisor_count(n: int) -> int:
    if n < 1:
        return 0
    count = 1
    factor = 2
    while factor * factor <= n:
        exponent = 0
        while n % factor == 0:
            n //= factor
            exponent += 1
        if exponent:
            count *= exponent + 1
        factor += 1 if factor == 2 else 2
    if n > 1:
        count *= 2
    return count


def _small_factor_count(n: int) -> int:
    return sum(1 for prime in (2, 3, 5, 7, 11, 13, 17, 19) if n % prime == 0)


def _prime_residual_features(records: list[dict[str, int]]) -> np.ndarray:
    max_index = max(record["prime_index"] for record in records)
    primes = _first_primes(max_index + 2)
    rows: list[list[float]] = []
    for record in records:
        index = record["prime_index"]
        value = primes[index - 1]
        previous_prime = primes[index - 2]
        next_prime = primes[index]
        log_value = math.log(value)

        gap_prev = (value - previous_prime) / log_value
        gap_next = (next_prime - value) / log_value
        gap_balance = gap_next / max(gap_prev + gap_next, 1e-9)

        features: list[float] = []
        for modulus in (7, 11, 13, 17, 19, 23):
            features.extend(_phase(value, modulus))
        features.extend(
            [
                gap_prev,
                gap_next,
                gap_balance,
                _divisor_count(value - 1) / 64.0,
                _divisor_count(value + 1) / 64.0,
                _small_factor_count(value - 1) / 8.0,
                _small_factor_count(value + 1) / 8.0,
            ]
        )
        rows.append(features)
    return np.asarray(rows, dtype=float)


def _monotone_index_features(records: list[dict[str, int]], width: int) -> np.ndarray:
    max_index = max(record["prime_index"] for record in records)
    rows: list[list[float]] = []
    for record in records:
        index = record["prime_index"]
        x = index / max_index
        features = [
            x,
            x * x,
            x**3,
            x**4,
            math.sqrt(x),
            math.log1p(index) / math.log1p(max_index),
            1.0 / (1.0 + index),
        ]
        power = 5
        while len(features) < width:
            features.append(x**power)
            power += 1
        rows.append(features[:width])
    return np.asarray(rows, dtype=float)


def run_probe(
    samples: int = DEFAULT_SAMPLES,
    null_runs: int = DEFAULT_NULLS,
    train_fraction: float = 0.65,
    seed: int = RNG_SEED,
) -> StructureProbeResult:
    if samples < 160:
        raise ValueError("samples must be >= 160 for the structure probe")
    if null_runs < 40:
        raise ValueError("null_runs must be >= 40")
    if not 0.2 <= train_fraction <= 0.8:
        raise ValueError("train_fraction must be between 0.2 and 0.8")

    token_sidecar, _token_id_only, _prime_address, records = (
        _build_controlled_inventory(samples, seed=seed)
    )
    train_idx, test_idx = _train_test_split(samples, train_fraction, seed=seed + 1)

    prime_residual = _prime_residual_features(records)
    monotone_index = _monotone_index_features(records, width=prime_residual.shape[1])
    monotone_plus_prime = np.hstack([monotone_index, prime_residual])

    monotone_metrics = _evaluate_bridge(
        token_sidecar, monotone_index, train_idx, test_idx
    )
    residual_metrics = _evaluate_bridge(
        token_sidecar, prime_residual, train_idx, test_idx
    )
    combined_metrics = _evaluate_bridge(
        token_sidecar, monotone_plus_prime, train_idx, test_idx
    )

    monotone_null = _null_metrics(
        token_sidecar,
        monotone_index,
        train_idx,
        test_idx,
        monotone_metrics.top1,
        null_runs,
        seed + 20,
    )
    residual_null = _null_metrics(
        token_sidecar,
        prime_residual,
        train_idx,
        test_idx,
        residual_metrics.top1,
        null_runs,
        seed + 21,
    )
    combined_null = _null_metrics(
        token_sidecar,
        monotone_plus_prime,
        train_idx,
        test_idx,
        combined_metrics.top1,
        null_runs,
        seed + 22,
    )

    prime_residual_clears_null = residual_metrics.top1 > residual_null.top1_p95
    prime_adds_over_monotone = combined_metrics.top1 > monotone_metrics.top1
    if prime_residual_clears_null and prime_adds_over_monotone:
        verdict = "PRIME_STRUCTURE_ADDS_SIGNAL"
    else:
        verdict = "PRIME_STRUCTURE_NOT_SUPPORTED_OVER_MONOTONE_INDEX"

    return StructureProbeResult(
        schema_version="token_prime_bridge_structure_probe_v1",
        verdict=verdict,
        scope=(
            "Controlled synthetic gate: separates monotone index recoverability from prime-specific "
            "residue/gap/factor residuals. Does not test a real tokenizer or LLM."
        ),
        samples=samples,
        train_count=len(train_idx),
        test_count=len(test_idx),
        null_runs=null_runs,
        monotone_index=monotone_metrics,
        prime_residual=residual_metrics,
        monotone_plus_prime=combined_metrics,
        monotone_index_null=monotone_null,
        prime_residual_null=residual_null,
        monotone_plus_prime_null=combined_null,
        comparison={
            "prime_residual_clears_null": prime_residual_clears_null,
            "prime_adds_over_monotone": prime_adds_over_monotone,
            "top1_delta_combined_minus_monotone": round(
                combined_metrics.top1 - monotone_metrics.top1, 12
            ),
            "interpretation": (
                "prime label is decorative at this scale"
                if verdict == "PRIME_STRUCTURE_NOT_SUPPORTED_OVER_MONOTONE_INDEX"
                else "prime residual fields add controlled signal"
            ),
        },
        control_contract={
            "source": "token sidecar coordinates only",
            "monotone_index": "smooth index powers/logs with no prime lookup",
            "prime_residual": "residue/gap/factor fields with index/log coordinates removed",
            "null": "same inventories, shuffled training pairings",
            "pass_condition": "prime_residual clears null AND monotone_plus_prime beats monotone_index",
        },
    )


def _print_summary(result: StructureProbeResult) -> None:
    print(result.verdict)
    print(
        f"samples={result.samples} train={result.train_count} test={result.test_count} nulls={result.null_runs}"
    )
    print(
        "monotone_index: "
        f"top1={result.monotone_index.top1:.3f} "
        f"top5={result.monotone_index.top5:.3f} "
        f"null95={result.monotone_index_null.top1_p95:.3f}"
    )
    print(
        "prime_residual: "
        f"top1={result.prime_residual.top1:.3f} "
        f"top5={result.prime_residual.top5:.3f} "
        f"null95={result.prime_residual_null.top1_p95:.3f} "
        f"p={result.prime_residual_null.p_value:.4f}"
    )
    print(
        "monotone_plus_prime: "
        f"top1={result.monotone_plus_prime.top1:.3f} "
        f"top5={result.monotone_plus_prime.top5:.3f} "
        f"null95={result.monotone_plus_prime_null.top1_p95:.3f}"
    )
    print(
        "delta combined-monotone: "
        f"{result.comparison['top1_delta_combined_minus_monotone']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--null-runs", type=int, default=DEFAULT_NULLS)
    parser.add_argument("--train-fraction", type=float, default=0.65)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=Path("artifacts/eval/token_prime_bridge_structure_probe_v1.json"),
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
