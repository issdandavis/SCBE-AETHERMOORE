import math

import pytest

from src.minimal.davis_formula import (
    DavisFormulaInputs,
    davis_security_score,
    davis_security_score_from_inputs,
)


def test_davis_formula_matches_reference_value() -> None:
    score = davis_security_score(
        time_budget=10.0,
        intent_intensity=2.0,
        context_dimensions=3,
        drift=1.0,
    )
    assert score == pytest.approx(10.0 / (2.0 * math.factorial(3) * 2.0))


def test_more_context_dimensions_reduce_score_factorially() -> None:
    score_c3 = davis_security_score(12.0, 1.0, 3, 0.0)
    score_c4 = davis_security_score(12.0, 1.0, 4, 0.0)
    assert score_c4 == pytest.approx(score_c3 / 4.0)


def test_more_drift_and_more_intent_reduce_score() -> None:
    baseline = davis_security_score(12.0, 1.0, 2, 0.0)
    higher_drift = davis_security_score(12.0, 1.0, 2, 2.0)
    higher_intent = davis_security_score(12.0, 3.0, 2, 0.0)
    assert higher_drift < baseline
    assert higher_intent < baseline


def test_more_time_increases_score() -> None:
    short = davis_security_score(6.0, 2.0, 2, 1.0)
    long = davis_security_score(12.0, 2.0, 2, 1.0)
    assert long > short


def test_dataclass_wrapper_matches_direct_call() -> None:
    inputs = DavisFormulaInputs(
        time_budget=9.0,
        intent_intensity=1.5,
        context_dimensions=4,
        drift=0.25,
    )
    assert davis_security_score_from_inputs(inputs) == pytest.approx(davis_security_score(9.0, 1.5, 4, 0.25))


@pytest.mark.parametrize(
    ("time_budget", "intent_intensity", "context_dimensions", "drift"),
    [
        (0.0, 1.0, 0, 0.0),
        (1.0, 0.0, 0, 0.0),
        (1.0, 1.0, -1, 0.0),
        (1.0, 1.0, 0, -0.1),
    ],
)
def test_invalid_inputs_raise_value_error(
    time_budget: float,
    intent_intensity: float,
    context_dimensions: int,
    drift: float,
) -> None:
    with pytest.raises(ValueError):
        davis_security_score(time_budget, intent_intensity, context_dimensions, drift)
