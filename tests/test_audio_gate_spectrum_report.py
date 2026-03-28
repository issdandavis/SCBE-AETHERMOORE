from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np

from scripts.audio_gate_spectrum_report import (
    analyze_wav,
    pressure_to_state,
    pressure_to_wavelength,
    read_wav_mono,
    wavelength_to_band,
)


def _write_sine_wav(
    path: Path,
    frequency: float = 440.0,
    sample_rate: int = 44100,
    seconds: float = 0.12,
) -> None:
    samples = int(sample_rate * seconds)
    values = []
    for n in range(samples):
        value = int(0.6 * 32767 * math.sin((2 * math.pi * frequency * n) / sample_rate))
        values.append(value)
    data = np.array(values, dtype=np.int16)

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(data.tobytes())


def test_visible_spectrum_helpers():
    assert pressure_to_wavelength(0.0) == 380.0
    assert pressure_to_wavelength(1.0) == 700.0
    assert wavelength_to_band(380.0) == "violet"
    assert wavelength_to_band(700.0) == "red"
    assert pressure_to_state(0.0) == "stable"
    assert pressure_to_state(1.0) == "breaking"


def test_read_wav_and_analyze(tmp_path: Path):
    wav_path = tmp_path / "tone.wav"
    _write_sine_wav(wav_path)

    signal, sample_rate = read_wav_mono(wav_path)
    assert sample_rate == 44100
    assert signal.ndim == 1
    assert len(signal) > 0

    report = analyze_wav(signal, sample_rate=sample_rate, frame_size=1024, hop_size=512)
    assert report["sample_rate"] == 44100
    assert report["frame_count"] >= 1
    assert "summary" in report
    assert "frames" in report

    first = report["frames"][0]
    assert len(first["band_pressures"]) == 6
    assert len(first["band_wavelengths_nm"]) == 6
    assert len(first["band_labels"]) == 6
    assert len(first["band_states"]) == 6
    assert 380.0 <= first["overall_wavelength_nm"] <= 700.0
