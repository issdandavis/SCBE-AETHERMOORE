"""
Regression tests for the hyperbolic_scanner -> kernel_antivirus_gate wire.

Three cases:
  1. Benign handoff:  state vector near origin  -> low geometry_norm -> ALLOW preserved
  2. Adversarial payload: state vector near ball boundary -> elevated geometry_norm
  3. Explicit caller-supplied geometry_norm (no state_vector) -> respected, not overridden
"""

from __future__ import annotations

from agents.kernel_antivirus_gate import (
    KernelEvent,
    evaluate_kernel_event_with_state,
    geometry_norm_from_state,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _safe_event(**overrides) -> KernelEvent:
    """Minimally suspicious kernel event (signed, hashed, boring operation)."""
    defaults = dict(
        host="test-host",
        pid=1234,
        process_name="python.exe",
        operation="open",
        target="/home/user/data.csv",
        command_line="python script.py",
        parent_process="bash",
        signer_trusted=True,
        hash_sha256="a" * 64,
        geometry_norm=0.0,
    )
    defaults.update(overrides)
    return KernelEvent(**defaults)


# ---------------------------------------------------------------------------
# Case 1: benign state vector -> low geometry_norm -> decision stays ALLOW
# ---------------------------------------------------------------------------


def test_benign_handoff_keeps_allow():
    """
    A state vector near the Poincaré-ball origin yields a low geometry_norm.
    Combined with a safe kernel event the decision must be ALLOW and the cell
    state must be HEALTHY or PRIMED (not INFLAMED/NECROTIC).
    """
    # Small values; L2 norm << 0.95 threshold in hyperbolic_scanner
    benign_state = [0.05, 0.05, 0.05, 0.05]

    result = evaluate_kernel_event_with_state(_safe_event(), state_vector=benign_state)

    assert result.decision == "ALLOW", f"Expected ALLOW for benign state, got {result.decision}"
    assert result.cell_state in ("HEALTHY", "PRIMED"), f"Expected healthy/primed cell, got {result.cell_state}"
    assert result.geometry_norm < 0.50, f"Expected low geometry_norm for benign state, got {result.geometry_norm}"


# ---------------------------------------------------------------------------
# Case 2: adversarial payload -> elevated geometry_norm -> suspicion increases
# ---------------------------------------------------------------------------


def test_adversarial_payload_elevates_suspicion():
    """
    A state vector near the Poincaré-ball boundary (L2 norm >= 0.95) is
    clipped and yields a high geometry_norm that measurably raises suspicion.

    Note: geometry_norm carries 15% weight in the suspicion blend, so a
    maxed norm contributes at most 0.15 to suspicion. A clean event (trusted
    signer, good hash, benign operation) has a very low base suspicion, so
    the decision can still be ALLOW — that is intentional. What matters is:
    (1) the scanner correctly clips the out-of-ball state to a norm near 1.0,
    (2) suspicion is meaningfully higher than the same event with a zero norm.
    """
    # L2 norm of [0.6, 0.6, 0.6] = 0.6 * sqrt(3) ≈ 1.039 -> clipped to ~0.999
    adversarial_state = [0.6, 0.6, 0.6]
    computed_norm = geometry_norm_from_state(adversarial_state)

    # Scanner should have clipped this near the boundary
    assert computed_norm >= 0.90, f"Expected high norm from near-boundary state, got {computed_norm}"

    result_high = evaluate_kernel_event_with_state(_safe_event(), state_vector=adversarial_state)
    result_zero = evaluate_kernel_event_with_state(_safe_event(geometry_norm=0.0), state_vector=None)

    # geometry_norm on result must reflect what the scanner computed
    assert (
        result_high.geometry_norm >= computed_norm * 0.90
    ), f"Result geometry_norm {result_high.geometry_norm} should track scanner norm {computed_norm}"

    # Suspicion must be higher with the elevated geometry_norm
    suspicion_lift = result_high.suspicion - result_zero.suspicion
    assert suspicion_lift > 0.05, f"Expected >=0.05 suspicion lift from near-boundary norm, got {suspicion_lift:.4f}"
    assert result_high.suspicion > 0.10, f"Expected elevated absolute suspicion, got {result_high.suspicion}"


# ---------------------------------------------------------------------------
# Case 3: explicit caller-supplied geometry_norm, no state_vector -> respected
# ---------------------------------------------------------------------------


def test_explicit_geometry_norm_respected_without_state_vector():
    """
    When no state_vector is passed, the geometry_norm already on the KernelEvent
    is used unchanged.  This confirms backward compatibility for callers that
    compute geometry_norm themselves (e.g. from a different scanner or sensor).
    """
    manual_norm = 0.42
    event = _safe_event(geometry_norm=manual_norm)

    # Call the wrapper with NO state_vector
    result = evaluate_kernel_event_with_state(event, state_vector=None)

    # The gate's internal geometry_norm computation blends the observed_norm
    # with suspicion (line 241 in gate: geometry_norm = clamp(max(observed, 0.20 + 0.75*s))).
    # What we check: the reported geometry_norm is >= the manually set value
    # (the gate may raise it, but must never drop it below the caller's signal).
    assert result.geometry_norm >= manual_norm * 0.90, (
        f"Caller-supplied norm {manual_norm} should be reflected in result, " f"got {result.geometry_norm}"
    )


# ---------------------------------------------------------------------------
# Case 4: scanner overrides event norm when state_vector is provided
# ---------------------------------------------------------------------------


def test_scanner_overrides_event_norm_when_state_vector_provided():
    """
    When state_vector is provided, the scanner-computed norm replaces the
    event's geometry_norm field (scanner takes precedence per policy docstring).
    """
    # Event has a hand-set high norm
    event = _safe_event(geometry_norm=0.85)

    # But the state vector is clearly benign
    benign_state = [0.02, 0.02, 0.02]
    scanner_norm = geometry_norm_from_state(benign_state)
    assert scanner_norm < 0.10, f"Expected benign scanner norm, got {scanner_norm}"

    result = evaluate_kernel_event_with_state(event, state_vector=benign_state)

    # The gate's reported geometry_norm must reflect the scanner result, not 0.85.
    # (Gate may raise it via internal blend but the starting observed_norm is scanner_norm.)
    assert (
        result.geometry_norm < 0.80
    ), f"Scanner-computed low norm should replace the event's 0.85; got {result.geometry_norm}"
    assert result.decision == "ALLOW", f"Benign state should yield ALLOW, got {result.decision}"
