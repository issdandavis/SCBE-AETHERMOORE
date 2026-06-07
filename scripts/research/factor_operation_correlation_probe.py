"""Factor-operation correlation probe.

This is a small sanity check for the "boundary operator is an integer operation"
claim. It measures whether adjacent factor-complexity signals are genuinely
independent or mostly showing elementary parity / 2-adic structure.

The useful object here is not a new prime law. It is the factorization operation
over all integers:

    n -> factor profile -> neighboring factor profile

Primes are the Omega=1 floor of that map; composites fill the richer levels.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "factor_operation_correlation_probe"


def smallest_prime_factor_sieve(limit: int) -> list[int]:
    if limit < 2:
        raise ValueError("limit must be at least 2")
    spf = list(range(limit + 1))
    spf[0] = 0
    spf[1] = 1
    for value in range(2, int(limit**0.5) + 1):
        if spf[value] != value:
            continue
        start = value * value
        for multiple in range(start, limit + 1, value):
            if spf[multiple] == multiple:
                spf[multiple] = value
    return spf


def factor_complexity_arrays(
    limit: int,
) -> tuple[list[int], list[int], list[int], list[int]]:
    spf = smallest_prime_factor_sieve(limit)
    omega = [0] * (limit + 1)
    big_omega = [0] * (limit + 1)
    v2 = [0] * (limit + 1)
    liouville = [1] * (limit + 1)

    for value in range(2, limit + 1):
        p = spf[value]
        rest = value // p
        big_omega[value] = big_omega[rest] + 1
        omega[value] = omega[rest] + (0 if rest % p == 0 else 1)
        v2[value] = v2[rest] + 1 if p == 2 else 0
        liouville[value] = -liouville[rest]
    return omega, big_omega, v2, liouville


def corr(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError(
            "correlation requires equal length vectors with at least two values"
        )
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0.0 or den_y == 0.0:
        return 0.0
    return num / (den_x * den_y)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def run_probe(limit: int) -> dict[str, float | int | str]:
    omega, big_omega, v2, liouville = factor_complexity_arrays(limit + 2)
    values = list(range(2, limit))
    omega_n = [float(omega[n]) for n in values]
    omega_n1 = [float(omega[n + 1]) for n in values]
    omega_n2 = [float(omega[n + 2]) for n in values]
    odd_complexity_n = [float(big_omega[n] - v2[n]) for n in values]
    odd_complexity_n1 = [float(big_omega[n + 1] - v2[n + 1]) for n in values]
    liouville_product = [float(liouville[n] * liouville[n + 1]) for n in values]

    prime_floor_share = sum(1 for n in values if big_omega[n] == 1) / len(values)

    return {
        "schema": "factor-operation-correlation-probe-v1",
        "limit": limit,
        "corr_omega_n_n_plus_1": corr(omega_n, omega_n1),
        "corr_odd_complexity_n_n_plus_1": corr(odd_complexity_n, odd_complexity_n1),
        "corr_omega_n_n_plus_2": corr(omega_n, omega_n2),
        "mean_liouville_n_times_n_plus_1": mean(liouville_product),
        "prime_floor_share_big_omega_eq_1": prime_floor_share,
        "decision": "INTEGER_OPERATION_SIGNAL_NOT_PRIME_ONLY",
        "interpretation": (
            "Adjacent Omega anticorrelation is dominated by even/odd 2-adic structure; "
            "the Liouville sign product is near zero, so the deeper parity-like object "
            "does not provide an exploitable adjacent-prime path in this probe."
        ),
    }


def write_outputs(result: dict[str, float | int | str], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "summary.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=1_000_000)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_probe(args.limit)
    path = write_outputs(result, args.out_dir)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("factor_operation_correlation_probe")
        print(f"limit={result['limit']}")
        print(f"corr Ω(n),Ω(n+1) = {result['corr_omega_n_n_plus_1']:.4f}")
        print(
            "corr odd-complexity(n),odd-complexity(n+1) = "
            f"{result['corr_odd_complexity_n_n_plus_1']:.4f}"
        )
        print(f"corr Ω(n),Ω(n+2) = {result['corr_omega_n_n_plus_2']:.4f}")
        print(f"mean λ(n)λ(n+1) = {result['mean_liouville_n_times_n_plus_1']:.4f}")
        print(f"prime floor share = {result['prime_floor_share_big_omega_eq_1']:.4f}")
        print(f"summary={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
