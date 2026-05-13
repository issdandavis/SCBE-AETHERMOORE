"""Python mirror of services/scbe-shim/src/decision.ts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from .axioms import AxiomReport

PHI = 1.618

SAFE_FALLBACK = (
    "I can't help with that request as phrased. If you can restate "
    "what you're trying to accomplish, I'll try a safer path."
)


@dataclass
class DecisionResult:
    decision: str  # ALLOW | QUARANTINE | ESCALATE | DENY
    harmonic_score: float
    reasons: List[str]
    suggested_correction: Optional[str]


def decide(
    axiom_report: AxiomReport,
    prompt_matched: bool,
    prompt_reason: Optional[str],
    raw_output: str,
) -> DecisionResult:
    d = axiom_report.worst_score
    pd = 1.0 if prompt_matched else 0.0
    H = 1.0 / (1.0 + PHI * d + 2.0 * pd)

    reasons: List[str] = []
    if prompt_reason:
        reasons.append(f"prompt:{prompt_reason}")
    reasons.extend(axiom_report.reasons)

    if H >= 0.65:
        return DecisionResult("ALLOW", round(H, 4), reasons, None)
    if H >= 0.45:
        return DecisionResult("QUARANTINE", round(H, 4), reasons, _redact(raw_output, axiom_report))
    if H >= 0.25:
        return DecisionResult("ESCALATE", round(H, 4), reasons, SAFE_FALLBACK)
    return DecisionResult("DENY", round(H, 4), reasons, SAFE_FALLBACK)


def _redact(output: str, report: AxiomReport) -> str:
    has_locality = any(v.axiom == "locality" for v in report.violations)
    has_symmetry = any(v.axiom == "symmetry" for v in report.violations)
    if not has_locality and not has_symmetry:
        return output
    redactors = [
        re.compile(r"^.*\b(system prompt|hidden instructions?)\b.*$", re.I | re.M),
        re.compile(r"^.*\bignore (previous|prior|all|above) instructions?\b.*$", re.I | re.M),
        re.compile(r"^.*\bbase64\s*[:=]\s*[A-Za-z0-9+/]{40,}.*$", re.I | re.M),
    ]
    cleaned = output
    for rx in redactors:
        cleaned = rx.sub("[redacted-locality]", cleaned)
    return cleaned
