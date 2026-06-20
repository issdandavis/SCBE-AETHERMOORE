"""Inscription by ratios — represent a value as a compact rational (bounded notation).

A real value is "inscribed" as the best ratio p/q within a denominator bound, and a
continued-fraction expansion gives a ladder of ever-better ratios from very little
information: e.g. pi -> [3; 7, 15, 1, ...] -> 22/7, 333/106, 355/113, where 355/113
already matches pi to ~3e-7 with three tiny integers. Few symbols, high accuracy.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Union

Number = Union[int, float, Fraction]


def continued_fraction(x: Number, max_terms: int = 64) -> List[int]:
    """The continued-fraction terms [a0; a1, a2, ...]. Finite for any rational input."""
    frac = x if isinstance(x, Fraction) else Fraction(x).limit_denominator(10**15)
    terms: List[int] = []
    for _ in range(max_terms):
        whole = frac.numerator // frac.denominator
        terms.append(whole)
        frac -= whole
        if frac == 0:
            break
        frac = 1 / frac
    return terms


def convergents(cf: List[int]) -> List[Fraction]:
    """Successive best-rational approximations p_n/q_n built from CF terms."""
    h_prev, h = 0, 1  # numerators  (h_-2, h_-1)
    k_prev, k = 1, 0  # denominators (k_-2, k_-1)
    out: List[Fraction] = []
    for a in cf:
        h_prev, h = h, a * h + h_prev
        k_prev, k = k, a * k + k_prev
        out.append(Fraction(h, k))
    return out


def inscribe(x: float, max_denominator: int = 10**6) -> Dict[str, object]:
    """Inscribe a real value as the best ratio with denominator <= max_denominator."""
    frac = Fraction(x).limit_denominator(max_denominator)
    return {
        "ratio": (frac.numerator, frac.denominator),
        "value": float(frac),
        "error": abs(float(frac) - x),
        "terms": continued_fraction(frac),
        "max_denominator": max_denominator,
    }


def ladder(x: float, max_terms: int = 12) -> List[Dict[str, object]]:
    """The accuracy ladder: each convergent of x with its error — small info, rising accuracy."""
    cf = continued_fraction(x, max_terms=max_terms)
    rungs: List[Dict[str, object]] = []
    for c in convergents(cf):
        rungs.append({"ratio": (c.numerator, c.denominator), "value": float(c), "error": abs(float(c) - x)})
    return rungs
