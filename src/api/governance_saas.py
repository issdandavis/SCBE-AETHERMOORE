"""
SCBE Governance SaaS API
=========================
Public-facing governance evaluation API with usage metering and API key auth.

Deploy alongside the existing bridge or standalone:
    uvicorn src.api.governance_saas:app --host 0.0.0.0 --port 8002

Endpoints:
    POST /v1/evaluate      — Evaluate text through governance pipeline
    POST /v1/batch         — Batch evaluate multiple inputs
    GET  /v1/usage         — Check API key usage stats
    GET  /v1/profiles      — List available governance profiles
    GET  /health           — Health check
    GET  /                 — Landing page
"""

import base64
import hashlib
import hmac
import math
import os
import secrets
import time
import json
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from fastapi import FastAPI, HTTPException, Depends, Header, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from pydantic import BaseModel, Field
except ImportError:
    raise RuntimeError("pip install fastapi uvicorn")


# ---------------------------------------------------------------------------
#  Core Governance Engine (inline — no external deps)
# ---------------------------------------------------------------------------

class Decision(str, Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


PHI = (1 + math.sqrt(5)) / 2
TONGUE_WEIGHTS = {
    "KO": 1.0, "AV": PHI, "RU": PHI**2,
    "CA": PHI**3, "UM": PHI**4, "DR": PHI**5,
}

# Threat keywords by category
THREAT_KEYWORDS = {
    "injection": ["ignore previous", "system prompt", "jailbreak", "DAN", "pretend you"],
    "exfiltration": ["send to", "upload to", "exfiltrate", "steal", "dump database"],
    "destruction": ["delete all", "drop table", "rm -rf", "format disk", "destroy"],
    "evasion": ["bypass", "disable safety", "turn off guard", "escape sandbox"],
    "social": ["act as admin", "elevated privileges", "root access", "sudo"],
}

PROFILES = {
    "chatbot": {
        "name": "Customer Service Chatbot",
        "thresholds": {"allow": 0.3, "quarantine": 0.6, "escalate": 0.85},
        "description": "Conservative profile for customer-facing chatbots",
    },
    "code_agent": {
        "name": "Code Generation Agent",
        "thresholds": {"allow": 0.4, "quarantine": 0.7, "escalate": 0.9},
        "description": "Balanced profile for code generation with system access",
    },
    "research_agent": {
        "name": "Research Agent",
        "thresholds": {"allow": 0.5, "quarantine": 0.75, "escalate": 0.9},
        "description": "Permissive profile for web research agents",
    },
    "fleet": {
        "name": "Multi-Agent Fleet",
        "thresholds": {"allow": 0.35, "quarantine": 0.65, "escalate": 0.85},
        "description": "Strict profile for coordinated multi-agent systems",
    },
    "enterprise": {
        "name": "Enterprise Default",
        "thresholds": {"allow": 0.3, "quarantine": 0.6, "escalate": 0.8},
        "description": "Standard enterprise governance profile",
    },
}


def poincare_distance(u: list, v: list) -> float:
    """Hyperbolic distance in the Poincare ball model."""
    diff_sq = sum((a - b) ** 2 for a, b in zip(u, v))
    norm_u_sq = sum(a ** 2 for a in u)
    norm_v_sq = sum(a ** 2 for a in v)
    denom = (1 - norm_u_sq) * (1 - norm_v_sq)
    if denom <= 0:
        return 10.0
    arg = 1 + 2 * diff_sq / denom
    return math.acosh(max(arg, 1.0))


def harmonic_wall(d: float, R: float = 1.5) -> float:
    """H(d,R) = R^(d^2) — exponential cost scaling."""
    return R ** (d ** 2)


def classify_tongue(text: str) -> str:
    """Simple Sacred Tongue classification."""
    lower = text.lower()
    if any(w in lower for w in ["data", "query", "fetch", "search"]):
        return "KO"
    elif any(w in lower for w in ["create", "build", "generate", "write"]):
        return "AV"
    elif any(w in lower for w in ["analyze", "compute", "calculate"]):
        return "RU"
    elif any(w in lower for w in ["connect", "send", "transfer"]):
        return "CA"
    elif any(w in lower for w in ["delete", "remove", "destroy", "modify"]):
        return "UM"
    elif any(w in lower for w in ["admin", "system", "root", "override"]):
        return "DR"
    return "KO"


def evaluate_text(text: str, profile: str = "enterprise") -> Dict[str, Any]:
    """Run text through the simplified 14-layer governance pipeline."""
    t0 = time.time()
    prof = PROFILES.get(profile, PROFILES["enterprise"])
    thresholds = prof["thresholds"]

    # L1-4: Semantic encoding
    tongue = classify_tongue(text)
    tongue_weight = TONGUE_WEIGHTS[tongue]
    text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

    # L5: Hyperbolic distance (text features → Poincare ball)
    word_count = len(text.split())
    char_count = len(text)
    special_ratio = sum(1 for c in text if not c.isalnum() and c != " ") / max(char_count, 1)
    upper_ratio = sum(1 for c in text if c.isupper()) / max(char_count, 1)

    origin = [0.0] * 6
    point = [
        min(special_ratio * 3, 0.95),
        min(upper_ratio * 2, 0.95),
        min(word_count / 200, 0.95),
        0.0, 0.0, 0.0,
    ]

    # Threat keyword detection
    threat_score = 0.0
    detected_threats = []
    lower_text = text.lower()
    for category, keywords in THREAT_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in lower_text:
                threat_score += 0.3
                detected_threats.append({"category": category, "keyword": kw})

    point[3] = min(threat_score, 0.95)
    point[4] = min(tongue_weight / 11.09, 0.95)  # Normalized tongue weight
    point[5] = min(len(detected_threats) * 0.15, 0.95)

    d_h = poincare_distance(origin, point)

    # L6-8: Phase analysis
    weighted_d = d_h * tongue_weight

    # L9-10: Coherence (simplified)
    coherence = max(0, 1.0 - (special_ratio + upper_ratio))

    # L11: Temporal binding (single evaluation = 1.0)
    temporal = 1.0

    # L12: Harmonic wall
    h_wall = harmonic_wall(d_h)

    # L13: Risk decision
    risk_score = min(d_h / 5.0 + threat_score * 0.4, 1.0)

    if risk_score <= thresholds["allow"]:
        decision = Decision.ALLOW
    elif risk_score <= thresholds["quarantine"]:
        decision = Decision.QUARANTINE
    elif risk_score <= thresholds["escalate"]:
        decision = Decision.ESCALATE
    else:
        decision = Decision.DENY

    confidence = max(0, 1.0 - abs(risk_score - thresholds["quarantine"]) / 0.5)
    duration_ms = (time.time() - t0) * 1000

    return {
        "decision": decision.value,
        "risk_score": round(risk_score, 4),
        "confidence": round(confidence, 4),
        "harmonic_wall": round(h_wall, 4),
        "hyperbolic_distance": round(d_h, 4),
        "tongue": tongue,
        "tongue_weight": round(tongue_weight, 4),
        "coherence": round(coherence, 4),
        "profile": profile,
        "threats_detected": detected_threats,
        "threat_count": len(detected_threats),
        "layer_summary": {
            "L1_4_encoding": text_hash,
            "L5_distance": round(d_h, 4),
            "L9_10_coherence": round(coherence, 4),
            "L11_temporal": temporal,
            "L12_harmonic_wall": round(h_wall, 4),
            "L13_decision": decision.value,
        },
        "duration_ms": round(duration_ms, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "patent": "USPTO #63/961,403 (Pending)",
    }


# ---------------------------------------------------------------------------
#  L12 Canonical Scoring (see docs/L12_HARMONIC_SCALING_CANON.md)
# ---------------------------------------------------------------------------

def h_score(d_star: float, phase_deviation: float = 0.0) -> float:
    """H_score = 1/(1 + d* + 2*pd) — bounded safety score in (0, 1]."""
    return 1.0 / (1.0 + d_star + 2.0 * phase_deviation)


def h_wall(d_star: float, alpha: float = 1.0, beta: float = 1.0) -> float:
    """H_wall = 1 + alpha*tanh(beta*d*) — bounded risk multiplier in [1, 1+alpha]."""
    return 1.0 + alpha * math.tanh(beta * d_star)


def h_exp(d_star: float, R: float = PHI) -> float:
    """H_exp = R^(d*^2) — unbounded exponential cost (clamped at exp(50))."""
    exponent = min(d_star ** 2, 50.0)
    return R ** exponent


def h_trit(d_star: float, phase_deviation: float = 0.0) -> Dict[str, int]:
    """Compute ternary trit vector from the three H formulas."""
    hs = h_score(d_star, phase_deviation)
    hw = h_wall(d_star)
    he = h_exp(d_star)

    def to_trit_score(v: float) -> int:
        if v > 0.67: return 1
        if v > 0.33: return 0
        return -1

    def to_trit_wall(v: float) -> int:
        if v < 1.5: return 1
        if v < 1.9: return 0
        return -1

    def to_trit_exp(v: float) -> int:
        if v < 2.0: return 1
        if v < 10.0: return 0
        return -1

    return {
        "t_score": to_trit_score(hs),
        "t_wall": to_trit_wall(hw),
        "t_exp": to_trit_exp(he),
    }


# ---------------------------------------------------------------------------
#  MMX — Multimodality Matrix Coherence (L9.5)
# ---------------------------------------------------------------------------

def compute_mmx(evaluation: Dict[str, Any]) -> Dict[str, Any]:
    """Compute multimodality matrix coherence from evaluation signals.

    Returns mm_coherence, mm_conflict, mm_drift, and decision_override.
    """
    risk = evaluation.get("risk_score", 0.0)
    coherence = evaluation.get("coherence", 1.0)
    d_h = evaluation.get("hyperbolic_distance", 0.0)
    h_wall_val = evaluation.get("harmonic_wall", 1.0)
    threats = evaluation.get("threat_count", 0)

    # Coherence: agreement between spectral and geometric signals
    # High coherence = both say the same thing (both safe or both risky)
    signal_agreement = 1.0 - abs(coherence - (1.0 - risk))
    mm_coherence = round(max(0.0, min(1.0, signal_agreement)), 4)

    # Conflict: disagreement between risk score and harmonic wall
    # If risk is low but H_wall is high (or vice versa), there's a conflict
    risk_from_wall = min(1.0, (h_wall_val - 1.0) / 5.0)  # Normalize wall to 0-1
    mm_conflict = round(abs(risk - risk_from_wall), 4)

    # Drift: rate of change signal (simplified — single evaluation = 0)
    # In streaming mode, this would track delta between consecutive evaluations
    mm_drift = 0.0

    # Decision override: conflict above threshold forces QUARANTINE
    decision_override = None
    if mm_conflict > 0.4 and evaluation.get("decision") == "ALLOW":
        decision_override = "QUARANTINE"
    if mm_conflict > 0.7:
        decision_override = "DENY"

    return {
        "mm_coherence": mm_coherence,
        "mm_conflict": mm_conflict,
        "mm_drift": mm_drift,
        "decision_override": decision_override,
    }


# ---------------------------------------------------------------------------
#  Signed Governance Receipts
# ---------------------------------------------------------------------------

# Receipt signing key — in production, use HSM or KMS
_RECEIPT_KEY = os.environ.get(
    "SCBE_RECEIPT_KEY",
    "scbe-dev-receipt-key-change-in-production"
).encode()

RECEIPT_SCHEMA_VERSION = "receipt.v1"
POLICY_HASH = hashlib.sha256(
    json.dumps(PROFILES, sort_keys=True).encode()
).hexdigest()[:16]


def sign_receipt(payload: Dict[str, Any]) -> str:
    """Create HMAC-SHA256 signed receipt (JWS-like, compact).

    Format: base64url(payload).base64url(signature)
    In production, replace with Ed25519 or ML-DSA-65.
    """
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")
    sig = hmac.new(_RECEIPT_KEY, payload_bytes, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return f"{payload_b64}.{sig_b64}"


def verify_receipt(receipt: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a signed receipt. Returns payload or None."""
    try:
        parts = receipt.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig_b64 = parts
        # Restore padding
        payload_b64 += "=" * (4 - len(payload_b64) % 4) if len(payload_b64) % 4 else ""
        sig_b64 += "=" * (4 - len(sig_b64) % 4) if len(sig_b64) % 4 else ""
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        sig = base64.urlsafe_b64decode(sig_b64)
        expected = hmac.new(_RECEIPT_KEY, payload_bytes, hashlib.sha256).digest()
        if hmac.compare_digest(sig, expected):
            return json.loads(payload_bytes)
        return None
    except Exception:
        return None


def build_governance_receipt(evaluation: Dict[str, Any], mmx: Dict[str, Any]) -> Dict[str, Any]:
    """Build a signed governance receipt from evaluation + MMX data."""
    receipt_id = secrets.token_hex(12)
    now = datetime.now(timezone.utc).isoformat()

    # Apply MMX override if present
    final_decision = mmx.get("decision_override") or evaluation["decision"]

    receipt_payload = {
        "receipt_id": receipt_id,
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "policy_hash": POLICY_HASH,
        "timestamp": now,
        "decision": final_decision,
        "risk_score": evaluation["risk_score"],
        "h_score": round(h_score(evaluation["hyperbolic_distance"]), 4),
        "h_wall": evaluation["harmonic_wall"],
        "h_exp": round(h_exp(evaluation["hyperbolic_distance"]), 4),
        "trits": h_trit(evaluation["hyperbolic_distance"]),
        "mmx": {
            "coherence": mmx["mm_coherence"],
            "conflict": mmx["mm_conflict"],
            "drift": mmx["mm_drift"],
        },
        "tongue": evaluation["tongue"],
        "profile": evaluation["profile"],
        "threats_detected": evaluation["threat_count"],
        "patent": "USPTO #63/961,403",
    }

    signed = sign_receipt(receipt_payload)

    return {
        "receipt_id": receipt_id,
        "receipt": signed,
        "payload": receipt_payload,
        "signature_algorithm": "HMAC-SHA256",
        "upgrade_path": "Ed25519 → ML-DSA-65 (post-quantum)",
    }


# ---------------------------------------------------------------------------
#  Usage Metering
# ---------------------------------------------------------------------------

# In-memory usage tracking (swap for Redis/DB in production)
_usage: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
    "evaluations": 0,
    "first_used": None,
    "last_used": None,
})

TIER_LIMITS = {
    "free": 100,
    "starter": 5000,
    "growth": 25000,
    "scale": 100000,
    "unlimited": float("inf"),
}

# API keys: key → tier (in production, use a database)
_api_keys: Dict[str, str] = {}


def _load_api_keys():
    """Load API keys from environment."""
    # Format: GOVERNANCE_API_KEYS=key1:tier1,key2:tier2
    keys_str = os.environ.get("GOVERNANCE_API_KEYS", "")
    if keys_str:
        for entry in keys_str.split(","):
            if ":" in entry:
                key, tier = entry.strip().split(":", 1)
                _api_keys[key] = tier
            else:
                _api_keys[entry.strip()] = "free"

    # Default dev keys
    for key in os.environ.get("SCBE_API_KEYS", "scbe-dev-key,test-key").split(","):
        if key.strip() and key.strip() not in _api_keys:
            _api_keys[key.strip()] = "free"


_load_api_keys()


def check_usage(api_key: str) -> Dict[str, Any]:
    """Check if API key has remaining quota."""
    tier = _api_keys.get(api_key, "free")
    limit = TIER_LIMITS.get(tier, 100)
    used = _usage[api_key]["evaluations"]
    return {
        "api_key_prefix": api_key[:8] + "...",
        "tier": tier,
        "limit": limit if limit != float("inf") else "unlimited",
        "used": used,
        "remaining": max(0, limit - used) if limit != float("inf") else "unlimited",
    }


def record_usage(api_key: str):
    """Record an API usage event."""
    now = datetime.now(timezone.utc).isoformat()
    _usage[api_key]["evaluations"] += 1
    if not _usage[api_key]["first_used"]:
        _usage[api_key]["first_used"] = now
    _usage[api_key]["last_used"] = now


# ---------------------------------------------------------------------------
#  FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SCBE Governance API",
    description=(
        "AI governance evaluation using the SCBE 14-layer pipeline. "
        "Patent pending (USPTO #63/961,403). "
        "Model-agnostic — works with any AI system."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# Auth dependency
async def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    if not x_api_key:
        raise HTTPException(401, "X-API-Key header required")
    if x_api_key not in _api_keys:
        raise HTTPException(403, "Invalid API key")
    usage = check_usage(x_api_key)
    remaining = usage["remaining"]
    if remaining != "unlimited" and remaining <= 0:
        raise HTTPException(429, f"Rate limit exceeded. Tier: {usage['tier']}, limit: {usage['limit']}/month")
    return x_api_key


# Request/Response models
class EvaluateRequest(BaseModel):
    text: str = Field(..., description="Text to evaluate through governance pipeline")
    profile: str = Field("enterprise", description="Governance profile to use")

class BatchRequest(BaseModel):
    items: List[EvaluateRequest] = Field(..., description="List of items to evaluate", max_length=100)


# Endpoints
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "SCBE Governance API",
        "version": "1.0.0",
        "profiles": list(PROFILES.keys()),
        "patent": "USPTO #63/961,403",
    }


@app.post("/v1/evaluate")
async def evaluate(req: EvaluateRequest, api_key: str = Depends(verify_api_key)):
    """Evaluate text through the SCBE 14-layer governance pipeline."""
    record_usage(api_key)
    result = evaluate_text(req.text, req.profile)
    return result


@app.post("/v1/batch")
async def batch_evaluate(req: BatchRequest, api_key: str = Depends(verify_api_key)):
    """Batch evaluate multiple items."""
    results = []
    for item in req.items:
        record_usage(api_key)
        results.append(evaluate_text(item.text, item.profile))
    return {
        "count": len(results),
        "results": results,
    }


@app.get("/v1/usage")
async def usage(api_key: str = Depends(verify_api_key)):
    """Check API key usage statistics."""
    return check_usage(api_key)


@app.get("/v1/profiles")
async def profiles():
    """List available governance profiles."""
    return {"profiles": PROFILES}


# ---------------------------------------------------------------------------
#  Revenue endpoints: /v1/score, /v1/govern, /v1/verify
# ---------------------------------------------------------------------------

class ScoreRequest(BaseModel):
    d_star: float = Field(..., ge=0, description="Realm distance (L8 output)")
    phase_deviation: float = Field(0.0, ge=0, description="Phase deviation (L10 output)")

class GovernRequest(BaseModel):
    text: str = Field(..., description="Text to evaluate through governance pipeline")
    profile: str = Field("enterprise", description="Governance profile to use")
    include_receipt: bool = Field(True, description="Include signed governance receipt")

class VerifyRequest(BaseModel):
    receipt: str = Field(..., description="Signed receipt string to verify")


@app.post("/v1/score", tags=["Revenue API"])
async def score_endpoint(req: ScoreRequest, api_key: str = Depends(verify_api_key)):
    """L12 Harmonic Safety Score — the core primitive.

    Returns all three H formulas and the ternary trit decomposition.
    See docs/L12_HARMONIC_SCALING_CANON.md for mathematical definitions.
    """
    record_usage(api_key)

    hs = h_score(req.d_star, req.phase_deviation)
    hw = h_wall(req.d_star)
    he = h_exp(req.d_star)
    trits = h_trit(req.d_star, req.phase_deviation)

    # Security bits equivalent
    security_bits = math.log2(1 + req.d_star + 2 * req.phase_deviation) if (req.d_star + req.phase_deviation) > 0 else 0

    return {
        "h_score": round(hs, 6),
        "h_wall": round(hw, 6),
        "h_exp": round(he, 6),
        "trits": trits,
        "trit_agreement": trits["t_score"] == trits["t_wall"] == trits["t_exp"],
        "security_bits_added": round(security_bits, 4),
        "inputs": {
            "d_star": req.d_star,
            "phase_deviation": req.phase_deviation,
        },
        "formulas": {
            "h_score": "1/(1 + d* + 2*pd)",
            "h_wall": "1 + alpha*tanh(beta*d*)",
            "h_exp": "R^(d*^2) where R=phi",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/v1/govern", tags=["Revenue API"])
async def govern_endpoint(req: GovernRequest, api_key: str = Depends(verify_api_key)):
    """Full governance evaluation with signed receipt.

    Runs the 14-layer pipeline, computes MMX coherence matrix,
    applies conflict overrides, and returns a cryptographically
    signed governance receipt.

    The receipt is the paid feature — verifiable proof that governance
    was applied. Upgrade path: HMAC-SHA256 → Ed25519 → ML-DSA-65.
    """
    record_usage(api_key)

    # Run evaluation
    evaluation = evaluate_text(req.text, req.profile)

    # Compute MMX coherence
    mmx = compute_mmx(evaluation)

    # Apply MMX override
    final_decision = mmx.get("decision_override") or evaluation["decision"]

    # Build response
    response = {
        "decision": final_decision,
        "risk_score": evaluation["risk_score"],
        "confidence": evaluation["confidence"],
        "h_score": round(h_score(evaluation["hyperbolic_distance"]), 6),
        "h_wall": evaluation["harmonic_wall"],
        "h_exp": round(h_exp(evaluation["hyperbolic_distance"]), 6),
        "trits": h_trit(evaluation["hyperbolic_distance"]),
        "mmx": mmx,
        "tongue": evaluation["tongue"],
        "tongue_weight": evaluation["tongue_weight"],
        "threats_detected": evaluation["threats_detected"],
        "layer_summary": evaluation["layer_summary"],
        "profile": req.profile,
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "policy_hash": POLICY_HASH,
        "duration_ms": evaluation["duration_ms"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Attach signed receipt
    if req.include_receipt:
        receipt = build_governance_receipt(evaluation, mmx)
        response["receipt"] = receipt

    return response


@app.post("/v1/verify", tags=["Revenue API"])
async def verify_endpoint(req: VerifyRequest):
    """Verify a signed governance receipt.

    Anyone can verify — no API key required.
    This is how customers prove governance was applied.
    """
    payload = verify_receipt(req.receipt)
    if payload is None:
        raise HTTPException(400, "Invalid or tampered receipt")
    return {
        "valid": True,
        "payload": payload,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/", response_class=HTMLResponse)
async def landing():
    """Landing page."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SCBE Governance API</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0a0a1a; color: #e0e0e0; }
  .hero { padding: 80px 40px; text-align: center; background: linear-gradient(135deg, #0a0a2e 0%, #1a1a3e 100%); }
  h1 { font-size: 2.5em; color: #00ff88; margin-bottom: 16px; }
  .tagline { font-size: 1.2em; color: #888; margin-bottom: 32px; }
  .badge { display: inline-block; background: #1a3a1a; color: #00ff88; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; margin: 4px; }
  .section { max-width: 800px; margin: 40px auto; padding: 0 20px; }
  .card { background: #12122a; border: 1px solid #2a2a4a; border-radius: 8px; padding: 24px; margin: 16px 0; }
  .card h3 { color: #00ff88; margin-bottom: 8px; }
  code { background: #1a1a3a; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
  pre { background: #1a1a3a; padding: 16px; border-radius: 8px; overflow-x: auto; margin: 12px 0; }
  a { color: #4488ff; }
  .pricing { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin: 24px 0; }
  .tier { background: #12122a; border: 1px solid #2a2a4a; border-radius: 8px; padding: 20px; text-align: center; }
  .tier h4 { color: #00ff88; margin-bottom: 8px; }
  .tier .price { font-size: 1.5em; font-weight: bold; color: #fff; }
  .tier .detail { font-size: 0.85em; color: #888; margin-top: 8px; }
  .cta { display: inline-block; background: #00ff88; color: #000; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; margin: 8px; }
  .cta:hover { background: #00cc6a; }
</style>
</head>
<body>
<div class="hero">
  <h1>SCBE Governance API</h1>
  <p class="tagline">Model-agnostic AI governance middleware.<br>Patent pending (USPTO #63/961,403).</p>
  <span class="badge">14-Layer Pipeline</span>
  <span class="badge">Hyperbolic Geometry</span>
  <span class="badge">Post-Quantum Crypto</span>
  <span class="badge">Sacred Tongues</span>
  <br><br>
  <a href="/docs" class="cta">API Docs</a>
  <a href="/redoc" class="cta" style="background:#4488ff;color:#fff">ReDoc</a>
</div>

<div class="section">
  <div class="card">
    <h3>Quick Start — Governance with Signed Receipts</h3>
    <pre>curl -X POST https://YOUR_HOST/v1/govern \\
  -H "X-API-Key: your-key" \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Delete all user records", "profile": "enterprise"}'</pre>
    <p>Returns: decision, risk score, <strong>signed governance receipt</strong>, MMX coherence matrix, ternary trit decomposition, full layer breakdown.</p>
    <pre style="font-size:0.8em"># The receipt is cryptographically signed — verify it:
curl -X POST https://YOUR_HOST/v1/verify \\
  -H "Content-Type: application/json" \\
  -d '{"receipt": "eyJkZWNpc2lvbi...abc123"}'</pre>
  </div>

  <div class="card">
    <h3>Three Endpoints</h3>
    <p><code>POST /v1/score</code> — Raw L12 harmonic safety score (3 formulas + ternary trits)</p>
    <p><code>POST /v1/govern</code> — Full 14-layer governance with signed receipt + MMX coherence</p>
    <p><code>POST /v1/verify</code> — Verify any signed receipt (no API key needed)</p>
    <p style="margin-top:12px"><strong>The receipt is the product.</strong> Verifiable proof that governance was applied. Upgrade path: HMAC-SHA256 → Ed25519 → ML-DSA-65 (post-quantum).</p>
  </div>

  <div class="card">
    <h3>How It Works</h3>
    <p>Every input passes through 14 governance layers:</p>
    <p><strong>L1-4:</strong> Semantic encoding with Sacred Tongues tokenizer</p>
    <p><strong>L5:</strong> Hyperbolic distance in Poincare ball — measures drift from safe behavior</p>
    <p><strong>L9-10:</strong> Spectral + spin coherence analysis</p>
    <p><strong>L12:</strong> Three harmonic formulas (H_score, H_wall, H_exp) with ternary trit decomposition</p>
    <p><strong>L13:</strong> Risk decision with MMX conflict override</p>
    <p><strong>Receipt:</strong> Cryptographically signed, schema-versioned, policy-hashed proof</p>
  </div>

  <h2 style="margin-top: 32px; color: #00ff88;">Pricing</h2>
  <div class="pricing">
    <div class="tier">
      <h4>Free</h4>
      <div class="price">$0</div>
      <div class="detail">100 evaluations/mo<br>All profiles<br>Community support</div>
    </div>
    <div class="tier" style="border-color: #00ff88;">
      <h4>Starter</h4>
      <div class="price">$49/mo</div>
      <div class="detail">5,000 evaluations/mo<br>Batch API<br>Email support</div>
    </div>
    <div class="tier">
      <h4>Growth</h4>
      <div class="price">$149/mo</div>
      <div class="detail">25,000 evaluations/mo<br>Custom profiles<br>Priority support</div>
    </div>
    <div class="tier">
      <h4>Scale</h4>
      <div class="price">$499/mo</div>
      <div class="detail">100,000 evaluations/mo<br>Dedicated instance<br>SLA guarantee</div>
    </div>
  </div>

  <div class="card">
    <h3>Enterprise</h3>
    <p>Need governance for your AI fleet? We offer dedicated deployments, custom profiles, blockchain-notarized audit trails, and direct integration support.</p>
    <p><a href="mailto:issdandavis7795@aethermoorgames.com">Contact us</a></p>
  </div>
</div>

<div style="text-align:center; padding: 40px; color: #555;">
  <p>&copy; 2026 Issac Davis / AethermoorGames</p>
  <p>Patent Pending: USPTO #63/961,403</p>
</div>
</body>
</html>"""
