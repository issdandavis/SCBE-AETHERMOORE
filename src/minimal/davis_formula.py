"""Reference implementation of the Davis security score.

S(t, i, C, d) = t / (i * C! * (1 + d))

Interpretation used here:
- t: time budget / dwell time contribution, must be > 0
- i: intent intensity / adversarial pressure divisor, must be > 0
- C: count of context dimensions, must be an integer >= 0
- d: drift from safe baseline, must be >= 0

This module keeps the formula small and testable before it is wired into any
larger governance path.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class DavisFormulaInputs:
    time_budget: float
    intent_intensity: float
    context_dimensions: int
    drift: float


def davis_security_score(
    time_budget: float,
    intent_intensity: float,
    context_dimensions: int,
    drift: float,
) -> float:
    """Compute the Davis security score.

    Raises:
        ValueError: If the inputs violate the reference domain assumptions.
    """
    if time_budget <= 0:
        raise ValueError("time_budget must be > 0")
    if intent_intensity <= 0:
        raise ValueError("intent_intensity must be > 0")
    if context_dimensions < 0:
        raise ValueError("context_dimensions must be >= 0")
    if drift < 0:
        raise ValueError("drift must be >= 0")

    context_factor = math.factorial(context_dimensions)
    return time_budget / (intent_intensity * context_factor * (1.0 + drift))


def davis_security_score_from_inputs(inputs: DavisFormulaInputs) -> float:
    """Convenience wrapper for dataclass-based call sites."""
    return davis_security_score(
        time_budget=inputs.time_budget,
        intent_intensity=inputs.intent_intensity,
        context_dimensions=inputs.context_dimensions,
        drift=inputs.drift,
    )
