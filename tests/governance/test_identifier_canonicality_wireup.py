"""Wire-up tests for identifier-canonicality overlay on RuntimeGate.

Contract:
  1. flag off                       -> no behavior change
  2. flag on  + clean code          -> ALLOW + receipt
  3. flag on  + mixed-script id     -> DENY + immune
  4. flag on  + confusable-only id  -> QUARANTINE
  5. flag on  + invisible char      -> DENY + immune
  6. flag on  + legitimate Greek    -> ALLOW (non_ascii annotation)
  7. base DENY + canonicality clean -> stays DENY (monotonic)
  8. prose with code keywords       -> NOT DENY (heuristic safety)
  9. env-var enables overlay
 10. tamper + canonicality compose: both signals visible in receipts
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.governance.runtime_gate import Decision, RuntimeGate  # noqa: E402


CLEAN_PY = "def add(x, y):\n    return x + y\n"
MIXED_SCRIPT_PY = "def login(pаssword):\n    return pаssword\n"  # Cyrillic а
CONFUSABLE_PY = "def get():\n    аре = 1\n    return аре\n"  # all Cyrillic
INVISIBLE_PY = "def admin‍_check(x):\n    return x\n"  # ZWJ
GREEK_PY = "def τ(x):\n    return x\n"  # legitimate Greek single-script


# --------------------------------------------------------------------------- #
#  1. flag off — no behavior change
# --------------------------------------------------------------------------- #

def test_flag_off_default_is_no_op():
    gate = RuntimeGate()
    assert gate._identifier_canonicality_enabled is False
    result = gate.evaluate(MIXED_SCRIPT_PY)
    assert result.identifier_canonicality_kind == ""
    assert result.identifier_canonicality_action == ""
    assert result.identifier_canonicality_score == 0.0
    assert not any("identifier_canonicality" in s for s in result.signals)


# --------------------------------------------------------------------------- #
#  2. flag on + clean -> ALLOW with receipt
# --------------------------------------------------------------------------- #

def test_flag_on_clean_allows_with_receipt():
    gate = RuntimeGate(use_identifier_canonicality=True)
    result = gate.evaluate(CLEAN_PY)
    assert result.decision == Decision.ALLOW
    assert result.identifier_canonicality_kind == "clean"
    assert result.identifier_canonicality_action == "ALLOW"
    assert result.identifier_canonicality_score == 0.0
    assert result.identifier_canonicality_fingerprint is not None
    assert any(s.startswith("identifier_canonicality(") for s in result.signals)


# --------------------------------------------------------------------------- #
#  3. mixed-script -> DENY + immune
# --------------------------------------------------------------------------- #

def test_mixed_script_attack_denies():
    gate = RuntimeGate(use_identifier_canonicality=True)
    result = gate.evaluate(MIXED_SCRIPT_PY)
    assert result.decision == Decision.DENY
    assert result.identifier_canonicality_kind == "mixed_script"
    assert result.identifier_canonicality_action == "DENY"
    assert any("identifier_canonicality_veto_deny" in s for s in result.signals)
    assert result.action_hash in gate._immune


# --------------------------------------------------------------------------- #
#  4. confusable-only -> QUARANTINE
# --------------------------------------------------------------------------- #

def test_confusable_only_quarantines():
    gate = RuntimeGate(use_identifier_canonicality=True)
    result = gate.evaluate(CONFUSABLE_PY)
    # QUARANTINE-recommendation overrides calibration ALLOW
    assert result.decision == Decision.QUARANTINE
    assert result.identifier_canonicality_kind == "confusable"
    assert result.identifier_canonicality_action == "QUARANTINE"
    assert any("identifier_canonicality_veto_quarantine" in s for s in result.signals)


# --------------------------------------------------------------------------- #
#  5. invisible char -> DENY + immune
# --------------------------------------------------------------------------- #

def test_invisible_char_denies():
    gate = RuntimeGate(use_identifier_canonicality=True)
    result = gate.evaluate(INVISIBLE_PY)
    assert result.decision == Decision.DENY
    assert result.identifier_canonicality_kind == "invisible"
    assert result.identifier_canonicality_score == 1.0
    assert any("identifier_canonicality_veto_deny" in s for s in result.signals)


# --------------------------------------------------------------------------- #
#  6. legitimate Greek -> ALLOW (non_ascii)
# --------------------------------------------------------------------------- #

def test_legitimate_greek_allows():
    gate = RuntimeGate(use_identifier_canonicality=True)
    result = gate.evaluate(GREEK_PY)
    assert result.decision == Decision.ALLOW
    assert result.identifier_canonicality_kind == "non_ascii"
    assert result.identifier_canonicality_action == "ALLOW"


# --------------------------------------------------------------------------- #
#  7. base DENY (immune-hit) + canonicality clean -> stays DENY
# --------------------------------------------------------------------------- #

def test_base_deny_plus_canonicality_clean_stays_deny():
    gate = RuntimeGate(use_identifier_canonicality=True)
    import hashlib

    h = hashlib.blake2s(CLEAN_PY.encode("utf-8", errors="replace"), digest_size=8).hexdigest()
    gate._immune.add(h)
    result = gate.evaluate(CLEAN_PY)
    assert result.decision == Decision.DENY
    # Receipt should still surface the clean canonicality assessment
    assert result.identifier_canonicality_kind == "clean"


# --------------------------------------------------------------------------- #
#  8. prose with code keywords -> NOT DENY (heuristic safety)
# --------------------------------------------------------------------------- #

def test_prose_with_code_keywords_not_denied():
    gate = RuntimeGate(use_identifier_canonicality=True)
    for text in [
        "Please write a function that sorts a list of numbers.",
        "Import duty applies to this category from the spec.",
        "Return to the previous step and try again.",
        "The class action settlement covers all members.",
    ]:
        result = gate.evaluate(text)
        assert result.decision != Decision.DENY, f"prose denied: {text!r}"
        assert result.identifier_canonicality_kind == ""


# --------------------------------------------------------------------------- #
#  9. env-var enablement
# --------------------------------------------------------------------------- #

def test_env_var_enables_overlay(monkeypatch):
    monkeypatch.setenv("SCBE_ENABLE_IDENTIFIER_CANONICALITY_GATE", "1")
    gate = RuntimeGate()
    assert gate._identifier_canonicality_enabled is True


def test_env_var_explicit_kwarg_wins(monkeypatch):
    monkeypatch.setenv("SCBE_ENABLE_IDENTIFIER_CANONICALITY_GATE", "1")
    gate = RuntimeGate(use_identifier_canonicality=False)
    assert gate._identifier_canonicality_enabled is False


# --------------------------------------------------------------------------- #
#  10. tamper + canonicality compose — both signals visible
# --------------------------------------------------------------------------- #

def test_tamper_and_canonicality_compose():
    """Both overlays on at once: both receipts must appear in audit."""
    gate = RuntimeGate(
        use_bijective_tamper=True,
        use_identifier_canonicality=True,
    )
    result = gate.evaluate(CLEAN_PY)
    receipts = [s for s in result.signals if "(" in s]
    has_tamper = any(s.startswith("bijective_tamper(") for s in receipts)
    has_canon = any(s.startswith("identifier_canonicality(") for s in receipts)
    assert has_tamper, f"missing bijective_tamper receipt; got {receipts}"
    assert has_canon, f"missing identifier_canonicality receipt; got {receipts}"
    # Both fields populated
    assert result.bijective_tamper_kind == "none"
    assert result.identifier_canonicality_kind == "clean"


def test_canonicality_deny_short_circuits_with_tamper_receipt():
    """When canonicality says DENY, the receipt for any concurrently-enabled
    tamper signal must still appear in the short-circuit signals."""
    gate = RuntimeGate(
        use_bijective_tamper=True,
        use_identifier_canonicality=True,
    )
    result = gate.evaluate(MIXED_SCRIPT_PY)
    assert result.decision == Decision.DENY
    has_tamper = any(s.startswith("bijective_tamper(") for s in result.signals)
    has_canon = any(s.startswith("identifier_canonicality(") for s in result.signals)
    assert has_tamper, f"missing tamper receipt in DENY signals: {result.signals}"
    assert has_canon, f"missing canonicality receipt in DENY signals: {result.signals}"
