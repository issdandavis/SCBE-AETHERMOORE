#!/usr/bin/env python3
"""
SCBE-AETHERMOORE SaaS API
============================
Multi-tenant, credit-metered API for governed AI agent fleets.

A company signs up, gets an API key, and can:
- Manage a fleet of governed AI agents
- Dispatch tasks with BFT consensus governance
- Ingest documents into a cultural knowledge base (Heart Vault)
- Scan content through the SemanticAntivirus pipeline
- Track credit usage via the MMCCL blockchain ledger

Run:
    uvicorn src.api.saas_api:app --port 8000

Or:
    python -m src.api.saas_api
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
import time
import uuid
from collections import defaultdict
from dataclasses import asdict
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Header, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
#  Path setup — allow running from project root
# ---------------------------------------------------------------------------
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.symphonic_cipher.scbe_aethermoore.flock_shepherd import (
    Flock,
    FlockTask,
    Sheep,
    SheepRole,
    SheepState,
    TrainingTrack,
)
from src.symphonic_cipher.scbe_aethermoore.concept_blocks.heart_vault.graph import (
    HeartVaultGraph,
    NodeType,
    TongueAffinity,
)
from src.symphonic_cipher.scbe_aethermoore.concept_blocks.web_agent.semantic_antivirus import (
    SemanticAntivirus,
)
from src.symphonic_cipher.scbe_aethermoore.concept_blocks.context_credit_ledger.credit import (
    ContextCredit,
    Denomination,
    mint_credit,
)
from src.symphonic_cipher.scbe_aethermoore.concept_blocks.context_credit_ledger.ledger import (
    ContextLedger,
)

# ============================================================================
#  APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="SCBE-AETHERMOORE SaaS API",
    version="1.0.0",
    description=(
        "Multi-tenant governed AI agent fleet management. "
        "Each API call is credit-metered via the MMCCL blockchain ledger."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
#  MULTI-TENANT STATE
# ============================================================================

# API key -> tenant_id
API_KEY_REGISTRY: Dict[str, str] = {
    "sk_test_acme_001": "tenant_acme",
    "sk_test_globex_002": "tenant_globex",
    "sk_test_demo_999": "tenant_demo",
}


class _ThreadSafeHeartVault(HeartVaultGraph):
    """HeartVaultGraph with check_same_thread=False for async API use."""

    def __init__(self, db_path: str = ":memory:"):
        # Bypass parent __init__ and replicate with thread-safe connection
        import sqlite3 as _sql
        self._db_path = db_path
        self._conn = _sql.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        # Import schema constant from parent module
        from src.symphonic_cipher.scbe_aethermoore.concept_blocks.heart_vault.graph import (
            _SCHEMA,
        )
        self._conn.executescript(_SCHEMA)
        self._conn.commit()


class TenantState:
    """Isolated per-tenant state: flock, knowledge vault, antivirus, ledger."""

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        self.flock = Flock()
        self.vault = _ThreadSafeHeartVault(":memory:")
        self.antivirus = SemanticAntivirus()
        self.ledger = ContextLedger(validator_id=f"{tenant_id}-validator")
        self.created_at = time.time()

        # Simple credit balance (starts with 10 000 free credits)
        self.credit_balance: float = 10_000.0
        self.usage_log: List[Dict[str, Any]] = []


# Lazily-created per-tenant stores
_TENANTS: Dict[str, TenantState] = {}


def _get_tenant(tenant_id: str) -> TenantState:
    if tenant_id not in _TENANTS:
        _TENANTS[tenant_id] = TenantState(tenant_id)
    return _TENANTS[tenant_id]


# ============================================================================
#  RATE LIMITER
# ============================================================================

class RateLimiter:
    """In-memory sliding-window rate limiter (200 req/min per key)."""

    def __init__(self, max_requests: int = 200, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: Dict[str, List[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        bucket = self._buckets[key]
        self._buckets[key] = [t for t in bucket if t > cutoff]
        if len(self._buckets[key]) >= self.max_requests:
            return False
        self._buckets[key].append(now)
        return True


_rate_limiter = RateLimiter()


# ============================================================================
#  AUTH DEPENDENCY
# ============================================================================

async def _authenticate(x_api_key: str = Header(...)) -> str:
    """Verify API key and return tenant_id."""
    tenant_id = API_KEY_REGISTRY.get(x_api_key)
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not _rate_limiter.check(x_api_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded (200 req/min)")
    return tenant_id


# ============================================================================
#  CREDIT HELPERS
# ============================================================================

# Cost table (credits per operation)
CREDIT_COSTS: Dict[str, float] = {
    "fleet.spawn": 50.0,
    "fleet.status": 1.0,
    "fleet.dispatch": 25.0,
    "fleet.retire": 10.0,
    "fleet.health": 1.0,
    "tasks.create": 10.0,
    "tasks.list": 1.0,
    "tasks.get": 1.0,
    "tasks.complete": 5.0,
    "knowledge.ingest": 20.0,
    "knowledge.query": 5.0,
    "knowledge.stats": 1.0,
    "safety.scan": 15.0,
    "safety.governance": 1.0,
    "safety.check": 10.0,
    "billing.balance": 0.0,
    "billing.usage": 0.0,
    "billing.leaderboard": 1.0,
}


def _charge(tenant: TenantState, operation: str, detail: str = "") -> float:
    """Deduct credits for an operation. Returns credits used. Raises 402 if broke."""
    cost = CREDIT_COSTS.get(operation, 1.0)
    if cost > 0 and tenant.credit_balance < cost:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Need {cost}, have {tenant.credit_balance:.2f}",
        )
    tenant.credit_balance -= cost
    tenant.usage_log.append({
        "operation": operation,
        "credits": cost,
        "detail": detail,
        "timestamp": time.time(),
        "balance_after": tenant.credit_balance,
    })
    return cost


def _ok(data: Any, credits_used: float = 0.0) -> Dict[str, Any]:
    return {"status": "ok", "data": data, "credits_used": credits_used}


def _serialize_sheep(s: Sheep) -> Dict[str, Any]:
    return {
        "agent_id": s.sheep_id,
        "name": s.name,
        "role": s.role.value,
        "state": s.state.value,
        "track": s.track.value,
        "coherence": round(s.coherence, 4),
        "error_rate": round(s.error_rate, 4),
        "tasks_completed": s.tasks_completed,
        "tasks_failed": s.tasks_failed,
        "health_label": s.health_label,
        "tongue": s.tongue,
        "current_task": s.current_task,
        "is_available": s.is_available,
    }


def _serialize_task(t: FlockTask) -> Dict[str, Any]:
    return {
        "task_id": t.task_id,
        "description": t.description,
        "track": t.track.value,
        "priority": t.priority,
        "owner": t.owner,
        "status": t.status,
        "result": t.result,
        "created_at": t.created_at,
    }


# ============================================================================
#  REQUEST MODELS
# ============================================================================

class SpawnRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Agent name")
    role: Optional[str] = Field(None, description="Role: leader/validator/executor/observer")
    track: str = Field("system", description="Training track: system/governance/functions")
    model: Optional[str] = Field(None, description="Model identifier (informational)")


class DispatchRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=2048)
    track: str = Field("system", description="Training track preference")
    priority: int = Field(5, ge=1, le=10, description="Priority 1 (highest) to 10 (lowest)")


class TaskCreateRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=2048)
    track: str = Field("system")
    priority: int = Field(5, ge=1, le=10)
    deadline: Optional[float] = Field(None, description="Unix timestamp deadline")


class TaskCompleteRequest(BaseModel):
    result: Any = Field(None, description="Task result payload")
    success: bool = Field(True, description="Whether the task succeeded")


class IngestRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=65536, description="Document text")
    source: str = Field("api", max_length=256, description="Source identifier")
    category: str = Field("CONCEPT", description="Node type: EMOTION/LITERARY/PROVERB/CONCEPT/SOURCE")
    tongue: Optional[str] = Field(None, description="Sacred Tongue affinity: KO/AV/RU/CA/UM/DR")


class KnowledgeQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=512)
    tongue: Optional[str] = Field(None)
    limit: int = Field(10, ge=1, le=100)


class ScanRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=65536)
    url: Optional[str] = Field(None, description="Optional URL context")


class GovernanceCheckRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=65536)
    agent_id: Optional[str] = Field(None, description="Agent to check against")


# ============================================================================
#  1. /api/v1/fleet -- Agent Fleet Management
# ============================================================================

@app.post("/api/v1/fleet/spawn", tags=["Fleet"])
async def fleet_spawn(req: SpawnRequest, tenant_id: str = Depends(_authenticate)):
    """Spawn a new governed AI agent in the fleet."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "fleet.spawn", req.name)

    # Parse track
    try:
        track = TrainingTrack(req.track)
    except ValueError:
        raise HTTPException(400, f"Invalid track: {req.track}. Use system/governance/functions")

    # Parse role
    role = None
    if req.role:
        try:
            role = SheepRole(req.role)
        except ValueError:
            raise HTTPException(400, f"Invalid role: {req.role}. Use leader/validator/executor/observer")

    agent = tenant.flock.spawn(name=req.name, track=track, role=role)

    # Mint a credit for the spawn event
    _mint_operation_credit(tenant, agent.sheep_id, "fleet.spawn", cost)

    return _ok(_serialize_sheep(agent), cost)


@app.get("/api/v1/fleet/status", tags=["Fleet"])
async def fleet_status(tenant_id: str = Depends(_authenticate)):
    """Get full fleet status: all agents, active tasks, event log."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "fleet.status")

    agents = [_serialize_sheep(s) for s in tenant.flock.sheep.values()]
    tasks = [_serialize_task(t) for t in tenant.flock.tasks.values()]

    return _ok({
        "agents": agents,
        "agent_count": len(agents),
        "tasks": tasks,
        "task_count": len(tasks),
        "pending_tasks": sum(1 for t in tenant.flock.tasks.values() if t.status == "pending"),
        "active_tasks": sum(1 for t in tenant.flock.tasks.values() if t.status == "active"),
    }, cost)


@app.post("/api/v1/fleet/dispatch", tags=["Fleet"])
async def fleet_dispatch(req: DispatchRequest, tenant_id: str = Depends(_authenticate)):
    """Dispatch a task to the best available agent, governed by BFT consensus."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "fleet.dispatch", req.description[:80])

    try:
        track = TrainingTrack(req.track)
    except ValueError:
        raise HTTPException(400, f"Invalid track: {req.track}")

    # Governance vote before dispatch
    vote = tenant.flock.vote_on_action(f"dispatch:{req.description[:60]}")
    if vote["consensus"] == "DENY":
        return _ok({
            "dispatched": False,
            "reason": "Governance vote DENIED the dispatch",
            "vote": vote,
        }, cost)

    # Create and auto-assign
    task = tenant.flock.add_task(description=req.description, track=track, priority=req.priority)
    assigned = tenant.flock.assign_task(task.task_id)

    result = {
        "dispatched": assigned,
        "task": _serialize_task(task),
        "governance_vote": vote,
    }
    if assigned and task.owner:
        agent = tenant.flock.sheep.get(task.owner)
        if agent:
            result["assigned_to"] = _serialize_sheep(agent)

    _mint_operation_credit(tenant, task.owner or "flock", "fleet.dispatch", cost)

    return _ok(result, cost)


@app.post("/api/v1/fleet/retire/{agent_id}", tags=["Fleet"])
async def fleet_retire(agent_id: str, tenant_id: str = Depends(_authenticate)):
    """Retire an agent from the fleet. Orphaned tasks get redistributed."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "fleet.retire", agent_id)

    if agent_id not in tenant.flock.sheep:
        raise HTTPException(404, f"Agent {agent_id} not found")

    agent_name = tenant.flock.sheep[agent_id].name
    retired = tenant.flock.retire(agent_id)

    # Redistribute any orphaned tasks
    redistributed = tenant.flock.redistribute_orphans()

    return _ok({
        "retired": retired,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "orphaned_tasks_redistributed": redistributed,
    }, cost)


@app.get("/api/v1/fleet/health", tags=["Fleet"])
async def fleet_health(tenant_id: str = Depends(_authenticate)):
    """Fleet health dashboard: overall score, BFT status, recommendations."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "fleet.health")

    health = tenant.flock.health_check()

    # Build recommendations
    recommendations: List[str] = []
    if health["total"] == 0:
        recommendations.append("No agents in fleet. Spawn agents via POST /api/v1/fleet/spawn.")
    else:
        if health["avg_coherence"] < 0.5:
            recommendations.append("Fleet coherence is low. Consider retiring degraded agents.")
        if health["isolated"] > 0:
            recommendations.append(f"{health['isolated']} agents are quarantined. Review and recover or retire them.")
        if health["bft_tolerance"] == 0 and health["total"] > 0:
            recommendations.append("BFT tolerance is 0. Add more agents for Byzantine fault tolerance.")
        if health["frozen"] > 0:
            recommendations.append(f"{health['frozen']} agents are frozen (attack detected). Investigate immediately.")

        # Track coverage
        for track_name, info in health["tracks"].items():
            if info["count"] == 0:
                recommendations.append(f"No agents on '{track_name}' track. Consider spawning one.")

    # Overall health score (0-100)
    if health["total"] > 0:
        coherence_score = health["avg_coherence"] * 40
        availability_score = ((health["active"] + health["idle"]) / health["total"]) * 30
        bft_score = min(1.0, health["bft_tolerance"] / max(1, health["total"] // 3)) * 20
        diversity_score = (sum(1 for t in health["tracks"].values() if t["count"] > 0) / 3) * 10
        overall_score = round(coherence_score + availability_score + bft_score + diversity_score, 1)
    else:
        overall_score = 0.0

    return _ok({
        "overall_score": overall_score,
        "health": health,
        "bft_tolerance": health["bft_tolerance"],
        "recommendations": recommendations,
    }, cost)


# ============================================================================
#  2. /api/v1/tasks -- Task Management
# ============================================================================

@app.post("/api/v1/tasks", tags=["Tasks"])
async def tasks_create(req: TaskCreateRequest, tenant_id: str = Depends(_authenticate)):
    """Create a task in the queue (not yet assigned)."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "tasks.create", req.description[:80])

    try:
        track = TrainingTrack(req.track)
    except ValueError:
        raise HTTPException(400, f"Invalid track: {req.track}")

    task = tenant.flock.add_task(description=req.description, track=track, priority=req.priority)
    return _ok(_serialize_task(task), cost)


@app.get("/api/v1/tasks", tags=["Tasks"])
async def tasks_list(
    status: Optional[str] = Query(None, description="Filter by status: pending/active/completed/failed/orphaned"),
    tenant_id: str = Depends(_authenticate),
):
    """List all tasks with optional status filter."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "tasks.list")

    tasks = list(tenant.flock.tasks.values())
    if status:
        tasks = [t for t in tasks if t.status == status]

    tasks.sort(key=lambda t: (t.priority, t.created_at))
    return _ok([_serialize_task(t) for t in tasks], cost)


@app.get("/api/v1/tasks/{task_id}", tags=["Tasks"])
async def tasks_get(task_id: str, tenant_id: str = Depends(_authenticate)):
    """Get task details and result."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "tasks.get")

    task = tenant.flock.tasks.get(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")

    data = _serialize_task(task)

    # Include assigned agent info if available
    if task.owner:
        agent = tenant.flock.sheep.get(task.owner)
        if agent:
            data["assigned_agent"] = _serialize_sheep(agent)

    return _ok(data, cost)


@app.post("/api/v1/tasks/{task_id}/complete", tags=["Tasks"])
async def tasks_complete(task_id: str, req: TaskCompleteRequest, tenant_id: str = Depends(_authenticate)):
    """Mark a task as complete with result."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "tasks.complete")

    task = tenant.flock.tasks.get(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")
    if task.status not in ("pending", "active"):
        raise HTTPException(400, f"Task is already {task.status}")

    # Complete the task
    task.result = req.result
    task.status = "completed" if req.success else "failed"

    # Update the owning agent
    if task.owner:
        agent = tenant.flock.sheep.get(task.owner)
        if agent:
            agent.complete_task(success=req.success)

    _mint_operation_credit(tenant, task.owner or "system", "tasks.complete", cost)

    return _ok(_serialize_task(task), cost)


# ============================================================================
#  3. /api/v1/knowledge -- Company Knowledge Base (Heart Vault)
# ============================================================================

@app.post("/api/v1/knowledge/ingest", tags=["Knowledge"])
async def knowledge_ingest(req: IngestRequest, tenant_id: str = Depends(_authenticate)):
    """Ingest a document into the Heart Vault knowledge graph."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "knowledge.ingest", req.source)

    # Map category string to NodeType
    try:
        node_type = NodeType(req.category.upper())
    except ValueError:
        raise HTTPException(400, f"Invalid category: {req.category}. Use EMOTION/LITERARY/PROVERB/CONCEPT/SOURCE")

    # Map tongue string
    tongue = None
    if req.tongue:
        try:
            tongue = TongueAffinity(req.tongue.upper())
        except ValueError:
            raise HTTPException(400, f"Invalid tongue: {req.tongue}. Use KO/AV/RU/CA/UM/DR")

    # Governance scan before ingestion
    threat = tenant.antivirus.scan(req.text)
    if threat.governance_decision == "DENY":
        return _ok({
            "ingested": False,
            "reason": "Content blocked by SemanticAntivirus",
            "threat_profile": threat.to_dict(),
        }, cost)

    # Compute quality score from safety
    quality_score = threat.hamiltonian_score

    # Add node to vault
    node = tenant.vault.add_node(
        node_type=node_type,
        label=req.text[:256],
        properties={
            "full_text": req.text,
            "source": req.source,
            "risk_score": threat.risk_score,
            "hamiltonian_score": threat.hamiltonian_score,
            "governance_decision": threat.governance_decision,
        },
        tongue=tongue,
        quality_score=quality_score,
    )

    _mint_operation_credit(tenant, tenant_id, "knowledge.ingest", cost)

    return _ok({
        "ingested": True,
        "node_id": node.id,
        "node_type": node.node_type.value,
        "label": node.label,
        "quality_score": round(quality_score, 4),
        "tongue": tongue.value if tongue else None,
        "threat_profile": threat.to_dict(),
    }, cost)


@app.get("/api/v1/knowledge/query", tags=["Knowledge"])
async def knowledge_query(
    query: str = Query(..., min_length=1, max_length=512),
    tongue: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    tenant_id: str = Depends(_authenticate),
):
    """Query the knowledge base with optional tongue filter."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "knowledge.query")

    tongue_filter = None
    if tongue:
        try:
            tongue_filter = TongueAffinity(tongue.upper())
        except ValueError:
            raise HTTPException(400, f"Invalid tongue: {tongue}")

    nodes = tenant.vault.find_nodes(
        label_contains=query,
        tongue=tongue_filter,
        limit=limit,
    )

    results = []
    for n in nodes:
        results.append({
            "node_id": n.id,
            "node_type": n.node_type.value,
            "label": n.label,
            "quality_score": round(n.quality_score, 4),
            "tongue": n.tongue.value if n.tongue else None,
            "properties": n.properties,
        })

    return _ok({
        "query": query,
        "results": results,
        "total": len(results),
    }, cost)


@app.get("/api/v1/knowledge/stats", tags=["Knowledge"])
async def knowledge_stats(tenant_id: str = Depends(_authenticate)):
    """Knowledge base statistics."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "knowledge.stats")
    stats = tenant.vault.stats()
    return _ok(stats, cost)


# ============================================================================
#  4. /api/v1/safety -- Governance & Safety
# ============================================================================

@app.post("/api/v1/safety/scan", tags=["Safety"])
async def safety_scan(req: ScanRequest, tenant_id: str = Depends(_authenticate)):
    """Scan text through the SemanticAntivirus pipeline."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "safety.scan")

    threat = tenant.antivirus.scan(req.text, url=req.url)

    return _ok({
        "threat_profile": threat.to_dict(),
        "is_safe": threat.governance_decision == "ALLOW",
        "session_stats": tenant.antivirus.session_stats,
    }, cost)


@app.get("/api/v1/safety/governance", tags=["Safety"])
async def safety_governance(tenant_id: str = Depends(_authenticate)):
    """Get current governance configuration and antivirus session state."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "safety.governance")

    # Governance config
    flock_health = tenant.flock.health_check()

    return _ok({
        "antivirus_session": tenant.antivirus.session_stats,
        "flock_governance": {
            "bft_tolerance": flock_health["bft_tolerance"],
            "total_agents": flock_health["total"],
            "active_validators": sum(
                1 for s in tenant.flock.sheep.values()
                if s.role == SheepRole.VALIDATOR and s.state == SheepState.ACTIVE
            ),
            "avg_coherence": flock_health["avg_coherence"],
        },
        "safety_threshold": tenant.antivirus._safety_threshold,
        "layers": {
            "L1": "Quantum Entropy (content unpredictability)",
            "L2": "Hamiltonian Safety H(d,pd)",
            "L5": "Governance Mesh (rule-based filtering)",
            "L8": "Adversarial Resilience (injection detection)",
            "L10": "Constitutional Alignment (value filtering)",
        },
    }, cost)


@app.post("/api/v1/safety/check", tags=["Safety"])
async def safety_check(req: GovernanceCheckRequest, tenant_id: str = Depends(_authenticate)):
    """Run full governance check on a prompt: antivirus scan + fleet vote."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "safety.check")

    # Step 1: Antivirus scan
    threat = tenant.antivirus.scan(req.prompt)

    # Step 2: Fleet governance vote
    vote = tenant.flock.vote_on_action(f"prompt-check:{req.prompt[:60]}")

    # Step 3: Combine decisions
    antivirus_ok = threat.governance_decision == "ALLOW"
    vote_ok = vote["consensus"] in ("ALLOW", "QUARANTINE")

    # Final decision: both must agree
    if antivirus_ok and vote_ok:
        final_decision = "ALLOW"
    elif threat.governance_decision == "DENY" or vote["consensus"] == "DENY":
        final_decision = "DENY"
    else:
        final_decision = "QUARANTINE"

    return _ok({
        "final_decision": final_decision,
        "antivirus": threat.to_dict(),
        "fleet_vote": vote,
        "antivirus_passed": antivirus_ok,
        "vote_passed": vote_ok,
    }, cost)


# ============================================================================
#  5. /api/v1/billing -- Usage & Credits
# ============================================================================

@app.get("/api/v1/billing/balance", tags=["Billing"])
async def billing_balance(tenant_id: str = Depends(_authenticate)):
    """Get current credit balance."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "billing.balance")  # Free

    total_spent = sum(e["credits"] for e in tenant.usage_log)

    return _ok({
        "tenant_id": tenant_id,
        "balance": round(tenant.credit_balance, 2),
        "total_spent": round(total_spent, 2),
        "total_operations": len(tenant.usage_log),
        "ledger_chain_length": tenant.ledger.chain_length,
        "ledger_total_supply": round(tenant.ledger.total_supply(), 6),
    }, cost)


@app.get("/api/v1/billing/usage", tags=["Billing"])
async def billing_usage(
    limit: int = Query(50, ge=1, le=500),
    tenant_id: str = Depends(_authenticate),
):
    """Get usage history (most recent first)."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "billing.usage")  # Free

    # Reverse chronological
    recent = list(reversed(tenant.usage_log[-limit:]))

    # Aggregation
    by_operation: Dict[str, float] = {}
    for entry in tenant.usage_log:
        op = entry["operation"]
        by_operation[op] = by_operation.get(op, 0) + entry["credits"]

    return _ok({
        "recent": recent,
        "total_entries": len(tenant.usage_log),
        "by_operation": {k: round(v, 2) for k, v in sorted(by_operation.items(), key=lambda x: -x[1])},
    }, cost)


@app.get("/api/v1/billing/leaderboard", tags=["Billing"])
async def billing_leaderboard(tenant_id: str = Depends(_authenticate)):
    """Agent contribution leaderboard based on tasks completed and credits earned."""
    tenant = _get_tenant(tenant_id)
    cost = _charge(tenant, "billing.leaderboard")

    board = []
    for sheep in tenant.flock.sheep.values():
        agent_credits = tenant.ledger.credits_by_agent(sheep.sheep_id)
        total_value = sum(c.face_value for c in agent_credits)
        board.append({
            "agent_id": sheep.sheep_id,
            "name": sheep.name,
            "role": sheep.role.value,
            "tasks_completed": sheep.tasks_completed,
            "tasks_failed": sheep.tasks_failed,
            "coherence": round(sheep.coherence, 4),
            "credits_earned": round(total_value, 6),
            "tongue": sheep.tongue,
        })

    board.sort(key=lambda x: (-x["tasks_completed"], -x["credits_earned"]))

    return _ok({
        "leaderboard": board,
        "total_agents": len(board),
    }, cost)


# ============================================================================
#  CREDIT MINTING HELPER
# ============================================================================

def _mint_operation_credit(
    tenant: TenantState,
    agent_id: str,
    operation: str,
    cost: float,
) -> None:
    """Mint a MMCCL credit recording the operation on the blockchain ledger."""
    try:
        credit = mint_credit(
            agent_id=agent_id,
            model_name="saas-api",
            denomination="KO",
            context_payload=f"{operation}:{cost}:{time.time()}".encode(),
            personality_vector=[0.0] * 21,
            hamiltonian_d=0.1,
            hamiltonian_pd=0.05,
            entropy=3.5,
            active_layers=[1, 2, 5],
            governance_verdict="ALLOW",
            legibility=1.0,
            context_summary=f"SaaS API operation: {operation}",
            difficulty=1,
        )
        tenant.ledger.add_credits([credit])
    except Exception:
        # Credit minting failure is non-fatal
        pass


# ============================================================================
#  ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "code": exc.status_code,
        },
    )


# ============================================================================
#  HEALTH & ROOT
# ============================================================================

@app.get("/", tags=["System"])
async def root():
    return {
        "service": "SCBE-AETHERMOORE SaaS API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "tenants_active": len(_TENANTS),
        "uptime_seconds": int(time.time() - _start_time),
    }


_start_time = time.time()


# ============================================================================
#  STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    print("=" * 72)
    print("  SCBE-AETHERMOORE SaaS API v1.0.0")
    print("  Multi-tenant governed AI agent fleet management")
    print("=" * 72)
    print()
    print("  Fleet:     POST/GET /api/v1/fleet/...")
    print("  Tasks:     POST/GET /api/v1/tasks/...")
    print("  Knowledge: POST/GET /api/v1/knowledge/...")
    print("  Safety:    POST/GET /api/v1/safety/...")
    print("  Billing:   GET      /api/v1/billing/...")
    print()
    print("  Docs:      http://localhost:8000/docs")
    print("=" * 72)


# ============================================================================
#  MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
