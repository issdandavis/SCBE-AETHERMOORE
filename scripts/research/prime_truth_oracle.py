"""Exact prime truth layer for prime-fog experiments.

The field sensors can rank candidate regions, but this module is the hard
truth rail for current ring-scale numbers:

  - is_prime_u64(n): deterministic Miller-Rabin for n < 2**64
  - next_prime_at_or_after(n) / previous_prime_at_or_before(n)
  - segmented_primes(lower, upper): exact prime generation on bounded intervals
  - verify_artifact_anchor_primes(path): prove stored anchor values are prime
  - verify_artifact_anchor_superprimes(path): prove anchor p and pi(p) are prime

This is intentionally separate from the large probe harness so primality is a
first-class process, not a side effect of the search experiment.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


U64_LIMIT = 1 << 64
MR_U64_BASES = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)
SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
ANCHOR_LIST_KEYS = {
    "anchors",
    "hit_anchors",
    "ip_new_anchors",
    "new_anchors",
    "top20_ip",
    "top20_union_anchors",
    "top50_union_anchors",
    "top100_union_anchors",
    "predicted_new_anchors",
    "new_anchors_under_prediction",
}


@dataclass(frozen=True)
class AnchorPrimeCheck:
    path: str
    value: int
    is_prime: bool


@dataclass(frozen=True)
class AnchorSuperprimeCheck:
    path: str
    value: int
    is_prime: bool
    prime_index: int | None
    index_is_prime: bool
    is_superprime: bool


def _require_u64(n: int) -> None:
    if not 0 <= n < U64_LIMIT:
        raise ValueError(f"n must satisfy 0 <= n < 2**64 for exact u64 primality, got {n}")


def is_prime_u64(n: int) -> bool:
    """Return exact primality for unsigned 64-bit integers."""
    _require_u64(n)
    if n < 2:
        return False
    for p in SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False

    d = n - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2

    for base in MR_U64_BASES:
        a = base % n
        if a in (0, 1):
            continue
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def next_prime_at_or_after(n: int) -> int:
    _require_u64(max(0, n))
    if n <= 2:
        return 2
    candidate = n if n % 2 else n + 1
    while candidate < U64_LIMIT and not is_prime_u64(candidate):
        candidate += 2
    if candidate >= U64_LIMIT:
        raise ValueError("no u64 prime exists at or after the requested value")
    return candidate


def previous_prime_at_or_before(n: int) -> int | None:
    _require_u64(max(0, n))
    if n < 2:
        return None
    if n == 2:
        return 2
    candidate = n if n % 2 else n - 1
    while candidate >= 3:
        if is_prime_u64(candidate):
            return candidate
        candidate -= 2
    return 2


def prime_stream(start: int, count: int) -> list[int]:
    if count < 0:
        raise ValueError("count must be non-negative")
    primes: list[int] = []
    cursor = start
    while len(primes) < count:
        prime = next_prime_at_or_after(cursor)
        primes.append(prime)
        cursor = prime + 1
    return primes


def _simple_sieve(limit: int) -> list[int]:
    if limit < 2:
        return []
    flags = bytearray(b"\x01") * (limit + 1)
    flags[0:2] = b"\x00\x00"
    root = math.isqrt(limit)
    for n in range(2, root + 1):
        if flags[n]:
            start = n * n
            flags[start : limit + 1 : n] = b"\x00" * (((limit - start) // n) + 1)
    return [n for n in range(2, limit + 1) if flags[n]]


def segmented_primes(lower: int, upper: int) -> list[int]:
    """Return all primes in the half-open interval [lower, upper)."""
    if upper <= lower:
        return []
    if lower < 0 or upper > U64_LIMIT:
        raise ValueError("range must stay within 0 <= n < 2**64")

    low = max(2, lower)
    size = upper - low
    flags = bytearray(b"\x01") * size
    for p in _simple_sieve(math.isqrt(upper - 1) + 1):
        start = max(p * p, ((low + p - 1) // p) * p)
        for multiple in range(start, upper, p):
            flags[multiple - low] = 0
    return [low + index for index, flag in enumerate(flags) if flag]


def prime_indices_for_values(values: Iterable[int], segment_size: int = 4_000_000) -> dict[int, int]:
    """Return 1-based prime indices pi(p) for requested prime values.

    This is an independent segmented count, deliberately separate from the
    prime-fog scorer. Non-prime requested values are omitted from the result.
    """
    targets = sorted({int(value) for value in values if int(value) >= 2})
    if not targets:
        return {}
    if segment_size < 1024:
        raise ValueError("segment_size must be at least 1024")
    for value in targets:
        _require_u64(value)

    target_set = set(targets)
    max_target = targets[-1]
    base_primes = _simple_sieve(math.isqrt(max_target) + 1)
    indices: dict[int, int] = {}
    prime_count = 0

    low = 2
    while low <= max_target:
        high = min(max_target + 1, low + segment_size)
        flags = bytearray(b"\x01") * (high - low)
        for p in base_primes:
            if p * p >= high:
                break
            start = max(p * p, ((low + p - 1) // p) * p)
            flags[start - low : high - low : p] = b"\x00" * (((high - 1 - start) // p) + 1)

        for offset, flag in enumerate(flags):
            if not flag:
                continue
            value = low + offset
            prime_count += 1
            if value in target_set:
                indices[value] = prime_count
        low = high

    return indices


def _extract_anchor_values(value: Any, path: str = "$", parent_key: str | None = None) -> Iterable[tuple[str, int]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == "anchor_prime" and isinstance(child, int):
                yield child_path, child
            elif key in ANCHOR_LIST_KEYS and isinstance(child, list):
                for index, item in enumerate(child):
                    if isinstance(item, int):
                        yield f"{child_path}[{index}]", item
            else:
                yield from _extract_anchor_values(child, child_path, key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _extract_anchor_values(child, f"{path}[{index}]", parent_key)


def extract_artifact_anchor_values(path: Path) -> list[tuple[str, int]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(_extract_anchor_values(data))


def verify_artifact_anchor_primes(path: Path) -> list[AnchorPrimeCheck]:
    extracted = extract_artifact_anchor_values(path)
    checks = [
        AnchorPrimeCheck(path=item_path, value=number, is_prime=is_prime_u64(number))
        for item_path, number in extracted
    ]
    checks.sort(key=lambda item: (item.value, item.path))
    return checks


def verify_artifact_anchor_superprimes(path: Path) -> list[AnchorSuperprimeCheck]:
    extracted = extract_artifact_anchor_values(path)
    prime_indices = prime_indices_for_values(number for _item_path, number in extracted)
    checks = []
    for item_path, number in extracted:
        is_prime = is_prime_u64(number)
        prime_index = prime_indices.get(number)
        index_is_prime = prime_index is not None and is_prime_u64(prime_index)
        checks.append(
            AnchorSuperprimeCheck(
                path=item_path,
                value=number,
                is_prime=is_prime,
                prime_index=prime_index,
                index_is_prime=index_is_prime,
                is_superprime=is_prime and index_is_prime,
            )
        )
    checks.sort(key=lambda item: (item.value, item.path))
    return checks


def _cmd(args: argparse.Namespace) -> int:
    if args.is_prime is not None:
        print(json.dumps({"n": args.is_prime, "is_prime": is_prime_u64(args.is_prime)}, indent=2))
        return 0
    if args.next is not None:
        print(json.dumps({"start": args.next, "prime": next_prime_at_or_after(args.next)}, indent=2))
        return 0
    if args.previous is not None:
        print(json.dumps({"start": args.previous, "prime": previous_prime_at_or_before(args.previous)}, indent=2))
        return 0
    if args.stream is not None:
        start, count = args.stream
        print(json.dumps({"start": start, "count": count, "primes": prime_stream(start, count)}, indent=2))
        return 0
    if args.segment is not None:
        lower, upper = args.segment
        primes = segmented_primes(lower, upper)
        print(json.dumps({"lower": lower, "upper": upper, "count": len(primes), "primes": primes}, indent=2))
        return 0
    if args.verify_artifact is not None:
        checks = verify_artifact_anchor_superprimes(args.verify_artifact)
        failures = [check for check in checks if not check.is_superprime]
        print(
            json.dumps(
                {
                    "artifact": str(args.verify_artifact),
                    "checked": len(checks),
                    "failed": len(failures),
                    "mode": "superprime",
                    "failures": [asdict(check) for check in failures],
                },
                indent=2,
            )
        )
        return 1 if failures else 0
    raise SystemExit("no command selected")


def main() -> int:
    parser = argparse.ArgumentParser(description="Exact prime truth layer for prime-fog ring-scale numbers.")
    parser.add_argument("--is-prime", type=int)
    parser.add_argument("--next", type=int)
    parser.add_argument("--previous", type=int)
    parser.add_argument("--stream", type=int, nargs=2, metavar=("START", "COUNT"))
    parser.add_argument("--segment", type=int, nargs=2, metavar=("LOWER", "UPPER"))
    parser.add_argument("--verify-artifact", type=Path)
    return _cmd(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
