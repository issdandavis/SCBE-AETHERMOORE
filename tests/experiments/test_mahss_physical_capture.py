from __future__ import annotations

import csv
import wave

import numpy as np
import pytest

from scripts.experiments.mahss_physical_capture import (
    import_wav_to_csv,
    normalize_trace,
    read_wav_mono,
    trim_trace,
)
from scripts.experiments.mahss_topology_validation import load_measurement_csv, run_measurement_validation


def _write_wav(path, samples: np.ndarray, sample_rate: int = 8000) -> None:
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * np.iinfo(np.int16).max).astype(np.int16)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())


def test_normalize_trace_centers_and_scales() -> None:
    trace = normalize_trace(np.asarray([1.0, 2.0, 3.0]))

    assert float(np.mean(trace)) == pytest.approx(0.0)
    assert float(np.max(np.abs(trace))) == pytest.approx(1.0)


def test_read_wav_mono_imports_pcm_trace(tmp_path) -> None:
    wav_path = tmp_path / "tap.wav"
    samples = np.sin(np.linspace(0.0, 8.0 * np.pi, 256))
    _write_wav(wav_path, samples)

    sample_rate, trace = read_wav_mono(wav_path)

    assert sample_rate == 8000
    assert trace.shape == (256,)
    assert float(np.max(np.abs(trace))) == pytest.approx(1.0)


def test_import_wav_to_csv_appends_measurement_rows(tmp_path) -> None:
    output = tmp_path / "measurements.csv"
    wav_a = tmp_path / "seed_a.wav"
    wav_b = tmp_path / "seed_b.wav"
    t = np.linspace(0.0, 1.0, 512, endpoint=False)
    _write_wav(wav_a, np.exp(-3.0 * t) * np.sin(2.0 * np.pi * 35.0 * t))
    _write_wav(wav_b, np.exp(-2.5 * t) * np.sin(2.0 * np.pi * 67.0 * t))

    for repeat in range(2):
        import_wav_to_csv(wav_a, output, seed="part-a", repeat=repeat, max_samples=256)
        import_wav_to_csv(wav_b, output, seed="part-b", repeat=repeat, max_samples=256)

    with output.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    loaded = load_measurement_csv(output)
    report = run_measurement_validation(loaded, enrollment_repeats=1)

    assert len(rows) == 4 * 256
    assert set(loaded) == {"part-a", "part-b"}
    assert report["seed_count"] == 2


def test_trim_trace_rejects_too_short_trace() -> None:
    with pytest.raises(ValueError, match="16"):
        trim_trace(np.arange(10), max_samples=10)
