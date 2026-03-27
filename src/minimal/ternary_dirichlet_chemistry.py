"""Experimental ternary Dirichlet harness with chemistry-style equilibrium proxies.

This module is intentionally narrow. It does not claim to prove the
Riemann Hypothesis or preserve the classical functional equation.

It provides:
- a ternary selector over positive / neutral / negative channels
- a rock-paper-scissors phase cycle via cubic roots of unity
- finite Dirichlet partial sums for exploration
- a chemistry-style equilibrium model based on chemical potentials

The chemistry model is a toy free-energy construction:
- positive and negative channels are treated as activities
- equilibrium is the point where their chemical potentials match
- in the symmetric case, the equilibrium sits at sigma = 1/2
"""

from __future__ import annotations

import cmath
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class TernaryActivities:
    """Mass-action style activities for the three ternary channels."""

    positive: float
    neutral: float
    negative: float

    @property
    def total(self) -> float:
        return self.positive + self.neutral + self.negative


def mod3_ternary_selector(n: int) -> int:
    """Map integers onto a simple ternary selector in {-1, 0, 1}."""
    if n <= 0:
        raise ValueError("n must be positive")

    residue = n % 3
    if residue == 0:
        return 1
    if residue == 1:
        return 0
    return -1


def rps_phase(n: int) -> complex:
    """Return the cubic root of unity used for the RPS-style phase cycle."""
    if n <= 0:
        raise ValueError("n must be positive")

    return cmath.exp(1j * 2.0 * math.pi * (n % 3) / 3.0)


def ternary_dirichlet_partial_sum(
    sigma: float,
    tau: float,
    terms: int,
    selector: callable = mod3_ternary_selector,
) -> complex:
    """Compute a finite ternary-weighted Dirichlet partial sum.

    F(s) = sum_{n<=N} u_n * omega_n / n^s
    where u_n in {-1, 0, 1} and omega_n is a unit-modulus phase.
    """
    if terms <= 0:
        raise ValueError("terms must be positive")

    s = complex(sigma, tau)
    total = 0j
    for n in range(1, terms + 1):
        total += selector(n) * rps_phase(n) / (n**s)
    return total


def activities_from_selector(
    sigma: float,
    terms: int,
    selector: callable = mod3_ternary_selector,
) -> TernaryActivities:
    """Project a finite ternary selector into chemistry-style activities."""
    if terms <= 0:
        raise ValueError("terms must be positive")

    positive = 0.0
    neutral = 0.0
    negative = 0.0

    for n in range(1, terms + 1):
        activity = n ** (-sigma)
        state = selector(n)
        if state > 0:
            positive += activity
        elif state < 0:
            negative += activity
        else:
            neutral += activity

    return TernaryActivities(positive=positive, neutral=neutral, negative=negative)


def chemical_potential_gap(
    sigma: float,
    activities: TernaryActivities,
    coupling: float = 1.0,
) -> float:
    """Difference between positive and negative chemical potentials.

    mu_plus  = ln(a_plus)  + coupling * (sigma - 1/2)
    mu_minus = ln(a_minus) - coupling * (sigma - 1/2)
    gap = mu_plus - mu_minus
    """
    if activities.positive <= 0.0 or activities.negative <= 0.0:
        raise ValueError("positive and negative activities must be > 0")
    if coupling <= 0.0:
        raise ValueError("coupling must be > 0")

    mu_plus = math.log(activities.positive) + coupling * (sigma - 0.5)
    mu_minus = math.log(activities.negative) - coupling * (sigma - 0.5)
    return mu_plus - mu_minus


def equilibrium_sigma(activities: TernaryActivities, coupling: float = 1.0) -> float:
    """Solve for the sigma where the two chemical potentials match."""
    if activities.positive <= 0.0 or activities.negative <= 0.0:
        raise ValueError("positive and negative activities must be > 0")
    if coupling <= 0.0:
        raise ValueError("coupling must be > 0")

    return 0.5 + math.log(activities.negative / activities.positive) / (2.0 * coupling)


def free_energy(
    sigma: float,
    activities: TernaryActivities,
    coupling: float = 1.0,
) -> float:
    """Quadratic free-energy proxy derived from the chemical-potential gap."""
    gap = chemical_potential_gap(sigma=sigma, activities=activities, coupling=coupling)
    return 0.5 * gap * gap

