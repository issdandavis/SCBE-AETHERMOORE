"""Mobius magic operator probe.

This is the constructive version of the "line as a magic operator" idea:

    line/ruler           = log(n)
    operation            = Dirichlet convolution
    inverse piece        = Mobius mu, where 1 * mu = delta
    prime indicator      = Lambda = mu * log

The inverse piece is load-bearing if perturbing it smears Lambda onto
non-prime-powers. The probe reports exact identity errors plus null leakage.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "mobius_magic_operator"


@dataclass(frozen=True)
class MobiusProbeResult:
    limit: int
    inverse_error: float
    lambda_error: float
    forward_log_error: float
    matrix_lambda_error: float
    true_leakage: float
    perturbed_leakage: float
    random_leakage: float
    random_seed: int
    fog_bright_count: int
    fog_hidden_prime_count: int
    fog_bright_precision: float
    fog_prime_recall: float
    fog_prime_power_lit_count: int
    zeta_log_derivative_error: float | None
    verdict: str


def smallest_prime_factor(limit: int) -> list[int]:
    spf = [0] * (limit + 1)
    for value in range(2, limit + 1):
        if spf[value] != 0:
            continue
        for multiple in range(value, limit + 1, value):
            if spf[multiple] == 0:
                spf[multiple] = value
    return spf


def mobius(limit: int) -> tuple[list[int], list[int]]:
    spf = smallest_prime_factor(limit)
    mu = [0] * (limit + 1)
    mu[1] = 1
    for n in range(2, limit + 1):
        x = n
        factor_count = 0
        squarefree = True
        while x > 1:
            prime = spf[x]
            exponent = 0
            while x % prime == 0:
                x //= prime
                exponent += 1
            if exponent > 1:
                squarefree = False
                break
            factor_count += 1
        mu[n] = 0 if not squarefree else (1 if factor_count % 2 == 0 else -1)
    return mu, spf


def von_mangoldt(limit: int, spf: Sequence[int]) -> list[float]:
    values = [0.0] * (limit + 1)
    for n in range(2, limit + 1):
        x = n
        prime = spf[n]
        while x % prime == 0:
            x //= prime
        if x == 1:
            values[n] = math.log(prime)
    return values


def divisors(n: int) -> list[int]:
    values: list[int] = []
    for candidate in range(1, int(math.sqrt(n)) + 1):
        if n % candidate == 0:
            values.append(candidate)
            other = n // candidate
            if other != candidate:
                values.append(other)
    return values


def dirichlet_convolution(
    f: Sequence[float], g: Sequence[float], limit: int
) -> list[float]:
    out = [0.0] * (limit + 1)
    for n in range(1, limit + 1):
        out[n] = sum(f[d] * g[n // d] for d in divisors(n))
    return out


def max_abs_delta(left: Sequence[float], right: Sequence[float]) -> float:
    return max(abs(a - b) for a, b in zip(left, right))


def lambda_matrix_apply(
    mu: Sequence[int], log_values: Sequence[float], limit: int
) -> list[float]:
    """Apply the unit lower-triangular Mobius convolution matrix to log."""
    out = [0.0] * (limit + 1)
    for n in range(1, limit + 1):
        out[n] = sum(mu[n // d] * log_values[d] for d in divisors(n))
    return out


def leakage_to_non_prime_powers(
    values: Sequence[float], lambda_true: Sequence[float]
) -> float:
    return sum(abs(values[n]) for n in range(2, len(values)) if lambda_true[n] == 0.0)


def fog_of_war_metrics(
    lambda_recovered: Sequence[float],
    lambda_true: Sequence[float],
    log_values: Sequence[float],
    tolerance: float = 1e-10,
) -> dict[str, float | int]:
    """Use Lambda/log(n) as a hidden-target search light over the integer line."""
    bright: list[int] = []
    hidden_primes: set[int] = set()
    lit_prime_powers: list[int] = []
    for n in range(2, len(lambda_recovered)):
        if log_values[n] == 0.0:
            continue
        normalized = lambda_recovered[n] / log_values[n]
        is_prime = abs(lambda_true[n] - log_values[n]) <= tolerance
        is_prime_power = lambda_true[n] > tolerance
        if abs(normalized - 1.0) <= tolerance:
            bright.append(n)
        if is_prime:
            hidden_primes.add(n)
        if is_prime_power and abs(lambda_recovered[n]) > tolerance:
            lit_prime_powers.append(n)

    bright_prime_hits = [n for n in bright if n in hidden_primes]
    return {
        "bright_count": len(bright),
        "hidden_prime_count": len(hidden_primes),
        "bright_precision": len(bright_prime_hits) / max(len(bright), 1),
        "prime_recall": len(bright_prime_hits) / max(len(hidden_primes), 1),
        "prime_power_lit_count": len(lit_prime_powers),
    }


def zeta_log_derivative_error(
    limit: int = 20_000, s: complex = 2.0 + 0.7j
) -> float | None:
    try:
        import mpmath as mp
    except Exception:
        return None

    spf = smallest_prime_factor(limit)
    lambda_true = von_mangoldt(limit, spf)
    series = sum(lambda_true[n] * (n ** (-s)) for n in range(2, limit + 1))
    mp.mp.dps = 30
    exact = -mp.zeta(s, derivative=1) / mp.zeta(s)
    return abs(series - complex(exact))


def run_probe(
    limit: int = 240, seed: int = 11, out_dir: Path | None = None
) -> dict[str, object]:
    mu, spf = mobius(limit)
    lambda_true = von_mangoldt(limit, spf)
    one = [0.0] + [1.0] * limit
    log_values = [0.0] + [math.log(n) for n in range(1, limit + 1)]
    delta = [0.0] * (limit + 1)
    delta[1] = 1.0

    inverse_check = dirichlet_convolution(one, [float(value) for value in mu], limit)
    lambda_recovered = dirichlet_convolution(
        [float(value) for value in mu], log_values, limit
    )
    forward_log = dirichlet_convolution(one, lambda_true, limit)
    matrix_lambda = lambda_matrix_apply(mu, log_values, limit)

    rng = random.Random(seed)
    mu_perturbed = [float(value) for value in mu]
    if limit >= 6:
        mu_perturbed[6] += 1.0
    lambda_perturbed = dirichlet_convolution(mu_perturbed, log_values, limit)
    mu_random = [0.0] + [rng.choice((-1.0, 0.0, 1.0)) for _ in range(limit)]
    mu_random[1] = 1.0
    lambda_random = dirichlet_convolution(mu_random, log_values, limit)
    fog = fog_of_war_metrics(lambda_recovered, lambda_true, log_values)

    result = MobiusProbeResult(
        limit=limit,
        inverse_error=max_abs_delta(inverse_check, delta),
        lambda_error=max_abs_delta(lambda_recovered, lambda_true),
        forward_log_error=max_abs_delta(forward_log, log_values),
        matrix_lambda_error=max_abs_delta(matrix_lambda, lambda_true),
        true_leakage=leakage_to_non_prime_powers(lambda_recovered, lambda_true),
        perturbed_leakage=leakage_to_non_prime_powers(lambda_perturbed, lambda_true),
        random_leakage=leakage_to_non_prime_powers(lambda_random, lambda_true),
        random_seed=seed,
        fog_bright_count=int(fog["bright_count"]),
        fog_hidden_prime_count=int(fog["hidden_prime_count"]),
        fog_bright_precision=float(fog["bright_precision"]),
        fog_prime_recall=float(fog["prime_recall"]),
        fog_prime_power_lit_count=int(fog["prime_power_lit_count"]),
        zeta_log_derivative_error=zeta_log_derivative_error(),
        verdict="MOBIUS_OPERATOR_LOAD_BEARING",
    )

    summary: dict[str, object] = {
        "metrics": asdict(result),
        "decision_record": {
            "promotion": "QUARANTINE_RESEARCH_ONLY",
            "verdict": result.verdict,
            "claim_boundary": (
                "Exact arithmetic-function identity on finite support. This is a constructive "
                "operator probe and fog-of-war target light, not a new fast primality test."
            ),
        },
        "sample_lambda": [
            {"n": n, "lambda": lambda_true[n], "recovered": lambda_recovered[n]}
            for n in range(1, min(limit, 40) + 1)
        ],
    }
    if out_dir is not None:
        write_artifacts(summary, out_dir)
    return summary


def write_artifacts(summary: dict[str, object], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=240)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_probe(limit=args.limit, seed=args.seed, out_dir=args.out_dir)
    print(json.dumps(summary["metrics"], indent=2, sort_keys=True))
    print(json.dumps(summary["decision_record"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
