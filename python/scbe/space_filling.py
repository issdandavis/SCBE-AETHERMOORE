"""Reversible bounded space-filling curve primitives.

Morton/Z-order encoding is a bijection between a bounded integer grid and a
single integer when the dimension count and bit width are fixed. It preserves
useful locality, but it does not by itself guarantee logarithmic search; speed
comes from using the 1D order with a hierarchy, index, or pruning rule.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


class SpaceFillingError(ValueError):
    """Raised when a space-filling coordinate packet is invalid."""


@dataclass(frozen=True)
class MortonPoint:
    """Receipt for a bounded Morton/Z-order mapping."""

    schema_version: str
    coords: tuple[int, ...]
    bits: int
    index: int


def _validate_coords(coords: Sequence[int], bits: int) -> tuple[int, ...]:
    if bits <= 0:
        raise SpaceFillingError("bits must be > 0")
    if not coords:
        raise SpaceFillingError("coords must not be empty")
    limit = 1 << bits
    out = tuple(int(value) for value in coords)
    for value in out:
        if value < 0 or value >= limit:
            raise SpaceFillingError(f"coordinate {value} outside [0, {limit})")
    return out


def morton_encode(coords: Sequence[int], *, bits: int) -> int:
    """Interleave coordinate bits into one Morton/Z-order integer."""

    clean = _validate_coords(coords, bits)
    index = 0
    dims = len(clean)
    for bit in range(bits):
        for axis, value in enumerate(clean):
            index |= ((value >> bit) & 1) << (bit * dims + axis)
    return index


def morton_decode(index: int, *, dims: int, bits: int) -> tuple[int, ...]:
    """Decode a Morton/Z-order integer into bounded grid coordinates."""

    if dims <= 0:
        raise SpaceFillingError("dims must be > 0")
    if bits <= 0:
        raise SpaceFillingError("bits must be > 0")
    max_index = 1 << (dims * bits)
    idx = int(index)
    if idx < 0 or idx >= max_index:
        raise SpaceFillingError(f"index {idx} outside [0, {max_index})")
    coords = [0] * dims
    for bit in range(bits):
        for axis in range(dims):
            coords[axis] |= ((idx >> (bit * dims + axis)) & 1) << bit
    return tuple(coords)


def morton_point(coords: Sequence[int], *, bits: int) -> MortonPoint:
    """Encode coordinates and return a reversible receipt."""

    clean = _validate_coords(coords, bits)
    return MortonPoint(
        schema_version="scbe_morton_point_v1",
        coords=clean,
        bits=bits,
        index=morton_encode(clean, bits=bits),
    )


def bits_for_cardinality(cardinality: int) -> int:
    """Smallest bit width able to index ``cardinality`` states per axis."""

    if cardinality <= 1:
        return 1
    return int(math.ceil(math.log2(cardinality)))


def quantize_unit_interval(value: float, *, bits: int) -> int:
    """Quantize a value in [0, 1] into a bounded Morton coordinate."""

    if bits <= 0:
        raise SpaceFillingError("bits must be > 0")
    if not math.isfinite(value):
        raise SpaceFillingError("value must be finite")
    clipped = min(1.0, max(0.0, float(value)))
    limit = (1 << bits) - 1
    return int(round(clipped * limit))


__all__ = [
    "MortonPoint",
    "SpaceFillingError",
    "bits_for_cardinality",
    "morton_decode",
    "morton_encode",
    "morton_point",
    "quantize_unit_interval",
]
