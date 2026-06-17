"""Simple first-pass utilities for M-TEF prototype bookkeeping.

These functions are intentionally conservative. They do not simulate ferrofluid,
TENG contact physics, or electromagnetic field geometry. They are bookkeeping
helpers for early bench tests so power claims stay tied to explicit inputs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrototypePowerBudget:
    """Power estimate for separate EM and TENG channels."""

    mechanical_input_w: float
    em_efficiency: float
    teng_efficiency: float
    pmic_efficiency: float = 1.0

    def __post_init__(self) -> None:
        for name, value in [
            ("mechanical_input_w", self.mechanical_input_w),
            ("em_efficiency", self.em_efficiency),
            ("teng_efficiency", self.teng_efficiency),
            ("pmic_efficiency", self.pmic_efficiency),
        ]:
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        for name, value in [
            ("em_efficiency", self.em_efficiency),
            ("teng_efficiency", self.teng_efficiency),
            ("pmic_efficiency", self.pmic_efficiency),
        ]:
            if value > 1:
                raise ValueError(f"{name} must be <= 1.0")

    @property
    def em_output_w(self) -> float:
        return self.mechanical_input_w * self.em_efficiency

    @property
    def teng_output_w(self) -> float:
        return self.mechanical_input_w * self.teng_efficiency

    @property
    def combined_raw_w(self) -> float:
        return self.em_output_w + self.teng_output_w

    @property
    def combined_after_power_management_w(self) -> float:
        return self.combined_raw_w * self.pmic_efficiency

    @property
    def stronger_individual_w(self) -> float:
        return max(self.em_output_w, self.teng_output_w)

    @property
    def additive_gain_ratio(self) -> float:
        return net_gain_ratio(
            self.combined_after_power_management_w,
            self.em_output_w,
            self.teng_output_w,
        )

    @property
    def clears_additive_gate(self) -> bool:
        return self.combined_after_power_management_w > self.stronger_individual_w

    def clears_margin_gate(self, minimum_gain_ratio: float = 1.2) -> bool:
        """Return True only if combined output clears a practical margin.

        A barely-positive ratio can disappear into measurement error, drag, or
        rectifier losses. Use this for prototype go/no-go decisions.
        """
        if minimum_gain_ratio <= 1.0:
            raise ValueError("minimum_gain_ratio must be > 1.0")
        return self.additive_gain_ratio >= minimum_gain_ratio

    def decision_packet(self) -> dict[str, float | bool | str]:
        """Bench-test decision packet for the M-TEF make-or-break gate."""
        minimum_gain_ratio = 1.2
        return {
            "schema_version": "mtef_additive_gate_v1",
            "mechanical_input_w": self.mechanical_input_w,
            "em_output_w": self.em_output_w,
            "teng_output_w": self.teng_output_w,
            "combined_after_power_management_w": self.combined_after_power_management_w,
            "stronger_individual_w": self.stronger_individual_w,
            "additive_gain_ratio": self.additive_gain_ratio,
            "clears_additive_gate": self.clears_additive_gate,
            "minimum_practical_gain_ratio": minimum_gain_ratio,
            "clears_practical_margin": self.clears_margin_gate(minimum_gain_ratio),
        }


def mechanical_power_from_stroke(force_n: float, stroke_m: float, cycles_per_second: float) -> float:
    """Estimate average mechanical input power for a repeated stroke.

    P = force * distance * cycles_per_second
    """

    if force_n < 0 or stroke_m < 0 or cycles_per_second < 0:
        raise ValueError("force, stroke, and cycles_per_second must be non-negative")
    return force_n * stroke_m * cycles_per_second


def capacitor_energy_j(capacitance_f: float, voltage_v: float) -> float:
    """Energy stored in a capacitor: E = 1/2 C V^2."""

    if capacitance_f < 0:
        raise ValueError("capacitance_f must be non-negative")
    return 0.5 * capacitance_f * voltage_v**2


def average_power_from_energy(energy_j: float, seconds: float) -> float:
    """Average power from stored/measured energy over a time interval."""

    if energy_j < 0:
        raise ValueError("energy_j must be non-negative")
    if seconds <= 0:
        raise ValueError("seconds must be positive")
    return energy_j / seconds


def faraday_voltage_estimate(turns: int, delta_flux_wb: float, delta_time_s: float) -> float:
    """Idealized magnitude estimate from Faraday's law.

    V = N * |dPhi/dt|

    This is not a coil-design substitute. It is a sanity-check utility.
    """

    if turns < 0:
        raise ValueError("turns must be non-negative")
    if delta_time_s <= 0:
        raise ValueError("delta_time_s must be positive")
    return turns * abs(delta_flux_wb) / delta_time_s


def net_gain_ratio(combined_w: float, em_only_w: float, teng_only_w: float) -> float:
    """Return combined output divided by the stronger individual channel."""

    if combined_w < 0 or em_only_w < 0 or teng_only_w < 0:
        raise ValueError("power values must be non-negative")
    baseline = max(em_only_w, teng_only_w)
    if baseline == 0:
        raise ValueError("at least one individual channel must have positive power")
    return combined_w / baseline
