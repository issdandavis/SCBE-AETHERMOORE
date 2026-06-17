"""Wiring test for the optional ONNX injection-classifier second pass.

Verifies the integration logic WITHOUT downloading the ~740MB model: the hook is
inert by default (pure-Python gate unchanged) and, when a stub returns a high
injection probability, the gate lifts intent risk and escalates. The real model is
opt-in (SCBE_INTENT_MODEL=1) and exercised separately once it is installed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scbe  # noqa: E402


def test_hook_off_by_default(monkeypatch):
    monkeypatch.delenv("SCBE_INTENT_MODEL", raising=False)
    r = scbe.pipeline_quick_score("a perfectly ordinary sentence about gardening")
    assert "model:injection" not in r["intent_flags"]
    assert r["decision"] == "ALLOW"


def test_maybe_model_intent_none_when_disabled(monkeypatch):
    monkeypatch.delenv("SCBE_INTENT_MODEL", raising=False)
    assert scbe._maybe_model_intent("anything at all") is None


def test_hook_escalates_when_stub_flags(monkeypatch):
    # stub the classifier to a high injection probability; the wiring must lift risk
    monkeypatch.setattr(scbe, "_maybe_model_intent", lambda _t: 0.97)
    r = scbe.pipeline_quick_score("an otherwise innocuous looking request about flowers")
    assert "model:injection" in r["intent_flags"]
    assert r["decision"] in ("QUARANTINE", "ESCALATE", "DENY")


def test_hook_below_threshold_does_not_flag(monkeypatch):
    monkeypatch.setattr(scbe, "_maybe_model_intent", lambda _t: 0.5)
    r = scbe.pipeline_quick_score("a normal sentence about hiking trails")
    assert "model:injection" not in r["intent_flags"]
