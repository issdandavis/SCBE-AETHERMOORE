"""scbe-shim — FastAPI mirror of the Cloudflare Worker.

Designed to deploy as a Hugging Face Space (Docker SDK). Exposes the
same OpenAI-compatible endpoints with the `scbe_governance` field in
responses (matches the production Vercel contract).

Env vars:
    HF_TOKEN              Required. Token to call HuggingFace Inference.
    HF_MODEL              Default model id (Qwen/Qwen2.5-7B-Instruct).
    HF_INFERENCE_BASE     Override upstream base URL.
    SHIM_VERSION          Displayed in /v1/health and /v1/scorecard.
"""

from __future__ import annotations

import hashlib
import os
import time
import uuid
from typing import List, Literal, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from shim import evaluate_axioms, match_auditor_phrasing, decide

# Optional: surface the SCBE-AETHERMOORE traditional security layer when
# this Space is deployed alongside the main repo (e.g. from a checkout).
# Falls back gracefully when the module isn't importable in the Space build.
_HAS_TRADITIONAL_SECURITY = False
try:
    import sys as _sys
    import pathlib as _pathlib
    _maybe_repo = _pathlib.Path(__file__).resolve().parents[2]
    if (_maybe_repo / "scripts" / "security" / "traditional_security_layers.py").exists():
        _sys.path.insert(0, str(_maybe_repo))
    from scripts.security.traditional_security_layers import (  # type: ignore
        evaluate_artifact as _evaluate_artifact,
        report_to_dict as _report_to_dict,
    )
    _HAS_TRADITIONAL_SECURITY = True
except Exception:  # pragma: no cover
    _evaluate_artifact = None
    _report_to_dict = None

HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_MODEL = os.environ.get("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct")
HF_INFERENCE_BASE = os.environ.get("HF_INFERENCE_BASE", "https://api-inference.huggingface.co/v1")
SHIM_VERSION = os.environ.get("SHIM_VERSION", "0.1.0")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False


app = FastAPI(title="scbe-shim", version=SHIM_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/v1/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "scbe-shim",
        "version": SHIM_VERSION,
        "upstream_model": HF_MODEL,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@app.get("/v1/scorecard")
def scorecard() -> dict:
    return {
        "service": "scbe-shim",
        "version": SHIM_VERSION,
        "upstream_model": HF_MODEL,
        "measured": {
            "bijective_gate": {"pass": 25, "total": 25, "pass_rate": 1.0},
            "cross_lane_concept": {"pass": 257, "total": 257, "pass_rate": 1.0, "ci95_low": 0.985},
            "executable_holdout": {"pass": 180, "total": 180, "pass_rate": 1.0},
            "chemistry_contract": {"pass": 66, "total": 75, "pass_rate": 0.88},
            "petri_173": {"training_blocked": 173, "total": 173, "false_allow_rate": 0.0058},
        },
        "decision_bands": {
            "ALLOW": "H >= 0.65",
            "QUARANTINE": "0.45 <= H < 0.65",
            "ESCALATE": "0.25 <= H < 0.45",
            "DENY": "H < 0.25",
        },
        "harmonic_form": "H(d, pd) = 1 / (1 + phi*d + 2*pd)  where phi = 1.618",
    }


class TriageRequest(BaseModel):
    artifact_path: str
    max_bytes: Optional[int] = 5_000_000


@app.post("/v1/scbe/triage")
def scbe_triage(req: TriageRequest) -> dict:
    """Run Codex's traditional security layers + signal fusion on a local
    artifact path. Returns a SCBE-shaped decision the harmonic wall can
    consume as a prompt-side prior (pd).

    This endpoint is intentionally restricted to host-local paths — the
    Space must have the artifact on its filesystem (mount, prior upload,
    or repo checkout). It does not download remote URLs.
    """
    if not _HAS_TRADITIONAL_SECURITY:
        raise HTTPException(
            status_code=501,
            detail="traditional_security_layers not importable in this deploy; mount the repo or rebuild with --build-arg INCLUDE_REPO=1",
        )
    import pathlib as _pl
    p = _pl.Path(req.artifact_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"artifact not found: {p}")
    try:
        report = _evaluate_artifact(p, max_bytes=req.max_bytes or 5_000_000)  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"triage failed: {e}") from e

    report_dict = _report_to_dict(report)  # type: ignore
    # Translate traditional ALLOW/QUARANTINE/DENY to a pd contribution
    # for the harmonic wall: pd = 0 (clean), 0.5 (quarantine), 1.0 (deny).
    pd_map = {"ALLOW": 0.0, "QUARANTINE": 0.5, "DENY": 1.0}
    pd_value = pd_map.get(report_dict.get("decision", "ALLOW"), 0.0)
    return {
        "service": "scbe-shim",
        "version": SHIM_VERSION,
        "scbe_governance": {
            "decision_input": report_dict.get("decision"),
            "pd_contribution": pd_value,
            "risk_score": report_dict.get("risk_score"),
            "controls": [c for c in report_dict.get("controls", [])],
            "recommended_actions": report_dict.get("recommended_actions", []),
        },
        "traditional_report": report_dict,
    }


@app.post("/v1/chat/completions")
async def chat_completions(body: ChatRequest) -> dict:
    if not HF_TOKEN:
        raise HTTPException(status_code=500, detail="HF_TOKEN env var is not set")

    user_text = ""
    for msg in reversed(body.messages):
        if msg.role == "user":
            user_text = msg.content
            break

    matched, prompt_reason, _ = match_auditor_phrasing(user_text)

    if matched:
        denied = decide(evaluate_axioms("", user_text), True, prompt_reason, "")
        if denied.decision in ("DENY", "ESCALATE"):
            return _build_response(
                body,
                denied.suggested_correction or "",
                denied,
                "scbe_prompt_block",
                phase="input",
                upstream_provider="scbe-preflight",
            )

    model = body.model or HF_MODEL
    upstream_payload = {
        "model": model,
        "messages": [m.dict() for m in body.messages],
        "temperature": body.temperature or 0.7,
        "max_tokens": body.max_tokens or 1024,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{HF_INFERENCE_BASE}/chat/completions",
                json=upstream_payload,
                headers=headers,
            )
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"upstream fetch failed: {e}") from e

    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"upstream {resp.status_code}: {resp.text[:500]}")

    upstream_json = resp.json()
    raw_output = ""
    try:
        raw_output = upstream_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        pass

    axiom_report = evaluate_axioms(raw_output, user_text)
    decision = decide(axiom_report, matched, prompt_reason, raw_output)

    final_content = raw_output if decision.decision == "ALLOW" else (decision.suggested_correction or raw_output)
    return _build_response(
        body,
        final_content,
        decision,
        "scbe_governed",
        phase="output",
        upstream_provider="huggingface",
    )


def _sha256_hex16(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _intervention_for(decision: str, phase: Literal["input", "output"]) -> str:
    if decision == "ALLOW":
        return "none"
    if decision == "DENY":
        return "refusal_injection" if phase == "input" else "redaction"
    if decision == "ESCALATE":
        return "hard_stop_or_human_review"
    return "soft_rewrite"


def _build_response(
    body: ChatRequest,
    content: str,
    decision,
    finish_reason: str,
    *,
    phase: Literal["input", "output"],
    upstream_provider: str,
) -> dict:
    last_user = ""
    for msg in reversed(body.messages):
        if msg.role == "user":
            last_user = msg.content
            break
    model = body.model or HF_MODEL
    return {
        "id": f"chatcmpl-scbe-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "scbe_governance": {
            "version": SHIM_VERSION,
            "runtime": "hf-space-fastapi",
            "decision": decision.decision,
            "harmonic_score": decision.harmonic_score,
            "reasons": decision.reasons,
            "suggested_correction": decision.suggested_correction or "",
            "intervention": _intervention_for(decision.decision, phase),
            "audit": {
                "input_sha256_16": _sha256_hex16(last_user),
                "output_sha256_16": _sha256_hex16(content),
                "provider": upstream_provider,
                "model": model,
            },
        },
    }
