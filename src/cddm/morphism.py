"""
Morphism — a structure-preserving map between Domains.

A Morphism maps values from a source Domain to a destination Domain
via a callable function, with automatic bounds validation on both ends.

Morphisms are the arrows in our category. They can be:
  - Composed (A->B then B->C = A->C)
  - Inverted (if an inverse function is provided)
  - Validated against constraints

@module cddm/morphism
@version 1.0.0
"""

from __future__ import annotations

import math
from typing import Callable, List, Optional, Tuple

from .domain import Domain, DomainError


class MorphismError(Exception):
    """Raised when morphism application or validation fails."""
    pass


class Morphism:
    """A structure-preserving map between two Domains.

    Attributes:
        src: Source domain.
        dst: Destination domain.
        func: Callable mapping src values to dst values.
        name: Optional human-readable label.
        inverse_func: Optional inverse for bidirectional mapping.
        constraints: Optional list of (label, predicate) pairs.
    """

    __slots__ = ("src", "dst", "func", "name", "inverse_func", "constraints")

    def __init__(
        self,
        src: Domain,
        dst: Domain,
        func: Callable[[float], float],
        name: Optional[str] = None,
        inverse_func: Optional[Callable[[float], float]] = None,
        constraints: Optional[List[Tuple[str, Callable[[float, float], bool]]]] = None,
    ):
        self.src = src
        self.dst = dst
        self.func = func
        self.name = name or f"{src.name}->{dst.name}"
        self.inverse_func = inverse_func
        self.constraints = constraints or []

    def __call__(self, x: float) -> float:
        """Apply the morphism: validate src, transform, validate dst."""
        if not self.src.contains(x):
            raise MorphismError(
                f"Input {x} out of {self.src.name} bounds "
                f"[{self.src.bounds[0]}, {self.src.bounds[1]}]"
            )
        y = self.func(x)
        if not self.dst.contains(y):
            raise MorphismError(
                f"Output {y} out of {self.dst.name} bounds "
                f"[{self.dst.bounds[0]}, {self.dst.bounds[1]}] "
                f"(input was {x} in {self.src.name})"
            )
        # Check constraints
        for label, pred in self.constraints:
            if not pred(x, y):
                raise MorphismError(f"Constraint '{label}' violated: f({x}) = {y}")
        return y

    def safe_call(self, x: float) -> Tuple[bool, float]:
        """Apply morphism, returning (success, value) without raising."""
        try:
            return True, self(x)
        except (MorphismError, DomainError, ValueError, ZeroDivisionError):
            return False, 0.0

    def invert(self) -> Morphism:
        """Return the inverse morphism (dst->src) if invertible."""
        if self.inverse_func is None:
            raise MorphismError(f"Morphism {self.name!r} has no inverse")
        return Morphism(
            src=self.dst,
            dst=self.src,
            func=self.inverse_func,
            name=f"inv({self.name})",
            inverse_func=self.func,
        )

    @property
    def invertible(self) -> bool:
        return self.inverse_func is not None

    def validate_roundtrip(self, x: float, tol: float = 1e-6) -> bool:
        """Check that invert(f(x)) ≈ x within tolerance."""
        if not self.invertible:
            return False
        try:
            y = self(x)
            x_back = self.invert()(y)
            return abs(x_back - x) < tol
        except (MorphismError, DomainError):
            return False

    def compose_with(self, other: Morphism) -> Morphism:
        """Compose self then other: (other ∘ self)(x) = other(self(x)).

        Requires self.dst == other.src (or compatible bounds overlap).
        """
        if self.dst != other.src:
            # Allow if bounds overlap sufficiently
            if self.dst.name != other.src.name:
                raise MorphismError(
                    f"Cannot compose: {self.name} dst={self.dst.name} "
                    f"!= {other.name} src={other.src.name}"
                )

        f1, f2 = self.func, other.func
        composed_func = lambda x: f2(f1(x))

        inv = None
        if self.invertible and other.invertible:
            g1, g2 = self.inverse_func, other.inverse_func
            inv = lambda y: g1(g2(y))

        return Morphism(
            src=self.src,
            dst=other.dst,
            func=composed_func,
            name=f"({other.name} ∘ {self.name})",
            inverse_func=inv,
        )

    def __repr__(self) -> str:
        inv_tag = " [invertible]" if self.invertible else ""
        return f"Morphism({self.name!r}: {self.src.name} -> {self.dst.name}{inv_tag})"
