"""Bit-level GeoSeed dressing with a prime-basis chunk bridge.

This is a deterministic constructor, not a trained neural model. It turns raw
bits into small geometric records that carry the same axes the GeoSeed design
uses: six tongue slots, Cl(6,0) basis blades, Poincare-ball position, spectral
phase, temporal position, governance stamp, and an audio frequency.

The prime research is used as a sparse chunk basis: the six tongue positions map
to the first six prime layers (2, 3, 5, 7, 11, 13). Composition can then emit an
abacus-compatible prime layer for agent math.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Literal, Sequence

from src.geoseed.prime_seed_init import DEFAULT_M6_LAYER_PRIMES, PHI, TONGUE_ABBRS

CL60_COMPONENTS = 64
SCHEMA_VERSION = "geoseed_dressed_bit_v1"


@dataclass(frozen=True)
class DressedBit:
    """One raw bit after deterministic GeoSeed dressing."""

    schema_version: str
    index: int
    bit: int
    tongue_index: int
    tongue_abbr: str
    layer_prime: int
    prime_residue: int
    prime_phase: float
    clifford_multivector: tuple[float, ...]
    poincare: tuple[float, float, float]
    hyperbolic_rho: float
    spectral_modes: tuple[float, float, float]
    temporal_signature: tuple[int, int, float]
    governance_stamp: str
    audio_frequency_hz: float
    fingerprint: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["clifford_multivector"] = list(self.clifford_multivector)
        payload["poincare"] = list(self.poincare)
        payload["spectral_modes"] = list(self.spectral_modes)
        payload["temporal_signature"] = list(self.temporal_signature)
        return payload


@dataclass(frozen=True)
class DressedBitComposition:
    """Aggregate surface for a run of dressed bits."""

    schema_version: str
    bit_count: int
    one_count: int
    zero_count: int
    tongue_counts: dict[str, int]
    prime_one_counts: dict[str, int]
    prime_weighted_total: int
    mean_hyperbolic_rho: float
    fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def dress_bit(bit: int, index: int) -> DressedBit:
    """Dress one bit into the six-seed geometric address space."""
    if bit not in (0, 1):
        raise ValueError("bit must be 0 or 1")
    if index < 0:
        raise ValueError("index must be non-negative")

    tongue_index = index % len(TONGUE_ABBRS)
    tongue_abbr = TONGUE_ABBRS[tongue_index]
    layer_prime = DEFAULT_M6_LAYER_PRIMES[tongue_index]
    address = index + 1
    prime_residue = address % layer_prime
    prime_phase = (2.0 * math.pi * prime_residue) / layer_prime
    bit_sign = 1.0 if bit else -1.0

    multivector = _clifford_multivector(
        bit_sign=bit_sign,
        tongue_index=tongue_index,
        layer_prime=layer_prime,
        prime_residue=prime_residue,
    )
    rho = _hyperbolic_rho(tongue_index, layer_prime, prime_residue, bit)
    poincare = _poincare_point(rho, prime_phase, bit_sign)
    spectral_modes = (
        round(math.cos(prime_phase), 12),
        round(math.sin(prime_phase), 12),
        round(bit_sign * (prime_residue + 1) / layer_prime, 12),
    )
    temporal_signature = (
        index // len(TONGUE_ABBRS),
        tongue_index,
        round(math.sin((address * math.pi) / len(TONGUE_ABBRS)), 12),
    )
    audio_frequency_hz = round(440.0 * (PHI**tongue_index), 6)
    fingerprint = _fingerprint(
        {
            "schema": SCHEMA_VERSION,
            "index": index,
            "bit": bit,
            "tongue": tongue_abbr,
            "layer_prime": layer_prime,
            "prime_residue": prime_residue,
            "poincare": poincare,
            "spectral_modes": spectral_modes,
            "temporal_signature": temporal_signature,
        }
    )

    return DressedBit(
        schema_version=SCHEMA_VERSION,
        index=index,
        bit=bit,
        tongue_index=tongue_index,
        tongue_abbr=tongue_abbr,
        layer_prime=layer_prime,
        prime_residue=prime_residue,
        prime_phase=round(prime_phase, 12),
        clifford_multivector=multivector,
        poincare=poincare,
        hyperbolic_rho=round(rho, 12),
        spectral_modes=spectral_modes,
        temporal_signature=temporal_signature,
        governance_stamp="ALLOW",
        audio_frequency_hz=audio_frequency_hz,
        fingerprint=fingerprint,
    )


def bits_from_bytes(
    data: bytes, bit_order: Literal["msb", "lsb"] = "msb"
) -> tuple[int, ...]:
    """Expand bytes into bits with a declared bit order."""
    if bit_order not in ("msb", "lsb"):
        raise ValueError("bit_order must be 'msb' or 'lsb'")
    shifts = range(7, -1, -1) if bit_order == "msb" else range(8)
    return tuple((byte >> shift) & 1 for byte in data for shift in shifts)


def dress_bytes(
    data: bytes, bit_order: Literal["msb", "lsb"] = "msb"
) -> tuple[DressedBit, ...]:
    """Dress every bit in a byte string."""
    return tuple(
        dress_bit(bit, index)
        for index, bit in enumerate(bits_from_bytes(data, bit_order))
    )


def compose_dressed_bits(bits: Sequence[DressedBit]) -> DressedBitComposition:
    """Compress dressed bits into a stable composition summary."""
    if not bits:
        raise ValueError("at least one dressed bit is required")

    tongue_counts = {abbr: 0 for abbr in TONGUE_ABBRS}
    prime_one_counts = {f"p{prime}": 0 for prime in DEFAULT_M6_LAYER_PRIMES}
    one_count = 0
    for dressed in bits:
        tongue_counts[dressed.tongue_abbr] += 1
        if dressed.bit == 1:
            one_count += 1
            prime_one_counts[f"p{dressed.layer_prime}"] += 1

    prime_weighted_total = sum(
        int(key[1:]) * count for key, count in prime_one_counts.items()
    )
    mean_rho = sum(dressed.hyperbolic_rho for dressed in bits) / len(bits)
    fingerprint = _fingerprint(
        {
            "schema": "geoseed_dressed_bit_composition_v1",
            "bit_count": len(bits),
            "one_count": one_count,
            "tongue_counts": tongue_counts,
            "prime_one_counts": prime_one_counts,
            "prime_weighted_total": prime_weighted_total,
            "bit_fingerprints": [dressed.fingerprint for dressed in bits],
        }
    )
    return DressedBitComposition(
        schema_version="geoseed_dressed_bit_composition_v1",
        bit_count=len(bits),
        one_count=one_count,
        zero_count=len(bits) - one_count,
        tongue_counts=tongue_counts,
        prime_one_counts=prime_one_counts,
        prime_weighted_total=prime_weighted_total,
        mean_hyperbolic_rho=round(mean_rho, 12),
        fingerprint=fingerprint,
    )


def build_prime_abacus_layer(
    bits: Sequence[DressedBit],
    layer_id: str = "geoseed-prime",
    name: str = "GeoSeed Prime Bit Chunks",
) -> dict[str, object]:
    """Return a Polly Pad compatible abacus layer from dressed bit composition."""
    composition = compose_dressed_bits(bits)
    return {
        "id": layer_id,
        "name": name,
        "rows": [
            {
                "id": key,
                "label": f"prime {key[1:]} one-bits",
                "value": int(key[1:]),
                "count": count,
                "maxCount": max(12, count),
            }
            for key, count in composition.prime_one_counts.items()
        ],
    }


def _clifford_multivector(
    bit_sign: float,
    tongue_index: int,
    layer_prime: int,
    prime_residue: int,
) -> tuple[float, ...]:
    components = [0.0] * CL60_COMPONENTS
    vector_mask = 1 << tongue_index
    neighbor_mask = 1 << ((tongue_index + 1) % len(TONGUE_ABBRS))
    bivector_mask = vector_mask | neighbor_mask
    pseudoscalar_mask = (1 << len(TONGUE_ABBRS)) - 1

    components[0] = 1.0
    components[vector_mask] = round(bit_sign * (PHI**tongue_index), 12)
    components[bivector_mask] = round(bit_sign * (prime_residue + 1) / layer_prime, 12)
    components[pseudoscalar_mask] = round(bit_sign / layer_prime, 12)
    return tuple(components)


def _hyperbolic_rho(
    tongue_index: int, layer_prime: int, prime_residue: int, bit: int
) -> float:
    base = tongue_index * math.log(PHI)
    residue_lift = ((prime_residue + 1) / layer_prime) * math.log(PHI)
    bit_lift = 0.5 * math.log(PHI) if bit else 0.0
    return base + residue_lift + bit_lift


def _poincare_point(
    rho: float, phase: float, bit_sign: float
) -> tuple[float, float, float]:
    radius = math.tanh(rho / 2.0)
    z_fraction = 0.35 * bit_sign
    planar_radius = radius * math.sqrt(1.0 - z_fraction * z_fraction)
    return (
        round(planar_radius * math.cos(phase), 12),
        round(planar_radius * math.sin(phase), 12),
        round(radius * z_fraction, 12),
    )


def _fingerprint(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "CL60_COMPONENTS",
    "DressedBit",
    "DressedBitComposition",
    "build_prime_abacus_layer",
    "bits_from_bytes",
    "compose_dressed_bits",
    "dress_bit",
    "dress_bytes",
]


if __name__ == "__main__":
    dressed = dress_bytes(b"\xa6")
    print(json.dumps(compose_dressed_bits(dressed).to_dict(), indent=2))
