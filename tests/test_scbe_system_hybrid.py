from __future__ import annotations

from benchmarks.scbe.baselines.scbe_system import SCBESystem
from src.governance.runtime_gate import RuntimeGate


def test_scbe_system_builds_runtime_gate_with_hybrid_config():
    system = SCBESystem(
        use_classifier=True,
        classifier_quarantine_threshold=0.7,
        classifier_deny_threshold=0.9,
    )

    assert system._gate is not None
    assert system._gate._classifier_enabled is True
    assert system._gate._classifier_quarantine_threshold == 0.7
    assert system._gate._classifier_deny_threshold == 0.9


def test_scbe_system_detect_surfaces_classifier_metadata():
    system = SCBESystem(use_classifier=True)
    system._gate = RuntimeGate(
        classifier_scorer=lambda text: 0.91 if "masked attack" in text else 0.05,
        reroute_rules=[],
    )
    system.calibrate([f"Clean calibration {i}" for i in range(5)])

    detected, signals, metadata = system.detect("masked attack phrased as a routine request")

    assert detected is True
    assert any("classifier_" in signal for signal in signals)
    assert metadata["classifier_score"] is not None
    assert metadata["classifier_score"] >= 0.91
    assert metadata["flags"]["classifier_flagged"] is True


def test_scbe_system_reset_preserves_hybrid_gate_config():
    system = SCBESystem(
        use_classifier=True,
        classifier_quarantine_threshold=0.73,
        classifier_deny_threshold=0.95,
    )

    system.reset()

    assert system._gate is not None
    assert system._gate._classifier_enabled is True
    assert system._gate._classifier_quarantine_threshold == 0.73
    assert system._gate._classifier_deny_threshold == 0.95
