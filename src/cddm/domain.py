"""
Domain — a bounded, typed region in the cross-domain mapping space.

A Domain defines:
  - A name (human-readable label)
  - Units (tuple of unit strings for dimensional analysis)
  - Bounds (min, max inclusive) — the valid range for values
  - An optional dimensionality (for multi-dimensional domains)

Domains are the objects in our category. Morphisms are the arrows.

@module cddm/domain
@version 1.0.0
"""

from __future__ import annotations

from typing import Tuple


class DomainError(Exception):
    """Raised when domain validation fails."""


class Domain:
    """A bounded, typed region for cross-domain mapping.

    Attributes:
        name: Human-readable domain label.
        units: Tuple of unit strings (e.g., ("Joule",), ("Motivation",)).
        bounds: (min, max) inclusive range for scalar values.
        dims: Number of dimensions (1 for scalar domains).
    """

    __slots__ = ("name", "units", "bounds", "dims", "_hash")

    def __init__(
        self,
        name: str,
        units: Tuple[str, ...],
        bounds: Tuple[float, float],
        dims: int = 1,
    ):
        if not name:
            raise DomainError("Domain name cannot be empty")
        if not units:
            raise DomainError("Domain must have at least one unit")
        lo, hi = bounds
        if lo >= hi:
            raise DomainError(f"Lower bound {lo} must be < upper bound {hi}")
        if dims < 1:
            raise DomainError(f"Dimensions must be >= 1, got {dims}")

        self.name = name
        self.units = tuple(units)
        self.bounds = (float(lo), float(hi))
        self.dims = dims
        self._hash = hash((name, self.units, self.bounds, dims))

    def contains(self, value: float) -> bool:
        """Check if a value is within this domain's bounds."""
        return self.bounds[0] <= value <= self.bounds[1]

    def clamp(self, value: float) -> float:
        """Clamp a value to this domain's bounds."""
        return max(self.bounds[0], min(self.bounds[1], value))

    def normalize(self, value: float) -> float:
        """Normalize a value to [0, 1] within this domain's bounds."""
        lo, hi = self.bounds
        span = hi - lo
        if span < 1e-12:
            return 0.5
        return (value - lo) / span

    def denormalize(self, t: float) -> float:
        """Map [0, 1] back to domain bounds."""
        lo, hi = self.bounds
        return lo + t * (hi - lo)

    def span(self) -> float:
        """Width of the domain (hi - lo)."""
        return self.bounds[1] - self.bounds[0]

    def midpoint(self) -> float:
        """Center of the domain."""
        return (self.bounds[0] + self.bounds[1]) / 2.0

    def validate(self, value: float) -> None:
        """Raise DomainError if value is out of bounds."""
        if not self.contains(value):
            raise DomainError(f"Value {value} out of {self.name} bounds [{self.bounds[0]}, {self.bounds[1]}]")

    def compatible(self, other: Domain) -> bool:
        """Check if two domains have the same unit signature."""
        return self.units == other.units

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Domain):
            return NotImplemented
        return (
            self.name == other.name
            and self.units == other.units
            and self.bounds == other.bounds
            and self.dims == other.dims
        )

    def __hash__(self) -> int:
        return self._hash

    def __repr__(self) -> str:
        return f"Domain({self.name!r}, units={self.units}, bounds={self.bounds}, dims={self.dims})"
