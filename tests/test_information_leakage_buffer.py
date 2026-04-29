"""Tests for the information leakage buffer simulator."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "scripts" / "experiments" / "information_leakage_buffer.py"
    spec = importlib.util.spec_from_file_location("information_leakage_buffer", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_sealed_symmetric_box_preserves_visibility() -> None:
    mod = _load()
    result = mod.simulate(mod.LeakageScenario(name="sealed", symmetric_noise=0.02))
    assert result.decision == "PRESERVE_BUFFER"
    assert result.route_metadata_leak == 0.0
    assert result.interference_visibility > 0.9


def test_reversible_buffer_can_be_erased() -> None:
    mod = _load()
    result = mod.simulate(
        mod.LeakageScenario(
            name="erased",
            buffer_coupling=0.9,
            erase_strength=0.98,
            symmetric_noise=0.02,
        )
    )
    assert result.route_metadata_leak < 0.05
    assert result.decision == "PRESERVE_BUFFER"


def test_irreversible_route_mark_becomes_leaky() -> None:
    mod = _load()
    result = mod.simulate(
        mod.LeakageScenario(name="leaky", environment_leak=0.7, symmetric_noise=0.02)
    )
    assert result.route_metadata_leak >= 0.7
    assert result.decision == "MEASURED_OR_LEAKY"


def test_common_mode_noise_is_not_route_metadata() -> None:
    mod = _load()
    result = mod.simulate(mod.LeakageScenario(name="common-mode", symmetric_noise=0.5))
    assert result.route_metadata_leak == 0.0
    assert result.interference_visibility > 0.4


def test_suite_has_all_decision_types() -> None:
    mod = _load()
    payload = mod.run_suite()
    assert payload["schema_version"] == "scbe_information_leakage_buffer_v1"
    decisions = {row["decision"] for row in payload["results"]}
    assert "PRESERVE_BUFFER" in decisions
    assert "WEAK_BUFFER_TEST" in decisions
    assert "MEASURED_OR_LEAKY" in decisions
