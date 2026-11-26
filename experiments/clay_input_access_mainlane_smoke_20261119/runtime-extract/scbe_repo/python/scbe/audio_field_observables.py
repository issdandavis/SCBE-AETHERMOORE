"""Audio-field observable bridge.

This module treats audio as a wave-observation lane. It does not infer a
magnetic field from sound alone. Instead it extracts stable acoustic features
and, when a physical model is declared, emits bounded field-coupling proxies
that can be carried by reaction packets or benchmark reports.
"""

from __future__ import annotations

import array
import math
import wave
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .quasi_integer_recoupling import (
    QuasiIntegerRecoupling,
    recouple_to_integer,
)

EPS = 1e-12
FieldModelKind = Literal["generic", "magnetoelastic", "magnetosonic"]


@dataclass(frozen=True, slots=True)
class AudioFieldModel:
    """Declared context for interpreting audio features as field proxies."""

    kind: FieldModelKind = "generic"
    name: str = "generic-acoustic"
    coupling_gain: float = 1.0
    sound_speed_mps: float | None = None
    alfven_speed_mps: float | None = None
    magnetic_field_tesla: float | None = None
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AudioFieldObservables:
    """Auditable acoustic features plus optional field-coupling proxies."""

    sample_rate_hz: float
    sample_count: int
    energy_log: float
    spectral_centroid_hz: float
    spectral_bandwidth_hz: float
    high_frequency_ratio: float
    stability: float
    dispersion_proxy: float
    reverberation_decay_s: float | None
    modal_count: int
    phase_wrap_count: int
    modal_count_state: QuasiIntegerRecoupling
    field_model: AudioFieldModel
    field_coupling_proxy: float | None
    field_relationship: str
    claim_boundary: tuple[str, ...] = field(
        default=(
            "audio observables are wave features, not standalone magnetic-field measurements",
            "field coupling requires a declared physical model or sensor context",
        )
    )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["modal_count_state"] = self.modal_count_state.to_dict()
        data["field_model"] = self.field_model.to_dict()
        return data


def _dft_complex(signal: list[float]) -> list[complex]:
    n_samples = len(signal)
    spectrum: list[complex] = []
    for k in range(n_samples // 2 + 1):
        real = 0.0
        imag = 0.0
        for n, value in enumerate(signal):
            angle = -2.0 * math.pi * k * n / n_samples
            real += value * math.cos(angle)
            imag += value * math.sin(angle)
        spectrum.append(complex(real, imag))
    return spectrum


def _unwrap_phase(phases: list[float]) -> list[float]:
    if not phases:
        return []
    unwrapped = [phases[0]]
    offset = 0.0
    previous = phases[0]
    for phase in phases[1:]:
        delta = phase - previous
        if delta > math.pi:
            offset -= 2.0 * math.pi
        elif delta < -math.pi:
            offset += 2.0 * math.pi
        unwrapped.append(phase + offset)
        previous = phase
    return unwrapped


def _count_peaks(powers: list[float], *, threshold_ratio: float = 0.1) -> int:
    if len(powers) < 3:
        return 0
    peak_power = max(powers)
    if peak_power <= EPS:
        return 0
    threshold = peak_power * threshold_ratio
    count = 0
    for index in range(1, len(powers) - 1):
        if powers[index] >= threshold and powers[index] >= powers[index - 1] and powers[index] >= powers[index + 1]:
            count += 1
    return count


def _estimate_decay_seconds(signal: list[float], sample_rate_hz: float) -> float | None:
    window = max(8, min(128, len(signal) // 8))
    if len(signal) < window * 3:
        return None
    points: list[tuple[float, float]] = []
    for start in range(0, len(signal) - window + 1, window):
        frame = signal[start : start + window]
        energy = sum(value * value for value in frame) / window
        if energy > EPS:
            t = (start + window / 2.0) / sample_rate_hz
            points.append((t, math.log(energy)))
    if len(points) < 3:
        return None
    n = len(points)
    sum_t = sum(point[0] for point in points)
    sum_y = sum(point[1] for point in points)
    sum_tt = sum(point[0] * point[0] for point in points)
    sum_ty = sum(point[0] * point[1] for point in points)
    denom = n * sum_tt - sum_t * sum_t
    if abs(denom) <= EPS:
        return None
    slope = (n * sum_ty - sum_t * sum_y) / denom
    if slope >= -EPS:
        return None
    # Energy decay: ln(E) slope. Time to -60 dB energy is ln(1e-6)/slope.
    return math.log(1e-6) / slope


def _compute_field_coupling(
    *,
    model: AudioFieldModel,
    stability: float,
    dispersion_proxy: float,
) -> tuple[float | None, str]:
    if model.kind == "generic":
        return None, "unmodeled-acoustic-observation"
    if model.kind == "magnetoelastic":
        coupling = max(0.0, min(1.0, model.coupling_gain * stability / (1.0 + dispersion_proxy)))
        return coupling, "strain-magnetization coupling proxy"
    if model.kind == "magnetosonic":
        if model.sound_speed_mps is None or model.alfven_speed_mps is None:
            return (
                None,
                "magnetosonic model missing sound_speed_mps or alfven_speed_mps",
            )
        sound = abs(model.sound_speed_mps)
        alfven = abs(model.alfven_speed_mps)
        magnetosonic_speed = math.sqrt(sound * sound + alfven * alfven)
        if magnetosonic_speed <= EPS:
            return None, "magnetosonic model has zero wave speed"
        magnetic_share = alfven / magnetosonic_speed
        coupling = max(0.0, min(1.0, model.coupling_gain * magnetic_share * stability))
        return coupling, "compressibility-magnetic-pressure coupling proxy"
    return None, "unsupported field model"


def analyze_audio_field(
    signal: list[float] | tuple[float, ...],
    *,
    sample_rate_hz: float = 44100.0,
    high_frequency_cutoff_ratio: float = 0.5,
    model: AudioFieldModel | None = None,
) -> AudioFieldObservables:
    """Extract acoustic observables and optional model-bound field proxies."""

    samples = [float(value) for value in signal]
    if not samples:
        raise ValueError("signal must not be empty")
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be > 0")
    if not 0.0 <= high_frequency_cutoff_ratio <= 1.0:
        raise ValueError("high_frequency_cutoff_ratio must be in [0, 1]")

    spectrum = _dft_complex(samples)
    powers = [value.real * value.real + value.imag * value.imag for value in spectrum]
    total_power = sum(powers) + EPS
    bin_width = sample_rate_hz / len(samples)
    frequencies = [index * bin_width for index in range(len(powers))]

    energy_log = math.log(EPS + sum(value * value for value in samples))
    centroid = sum(freq * power for freq, power in zip(frequencies, powers)) / total_power
    variance = sum(((freq - centroid) ** 2) * power for freq, power in zip(frequencies, powers)) / total_power
    bandwidth = math.sqrt(max(0.0, variance))
    cutoff_index = int(len(powers) * high_frequency_cutoff_ratio)
    high_frequency_ratio = sum(powers[cutoff_index:]) / total_power
    high_frequency_ratio = max(0.0, min(1.0, high_frequency_ratio))
    stability = 1.0 - high_frequency_ratio
    dispersion_proxy = bandwidth / (centroid + EPS) if centroid > EPS else 0.0
    modal_count = _count_peaks(powers)
    modal_state = recouple_to_integer(modal_count, min_value=0, max_value=64, tolerance=0.0)

    phases = _unwrap_phase([math.atan2(value.imag, value.real) for value in spectrum])
    phase_wrap_count = 0
    for previous, current in zip(phases, phases[1:]):
        if abs(current - previous) > math.pi:
            phase_wrap_count += 1

    field_model = model or AudioFieldModel()
    coupling, relationship = _compute_field_coupling(
        model=field_model,
        stability=stability,
        dispersion_proxy=dispersion_proxy,
    )

    return AudioFieldObservables(
        sample_rate_hz=sample_rate_hz,
        sample_count=len(samples),
        energy_log=energy_log,
        spectral_centroid_hz=centroid,
        spectral_bandwidth_hz=bandwidth,
        high_frequency_ratio=high_frequency_ratio,
        stability=stability,
        dispersion_proxy=dispersion_proxy,
        reverberation_decay_s=_estimate_decay_seconds(samples, sample_rate_hz),
        modal_count=modal_count,
        phase_wrap_count=phase_wrap_count,
        modal_count_state=modal_state,
        field_model=field_model,
        field_coupling_proxy=coupling,
        field_relationship=relationship,
    )


def generate_sine(
    frequency_hz: float,
    *,
    sample_rate_hz: float = 44100.0,
    duration_s: float = 0.02,
    amplitude: float = 1.0,
) -> list[float]:
    sample_count = max(1, int(sample_rate_hz * duration_s))
    return [
        amplitude * math.sin(2.0 * math.pi * frequency_hz * index / sample_rate_hz) for index in range(sample_count)
    ]


def generate_decaying_sine(
    frequency_hz: float,
    *,
    sample_rate_hz: float = 44100.0,
    duration_s: float = 0.08,
    decay_seconds: float = 0.02,
) -> list[float]:
    sample_count = max(1, int(sample_rate_hz * duration_s))
    return [
        math.exp(-(index / sample_rate_hz) / decay_seconds)
        * math.sin(2.0 * math.pi * frequency_hz * index / sample_rate_hz)
        for index in range(sample_count)
    ]


def read_wav(path: str, *, max_samples: int = 4096) -> tuple[list[float], float]:
    """Decode a PCM WAV to a mono float signal in [-1, 1] + its (effective) sample rate. Stdlib only
    ($0, no ffmpeg). Block-averages down to <= max_samples so the naive O(n^2) DFT stays cheap on a real
    clip (a cheap anti-alias + decimate). Handles 8/16/32-bit PCM."""
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        rate = float(handle.getframerate())
        raw = handle.readframes(handle.getnframes())
    if width == 2:
        samples: Any = array.array("h")
        samples.frombytes(raw)
        scale = 32768.0
    elif width == 4:
        samples = array.array("i")
        samples.frombytes(raw)
        scale = 2147483648.0
    elif width == 1:
        samples = [byte - 128 for byte in raw]  # WAV 8-bit is unsigned, centered at 128
        scale = 128.0
    else:
        raise ValueError("unsupported WAV sample width: %d bytes" % width)
    mono = [
        sum(samples[i + c] for c in range(channels)) / (channels * scale)
        for i in range(0, len(samples) - channels + 1, channels)
    ]
    if not mono:
        raise ValueError("WAV decoded to an empty signal")
    if len(mono) > max_samples:
        block = len(mono) // max_samples
        mono = [sum(mono[i : i + block]) / block for i in range(0, block * max_samples, block)]
        rate = rate / block
    return mono, rate


def analyze_wav(
    path: str,
    *,
    model: AudioFieldModel | None = None,
    max_samples: int = 4096,
    high_frequency_cutoff_ratio: float = 0.5,
) -> AudioFieldObservables:
    """Run the audio-axis (L14) analysis on a REAL audio file -- the whisper input / TTS output clips the
    universal port produces -- not just synthetic sines. Decodes the WAV ($0, stdlib) then reuses the
    existing analyze_audio_field, so every acoustic observable (centroid, bandwidth, stability, modal
    count, decay, field-coupling proxy) is now available for real captured/synthesized audio."""
    signal, rate = read_wav(path, max_samples=max_samples)
    return analyze_audio_field(
        signal, sample_rate_hz=rate, model=model, high_frequency_cutoff_ratio=high_frequency_cutoff_ratio
    )
