"""Extrapolation from small information to high accuracy, with bounded notation.

Given a few exact samples of a polynomial relationship, reconstruct the whole
polynomial *exactly* (Newton divided differences over rationals) and predict any
far point with zero error. The "bounded notation" is the short coefficient list:
n points pin down a degree < n polynomial, so a handful of samples extrapolate
perfectly. (1-D today; the same divided-difference scheme extends to tensor-product
multi-dimensional grids — see the README — but that is not built here.)
"""

from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence, Tuple, Union

Number = Union[int, float, Fraction]
Point = Tuple[Number, Number]


def fit_polynomial(points: Sequence[Point]) -> List[Fraction]:
    """Exact ascending coefficients [c0, c1, ...] of the minimal-degree polynomial
    through `points` (x values must be distinct)."""
    pts = list(points)
    if not pts:
        raise ValueError("need at least one point")
    xs = [Fraction(x) for x, _ in pts]
    if len(set(xs)) != len(xs):
        raise ValueError("x values must be distinct")

    coef = [Fraction(y) for _, y in pts]  # Newton divided differences, in place
    n = len(pts)
    for j in range(1, n):
        for i in range(n - 1, j - 1, -1):
            coef[i] = (coef[i] - coef[i - 1]) / (xs[i] - xs[i - j])

    poly: List[Fraction] = [Fraction(0)]  # standard form, ascending
    basis: List[Fraction] = [Fraction(1)]  # running product (x - x0)(x - x1)...
    for k in range(n):
        for d, c in enumerate(basis):
            if d < len(poly):
                poly[d] += coef[k] * c
            else:
                poly.append(coef[k] * c)
        if k < n - 1:  # basis *= (x - xs[k])
            nxt = [Fraction(0)] * (len(basis) + 1)
            for d, c in enumerate(basis):
                nxt[d] += c * (-xs[k])
                nxt[d + 1] += c
            basis = nxt
    return poly


def evaluate(coeffs: Sequence[Fraction], x: Number) -> Fraction:
    """Evaluate a polynomial (ascending coeffs) at x, exactly, via Horner's method."""
    acc = Fraction(0)
    for c in reversed(list(coeffs)):
        acc = acc * Fraction(x) + c
    return acc


def extrapolate(points: Sequence[Point], at: Union[Number, Sequence[Number]]):
    """Fit the minimal polynomial through `points` and predict at one or many x."""
    coeffs = fit_polynomial(points)
    if isinstance(at, (list, tuple)):
        return [evaluate(coeffs, x) for x in at]
    return evaluate(coeffs, at)


def reconstruction_error(train: Sequence[Point], test: Sequence[Point]) -> float:
    """Fit on `train`, predict `test` x's, return the max abs error (0 for polynomial data)."""
    coeffs = fit_polynomial(train)
    return max((abs(float(evaluate(coeffs, x)) - float(y)) for x, y in test), default=0.0)
