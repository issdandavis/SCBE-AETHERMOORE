"""Quasi-integer recoupling utilities.

This module bridges continuous or fractional values back into auditable
integer-like symbolic states without pretending the approximation is exact.
Examples include partial charges, fractional/aromatic bond orders, model
confidence scores, and manifold coordinates that need to be packetized as
discrete states.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import isfinite
from typing import Any, Literal

RecouplingDecision = Literal["RECOUPLED", "AMBIGUOUS", "OUT_OF_RANGE", "INVALID"]


@dataclass(frozen=True, slots=True)
class RecouplingState:
    """A named discrete state available to the recoupler."""

    value: float
    label: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class QuasiIntegerRecoupling:
    """Result of snapping a continuous value to a declared discrete state."""

    raw_value: float
    recoupled_value: float | None
    label: str | None
    error: float | None
    tolerance: float
    confidence: float
    decision: RecouplingDecision
    reason: str
    state_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.decision == "RECOUPLED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def integer_states(min_value: int, max_value: int) -> list[RecouplingState]:
    if min_value > max_value:
        raise ValueError("min_value must be <= max_value")
    return [RecouplingState(float(value), str(value)) for value in range(min_value, max_value + 1)]


def half_integer_states(min_value: int, max_value: int) -> list[RecouplingState]:
    if min_value > max_value:
        raise ValueError("min_value must be <= max_value")
    states: list[RecouplingState] = []
    current = min_value * 2
    final = max_value * 2
    while current <= final:
        value = current / 2
        states.append(RecouplingState(float(value), f"{value:g}"))
        current += 1
    return states


CHEMICAL_BOND_ORDER_STATES: tuple[RecouplingState, ...] = (
    RecouplingState(0.0, "no-bond"),
    RecouplingState(1.0, "single-bond-like"),
    RecouplingState(1.5, "aromatic-or-resonance-like"),
    RecouplingState(2.0, "double-bond-like"),
    RecouplingState(3.0, "triple-bond-like"),
)

FORMAL_CHARGE_STATES: tuple[RecouplingState, ...] = tuple(integer_states(-4, 4))


def recouple_to_states(
    raw_value: float,
    states: list[RecouplingState] | tuple[RecouplingState, ...],
    *,
    tolerance: float,
    tie_tolerance: float = 1e-12,
) -> QuasiIntegerRecoupling:
    """Snap raw_value to the nearest declared state with error accounting."""

    if not isfinite(raw_value):
        return QuasiIntegerRecoupling(
            raw_value=raw_value,
            recoupled_value=None,
            label=None,
            error=None,
            tolerance=tolerance,
            confidence=0.0,
            decision="INVALID",
            reason="raw value is not finite",
        )
    if tolerance < 0:
        raise ValueError("tolerance must be >= 0")
    if not states:
        raise ValueError("states must not be empty")

    ranked = sorted(
        ((abs(raw_value - state.value), state) for state in states),
        key=lambda item: (item[0], item[1].value, item[1].label),
    )
    best_error, best_state = ranked[0]
    tied = [state for error, state in ranked if abs(error - best_error) <= tie_tolerance]
    if len(tied) > 1:
        return QuasiIntegerRecoupling(
            raw_value=raw_value,
            recoupled_value=None,
            label=None,
            error=best_error,
            tolerance=tolerance,
            confidence=0.0,
            decision="AMBIGUOUS",
            reason="raw value is equidistant between multiple states",
        )
    if best_error > tolerance:
        return QuasiIntegerRecoupling(
            raw_value=raw_value,
            recoupled_value=best_state.value,
            label=best_state.label,
            error=best_error,
            tolerance=tolerance,
            confidence=0.0,
            decision="OUT_OF_RANGE",
            reason="nearest state exceeds tolerance",
            state_metadata=dict(best_state.metadata),
        )
    confidence = 1.0 if tolerance == 0 else max(0.0, 1.0 - best_error / tolerance)
    return QuasiIntegerRecoupling(
        raw_value=raw_value,
        recoupled_value=best_state.value,
        label=best_state.label,
        error=best_error,
        tolerance=tolerance,
        confidence=confidence,
        decision="RECOUPLED",
        reason="nearest state within tolerance",
        state_metadata=dict(best_state.metadata),
    )


def recouple_to_integer(
    raw_value: float,
    *,
    min_value: int,
    max_value: int,
    tolerance: float,
) -> QuasiIntegerRecoupling:
    return recouple_to_states(
        raw_value,
        integer_states(min_value, max_value),
        tolerance=tolerance,
    )


def recouple_bond_order(
    raw_value: float,
    *,
    tolerance: float = 0.2,
) -> QuasiIntegerRecoupling:
    return recouple_to_states(
        raw_value,
        CHEMICAL_BOND_ORDER_STATES,
        tolerance=tolerance,
    )


def recouple_formal_charge(
    raw_value: float,
    *,
    tolerance: float = 0.25,
) -> QuasiIntegerRecoupling:
    return recouple_to_states(
        raw_value,
        FORMAL_CHARGE_STATES,
        tolerance=tolerance,
    )
