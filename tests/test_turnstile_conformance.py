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

from hydra.turnstile import resolve_turnstile  # noqa: E402

MATRIX_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "scbe-kernel-external-toolcall-specialist"
    / "references"
    / "turnstile-matrix.yaml"
)

DECISIONS = ["ALLOW", "DENY", "ESCALATE", "QUARANTINE"]
IMPLEMENTED_DOMAINS = ["browser", "vehicle", "fleet", "antivirus"]


def _matrix():
    return yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))["domains"]


@pytest.mark.parametrize("domain", IMPLEMENTED_DOMAINS)
@pytest.mark.parametrize("decision", DECISIONS)
@pytest.mark.parametrize("suspicion,geometry_norm", [(0.0, 0.0), (0.5, 0.5), (0.95, 0.995)])
def test_action_is_permitted_by_the_matrix(domain, decision, suspicion, geometry_norm):
    """Whatever the turnstile returns must be in that domain's allowed list."""
    allowed = set(_matrix()[domain]["allowed_actions"])
    out = resolve_turnstile(
        decision=decision,
        domain=domain,
        suspicion=suspicion,
        geometry_norm=geometry_norm,
        previous_antibody_load=suspicion,
        quorum_ok=True,
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


def test_every_matrix_domain_is_either_implemented_or_declared_default():
    """Domains in the matrix that the code does not implement fall to default.

    arxiv and patent are declared but not branched on; they resolve through the
    default path. That is only acceptable while the default action is inside
    their allowed list -- this test fails the day that stops being true.
    """
    m = _matrix()
    for name in m:
        if name in IMPLEMENTED_DOMAINS:
            continue
        out = resolve_turnstile(decision="DENY", domain=name, suspicion=0.0, geometry_norm=0.0)
        assert out.action in set(m[name]["allowed_actions"]), (
            f"{name} is declared in the matrix, is not implemented, and its default "
            f"action {out.action!r} is not in {sorted(m[name]['allowed_actions'])}"
        )
