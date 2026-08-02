import math

import pytest

from python.scbe.phi_audio_axis import (
    PHI,
    RISK_AMPLITUDES,
    TONGUES,
    decode_ratioed_integers,
    encode_ratioed_integers,
    pairwise_fluctuations,
    phi_carriers,
    recover_l14_phi,
    synthesize_l14_phi,
)


def _circular_error(a, b):
    return abs(((a - b + 0.5) % 1.0) - 0.5)


def test_carriers_bind_both_phi_ladders_and_six_phase_sectors():
    carriers = phi_carriers()
    assert tuple(carrier.tongue for carrier in carriers) == TONGUES
    for k, carrier in enumerate(carriers):
        assert carrier.semantic_weight == pytest.approx(PHI**k)
        assert carrier.frequency_hz == pytest.approx(440.0 * PHI ** (k / 6))
        assert carrier.phase_sector_rad == pytest.approx(2 * math.pi * k / 6)


def test_pairwise_fluctuation_surface_has_all_fifteen_edges():
    rows = pairwise_fluctuations()
    assert len(rows) == 15
    assert all(row.beat_hz > 0.0 and row.envelope_period_s > 0.0 for row in rows)


@pytest.mark.parametrize("radial_power", [0.5, 1.0, 2.0])
def test_ratioed_integers_round_trip_through_radial_phase_tensor(radial_power):
    activations = (13, -8, 5, -3, 2, -1)
    tensor = encode_ratioed_integers(
        activations,
        peak_radius=0.75,
        radial_power=radial_power,
        rotation_rad=0.731,
    )
    assert decode_ratioed_integers(tensor) == activations
    assert len(tensor.real_tensor) == 12
    assert max(point.radius for point in tensor.points) == pytest.approx(0.75)
    assert tensor.head_amplitude == pytest.approx(
        max(abs(value) * PHI**k for k, value in enumerate(activations))
    )


def test_radial_power_spreads_or_bunches_but_keeps_the_head():
    activations = (21, 1, 1, 1, 1, 1)
    spread = encode_ratioed_integers(activations, radial_power=0.5)
    linear = encode_ratioed_integers(activations, radial_power=1.0)
    bunched = encode_ratioed_integers(activations, radial_power=2.0)
    assert spread.points[0].radius == pytest.approx(1.0)
    assert linear.points[0].radius == pytest.approx(1.0)
    assert bunched.points[0].radius == pytest.approx(1.0)
    assert spread.points[1].radius > linear.points[1].radius > bunched.points[1].radius


def test_aggressive_bunching_does_not_erase_small_nonzero_integer():
    activations = (-752, -79, -5, 504, -937, -203)
    tensor = encode_ratioed_integers(activations, radial_power=4.0, rotation_rad=-7.3)
    assert tensor.points[2].radius < 1e-8
    assert decode_ratioed_integers(tensor) == activations


def test_global_phase_rotation_changes_the_frame_not_the_integers():
    activations = (1, 2, 3, 5, 8, 13)
    base = encode_ratioed_integers(activations)
    rotated = encode_ratioed_integers(activations, rotation_rad=1.234)
    turn = complex(math.cos(1.234), math.sin(1.234))
    for point_a, point_b in zip(base.points, rotated.points):
        assert complex(point_b.real, point_b.imag) == pytest.approx(
            complex(point_a.real, point_a.imag) * turn
        )
    assert decode_ratioed_integers(rotated) == activations


def test_phase_scale_requires_integer_payload_and_valid_range_controls():
    with pytest.raises(TypeError):
        encode_ratioed_integers([1, 2, 3, 4, 5, 6.5])
    with pytest.raises(ValueError):
        encode_ratioed_integers([1, 2, 3, 4, 5, 6], peak_radius=0.0)
    with pytest.raises(ValueError):
        encode_ratioed_integers([1, 2, 3, 4, 5, 6], radial_power=0.0)


def test_l14_packet_uses_amplitude_phase_coherence_and_fft_observables():
    packet = synthesize_l14_phi(
        {"KO": 2, "AV": 1, "RU": 1, "CA": 2, "UM": 1, "DR": 1},
        intent=0.75,
        coherence=0.4,
        amplitude=0.3,
        sample_rate_hz=8000,
        duration_s=0.25,
        telemetry_samples=256,
    )
    assert packet.layer == "L14"
    assert packet.amplitude == pytest.approx(0.3)
    assert packet.risk_level is None
    assert packet.risk_gain == 1.0
    assert packet.envelope_end < 1.0
    assert sum(packet.tongue_mix.values()) == pytest.approx(1.0)
    assert len(packet.signal) == 2000
    assert max(abs(value) for value in packet.signal) <= packet.amplitude + 1e-12
    assert math.isfinite(packet.observables.energy_log)
    assert 0.0 <= packet.observables.stability <= 1.0


@pytest.mark.parametrize("intent", [0.0, 0.125, 0.75, 0.99])
@pytest.mark.parametrize("coherence", [0.0, 0.4, 1.0])
def test_six_carrier_superposition_recovers_mix_and_intent(intent, coherence):
    wanted = {"KO": 0.05, "AV": 0.10, "RU": 0.20, "CA": 0.25, "UM": 0.15, "DR": 0.25}
    packet = synthesize_l14_phi(
        wanted,
        intent=intent,
        coherence=coherence,
        amplitude=0.6,
        sample_rate_hz=8000,
        duration_s=0.25,
        telemetry_samples=128,
    )
    recovered = recover_l14_phi(
        packet.signal,
        coherence=coherence,
        sample_rate_hz=packet.sample_rate_hz,
    )
    for tongue in TONGUES:
        assert recovered.tongue_mix[tongue] == pytest.approx(wanted[tongue], abs=1e-10)
    assert _circular_error(recovered.intent, intent) < 1e-10
    assert recovered.total_amplitude == pytest.approx(packet.amplitude, abs=1e-10)
    assert recovered.relative_reconstruction_error < 1e-10


def test_optional_governance_gain_changes_amplitude_without_becoming_the_payload():
    mix = [1, 2, 3, 4, 5, 6]
    low = synthesize_l14_phi(mix, intent=0.2, coherence=1.0, amplitude=0.8, risk_level="LOW",
                             sample_rate_hz=8000, duration_s=0.1, telemetry_samples=64)
    critical = synthesize_l14_phi(mix, intent=0.2, coherence=1.0, amplitude=0.8, risk_level="CRITICAL",
                                  sample_rate_hz=8000, duration_s=0.1, telemetry_samples=64)
    recovered_low = recover_l14_phi(low.signal, coherence=1.0, sample_rate_hz=8000)
    recovered_critical = recover_l14_phi(critical.signal, coherence=1.0, sample_rate_hz=8000)
    assert recovered_low.tongue_mix == pytest.approx(recovered_critical.tongue_mix)
    assert recovered_critical.total_amplitude / recovered_low.total_amplitude == pytest.approx(0.1)
    assert critical.risk_gain == RISK_AMPLITUDES["CRITICAL"]
    assert critical.tongue_mix == low.tongue_mix


def test_invalid_or_dark_mix_is_rejected():
    with pytest.raises(ValueError):
        synthesize_l14_phi([0, 0, 0, 0, 0, 0], intent=0.5, coherence=0.5)
    with pytest.raises(ValueError):
        synthesize_l14_phi({"KO": 1, "BAD": 2}, intent=0.5, coherence=0.5)
