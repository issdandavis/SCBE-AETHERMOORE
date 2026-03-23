from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, Sequence

from api.validation import run_nextgen_action_validation

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

try:
    from python.scbe.phdm_embedding import FluxState, PHDMEmbedder
except Exception:  # pragma: no cover
    FluxState = None
    PHDMEmbedder = None

try:
    from src.minimal.davis_formula import davis_security_score
except Exception:  # pragma: no cover
    def davis_security_score(
        time_budget: float,
        intent_intensity: float,
        context_dimensions: int,
        drift: float,
    ) -> float:
        context_factor = math.factorial(max(context_dimensions, 0))
        return time_budget / (intent_intensity * context_factor * (1.0 + drift))


HIGH_RISK_PATTERNS = (
    "disable auth",
    "skip test",
    "skip ci",
    "bypass",
    "hardcode secret",
    "production hotfix",
    "force push",
    "rm -rf",
    "sudo ",
    "token",
    "private key",
)

GOVERNANCE_PATTERNS = (
    "test",
    "docs",
    "readme",
    "rollback",
    "migration plan",
    "audit",
    "checklist",
    "incident",
    "validation",
)

PRIVILEGED_PATH_MARKERS = (
    ".github/workflows/",
    "deploy/",
    "infra/",
    "terraform/",
    "k8s/",
    "docker-compose",
    ".env",
    "secrets",
    "credentials",
    "billing/",
    "auth",
)


@dataclass(frozen=True)
class PullRequestIntentAssessment:
    decision: str
    safety_score: float
    base_score: float
    trust_score: float
    sensitivity: float
    drift: float
    trust_ring: str
    energy_cost: float
    davis_score: float
    reasons: list[str]
    risk_hits: list[str]
    governance_hits: list[str]
    privileged_files: list[str]
    explanation: Dict[str, Any]


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _normalize_text(title: str, body: str) -> str:
    compact_body = re.sub(r"\s+", " ", (body or "").strip())
    compact_title = re.sub(r"\s+", " ", (title or "").strip())
    return f"{compact_title}\n\n{compact_body}".strip()


def _collect_hits(text: str, patterns: Sequence[str]) -> list[str]:
    lowered = text.lower()
    return [pattern for pattern in patterns if pattern in lowered]


def _collect_privileged_files(filenames: Sequence[str]) -> list[str]:
    privileged: list[str] = []
    for name in filenames:
        lowered = name.lower()
        if any(marker in lowered for marker in PRIVILEGED_PATH_MARKERS):
            privileged.append(name)
    return privileged


def _default_embedding_metrics(text: str) -> tuple[float, str, float]:
    normalized = _normalize_text(text, "")
    base = sum(ord(char) for char in normalized[:256]) % 1000 / 1000.0
    drift = 0.2 + base * 0.5
    return drift, "INNER" if drift < 0.7 else "OUTER", drift**4


def assess_pull_request_intent(
    *,
    action: str,
    actor: str,
    repository: str,
    title: str,
    body: str,
    additions: int,
    deletions: int,
    changed_files_count: int,
    filenames: Sequence[str] | None = None,
    head_sha: str | None = None,
) -> PullRequestIntentAssessment:
    filenames = list(filenames or [])
    text = _normalize_text(title, body)
    risk_hits = _collect_hits(text, HIGH_RISK_PATTERNS)
    governance_hits = _collect_hits(text, GOVERNANCE_PATTERNS)
    privileged_files = _collect_privileged_files(filenames)

    body_bonus = min(len((body or "").strip()) / 1200.0, 0.18)
    title_bonus = 0.05 if len((title or "").strip()) >= 12 else 0.0
    governance_bonus = min(0.12, 0.03 * len(governance_hits))
    risk_penalty = min(0.28, 0.08 * len(risk_hits))
    volume_penalty = _clamp((additions + deletions) / 4000.0, 0.0, 0.12)
    file_count_penalty = _clamp(changed_files_count / 150.0, 0.0, 0.10)
    privileged_penalty = min(0.18, 0.05 * len(privileged_files))
    description_penalty = 0.16 if not (body or "").strip() else 0.0

    trust_score = _clamp(
        0.55
        + body_bonus
        + title_bonus
        + governance_bonus
        - risk_penalty
        - volume_penalty
        - file_count_penalty
        - privileged_penalty
        - description_penalty,
        0.05,
        0.98,
    )

    sensitivity = _clamp(
        0.18
        + _clamp((additions + deletions) / 2500.0, 0.0, 0.24)
        + _clamp(changed_files_count / 80.0, 0.0, 0.18)
        + min(0.25, 0.07 * len(privileged_files))
        + min(0.18, 0.05 * len(risk_hits))
        + (0.08 if action == "synchronize" else 0.04 if action == "edited" else 0.0),
        0.05,
        0.98,
    )

    context = {
        "mode": "github_pull_request",
        "repository": repository,
        "actor": actor,
        "additions": additions,
        "deletions": deletions,
        "changed_files": changed_files_count,
        "head_sha": head_sha or "",
        "risk_hits": risk_hits,
        "privileged_file_count": len(privileged_files),
    }

    base_decision, base_score, explanation = run_nextgen_action_validation(
        agent_id=actor or "unknown-actor",
        action=f"github_pr_{action}",
        target=text[:1024] or repository,
        trust_score=trust_score,
        sensitivity=sensitivity,
        context=context,
    )

    if PHDMEmbedder is not None and np is not None:
        embedder = PHDMEmbedder()
        flux_state = FluxState.QUASI if FluxState is not None and (risk_hits or privileged_files) else FluxState.POLLY
        embedding = embedder.encode(
            text or repository,
            context={
                "user_id": actor or repository,
                "session_id": head_sha or f"{repository}:{action}",
                "flux_state": flux_state,
            },
        )
        drift = float(np.linalg.norm(embedding[:6]))
        trust_ring = str(embedder.get_trust_ring(embedding))
        energy_cost = float(embedder.calculate_energy_cost(embedding))
    else:  # pragma: no cover
        drift, trust_ring, energy_cost = _default_embedding_metrics(text or repository)

    davis_score = float(
        davis_security_score(
            time_budget=max(1.0, min(len(text or repository) / 96.0, 48.0)),
            intent_intensity=1.0 + 0.45 * len(risk_hits) + 0.35 * len(privileged_files) + sensitivity,
            context_dimensions=min(max(changed_files_count, 1), 4),
            drift=max(drift, 0.0),
        )
    )

    normalized_davis = math.tanh(davis_score * 2.0)
    drift_penalty = _clamp(drift / 1.25, 0.0, 1.0)
    safety_score = _clamp(
        base_score * 0.75
        + normalized_davis * 0.15
        + (1.0 - drift_penalty) * 0.10
        - 0.05 * len(risk_hits)
        - 0.04 * len(privileged_files),
        0.0,
        1.0,
    )

    reasons: list[str] = []
    if risk_hits:
        reasons.append(f"high-risk wording detected: {', '.join(risk_hits)}")
    if privileged_files:
        reasons.append(f"privileged paths touched: {', '.join(privileged_files[:5])}")
    if not (body or "").strip():
        reasons.append("pull request body is empty")
    if changed_files_count > 40 or (additions + deletions) > 2000:
        reasons.append("change volume is high")
    if base_decision == "QUARANTINE":
        reasons.append("SCBE validation requested quarantine review")
    if base_decision == "DENY":
        reasons.append("SCBE validation denied the change")
    if not reasons:
        reasons.append("intent remained inside the review threshold")

    if trust_ring == "WALL" or safety_score < 0.35:
        final_decision = "DENY"
    elif risk_hits or privileged_files:
        final_decision = "DENY" if safety_score < 0.45 else "QUARANTINE"
    elif base_decision == "DENY" and safety_score < 0.45:
        final_decision = "DENY"
    elif safety_score >= 0.40 and trust_score >= 0.60 and sensitivity <= 0.35:
        final_decision = "ALLOW"
    elif base_decision == "QUARANTINE" or safety_score < 0.58:
        final_decision = "QUARANTINE"
    else:
        final_decision = "ALLOW"

    explanation = {
        **explanation,
        "repository": repository,
        "action": action,
        "risk_hits": risk_hits,
        "governance_hits": governance_hits,
        "privileged_files": privileged_files,
        "trust_ring": trust_ring,
        "energy_cost": round(energy_cost, 6),
        "davis_score": round(davis_score, 6),
    }

    return PullRequestIntentAssessment(
        decision=final_decision,
        safety_score=round(safety_score, 4),
        base_score=round(float(base_score), 4),
        trust_score=round(trust_score, 4),
        sensitivity=round(sensitivity, 4),
        drift=round(drift, 4),
        trust_ring=trust_ring,
        energy_cost=round(energy_cost, 6),
        davis_score=round(davis_score, 6),
        reasons=reasons,
        risk_hits=risk_hits,
        governance_hits=governance_hits,
        privileged_files=privileged_files,
        explanation=explanation,
    )
