from hydra.turnstile import (
    compute_antibody_load,
    compute_membrane_stress,
    resolve_turnstile,
)


def test_browser_quarantine_holds_for_review():
    outcome = resolve_turnstile(
        decision="QUARANTINE",
        domain="browser",
        suspicion=0.4,
        geometry_norm=0.7,
    )
    assert outcome.action == "HOLD"
    assert outcome.require_human is True
    assert outcome.continue_execution is False


def test_vehicle_quarantine_pivots_not_stalls():
    outcome = resolve_turnstile(
        decision="QUARANTINE",
        domain="vehicle",
        suspicion=0.6,
        geometry_norm=0.8,
    )
    assert outcome.action == "PIVOT"
    assert outcome.require_human is False
    assert outcome.continue_execution is True


def test_fleet_escalate_degrades_without_global_stop():
    outcome = resolve_turnstile(
        decision="ESCALATE",
        domain="fleet",
        suspicion=0.5,
        geometry_norm=0.75,
        quorum_ok=True,
    )
    assert outcome.action == "DEGRADE"
    assert outcome.continue_execution is True


def test_high_geometry_or_antibody_triggers_honeypot():
    outcome = resolve_turnstile(
        decision="DENY",
        domain="antivirus",
        suspicion=0.95,
        geometry_norm=float("inf"),
    )
    assert outcome.action == "HONEYPOT"
    assert outcome.deploy_honeypot is True
    assert outcome.isolate is True


def test_cell_math_functions_are_bounded():
    load = compute_antibody_load(suspicion=0.8, previous_load=0.6, dt=1.0, half_life=10.0)
    stress = compute_membrane_stress(norm_value=0.99, threshold=0.98)
    assert 0.0 <= load <= 1.0
    assert 0.0 <= stress <= 1.0
