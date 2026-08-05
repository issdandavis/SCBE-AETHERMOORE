"""The turnstile must obey the matrix that declares it.

The matrix at skills/scbe-kernel-external-toolcall-specialist/references/
turnstile-matrix.yaml declares, per domain, which actions are permitted. Until
now the only test read that YAML and asserted things about the YAML -- the spec
was checked against itself and never against the code. That is how a stub which
ignored `domain` entirely survived from acfc3734c until 2026-08-05.

These tests call resolve_turnstile and compare its output to the declaration.
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

from hydra.turnstile import allowed_actions_for, resolve_turnstile  # noqa: E402

MATRIX_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "scbe-kernel-external-toolcall-specialist"
    / "references"
    / "turnstile-matrix.yaml"
)

DECISIONS = ["ALLOW", "DENY", "ESCALATE", "QUARANTINE"]


def _matrix():
    return yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))["domains"]


@pytest.mark.parametrize("domain", sorted(_matrix()))
@pytest.mark.parametrize("decision", DECISIONS)
@pytest.mark.parametrize("suspicion,geometry_norm", [(0.0, 0.0), (0.5, 0.5), (0.95, 0.995)])
@pytest.mark.parametrize("quorum_ok", [False, True])
def test_action_is_permitted_by_the_matrix(domain, decision, suspicion, geometry_norm, quorum_ok):
    """Whatever the turnstile returns must be in that domain's allowed list."""
    allowed = set(_matrix()[domain]["allowed_actions"])
    out = resolve_turnstile(
        decision=decision,
        domain=domain,
        suspicion=suspicion,
        geometry_norm=geometry_norm,
        previous_antibody_load=suspicion,
        quorum_ok=quorum_ok,
    )
    assert out.action in allowed, (
        f"{domain}/{decision} -> {out.action!r}, which the matrix does not permit "
        f"({sorted(allowed)}). reason={out.reason!r}"
    )


@pytest.mark.parametrize("decision", DECISIONS)
def test_vehicle_never_stalls(decision):
    """The matrix note is 'No stall; choose safe maneuver.' HOLD is a stall.

    This is the assertion the stub failed: HOLD was its fallback action.
    """
    out = resolve_turnstile(decision=decision, domain="vehicle", suspicion=0.4, geometry_norm=0.4)
    assert out.action != "HOLD"
    assert out.continue_execution is True


def test_unknown_decision_falls_to_deny_not_hold():
    """An unrecognised decision must not be indistinguishable from QUARANTINE.

    The stub returned HOLD for both, so a garbage decision string looked exactly
    like a legitimate quarantine in the outcome.
    """
    out = resolve_turnstile(decision="NOT_A_DECISION", domain="default", suspicion=0.0)
    assert out.action != "ALLOW"
    assert out.continue_execution is False


def test_domain_is_actually_read():
    """The regression itself: `domain` was accepted and never used.

    Same decision and signals, two domains, must not give the same action.
    """
    a = resolve_turnstile(decision="QUARANTINE", domain="browser", suspicion=0.3, geometry_norm=0.3)
    b = resolve_turnstile(decision="QUARANTINE", domain="vehicle", suspicion=0.3, geometry_norm=0.3)
    assert a.action != b.action, "domain is being ignored again"


@pytest.mark.parametrize("domain", sorted(_matrix()))
def test_runtime_policy_matches_declared_matrix(domain):
    """The runtime guard and the declarative matrix must be the same set."""

    assert set(allowed_actions_for(domain)) == set(_matrix()[domain]["allowed_actions"])


@pytest.mark.parametrize("domain", sorted(_matrix()))
def test_every_declared_action_is_reachable(domain):
    """Allowed actions are an executable policy, not decorative vocabulary."""

    observed = set()
    for decision in DECISIONS:
        for suspicion, geometry_norm in ((0.0, 0.0), (0.95, 1.0)):
            for quorum_ok in (False, True):
                observed.add(
                    resolve_turnstile(
                        decision=decision,
                        domain=domain,
                        suspicion=suspicion,
                        previous_antibody_load=suspicion,
                        geometry_norm=geometry_norm,
                        quorum_ok=quorum_ok,
                    ).action
                )
    assert observed == set(_matrix()[domain]["allowed_actions"])


def test_unknown_domain_fails_closed_even_under_honeypot_pressure():
    out = resolve_turnstile(
        decision="DENY",
        domain="not-a-domain",
        suspicion=1.0,
        previous_antibody_load=1.0,
        geometry_norm=1.0,
    )
    assert out.action == "STOP"
    assert out.continue_execution is False
    assert out.deploy_honeypot is False


@pytest.mark.parametrize("domain", sorted(_matrix()))
@pytest.mark.parametrize("decision", DECISIONS)
def test_outcome_flags_agree_with_action(domain, decision):
    out = resolve_turnstile(decision=decision, domain=domain, suspicion=0.0, geometry_norm=0.0)
    assert out.deploy_honeypot is (out.action == "HONEYPOT")
    assert out.require_human is (out.action == "HOLD")
    if out.action in {"ALLOW", "PIVOT", "DEGRADE", "HONEYPOT"}:
        assert out.continue_execution is True
    if out.action in {"HOLD", "STOP"}:
        assert out.continue_execution is False
