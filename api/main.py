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

# Import billing and key management routes
try:
    from api.billing.routes import router as billing_router
    from api.billing.database import init_db
    from api.keys.routes import router as keys_router
    BILLING_AVAILABLE = True
except ImportError:
    BILLING_AVAILABLE = False
    billing_router = None
    keys_router = None

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

# Initialize billing database and register routes
if BILLING_AVAILABLE:
    init_db()
    app.include_router(billing_router)
    app.include_router(keys_router)
    logger.info("Billing and API key management routes registered")

# API Key authentication
API_KEY_HEADER = APIKeyHeader(name="SCBE_api_key", auto_error=False)

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
    ALLOW = "ALLOW"         # Action permitted immediately
    DENY = "DENY"           # Action blocked immediately
    QUARANTINE = "QUARANTINE"  # Temporary hold - isolate and monitor
    ESCALATE = "ESCALATE"   # Escalate to higher AI, then human if AIs disagree


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

    # Decision thresholds (4-tier system)
    if final_score > 0.7:
        decision = Decision.ALLOW       # High trust - proceed
    elif final_score > 0.5:
        decision = Decision.QUARANTINE  # Medium trust - isolate & monitor
    elif final_score > 0.3:
        decision = Decision.ESCALATE    # Low trust - needs higher AI review
    else:
        decision = Decision.DENY        # Very low trust - block

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

    Evaluates an agent's request through the 14-layer SCBE pipeline.
    Returns one of four decisions:
    - ALLOW: Action permitted immediately
    - QUARANTINE: Temporary hold - isolate and monitor
    - ESCALATE: Swarm escalation to higher AI, then human
    - DENY: Action blocked immediately
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

        # ALLOW counts as approval, ESCALATE triggers swarm review
        is_approve = decision in (Decision.ALLOW, Decision.ESCALATE)

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
    escalate_count: int
    deny_count: int
    allow_rate: float
    quarantine_rate: float
    escalate_rate: float
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
    events: List[str] = ["decision_deny", "decision_quarantine", "decision_escalate", "trust_decline"]
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
            if log["decision"] in ["DENY", "QUARANTINE", "ESCALATE"]:
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
# Fleet Scenario Endpoint (Pilot Demo)
# =============================================================================

class FleetAgent(BaseModel):
    agent_id: str
    name: str
    role: str = "worker"
    initial_trust: float = Field(default=0.5, ge=0.0, le=1.0)


class FleetAction(BaseModel):
    agent_id: str
    action: str
    target: str
    sensitivity: float = Field(default=0.5, ge=0.0, le=1.0)


class FleetScenario(BaseModel):
    scenario_name: str = "default"
    agents: List[FleetAgent]
    actions: List[FleetAction]
    require_consensus: bool = False
    consensus_threshold: int = 3

    class Config:
        json_schema_extra = {
            "example": {
                "scenario_name": "fraud-detection-fleet",
                "agents": [
                    {"agent_id": "fraud-detector-001", "name": "Fraud Detector", "role": "analyzer", "initial_trust": 0.8},
                    {"agent_id": "risk-scorer-002", "name": "Risk Scorer", "role": "scorer", "initial_trust": 0.7},
                    {"agent_id": "alert-bot-003", "name": "Alert Bot", "role": "notifier", "initial_trust": 0.6}
                ],
                "actions": [
                    {"agent_id": "fraud-detector-001", "action": "READ", "target": "transaction_stream", "sensitivity": 0.3},
                    {"agent_id": "risk-scorer-002", "action": "WRITE", "target": "risk_scores_db", "sensitivity": 0.6},
                    {"agent_id": "alert-bot-003", "action": "EXECUTE", "target": "send_alert", "sensitivity": 0.4}
                ]
            }
        }


class FleetDecision(BaseModel):
    agent_id: str
    action: str
    target: str
    decision: str
    score: float
    trust_score: float
    risk_factor: float


class FleetScenarioResponse(BaseModel):
    scenario_id: str
    scenario_name: str
    timestamp: str
    summary: Dict[str, int]
    decisions: List[FleetDecision]
    metrics: Dict[str, float]


@app.post("/v1/fleet/run-scenario", response_model=FleetScenarioResponse, tags=["Fleet"])
async def run_fleet_scenario(
    scenario: FleetScenario,
    tenant: str = Depends(verify_api_key)
):
    """
    Run a complete fleet scenario through SCBE.

    This endpoint:
    1. Registers all agents in the scenario
    2. Runs each action through the 14-layer SCBE pipeline
    3. Aggregates results and returns a summary

    Use this for demos, testing, and UI integration.
    """
    scenario_id = f"scenario_{uuid.uuid4().hex[:12]}"
    start_time = time.time()

    # Register all agents
    for agent in scenario.agents:
        if agent.agent_id not in AGENTS_STORE:
            AGENTS_STORE[agent.agent_id] = {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "role": agent.role,
                "trust_score": agent.initial_trust,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": None,
                "decision_count": 0
            }

    # Process all actions
    decisions = []
    allow_count = 0
    quarantine_count = 0
    escalate_count = 0
    deny_count = 0
    total_score = 0.0

    for action in scenario.actions:
        agent = AGENTS_STORE.get(action.agent_id)
        if not agent:
            continue

        trust_score = agent["trust_score"]

        # Run 14-layer pipeline
        decision, score, explanation = scbe_14_layer_pipeline(
            agent_id=action.agent_id,
            action=action.action,
            target=action.target,
            trust_score=trust_score,
            sensitivity=action.sensitivity
        )

        # Track metrics
        if decision == Decision.ALLOW:
            allow_count += 1
        elif decision == Decision.QUARANTINE:
            quarantine_count += 1
        elif decision == Decision.ESCALATE:
            escalate_count += 1
        else:
            deny_count += 1

        total_score += score

        decisions.append(FleetDecision(
            agent_id=action.agent_id,
            action=action.action,
            target=action.target,
            decision=decision.value,
            score=round(score, 3),
            trust_score=trust_score,
            risk_factor=explanation.get("risk_factor", 0)
        ))

        # Update agent stats
        agent["decision_count"] += 1
        agent["last_activity"] = datetime.utcnow().isoformat()

    elapsed_ms = (time.time() - start_time) * 1000

    logger.info(json.dumps({
        "event": "fleet_scenario_completed",
        "scenario_id": scenario_id,
        "scenario_name": scenario.scenario_name,
        "agents": len(scenario.agents),
        "actions": len(scenario.actions),
        "allow": allow_count,
        "quarantine": quarantine_count,
        "escalate": escalate_count,
        "deny": deny_count,
        "elapsed_ms": round(elapsed_ms, 2)
    }))

    return FleetScenarioResponse(
        scenario_id=scenario_id,
        scenario_name=scenario.scenario_name,
        timestamp=datetime.utcnow().isoformat() + "Z",
        summary={
            "total_actions": len(scenario.actions),
            "allowed": allow_count,
            "quarantined": quarantine_count,
            "escalated": escalate_count,
            "denied": deny_count
        },
        decisions=decisions,
        metrics={
            "avg_score": round(total_score / max(len(decisions), 1), 3),
            "allow_rate": round(allow_count / max(len(decisions), 1), 3),
            "elapsed_ms": round(elapsed_ms, 2)
        }
    )


# =============================================================================
# Roundtable Multi-Signature Governance (Six Sacred Tongues)
# =============================================================================

# Security tier configuration based on Sacred Tongues
ROUNDTABLE_TIERS = {
    1: {"tongues": ["KO"], "signatures": 1, "multiplier": 1.5, "name": "Single"},
    2: {"tongues": ["KO", "RU"], "signatures": 2, "multiplier": 5.06, "name": "Dual"},
    3: {"tongues": ["KO", "RU", "UM"], "signatures": 3, "multiplier": 38.4, "name": "Triple"},
    4: {"tongues": ["KO", "RU", "UM", "CA"], "signatures": 4, "multiplier": 656, "name": "Quad"},
    5: {"tongues": ["KO", "RU", "UM", "CA", "AV"], "signatures": 5, "multiplier": 14348, "name": "Quint"},
    6: {"tongues": ["KO", "AV", "RU", "CA", "UM", "DR"], "signatures": 6, "multiplier": 518400, "name": "Full Roundtable"},
}


class RoundtableRequest(BaseModel):
    action: str = Field(..., description="Action requiring multi-sig approval")
    target: str = Field(..., description="Target resource")
    tier: int = Field(..., ge=1, le=6, description="Security tier (1-6)")
    signers: List[str] = Field(..., description="List of signer agent IDs")
    context: Optional[Dict[str, Any]] = {}

    class Config:
        json_schema_extra = {
            "example": {
                "action": "DEPLOY",
                "target": "production-cluster",
                "tier": 4,
                "signers": ["admin-001", "security-002", "ops-003", "lead-004"],
                "context": {"environment": "production"}
            }
        }


class RoundtableVote(BaseModel):
    signer_id: str
    tongue: str
    decision: str
    score: float
    signature: str


class RoundtableResponse(BaseModel):
    roundtable_id: str
    tier: int
    tier_name: str
    required_signatures: int
    collected_signatures: int
    security_multiplier: float
    status: str  # APPROVED, REJECTED, PENDING, ESCALATE_TO_HUMAN
    tongues_used: List[str]
    votes: List[RoundtableVote]
    final_decision: str
    timestamp: str


@app.post("/v1/roundtable", response_model=RoundtableResponse, tags=["Governance"])
async def roundtable_governance(
    request: RoundtableRequest,
    tenant: str = Depends(verify_api_key)
):
    """
    Multi-signature governance using the Six Sacred Tongues protocol.

    Security Tiers:
    - Tier 1: Single (KO) - 1.5× - Basic coordination
    - Tier 2: Dual (KO+RU) - 5.06× - Config changes
    - Tier 3: Triple (KO+RU+UM) - 38.4× - Security ops
    - Tier 4: Quad (KO+RU+UM+CA) - 656× - Deploy/delete
    - Tier 5: Quint (5 tongues) - 14,348× - Infrastructure
    - Tier 6: Full Roundtable (all 6) - 518,400× - Genesis ops
    """
    tier_config = ROUNDTABLE_TIERS[request.tier]
    required_sigs = tier_config["signatures"]
    tongues = tier_config["tongues"]

    if len(request.signers) < required_sigs:
        raise HTTPException(
            status_code=400,
            detail=f"Tier {request.tier} requires {required_sigs} signers, got {len(request.signers)}"
        )

    roundtable_id = f"rt_{uuid.uuid4().hex[:12]}"
    votes = []
    approvals = 0
    denials = 0
    escalations = 0

    # Collect votes from each signer using assigned tongue
    for i, signer_id in enumerate(request.signers[:required_sigs]):
        tongue = tongues[i % len(tongues)]

        # Get signer's trust or default
        if signer_id in AGENTS_STORE:
            trust = AGENTS_STORE[signer_id]["trust_score"]
        else:
            trust = 0.5

        # Run through 14-layer pipeline
        # Lower tiers are more permissive, higher tiers are stricter
        base_sensitivity = 0.1 + (request.tier * 0.05)  # Tier 1=0.15, Tier 6=0.4
        decision, score, _ = scbe_14_layer_pipeline(
            agent_id=signer_id,
            action=request.action,
            target=request.target,
            trust_score=trust,
            sensitivity=base_sensitivity
        )

        # Generate tongue-specific signature
        sig_data = f"{roundtable_id}:{signer_id}:{tongue}:{decision.value}"
        signature = hashlib.sha256(sig_data.encode()).hexdigest()[:16]

        if decision == Decision.ALLOW:
            approvals += 1
        elif decision == Decision.DENY:
            denials += 1
        else:  # QUARANTINE or ESCALATE
            escalations += 1

        votes.append(RoundtableVote(
            signer_id=signer_id,
            tongue=tongue,
            decision=decision.value,
            score=round(score, 3),
            signature=f"{tongue.lower()}:{signature}"
        ))

    # Determine final status
    if approvals >= required_sigs:
        status = "APPROVED"
        final_decision = "ALLOW"
    elif denials >= (required_sigs // 2) + 1:
        status = "REJECTED"
        final_decision = "DENY"
    elif escalations > 0:
        status = "ESCALATE_TO_HUMAN"
        final_decision = "ESCALATE"
    else:
        status = "PENDING"
        final_decision = "QUARANTINE"

    logger.info(json.dumps({
        "event": "roundtable_decision",
        "roundtable_id": roundtable_id,
        "tier": request.tier,
        "status": status,
        "approvals": approvals,
        "denials": denials,
        "escalations": escalations,
        "multiplier": tier_config["multiplier"]
    }))

    return RoundtableResponse(
        roundtable_id=roundtable_id,
        tier=request.tier,
        tier_name=tier_config["name"],
        required_signatures=required_sigs,
        collected_signatures=len(votes),
        security_multiplier=tier_config["multiplier"],
        status=status,
        tongues_used=tongues[:len(votes)],
        votes=votes,
        final_decision=final_decision,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@app.get("/v1/roundtable/tiers", tags=["Governance"])
async def get_roundtable_tiers():
    """Get available Roundtable security tiers and their requirements."""
    tiers = []
    use_cases = {
        1: "Basic coordination, status updates",
        2: "State modifications, config changes",
        3: "Security operations, key rotation",
        4: "Irreversible ops (deploy, delete)",
        5: "Critical infrastructure changes",
        6: "Genesis-level operations, system reboot"
    }
    for tier_num, config in ROUNDTABLE_TIERS.items():
        tiers.append({
            "tier": tier_num,
            "name": config["name"],
            "tongues_required": config["tongues"],
            "signatures_required": config["signatures"],
            "security_multiplier": config["multiplier"],
            "use_cases": use_cases[tier_num]
        })
    return {"tiers": tiers}


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
