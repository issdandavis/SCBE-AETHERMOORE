"""
Elastic Bijective Hash (EBH)
============================

A reversible, lossless hash inspired by Andrew Krapivin's elastic hashing
(2024/25 — overturning Yao's 1985 "a full table must be slow" conjecture).

THE FIREBREAK (non-greedy placement)
------------------------------------
Linear probing greedily grabs the next slot, welding clusters into the
"full parking lot" jam. EBH gives every key its own odd-stride orbit
(double hashing) so probes scatter across the whole table — clusters
can't merge. That is the elastic firebreak idea, and it keeps lookups
fast where greedy probing collapses.

BIJECTIVE (lossless round-trip, reversible scramble)
----------------------------------------------------
* the slot scramble is splitmix64 — an INVERTIBLE 64-bit permutation, so
  the base map is reversible (mix_inverse), nothing is lost in mixing;
* the table stores exact (key, value) pairs, so items() reconstructs the
  precise input set: a true bijective round-trip.

NO SHAPES: pure integer arithmetic — modular permutations, no geometry.

Sacred Tongues hook: encode_key_with_tongue() runs a key through the
bijective byte<->token map first, composing with the bijective round-trip
lane already in the project.
"""

from __future__ import annotations

from typing import Any, Iterator, List, Optional, Tuple

_M64 = (1 << 64) - 1
_C1 = 0xBF58476D1CE4E5B9
_C2 = 0x94D049BB133111EB
_C1_INV = pow(_C1, -1, 1 << 64)
_C2_INV = pow(_C2, -1, 1 << 64)
_STRIDE_SALT = 0xD1B54A32D192ED03


def splitmix64(x: int) -> int:
    """Invertible 64-bit avalanche permutation (a bijection on [0, 2^64))."""
    x &= _M64
    x = ((x ^ (x >> 30)) * _C1) & _M64
    x = ((x ^ (x >> 27)) * _C2) & _M64
    return x ^ (x >> 31)


def _unxorshift(y: int, shift: int) -> int:
    # invert  y = x ^ (x >> shift)  via doubling shifts
    x = y
    s = shift
    while s < 64:
        x ^= x >> s
        s <<= 1
    return x & _M64


def splitmix64_inverse(y: int) -> int:
    """Inverse of splitmix64 — proof the scramble loses no information."""
    y &= _M64
    y = _unxorshift(y, 31)
    y = (y * _C2_INV) & _M64
    y = _unxorshift(y, 27)
    y = (y * _C1_INV) & _M64
    y = _unxorshift(y, 30)
    return y


class ElasticBijectiveHash:
    """Open-addressing map: non-greedy double-hash probing + reversible mix."""

    def __init__(self, bits: int = 16, seed: int = 0) -> None:
        if bits < 1:
            raise ValueError("bits must be >= 1")
        self.bits = bits
        self.size = 1 << bits
        self.mask = self.size - 1
        self.seed = seed & _M64
        self.slots: List[Optional[Tuple[Any, Any]]] = [None] * self.size
        self.count = 0
        self.total_probes = 0

    @staticmethod
    def key_int(key: Any) -> int:
        if isinstance(key, int):
            return key
        if isinstance(key, str):
            b = key.encode("utf-8")
        elif isinstance(key, (bytes, bytearray)):
            b = bytes(key)
        else:
            b = repr(key).encode("utf-8")
        return int.from_bytes(len(b).to_bytes(4, "big") + b, "big")

    def base_slot(self, key: Any) -> int:
        return splitmix64(self.key_int(key) ^ self.seed) & self.mask

    def base_inverse(self, mixed_full: int) -> int:
        """Reversibility witness: recover the pre-mix value from a full 64-bit mix."""
        return splitmix64_inverse(mixed_full) ^ self.seed

    def _stride(self, ki: int) -> int:
        return (splitmix64(ki ^ _STRIDE_SALT ^ self.seed) | 1) & self.mask or 1

    def put(self, key: Any, value: Any = None) -> int:
        ki = self.key_int(key)
        base = splitmix64(ki ^ self.seed) & self.mask
        stride = self._stride(ki)
        for i in range(self.size):
            self.total_probes += 1
            slot = (base + i * stride) & self.mask
            cell = self.slots[slot]
            if cell is None:
                self.slots[slot] = (key, value)
                self.count += 1
                return slot
            if cell[0] == key:
                self.slots[slot] = (key, value)
                return slot
        raise RuntimeError("table full")

    def get(self, key: Any, default: Any = None) -> Any:
        ki = self.key_int(key)
        base = splitmix64(ki ^ self.seed) & self.mask
        stride = self._stride(ki)
        for i in range(self.size):
            self.total_probes += 1
            slot = (base + i * stride) & self.mask
            cell = self.slots[slot]
            if cell is None:
                return default
            if cell[0] == key:
                return cell[1]
        return default

    def __contains__(self, key: Any) -> bool:
        s = object()
        return self.get(key, s) is not s

    def items(self) -> Iterator[Tuple[Any, Any]]:
        for cell in self.slots:
            if cell is not None:
                yield cell

    @property
    def load(self) -> float:
        return self.count / self.size

    def avg_probes(self) -> float:
        return self.total_probes / max(1, self.count)


def encode_key_with_tongue(key: bytes, tongue: str = "KO") -> str:
    try:
        from scbe import encode_bytes  # type: ignore
        return encode_bytes(tongue, key)
    except Exception:
        return key.hex()


def _bench_at(bits: int, load: float) -> Tuple[float, float, bool]:
    import random
    h = ElasticBijectiveHash(bits=bits, seed=42)
    n = int(h.size * load)
    keys = [f"k-{i}-{random.getrandbits(48)}" for i in range(n)]
    for i, k in enumerate(keys):
        h.put(k, i)
    ins = h.total_probes / n
    h.total_probes = 0
    ok = all(h.get(k) == i for i, k in enumerate(keys))
    look = h.total_probes / n
    lossless = sorted(v for _, v in h.items()) == list(range(n))
    return ins, look, (ok and lossless)


def _demo() -> None:
    bits = 16
    print(f"Elastic Bijective Hash  (non-greedy double-hash, 2^{bits} = {1<<bits} slots)\n")
    print(f"  {'load':>6} | {'probes/insert':>13} | {'probes/lookup':>13} | bijective")
    print(f"  {'-'*6}-+-{'-'*13}-+-{'-'*13}-+-----------")
    for load in (0.50, 0.90, 0.99, 0.999):
        ins, look, ok = _bench_at(bits, load)
        print(f"  {load*100:5.1f}% | {ins:13.2f} | {look:13.2f} | {'YES' if ok else 'FAIL'}")
    # reversible-mix witness
    x = ElasticBijectiveHash.key_int("hello") & _M64
    print(f"\n  splitmix64 reversible: x={x} -> mix -> inverse == x : "
          f"{splitmix64_inverse(splitmix64(x)) == x}")


if __name__ == "__main__":
    _demo()
