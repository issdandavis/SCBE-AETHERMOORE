from src.spiralverse.temporal_intent import (
    TEMPORAL_CURVATURE_ALPHA,
    TEMPORAL_OMEGA_TELEMETRY_SCHEMA_VERSION,
    TemporalSecurityGate,
    validate_telemetry_event,
)


def test_build_telemetry_event_reports_fixed_alpha_and_live_lock_values() -> None:
    gate = TemporalSecurityGate()
    gate.record_observation("agent-alpha", distance=0.42, velocity=0.08, harmony=0.15)
    lock = gate.compute_lock_vector("agent-alpha", triadic_stable=0.88, spectral_score=0.91)

    event = gate.build_telemetry_event(
        "agent-alpha",
        layer="L2",
        stage="active",
        triadic_stable=0.88,
        spectral_score=0.91,
        lock_vector=lock,
        timestamp=1234.5,
    )

    assert event["schema_version"] == TEMPORAL_OMEGA_TELEMETRY_SCHEMA_VERSION
    assert event["t"] == 1234.5
    assert event["state"]["alpha"] == TEMPORAL_CURVATURE_ALPHA
    assert event["state"]["d"] == lock.distance
    assert event["state"]["x"] == lock.x_factor
    assert event["temporal"]["H_eff"] == lock.harmonic_wall
    assert event["temporal"]["harm_score"] == lock.harm_score
    assert event["omega"]["omega_score"] == lock.omega
    assert event["omega"]["weakest_lock"] == lock.weakest_lock
    assert event["outcome"]["decision"] == lock.decision
    assert validate_telemetry_event(event) is event


def test_emit_telemetry_event_appends_and_filters_recent_log() -> None:
    gate = TemporalSecurityGate()
    gate.record_observation("agent-a", distance=0.25, velocity=0.02, harmony=0.4)
    gate.record_observation("agent-b", distance=0.55, velocity=0.11, harmony=-0.2)

    gate.emit_telemetry_event("agent-a", stage="analysis", triadic_stable=0.95, spectral_score=0.93)
    event_b = gate.emit_telemetry_event("agent-b", stage="analysis", triadic_stable=0.72, spectral_score=0.81)

    assert len(gate.recent_telemetry()) == 2
    assert gate.recent_telemetry(agent_id="agent-b", limit=5) == [event_b]


def test_validate_telemetry_event_rejects_missing_sublock() -> None:
    gate = TemporalSecurityGate()
    gate.record_observation("agent-bad", distance=0.33, velocity=0.04, harmony=0.1)
    event = gate.build_telemetry_event("agent-bad")
    event["omega"]["sublocks"].pop("spectral")

    try:
        validate_telemetry_event(event)
    except ValueError as exc:
        assert "omega.sublocks" in str(exc)
    else:
        raise AssertionError("Expected malformed telemetry payload to fail validation")
