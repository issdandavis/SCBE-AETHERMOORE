from __future__ import annotations

from src.spiralverse.temporal_intent import TemporalSecurityGate


def test_lock_vector_safe_vs_dangerous() -> None:
    gate = TemporalSecurityGate()

    for _ in range(3):
        gate.record_observation("safe", distance=0.10, velocity=0.00, harmony=0.8)
    safe = gate.compute_lock_vector("safe", pqc_valid=True, triadic_stable=1.0, spectral_score=1.0)

    for _ in range(10):
        gate.record_observation("danger", distance=0.92, velocity=0.08, harmony=-0.4)
    danger = gate.compute_lock_vector("danger", pqc_valid=True, triadic_stable=1.0, spectral_score=1.0)

    assert safe.omega > danger.omega
    assert safe.harm_score > danger.harm_score
    assert danger.latency_multiplier > safe.latency_multiplier


def test_lock_vector_permission_color_bands() -> None:
    gate = TemporalSecurityGate()
    gate.record_observation("c", distance=0.15, velocity=0.0, harmony=0.9)

    green = gate.compute_lock_vector("c", pqc_valid=True, triadic_stable=1.0, spectral_score=1.0)
    amber = gate.compute_lock_vector("c", pqc_valid=True, triadic_stable=0.45, spectral_score=0.9)
    red = gate.compute_lock_vector("c", pqc_valid=False, triadic_stable=1.0, spectral_score=1.0)

    assert green.permission_color == "green"
    assert amber.permission_color == "amber"
    assert red.permission_color == "red"
    assert red.omega == 0.0
