from __future__ import annotations

from .models import AgentState, EggGenome


def geoseal_governance(state: AgentState, genome: EggGenome) -> str:
    """Simple ALLOW/QUARANTINE/DENY gate for prototype training loops."""
    risk_score = (1.0 - state.safety) * 0.5 + state.drift * 0.4 + (1.0 - state.stability) * 0.1
    risk_score *= (0.5 + genome.geoseal_sensitivity)

    if risk_score > 0.72:
        return "DENY"
    if risk_score > 0.45:
        return "QUARANTINE"
    return "ALLOW"
