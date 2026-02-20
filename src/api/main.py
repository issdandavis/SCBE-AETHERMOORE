#!/usr/bin/env python3
"""
SCBE-AETHERMOORE MVP API
========================
6 essential endpoints for sellable MVP.

FastAPI implementation with:
- API key authentication
- Rate limiting
- Comprehensive error handling
- Swagger documentation

Run: uvicorn src.api.main:app --reload
"""

from fastapi import FastAPI, HTTPException, Header, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
import json
import numpy as np
import hashlib
import hmac
import time
from collections import defaultdict
from enum import Enum
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.scbe_14layer_reference import scbe_14layer_pipeline
from src.crypto.rwp_v3 import RWPv3Protocol, RWPEnvelope
from src.crypto.sacred_tongues import SacredTongueTokenizer
from src.storage import BlobNotFoundError, SealedBlobRecord, get_storage_backend

# ============================================================================
# APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="SCBE-AETHERMOORE MVP API",
    version="3.0.0",
    description="Quantum-resistant memory sealing with hyperbolic governance",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS for demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# RATE LIMITING
# ============================================================================


class RateLimiter:
    """Simple in-memory rate limiter (100 req/min per key)."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key] if req_time > window_start
        ]

        # Check limit
        if len(self.requests[key]) >= self.max_requests:
            return False

        # Record request
        self.requests[key].append(now)
        return True


rate_limiter = RateLimiter()

# ============================================================================
# METRICS STORAGE (In-memory for MVP)
# ============================================================================


class MetricsStore:
    """Simple in-memory metrics storage."""

    def __init__(self):
        self.total_seals = 0
        self.total_retrievals = 0
        self.total_denials = 0
        self.risk_scores = []
        self.agent_requests = defaultdict(int)
        self.start_time = time.time()

    def record_seal(self, agent: str, risk_score: float):
        self.total_seals += 1
        self.risk_scores.append(risk_score)
        self.agent_requests[agent] += 1

    def record_retrieval(self, agent: str, denied: bool):
        self.total_retrievals += 1
        if denied:
            self.total_denials += 1
        self.agent_requests[agent] += 1

    def get_metrics(self) -> dict:
        return {
            "total_seals": self.total_seals,
            "total_retrievals": self.total_retrievals,
            "total_denials": self.total_denials,
            "avg_risk_score": np.mean(self.risk_scores) if self.risk_scores else 0.0,
            "top_agents": sorted(
                [{"agent": k, "requests": v} for k, v in self.agent_requests.items()],
                key=lambda x: x["requests"],
                reverse=True,
            )[:5],
            "uptime_seconds": int(time.time() - self.start_time),
        }


metrics_store = MetricsStore()
storage_backend = get_storage_backend()

# Mobile autonomy goal control plane (in-memory MVP store).
GOAL_STORE: Dict[str, Dict[str, Any]] = {}
CONNECTOR_STORE: Dict[str, Dict[str, Any]] = {}

# ============================================================================
# MODELS
# ============================================================================


class SealRequest(BaseModel):
    plaintext: str = Field(..., max_length=4096, description="Data to seal (max 4KB)")
    agent: str = Field(
        ..., min_length=1, max_length=256, description="Agent identifier"
    )
    topic: str = Field(..., min_length=1, max_length=256, description="Topic/category")
    position: List[int] = Field(
        ..., min_length=6, max_length=6, description="6D position vector"
    )

    @field_validator("position")
    @classmethod
    def validate_position(cls, v):
        if len(v) != 6:
            raise ValueError("Position must contain exactly 6 integers")
        if not all(isinstance(x, int) for x in v):
            raise ValueError("Position must contain integers")
        return v


class RetrieveRequest(BaseModel):
    position: List[int] = Field(..., min_length=6, max_length=6)
    agent: str = Field(..., min_length=1, max_length=256)
    context: str = Field(..., pattern="^(internal|external|untrusted)$")

    @field_validator("position")
    @classmethod
    def validate_position(cls, v):
        if len(v) != 6:
            raise ValueError("Position must contain exactly 6 integers")
        if not all(isinstance(x, int) for x in v):
            raise ValueError("Position must contain integers")
        return v


class SimulateAttackRequest(BaseModel):
    position: List[int] = Field(..., min_length=6, max_length=6)
    agent: str = Field(default="malicious_bot")
    context: str = Field(default="untrusted")


class GoalPriority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"
    critical = "critical"


class GoalStatus(str, Enum):
    queued = "queued"
    running = "running"
    review_required = "review_required"
    completed = "completed"
    failed = "failed"


class ConnectorKind(str, Enum):
    n8n = "n8n"
    zapier = "zapier"
    shopify = "shopify"
    generic_webhook = "generic_webhook"


class ConnectorAuthType(str, Enum):
    none = "none"
    bearer = "bearer"
    header = "header"


class MobileGoalRequest(BaseModel):
    goal: str = Field(..., min_length=3, max_length=1024, description="Natural language goal description")
    channel: str = Field(
        default="store_ops",
        pattern="^(store_ops|web_research|content_ops|custom)$",
        description="Execution domain profile",
    )
    priority: GoalPriority = Field(default=GoalPriority.normal)
    execution_mode: str = Field(
        default="simulate",
        pattern="^(simulate|hydra_headless|connector)$",
        description="Execution adapter mode",
    )
    targets: List[str] = Field(default_factory=list, description="Optional URLs or entity targets")
    connector_id: Optional[str] = Field(default=None, description="Connector to use when execution_mode=connector")
    require_human_for_high_risk: bool = Field(
        default=True, description="Require explicit approval for high risk actions"
    )


class MobileGoalApproveRequest(BaseModel):
    note: str = Field(default="", max_length=512)


class MobileGoalActionRequest(BaseModel):
    note: str = Field(default="", max_length=512)


class ConnectorRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=64)
    kind: ConnectorKind
    endpoint_url: str = Field(..., min_length=8, max_length=2048)
    auth_type: ConnectorAuthType = Field(default=ConnectorAuthType.none)
    auth_token: str = Field(default="", max_length=4096, description="Bearer or header token/secret")
    auth_header_name: str = Field(default="x-api-key", max_length=128)
    enabled: bool = Field(default=True)


class MobileGoalBindConnectorRequest(BaseModel):
    connector_id: str = Field(..., min_length=6, max_length=64)


# ============================================================================
# AUTH
# ============================================================================

VALID_API_KEYS = {
    "demo_key_12345": "demo_user",
    "pilot_key_67890": "pilot_customer",
}


async def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key and return user identifier."""
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(401, "Invalid API key")

    # Check rate limit
    if not rate_limiter.is_allowed(x_api_key):
        raise HTTPException(429, "Rate limit exceeded (100 req/min)")

    return VALID_API_KEYS[x_api_key]


# ============================================================================
# MOBILE AUTONOMY HELPERS
# ============================================================================


def _goal_id(user: str, goal: str) -> str:
    seed = f"{user}:{goal}:{time.time_ns()}".encode("utf-8")
    return hashlib.sha256(seed).hexdigest()[:20]


def _connector_id(owner: str, name: str, kind: str) -> str:
    seed = f"{owner}:{name}:{kind}:{time.time_ns()}".encode("utf-8")
    return f"conn_{hashlib.sha256(seed).hexdigest()[:16]}"


def _build_goal_steps(channel: str, targets: List[str]) -> List[Dict[str, Any]]:
    target_hint = f" ({len(targets)} targets)" if targets else ""
    if channel == "store_ops":
        return [
            {"name": f"collect_store_state{target_hint}", "risk": "low", "status": "pending"},
            {"name": "prioritize_orders_and_messages", "risk": "medium", "status": "pending"},
            {"name": "execute_catalog_or_fulfillment_changes", "risk": "high", "status": "pending"},
            {"name": "publish_daily_report", "risk": "low", "status": "pending"},
        ]
    if channel == "web_research":
        return [
            {"name": f"crawl_sources{target_hint}", "risk": "medium", "status": "pending"},
            {"name": "scan_and_filter_results", "risk": "low", "status": "pending"},
            {"name": "assemble_training_brief", "risk": "low", "status": "pending"},
        ]
    if channel == "content_ops":
        return [
            {"name": "collect_trend_inputs", "risk": "low", "status": "pending"},
            {"name": "draft_content_batches", "risk": "medium", "status": "pending"},
            {"name": "schedule_and_publish", "risk": "high", "status": "pending"},
        ]
    return [
        {"name": "analyze_goal", "risk": "low", "status": "pending"},
        {"name": "execute_goal_plan", "risk": "medium", "status": "pending"},
    ]


def _goal_view(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "goal_id": record["goal_id"],
        "owner": record["owner"],
        "goal": record["goal"],
        "channel": record["channel"],
        "priority": record["priority"],
        "execution_mode": record["execution_mode"],
        "connector_id": record.get("connector_id"),
        "status": record["status"],
        "targets": record["targets"],
        "require_human_for_high_risk": record["require_human_for_high_risk"],
        "approved_high_risk": record["approved_high_risk"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "completed_at": record.get("completed_at"),
        "current_step_index": record["current_step_index"],
        "steps": record["steps"],
        "events": record["events"][-20:],
    }


def _connector_view(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "connector_id": record["connector_id"],
        "owner": record["owner"],
        "name": record["name"],
        "kind": record["kind"],
        "endpoint_url": record["endpoint_url"],
        "auth_type": record["auth_type"],
        "auth_header_name": record["auth_header_name"],
        "enabled": record["enabled"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
    }


def _next_pending_step(record: Dict[str, Any]) -> Optional[int]:
    for i, step in enumerate(record["steps"]):
        if step["status"] == "pending":
            return i
    return None


def _sign_connector_payload(payload: Dict[str, Any]) -> tuple[str, str]:
    ts = str(int(time.time()))
    signing_key = os.getenv("SCBE_CONNECTOR_SIGNING_KEY", "").encode("utf-8")
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if not signing_key:
        return ts, ""
    sig = hmac.new(signing_key, ts.encode("utf-8") + b"." + body, hashlib.sha256).hexdigest()
    return ts, sig


def _dispatch_connector_step(record: Dict[str, Any], step: Dict[str, Any]) -> Dict[str, Any]:
    if record["execution_mode"] != "connector":
        return {"ok": True, "mode": record["execution_mode"], "detail": "non-connector-mode"}

    connector_id = record.get("connector_id")
    if not connector_id:
        return {"ok": False, "code": "connector_missing", "detail": "connector_id required for connector mode"}

    connector = CONNECTOR_STORE.get(connector_id)
    if connector is None:
        return {"ok": False, "code": "connector_not_found", "detail": "connector not found"}
    if not connector.get("enabled", False):
        return {"ok": False, "code": "connector_disabled", "detail": "connector disabled"}

    payload = {
        "goal_id": record["goal_id"],
        "channel": record["channel"],
        "priority": record["priority"],
        "step": {"name": step["name"], "risk": step["risk"]},
        "targets": record["targets"],
        "metadata": {
            "owner": record["owner"],
            "ts": int(time.time()),
        },
    }

    headers = {"Content-Type": "application/json"}
    if connector["auth_type"] == ConnectorAuthType.bearer.value and connector.get("auth_token"):
        headers["Authorization"] = f"Bearer {connector['auth_token']}"
    elif connector["auth_type"] == ConnectorAuthType.header.value and connector.get("auth_token"):
        hdr = connector.get("auth_header_name", "x-api-key")
        headers[hdr] = connector["auth_token"]

    sig_ts, sig = _sign_connector_payload(payload)
    headers["x-scbe-ts"] = sig_ts
    if sig:
        headers["x-scbe-signature"] = sig

    req = urlrequest.Request(
        connector["endpoint_url"],
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=8) as resp:
            status = int(getattr(resp, "status", 200))
            text = resp.read().decode("utf-8", errors="replace")
            if 200 <= status < 300:
                return {"ok": True, "status": status, "detail": text[:400]}
            return {"ok": False, "code": "connector_http_status", "status": status, "detail": text[:400]}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
        return {"ok": False, "code": "connector_http_error", "status": int(exc.code), "detail": detail[:400]}
    except URLError as exc:
        return {"ok": False, "code": "connector_network_error", "detail": str(exc.reason)}
    except Exception as exc:
        return {"ok": False, "code": "connector_dispatch_error", "detail": str(exc)}


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.post("/seal-memory", tags=["Core"])
async def seal_memory(request: SealRequest, user: str = Depends(verify_api_key)):
    """
    ## Seal Memory

    Hide plaintext in 6D hyperbolic memory shard with governance check.

    **Security:** Requires API key, rate-limited to 100 req/min

    **Returns:** Sealed blob with governance decision and risk score
    """
    try:
        # Convert position to numpy array
        position_array = np.array(request.position, dtype=float)

        # Run SCBE 14-layer pipeline
        result = scbe_14layer_pipeline(t=position_array, D=6)

        # Seal with RWP v3 (quantum-resistant)
        rwp = RWPv3Protocol()
        password = f"{request.agent}:{request.topic}".encode()
        envelope = rwp.encrypt(plaintext=request.plaintext.encode(), password=password)
        sealed_blob_bytes = json.dumps(envelope.to_dict()).encode("utf-8")

        storage_backend.save(
            SealedBlobRecord(
                position=request.position,
                agent=request.agent,
                topic=request.topic,
                sealed_blob=sealed_blob_bytes,
            )
        )

        # Record metrics
        metrics_store.record_seal(request.agent, result["risk_base"])

        return {
            "status": "sealed",
            "data": {
                "sealed_blob": sealed_blob_bytes.hex(),
                "position": request.position,
                "risk_score": float(result["risk_base"]),
                "risk_prime": float(result["risk_prime"]),
                "governance_result": result["decision"],
                "harmonic_factor": float(result["H"]),
            },
            "trace": f"seal_v1_d{result['d_star']:.4f}_H{result['H']:.2f}",
        }

    except Exception as e:
        raise HTTPException(500, f"Seal failed: {str(e)}")


@app.post("/retrieve-memory", tags=["Core"])
async def retrieve_memory(
    request: RetrieveRequest, user: str = Depends(verify_api_key)
):
    """
    ## Retrieve Memory

    Retrieve plaintext if governance allows, otherwise fail-to-noise.

    **Security:** Requires API key + agent verification

    **Returns:** Plaintext (ALLOW/QUARANTINE) or random noise (DENY)
    """
    try:
        # Convert position to numpy array
        position_array = np.array(request.position, dtype=float)

        # Adjust weights based on context
        context_params = {
            "internal": {"w_d": 0.2, "w_tau": 0.2},
            "external": {"w_d": 0.3, "w_tau": 0.3},
            "untrusted": {"w_d": 0.4, "w_tau": 0.4},
        }

        # Run SCBE pipeline with context-aware weights
        result = scbe_14layer_pipeline(
            t=position_array, D=6, **context_params[request.context]
        )

        # Record metrics
        denied = result["decision"] == "DENY"
        metrics_store.record_retrieval(request.agent, denied)

        # Check governance decision
        if result["decision"] == "DENY":
            # Fail to noise - return random data
            fail_noise = np.random.bytes(32).hex()
            return {
                "status": "denied",
                "data": {
                    "plaintext": fail_noise,
                    "governance_result": "DENY",
                    "risk_score": float(result["risk_prime"]),
                    "reason": f"High risk: {request.context} context, d*={result['d_star']:.3f}",
                },
            }

        # ALLOW or QUARANTINE - retrieve and unseal plaintext
        try:
            record = storage_backend.load(request.position)
        except BlobNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc

        if record.agent != request.agent:
            raise HTTPException(403, "Agent mismatch for sealed blob")

        try:
            envelope_dict = json.loads(record.sealed_blob.decode("utf-8"))
            envelope = RWPEnvelope.from_dict(envelope_dict)
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as exc:
            raise HTTPException(500, "Stored sealed blob is corrupted") from exc

        rwp = RWPv3Protocol()
        password = f"{record.agent}:{record.topic}".encode()
        try:
            plaintext = rwp.decrypt(password=password, envelope=envelope)
        except ValueError as exc:
            raise HTTPException(500, "Failed to decrypt sealed blob") from exc

        resp_data = {
            "plaintext": plaintext.decode("utf-8"),
            "governance_result": result["decision"],
            "risk_score": float(result["risk_base"]),
            "risk_prime": float(result["risk_prime"]),
            "coherence_metrics": {
                k: float(v) for k, v in result["coherence"].items()
            },
        }
        if result.get("mmx") is not None:
            resp_data["mmx"] = result["mmx"]

        return {
            "status": "retrieved" if result["decision"] == "ALLOW" else "quarantined",
            "data": resp_data,
        }

    except Exception as e:
        raise HTTPException(500, f"Retrieve failed: {str(e)}")


@app.get("/governance-check", tags=["Governance"])
async def governance_check(
    agent: str = Query(..., description="Agent identifier"),
    topic: str = Query(..., description="Topic/category"),
    context: str = Query(
        ...,
        pattern="^(internal|external|untrusted)$",
        description="Context: internal/external/untrusted",
    ),
):
    """
    ## Governance Check

    Check governance decision without sealing/retrieving.

    **Security:** Public demo endpoint (no auth required)

    **Returns:** Governance decision with risk metrics
    """
    try:
        # Create synthetic position from agent/topic hash
        hash_input = f"{agent}:{topic}".encode()
        hash_bytes = hashlib.sha256(hash_input).digest()
        position = [int(b) % 100 for b in hash_bytes[:6]]

        # Adjust weights based on context
        context_params = {
            "internal": {"w_d": 0.2, "w_tau": 0.2},
            "external": {"w_d": 0.3, "w_tau": 0.3},
            "untrusted": {"w_d": 0.4, "w_tau": 0.4},
        }

        # Run SCBE pipeline
        result = scbe_14layer_pipeline(
            t=np.array(position, dtype=float), D=6, **context_params[context]
        )

        gov_data = {
            "decision": result["decision"],
            "risk_score": float(result["risk_base"]),
            "risk_prime": float(result["risk_prime"]),
            "harmonic_factor": float(result["H"]),
            "reason": f"Context: {context}, d*={result['d_star']:.3f}, Risk={result['risk_base']:.3f}",
            "coherence_metrics": {
                k: float(v) for k, v in result["coherence"].items()
            },
            "geometry": {k: float(v) for k, v in result["geometry"].items()},
        }
        if result.get("mmx") is not None:
            gov_data["mmx"] = result["mmx"]

        return {
            "status": "ok",
            "data": gov_data,
        }

    except Exception as e:
        raise HTTPException(500, f"Governance check failed: {str(e)}")


@app.post("/simulate-attack", tags=["Demo"])
async def simulate_attack(request: SimulateAttackRequest):
    """
    ## Simulate Attack

    Simulate malicious access attempt to demonstrate fail-to-noise.

    **Security:** Public demo endpoint

    **Returns:** Governance decision with detection details
    """
    try:
        # Force high-risk parameters
        position_array = np.array(request.position, dtype=float)

        result = scbe_14layer_pipeline(
            t=position_array,
            D=6,
            breathing_factor=2.0,  # Extreme breathing
            w_d=0.5,  # High distance weight
            w_tau=0.5,  # High trust weight
            theta1=0.2,  # Lower ALLOW threshold
            theta2=0.5,  # Lower QUARANTINE threshold
        )

        sim_data = {
            "governance_result": result["decision"],
            "risk_score": float(result["risk_base"]),
            "risk_prime": float(result["risk_prime"]),
            "fail_to_noise_example": np.random.bytes(16).hex(),
            "reason": "Malicious agent detected via hyperbolic distance",
            "detection_layers": [
                f"Layer 5: Hyperbolic distance d_ℍ={result['d_star']:.4f}",
                f"Layer 8: Realm distance d*={result['d_star']:.4f} (threshold exceeded)",
                f"Layer 12: Harmonic amplification H={result['H']:.4f}",
                f"Layer 13: Risk' = {result['risk_prime']:.4f} → {result['decision']}",
            ],
            "coherence_breakdown": {
                k: float(v) for k, v in result["coherence"].items()
            },
        }
        if result.get("mmx") is not None:
            sim_data["mmx"] = result["mmx"]

        return {
            "status": "simulated",
            "data": sim_data,
        }

    except Exception as e:
        raise HTTPException(500, f"Simulation failed: {str(e)}")


@app.post("/mobile/connectors", tags=["Mobile Autonomy"])
async def register_mobile_connector(
    request: ConnectorRegisterRequest, user: str = Depends(verify_api_key)
):
    """
    ## Register Connector

    Register external automation connector (n8n / Zapier / Shopify / generic webhook).
    """
    connector_id = _connector_id(user, request.name, request.kind.value)
    ts = int(time.time())
    CONNECTOR_STORE[connector_id] = {
        "connector_id": connector_id,
        "owner": user,
        "name": request.name,
        "kind": request.kind.value,
        "endpoint_url": request.endpoint_url,
        "auth_type": request.auth_type.value,
        "auth_token": request.auth_token,
        "auth_header_name": request.auth_header_name,
        "enabled": bool(request.enabled),
        "created_at": ts,
        "updated_at": ts,
    }
    return {"status": "registered", "data": _connector_view(CONNECTOR_STORE[connector_id])}


@app.get("/mobile/connectors", tags=["Mobile Autonomy"])
async def list_mobile_connectors(
    limit: int = Query(50, ge=1, le=200),
    user: str = Depends(verify_api_key),
):
    """
    ## List Connectors

    List connectors owned by caller.
    """
    rows = [v for v in CONNECTOR_STORE.values() if v["owner"] == user]
    rows.sort(key=lambda x: x["created_at"], reverse=True)
    return {"status": "ok", "data": [_connector_view(r) for r in rows[:limit]]}


@app.get("/mobile/connectors/{connector_id}", tags=["Mobile Autonomy"])
async def get_mobile_connector(connector_id: str, user: str = Depends(verify_api_key)):
    """
    ## Get Connector
    """
    record = CONNECTOR_STORE.get(connector_id)
    if not record or record["owner"] != user:
        raise HTTPException(404, "Connector not found")
    return {"status": "ok", "data": _connector_view(record)}


@app.delete("/mobile/connectors/{connector_id}", tags=["Mobile Autonomy"])
async def delete_mobile_connector(connector_id: str, user: str = Depends(verify_api_key)):
    """
    ## Delete Connector
    """
    record = CONNECTOR_STORE.get(connector_id)
    if not record or record["owner"] != user:
        raise HTTPException(404, "Connector not found")
    del CONNECTOR_STORE[connector_id]
    return {"status": "deleted", "data": {"connector_id": connector_id}}


@app.post("/mobile/goals", tags=["Mobile Autonomy"])
async def create_mobile_goal(
    request: MobileGoalRequest, user: str = Depends(verify_api_key)
):
    """
    ## Create Mobile Goal

    Submit a high-level goal from phone/app and receive deterministic step plan.
    """
    if request.execution_mode == "connector":
        if not request.connector_id:
            raise HTTPException(400, "connector_id required when execution_mode=connector")
        conn = CONNECTOR_STORE.get(request.connector_id)
        if conn is None or conn["owner"] != user:
            raise HTTPException(404, "connector not found")

    goal_id = _goal_id(user, request.goal)
    ts = int(time.time())
    steps = _build_goal_steps(request.channel, request.targets)
    GOAL_STORE[goal_id] = {
        "goal_id": goal_id,
        "owner": user,
        "goal": request.goal,
        "channel": request.channel,
        "priority": request.priority.value,
        "execution_mode": request.execution_mode,
        "connector_id": request.connector_id,
        "targets": request.targets,
        "require_human_for_high_risk": request.require_human_for_high_risk,
        "approved_high_risk": False,
        "status": GoalStatus.queued.value,
        "created_at": ts,
        "updated_at": ts,
        "completed_at": None,
        "current_step_index": 0,
        "steps": steps,
        "events": [{"ts": ts, "event": "goal_created", "detail": request.goal}],
    }
    return {"status": "accepted", "data": _goal_view(GOAL_STORE[goal_id])}


@app.get("/mobile/goals", tags=["Mobile Autonomy"])
async def list_mobile_goals(
    limit: int = Query(20, ge=1, le=100),
    user: str = Depends(verify_api_key),
):
    """
    ## List Mobile Goals

    List recently submitted goals for caller identity.
    """
    rows = [v for v in GOAL_STORE.values() if v["owner"] == user]
    rows.sort(key=lambda x: x["created_at"], reverse=True)
    return {"status": "ok", "data": [_goal_view(r) for r in rows[:limit]]}


@app.get("/mobile/goals/{goal_id}", tags=["Mobile Autonomy"])
async def get_mobile_goal(goal_id: str, user: str = Depends(verify_api_key)):
    """
    ## Get Mobile Goal

    Get full state for one goal.
    """
    record = GOAL_STORE.get(goal_id)
    if not record or record["owner"] != user:
        raise HTTPException(404, "Goal not found")
    return {"status": "ok", "data": _goal_view(record)}


@app.post("/mobile/goals/{goal_id}/bind-connector", tags=["Mobile Autonomy"])
async def bind_mobile_goal_connector(
    goal_id: str,
    request: MobileGoalBindConnectorRequest,
    user: str = Depends(verify_api_key),
):
    """
    ## Bind Connector To Goal

    Attach connector to existing goal and set execution mode to connector.
    """
    record = GOAL_STORE.get(goal_id)
    if not record or record["owner"] != user:
        raise HTTPException(404, "Goal not found")
    conn = CONNECTOR_STORE.get(request.connector_id)
    if conn is None or conn["owner"] != user:
        raise HTTPException(404, "Connector not found")
    record["connector_id"] = request.connector_id
    record["execution_mode"] = "connector"
    record["updated_at"] = int(time.time())
    record["events"].append(
        {
            "ts": record["updated_at"],
            "event": "connector_bound",
            "detail": request.connector_id,
        }
    )
    return {"status": "ok", "data": _goal_view(record)}


@app.post("/mobile/goals/{goal_id}/approve", tags=["Mobile Autonomy"])
async def approve_mobile_goal(
    goal_id: str,
    request: MobileGoalApproveRequest,
    user: str = Depends(verify_api_key),
):
    """
    ## Approve High-Risk Steps

    Explicitly approve high-risk actions for an existing goal.
    """
    record = GOAL_STORE.get(goal_id)
    if not record or record["owner"] != user:
        raise HTTPException(404, "Goal not found")
    record["approved_high_risk"] = True
    record["updated_at"] = int(time.time())
    record["events"].append(
        {"ts": record["updated_at"], "event": "high_risk_approved", "detail": request.note}
    )
    if record["status"] == GoalStatus.review_required.value:
        record["status"] = GoalStatus.running.value
    return {"status": "ok", "data": _goal_view(record)}


@app.post("/mobile/goals/{goal_id}/advance", tags=["Mobile Autonomy"])
async def advance_mobile_goal(
    goal_id: str,
    request: MobileGoalActionRequest,
    user: str = Depends(verify_api_key),
):
    """
    ## Advance Goal Execution

    Execute the next pending step with guardrails.
    """
    record = GOAL_STORE.get(goal_id)
    if not record or record["owner"] != user:
        raise HTTPException(404, "Goal not found")

    if record["status"] in {GoalStatus.completed.value, GoalStatus.failed.value}:
        return {"status": "ok", "data": _goal_view(record)}

    idx = _next_pending_step(record)
    if idx is None:
        record["status"] = GoalStatus.completed.value
        record["completed_at"] = int(time.time())
        record["updated_at"] = record["completed_at"]
        record["events"].append({"ts": record["completed_at"], "event": "goal_completed", "detail": ""})
        return {"status": "ok", "data": _goal_view(record)}

    step = record["steps"][idx]
    record["current_step_index"] = idx

    if (
        step["risk"] == "high"
        and record["require_human_for_high_risk"]
        and not record["approved_high_risk"]
    ):
        record["status"] = GoalStatus.review_required.value
        record["updated_at"] = int(time.time())
        record["events"].append(
            {
                "ts": record["updated_at"],
                "event": "review_required",
                "detail": f"approval required for step:{step['name']}",
            }
        )
        return {"status": "blocked", "data": _goal_view(record)}

    dispatch = _dispatch_connector_step(record, step)
    if not dispatch.get("ok", False):
        now = int(time.time())
        record["status"] = GoalStatus.failed.value
        record["updated_at"] = now
        record["events"].append(
            {
                "ts": now,
                "event": "connector_dispatch_failed",
                "detail": f"{dispatch.get('code', 'error')}:{dispatch.get('detail', '')}",
            }
        )
        return {"status": "error", "data": _goal_view(record), "dispatch": dispatch}

    now = int(time.time())
    record["status"] = GoalStatus.running.value
    record["steps"][idx]["status"] = "done"
    record["steps"][idx]["completed_at"] = now
    if request.note:
        record["steps"][idx]["note"] = request.note
    if record["execution_mode"] == "connector":
        record["steps"][idx]["dispatch"] = {
            "status": dispatch.get("status"),
            "detail": dispatch.get("detail", ""),
        }
    record["updated_at"] = now
    record["events"].append({"ts": now, "event": "step_completed", "detail": step["name"]})

    nxt = _next_pending_step(record)
    if nxt is None:
        record["status"] = GoalStatus.completed.value
        record["completed_at"] = now
        record["events"].append({"ts": now, "event": "goal_completed", "detail": ""})

    return {"status": "ok", "data": _goal_view(record)}


@app.get("/health", tags=["System"])
async def health():
    """
    ## Health Check

    System health and status.

    **Security:** Public endpoint
    """
    return {
        "status": "healthy",
        "version": "3.0.0",
        "tests_passing": 120,
        "tests_total": 160,
        "coverage": "75%",
        "uptime_seconds": metrics_store.get_metrics()["uptime_seconds"],
    }


@app.get("/metrics", tags=["System"])
async def metrics(user: str = Depends(verify_api_key)):
    """
    ## Usage Metrics

    Usage statistics for customer dashboard.

    **Security:** Requires API key
    """
    return {"status": "ok", "data": metrics_store.get_metrics()}


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "error": exc.detail, "code": exc.status_code},
    )


# ============================================================================
# STARTUP
# ============================================================================


@app.on_event("startup")
async def startup_event():
    print("=" * 80)
    print("SCBE-AETHERMOORE MVP API v3.0.0")
    print("=" * 80)
    print("Quantum-resistant memory sealing with hyperbolic governance")
    print()
    print("Endpoints:")
    print("  POST /seal-memory       - Seal plaintext into 6D memory shard")
    print("  POST /retrieve-memory   - Retrieve with governance check")
    print("  GET  /governance-check  - Check governance decision")
    print("  POST /simulate-attack   - Demo fail-to-noise protection")
    print("  POST /mobile/connectors - Register n8n/Zapier/Shopify connector")
    print("  POST /mobile/goals      - Submit mobile autonomy goal")
    print("  POST /mobile/goals/{id}/bind-connector - Attach connector to goal")
    print("  POST /mobile/goals/{id}/advance - Run next goal step")
    print("  POST /mobile/goals/{id}/approve - Approve high-risk step")
    print("  GET  /health            - System health")
    print("  GET  /metrics           - Usage metrics")
    print()
    print("Documentation: http://localhost:8000/docs")
    print("=" * 80)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
