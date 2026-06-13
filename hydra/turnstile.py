"""
Domain-aware turnstile resolution for SCBE antivirus and extension gates.

Turnstile maps a governance decision + suspicion signals to a containment
action and updates the running antibody load (immune memory across calls).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TurnstileOutcome:
    action: str
    antibody_load: float
    membrane_stress: float


_DECISION_TO_ACTION = {
    "DENY": "STOP",
    "ESCALATE": "ISOLATE",
    "QUARANTINE": "HOLD",
    "ALLOW": "ALLOW",
}


def resolve_turnstile(
    *,
    decision: str,
    domain: str,
    suspicion: float,
    geometry_norm: float,
    previous_antibody_load: float = 0.0,
    quorum_ok: bool = True,
) -> TurnstileOutcome:
    """
    Map governance decision + live signals to a containment action.

    antibody_load decays toward 0 when suspicion is low and accumulates when
    suspicion is high (immune memory across successive calls for the same process).

    membrane_stress reflects current load: a weighted blend of suspicion and
    geometry_norm that indicates how hard the membrane is working right now.
    """

    def _clamp(x):
        return min(1.0, max(0.0, float(x)))

    antibody_load = _clamp(0.65 * previous_antibody_load + 0.35 * suspicion)
    membrane_stress = _clamp(0.60 * suspicion + 0.40 * geometry_norm)

    # Escalate to honeypot when immune memory is saturated and active suspicion is high.
    if antibody_load >= 0.85 and suspicion >= 0.60:
        action = "HONEYPOT"
    else:
        action = _DECISION_TO_ACTION.get(decision.upper(), "HOLD")
        # Downgrade ALLOW to HOLD when quorum is not satisfied.
        if not quorum_ok and action == "ALLOW":
            action = "HOLD"

    return TurnstileOutcome(
        action=action,
        antibody_load=round(antibody_load, 4),
        membrane_stress=round(membrane_stress, 4),
    )
