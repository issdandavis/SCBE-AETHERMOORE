"""Tests for the v6f gate-result interpreter.

Mocks ``hf jobs logs`` output as a fixture string, then verifies the
verdict mapping logic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.eval.interpret_v6f_gate_result import _find_event, _verdict


def test_find_event_picks_last_matching():
    """When the log has multiple events of the same name (e.g. per-prompt
    gate_prompt events plus a final gate_report), find the FINAL one."""

    log = "\n".join(
        [
            '{"event": "gate_prompt", "id": "p1", "ok": true}',
            '{"event": "gate_prompt", "id": "p2", "ok": false}',
            '{"event": "gate_report", "report": {"pass_rate": 0.5}}',
            '{"event": "gate_prompt", "id": "p3", "ok": true}',  # noisy trailing
        ]
    )
    event = _find_event(log, "gate_report")
    assert event is not None
    assert event["report"]["pass_rate"] == 0.5


def test_find_event_returns_none_when_absent():
    log = '{"event": "gate_prompt", "id": "p1", "ok": true}\n'
    assert _find_event(log, "gate_report") is None


def test_verdict_green_when_shim_high_and_raw_above_half():
    """Shim 0.95+ AND raw 0.5+ = SFT internalized discipline → ship."""

    report = {
        "pass_rate": 0.97,
        "raw_pass_rate": 0.66,
        "must_pass_all_ok": True,
        "overall_pass": True,
        "minimum_pass_rate": 0.7,
        "production_shim_gate": True,
    }
    verdict, advice = _verdict(report)
    assert "GREEN" in verdict
    assert any("internalized the discipline" in a for a in advice)


def test_verdict_amber_when_shim_passes_but_raw_low():
    """Shim clears threshold but bare model is below 0.5 = ship as
    shim-required adapter."""

    report = {
        "pass_rate": 0.83,
        "raw_pass_rate": 0.08,
        "must_pass_all_ok": True,
        "overall_pass": True,
        "minimum_pass_rate": 0.7,
        "production_shim_gate": True,
    }
    verdict, advice = _verdict(report)
    assert "AMBER" in verdict
    assert any("shim-required" in a for a in advice)


def test_verdict_red_when_must_pass_missed():
    """A must_pass failure dominates regardless of overall pass_rate."""

    report = {
        "pass_rate": 0.83,
        "raw_pass_rate": 0.5,
        "must_pass_all_ok": False,
        "overall_pass": False,
        "minimum_pass_rate": 0.7,
        "production_shim_gate": True,
    }
    verdict, advice = _verdict(report)
    assert "RED" in verdict
    assert any("must_pass" in a for a in advice)


def test_verdict_red_when_below_minimum():
    """Below pass_rate threshold without must_pass help."""

    report = {
        "pass_rate": 0.5,
        "raw_pass_rate": 0.2,
        "must_pass_all_ok": True,
        "overall_pass": False,
        "minimum_pass_rate": 0.7,
        "production_shim_gate": True,
    }
    verdict, advice = _verdict(report)
    assert "RED" in verdict
    # Should mention the diagnosis fork (drift vs capability)
    assert any("drift" in a.lower() or "capability" in a.lower() for a in advice)


def test_verdict_warns_on_legacy_scaffold_only():
    """If production_shim_gate flag absent, the gate was the legacy fake-pass
    mode and we must surface that the pass_rate is not a real verdict."""

    report = {
        "pass_rate": 1.0,
        "raw_pass_rate": 0.083,
        "must_pass_all_ok": True,
        "overall_pass": True,
        "minimum_pass_rate": 0.7,
        # production_shim_gate omitted -> defaults False in _verdict
    }
    _, advice = _verdict(report)
    assert any("legacy scaffolded-gate" in a or "fake-pass" in a for a in advice)


def test_verdict_lift_calculation():
    """When both pass_rate and raw_pass_rate are positive, advice should
    include the per-percentage-point lift."""

    report = {
        "pass_rate": 0.83,
        "raw_pass_rate": 0.083,
        "must_pass_all_ok": True,
        "overall_pass": True,
        "minimum_pass_rate": 0.7,
        "production_shim_gate": True,
    }
    _, advice = _verdict(report)
    assert any("shim lift over bare model" in a for a in advice)
    # 0.83 - 0.083 = 0.747 = +74.7pp
    assert any("+74.7 pp" in a for a in advice)
