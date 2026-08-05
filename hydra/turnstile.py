"""
HYDRA turnstile policy for domain-aware containment decisions.

RESTORED 2026-08-05. The domain-aware implementation was removed by
`acfc3734c refactor: split monolith into 9 focused repos (#1042)`, which left a
stub that accepted `domain` and never read it -- `domain` appeared exactly once
in the file, as the parameter. Evidence: `git log -S deploy_honeypot -- hydra/
turnstile.py` and `-S PIVOT` both show the symbols entering at 123d997bb and
leaving at acfc3734c, and nowhere else.

What the stub could not do, against
skills/scbe-kernel-external-toolcall-specialist/references/turnstile-matrix.yaml:

  vehicle  allowed ALLOW/PIVOT/DEGRADE, "No stall; choose safe maneuver."
           The stub could emit NEITHER PIVOT nor DEGRADE, and its fallback for an
           unrecognised decision was HOLD -- the one action the domain forbids.
  fleet    allowed ALLOW/ISOLATE/DEGRADE/HONEYPOT; DEGRADE was unreachable.
  unknown  decision fell to HOLD, which is byte-identical to a legitimate
           QUARANTINE, so a defaulted decision was invisible in the outcome.
           This version falls to DENY and carries a `reason`.

Nothing checked any of that: the only turnstile test read the YAML and asserted
things about the YAML. test_turnstile_conformance.py now runs this function
against that matrix.

Source of the restore: the archived mirror github.com/issdandavis/scbe-agents
(read-only snapshot 2026-04-13), the last surviving copy.

Design goals:
- Browser agents may HOLD for manual approval.
- Real-time vehicle agents must PIVOT instead of stalling.
- Fleet nodes should isolate compromised workers without freezing the swarm.
- Antivirus domain can deploy honeypot routing as a final containment layer.

Cell-theory inspired math:
  antibody_load(t+1) = clamp( decay * antibody_load(t) + (1-decay) * suspicion, 0, 1 )
  membrane_stress     = clamp((norm - threshold) / (1 - threshold), 0, 1)
where decay = exp(-ln(2) * dt / half_life)
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

Decision = Literal["ALLOW", "DENY", "ESCALATE", "QUARANTINE"]
Domain = Literal["browser", "vehicle", "fleet", "antivirus", "arxiv", "patent", "default"]
Action = Literal["ALLOW", "HOLD", "PIVOT", "DEGRADE", "ISOLATE", "HONEYPOT", "STOP"]


@dataclass(frozen=True)
class TurnstileOutcome:
    action: Action
    require_human: bool
    isolate: bool
    deploy_honeypot: bool
    continue_execution: bool
    reason: str
    antibody_load: float
    membrane_stress: float


# Runtime copy of the declarative turnstile contract.  The conformance suite
# compares every entry to turnstile-matrix.yaml, so changing either side alone
# fails.  Every outcome is constructed through _outcome(), which refuses an
# action outside its domain's declared set.
_DOMAIN_ALLOWED_ACTIONS: dict[Domain, frozenset[Action]] = {
    "browser": frozenset({"ALLOW", "HOLD", "HONEYPOT"}),
    "vehicle": frozenset({"ALLOW", "PIVOT", "DEGRADE"}),
    "fleet": frozenset({"ALLOW", "ISOLATE", "DEGRADE", "HONEYPOT"}),
    "antivirus": frozenset({"ALLOW", "ISOLATE", "HONEYPOT"}),
    "arxiv": frozenset({"ALLOW", "HOLD", "STOP"}),
    "patent": frozenset({"ALLOW", "HOLD", "STOP"}),
    "default": frozenset({"ALLOW", "STOP"}),
}

# The input decision is not itself a turnstile action.  This table is the
# complete low-stress dispatch for every non-ALLOW decision.  Keeping it data-
# shaped makes both coverage and reachability testable.
_DOMAIN_DECISION_ACTIONS: dict[Domain, dict[Decision, Action]] = {
    "browser": {"DENY": "HOLD", "ESCALATE": "HOLD", "QUARANTINE": "HOLD"},
    "vehicle": {"DENY": "PIVOT", "ESCALATE": "DEGRADE", "QUARANTINE": "PIVOT"},
    "fleet": {"DENY": "ISOLATE", "ESCALATE": "DEGRADE", "QUARANTINE": "ISOLATE"},
    "antivirus": {"DENY": "ISOLATE", "ESCALATE": "ISOLATE", "QUARANTINE": "ISOLATE"},
    "arxiv": {"DENY": "STOP", "ESCALATE": "HOLD", "QUARANTINE": "HOLD"},
    "patent": {"DENY": "STOP", "ESCALATE": "HOLD", "QUARANTINE": "HOLD"},
    "default": {"DENY": "STOP", "ESCALATE": "STOP", "QUARANTINE": "STOP"},
}

_ACTION_TRAITS: dict[Action, tuple[bool, bool, bool, bool]] = {
    # require_human, isolate, deploy_honeypot, continue_execution
    "ALLOW": (False, False, False, True),
    "HOLD": (True, False, False, False),
    "PIVOT": (False, False, False, True),
    "DEGRADE": (False, False, False, True),
    "ISOLATE": (False, True, False, False),
    "HONEYPOT": (False, True, True, True),
    "STOP": (False, False, False, False),
}


def _normalize_domain(domain: str) -> Domain:
    normalized = domain.lower() if isinstance(domain, str) else "default"
    return normalized if normalized in _DOMAIN_ALLOWED_ACTIONS else "default"  # type: ignore[return-value]


def allowed_actions_for(domain: str) -> frozenset[Action]:
    """Return the executable policy boundary for a declared domain."""

    return _DOMAIN_ALLOWED_ACTIONS[_normalize_domain(domain)]


def _outcome(
    *,
    domain: Domain,
    action: Action,
    reason: str,
    antibody_load: float,
    membrane_stress: float,
    isolate: bool | None = None,
    continue_execution: bool | None = None,
) -> TurnstileOutcome:
    allowed = _DOMAIN_ALLOWED_ACTIONS[domain]
    if action not in allowed:
        raise AssertionError(f"turnstile policy violation: {domain} cannot emit {action}; allowed={sorted(allowed)}")

    require_human, default_isolate, deploy_honeypot, default_continue = _ACTION_TRAITS[action]
    return TurnstileOutcome(
        action=action,
        require_human=require_human,
        isolate=default_isolate if isolate is None else isolate,
        deploy_honeypot=deploy_honeypot,
        continue_execution=default_continue if continue_execution is None else continue_execution,
        reason=reason,
        antibody_load=antibody_load,
        membrane_stress=membrane_stress,
    )


def _clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


def compute_antibody_load(
    suspicion: float,
    previous_load: float = 0.0,
    dt: float = 1.0,
    half_life: float = 12.0,
) -> float:
    if not math.isfinite(suspicion):
        return 1.0
    hl = max(1e-6, half_life)
    decay = math.exp(-math.log(2.0) * max(0.0, dt) / hl)
    return _clamp01(decay * _clamp01(previous_load) + (1.0 - decay) * _clamp01(suspicion))


def compute_membrane_stress(norm_value: float, threshold: float = 0.98) -> float:
    if not math.isfinite(norm_value):
        return 1.0
    t = min(0.999999, max(0.0, threshold))
    return _clamp01((norm_value - t) / max(1e-9, 1.0 - t))


def resolve_turnstile(
    decision: str,
    domain: str = "default",
    suspicion: float = 0.0,
    geometry_norm: float = 0.0,
    previous_antibody_load: float = 0.0,
    quorum_ok: bool = True,
) -> TurnstileOutcome:
    normalized_decision: Decision = decision.upper() if isinstance(decision, str) else "DENY"
    if normalized_decision not in {"ALLOW", "DENY", "ESCALATE", "QUARANTINE"}:
        normalized_decision = "DENY"

    normalized_domain = _normalize_domain(domain)

    antibody = compute_antibody_load(suspicion, previous_antibody_load)
    stress = compute_membrane_stress(geometry_norm)

    # Last line of defense: geometrically suspicious or immune-overloaded contexts
    # are rerouted to a honeypot execution lane.
    #
    # This used to be a hardcoded domain allowlist.  Membership now comes from
    # the same executable policy checked against the matrix, so a newly declared
    # domain cannot inherit HONEYPOT through the default branch.
    if (
        normalized_decision != "ALLOW"
        and "HONEYPOT" in _DOMAIN_ALLOWED_ACTIONS[normalized_domain]
        and (stress >= 0.9 or antibody >= 0.85)
    ):
        return _outcome(
            domain=normalized_domain,
            action="HONEYPOT",
            reason="honeypot triggered by membrane stress / antibody load",
            antibody_load=antibody,
            membrane_stress=stress,
        )

    if normalized_decision == "ALLOW":
        return _outcome(
            domain=normalized_domain,
            action="ALLOW",
            reason="decision allow",
            antibody_load=antibody,
            membrane_stress=stress,
        )

    action = _DOMAIN_DECISION_ACTIONS[normalized_domain][normalized_decision]
    reasons = {
        "browser": "browser turnstile hold for review",
        "vehicle": "vehicle domain continues through a safe maneuver",
        "fleet": "fleet containment without global stall",
        "antivirus": "antivirus domain isolates suspicious artifact",
        "arxiv": "arxiv submission requires human review or stop",
        "patent": "patent filing requires attorney review or stop",
        "default": "default hard stop",
    }
    # A failed fleet quorum always isolates the node and keeps the rest of the
    # swarm alive.  ISOLATE in antivirus remains a terminal containment action.
    if normalized_domain == "fleet" and not quorum_ok:
        action = "ISOLATE"
        reason = "fleet quorum failed; isolate node and continue"
    else:
        reason = reasons[normalized_domain]

    return _outcome(
        domain=normalized_domain,
        action=action,
        isolate=(normalized_decision == "QUARANTINE") if normalized_domain == "browser" else None,
        continue_execution=True if normalized_domain == "fleet" and action == "ISOLATE" else None,
        reason=reason,
        antibody_load=antibody,
        membrane_stress=stress,
    )
