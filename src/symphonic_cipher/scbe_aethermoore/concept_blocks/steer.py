"""
Concept Blocks — STEER
======================

PID controller for continuous correction.  Maps to SCBE Layer 8
(Hamiltonian energy regulation).

PIDController
-------------
Classic proportional-integral-derivative loop with anti-windup
clamping.  Pure Python, no external deps.

SteerBlock
----------
ConceptBlock wrapper — feed an error signal into ``tick()`` and get
the correction output back.
"""

from __future__ import annotations

import math
from typing import Any, Dict

from .base import BlockResult, BlockStatus, ConceptBlock


class PIDController:
    """Discrete PID controller with anti-windup."""

    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        output_min: float = -1.0,
        output_max: float = 1.0,
        dt: float = 0.01,
    ) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.dt = dt

        self._integral = 0.0
        self._prev_error = 0.0
        self._first_tick = True

    def update(self, error: float, dt: float | None = None) -> float:
        dt = dt if dt is not None else self.dt

        # Proportional
        p_term = self.kp * error

        # Integral with anti-windup
        self._integral += error * dt
        i_term = self.ki * self._integral

        # Derivative (skip on first tick to avoid spike)
        if self._first_tick:
            d_term = 0.0
            self._first_tick = False
        else:
            d_term = self.kd * (error - self._prev_error) / dt if dt > 0 else 0.0

        self._prev_error = error

        # Sum and clamp
        output = p_term + i_term + d_term
        output = max(self.output_min, min(self.output_max, output))

        # Anti-windup: if output saturated, stop integrating in that direction
        if output >= self.output_max and error > 0:
            self._integral -= error * dt
        elif output <= self.output_min and error < 0:
            self._integral -= error * dt

        return output

    @property
    def terms(self) -> Dict[str, float]:
        return {
            "p_term": self.kp * self._prev_error,
            "i_term": self.ki * self._integral,
            "d_term": 0.0,  # last d_term not stored, use for diagnostics
        }

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_error = 0.0
        self._first_tick = True


# -- concept block wrapper ---------------------------------------------------

class SteerBlock(ConceptBlock):
    """Concept block wrapping a PID controller.

    tick(inputs):
        inputs["error"]  — current error signal (float)
        inputs["dt"]     — (optional) time step override
    returns:
        BlockResult with output={"correction": float, "p_term": ..., "i_term": ..., "integral": ...}
    """

    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        output_min: float = -1.0,
        output_max: float = 1.0,
        name: str = "STEER",
    ) -> None:
        super().__init__(name)
        self._pid = PIDController(kp=kp, ki=ki, kd=kd, output_min=output_min, output_max=output_max)

    def _do_tick(self, inputs: Dict[str, Any]) -> BlockResult:
        error = inputs.get("error")
        if error is None:
            return BlockResult(status=BlockStatus.FAILURE, message="No error signal provided")

        dt = inputs.get("dt")
        correction = self._pid.update(float(error), dt=dt)
        terms = self._pid.terms

        return BlockResult(
            status=BlockStatus.SUCCESS,
            output={
                "correction": correction,
                "p_term": terms["p_term"],
                "i_term": terms["i_term"],
                "integral": self._pid._integral,
            },
        )

    def _do_configure(self, params: Dict[str, Any]) -> None:
        for attr in ("kp", "ki", "kd", "output_min", "output_max", "dt"):
            if attr in params:
                setattr(self._pid, attr, params[attr])

    def _do_reset(self) -> None:
        self._pid.reset()
