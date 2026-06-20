"""Wire-up tests for Tree of Escalation v1.0 overlay on RuntimeGate.

Contract:
  1. flag off                                  -> no toe behavior
  2. flag on  + clean code (post-calibration)  -> toe fields populated +
                                                  receipt in signals
  3. flag on  + early fast-path (calibration)  -> toe fields populated
                                                  even though receipt
                                                  signal absent
  4. env-var enables overlay
  5. explicit kwarg beats env
  6. toe is observational: never overrides decision
  7. compose with bijective_tamper + canonicality enabled simultaneously
  8. toe_terminated_as values are valid
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.governance.runtime_gate import Decision, RuntimeGate  # noqa: E402

CLEAN_PY = "def add(x, y):\n    return x + y\n"


def _drain_calibration(gate: RuntimeGate, payloads=("def f(x):\n    return x\n",)) -> None:
    """Burn through calibration warm-up so the next evaluate hits the main path."""
    for _ in range(8):
        for p in payloads:
            gate.evaluate(p)


# --------------------------------------------------------------------------- #
#  1. flag off — no behavior change
# --------------------------------------------------------------------------- #


def test_flag_off_default_is_no_op():
    gate = RuntimeGate()
    assert gate._tree_of_escalation_enabled is False
    result = gate.evaluate(CLEAN_PY)
    assert result.toe_terminated_as == ""
    assert result.toe_tier_reached == 0
    assert result.toe_provisional_minted is False
    assert result.toe_abridged_form_hex == ""
    assert not any("tree_of_escalation" in s for s in result.signals)


# --------------------------------------------------------------------------- #
#  2. flag on + clean (post-calibration) — fields + signal
# --------------------------------------------------------------------------- #


def test_flag_on_clean_post_calibration_emits_receipt():
    gate = RuntimeGate(use_tree_of_escalation=True)
    _drain_calibration(gate)
    result = gate.evaluate(CLEAN_PY)
    assert result.decision == Decision.ALLOW
    assert result.toe_terminated_as == "abridged"
    assert result.toe_tier_reached >= 2  # at least the bicameral pair
    assert result.toe_provisional_minted is False
    assert result.toe_abridged_form_hex  # non-empty
    assert any(s.startswith("tree_of_escalation(") for s in result.signals)


# --------------------------------------------------------------------------- #
#  3. fields populated even on calibration fast-path
# --------------------------------------------------------------------------- #


def test_fields_populated_on_calibration_fast_path():
    gate = RuntimeGate(use_tree_of_escalation=True)
    # First call goes straight to calibration warm-up — receipt signal
    # may not be appended (that lives on the main pipeline return) but
    # the structured GateResult fields MUST be populated.
    result = gate.evaluate(CLEAN_PY)
    assert result.toe_terminated_as == "abridged"
    assert result.toe_tier_reached >= 2
    assert result.toe_abridged_form_hex


# --------------------------------------------------------------------------- #
#  4. env-var enablement
# --------------------------------------------------------------------------- #


def test_env_var_enables_overlay(monkeypatch):
    monkeypatch.setenv("SCBE_ENABLE_TREE_OF_ESCALATION_GATE", "1")
    gate = RuntimeGate()
    assert gate._tree_of_escalation_enabled is True


def test_env_var_explicit_kwarg_wins(monkeypatch):
    monkeypatch.setenv("SCBE_ENABLE_TREE_OF_ESCALATION_GATE", "1")
    gate = RuntimeGate(use_tree_of_escalation=False)
    assert gate._tree_of_escalation_enabled is False


# --------------------------------------------------------------------------- #
#  5. toe is observational — never overrides the base decision (v1.0)
# --------------------------------------------------------------------------- #


def test_toe_does_not_override_base_decision_on_clean_input():
    """Without ToE the decision is ALLOW; with ToE it must STILL be ALLOW."""
    base = RuntimeGate()
    _drain_calibration(base)
    base_result = base.evaluate(CLEAN_PY)

    with_toe = RuntimeGate(use_tree_of_escalation=True)
    _drain_calibration(with_toe)
    toe_result = with_toe.evaluate(CLEAN_PY)

    assert base_result.decision == toe_result.decision


# --------------------------------------------------------------------------- #
#  6. compose with bijective_tamper + canonicality
# --------------------------------------------------------------------------- #


def test_toe_composes_with_other_overlays():
    gate = RuntimeGate(
        use_bijective_tamper=True,
        use_identifier_canonicality=True,
        use_tree_of_escalation=True,
    )
    _drain_calibration(gate)
    result = gate.evaluate(CLEAN_PY)
    receipts = [s for s in result.signals if "(" in s]
    has_tamper = any(s.startswith("bijective_tamper(") for s in receipts)
    has_canon = any(s.startswith("identifier_canonicality(") for s in receipts)
    has_toe = any(s.startswith("tree_of_escalation(") for s in receipts)
    assert has_tamper, f"missing tamper receipt; got {receipts}"
    assert has_canon, f"missing canonicality receipt; got {receipts}"
    assert has_toe, f"missing toe receipt; got {receipts}"


# --------------------------------------------------------------------------- #
#  7. terminated_as values are valid strings from the Termination enum
# --------------------------------------------------------------------------- #


def test_terminated_as_values_are_known():
    valid = {"abridged", "provisional", "refused", "incomplete"}
    gate = RuntimeGate(use_tree_of_escalation=True)
    for payload in [
        CLEAN_PY,
        "def f(x):\n    return x * 2\n",
        "def g():\n    return 42\n",
    ]:
        result = gate.evaluate(payload)
        assert result.toe_terminated_as in valid


# --------------------------------------------------------------------------- #
#  8. prose payloads still get a toe observation (HashReader works on bytes)
# --------------------------------------------------------------------------- #


def test_prose_payload_still_observed():
    gate = RuntimeGate(use_tree_of_escalation=True)
    result = gate.evaluate("Please write a function that sorts a list of numbers.")
    # ToE runs on raw bytes so prose doesn't bypass it (unlike the
    # canonicality / tamper gates which require code-shaped input).
    assert result.toe_terminated_as in {"abridged", "provisional", "refused"}
