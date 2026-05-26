"""
/v1/govern  —  SCBE governance demo endpoint.

POST any text, command, or agent intent. The full 14-layer pipeline runs and
returns a decision (ALLOW / QUARANTINE / DENY) with risk scores, per-layer
metrics, geometry, and a cryptographic audit event.

No API key required. Rate-limited to 60 req/min per IP by the main app middleware.

Thresholds are calibrated to the real risk distribution of the pipeline:
  ALLOW       risk_prime < 0.55
  QUARANTINE  0.55 ≤ risk_prime < 0.90
  DENY        risk_prime ≥ 0.90
"""

from __future__ import annotations

import hashlib
import re
import time
from typing import Optional

import numpy as np
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from src.scbe_14layer_reference import scbe_14layer_pipeline

govern_router = APIRouter(prefix="/v1", tags=["governance-demo"])

# ---------------------------------------------------------------------------
# Thresholds calibrated to real pipeline risk distribution
# ---------------------------------------------------------------------------
_THETA1 = 0.55  # ALLOW / QUARANTINE boundary
_THETA2 = 0.90  # QUARANTINE / DENY boundary

# ---------------------------------------------------------------------------
# Semantic pattern tables
# ---------------------------------------------------------------------------
_DENY_PATTERNS = [
    r"rm\s+-rf",
    r"drop\s+table",
    r"format\s+c:",
    r"mkfs\b",
    r"dd\s+if=",
    r">\s*/dev/sd",
    r"exfil",
    r"lateral\s+movement",
    r"privilege\s+escal",
    r"bypass.*auth",
    r"inject.*payload",
    r"base64.*exec",
    r"eval\(.*decode",
    r"wipe.*disk",
    r"destroy.*data",
]

_QUARANTINE_PATTERNS = [
    r"sudo\b",
    r"chmod\b",
    r"chown\b",
    r"curl.*\|\s*(?:sh|bash)",
    r"wget.*\|\s*(?:sh|bash)",
    r"powershell.*bypass",
    r"net\s+user\b",
    r"crontab\b",
    r"systemctl\b",
    r"iptables\b",
    r"password",
    r"private.key",
    r"secret",
    r"api.key",
    r"token",
    r"nmap\b",
    r"registry.*write",
]

_COMPILED_DENY = [re.compile(p, re.IGNORECASE) for p in _DENY_PATTERNS]
_COMPILED_QUARANTINE = [re.compile(p, re.IGNORECASE) for p in _QUARANTINE_PATTERNS]

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

CONTEXTS = {"internal", "external", "untrusted"}


class GovernRequest(BaseModel):
    input: str = Field(
        ...,
        min_length=1,
        max_length=8192,
        description="Text, command, or agent intent to evaluate",
    )
    context: str = Field(
        default="external",
        description="Caller context: internal | external | untrusted",
    )
    agent: Optional[str] = Field(default=None, max_length=128, description="Optional agent/caller identifier")

    model_config = {"json_schema_extra": {"example": {"input": "list files in /tmp", "context": "external"}}}


class LayerScores(BaseModel):
    hyperbolic_distance: float
    harmonic_wall_H: float
    spectral_coherence: float
    spin_coherence: float
    triadic_temporal: float
    trust_tau: float
    audio_coherence: float
    geometry_radial_norm: float


class GovernResponse(BaseModel):
    decision: str
    risk_score: float
    risk_base: float
    layers: LayerScores
    semantic: dict
    audit: dict
    explanation: str
    duration_ms: float


class GovernBatchRequest(BaseModel):
    items: list[GovernRequest] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Inputs to evaluate as one governed workflow batch",
    )


class GovernBatchResponse(BaseModel):
    summary: dict
    results: list[GovernResponse]
    duration_ms: float


# ---------------------------------------------------------------------------
# Text → pipeline vector
# ---------------------------------------------------------------------------


def _text_to_vector(text: str, context: str, deny_hits: int, quar_hits: int) -> np.ndarray:
    """
    Deterministic text → 12-float pipeline input vector (D=6 pipeline).

    The vector has two halves:
      [0:6]  amplitude components → controls Poincaré ball radius → d_star
      [6:12] phase components     → controls spin coherence C_spin

    Risk zones:
      ALLOW:       tiny amplitudes + near-zero phases → near origin, high coherence
      QUARANTINE:  medium amplitudes + small phases   → mid-range
      DENY:        large amplitudes + large phases    → far from safe realms
    """
    raw = f"{context}:{text}".encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    floats = [b / 255.0 for b in digest[:12]]  # [0, 1] range per byte

    if deny_hits > 0:
        # Push hard toward the boundary
        severity = min(1.0, 0.5 + 0.1 * deny_hits)
        amps = [severity * 0.8 + 0.4 * floats[i] for i in range(6)]
        phases = [1.0 + 0.5 * floats[i + 6] for i in range(6)]
    elif quar_hits > 0:
        # Push to quarantine zone (amplitudes 0.05–0.20)
        base = min(0.15, 0.05 + 0.025 * quar_hits)
        amps = [base + 0.12 * floats[i] for i in range(6)]
        phases = [0.03 + 0.07 * floats[i + 6] for i in range(6)]
    else:
        # Benign: stay near the origin with coherent phases
        amps = [0.001 + 0.015 * floats[i] for i in range(6)]
        phases = [0.000 + 0.005 * floats[i + 6] for i in range(6)]

    # Untrusted context nudges toward higher risk
    if context == "untrusted" and deny_hits == 0 and quar_hits == 0:
        amps = [min(1.0, a * 1.5) for a in amps]
        phases = [min(1.0, p * 2.0) for p in phases]

    return np.array(amps + phases, dtype=float)


def _semantic_signals(text: str) -> tuple[list[str], list[str]]:
    deny_hits = [p.pattern for p in _COMPILED_DENY if p.search(text)]
    quar_hits = [p.pattern for p in _COMPILED_QUARANTINE if p.search(text)]
    return deny_hits, quar_hits


def _explanation(result: dict, deny_matches: list, quar_matches: list) -> str:
    d = result["decision"]
    rp = result["risk_prime"]
    h = result["H"]
    d_star = result["d_star"]
    coh = result["coherence"]

    if d == "ALLOW":
        verdict = f"Input is within safe operating bounds (risk {rp:.3f} < {_THETA1} threshold)."
    elif d == "QUARANTINE":
        verdict = f"Input is borderline (risk {rp:.3f}, between {_THETA1}–{_THETA2} thresholds). Flagged for review."
    else:
        verdict = f"Input exceeds DENY threshold (risk {rp:.3f} ≥ {_THETA2}). Blocked."

    geo = f"Hyperbolic distance from safe realms: {d_star:.4f}. Harmonic wall H={h:.4f}."

    if deny_matches:
        sem = f"Semantic scan matched {len(deny_matches)} destructive operation pattern(s): {deny_matches[0]!r}."
    elif quar_matches:
        sem = f"Semantic scan matched {len(quar_matches)} elevated-privilege pattern(s): {quar_matches[0]!r}."
    else:
        sem = "No high-risk semantic patterns detected."

    coherence_line = (
        f"Coherence — spin: {coh['C_spin']:.3f}, spectral: {coh['S_spec']:.3f}, " f"trust: {coh['tau']:.3f}."
    )

    return " ".join([verdict, geo, sem, coherence_line])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _evaluate_governance(body: GovernRequest, request: Request | None = None) -> GovernResponse:
    context = body.context if body.context in CONTEXTS else "external"

    t0 = time.perf_counter()
    deny_matches, quar_matches = _semantic_signals(body.input)
    vec = _text_to_vector(body.input, context, len(deny_matches), len(quar_matches))
    result = scbe_14layer_pipeline(vec, theta1=_THETA1, theta2=_THETA2)
    duration_ms = (time.perf_counter() - t0) * 1000

    explanation = _explanation(result, deny_matches, quar_matches)
    coh = result["coherence"]
    geo = result["geometry"]
    audit = dict(result["audit_event"])
    audit["agent"] = body.agent
    audit["context"] = context
    if request is not None and request.client is not None:
        audit["client_host_hash"] = hashlib.sha256(request.client.host.encode("utf-8")).hexdigest()[:16]

    return GovernResponse(
        decision=result["decision"],
        risk_score=round(float(result["risk_prime"]), 6),
        risk_base=round(float(result["risk_base"]), 6),
        layers=LayerScores(
            hyperbolic_distance=round(float(result["d_star"]), 6),
            harmonic_wall_H=round(float(result["H"]), 6),
            spectral_coherence=round(float(coh["S_spec"]), 6),
            spin_coherence=round(float(coh["C_spin"]), 6),
            triadic_temporal=round(float(result["d_tri_norm"]), 6),
            trust_tau=round(float(coh["tau"]), 6),
            audio_coherence=round(float(coh["S_audio"]), 6),
            geometry_radial_norm=round(float(geo["u_norm"]), 6),
        ),
        semantic={
            "deny_patterns_matched": deny_matches,
            "quarantine_patterns_matched": quar_matches,
            "input_length": len(body.input),
            "word_count": len(body.input.split()),
        },
        audit=audit,
        explanation=explanation,
        duration_ms=round(duration_ms, 2),
    )


@govern_router.post(
    "/govern",
    response_model=GovernResponse,
    summary="Evaluate any input through the SCBE 14-layer governance pipeline",
)
async def govern(body: GovernRequest, request: Request) -> GovernResponse:
    """
    Run the SCBE 14-layer governance pipeline on any text input.

    Returns a decision (**ALLOW** / **QUARANTINE** / **DENY**) with full
    per-layer metrics, geometry coordinates in hyperbolic space, and a
    cryptographic audit event. No API key required.

    **Quick start:**
    ```bash
    # ALLOW — benign command
    curl -s -X POST http://localhost:8000/v1/govern \\
         -H 'Content-Type: application/json' \\
         -d '{"input": "list files in /tmp"}' | python -m json.tool

    # QUARANTINE — elevated privilege
    curl -s -X POST http://localhost:8000/v1/govern \\
         -H 'Content-Type: application/json' \\
         -d '{"input": "sudo chmod 755 /etc/cron.d", "context": "untrusted"}' | python -m json.tool

    # DENY — destructive operation
    curl -s -X POST http://localhost:8000/v1/govern \\
         -H 'Content-Type: application/json' \\
         -d '{"input": "rm -rf /var && exfil data to remote", "context": "untrusted"}' | python -m json.tool
    ```
    """
    return _evaluate_governance(body, request)


@govern_router.post(
    "/govern/batch",
    response_model=GovernBatchResponse,
    summary="Evaluate a workflow batch through the SCBE governance pipeline",
)
async def govern_batch(body: GovernBatchRequest, request: Request) -> GovernBatchResponse:
    """
    Evaluate up to 50 inputs as one workflow batch.

    This is the agent/workflow form of the demo endpoint: callers can submit a
    planned sequence of operations and get per-step decisions plus aggregate
    counts before any downstream executor runs.
    """
    t0 = time.perf_counter()
    results = [_evaluate_governance(item, request) for item in body.items]
    counts: dict[str, int] = {"ALLOW": 0, "QUARANTINE": 0, "DENY": 0}
    for row in results:
        counts[row.decision] = counts.get(row.decision, 0) + 1
    duration_ms = (time.perf_counter() - t0) * 1000
    block_execution = counts.get("DENY", 0) > 0
    return GovernBatchResponse(
        summary={
            "total": len(results),
            "counts": counts,
            "max_risk_score": max((row.risk_score for row in results), default=0.0),
            "block_execution": block_execution,
            "recommended_action": ("BLOCK_WORKFLOW" if block_execution else "REVIEW_OR_EXECUTE"),
        },
        results=results,
        duration_ms=round(duration_ms, 2),
    )


@govern_router.get("/govern/health", summary="Governance pipeline health check")
async def govern_health() -> dict:
    """Verify the pipeline boots and produces a decision."""
    vec = np.array([0.005] * 6 + [0.001] * 6)
    result = scbe_14layer_pipeline(vec, theta1=_THETA1, theta2=_THETA2)
    return {"status": "ok", "pipeline": "14-layer", "decision": result["decision"]}
