"""Nth-prime baseline gate.

This is the engineering comparator for the prime atlas work:

    n -> corridor for p_n -> count primes before corridor -> segmented wheel sieve -> p_n

The count-before-corridor step uses a sublinear prime_pi (Lucy_Hedgehog /
Dirichlet-hyperbola method): it evaluates pi only at the ~2*sqrt(x) distinct
floor(x/i) "ratio" points instead of sieving every integer up to x, so that
step no longer scales with x. That count step -- not the corridor -- was the
runtime floor; moving it is the only change that touches the dominant cost.
The segmented wheel sieve over the narrow corridor stays plain Python; this is
still a correctness/instrumentation baseline, not an LLVM-speed engine.

Indexing: standard 1-based indexing, so nth_prime(1) == 2. QueenJewels uses the
convention p_0 := 2, so subtract one when comparing command-line inputs.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "nth_prime_baseline_gate"
WHEEL_MODULUS = 30
WHEEL_RESIDUES = (1, 7, 11, 13, 17, 19, 23, 29)


@dataclass(frozen=True)
class PrimeCorridor:
    lower: int
    upper: int
    source: str


@dataclass(frozen=True)
class NthPrimeResult:
    n: int
    prime: int
    corridor_lower: int
    corridor_upper: int
    corridor_width: int
    count_before_lower: int
    count_step_keys: int
    remaining_index: int
    base_prime_count: int
    segments_scanned: int
    candidates_touched: int
    composites_marked: int
    elapsed_ms: float


def simple_sieve(limit: int) -> list[int]:
    if limit < 2:
        return []
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    root = int(math.isqrt(limit))
    for value in range(2, root + 1):
        if sieve[value]:
            start = value * value
            sieve[start : limit + 1 : value] = b"\x00" * (((limit - start) // value) + 1)
    return [idx for idx, is_prime in enumerate(sieve) if is_prime]


def prime_count_sieve(limit: int) -> int:
    """O(limit) reference count via full sieve. Kept as the exactness oracle."""
    return len(simple_sieve(limit))


def lucy_key_count(x: int) -> int:
    """Number of distinct floor(x/i) ratio-points Lucy evaluates (~2*sqrt(x))."""
    if x < 1:
        return 0
    r = math.isqrt(x)
    return r + (x // r) - 1


def prime_pi_lucy(x: int) -> int:
    """Sublinear prime count pi(x) via the Lucy_Hedgehog / Dirichlet-hyperbola method.

    Instead of sieving every integer up to x (O(x) time and memory), evaluate the
    running count only at the ~2*sqrt(x) DISTINCT values of floor(x/i) -- the
    "ratios" -- and let the multiplicative atoms (primes <= sqrt(x)) sieve across
    those few ratio-points in ever-larger steps. Time ~O(x^0.75), memory O(sqrt(x)).
    Returns pi(x) exactly; this is the count-step floor-lever.
    """
    if x < 2:
        return 0
    r = math.isqrt(x)
    keys = [x // i for i in range(1, r + 1)]
    keys += list(range(keys[-1] - 1, 0, -1))
    # counts[v] = (# integers in [2, v]); becomes pi(v) once all atoms are applied.
    counts = {v: v - 1 for v in keys}
    for p in range(2, r + 1):
        if counts[p] == counts[p - 1]:
            continue  # p is composite (no new prime between p-1 and p)
        primes_below_p = counts[p - 1]
        p_sq = p * p
        for v in keys:
            if v < p_sq:
                break
            counts[v] -= counts[v // p] - primes_below_p
    return counts[x]


def nth_prime_small(n: int) -> int:
    if n < 1:
        raise ValueError("n must be 1-based and positive")
    small = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
    if n <= len(small):
        return small[n - 1]
    # Rosser-style upper is enough for a compact small fallback.
    bound = int(n * (math.log(n) + math.log(math.log(n))) + 16)
    while True:
        primes = simple_sieve(bound)
        if len(primes) >= n:
            return primes[n - 1]
        bound *= 2


def nth_prime_corridor(n: int) -> PrimeCorridor:
    if n < 1:
        raise ValueError("n must be 1-based and positive")
    if n < 6:
        value = nth_prime_small(n)
        return PrimeCorridor(lower=value, upper=value, source="exact_small")

    x = float(n)
    log_n = math.log(x)
    log_log_n = math.log(log_n)
    upper = math.ceil(x * (log_n + log_log_n)) + 32
    if n >= 4:
        lower = math.floor(x * (log_n + log_log_n - 1.0 + (log_log_n - 2.1) / log_n))
    else:
        lower = 2
    lower = max(2, lower)
    upper = max(upper, lower + 256)

    # Widen if the lower bound was too aggressive for small n.
    while prime_pi_lucy(max(lower - 1, 1)) >= n:
        lower = max(2, lower - max(128, (upper - lower) // 2))
    while prime_pi_lucy(upper) < n:
        upper *= 2
    return PrimeCorridor(lower=lower, upper=upper, source="dusart_rosser")


def wheel_candidates_in_segment(start: int, stop: int) -> list[int]:
    candidates: list[int] = []
    if start <= 2 <= stop:
        candidates.append(2)
    if start <= 3 <= stop:
        candidates.append(3)
    if start <= 5 <= stop:
        candidates.append(5)
    first_block = max(0, start // WHEEL_MODULUS - 1)
    last_block = stop // WHEEL_MODULUS + 1
    for block in range(first_block, last_block + 1):
        base = block * WHEEL_MODULUS
        for residue in WHEEL_RESIDUES:
            value = base + residue
            if start <= value <= stop and value > 5:
                candidates.append(value)
    return sorted(set(candidates))


def segmented_primes(
    start: int,
    stop: int,
    base_primes: list[int],
    segment_size: int = 262_144,
) -> tuple[list[int], int, int, int]:
    if stop < start:
        return [], 0, 0, 0
    found: list[int] = []
    segments = 0
    candidates_touched = 0
    composites_marked = 0
    for low in range(start, stop + 1, segment_size):
        high = min(stop, low + segment_size - 1)
        candidates = wheel_candidates_in_segment(low, high)
        is_candidate = {value: True for value in candidates}
        candidates_touched += len(candidates)
        for prime in base_primes:
            if prime < 7:
                continue
            prime_square = prime * prime
            if prime_square > high:
                break
            first = max(prime_square, ((low + prime - 1) // prime) * prime)
            for multiple in range(first, high + 1, prime):
                if multiple in is_candidate and is_candidate[multiple]:
                    is_candidate[multiple] = False
                    composites_marked += 1
        found.extend(value for value in candidates if is_candidate.get(value, False) and value >= start)
        segments += 1
    return found, segments, candidates_touched, composites_marked


def nth_prime_baseline(n: int, segment_size: int = 262_144) -> NthPrimeResult:
    start_time = time.perf_counter()
    corridor = nth_prime_corridor(n)
    if corridor.lower == corridor.upper:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return NthPrimeResult(
            n=n,
            prime=corridor.lower,
            corridor_lower=corridor.lower,
            corridor_upper=corridor.upper,
            corridor_width=0,
            count_before_lower=n - 1,
            count_step_keys=0,
            remaining_index=1,
            base_prime_count=0,
            segments_scanned=0,
            candidates_touched=1,
            composites_marked=0,
            elapsed_ms=elapsed_ms,
        )

    count_before = prime_pi_lucy(corridor.lower - 1)
    count_keys = lucy_key_count(corridor.lower - 1)
    remaining = n - count_before
    base_primes = simple_sieve(math.isqrt(corridor.upper) + 1)
    segment_primes, segments, candidates_touched, composites_marked = segmented_primes(
        corridor.lower,
        corridor.upper,
        base_primes,
        segment_size=segment_size,
    )
    if remaining < 1 or remaining > len(segment_primes):
        raise RuntimeError(
            f"corridor failed for n={n}: count_before={count_before}, segment_primes={len(segment_primes)}"
        )
    prime = segment_primes[remaining - 1]
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    return NthPrimeResult(
        n=n,
        prime=prime,
        corridor_lower=corridor.lower,
        corridor_upper=corridor.upper,
        corridor_width=corridor.upper - corridor.lower + 1,
        count_before_lower=count_before,
        count_step_keys=count_keys,
        remaining_index=remaining,
        base_prime_count=len(base_primes),
        segments_scanned=segments,
        candidates_touched=candidates_touched,
        composites_marked=composites_marked,
        elapsed_ms=elapsed_ms,
    )


def run_benchmark(ns: list[int], segment_size: int = 262_144, out_dir: Path | None = None) -> dict[str, object]:
    results = [nth_prime_baseline(n, segment_size=segment_size) for n in ns]
    summary: dict[str, object] = {
        "indexing": "1-based: nth_prime(1) == 2",
        "segment_size": segment_size,
        "results": [asdict(result) for result in results],
        "decision_record": {
            "promotion": "BASELINE_GATE",
            "verdict": "NTH_PRIME_BASELINE_READY",
            "claim_boundary": (
                "Plain Python correctness/instrumentation baseline. "
                "Not intended to match LLVM or production sieve speed."
            ),
        },
    }
    if out_dir is not None:
        write_artifacts(summary, out_dir)
    return summary


def write_artifacts(summary: dict[str, object], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("n", nargs="*", type=int, help="1-based prime indices to compute")
    parser.add_argument("--segment-size", type=int, default=262_144)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ns = args.n or [1, 10, 100, 1_000, 10_000, 100_000]
    summary = run_benchmark(ns, segment_size=args.segment_size, out_dir=args.out_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
