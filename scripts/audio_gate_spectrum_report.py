#!/usr/bin/env python3
"""Experimental WAV -> SCBE audio gate spectrum telemetry runner."""

from __future__ import annotations

import argparse
import json
import math
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

VISIBLE_MIN_NM = 380.0
VISIBLE_MAX_NM = 700.0
EPSILON = 1e-10


@dataclass
class FrameFeatures:
    index: int
    start_sample: int
    end_sample: int
    energy: float
    centroid: float
    flux: float
    hf_ratio: float
    stability: float
    overall_pressure: float
    overall_wavelength_nm: float
    overall_band: str
    overall_state: str
    band_pressures: list[float]
    band_wavelengths_nm: list[float]
    band_labels: list[str]
    band_states: list[str]


def clamp01(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def pressure_to_wavelength(pressure: float) -> float:
    p = clamp01(pressure)
    return VISIBLE_MIN_NM + p * (VISIBLE_MAX_NM - VISIBLE_MIN_NM)


def wavelength_to_band(wavelength_nm: float) -> str:
    if wavelength_nm < 450:
        return "violet"
    if wavelength_nm < 495:
        return "blue"
    if wavelength_nm < 570:
        return "green"
    if wavelength_nm < 590:
        return "yellow"
    if wavelength_nm < 620:
        return "orange"
    return "red"


def pressure_to_state(pressure: float) -> str:
    p = clamp01(pressure)
    if p < 0.2:
        return "stable"
    if p < 0.5:
        return "pressured"
    if p < 0.8:
        return "near_break"
    return "breaking"


def read_wav_mono(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frame_count = wav.getnframes()
        raw = wav.readframes(frame_count)

    if sample_width == 1:
        data = np.frombuffer(raw, dtype=np.uint8).astype(np.float64)
        data = (data - 128.0) / 128.0
    elif sample_width == 2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    elif sample_width == 4:
        data = np.frombuffer(raw, dtype=np.int32).astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width} bytes")

    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)

    return data.astype(np.float64), sample_rate


def compute_power_spectrum(frame: np.ndarray) -> np.ndarray:
    spectrum = np.fft.rfft(frame)
    return (np.abs(spectrum) ** 2) / max(1, len(frame))


def compute_audio_features(
    frame: np.ndarray,
    sample_rate: int,
    previous_spectrum: np.ndarray | None,
    hf_cutoff_ratio: float,
) -> tuple[dict[str, float], np.ndarray]:
    spectrum = compute_power_spectrum(frame)
    freqs = np.fft.rfftfreq(len(frame), d=1.0 / sample_rate)

    energy = float(np.log(EPSILON + np.sum(frame * frame)))

    total_power = float(np.sum(spectrum)) + EPSILON
    centroid = float(np.sum(freqs * spectrum) / total_power)

    if previous_spectrum is None:
        flux = 0.0
    else:
        use = min(len(previous_spectrum), len(spectrum))
        delta = np.sqrt(spectrum[:use]) - np.sqrt(previous_spectrum[:use])
        flux = float(np.sum(delta * delta) / max(1, use))

    cutoff_bin = int(len(spectrum) * hf_cutoff_ratio)
    hf_ratio = float(np.sum(spectrum[cutoff_bin:]) / total_power)
    stability = float(1.0 - hf_ratio)

    return {
        "energy": energy,
        "centroid": centroid,
        "flux": flux,
        "hf_ratio": hf_ratio,
        "stability": stability,
    }, spectrum


def compute_band_pressures(spectrum: np.ndarray, overall_pressure: float, band_count: int = 6) -> list[float]:
    total_power = float(np.sum(spectrum)) + EPSILON
    max_power = float(np.max(spectrum)) + EPSILON
    band_pressures: list[float] = []

    for band_index in range(band_count):
        start = int((band_index / band_count) * len(spectrum))
        end = int(((band_index + 1) / band_count) * len(spectrum))
        if end <= start:
            band_pressures.append(0.0)
            continue
        band_power = float(np.sum(spectrum[start:end]))
        ratio = band_power / total_power
        # Experimental pressure:
        # - overall instability is authoritative
        # - energetic bands carry more of that instability
        # This prevents clean, narrow-band signals from looking "broken"
        # just because one band dominates a stable frame.
        dominance = band_power / max_power
        contribution = (0.5 * ratio * band_count) + (0.5 * dominance)
        pressure = clamp01(overall_pressure * contribution)
        band_pressures.append(pressure)

    return band_pressures


def compute_overall_pressure(flux: float, hf_ratio: float) -> float:
    # Experimental proxy for "mid-fall" audio instability.
    flux_pressure = clamp01(math.sqrt(max(flux, 0.0)) * 4.0)
    return clamp01((0.6 * hf_ratio) + (0.4 * flux_pressure))


def analyze_wav(
    signal: np.ndarray,
    sample_rate: int,
    frame_size: int = 2048,
    hop_size: int = 1024,
    hf_cutoff_ratio: float = 0.5,
) -> dict[str, Any]:
    frames: list[FrameFeatures] = []
    previous_spectrum: np.ndarray | None = None

    for start in range(0, max(1, len(signal) - frame_size + 1), hop_size):
        end = start + frame_size
        frame = signal[start:end]
        if len(frame) < frame_size:
            break

        features, spectrum = compute_audio_features(frame, sample_rate, previous_spectrum, hf_cutoff_ratio)
        previous_spectrum = spectrum

        overall_pressure = compute_overall_pressure(features["flux"], features["hf_ratio"])
        band_pressures = compute_band_pressures(spectrum, overall_pressure=overall_pressure, band_count=6)
        band_wavelengths = [pressure_to_wavelength(p) for p in band_pressures]
        band_labels = [wavelength_to_band(w) for w in band_wavelengths]
        band_states = [pressure_to_state(p) for p in band_pressures]
        overall_wavelength = pressure_to_wavelength(overall_pressure)

        frames.append(
            FrameFeatures(
                index=len(frames),
                start_sample=start,
                end_sample=end,
                energy=features["energy"],
                centroid=features["centroid"],
                flux=features["flux"],
                hf_ratio=features["hf_ratio"],
                stability=features["stability"],
                overall_pressure=overall_pressure,
                overall_wavelength_nm=overall_wavelength,
                overall_band=wavelength_to_band(overall_wavelength),
                overall_state=pressure_to_state(overall_pressure),
                band_pressures=band_pressures,
                band_wavelengths_nm=band_wavelengths,
                band_labels=band_labels,
                band_states=band_states,
            )
        )

    if not frames:
        raise ValueError("No complete frames could be extracted from the WAV input.")

    avg = lambda key: float(np.mean([getattr(frame, key) for frame in frames]))
    max_pressure_frame = max(frames, key=lambda frame: frame.overall_pressure)

    return {
        "sample_rate": sample_rate,
        "frame_size": frame_size,
        "hop_size": hop_size,
        "frame_count": len(frames),
        "summary": {
            "avg_energy": avg("energy"),
            "avg_centroid": avg("centroid"),
            "avg_flux": avg("flux"),
            "avg_hf_ratio": avg("hf_ratio"),
            "avg_stability": avg("stability"),
            "avg_overall_pressure": avg("overall_pressure"),
            "max_overall_pressure": float(max(frame.overall_pressure for frame in frames)),
            "peak_state": max_pressure_frame.overall_state,
            "peak_band": max_pressure_frame.overall_band,
            "peak_frame_index": max_pressure_frame.index,
        },
        "frames": [asdict(frame) for frame in frames],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an SCBE audio gate spectrum report from a WAV file.")
    parser.add_argument("--wav", required=True, help="Path to a PCM WAV file")
    parser.add_argument("--frame-size", type=int, default=2048)
    parser.add_argument("--hop-size", type=int, default=1024)
    parser.add_argument("--hf-cutoff", type=float, default=0.5, help="High-frequency cutoff ratio [0,1]")
    parser.add_argument("--output", default="", help="Optional JSON output path")
    args = parser.parse_args()

    wav_path = Path(args.wav).expanduser().resolve()
    signal, sample_rate = read_wav_mono(wav_path)
    report = analyze_wav(
        signal=signal,
        sample_rate=sample_rate,
        frame_size=args.frame_size,
        hop_size=args.hop_size,
        hf_cutoff_ratio=args.hf_cutoff,
    )
    report["input_wav"] = str(wav_path)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(output_path)
    else:
        print(json.dumps(report, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
