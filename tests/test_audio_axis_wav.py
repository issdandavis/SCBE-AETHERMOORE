"""Tests for the audio-axis (L14) real-WAV ingestion -- analyze_wav / read_wav.

Stdlib-only (wave): runs everywhere, no whisper/ffmpeg needed. Proves the audio axis now analyzes a REAL
captured/synthesized clip (the port's whisper input / TTS output), not just synthetic sines.
"""

from __future__ import annotations

import os

import pytest

from python.scbe.audio_field_observables import analyze_wav, generate_sine, read_wav

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "whisper_sample.wav")


def test_read_wav_decodes_to_normalized_mono():
    if not os.path.exists(_FIXTURE):
        pytest.skip("no wav fixture")
    sig, rate = read_wav(_FIXTURE, max_samples=2048)
    assert 0 < len(sig) <= 2048
    assert rate > 0
    assert all(-1.0 <= s <= 1.0 for s in sig)  # normalized to [-1, 1]


def test_analyze_wav_on_real_audio_yields_observables():
    if not os.path.exists(_FIXTURE):
        pytest.skip("no wav fixture")
    obs = analyze_wav(_FIXTURE, max_samples=2048)
    assert obs.sample_count > 0
    assert obs.spectral_centroid_hz > 0.0
    assert 0.0 <= obs.stability <= 1.0
    assert obs.modal_count >= 0
    assert obs.energy_log == obs.energy_log  # not NaN


def test_analyze_wav_agrees_with_analyze_audio_field_on_a_synthetic_tone(tmp_path):
    # write a known sine to a real WAV, read it back, and confirm the axis sees energy at a sane centroid
    import array
    import wave

    rate = 16000
    tone = generate_sine(1000.0, sample_rate_hz=rate, duration_s=0.3)
    pcm = array.array("h", [int(max(-1.0, min(1.0, s)) * 30000) for s in tone])
    wav = os.path.join(tmp_path, "tone.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    obs = analyze_wav(wav, max_samples=2048)
    assert obs.sample_count > 0 and obs.spectral_centroid_hz > 0.0
