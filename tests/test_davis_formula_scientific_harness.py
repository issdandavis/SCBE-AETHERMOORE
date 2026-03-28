"""Scientific-style behavioral harness for the Davis Formula.

This suite treats the formula like a small experimental system:
- 5 probe families
- 3 control anchors
- bidirectional sweeps around a baseline

The goal is not just "does the function return a number",
but "does it behave predictably under controlled variation?"
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pytest

from src.minimal.davis_formula import DavisFormulaInputs, davis_security_score


@dataclass(frozen=True)
class ControlCase:
    name: str
    inputs: DavisFormulaInputs


BASELINE = ControlCase(
    name="baseline",
    inputs=DavisFormulaInputs(
        time_budget=12.0,
        intent_intensity=2.0,
        context_dimensions=3,
        drift=1.0,
    ),
)

FAVORABLE = ControlCase(
    name="favorable",
    inputs=DavisFormulaInputs(
        time_budget=18.0,
        intent_intensity=1.0,
        context_dimensions=2,
        drift=0.25,
    ),
)

ADVERSE = ControlCase(
    name="adverse",
    inputs=DavisFormulaInputs(
        time_budget=6.0,
        intent_intensity=4.0,
        context_dimensions=5,
        drift=2.5,
    ),
)

CONTROLS = (BASELINE, FAVORABLE, ADVERSE)
DRIFT_DELTAS = (-0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75)
TIME_SCALES = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)
INTENT_SCALES = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)


def _score(inputs: DavisFormulaInputs) -> float:
    return davis_security_score(
        time_budget=inputs.time_budget,
        intent_intensity=inputs.intent_intensity,
        context_dimensions=inputs.context_dimensions,
        drift=inputs.drift,
    )


def _replace(
    inputs: DavisFormulaInputs,
    *,
    time_budget: float | None = None,
    intent_intensity: float | None = None,
    context_dimensions: int | None = None,
    drift: float | None = None,
) -> DavisFormulaInputs:
    return DavisFormulaInputs(
        time_budget=inputs.time_budget if time_budget is None else time_budget,
        intent_intensity=(inputs.intent_intensity if intent_intensity is None else intent_intensity),
        context_dimensions=(inputs.context_dimensions if context_dimensions is None else context_dimensions),
        drift=inputs.drift if drift is None else drift,
    )


class TestControlAnchors:
    def test_control_order_matches_security_expectation(self) -> None:
        baseline = _score(BASELINE.inputs)
        favorable = _score(FAVORABLE.inputs)
        adverse = _score(ADVERSE.inputs)

        assert favorable > baseline > adverse

    def test_control_values_stay_positive(self) -> None:
        for control in CONTROLS:
            assert _score(control.inputs) > 0.0


class TestProbeReferenceIdentity:
    def test_reference_identity_holds_for_all_controls(self) -> None:
        for control in CONTROLS:
            inputs = control.inputs
            expected = inputs.time_budget / (
                inputs.intent_intensity * math.factorial(inputs.context_dimensions) * (1.0 + inputs.drift)
            )
            assert _score(inputs) == pytest.approx(expected)


class TestProbeTimeSweep:
    def test_time_sweep_is_monotone_for_all_controls(self) -> None:
        for control in CONTROLS:
            scores = [
                _score(_replace(control.inputs, time_budget=control.inputs.time_budget * scale))
                for scale in TIME_SCALES
            ]
            assert scores == sorted(scores)


class TestProbeIntentSweep:
    def test_intent_sweep_is_inverse_monotone_for_all_controls(self) -> None:
        for control in CONTROLS:
            scores = [
                _score(
                    _replace(
                        control.inputs,
                        intent_intensity=control.inputs.intent_intensity * scale,
                    )
                )
                for scale in INTENT_SCALES
            ]
            assert scores == sorted(scores, reverse=True)


class TestProbeContextFactorialSweep:
    def test_context_dimension_step_matches_factorial_ratio(self) -> None:
        for control in CONTROLS:
            start = max(0, control.inputs.context_dimensions - 1)
            for context_dimensions in range(start, start + 4):
                current = _score(_replace(control.inputs, context_dimensions=context_dimensions))
                next_score = _score(_replace(control.inputs, context_dimensions=context_dimensions + 1))
                assert next_score == pytest.approx(current / (context_dimensions + 1))


class TestProbeDriftBidirectionalCycles:
    def test_drift_cycles_around_baseline_are_symmetric_in_direction(self) -> None:
        baseline = BASELINE.inputs
        upward = []
        downward = []

        for delta in DRIFT_DELTAS:
            drift_value = max(0.0, baseline.drift + delta)
            upward.append(_score(_replace(baseline, drift=drift_value)))

        for delta in reversed(DRIFT_DELTAS):
            drift_value = max(0.0, baseline.drift + delta)
            downward.append(_score(_replace(baseline, drift=drift_value)))

        assert upward == pytest.approx(list(reversed(downward)))

    def test_drift_cycles_peak_at_minimum_drift(self) -> None:
        baseline = BASELINE.inputs
        pairs = [
            (
                max(0.0, baseline.drift + delta),
                _score(_replace(baseline, drift=max(0.0, baseline.drift + delta))),
            )
            for delta in DRIFT_DELTAS
        ]
        best_drift, best_score = max(pairs, key=lambda item: item[1])
        assert best_drift == min(drift for drift, _score_value in pairs)
        assert best_score == max(score for _drift, score in pairs)


class TestCombinedResponseSurface:
    def test_favorable_direction_beats_adverse_direction_across_a_cycle(self) -> None:
        baseline = BASELINE.inputs
        favorable_path = []
        adverse_path = []

        for scale in (0.75, 1.0, 1.25, 1.5):
            favorable_path.append(
                _score(
                    DavisFormulaInputs(
                        time_budget=baseline.time_budget * scale,
                        intent_intensity=baseline.intent_intensity / scale,
                        context_dimensions=max(0, baseline.context_dimensions - 1),
                        drift=max(0.0, baseline.drift - 0.25),
                    )
                )
            )
            adverse_path.append(
                _score(
                    DavisFormulaInputs(
                        time_budget=baseline.time_budget / scale,
                        intent_intensity=baseline.intent_intensity * scale,
                        context_dimensions=baseline.context_dimensions + 1,
                        drift=baseline.drift + 0.25,
                    )
                )
            )

        assert min(favorable_path) > max(adverse_path)
