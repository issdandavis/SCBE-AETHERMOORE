"""Deterministic regional breathing field for the Clay action sandbox.

The filed-looking SCBE Layer-6 primitive is a positive radial map.  This
module does not replace that primitive.  It supplies a non-uniform, causal
field of breathing factors: twelve angular regions have their own drive and
compliance, exchange pressure with adjacent regions, and retain zero net
pressure.  Canonical world state and reward coordinates remain authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
import hashlib
import math
from typing import Any, Literal

from developmental_game_sandbox import (
    D,
    DevelopmentalGameSandbox,
    Phase,
    SandboxConfig,
    SandboxState,
    Vec2,
    _add,
    _matvec,
    _norm,
    _scale,
    sha256_json,
)


SCHEMA = "clay.regional-breathing-field.v1"
SAMPLE_SCHEMA = "clay.regional-breathing-sample.v1"

# A fixed 24-phase carrier avoids platform-specific trigonometry in the field
# recurrence.  Spatial interpolation still uses atan2 only to select a sector.
SINE_24 = tuple(
    D(value)
    for value in (
        "0",
        "0.258819045102521",
        "0.5",
        "0.707106781186548",
        "0.866025403784439",
        "0.965925826289068",
        "1",
        "0.965925826289068",
        "0.866025403784439",
        "0.707106781186548",
        "0.5",
        "0.258819045102521",
        "0",
        "-0.258819045102521",
        "-0.5",
        "-0.707106781186548",
        "-0.866025403784439",
        "-0.965925826289068",
        "-1",
        "-0.965925826289068",
        "-0.866025403784439",
        "-0.707106781186548",
        "-0.5",
        "-0.258819045102521",
    )
)
PRIME_PHASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
BALANCED_TRITS = (-1, 0, 1, 1, 0, -1, 0, 1, -1, -1, 1, 0)


def _text(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("regional breathing values must be finite")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _clamp(value: Decimal, lower: Decimal, upper: Decimal) -> Decimal:
    return min(upper, max(lower, value))


def _unit(value: Vec2, fallback: Vec2) -> Vec2:
    length = _norm(value)
    if length <= D("1e-24"):
        value = fallback
        length = _norm(value)
    if length <= D("1e-24"):
        return D("1"), D("0")
    return value[0] / length, value[1] / length


def _matrix_multiply(
    left: tuple[Vec2, Vec2], right: tuple[Vec2, Vec2]
) -> tuple[Vec2, Vec2]:
    return (
        (
            left[0][0] * right[0][0] + left[0][1] * right[1][0],
            left[0][0] * right[0][1] + left[0][1] * right[1][1],
        ),
        (
            left[1][0] * right[0][0] + left[1][1] * right[1][0],
            left[1][0] * right[0][1] + left[1][1] * right[1][1],
        ),
    )


def _atanh(value: Decimal) -> Decimal:
    if not D("-1") < value < D("1"):
        raise ValueError("atanh input must lie in the open unit interval")
    with localcontext() as context:
        context.prec = 40
        return (((D("1") + value) / (D("1") - value)).ln()) / D("2")


def _tanh(value: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 40
        doubled = (D("2") * value).exp()
        return (doubled - D("1")) / (doubled + D("1"))


def breathe_radius(radius: Decimal, factor: Decimal) -> Decimal:
    """Apply the canonical positive SCBE radial map on ``0 <= radius < 1``."""

    if not D("0") <= radius < D("1") or factor <= 0:
        raise ValueError("breathing radius/factor lies outside its domain")
    if radius == 0:
        return D("0")
    return _tanh(factor * _atanh(radius))


def inverse_breathe_radius(radius: Decimal, factor: Decimal) -> Decimal:
    if factor <= 0:
        raise ValueError("breathing factor must be positive")
    return breathe_radius(radius, D("1") / factor)


@dataclass(frozen=True, slots=True)
class RegionalBreathingConfig:
    sector_count: int = 12
    dt: Decimal = D("0.08")
    coupling: Decimal = D("0.22")
    spring: Decimal = D("0.16")
    damping: Decimal = D("0.18")
    drive_amplitude: Decimal = D("0.11")
    pressure_limit: Decimal = D("0.32")
    velocity_limit: Decimal = D("0.50")
    breath_gain: Decimal = D("0.70")
    breath_min: Decimal = D("0.80")
    breath_max: Decimal = D("1.25")
    force_gain: Decimal = D("0.075")
    phase_offset: int = 0
    orientation: int = 1
    mode: Literal["regional", "uniform"] = "regional"

    def __post_init__(self) -> None:
        if self.sector_count != 12:
            raise ValueError("the preregistered membrane has exactly twelve sectors")
        positives = (
            self.dt,
            self.coupling,
            self.spring,
            self.damping,
            self.drive_amplitude,
            self.pressure_limit,
            self.velocity_limit,
            self.breath_gain,
            self.breath_min,
            self.breath_max,
            self.force_gain,
        )
        if any(not value.is_finite() or value <= 0 for value in positives):
            raise ValueError("regional breathing coefficients must be positive and finite")
        if self.breath_min >= self.breath_max:
            raise ValueError("breathing bounds are reversed")
        if self.orientation not in (-1, 1):
            raise ValueError("field orientation must be -1 or +1")

    def record(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "sector_count": self.sector_count,
            "dt": _text(self.dt),
            "coupling": _text(self.coupling),
            "spring": _text(self.spring),
            "damping": _text(self.damping),
            "drive_amplitude": _text(self.drive_amplitude),
            "pressure_limit": _text(self.pressure_limit),
            "velocity_limit": _text(self.velocity_limit),
            "breath_gain": _text(self.breath_gain),
            "breath_min": _text(self.breath_min),
            "breath_max": _text(self.breath_max),
            "force_gain": _text(self.force_gain),
            "phase_offset": self.phase_offset,
            "orientation": self.orientation,
            "mode": self.mode,
            "prime_phases": list(PRIME_PHASES),
            "balanced_trits": list(BALANCED_TRITS),
        }


@dataclass(frozen=True, slots=True)
class FieldSnapshot:
    tick: int
    pressure: tuple[Decimal, ...]
    velocity: tuple[Decimal, ...]
    energy: Decimal
    neighbor_tension: Decimal


@dataclass(frozen=True, slots=True)
class BreathingSample:
    tick: int
    sector: int
    next_sector: int
    sector_fraction: Decimal
    pressure: Decimal
    pressure_gradient: Decimal
    pressure_mean: Decimal
    pressure_min: Decimal
    pressure_max: Decimal
    compliance: Decimal
    factor: Decimal
    radial_force: Decimal
    tangential_force: Decimal
    flow_magnitude: Decimal
    field_energy: Decimal
    neighbor_tension: Decimal
    config_sha256: str

    def record(self) -> dict[str, Any]:
        return {
            "schema": SAMPLE_SCHEMA,
            "tick": self.tick,
            "sector": self.sector,
            "next_sector": self.next_sector,
            "sector_fraction": _text(self.sector_fraction),
            "pressure": _text(self.pressure),
            "pressure_gradient": _text(self.pressure_gradient),
            "pressure_mean": _text(self.pressure_mean),
            "pressure_min": _text(self.pressure_min),
            "pressure_max": _text(self.pressure_max),
            "compliance": _text(self.compliance),
            "breathing_factor": _text(self.factor),
            "radial_force": _text(self.radial_force),
            "tangential_force": _text(self.tangential_force),
            "flow_magnitude": _text(self.flow_magnitude),
            "field_energy": _text(self.field_energy),
            "neighbor_tension": _text(self.neighbor_tension),
            "config_sha256": self.config_sha256,
        }


class RegionalBreathingField:
    """A cached deterministic pressure membrane on a twelve-sector ring."""

    def __init__(self, config: RegionalBreathingConfig = RegionalBreathingConfig()) -> None:
        self.config = config
        self.config_sha256 = sha256_json(config.record())
        zero = tuple(D("0") for _ in range(config.sector_count))
        self._states: list[tuple[tuple[Decimal, ...], tuple[Decimal, ...]]] = [
            (zero, zero)
        ]
        self.compliance = tuple(
            D("1") + D(BALANCED_TRITS[index]) * D("0.08")
            + D(PRIME_PHASES[index] % 5) * D("0.01")
            for index in range(config.sector_count)
        )

    def _drive(self, tick: int, sector: int) -> Decimal:
        source = 0 if self.config.mode == "uniform" else sector
        phase = (
            self.config.orientation * tick
            + self.config.phase_offset
            + 2 * source
            + PRIME_PHASES[source]
        ) % len(SINE_24)
        amplitude = self.config.drive_amplitude * (
            D("1") + D(BALANCED_TRITS[source]) * D("0.10")
        )
        return amplitude * SINE_24[phase]

    @staticmethod
    def _center_and_bound(
        values: list[Decimal], limit: Decimal, *, center: bool
    ) -> tuple[Decimal, ...]:
        if center:
            mean = sum(values, D("0")) / D(len(values))
            values = [value - mean for value in values]
        largest = max(abs(value) for value in values)
        if largest > limit:
            scale = limit / largest
            values = [value * scale for value in values]
        if center:
            # Decimal division may round.  Put the residual in the final sector
            # so the conserved sum is exactly zero in the stored ledger.
            values[-1] -= sum(values, D("0"))
        return tuple(values)

    def _advance(self, tick: int) -> None:
        pressure, velocity = self._states[-1]
        next_velocity: list[Decimal] = []
        for index in range(self.config.sector_count):
            left = pressure[(index - 1) % self.config.sector_count]
            right = pressure[(index + 1) % self.config.sector_count]
            laplacian = left - D("2") * pressure[index] + right
            acceleration = (
                self._drive(tick, index)
                + self.config.coupling * laplacian
                - self.config.spring * pressure[index]
                - self.config.damping * velocity[index]
            )
            next_velocity.append(velocity[index] + self.config.dt * acceleration)
        center = self.config.mode == "regional"
        velocity_tuple = self._center_and_bound(
            next_velocity, self.config.velocity_limit, center=center
        )
        next_pressure = [
            pressure[index] + self.config.dt * velocity_tuple[index]
            for index in range(self.config.sector_count)
        ]
        pressure_tuple = self._center_and_bound(
            next_pressure, self.config.pressure_limit, center=center
        )
        self._states.append((pressure_tuple, velocity_tuple))

    def snapshot(self, tick: int) -> FieldSnapshot:
        if tick < 0:
            raise ValueError("field tick cannot be negative")
        while len(self._states) <= tick:
            self._advance(len(self._states))
        pressure, velocity = self._states[tick]
        energy = sum(
            (
                D("0.5") * velocity[index] * velocity[index]
                + D("0.5") * self.config.spring * pressure[index] * pressure[index]
            )
            for index in range(self.config.sector_count)
        )
        tension = sum(
            (pressure[(index + 1) % self.config.sector_count] - pressure[index]) ** 2
            for index in range(self.config.sector_count)
        ) / D("2")
        return FieldSnapshot(tick, pressure, velocity, energy, tension)

    def sample(self, tick: int, position: Vec2, fallback: Vec2) -> BreathingSample:
        snapshot = self.snapshot(tick)
        direction = _unit(position, fallback)
        angle = math.atan2(float(direction[1]), float(direction[0])) % (2 * math.pi)
        coordinate = angle * self.config.sector_count / (2 * math.pi)
        sector = int(math.floor(coordinate)) % self.config.sector_count
        fraction = D(str(coordinate - math.floor(coordinate)))
        following = (sector + 1) % self.config.sector_count
        pressure = (
            snapshot.pressure[sector] * (D("1") - fraction)
            + snapshot.pressure[following] * fraction
        )
        compliance = (
            self.compliance[sector] * (D("1") - fraction)
            + self.compliance[following] * fraction
        )
        gradients = tuple(
            (
                snapshot.pressure[(index + 1) % self.config.sector_count]
                - snapshot.pressure[(index - 1) % self.config.sector_count]
            )
            / D("2")
            for index in range(self.config.sector_count)
        )
        gradient = gradients[sector] * (D("1") - fraction) + gradients[following] * fraction
        factor = _clamp(
            (self.config.breath_gain * compliance * pressure).exp(),
            self.config.breath_min,
            self.config.breath_max,
        )
        radial_force = self.config.force_gain * pressure
        tangential_force = self.config.force_gain * gradient
        flow_magnitude = (radial_force * radial_force + tangential_force * tangential_force).sqrt()
        mean = sum(snapshot.pressure, D("0")) / D(self.config.sector_count)
        return BreathingSample(
            tick=tick,
            sector=sector,
            next_sector=following,
            sector_fraction=fraction,
            pressure=pressure,
            pressure_gradient=gradient,
            pressure_mean=mean,
            pressure_min=min(snapshot.pressure),
            pressure_max=max(snapshot.pressure),
            compliance=compliance,
            factor=factor,
            radial_force=radial_force,
            tangential_force=tangential_force,
            flow_magnitude=flow_magnitude,
            field_energy=snapshot.energy,
            neighbor_tension=snapshot.neighbor_tension,
            config_sha256=self.config_sha256,
        )


class RegionalBreathingSandbox(DevelopmentalGameSandbox):
    """Developmental sandbox viewed through a causal regional breath field."""

    def __init__(
        self,
        config: SandboxConfig = SandboxConfig(),
        field_config: RegionalBreathingConfig = RegionalBreathingConfig(),
    ) -> None:
        super().__init__(config)
        self.field = RegionalBreathingField(field_config)

    def _sample(self, state: SandboxState) -> BreathingSample:
        return self.field.sample(state.tick, state.position, self._target(state))

    @property
    def presentation_radius(self) -> Decimal:
        return self.config.world_limit * D("2")

    def breathe_vector(self, value: Vec2, factor: Decimal) -> Vec2:
        radius = _norm(value)
        if radius <= D("1e-24"):
            return value
        normalized = min(D("0.999999999999"), radius / self.presentation_radius)
        mapped = breathe_radius(normalized, factor)
        scale = mapped / normalized
        return _scale(value, scale)

    def _local_jacobian(self, state: SandboxState, factor: Decimal) -> tuple[Vec2, Vec2]:
        direction = _unit(state.position, self._target(state))
        radius = min(
            D("0.999999999999"), _norm(state.position) / self.presentation_radius
        )
        if radius <= D("1e-18"):
            radial_scale = factor
            tangential_scale = factor
        else:
            mapped = breathe_radius(radius, factor)
            tangential_scale = mapped / radius
            radial_scale = factor * (D("1") - mapped * mapped) / (
                D("1") - radius * radius
            )
        difference = radial_scale - tangential_scale
        ux, uy = direction
        return (
            (
                tangential_scale + difference * ux * ux,
                difference * ux * uy,
            ),
            (
                difference * ux * uy,
                tangential_scale + difference * uy * uy,
            ),
        )

    def geometry_matrix_for_state(self, state: SandboxState) -> tuple[Vec2, Vec2]:
        sample = self._sample(state)
        base = DevelopmentalGameSandbox.geometry_matrix(self.phase(state))
        return _matrix_multiply(self._local_jacobian(state, sample.factor), base)

    def present_vector(self, state: SandboxState, value: Vec2) -> Vec2:
        base = DevelopmentalGameSandbox.geometry_matrix(self.phase(state))
        linearly_presented = _matvec(base, value)
        return self.breathe_vector(linearly_presented, self._sample(state).factor)

    def environment_forces(
        self,
        state: SandboxState,
        phase: Phase,
        gravity_scale: Decimal,
    ) -> tuple[Vec2, Vec2]:
        gravity, restoring = super().environment_forces(state, phase, gravity_scale)
        sample = self._sample(state)
        direction = _unit(state.position, self._target(state))
        tangent = -direction[1], direction[0]
        phase_scale = {
            "crawl": D("0.65"),
            "play": D("1"),
            "swaddle": D("0.05"),
            "release": D("0.35"),
        }[phase]
        flow = _add(
            _scale(direction, sample.radial_force * phase_scale),
            _scale(tangent, sample.tangential_force * phase_scale),
        )
        return gravity, _add(restoring, flow)

    def observation(self, state: SandboxState) -> dict[str, Any]:
        observation = super().observation(state)
        observation["breathing_field"] = self._sample(state).record()
        return observation


def training_field_config() -> RegionalBreathingConfig:
    return RegionalBreathingConfig()


def holdout_field_config() -> RegionalBreathingConfig:
    # Same declared physics, unseen phase/orientation.  This is a dynamics
    # holdout rather than a renamed copy of the training membrane.
    return RegionalBreathingConfig(phase_offset=7, orientation=-1)


__all__ = [
    "BALANCED_TRITS",
    "PRIME_PHASES",
    "SCHEMA",
    "SAMPLE_SCHEMA",
    "BreathingSample",
    "FieldSnapshot",
    "RegionalBreathingConfig",
    "RegionalBreathingField",
    "RegionalBreathingSandbox",
    "breathe_radius",
    "holdout_field_config",
    "inverse_breathe_radius",
    "training_field_config",
]
