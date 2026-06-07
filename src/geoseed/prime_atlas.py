"""Prime Spacetime Atlas — a truthful multi-coordinate address over KNOWN primes.

Mission (prime-fog handoff): the known primes are the stars, the transforms are
the maps, the pathfinder is the ship. Before any ship flies outward, the atlas
must explain the OLD territory truthfully. Each known prime gets an ADDRESS built
from coordinates that are either exact facts about the integer or whose
predictive status the prime-fog null gates already settled.

The atlas carries the VERDICT on each coordinate, so a path through number-space
can be checked as real-vs-hallucinated geometry by construction:

    FACT                 - exact property of the integer (recording it never overfits)
    KNOWN_STRUCTURE      - an alignment that SURVIVED a proper null (wheel, log density)
    FALSIFIED_PROJECTION - computable, but proven NON-predictive by the null gates
                           (ratio graph, gap acceleration) — kept so the map can SHOW
                           you the hallucinated geometry instead of hiding it.

This is the constructor-side companion to
``scripts/research/prime_alignment_ledger.py`` (the ring-anchor gate substrate);
here the key is the prime itself, for general GeoSeed / M6 use. It reuses the
wheel/log structure of :mod:`src.geoseed.prime_seed_init`.
"""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

from src.geoseed.prime_seed_init import (
    DEFAULT_M6_LAYER_PRIMES,
    PrimeAnchorSeed,
    build_prime_anchor_seed,
    dusart_bracket,
)

# Small-prime residue vector. These are FACTS about the integer; recording them
# never overfits. Whether a residue ALIGNS to structure is a gate question.
RESIDUE_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)

# M6 primorial wheel modulus (KO..DR = 2,3,5,7,11,13).
WHEEL_MODULUS = math.prod(DEFAULT_M6_LAYER_PRIMES)  # 30030

# The epistemic status of every coordinate the atlas records. A coordinate with
# no entry here is a bug: the atlas must never carry an unclassified projection.
# (Enforced by test_every_coordinate_has_declared_status.)
COORDINATE_STATUS: dict[str, tuple[str, str]] = {
    "value": ("FACT", "the prime itself"),
    "index": ("FACT", "n such that value == p_n (1-based)"),
    "gap_prev": ("FACT", "value - previous prime"),
    "gap_next": ("FACT", "next prime - value"),
    "ratio_prev": ("FACT", "value / previous prime"),
    "ratio_next": ("FACT", "next prime / value"),
    "curvature": (
        "FALSIFIED_PROJECTION",
        "ratio_next/ratio_prev; ratio_curvature failed the count-honest gate (3/4 rings)",
    ),
    "log_value": ("KNOWN_STRUCTURE", "ln value — PNT density coordinate (survives)"),
    "log_log_value": ("KNOWN_STRUCTURE", "ln ln value — Cipolla tower term (survives)"),
    "residues": ("FACT", f"value mod {RESIDUE_PRIMES}"),
    "wheel_lane": (
        "KNOWN_STRUCTURE",
        f"value mod {WHEEL_MODULUS}; primorial wheel lane (survives as the density floor)",
    ),
    "ap_length": (
        "KNOWN_STRUCTURE",
        "length of the longest prime arithmetic progression through value (Green-Tao "
        "straight-line structure: sparse space, guaranteed APs under the AP coordinate)",
    ),
    "ap_difference": (
        "KNOWN_STRUCTURE",
        "common difference of that prime AP (must be even, and divisible by primorials "
        "for longer APs — a known constraint)",
    ),
    "graph_signature": (
        "FALSIFIED_PROJECTION",
        "(gap_prev, gap_next) transition node; ratio_graph_resonance died 0/14 (circular-shift null)",
    ),
}


@dataclass(frozen=True)
class PrimeAddress:
    """The truthful multi-coordinate address of one known prime."""

    value: int
    index: int
    gap_prev: int
    gap_next: int
    ratio_prev: float
    ratio_next: float
    curvature: float
    log_value: float
    log_log_value: float
    residues: tuple[int, ...]
    wheel_lane: int
    ap_length: int
    ap_difference: int
    graph_signature: tuple[int, int]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PrimeSeedRegion:
    """Exact atlas view over one GeoSeed prime-seed window.

    This is the bridge from constructor to atlas: the seed emits a guaranteed
    candidate interval, and the region query enumerates the KNOWN primes inside
    that interval. It does not select a prime; it reports the truth-map surface
    the pathfinder is allowed to inspect.
    """

    schema_version: str
    query_index: int
    seed: PrimeAnchorSeed
    addresses: tuple[PrimeAddress, ...]
    target_inside_window: bool
    target_value: int | None
    structure_counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "query_index": self.query_index,
            "seed": self.seed.to_dict(),
            "addresses": [address.to_dict() for address in self.addresses],
            "known_structures": [
                nearest_known_structures(address) for address in self.addresses
            ],
            "target_inside_window": self.target_inside_window,
            "target_value": self.target_value,
            "structure_counts": dict(self.structure_counts),
        }


def _primes_upto(limit: int) -> list[int]:
    """Exact prime table by sieve — the atlas's truth source (the 'star map')."""
    if limit < 2:
        return []
    sieve = bytearray([1]) * (limit + 1)
    sieve[0] = sieve[1] = 0
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            sieve[i * i :: i] = bytearray(len(sieve[i * i :: i]))
    return [i for i in range(limit + 1) if sieve[i]]


def _is_prime(n: int) -> bool:
    """Trial-division primality — fallback for AP terms beyond the sieved range."""
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    factor = 3
    while factor * factor <= n:
        if n % factor == 0:
            return False
        factor += 2
    return True


def prime_ap_through(
    value, is_prime, max_len: int = 6, max_diff: int = 210
) -> tuple[int, int]:
    """Longest arithmetic progression of PRIMES through `value` (Green-Tao structure).

    The "right coordinate rule" that turns scattered primes into straight lines:
    search even common differences d (odd d would force an even, non-prime term
    since `value` is odd), extend the AP forward and backward from `value`, and
    report the longest (length, difference) found, capped at `max_len`.

    Returns (1, 0) for a prime in no detected AP within the bounds.
    """
    best_length, best_diff = 1, 0
    for diff in range(2, max_diff + 1, 2):
        forward = 0
        while forward < max_len and is_prime(value + (forward + 1) * diff):
            forward += 1
        backward = 0
        while (
            backward < max_len
            and value - (backward + 1) * diff >= 2
            and is_prime(value - (backward + 1) * diff)
        ):
            backward += 1
        length = min(1 + forward + backward, max_len)
        if length > best_length:
            best_length, best_diff = length, diff
    return best_length, best_diff


def _address_from_neighbors(
    index: int, prev_p: int, value: int, next_p: int, ap_length: int, ap_difference: int
) -> PrimeAddress:
    gap_prev = value - prev_p
    gap_next = next_p - value
    ratio_prev = value / prev_p
    ratio_next = next_p / value
    log_value = math.log(value)
    return PrimeAddress(
        value=value,
        index=index,
        gap_prev=gap_prev,
        gap_next=gap_next,
        ratio_prev=ratio_prev,
        ratio_next=ratio_next,
        curvature=ratio_next / ratio_prev,
        log_value=log_value,
        log_log_value=math.log(log_value),
        residues=tuple(value % q for q in RESIDUE_PRIMES),
        wheel_lane=value % WHEEL_MODULUS,
        ap_length=ap_length,
        ap_difference=ap_difference,
        graph_signature=(gap_prev, gap_next),
    )


def build_prime_atlas(start_index: int, count: int) -> tuple[PrimeAddress, ...]:
    """Build truthful addresses for `count` known primes starting at `start_index`.

    `start_index` is 1-based (index 1 -> p_1 = 2). Neighbors are needed for gaps,
    so the sieve is sized by the proven Dusart upper bound on the largest index.
    """
    if start_index < 2:
        raise ValueError("start_index must be >= 2 (need a previous prime for gaps)")
    if count < 1:
        raise ValueError("count must be positive")
    last_index = start_index + count  # +1 neighbor on the high side
    sieve_limit = dusart_bracket(last_index)[1] + 1
    primes = _primes_upto(sieve_limit)
    if len(primes) <= last_index:
        raise RuntimeError("sieve undershot the requested index range")
    prime_set = set(primes)

    def is_prime(n: int) -> bool:
        # fast set membership inside the sieved range; exact trial division above it
        return (n in prime_set) if n <= sieve_limit else _is_prime(n)

    addresses = []
    for index in range(start_index, start_index + count):
        # primes is 0-based: primes[k] == p_{k+1}
        prev_p, value, next_p = primes[index - 2], primes[index - 1], primes[index]
        ap_length, ap_difference = prime_ap_through(value, is_prime)
        addresses.append(
            _address_from_neighbors(
                index, prev_p, value, next_p, ap_length, ap_difference
            )
        )
    return tuple(addresses)


def build_prime_seed_region(
    index: int,
    layer_primes: Iterable[int] = DEFAULT_M6_LAYER_PRIMES,
    mode: str = "proven",
    sigma: float = 16.0,
    max_sieve_limit: int = 2_000_000,
) -> PrimeSeedRegion:
    """Return exact atlas addresses inside the GeoSeed seed window.

    Default `mode="proven"` inherits the seed's Dusart/Rosser-Schoenfeld
    containment contract. The atlas side then enumerates the known primes inside
    that interval and annotates their survived structures.

    `max_sieve_limit` is an intentional safety guard: this function is for
    constructor/atlas views, not accidental giant-ring sieves. Raise it
    explicitly when a larger local atlas is worth the memory.
    """
    if max_sieve_limit < 100:
        raise ValueError("max_sieve_limit is too small for an atlas region")
    seed = build_prime_anchor_seed(
        index, layer_primes=layer_primes, mode=mode, sigma=sigma
    )
    buffer = max(1024, int(math.sqrt(seed.upper_bound)) + 100)
    sieve_limit = seed.upper_bound + buffer
    if sieve_limit > max_sieve_limit:
        raise ValueError(
            f"seed region requires sieve_limit={sieve_limit}; "
            f"increase max_sieve_limit knowingly (current {max_sieve_limit})"
        )

    while True:
        primes = _primes_upto(sieve_limit)
        if primes and primes[-1] > seed.upper_bound:
            break
        sieve_limit *= 2
        if sieve_limit > max_sieve_limit:
            raise ValueError(
                f"seed region requires sieve_limit>{max_sieve_limit} to find a high-side neighbor; "
                "increase max_sieve_limit knowingly"
            )

    prime_set = set(primes)

    def is_prime(n: int) -> bool:
        return (n in prime_set) if n <= sieve_limit else _is_prime(n)

    addresses: list[PrimeAddress] = []
    for position, value in enumerate(primes):
        if value < seed.lower_bound:
            continue
        if value > seed.upper_bound:
            break
        if position == 0 or position + 1 >= len(primes):
            raise RuntimeError("sieve did not provide required prime neighbors")
        ap_length, ap_difference = prime_ap_through(value, is_prime)
        addresses.append(
            _address_from_neighbors(
                position + 1,
                primes[position - 1],
                value,
                primes[position + 1],
                ap_length,
                ap_difference,
            )
        )

    target = next((address for address in addresses if address.index == index), None)
    return PrimeSeedRegion(
        schema_version="prime_seed_region_v1",
        query_index=index,
        seed=seed,
        addresses=tuple(addresses),
        target_inside_window=target is not None,
        target_value=target.value if target else None,
        structure_counts=_structure_counts(addresses),
    )


def _structure_counts(addresses: Sequence[PrimeAddress]) -> dict[str, int]:
    structures = [nearest_known_structures(address) for address in addresses]
    return {
        "known_primes": len(addresses),
        "wheel_coprime": sum(1 for item in structures if item["wheel_coprime"]),
        "twin_prime": sum(1 for item in structures if item["twin_prime"]),
        "cousin_prime": sum(1 for item in structures if item["cousin_prime"]),
        "sexy_prime": sum(1 for item in structures if item["sexy_prime"]),
        "on_prime_ap": sum(1 for item in structures if item["on_prime_ap"]),
    }


def nearest_known_structures(address: PrimeAddress) -> dict[str, object]:
    """What known (survived) structures does this prime sit in or next to?

    Only FACT / KNOWN_STRUCTURE relations — never a falsified projection.
    """
    return {
        "wheel_lane": address.wheel_lane,
        "wheel_coprime": math.gcd(address.wheel_lane, WHEEL_MODULUS) == 1,
        "twin_prime": address.gap_prev == 2 or address.gap_next == 2,
        "cousin_prime": address.gap_prev == 4 or address.gap_next == 4,
        "sexy_prime": address.gap_prev == 6 or address.gap_next == 6,
        "on_prime_ap": address.ap_length >= 3,
        "ap_length": address.ap_length,
        "ap_difference": address.ap_difference,
        "log_scale": round(address.log_value, 6),
    }


def circular_shift_null(values: Sequence[float], shift: int) -> list[float]:
    """Roll a score in order — preserves run/smoothness structure, breaks alignment.

    This is the count-matched null that killed ratio_graph_resonance; a plain
    value-shuffle is NOT count-matched for a smooth score. Baked in here so the
    atlas cannot report an alignment without the correct null available.
    """
    n = len(values)
    if n == 0:
        return []
    shift %= n
    return list(values[-shift:]) + list(values[:-shift]) if shift else list(values)


def alignment_vs_null(
    signal: Sequence[float],
    target: Sequence[float],
    seeds: int = 200,
    null: str = "circular_shift",
) -> dict[str, object]:
    """Does `signal` align with `target` better than its own null?

    Returns the real |correlation|, the null p95, and the verdict. This is the
    real-vs-hallucinated test, as a first-class atlas operation: a projection is
    only a 'real path' if it clears the null on this object.
    """
    if len(signal) != len(target):
        raise ValueError("signal and target must be the same length")
    n = len(signal)
    if n < 8:
        raise ValueError("need at least 8 points for a meaningful null")
    real = abs(_pearson(signal, target))
    rng = random.Random(20260605)
    null_stats = []
    for _ in range(seeds):
        if null == "circular_shift":
            rolled = circular_shift_null(signal, rng.randrange(1, n))
        elif null == "shuffle":
            rolled = list(signal)
            rng.shuffle(rolled)
        else:
            raise ValueError("null must be 'circular_shift' or 'shuffle'")
        null_stats.append(abs(_pearson(rolled, target)))
    null_stats.sort()
    p95 = null_stats[min(len(null_stats) - 1, int(0.95 * len(null_stats)))]
    return {
        "real": real,
        "null_p95": p95,
        "beats_null": real > p95,
        "null": null,
        "seeds": seeds,
    }


def _pearson(a: Sequence[float], b: Sequence[float]) -> float:
    n = len(a)
    ma = sum(a) / n
    mb = sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = math.sqrt(sum((x - ma) ** 2 for x in a))
    vb = math.sqrt(sum((y - mb) ** 2 for y in b))
    if va == 0 or vb == 0:
        return 0.0
    return cov / (va * vb)


if __name__ == "__main__":
    import json

    atlas = build_prime_atlas(9_999, 3)
    print(json.dumps([a.to_dict() for a in atlas], indent=2, default=list))
    print("\nnearest known structures for p_10000:")
    print(json.dumps(nearest_known_structures(atlas[1]), indent=2))
    print("\nseed region for p_10000:")
    region = build_prime_seed_region(10_000)
    print(json.dumps(region.to_dict()["structure_counts"], indent=2))
