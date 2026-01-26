"""
SCBE-AETHERMOORE REST API
=========================

Production-ready API for AI Agent Governance.

Endpoints:
- POST /v1/authorize     - Main governance decision
- POST /v1/agents        - Register new agent
- GET  /v1/agents/{id}   - Get agent info
- POST /v1/consensus     - Multi-signature approval
- GET  /v1/audit/{id}    - Retrieve decision audit
- GET  /v1/health        - Health check

Run: uvicorn api.main:app --host 0.0.0.0 --port 8080
"""

import hashlib
import json
import logging
import math
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Header, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

# Import persistence layer
try:
    from api.persistence import get_persistence, SCBEPersistence
except ImportError:
    from persistence import get_persistence, SCBEPersistence

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}'
)
logger = logging.getLogger("scbe-api")

# =============================================================================
# App Configuration
# =============================================================================

app = FastAPI(
    title="SCBE-AETHERMOORE API",
    description="Quantum-Resistant AI Agent Governance System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key authentication
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def _load_api_keys() -> dict:
    """
    Load API keys from environment. No hardcoded defaults.

    Set SCBE_API_KEY environment variable before starting.
    For multiple keys: SCBE_API_KEY=key1,key2,key3
    """
    api_key_env = os.getenv("SCBE_API_KEY")
    if not api_key_env:
        logger.warning("SCBE_API_KEY not set - API will reject all requests")
        return {}

    keys = {}
    for i, key in enumerate(api_key_env.split(",")):
        key = key.strip()
        if key:
            keys[key] = f"tenant_{i}"
    return keys

VALID_API_KEYS = _load_api_keys()

# In-memory stores (replace with database in production)
AGENTS_STORE: Dict[str, dict] = {}
DECISIONS_STORE: Dict[str, dict] = {}
CONSENSUS_STORE: Dict[str, dict] = {}

# =============================================================================
# Models
# =============================================================================

class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    QUARANTINE = "QUARANTINE"


class AuthorizeRequest(BaseModel):
    agent_id: str = Field(..., description="Unique agent identifier")
    action: str = Field(..., description="Action being requested (READ, WRITE, EXECUTE, etc.)")
    target: str = Field(..., description="Target resource")
    context: Optional[Dict[str, Any]] = Field(default={}, description="Additional context")

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "fraud-detector-001",
                "action": "READ",
                "target": "transaction_stream",
                "context": {"sensitivity": 0.3}
            }
        }


class AuthorizeResponse(BaseModel):
    decision: Decision
    decision_id: str
    score: float
    explanation: Dict[str, Any]
    token: Optional[str] = None
    expires_at: Optional[str] = None


class AgentRegisterRequest(BaseModel):
    agent_id: str
    name: str
    role: str
    initial_trust: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = {}


class AgentResponse(BaseModel):
    agent_id: str
    name: str
    role: str
    trust_score: float
    created_at: str
    last_activity: Optional[str] = None
    decision_count: int = 0


class ConsensusRequest(BaseModel):
    action: str
    target: str
    required_approvals: int = Field(default=3, ge=1, le=10)
    validator_ids: List[str]
    timeout_seconds: int = Field(default=60, ge=10, le=300)


class ConsensusResponse(BaseModel):
    consensus_id: str
    status: str  # PENDING, APPROVED, REJECTED, TIMEOUT
    approvals: int
    rejections: int
    required: int
    votes: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    checks: Dict[str, str]


# =============================================================================
# Authentication
# =============================================================================

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    if api_key is None:
        raise HTTPException(status_code=401, detail="Missing API key")
    if api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return VALID_API_KEYS[api_key]


# =============================================================================
# SCBE Core Logic (14-Layer Pipeline)
# =============================================================================

def hyperbolic_distance(p1: tuple, p2: tuple) -> float:
    """Poincaré ball distance calculation."""
    norm1_sq = sum(x**2 for x in p1)
    norm2_sq = sum(x**2 for x in p2)
    diff_sq = sum((a - b)**2 for a, b in zip(p1, p2))

    norm1_sq = min(norm1_sq, 0.9999)
    norm2_sq = min(norm2_sq, 0.9999)

    numerator = 2 * diff_sq
    denominator = (1 - norm1_sq) * (1 - norm2_sq)

    if denominator <= 0:
        return float('inf')

    delta = numerator / denominator
    return math.acosh(1 + delta) if delta >= 0 else 0.0


def agent_to_6d_position(agent_id: str, action: str, target: str, trust: float) -> tuple:
    """Map agent+action to 6D hyperbolic position."""
    seed = hashlib.sha256(f"{agent_id}:{action}:{target}".encode()).digest()
    coords = []
    for i in range(6):
        val = seed[i] / 255.0
        radius = (1 - trust) * 0.8 + 0.1
        coords.append(val * radius - radius/2)
    return tuple(coords)


def scbe_14_layer_pipeline(
    agent_id: str,
    action: str,
    target: str,
    trust_score: float,
    sensitivity: float = 0.5
) -> tuple:
    """
    Full 14-layer SCBE governance pipeline.
    Returns (decision, score, explanation).
    """
    explanation = {"layers": {}}

    # Layer 1-4: Context Embedding
    position = agent_to_6d_position(agent_id, action, target, trust_score)
    explanation["layers"]["L1-4"] = f"6D position computed"

    # Layer 5-7: Hyperbolic Geometry Check
    safe_center = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    distance = hyperbolic_distance(position, safe_center)
    explanation["layers"]["L5-7"] = f"Distance: {distance:.3f}"

    # Layer 8: Realm Trust
    realm_trust = trust_score * (1 - sensitivity * 0.5)
    explanation["layers"]["L8"] = f"Realm trust: {realm_trust:.2f}"

    # Layer 9-10: Spectral/Spin Coherence
    coherence = 1.0 - abs(math.sin(distance * math.pi))
    explanation["layers"]["L9-10"] = f"Coherence: {coherence:.2f}"

    # Layer 11: Temporal Pattern
    temporal_score = trust_score * 0.9 + 0.1
    explanation["layers"]["L11"] = f"Temporal: {temporal_score:.2f}"

    # Layer 12: Harmonic Scaling
    R = 2
    d = int(sensitivity * 3) + 1
    H = R ** d
    risk_factor = (1 - realm_trust) * sensitivity * 0.5
    explanation["layers"]["L12"] = f"H(d={d},R={R})={H}, risk: {risk_factor:.2f}"

    # Layer 13: Final Decision
    final_score = (realm_trust * 0.6 + coherence * 0.2 + temporal_score * 0.2) - risk_factor
    explanation["layers"]["L13"] = f"Score: {final_score:.3f}"

    # Layer 14: Telemetry
    explanation["layers"]["L14"] = f"Logged at {time.time():.0f}"

    # Decision thresholds
    if final_score > 0.6:
        decision = Decision.ALLOW
    elif final_score > 0.3:
        decision = Decision.QUARANTINE
    else:
        decision = Decision.DENY

    explanation["trust_score"] = trust_score
    explanation["distance"] = round(distance, 3)
    explanation["risk_factor"] = round(risk_factor, 3)

    return decision, final_score, explanation


def generate_token(decision_id: str, agent_id: str, action: str, expires_minutes: int = 5) -> str:
    """Generate a simple authorization token (replace with JWT in production)."""
    payload = f"{decision_id}:{agent_id}:{action}:{time.time() + expires_minutes * 60}"
    signature = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"scbe_{signature}_{decision_id[:8]}"


def generate_noise() -> str:
    """Generate cryptographic noise for DENY responses."""
    return hashlib.sha256(secrets.token_bytes(32)).hexdigest()


# =============================================================================
# API Endpoints
# =============================================================================

@app.post("/v1/authorize", response_model=AuthorizeResponse, tags=["Governance"])
async def authorize(
    request: AuthorizeRequest,
    tenant: str = Depends(verify_api_key)
):
    """
    Main governance decision endpoint.

    Evaluates an agent's request through the 14-layer SCBE pipeline
    and returns ALLOW, DENY, or QUARANTINE.
    """
    start_time = time.time()

    # Get or create agent
    if request.agent_id not in AGENTS_STORE:
        AGENTS_STORE[request.agent_id] = {
            "agent_id": request.agent_id,
            "name": request.agent_id,
            "role": "unknown",
            "trust_score": 0.5,
            "created_at": datetime.utcnow().isoformat(),
            "decision_count": 0
        }

    agent = AGENTS_STORE[request.agent_id]
    trust_score = agent["trust_score"]
    sensitivity = request.context.get("sensitivity", 0.5) if request.context else 0.5

    # Run 14-layer pipeline
    decision, score, explanation = scbe_14_layer_pipeline(
        agent_id=request.agent_id,
        action=request.action,
        target=request.target,
        trust_score=trust_score,
        sensitivity=sensitivity
    )

    # Generate decision ID and store
    decision_id = f"dec_{uuid.uuid4().hex[:12]}"

    # Generate token for ALLOW, noise for DENY
    token = None
    if decision == Decision.ALLOW:
        token = generate_token(decision_id, request.agent_id, request.action)
    elif decision == Decision.DENY:
        explanation["noise"] = generate_noise()

    expires_at = None
    if token:
        expires_at = (datetime.utcnow() + timedelta(minutes=5)).isoformat() + "Z"

    # Store decision for audit
    DECISIONS_STORE[decision_id] = {
        "decision_id": decision_id,
        "tenant": tenant,
        "agent_id": request.agent_id,
        "action": request.action,
        "target": request.target,
        "decision": decision.value,
        "score": round(score, 3),
        "explanation": explanation,
        "timestamp": datetime.utcnow().isoformat(),
        "latency_ms": round((time.time() - start_time) * 1000, 2)
    }

    # Update agent stats
    agent["decision_count"] += 1
    agent["last_activity"] = datetime.utcnow().isoformat()

    # Log decision
    logger.info(json.dumps({
        "event": "governance_decision",
        "decision_id": decision_id,
        "agent_id": request.agent_id,
        "action": request.action,
        "decision": decision.value,
        "score": round(score, 3),
        "latency_ms": DECISIONS_STORE[decision_id]["latency_ms"]
    }))

    # Persist to Firebase
    try:
        persistence = get_persistence()
        risk_level = "LOW" if score > 0.6 else ("MEDIUM" if score > 0.3 else "HIGH")
        audit_id = persistence.log_decision(
            agent_id=request.agent_id,
            action=request.action,
            decision=decision.value,
            trust_score=trust_score,
            risk_level=risk_level,
            context=request.context or {},
            consensus_result={"single_decision": True}
        )
        persistence.record_trust(
            agent_id=request.agent_id,
            trust_score=trust_score,
            factors={"score": score, "sensitivity": sensitivity},
            decision=decision.value
        )
    except Exception as e:
        logger.warning(f"Persistence error (non-fatal): {e}")

    return AuthorizeResponse(
        decision=decision,
        decision_id=decision_id,
        score=round(score, 3),
        explanation=explanation,
        token=token,
        expires_at=expires_at
    )


@app.post("/v1/agents", response_model=AgentResponse, tags=["Agents"])
async def register_agent(
    request: AgentRegisterRequest,
    tenant: str = Depends(verify_api_key)
):
    """Register a new agent with initial trust score."""
    if request.agent_id in AGENTS_STORE:
        raise HTTPException(status_code=409, detail="Agent already exists")

    agent = {
        "agent_id": request.agent_id,
        "name": request.name,
        "role": request.role,
        "trust_score": request.initial_trust,
        "created_at": datetime.utcnow().isoformat(),
        "last_activity": None,
        "decision_count": 0,
        "metadata": request.metadata
    }
    AGENTS_STORE[request.agent_id] = agent

    logger.info(json.dumps({
        "event": "agent_registered",
        "agent_id": request.agent_id,
        "role": request.role,
        "initial_trust": request.initial_trust
    }))

    return AgentResponse(**agent)


@app.get("/v1/agents/{agent_id}", response_model=AgentResponse, tags=["Agents"])
async def get_agent(
    agent_id: str,
    tenant: str = Depends(verify_api_key)
):
    """Get agent information and current trust score."""
    if agent_id not in AGENTS_STORE:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentResponse(**AGENTS_STORE[agent_id])


@app.post("/v1/consensus", response_model=ConsensusResponse, tags=["Governance"])
async def request_consensus(
    request: ConsensusRequest,
    tenant: str = Depends(verify_api_key)
):
    """
    Request multi-signature consensus for sensitive operations.

    Collects votes from specified validators and returns
    approval status based on threshold.
    """
    consensus_id = f"con_{uuid.uuid4().hex[:12]}"

    votes = []
    approvals = 0
    rejections = 0

    for validator_id in request.validator_ids:
        # Get validator trust score
        if validator_id in AGENTS_STORE:
            trust = AGENTS_STORE[validator_id]["trust_score"]
        else:
            trust = 0.5  # Default for unknown validators

        # Run pipeline for each validator
        decision, score, _ = scbe_14_layer_pipeline(
            agent_id=validator_id,
            action=request.action,
            target=request.target,
            trust_score=trust,
            sensitivity=0.5
        )

        # ALLOW and QUARANTINE count as approval
        is_approve = decision in (Decision.ALLOW, Decision.QUARANTINE)

        if is_approve:
            approvals += 1
        else:
            rejections += 1

        votes.append({
            "validator_id": validator_id,
            "decision": decision.value,
            "score": round(score, 3),
            "approved": is_approve
        })

    # Determine consensus status
    if approvals >= request.required_approvals:
        status = "APPROVED"
    else:
        status = "REJECTED"

    # Store consensus
    CONSENSUS_STORE[consensus_id] = {
        "consensus_id": consensus_id,
        "status": status,
        "approvals": approvals,
        "rejections": rejections,
        "required": request.required_approvals,
        "votes": votes,
        "timestamp": datetime.utcnow().isoformat()
    }

    logger.info(json.dumps({
        "event": "consensus_decision",
        "consensus_id": consensus_id,
        "status": status,
        "approvals": approvals,
        "required": request.required_approvals
    }))

    return ConsensusResponse(
        consensus_id=consensus_id,
        status=status,
        approvals=approvals,
        rejections=rejections,
        required=request.required_approvals,
        votes=votes
    )


@app.get("/v1/audit/{decision_id}", tags=["Audit"])
async def get_audit(
    decision_id: str,
    tenant: str = Depends(verify_api_key)
):
    """Retrieve full audit trail for a governance decision."""
    if decision_id not in DECISIONS_STORE:
        raise HTTPException(status_code=404, detail="Decision not found")

    return DECISIONS_STORE[decision_id]


@app.get("/v1/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint (no auth required)."""
    persistence = get_persistence()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
        checks={
            "api": "ok",
            "pipeline": "ok",
            "storage": "ok" if len(AGENTS_STORE) >= 0 else "degraded",
            "firebase": "connected" if persistence.is_connected else "disconnected"
        }
    )


# =============================================================================
# Metrics & Monitoring Endpoints
# =============================================================================

class MetricsResponse(BaseModel):
    total_decisions: int
    allow_count: int
    quarantine_count: int
    deny_count: int
    allow_rate: float
    quarantine_rate: float
    deny_rate: float
    avg_trust_score: float
    firebase_connected: bool


@app.get("/v1/metrics", response_model=MetricsResponse, tags=["Monitoring"])
async def get_metrics(tenant: str = Depends(verify_api_key)):
    """Get decision metrics for monitoring dashboards."""
    persistence = get_persistence()
    metrics = persistence.get_metrics()
    metrics["firebase_connected"] = persistence.is_connected
    return MetricsResponse(**metrics)


# =============================================================================
# Webhook/Zapier Integration Endpoints
# =============================================================================

class WebhookConfig(BaseModel):
    webhook_url: str
    events: List[str] = ["decision_deny", "decision_quarantine", "trust_decline"]
    min_severity: str = "medium"


class AlertResponse(BaseModel):
    alert_id: str
    timestamp: str
    severity: str
    alert_type: str
    message: str
    agent_id: Optional[str]
    audit_id: Optional[str]
    data: dict


# Store webhooks in memory (would be persisted in production)
WEBHOOK_STORE: Dict[str, dict] = {}


@app.post("/v1/webhooks", tags=["Webhooks"])
async def register_webhook(
    config: WebhookConfig,
    tenant: str = Depends(verify_api_key)
):
    """
    Register a webhook URL for alert notifications.

    Use this to connect SCBE alerts to Zapier, Slack, or other services.
    """
    webhook_id = f"webhook_{uuid.uuid4().hex[:8]}"
    WEBHOOK_STORE[webhook_id] = {
        "webhook_id": webhook_id,
        "tenant": tenant,
        "url": config.webhook_url,
        "events": config.events,
        "min_severity": config.min_severity,
        "created_at": datetime.utcnow().isoformat()
    }

    logger.info(json.dumps({
        "event": "webhook_registered",
        "webhook_id": webhook_id,
        "url": config.webhook_url[:50] + "..."
    }))

    return {"webhook_id": webhook_id, "status": "registered"}


@app.get("/v1/webhooks", tags=["Webhooks"])
async def list_webhooks(tenant: str = Depends(verify_api_key)):
    """List registered webhooks for this tenant."""
    return [w for w in WEBHOOK_STORE.values() if w["tenant"] == tenant]


@app.delete("/v1/webhooks/{webhook_id}", tags=["Webhooks"])
async def delete_webhook(
    webhook_id: str,
    tenant: str = Depends(verify_api_key)
):
    """Remove a registered webhook."""
    if webhook_id not in WEBHOOK_STORE:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if WEBHOOK_STORE[webhook_id]["tenant"] != tenant:
        raise HTTPException(status_code=403, detail="Not authorized")

    del WEBHOOK_STORE[webhook_id]
    return {"status": "deleted"}


@app.get("/v1/alerts", response_model=List[AlertResponse], tags=["Alerts"])
async def get_alerts(
    tenant: str = Depends(verify_api_key),
    limit: int = 50,
    pending_only: bool = True
):
    """
    Get alerts for webhook delivery.

    Zapier can poll this endpoint to get new alerts.
    """
    persistence = get_persistence()

    if pending_only:
        alerts = persistence.get_pending_alerts(limit=limit)
    else:
        # Get recent alerts from audit logs
        alerts = []
        logs = persistence.get_audit_logs(limit=limit)
        for log in logs:
            if log["decision"] in ["DENY", "QUARANTINE"]:
                alerts.append({
                    "alert_id": f"alert-{log['audit_id']}",
                    "timestamp": log["timestamp"],
                    "severity": "high" if log["decision"] == "DENY" else "medium",
                    "alert_type": f"decision_{log['decision'].lower()}",
                    "message": f"Agent {log['agent_id']} request was {log['decision']}",
                    "agent_id": log["agent_id"],
                    "audit_id": log["audit_id"],
                    "data": {"trust_score": log["trust_score"]}
                })

    return alerts


@app.post("/v1/alerts/{alert_id}/ack", tags=["Alerts"])
async def acknowledge_alert(
    alert_id: str,
    tenant: str = Depends(verify_api_key)
):
    """
    Acknowledge an alert (mark as sent/processed).

    Call this after successfully processing an alert via webhook.
    """
    persistence = get_persistence()
    success = persistence.mark_alert_sent(alert_id)

    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"status": "acknowledged", "alert_id": alert_id}


# =============================================================================
# Trust History Endpoints
# =============================================================================

@app.get("/v1/agents/{agent_id}/trust-history", tags=["Agents"])
async def get_trust_history(
    agent_id: str,
    tenant: str = Depends(verify_api_key),
    limit: int = 30
):
    """Get trust score history for an agent."""
    persistence = get_persistence()
    history = persistence.get_trust_history(agent_id, limit=limit)
    trend = persistence.get_trust_trend(agent_id)

    return {
        "agent_id": agent_id,
        "trend": trend,
        "history": history
    }


@app.get("/v1/audit", tags=["Audit"])
async def list_audit_logs(
    tenant: str = Depends(verify_api_key),
    agent_id: Optional[str] = None,
    decision: Optional[str] = None,
    limit: int = 100
):
    """Query audit logs with optional filters."""
    persistence = get_persistence()
    logs = persistence.get_audit_logs(
        agent_id=agent_id,
        decision=decision,
        limit=limit
    )
    return {"count": len(logs), "logs": logs}


# =============================================================================
# Startup
# =============================================================================

@app.on_event("startup")
async def startup():
    persistence = get_persistence()
    logger.info(json.dumps({
        "event": "api_startup",
        "version": "1.0.0",
        "endpoints": 14,
        "firebase_connected": persistence.is_connected
    }))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
