"""Wire-up tests for the bijective tamper overlay on RuntimeGate.

The contract under test:
  1. flag off                                  -> no behavior change vs baseline
  2. flag on  + clean code                     -> still ALLOW + receipt
  3. flag on  + user-submitted syntax-broken   -> NO-OP (input_invalid is not
     a tamper signal at this layer; prose looks the same to the parser)
  4. base DENY + tamper ALLOW                  -> stays DENY (monotonic)
  5. base ALLOW + synthetic kind="syntax"      -> DENY (true tamper escalates)
  6. prose with code keywords                  -> NOT DENY (heuristic safety)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.governance.runtime_gate import Decision, RuntimeGate  # noqa: E402

CLEAN_PY = "def add(x, y):\n    return x + y\n"
BROKEN_PY = "def add(:\n    return\n"


# --------------------------------------------------------------------------- #
#  1. flag off — no behavior change
# --------------------------------------------------------------------------- #


def test_flag_off_default_is_no_op():
    """With the flag off, the tamper overlay must not run at all."""
    gate = RuntimeGate()
    assert gate._bijective_tamper_enabled is False
    result = gate.evaluate(CLEAN_PY)
    assert result.bijective_tamper_action == ""
    assert result.bijective_tamper_kind == ""
    assert result.bijective_tamper_score == 0.0
    assert result.semantic_fingerprint is None
    assert not any("bijective_tamper" in s for s in result.signals)


def test_flag_off_does_not_deny_broken_code():
    """Without the flag, syntax-broken code is just text; gate uses base logic only."""
    gate = RuntimeGate()
    result = gate.evaluate(BROKEN_PY)
    assert not any("bijective_tamper" in s for s in result.signals)


# --------------------------------------------------------------------------- #
#  2. flag on  + clean code  -> ALLOW (with annotation)
# --------------------------------------------------------------------------- #


def test_flag_on_clean_code_allows():
    gate = RuntimeGate(use_bijective_tamper=True)
    assert gate._bijective_tamper_enabled is True
    result = gate.evaluate(CLEAN_PY)
    assert result.decision == Decision.ALLOW
    assert result.bijective_tamper_kind == "none"
    assert result.bijective_tamper_action == "ALLOW"
    assert result.bijective_tamper_score == 0.0
    assert result.semantic_fingerprint is not None
    assert any(s.startswith("bijective_tamper(") for s in result.signals)


# --------------------------------------------------------------------------- #
#  3. flag on  + user-submitted syntax-broken code  -> no-op
# --------------------------------------------------------------------------- #


def test_flag_on_user_syntax_broken_is_noop():
    """input_invalid is NOT a tamper signal at the runtime-gate layer.
    It just means the input did not parse — which is true for prose too.
    The genuine tamper case is kind='syntax' (decoded form fails to parse
    even though the original parsed)."""
    gate = RuntimeGate(use_bijective_tamper=True)
    result = gate.evaluate(BROKEN_PY)
    # Must not produce a tamper receipt or DENY based on input_invalid alone.
    assert result.bijective_tamper_kind == ""
    assert result.bijective_tamper_action == ""
    assert not any("bijective_tamper" in s for s in result.signals)


# --------------------------------------------------------------------------- #
#  4. base DENY + tamper ALLOW -> stays DENY (monotonic)
# --------------------------------------------------------------------------- #


def test_base_deny_plus_tamper_allow_stays_deny():
    """If the base gate denies for non-tamper reasons, a clean tamper signal
    must NOT downgrade the decision (monotonic property).

    Approach: pre-seed the immune set with the action's exact action_hash,
    using the same blake2s(digest_size=8) the gate computes. Then evaluate
    clean Python whose tamper recommendation is ALLOW. The base gate must
    return DENY via immune_memory_hit, and the tamper signal must not
    silently downgrade it.
    """
    gate = RuntimeGate(use_bijective_tamper=True)
    forced_immune_text = CLEAN_PY  # clean python — tamper alone says ALLOW
    import hashlib

    h = hashlib.blake2s(
        forced_immune_text.encode("utf-8", errors="replace"),
        digest_size=8,
    ).hexdigest()
    gate._immune.add(h)
    result = gate.evaluate(forced_immune_text)
    assert result.decision == Decision.DENY, f"immune-hit path must DENY regardless of tamper; got {result.decision}"
    # Tamper receipt should still be present in audit (overlay computed at top).
    assert result.bijective_tamper_kind == "none"
    assert result.bijective_tamper_action == "ALLOW"


# --------------------------------------------------------------------------- #
#  5. base ALLOW + synthetic kind="syntax" -> DENY (escalation via top short-circuit)
# --------------------------------------------------------------------------- #


def test_synthetic_syntax_tamper_escalates_to_deny(monkeypatch):
    """Inject a synthetic kind='syntax' TamperResult to verify the escalation
    path. We cannot reliably mangle Qwen's tokenizer in a unit test, so we
    mock the evaluator. This proves the wire-up will DENY when a true
    encoding-level tamper is detected in production."""
    from src.governance import bijective_tamper as bt

    def fake_evaluate_code(src, language="python", tokenizer=None, tokenizer_dir=None):
        return bt.TamperResult(
            score=1.0,
            kind="syntax",
            semantic_fingerprint="deadbeef" * 8,
            bytes_diverge=True,
            nfc_recovers_bytes=False,
            ast_diverge=True,
            decoded_parses=False,
            detail={"error": "synthetic test injection"},
        )

    gate = RuntimeGate(use_bijective_tamper=True)
    # Force lazy-load to populate, then patch the evaluator.
    gate._ensure_bijective_tamper()
    gate._bijective_tamper_evaluator = fake_evaluate_code
    result = gate.evaluate(CLEAN_PY)
    assert result.decision == Decision.DENY
    assert result.bijective_tamper_kind == "syntax"
    assert result.bijective_tamper_action == "DENY"
    assert any("bijective_tamper_veto_deny" in s for s in result.signals)
    assert result.action_hash in gate._immune


# --------------------------------------------------------------------------- #
#  6. prose with code keywords -> NOT DENY (heuristic false-positive guard)
# --------------------------------------------------------------------------- #


def test_prose_with_code_keywords_not_denied():
    """Prose containing 'function', 'import', 'return', 'class', 'from' must
    not get parsed as Python and falsely DENY'd. The two-signal heuristic
    plus the input_invalid no-op together make this safe."""
    gate = RuntimeGate(use_bijective_tamper=True)
    prose_samples = [
        "Please write a function that sorts a list of numbers.",
        "Import duty applies to this category from the spec.",
        "Return to the previous step and try again.",
        "The class action settlement covers all members.",
        "From the documentation above, summarize the API contract.",
    ]
    for text in prose_samples:
        result = gate.evaluate(text)
        assert result.decision != Decision.DENY, f"prose falsely DENY'd: {text!r} (signals={result.signals})"
        assert (
            result.bijective_tamper_kind == ""
        ), f"prose triggered tamper kind={result.bijective_tamper_kind!r}: {text!r}"


# --------------------------------------------------------------------------- #
#  Env-var enablement path
# --------------------------------------------------------------------------- #


def test_env_var_enables_overlay(monkeypatch):
    monkeypatch.setenv("SCBE_ENABLE_BIJECTIVE_TAMPER_GATE", "1")
    gate = RuntimeGate()
    assert gate._bijective_tamper_enabled is True
    result = gate.evaluate(CLEAN_PY)
    assert result.bijective_tamper_kind == "none"


def test_env_var_off_string_disables(monkeypatch):
    monkeypatch.setenv("SCBE_ENABLE_BIJECTIVE_TAMPER_GATE", "0")
    gate = RuntimeGate()
    assert gate._bijective_tamper_enabled is False


def test_explicit_kwarg_beats_env(monkeypatch):
    monkeypatch.setenv("SCBE_ENABLE_BIJECTIVE_TAMPER_GATE", "1")
    gate = RuntimeGate(use_bijective_tamper=False)
    assert gate._bijective_tamper_enabled is False


# --------------------------------------------------------------------------- #
#  Heuristic skip — non-code action_text never invokes the tokenizer
# --------------------------------------------------------------------------- #


def test_non_code_skips_tamper(monkeypatch):
    """Plain prose must not trigger the AST/tokenizer path."""
    gate = RuntimeGate(use_bijective_tamper=True)
    # A side channel: if _evaluate_bijective_tamper returns None,
    # the result fields stay at their defaults.
    result = gate.evaluate("hello world, please summarize the latest news")
    assert result.bijective_tamper_kind == ""
    assert result.bijective_tamper_action == ""
    assert not any("bijective_tamper" in s for s in result.signals)


# --------------------------------------------------------------------------- #
#  Receipt envelope is parseable
# --------------------------------------------------------------------------- #


def test_receipt_envelope_format():
    gate = RuntimeGate(use_bijective_tamper=True)
    result = gate.evaluate(CLEAN_PY)
    receipts = [s for s in result.signals if s.startswith("bijective_tamper(")]
    assert len(receipts) == 1
    receipt = receipts[0]
    # Required keys per the wire-up contract
    assert "kind=" in receipt
    assert "score=" in receipt
    assert "action=" in receipt
    # Clean code has a fingerprint
    assert "fp=" in receipt
