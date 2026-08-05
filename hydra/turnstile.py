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
Domain = Literal["browser", "vehicle", "fleet", "antivirus", "default"]
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


# Domains whose turnstile-matrix.yaml entry lists HONEYPOT as an allowed action.
# vehicle does not (ALLOW/PIVOT/DEGRADE, "No stall"), nor do arxiv/patent.
_HONEYPOT_DOMAINS = frozenset({"browser", "fleet", "antivirus", "default"})


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

    normalized_domain: Domain = domain.lower() if isinstance(domain, str) else "default"
    if normalized_domain not in {"browser", "vehicle", "fleet", "antivirus", "default"}:
        normalized_domain = "default"

    antibody = compute_antibody_load(suspicion, previous_antibody_load)
    stress = compute_membrane_stress(geometry_norm)

    # Last line of defense: geometrically suspicious or immune-overloaded contexts
    # are rerouted to a honeypot execution lane.
    #
    # GATED ON DOMAIN, and it was not in the archived original. That short-circuit
    # returned before the domain dispatch, so it overrode every per-domain rule --
    # including vehicle's, whose matrix entry is ALLOW/PIVOT/DEGRADE with the note
    # "No stall; choose safe maneuver." Caught by test_turnstile_conformance:
    # vehicle/DENY at stress 0.995 returned HONEYPOT, which the matrix forbids.
    # Domains whose matrix entry lists HONEYPOT: browser, fleet, antivirus.
    if (
        normalized_decision != "ALLOW"
        and normalized_domain in _HONEYPOT_DOMAINS
        and (stress >= 0.9 or antibody >= 0.85)
    ):
        return TurnstileOutcome(
            action="HONEYPOT",
            require_human=False,
            isolate=True,
            deploy_honeypot=True,
            continue_execution=True,
            reason="honeypot triggered by membrane stress / antibody load",
            antibody_load=antibody,
            membrane_stress=stress,
        )

    if normalized_decision == "ALLOW":
        return TurnstileOutcome(
            action="ALLOW",
            require_human=False,
            isolate=False,
            deploy_honeypot=False,
            continue_execution=True,
            reason="decision allow",
            antibody_load=antibody,
            membrane_stress=stress,
        )

    if normalized_domain == "browser":
        # Browser can pause for user review safely.
        return TurnstileOutcome(
            action="HOLD",
            require_human=True,
            isolate=normalized_decision == "QUARANTINE",
            deploy_honeypot=False,
            continue_execution=False,
            reason="browser turnstile hold for review",
            antibody_load=antibody,
            membrane_stress=stress,
        )

    if normalized_domain == "vehicle":
        # Real-time systems cannot stall; always pivot to safe maneuver.
        return TurnstileOutcome(
            action="PIVOT",
            require_human=False,
            isolate=False,
            deploy_honeypot=False,
            continue_execution=True,
            reason="vehicle domain requires immediate pivot",
            antibody_load=antibody,
            membrane_stress=stress,
        )

    if normalized_domain == "fleet":
        if not quorum_ok:
            return TurnstileOutcome(
                action="ISOLATE",
                require_human=False,
                isolate=True,
                deploy_honeypot=False,
                continue_execution=True,
                reason="fleet quorum failed; isolate node and continue",
                antibody_load=antibody,
                membrane_stress=stress,
            )
        return TurnstileOutcome(
            action="DEGRADE" if normalized_decision == "ESCALATE" else "ISOLATE",
            require_human=False,
            isolate=normalized_decision != "ESCALATE",
            deploy_honeypot=False,
            continue_execution=True,
            reason="fleet containment without global stall",
            antibody_load=antibody,
            membrane_stress=stress,
        )

    if normalized_domain == "antivirus":
        return TurnstileOutcome(
            action="ISOLATE",
            require_human=False,
            isolate=True,
            deploy_honeypot=False,
            continue_execution=False,
            reason="antivirus domain isolates suspicious artifact",
            antibody_load=antibody,
            membrane_stress=stress,
        )

    # Default strict behavior.
    return TurnstileOutcome(
        action="STOP",
        require_human=False,
        isolate=False,
        deploy_honeypot=False,
        continue_execution=False,
        reason="default hard stop",
        antibody_load=antibody,
        membrane_stress=stress,
    )
