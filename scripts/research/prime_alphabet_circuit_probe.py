"""Prime alphabet circuit probe.

This tests the "let primes write letters" idea as a compression experiment:

    primes -> behavior-derived symbols -> rotating alphabet circuit -> n-grams

The key discipline is that the letters must encode prime behavior, not just
prime order. Each encoding is compared against a null that shuffles the same
behavior letters and then applies the same rotating alphabet circuit. That
preserves the letter inventory and the circuit schedule while destroying prime
order.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

try:
    from run_prime_calibration_targeting_probe import simple_sieve
except ModuleNotFoundError:  # pragma: no cover - package import path for tests
    from scripts.research.run_prime_calibration_targeting_probe import simple_sieve


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "prime_alphabet_circuit_probe"
ALPHABET = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
ALPHABET_SIZE = len(ALPHABET)
CIRCUIT_SIZE = ALPHABET_SIZE * ALPHABET_SIZE
WHEEL_210_ALLOWED = tuple(r for r in range(210) if math.gcd(r, 210) == 1)
WHEEL_210_RANK = {residue: index for index, residue in enumerate(WHEEL_210_ALLOWED)}


@dataclass(frozen=True)
class SequenceStats:
    adjacent_mi_bits: float
    top_trigram_count: int
    transition_coverage: float
    distinct_letters: int


@dataclass(frozen=True)
class AlphabetResult:
    encoding: str
    mode: str
    symbol_count: int
    circuit_count: int
    stats: SequenceStats
    null_mean_mi: float
    null_p95_mi: float
    null_pvalue_mi: float
    null_mean_top_trigram: float
    null_p95_top_trigram: float
    null_pvalue_top_trigram: float
    verdict: str
    sample: str


def rotation_offset(index: int, alphabet_size: int = ALPHABET_SIZE) -> int:
    """Return the circuit offset: A, Z, Y, ..., B, then repeat."""
    if index < 0:
        raise ValueError("index must be non-negative")
    return (-(index // alphabet_size)) % alphabet_size


def apply_rotating_circuit(symbols: list[int]) -> list[int]:
    return [
        (symbol + rotation_offset(index)) % ALPHABET_SIZE
        for index, symbol in enumerate(symbols)
    ]


def symbols_to_text(symbols: list[int], limit: int = 96) -> str:
    return "".join(ALPHABET[symbol % ALPHABET_SIZE] for symbol in symbols[:limit])


def trim_to_complete_circuits(symbols: list[int]) -> list[int]:
    count = len(symbols) // CIRCUIT_SIZE
    if count == 0:
        return symbols[:]
    return symbols[: count * CIRCUIT_SIZE]


def quantile_buckets(
    values: list[float], bucket_count: int = ALPHABET_SIZE
) -> list[int]:
    if not values:
        return []
    ordered = sorted(values)
    buckets: list[int] = []
    n = len(values)
    for value in values:
        # bisect_right without importing bisect keeps this tiny and deterministic.
        lo = 0
        hi = n
        while lo < hi:
            mid = (lo + hi) // 2
            if value < ordered[mid]:
                hi = mid
            else:
                lo = mid + 1
        bucket = min(bucket_count - 1, (lo * bucket_count) // n)
        buckets.append(bucket)
    return buckets


def value_mod26(primes: list[int]) -> list[int]:
    return [prime % ALPHABET_SIZE for prime in primes]


def gap_mod26(primes: list[int]) -> list[int]:
    return [(b - a) % ALPHABET_SIZE for a, b in zip(primes, primes[1:])]


def wheel210_bucket26(primes: list[int]) -> list[int]:
    symbols: list[int] = []
    for prime in primes:
        rank = WHEEL_210_RANK.get(prime % 210)
        if rank is None:
            continue
        symbols.append((rank * ALPHABET_SIZE) // len(WHEEL_210_ALLOWED))
    return symbols


def normalized_gap_bucket(primes: list[int]) -> list[int]:
    symbols: list[int] = []
    for prime, next_prime in zip(primes, primes[1:]):
        expected = max(math.log(prime), 1.0)
        ratio = (next_prime - prime) / expected
        symbols.append(min(ALPHABET_SIZE - 1, max(0, int(ratio * 4.0))))
    return symbols


def ratio_curvature_bucket(primes: list[int]) -> list[int]:
    values: list[float] = []
    for left, middle, right in zip(primes, primes[1:], primes[2:]):
        first = math.log(middle / left)
        second = math.log(right / middle)
        values.append(second - first)
    return quantile_buckets(values)


ENCODERS: dict[str, Callable[[list[int]], list[int]]] = {
    "value_mod26": value_mod26,
    "gap_mod26": gap_mod26,
    "wheel210_bucket26": wheel210_bucket26,
    "normalized_gap_bucket": normalized_gap_bucket,
    "ratio_curvature_bucket": ratio_curvature_bucket,
}


def adjacent_mi_bits(symbols: list[int]) -> float:
    if len(symbols) < 2:
        return 0.0
    left_counts = Counter(symbols[:-1])
    right_counts = Counter(symbols[1:])
    pair_counts = Counter(zip(symbols[:-1], symbols[1:]))
    total = len(symbols) - 1
    score = 0.0
    for (left, right), count in pair_counts.items():
        pxy = count / total
        px = left_counts[left] / total
        py = right_counts[right] / total
        score += pxy * math.log2(pxy / (px * py))
    return score


def top_ngram_count(symbols: list[int], n: int = 3) -> int:
    if len(symbols) < n:
        return 0
    return max(
        Counter(
            tuple(symbols[index : index + n]) for index in range(len(symbols) - n + 1)
        ).values()
    )


def transition_coverage(symbols: list[int]) -> float:
    if len(symbols) < 2:
        return 0.0
    return len(set(zip(symbols[:-1], symbols[1:]))) / float(
        ALPHABET_SIZE * ALPHABET_SIZE
    )


def sequence_stats(symbols: list[int]) -> SequenceStats:
    return SequenceStats(
        adjacent_mi_bits=round(adjacent_mi_bits(symbols), 9),
        top_trigram_count=top_ngram_count(symbols),
        transition_coverage=round(transition_coverage(symbols), 9),
        distinct_letters=len(set(symbols)),
    )


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil((pct / 100.0) * len(ordered)) - 1))
    return ordered[index]


def evaluate_symbols(
    encoding: str,
    base_symbols: list[int],
    mode: str,
    null_seeds: int,
    complete_circuits: bool,
) -> AlphabetResult:
    if mode not in {"direct", "rotating"}:
        raise ValueError("mode must be direct or rotating")

    symbols = (
        trim_to_complete_circuits(base_symbols)
        if complete_circuits
        else base_symbols[:]
    )
    if mode == "rotating":
        real_symbols = apply_rotating_circuit(symbols)
    else:
        real_symbols = symbols

    real_stats = sequence_stats(real_symbols)
    null_mi: list[float] = []
    null_top: list[float] = []
    rng = random.Random(1729)
    for _seed in range(null_seeds):
        shuffled = symbols[:]
        rng.shuffle(shuffled)
        if mode == "rotating":
            shuffled = apply_rotating_circuit(shuffled)
        stats = sequence_stats(shuffled)
        null_mi.append(stats.adjacent_mi_bits)
        null_top.append(float(stats.top_trigram_count))

    mi_ge = sum(1 for value in null_mi if value >= real_stats.adjacent_mi_bits)
    top_ge = sum(1 for value in null_top if value >= real_stats.top_trigram_count)
    null_p95_mi = percentile(null_mi, 95.0)
    null_p95_top = percentile(null_top, 95.0)
    clears_mi = real_stats.adjacent_mi_bits > null_p95_mi
    verdict = "CLEARS_MI_NULL" if clears_mi else "null"
    return AlphabetResult(
        encoding=encoding,
        mode=mode,
        symbol_count=len(symbols),
        circuit_count=len(symbols) // CIRCUIT_SIZE,
        stats=real_stats,
        null_mean_mi=round(sum(null_mi) / len(null_mi), 9) if null_mi else 0.0,
        null_p95_mi=round(null_p95_mi, 9),
        null_pvalue_mi=round((mi_ge + 1) / (len(null_mi) + 1), 6) if null_mi else 1.0,
        null_mean_top_trigram=(
            round(sum(null_top) / len(null_top), 3) if null_top else 0.0
        ),
        null_p95_top_trigram=round(null_p95_top, 3),
        null_pvalue_top_trigram=(
            round((top_ge + 1) / (len(null_top) + 1), 6) if null_top else 1.0
        ),
        verdict=verdict,
        sample=symbols_to_text(real_symbols),
    )


def run_probe(
    limit: int,
    max_primes: int,
    null_seeds: int,
    complete_circuits: bool,
    modes: tuple[str, ...] = ("direct", "rotating"),
) -> dict[str, object]:
    primes = simple_sieve(limit)
    if max_primes > 0:
        primes = primes[:max_primes]
    if len(primes) < CIRCUIT_SIZE:
        raise ValueError(f"need at least {CIRCUIT_SIZE} primes for one full circuit")

    results: list[AlphabetResult] = []
    for encoding, encoder in ENCODERS.items():
        base_symbols = encoder(primes)
        if len(base_symbols) < CIRCUIT_SIZE:
            continue
        for mode in modes:
            results.append(
                evaluate_symbols(
                    encoding=encoding,
                    base_symbols=base_symbols,
                    mode=mode,
                    null_seeds=null_seeds,
                    complete_circuits=complete_circuits,
                )
            )

    return {
        "schema_version": "prime_alphabet_circuit_probe_v1",
        "config": {
            "limit": limit,
            "prime_count": len(primes),
            "null_seeds": null_seeds,
            "complete_circuits": complete_circuits,
            "circuit_size": CIRCUIT_SIZE,
            "alphabet": "".join(ALPHABET),
        },
        "results": [asdict(result) for result in results],
    }


def write_markdown(report: dict[str, object], path: Path) -> None:
    config = report["config"]  # type: ignore[index]
    results = report["results"]  # type: ignore[index]
    lines = [
        "# Prime Alphabet Circuit Probe",
        "",
        "Behavior-derived letters are tested against a same-inventory shuffle null.",
        "The rotating mode applies the A, Z, Y, ..., B start-position circuit before scoring n-grams.",
        "",
        "## Config",
        "",
        f"- limit: `{config['limit']}`",  # type: ignore[index]
        f"- prime_count: `{config['prime_count']}`",  # type: ignore[index]
        f"- null_seeds: `{config['null_seeds']}`",  # type: ignore[index]
        f"- complete_circuits: `{config['complete_circuits']}`",  # type: ignore[index]
        "",
        "## Results",
        "",
        "| Encoding | Mode | Circuits | MI bits | Null p95 | p | Top tri | Verdict |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in results:  # type: ignore[assignment]
        stats = item["stats"]
        lines.append(
            "| {encoding} | {mode} | {circuit_count} | {mi:.6f} | {p95:.6f} | {p:.4f} | {tri} | {verdict} |".format(
                encoding=item["encoding"],
                mode=item["mode"],
                circuit_count=item["circuit_count"],
                mi=stats["adjacent_mi_bits"],
                p95=item["null_p95_mi"],
                p=item["null_pvalue_mi"],
                tri=stats["top_trigram_count"],
                verdict=item["verdict"],
            )
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "- A pass means the letter stream has adjacent transition structure beyond a same-inventory shuffle.",
            (
                "- A pass does not make a prime-fog targeting lane; it only says the symbolic "
                "encoding carries order information."
            ),
            (
                "- A null result means the alphabet circuit is a visualization for that encoding, "
                "not a compression signal."
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1_000_000)
    parser.add_argument("--max-primes", type=int, default=50_000)
    parser.add_argument("--null-seeds", type=int, default=120)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--no-complete-circuits", action="store_true")
    args = parser.parse_args()

    report = run_probe(
        limit=args.limit,
        max_primes=args.max_primes,
        null_seeds=args.null_seeds,
        complete_circuits=not args.no_complete_circuits,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "latest.json"
    md_path = args.out_dir / "LATEST.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, md_path)
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
