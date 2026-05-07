"""Tests for the v6f gate-result interpreter.

Mocks ``hf jobs logs`` output as a fixture string, then verifies the
verdict mapping logic.
"""

from __future__ import annotations

import subprocess
from unittest.mock import patch


from scripts.eval.interpret_v6f_gate_result import (
    _find_event,
    _verdict,
    _verify_hf_adapter,
)


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


def test_find_event_handles_multiline_pretty_printed_json():
    """training_complete is emitted by json.dumps(..., indent=2) — multi-line.
    The single-line regex misses it, so the parser must fall back to a
    brace-balanced scan."""

    log = "\n".join(
        [
            '{"event": "gate_prompt", "id": "p1", "ok": true}',
            "{",
            '  "event": "training_complete",',
            '  "summary": {',
            '    "profile_id": "scbe-coding-primary-7b-qlora-v6f",',
            '    "pushed_adapter": true,',
            '    "adapter_repo": "issdandavis/scbe-coding-primary-7b-qlora-v6f"',
            "  }",
            "}",
            '{"event": "push_attempt", "adapter_repo": "x"}',
        ]
    )
    event = _find_event(log, "training_complete")
    assert event is not None
    assert event["summary"]["pushed_adapter"] is True
    assert event["summary"]["adapter_repo"] == "issdandavis/scbe-coding-primary-7b-qlora-v6f"


def test_find_event_multiline_handles_strings_with_braces():
    """Brace-balanced scan must respect strings (a } inside a string value
    is not a structural close)."""

    log = "\n".join(
        [
            "{",
            '  "event": "training_complete",',
            '  "summary": {',
            '    "chat_template": "if x then {y} else z",',
            '    "pushed_adapter": false',
            "  }",
            "}",
        ]
    )
    event = _find_event(log, "training_complete")
    assert event is not None
    assert event["summary"]["pushed_adapter"] is False
    assert "if x then {y}" in event["summary"]["chat_template"]


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


def test_verify_hf_adapter_skips_when_repo_missing():
    ok, msg = _verify_hf_adapter(None)
    assert not ok
    assert "no adapter_repo" in msg


def test_verify_hf_adapter_calls_hf_models_info():
    """When repo is provided, shells out to 'hf models info' and reports
    PASS on returncode 0, FAIL otherwise."""

    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("scripts.eval.interpret_v6f_gate_result.subprocess.run", return_value=fake_ok) as mock_run:
        ok, msg = _verify_hf_adapter("issdandavis/scbe-coding-primary-7b-qlora-v6f")
        assert ok
        assert "huggingface.co/issdandavis/scbe-coding-primary-7b-qlora-v6f" in msg
        cmd = mock_run.call_args[0][0]
        assert cmd[:3] == ["hf", "models", "info"]
        assert "issdandavis/scbe-coding-primary-7b-qlora-v6f" in cmd

    fake_fail = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Repository not found")
    with patch("scripts.eval.interpret_v6f_gate_result.subprocess.run", return_value=fake_fail):
        ok, msg = _verify_hf_adapter("issdandavis/does-not-exist")
        assert not ok
        assert "Repository not found" in msg
