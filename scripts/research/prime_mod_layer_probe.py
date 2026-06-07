"""Prime modular layer probe.

This is the exact "mod layers" stack:

    integers -> mod 2 gate -> mod 3 gate -> mod 5 gate -> ... -> survivors

Each layer measures how much candidate space remains, how many true primes are
kept, and the decimal/log compression of the search cone. This is not a new
targeting lane; it is the cost/precision map of the classical wheel/sieve
structure.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    from run_prime_calibration_targeting_probe import simple_sieve
except ModuleNotFoundError:  # pragma: no cover - package import path for tests
    from scripts.research.run_prime_calibration_targeting_probe import simple_sieve


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "prime_mod_layer_probe"
DEFAULT_LAYER_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47)


@dataclass(frozen=True)
class ModLayerResult:
    layer: int
    added_prime: int
    modulus: int
    totient: int
    theoretical_survival: float
    range_count: int
    candidate_count: int
    prime_count: int
    candidate_fraction: float
    precision: float
    recall: float
    lift_vs_base_density: float
    candidates_per_prime: float
    compression_digits: float
    marginal_compression_digits: float
    modulo_tests_per_integer: int


def parse_layer_primes(text: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in text.split(",") if part.strip())
    if not values:
        raise ValueError("at least one layer prime is required")
    if sorted(values) != list(values) or len(set(values)) != len(values):
        raise ValueError("layer primes must be sorted and unique")
    known = set(simple_sieve(max(values)))
    missing = [value for value in values if value not in known]
    if missing:
        raise ValueError(f"layer values must be prime, got {missing}")
    return values


def survivors_for_layer(values: range, layer_primes: tuple[int, ...]) -> list[int]:
    return [
        value
        for value in values
        if all(value % prime != 0 or value == prime for prime in layer_primes)
    ]


def run_layers(
    lower: int, upper: int, layer_primes: tuple[int, ...]
) -> list[ModLayerResult]:
    if upper <= lower:
        raise ValueError("upper must be greater than lower")
    if lower < 2:
        raise ValueError("lower must be at least 2")

    values = range(lower, upper)
    range_count = upper - lower
    primes_in_range = [prime for prime in simple_sieve(upper - 1) if prime >= lower]
    prime_set = set(primes_in_range)
    prime_count = len(primes_in_range)
    base_density = prime_count / range_count if range_count else 0.0

    results: list[ModLayerResult] = []
    modulus = 1
    totient = 1
    previous_digits = 0.0
    active_primes: list[int] = []
    for layer, added_prime in enumerate(layer_primes, start=1):
        active_primes.append(added_prime)
        modulus *= added_prime
        totient *= added_prime - 1
        candidates = survivors_for_layer(values, tuple(active_primes))
        candidate_count = len(candidates)
        candidate_prime_count = sum(1 for value in candidates if value in prime_set)
        candidate_fraction = candidate_count / range_count if range_count else 0.0
        precision = candidate_prime_count / candidate_count if candidate_count else 0.0
        recall = candidate_prime_count / prime_count if prime_count else 0.0
        compression_digits = (
            -math.log10(candidate_fraction) if candidate_fraction else float("inf")
        )
        results.append(
            ModLayerResult(
                layer=layer,
                added_prime=added_prime,
                modulus=modulus,
                totient=totient,
                theoretical_survival=round(totient / modulus, 12),
                range_count=range_count,
                candidate_count=candidate_count,
                prime_count=prime_count,
                candidate_fraction=round(candidate_fraction, 12),
                precision=round(precision, 12),
                recall=round(recall, 12),
                lift_vs_base_density=(
                    round(precision / base_density, 12) if base_density else 0.0
                ),
                candidates_per_prime=(
                    round(candidate_count / prime_count, 6) if prime_count else 0.0
                ),
                compression_digits=round(compression_digits, 9),
                marginal_compression_digits=round(
                    compression_digits - previous_digits, 9
                ),
                modulo_tests_per_integer=layer,
            )
        )
        previous_digits = compression_digits
    return results


def write_markdown(report: dict[str, object], path: Path) -> None:
    config = report["config"]  # type: ignore[index]
    results = report["results"]  # type: ignore[index]
    lines = [
        "# Prime Mod Layer Probe",
        "",
        "Classical modular gates measured as a precision/cost stack.",
        "",
        "## Config",
        "",
        f"- range: `{config['lower']}` to `{config['upper']}`",
        f"- range_count: `{config['range_count']}`",
        f"- prime_count: `{config['prime_count']}`",
        f"- base_density: `{config['base_density']}`",
        "",
        "## Layers",
        "",
        (
            "| Layer | Add p | Modulus | Candidates | Fraction | Precision | Recall | "
            "Lift | Cand/prime | Digits | Δdigits |"
        ),
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in results:  # type: ignore[assignment]
        lines.append(
            "| {layer} | {added_prime} | {modulus} | {candidate_count} | {candidate_fraction:.6f} | "
            "{precision:.6f} | {recall:.3f} | {lift_vs_base_density:.3f} | {candidates_per_prime:.2f} | "
            "{compression_digits:.3f} | {marginal_compression_digits:.3f} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "- Recall should stay 1.0 when the range starts above the layer primes.",
            "- Precision rises because each layer excludes another composite family.",
            "- Compression digits are `-log10(candidate_fraction)`: decimal narrowing of the search cone.",
            "- This is wheel/sieve structure, not a new local targeting lane.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_probe(
    lower: int, upper: int, layer_primes: tuple[int, ...]
) -> dict[str, object]:
    results = run_layers(lower, upper, layer_primes)
    prime_count = results[0].prime_count if results else 0
    range_count = upper - lower
    return {
        "schema_version": "prime_mod_layer_probe_v1",
        "config": {
            "lower": lower,
            "upper": upper,
            "range_count": range_count,
            "prime_count": prime_count,
            "base_density": (
                round(prime_count / range_count, 12) if range_count else 0.0
            ),
            "layer_primes": list(layer_primes),
        },
        "results": [asdict(result) for result in results],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lower", type=int, default=100_000)
    parser.add_argument("--upper", type=int, default=1_000_000)
    parser.add_argument(
        "--layer-primes", default=",".join(str(value) for value in DEFAULT_LAYER_PRIMES)
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    layer_primes = parse_layer_primes(args.layer_primes)
    report = run_probe(args.lower, args.upper, layer_primes)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "latest.json"
    md_path = args.out_dir / "LATEST.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, md_path)
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
