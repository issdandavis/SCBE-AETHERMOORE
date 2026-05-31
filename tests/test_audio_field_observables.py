from __future__ import annotations

import pytest

from python.scbe.audio_field_observables import (
    AudioFieldModel,
    analyze_audio_field,
    generate_decaying_sine,
    generate_sine,
)


def test_high_frequency_ratio_tracks_signal_band() -> None:
    low = analyze_audio_field(
        generate_sine(100.0, sample_rate_hz=2048.0, duration_s=0.25),
        sample_rate_hz=2048.0,
        high_frequency_cutoff_ratio=0.5,
    )
    high = analyze_audio_field(
        generate_sine(800.0, sample_rate_hz=2048.0, duration_s=0.25),
        sample_rate_hz=2048.0,
        high_frequency_cutoff_ratio=0.5,
    )

    assert low.high_frequency_ratio < 0.05
    assert high.high_frequency_ratio > 0.95
    assert low.stability > high.stability


def test_reverberation_decay_proxy_detects_decay() -> None:
    observed = analyze_audio_field(
        generate_decaying_sine(
            220.0,
            sample_rate_hz=4096.0,
            duration_s=0.12,
            decay_seconds=0.025,
        ),
        sample_rate_hz=4096.0,
    )

    assert observed.reverberation_decay_s is not None
    assert observed.reverberation_decay_s > 0


def test_generic_model_does_not_claim_magnetic_field() -> None:
    observed = analyze_audio_field(
        generate_sine(440.0, sample_rate_hz=4096.0, duration_s=0.05),
        sample_rate_hz=4096.0,
    )

    assert observed.field_coupling_proxy is None
    assert observed.field_relationship == "unmodeled-acoustic-observation"
    assert "not standalone magnetic-field measurements" in observed.claim_boundary[0]


def test_magnetoelastic_model_emits_bounded_coupling_proxy() -> None:
    observed = analyze_audio_field(
        generate_sine(440.0, sample_rate_hz=4096.0, duration_s=0.05),
        sample_rate_hz=4096.0,
        model=AudioFieldModel(
            kind="magnetoelastic", name="thin-film-saw", coupling_gain=0.8
        ),
    )

    assert observed.field_relationship == "strain-magnetization coupling proxy"
    assert observed.field_coupling_proxy is not None
    assert 0.0 <= observed.field_coupling_proxy <= 1.0


def test_magnetosonic_model_requires_wave_speeds() -> None:
    missing = analyze_audio_field(
        generate_sine(120.0, sample_rate_hz=2048.0, duration_s=0.05),
        sample_rate_hz=2048.0,
        model=AudioFieldModel(kind="magnetosonic", name="plasma-no-speeds"),
    )
    with_speeds = analyze_audio_field(
        generate_sine(120.0, sample_rate_hz=2048.0, duration_s=0.05),
        sample_rate_hz=2048.0,
        model=AudioFieldModel(
            kind="magnetosonic",
            name="declared-plasma",
            sound_speed_mps=10_000.0,
            alfven_speed_mps=30_000.0,
        ),
    )

    assert missing.field_coupling_proxy is None
    assert "missing" in missing.field_relationship
    assert (
        with_speeds.field_relationship
        == "compressibility-magnetic-pressure coupling proxy"
    )
    assert with_speeds.field_coupling_proxy is not None
    assert 0.0 <= with_speeds.field_coupling_proxy <= 1.0


def test_modal_count_is_recoupled_to_integer_state() -> None:
    signal = [
        a + b
        for a, b in zip(
            generate_sine(128.0, sample_rate_hz=2048.0, duration_s=0.25),
            generate_sine(384.0, sample_rate_hz=2048.0, duration_s=0.25, amplitude=0.6),
        )
    ]
    observed = analyze_audio_field(signal, sample_rate_hz=2048.0)

    assert observed.modal_count >= 2
    assert observed.modal_count_state.ok is True
    assert observed.modal_count_state.recoupled_value == pytest.approx(
        float(observed.modal_count)
    )
