from __future__ import annotations

import math

import pytest

from python.scbe.quasi_integer_recoupling import (
    RecouplingState,
    half_integer_states,
    integer_states,
    recouple_bond_order,
    recouple_formal_charge,
    recouple_to_integer,
    recouple_to_states,
)


def test_integer_recoupling_preserves_error_and_confidence() -> None:
    result = recouple_to_integer(1.92, min_value=0, max_value=4, tolerance=0.25)

    assert result.ok is True
    assert result.recoupled_value == 2.0
    assert result.label == "2"
    assert result.error == pytest.approx(0.08)
    assert 0.67 < result.confidence < 0.69


def test_integer_recoupling_out_of_range_keeps_nearest_state() -> None:
    result = recouple_to_integer(1.62, min_value=0, max_value=4, tolerance=0.1)

    assert result.ok is False
    assert result.decision == "OUT_OF_RANGE"
    assert result.recoupled_value == 2.0
    assert result.error == pytest.approx(0.38)
    assert result.confidence == 0.0


def test_half_integer_ladder_supports_aromatic_like_values() -> None:
    states = half_integer_states(0, 3)
    result = recouple_to_states(1.49, states, tolerance=0.08)

    assert result.ok is True
    assert result.recoupled_value == 1.5
    assert result.label == "1.5"


def test_bond_order_preset_recouples_aromatic_state() -> None:
    result = recouple_bond_order(1.48, tolerance=0.1)

    assert result.ok is True
    assert result.recoupled_value == 1.5
    assert result.label == "aromatic-or-resonance-like"


def test_formal_charge_preset_recouples_integer_charge() -> None:
    result = recouple_formal_charge(-0.91, tolerance=0.2)

    assert result.ok is True
    assert result.recoupled_value == -1.0
    assert result.label == "-1"


def test_equidistant_value_is_ambiguous() -> None:
    result = recouple_to_states(
        0.5,
        [RecouplingState(0.0, "zero"), RecouplingState(1.0, "one")],
        tolerance=0.6,
    )

    assert result.ok is False
    assert result.decision == "AMBIGUOUS"
    assert result.recoupled_value is None


def test_non_finite_value_is_invalid() -> None:
    result = recouple_to_integer(math.nan, min_value=-1, max_value=1, tolerance=0.1)

    assert result.ok is False
    assert result.decision == "INVALID"
    assert result.error is None


def test_state_validation() -> None:
    with pytest.raises(ValueError, match="states must not be empty"):
        recouple_to_states(1.0, [], tolerance=0.1)
    with pytest.raises(ValueError, match="min_value"):
        integer_states(2, 1)
