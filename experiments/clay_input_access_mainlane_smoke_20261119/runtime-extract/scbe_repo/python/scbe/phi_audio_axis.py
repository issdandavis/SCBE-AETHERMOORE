"""Layer 14 phi-carrier audio realization and recovery.

This module extends the existing L14 Audio Axis; it does not define a parallel
audio layer.  It preserves the canonical mapping:

* L3 supplies a normalized mixture over ``KO, AV, RU, CA, UM, DR``;
* L7 supplies the intent phase;
* L13 may supply a risk gain when governance is one active process;
* L14 realizes the multiplex as audio and emits FFT telemetry.

Governance is metadata/control on this route, not the goal of the audio axis or
of the larger system.  Direct amplitude remains available independently of any
governance decision.

For tongue index ``k`` the three existing structures are kept separate:

    semantic weight  = phi**k
    audio carrier    = base_hz * phi**(k/6)
    phase sector     = 2*pi*k/6

The decoder uses a least-squares matched bank over all six carriers.  It does
not rely on a beat-frequency GCD or assume that the carriers are orthogonal in
a finite window.  The finite-window Gram matrix is solved directly.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from numbers import Integral
from typing import Mapping, Sequence

from .audio_field_observables import AudioFieldObservables, analyze_audio_field


PHI = (1.0 + math.sqrt(5.0)) / 2.0
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
DEFAULT_BASE_HZ = 440.0
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_DURATION_S = 0.5
RISK_AMPLITUDES = {"LOW": 1.0, "MEDIUM": 0.6, "HIGH": 0.3, "CRITICAL": 0.1}


@dataclass(frozen=True, slots=True)
class PhiCarrier:
    tongue: str
    index: int
    semantic_weight: float
    frequency_hz: float
    phase_sector_rad: float


@dataclass(frozen=True, slots=True)
class AudioFluctuation:
    tongue_a: str
    tongue_b: str
    beat_hz: float
    envelope_period_s: float


@dataclass(frozen=True, slots=True)
class RadialPhasePoint:
    """One integer activation after phi-ratio range matching and phase placement."""

    tongue: str
    index: int
    integer: int
    ratio: float
    ratioed_value: float
    radius: float
    phase_rad: float
    real: float
    imag: float


@dataclass(frozen=True, slots=True)
class L14RadialPhaseTensor:
    """Six complex lanes represented as a network-friendly 12-real tensor.

    ``head_amplitude`` is a shared block-floating scale.  ``radial_power``
    changes the spacing of sub-head values while leaving the head exactly at
    ``peak_radius``.  ``rotation_rad`` rotates every lane together, so it can
    splay into a phase frame and rotate back without changing the payload.
    """

    points: tuple[RadialPhasePoint, ...]
    head_amplitude: float
    peak_radius: float
    radial_power: float
    rotation_rad: float
    layer: str = "L14"
    schema: str = "scbe.l14.radial-phase-integers.v1"

    @property
    def real_tensor(self) -> tuple[float, ...]:
        """Interleaved real/imaginary coordinates for ordinary real-valued nets."""
        return tuple(coordinate for point in self.points for coordinate in (point.real, point.imag))

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "layer": self.layer,
            "head_amplitude": self.head_amplitude,
            "peak_radius": self.peak_radius,
            "radial_power": self.radial_power,
            "rotation_rad": self.rotation_rad,
            "real_tensor": list(self.real_tensor),
            "points": [asdict(point) for point in self.points],
        }


@dataclass(frozen=True, slots=True)
class L14PhiAudioPacket:
    """L14 multiplex waveform plus the telemetry extracted from it."""

    signal: tuple[float, ...]
    sample_rate_hz: int
    duration_s: float
    amplitude: float
    risk_level: str | None
    risk_gain: float
    coherence: float
    intent: float
    envelope_end: float
    tongue_mix: dict[str, float]
    carriers: tuple[PhiCarrier, ...]
    observables: AudioFieldObservables
    layer: str = "L14"
    schema: str = "scbe.l14.phi-audio.v1"

    def to_dict(self, *, include_signal: bool = False) -> dict:
        data = {
            "schema": self.schema,
            "layer": self.layer,
            "sample_rate_hz": self.sample_rate_hz,
            "duration_s": self.duration_s,
            "amplitude": self.amplitude,
            "risk_level": self.risk_level,
            "risk_gain": self.risk_gain,
            "coherence": self.coherence,
            "intent": self.intent,
            "envelope_end": self.envelope_end,
            "tongue_mix": dict(self.tongue_mix),
            "carriers": [asdict(carrier) for carrier in self.carriers],
            "observables": self.observables.to_dict(),
        }
        if include_signal:
            data["signal"] = list(self.signal)
        return data


@dataclass(frozen=True, slots=True)
class L14PhiRecovery:
    tongue_mix: dict[str, float]
    component_amplitudes: dict[str, float]
    component_phases_rad: dict[str, float]
    intent: float
    total_amplitude: float
    relative_reconstruction_error: float


def phi_carriers(base_hz: float = DEFAULT_BASE_HZ) -> tuple[PhiCarrier, ...]:
    if base_hz <= 0.0:
        raise ValueError("base_hz must be positive")
    return tuple(
        PhiCarrier(
            tongue=tongue,
            index=k,
            semantic_weight=PHI**k,
            frequency_hz=base_hz * PHI ** (k / len(TONGUES)),
            phase_sector_rad=2.0 * math.pi * k / len(TONGUES),
        )
        for k, tongue in enumerate(TONGUES)
    )


def _integer_activations(values: Mapping[str, int] | Sequence[int]) -> tuple[int, ...]:
    if isinstance(values, Mapping):
        unknown = set(values) - set(TONGUES)
        if unknown:
            raise ValueError(f"unknown tongue keys: {sorted(unknown)}")
        ordered = [values.get(tongue, 0) for tongue in TONGUES]
    else:
        ordered = list(values)
        if len(ordered) != len(TONGUES):
            raise ValueError(f"activations must have {len(TONGUES)} values")
    if any(isinstance(value, bool) or not isinstance(value, Integral) for value in ordered):
        raise TypeError("phase-scaled activations must be integers")
    return tuple(int(value) for value in ordered)


def encode_ratioed_integers(
    activations: Mapping[str, int] | Sequence[int],
    *,
    peak_radius: float = 1.0,
    radial_power: float = 1.0,
    rotation_rad: float = 0.0,
) -> L14RadialPhaseTensor:
    """Place ratioed integer activations on the six-lane phase scale.

    For integer activation ``a_k`` and semantic ratio ``r_k = phi**k``::

        h     = max_k(abs(a_k * r_k))
        rho_k = peak * (abs(a_k * r_k) / h)**power
        z_k   = sign(a_k) * rho_k * exp(i * (rotation + 2*pi*k/6))

    This is a reversible range match, not a projection.  A power below one
    spreads smaller radii outward; a power above one bunches them inward.  The
    head remains at ``peak_radius`` because one raised to any positive power is
    one.  Signed values use the antipodal phase while carrier index preserves
    the lane address.  The audio carrier ratio remains ``phi**(k/6)`` in
    :func:`phi_carriers`; semantic radius and carrier frequency are separate
    scales.
    """
    integers = _integer_activations(activations)
    for value, name in (
        (peak_radius, "peak_radius"),
        (radial_power, "radial_power"),
        (rotation_rad, "rotation_rad"),
    ):
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
    if peak_radius <= 0.0:
        raise ValueError("peak_radius must be positive")
    if radial_power <= 0.0:
        raise ValueError("radial_power must be positive")

    ratios = tuple(PHI**k for k in range(len(TONGUES)))
    ratioed = tuple(integer * ratio for integer, ratio in zip(integers, ratios))
    head = max((abs(value) for value in ratioed), default=0.0)
    rotation = rotation_rad % (2.0 * math.pi)
    points: list[RadialPhasePoint] = []
    for k, (tongue, integer, ratio, value) in enumerate(zip(TONGUES, integers, ratios, ratioed)):
        base_phase = rotation + 2.0 * math.pi * k / len(TONGUES)
        radius = 0.0 if head == 0.0 else peak_radius * (abs(value) / head) ** radial_power
        signed_radius = math.copysign(radius, value) if value else 0.0
        real = signed_radius * math.cos(base_phase)
        imag = signed_radius * math.sin(base_phase)
        phase = math.atan2(imag, real) % (2.0 * math.pi) if radius else base_phase % (2.0 * math.pi)
        points.append(
            RadialPhasePoint(
                tongue=tongue,
                index=k,
                integer=integer,
                ratio=ratio,
                ratioed_value=value,
                radius=radius,
                phase_rad=phase,
                real=real,
                imag=imag,
            )
        )
    return L14RadialPhaseTensor(
        points=tuple(points),
        head_amplitude=head,
        peak_radius=peak_radius,
        radial_power=radial_power,
        rotation_rad=rotation,
    )


def decode_ratioed_integers(
    tensor: L14RadialPhaseTensor,
    *,
    tolerance: float = 1e-8,
) -> tuple[int, ...]:
    """Invert :func:`encode_ratioed_integers` from coordinates, scale, and frame."""
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("tolerance must be positive and finite")
    if len(tensor.points) != len(TONGUES):
        raise ValueError(f"tensor must have {len(TONGUES)} phase lanes")
    if tensor.head_amplitude == 0.0:
        if any(math.hypot(point.real, point.imag) > tolerance for point in tensor.points):
            raise ValueError("zero-head tensor contains non-zero phase points")
        return (0,) * len(TONGUES)

    decoded: list[int] = []
    for k, point in enumerate(tensor.points):
        if point.index != k or point.tongue != TONGUES[k]:
            raise ValueError("phase lanes are out of canonical tongue order")
        base_phase = tensor.rotation_rad + 2.0 * math.pi * k / len(TONGUES)
        aligned = complex(point.real, point.imag) * complex(math.cos(base_phase), -math.sin(base_phase))
        if abs(aligned.imag) > tolerance:
            raise ValueError(f"{point.tongue} is off its phase axis")
        signed_radius = aligned.real
        # Power companding can deliberately bunch a small, valid activation
        # arbitrarily close to the origin.  Only an encoded exact zero is
        # payload-zero; tolerance is for phase/integer validation, not erasure.
        if signed_radius == 0.0:
            raw_integer = 0.0
        else:
            normalized = min(1.0, abs(signed_radius) / tensor.peak_radius)
            ratioed_value = math.copysign(
                tensor.head_amplitude * normalized ** (1.0 / tensor.radial_power),
                signed_radius,
            )
            raw_integer = ratioed_value / point.ratio
        nearest = round(raw_integer)
        if abs(raw_integer - nearest) > tolerance:
            raise ValueError(f"{point.tongue} does not decode to an integer")
        decoded.append(nearest)
    return tuple(decoded)


def pairwise_fluctuations(base_hz: float = DEFAULT_BASE_HZ) -> tuple[AudioFluctuation, ...]:
    """All fifteen physical difference-frequency envelopes."""
    carriers = phi_carriers(base_hz)
    rows: list[AudioFluctuation] = []
    for i, a in enumerate(carriers):
        for b in carriers[i + 1 :]:
            beat = abs(b.frequency_hz - a.frequency_hz)
            rows.append(AudioFluctuation(a.tongue, b.tongue, beat, 1.0 / beat))
    return tuple(rows)


def _normalized_mix(tongue_mix: Mapping[str, float] | Sequence[float]) -> dict[str, float]:
    if isinstance(tongue_mix, Mapping):
        unknown = set(tongue_mix) - set(TONGUES)
        if unknown:
            raise ValueError(f"unknown tongue keys: {sorted(unknown)}")
        values = [float(tongue_mix.get(tongue, 0.0)) for tongue in TONGUES]
    else:
        values = [float(value) for value in tongue_mix]
        if len(values) != len(TONGUES):
            raise ValueError(f"tongue_mix must have {len(TONGUES)} values")
    if any(not math.isfinite(value) or value < 0.0 for value in values):
        raise ValueError("tongue weights must be finite and non-negative")
    total = sum(values)
    if total <= 0.0:
        raise ValueError("at least one tongue weight must be positive")
    return {tongue: value / total for tongue, value in zip(TONGUES, values)}


def _clamp_unit(value: float, name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return max(0.0, min(1.0, float(value)))


def synthesize_l14_phi(
    tongue_mix: Mapping[str, float] | Sequence[float],
    *,
    intent: float,
    coherence: float,
    amplitude: float = 1.0,
    risk_level: str | None = None,
    base_hz: float = DEFAULT_BASE_HZ,
    sample_rate_hz: int = DEFAULT_SAMPLE_RATE,
    duration_s: float = DEFAULT_DURATION_S,
    telemetry_samples: int = 512,
) -> L14PhiAudioPacket:
    """Realize an L3/L7 multiplex through L14, optionally applying L13 gain."""
    if sample_rate_hz <= 0 or duration_s <= 0.0:
        raise ValueError("sample_rate_hz and duration_s must be positive")
    if telemetry_samples < 16:
        raise ValueError("telemetry_samples must be at least 16")
    if not math.isfinite(amplitude) or amplitude < 0.0:
        raise ValueError("amplitude must be finite and non-negative")
    risk = risk_level.strip().upper() if risk_level is not None else None
    if risk is not None and risk not in RISK_AMPLITUDES:
        raise ValueError(f"risk_level must be one of {tuple(RISK_AMPLITUDES)}")

    mix = _normalized_mix(tongue_mix)
    intent_value = _clamp_unit(intent, "intent")
    coherence_value = _clamp_unit(coherence, "coherence")
    risk_gain = RISK_AMPLITUDES[risk] if risk is not None else 1.0
    output_amplitude = amplitude * risk_gain
    carriers = phi_carriers(base_hz)
    count = max(1, round(sample_rate_hz * duration_s))
    intent_phase = 2.0 * math.pi * intent_value
    decay_rate = 2.0 * (1.0 - coherence_value)

    signal: list[float] = []
    for n in range(count):
        time_s = n / sample_rate_hz
        envelope = math.exp(-decay_rate * time_s)
        carrier_sum = sum(
            mix[carrier.tongue]
            * math.cos(2.0 * math.pi * carrier.frequency_hz * time_s
                       + carrier.phase_sector_rad + intent_phase)
            for carrier in carriers
        )
        signal.append(output_amplitude * envelope * carrier_sum)

    observed = signal[: min(len(signal), telemetry_samples)]
    observables = analyze_audio_field(observed, sample_rate_hz=sample_rate_hz)
    return L14PhiAudioPacket(
        signal=tuple(signal),
        sample_rate_hz=sample_rate_hz,
        duration_s=count / sample_rate_hz,
        amplitude=output_amplitude,
        risk_level=risk,
        risk_gain=risk_gain,
        coherence=coherence_value,
        intent=intent_value,
        envelope_end=math.exp(-decay_rate * ((count - 1) / sample_rate_hz)),
        tongue_mix=mix,
        carriers=carriers,
        observables=observables,
    )


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Partial-pivot Gaussian elimination for the small 12x12 Gram system."""
    n = len(vector)
    augmented = [row[:] + [value] for row, value in zip(matrix, vector)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("carrier Gram matrix is singular for this sampling window")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(n):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor == 0.0:
                continue
            augmented[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[column])
            ]
    return [row[-1] for row in augmented]


def recover_l14_phi(
    signal: Sequence[float],
    *,
    coherence: float,
    base_hz: float = DEFAULT_BASE_HZ,
    sample_rate_hz: int = DEFAULT_SAMPLE_RATE,
) -> L14PhiRecovery:
    """Recover six component amplitudes/phases and the common L7 intent phase."""
    samples = [float(value) for value in signal]
    if len(samples) < 24:
        raise ValueError("at least 24 samples are required")
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")
    coherence_value = _clamp_unit(coherence, "coherence")
    decay_rate = 2.0 * (1.0 - coherence_value)
    carriers = phi_carriers(base_hz)
    width = 2 * len(carriers)
    gram = [[0.0] * width for _ in range(width)]
    rhs = [0.0] * width

    for n, sample in enumerate(samples):
        time_s = n / sample_rate_hz
        envelope = math.exp(-decay_rate * time_s)
        basis: list[float] = []
        for carrier in carriers:
            angle = 2.0 * math.pi * carrier.frequency_hz * time_s
            basis.extend((envelope * math.cos(angle), envelope * math.sin(angle)))
        for i, value_i in enumerate(basis):
            rhs[i] += value_i * sample
            for j in range(i, width):
                gram[i][j] += value_i * basis[j]
    for i in range(width):
        for j in range(i):
            gram[i][j] = gram[j][i]

    coefficients = _solve_linear_system(gram, rhs)
    amplitudes: dict[str, float] = {}
    phases: dict[str, float] = {}
    intent_x = 0.0
    intent_y = 0.0
    for k, carrier in enumerate(carriers):
        cosine_coefficient = coefficients[2 * k]
        sine_coefficient = coefficients[2 * k + 1]
        component_amplitude = math.hypot(cosine_coefficient, sine_coefficient)
        phase = math.atan2(-sine_coefficient, cosine_coefficient) % (2.0 * math.pi)
        intent_phase = phase - carrier.phase_sector_rad
        amplitudes[carrier.tongue] = component_amplitude
        phases[carrier.tongue] = phase
        intent_x += component_amplitude * math.cos(intent_phase)
        intent_y += component_amplitude * math.sin(intent_phase)

    total_amplitude = sum(amplitudes.values())
    if total_amplitude <= 1e-15:
        raise ValueError("signal contains no recoverable phi-carrier amplitude")
    mix = {tongue: amplitude / total_amplitude for tongue, amplitude in amplitudes.items()}
    recovered_intent = (math.atan2(intent_y, intent_x) % (2.0 * math.pi)) / (2.0 * math.pi)

    squared_error = 0.0
    squared_signal = 0.0
    for n, sample in enumerate(samples):
        time_s = n / sample_rate_hz
        envelope = math.exp(-decay_rate * time_s)
        estimate = 0.0
        for k, carrier in enumerate(carriers):
            angle = 2.0 * math.pi * carrier.frequency_hz * time_s
            estimate += envelope * (
                coefficients[2 * k] * math.cos(angle)
                + coefficients[2 * k + 1] * math.sin(angle)
            )
        squared_error += (sample - estimate) ** 2
        squared_signal += sample * sample
    relative_error = math.sqrt(squared_error / max(squared_signal, 1e-30))

    return L14PhiRecovery(
        tongue_mix=mix,
        component_amplitudes=amplitudes,
        component_phases_rad=phases,
        intent=recovered_intent,
        total_amplitude=total_amplitude,
        relative_reconstruction_error=relative_error,
    )
