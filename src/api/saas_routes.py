from __future__ import annotations

import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from api.metering import (
    AUDIT_REPORT_GENERATIONS,
    GOVERNANCE_EVALUATIONS,
    WORKFLOW_EXECUTIONS,
    MeteringStore,
    metering_store,
)
from src.symphonic_cipher.scbe_aethermoore.flock_shepherd import (
    Flock,
    SheepRole,
    TrainingTrack,
)


saas_router = APIRouter(prefix="/saas")

VALID_API_KEYS = {
    "demo_key_12345": "demo_user",
    "pilot_key_67890": "pilot_customer",
}

PLAN_LIMITS: Dict[str, Dict[str, int]] = {
    "free": {"flocks": 1, "agents": 2, "monthly_governance": 500, "monthly_attestations": 100},
    "starter": {"flocks": 1, "agents": 8, "monthly_governance": 5000},
    "growth": {"flocks": 5, "agents": 40, "monthly_governance": 25000},
    "enterprise": {"flocks": 25, "agents": 250, "monthly_governance": 100000},
}

SAAS_TENANTS: Dict[str, Dict[str, Any]] = {}
SAAS_FLOCKS: Dict[str, Dict[str, Any]] = {}
_saas_metering_store: MeteringStore = metering_store


def reset_saas_state() -> None:
    SAAS_TENANTS.clear()
    SAAS_FLOCKS.clear()


def set_saas_metering_store(store: MeteringStore) -> None:
    global _saas_metering_store
    _saas_metering_store = store


async def verify_saas_api_key(x_api_key: str = Header(...)) -> str:
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(401, "Invalid API key")
    return VALID_API_KEYS[x_api_key]


class SaaSPlan(str, Enum):
    free = "free"
    starter = "starter"
    growth = "growth"
    enterprise = "enterprise"


class TenantCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    plan: SaaSPlan = Field(default=SaaSPlan.starter)
    governance_profile: str = Field(default="balanced", max_length=40)
    region: str = Field(default="us", max_length=20)


class FlockCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    mission: str = Field(default="", max_length=240)
    heartbeat_timeout_seconds: float = Field(default=60.0, ge=5.0, le=3600.0)
    freeze_after_missed_heartbeats: int = Field(default=2, ge=1, le=10)


class SheepCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    track: TrainingTrack = Field(default=TrainingTrack.SYSTEM)
    role: Optional[SheepRole] = Field(default=None)


class RefreshRequest(BaseModel):
    heartbeat_timeout_seconds: Optional[float] = Field(default=None, ge=5.0, le=3600.0)
    auto_redistribute: bool = Field(default=True)


class TaskCreateRequest(BaseModel):
    description: str = Field(..., min_length=3, max_length=1024)
    track: TrainingTrack = Field(default=TrainingTrack.SYSTEM)
    priority: int = Field(default=5, ge=1, le=10)
    auto_assign: bool = Field(default=True)
    sheep_id: Optional[str] = Field(default=None)


class TaskAssignRequest(BaseModel):
    sheep_id: Optional[str] = Field(default=None)


class TaskCompleteRequest(BaseModel):
    success: bool = Field(default=True)
    result: Optional[Dict[str, Any]] = Field(default=None)
    error_message: str = Field(default="", max_length=512)


class GovernanceCheckRequest(BaseModel):
    tenant_id: str = Field(..., min_length=4, max_length=40)
    flock_id: str = Field(..., min_length=4, max_length=40)
    action: str = Field(..., min_length=3, max_length=256)


def _tenant_id() -> str:
    return f"tenant_{uuid.uuid4().hex[:12]}"


def _flock_id() -> str:
    return f"flock_{uuid.uuid4().hex[:12]}"


def _tenant_view(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tenant_id": record["tenant_id"],
        "owner": record["owner"],
        "name": record["name"],
        "plan": record["plan"],
        "governance_profile": record["governance_profile"],
        "region": record["region"],
        "plan_limits": record["plan_limits"],
        "flock_count": sum(1 for flock in SAAS_FLOCKS.values() if flock["tenant_id"] == record["tenant_id"]),
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
    }


def _flock_view(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "flock_id": record["flock_id"],
        "tenant_id": record["tenant_id"],
        "owner": record["owner"],
        "name": record["name"],
        "mission": record["mission"],
        "heartbeat_timeout_seconds": record["heartbeat_timeout_seconds"],
        "freeze_after_missed_heartbeats": record["freeze_after_missed_heartbeats"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "dashboard": record["flock"].get_dashboard_data(),
    }


def _require_tenant(user: str, tenant_id: str) -> Dict[str, Any]:
    record = SAAS_TENANTS.get(tenant_id)
    if record is None or record["owner"] != user:
        raise HTTPException(404, "Tenant not found")
    return record


def _require_flock(user: str, flock_id: str) -> Dict[str, Any]:
    record = SAAS_FLOCKS.get(flock_id)
    if record is None or record["owner"] != user:
        raise HTTPException(404, "Flock not found")
    return record


@saas_router.post("/tenants", tags=["SaaS Tenants"])
async def create_tenant(request: TenantCreateRequest, user: str = Header(..., alias="x-api-key")):
    owner = await verify_saas_api_key(user)
    tenant_id = _tenant_id()
    now = int(time.time())
    SAAS_TENANTS[tenant_id] = {
        "tenant_id": tenant_id,
        "owner": owner,
        "name": request.name,
        "plan": request.plan.value,
        "governance_profile": request.governance_profile,
        "region": request.region,
        "plan_limits": PLAN_LIMITS[request.plan.value],
        "created_at": now,
        "updated_at": now,
    }
    return {"status": "created", "data": _tenant_view(SAAS_TENANTS[tenant_id])}


@saas_router.get("/tenants", tags=["SaaS Tenants"])
async def list_tenants(x_api_key: str = Header(...)):
    owner = await verify_saas_api_key(x_api_key)
    rows = [record for record in SAAS_TENANTS.values() if record["owner"] == owner]
    rows.sort(key=lambda value: value["created_at"], reverse=True)
    return {"status": "ok", "data": [_tenant_view(record) for record in rows]}


@saas_router.get("/tenants/{tenant_id}", tags=["SaaS Tenants"])
async def get_tenant(tenant_id: str, x_api_key: str = Header(...)):
    owner = await verify_saas_api_key(x_api_key)
    return {"status": "ok", "data": _tenant_view(_require_tenant(owner, tenant_id))}


@saas_router.post("/tenants/{tenant_id}/flocks", tags=["SaaS Flocks"])
async def create_flock(tenant_id: str, request: FlockCreateRequest, x_api_key: str = Header(...)):
    owner = await verify_saas_api_key(x_api_key)
    tenant = _require_tenant(owner, tenant_id)
    existing_count = sum(1 for flock in SAAS_FLOCKS.values() if flock["tenant_id"] == tenant_id)
    if existing_count >= tenant["plan_limits"]["flocks"]:
        raise HTTPException(400, "Plan flock limit reached")

    now = int(time.time())
    flock_id = _flock_id()
    flock = Flock(
        heartbeat_timeout=request.heartbeat_timeout_seconds,
        freeze_after_missed_heartbeats=request.freeze_after_missed_heartbeats,
    )
    SAAS_FLOCKS[flock_id] = {
        "flock_id": flock_id,
        "tenant_id": tenant_id,
        "owner": owner,
        "name": request.name,
        "mission": request.mission,
        "heartbeat_timeout_seconds": request.heartbeat_timeout_seconds,
        "freeze_after_missed_heartbeats": request.freeze_after_missed_heartbeats,
        "created_at": now,
        "updated_at": now,
        "flock": flock,
    }
    tenant["updated_at"] = now
    return {"status": "created", "data": _flock_view(SAAS_FLOCKS[flock_id])}


@saas_router.get("/tenants/{tenant_id}/flocks", tags=["SaaS Flocks"])
async def list_flocks(tenant_id: str, x_api_key: str = Header(...)):
    owner = await verify_saas_api_key(x_api_key)
    _require_tenant(owner, tenant_id)
    rows = [record for record in SAAS_FLOCKS.values() if record["tenant_id"] == tenant_id and record["owner"] == owner]
    rows.sort(key=lambda value: value["created_at"], reverse=True)
    return {"status": "ok", "data": [_flock_view(record) for record in rows]}


@saas_router.get("/flocks/{flock_id}", tags=["SaaS Flocks"])
async def get_flock(flock_id: str, x_api_key: str = Header(...)):
    owner = await verify_saas_api_key(x_api_key)
    return {"status": "ok", "data": _flock_view(_require_flock(owner, flock_id))}


@saas_router.post("/flocks/{flock_id}/sheep", tags=["SaaS Flocks"])
async def spawn_sheep(flock_id: str, request: SheepCreateRequest, x_api_key: str = Header(...)):
    owner = await verify_saas_api_key(x_api_key)
    record = _require_flock(owner, flock_id)
    tenant = _require_tenant(owner, record["tenant_id"])
    if len(record["flock"].sheep) >= tenant["plan_limits"]["agents"]:
        raise HTTPException(400, "Plan agent limit reached")

    sheep = record["flock"].spawn(request.name, request.track, request.role)
    record["updated_at"] = int(time.time())
    return {
        "status": "created",
        "data": {
            "sheep_id": sheep.sheep_id,
            "name": sheep.name,
            "role": sheep.role.value,
            "track": sheep.track.value,
            "state": sheep.state.value,
            "tongue": sheep.tongue,
        },
    }


@saas_router.post("/flocks/{flock_id}/heartbeat/{sheep_id}", tags=["SaaS Flocks"])
async def heartbeat_sheep(flock_id: str, sheep_id: str, x_api_key: str = Header(...)):
    owner = await verify_saas_api_key(x_api_key)
    record = _require_flock(owner, flock_id)
    if not record["flock"].record_heartbeat(sheep_id):
        raise HTTPException(404, "Sheep not found")
    record["updated_at"] = int(time.time())
    return {"status": "ok", "data": _flock_view(record)}


@saas_router.post("/flocks/{flock_id}/refresh", tags=["SaaS Flocks"])
async def refresh_flock(flock_id: str, request: RefreshRequest, x_api_key: str = Header(...)):
    owner = await verify_saas_api_key(x_api_key)
    record = _require_flock(owner, flock_id)
    summary = record["flock"].refresh(
        heartbeat_timeout=request.heartbeat_timeout_seconds,
        auto_redistribute=request.auto_redistribute,
    )
    record["updated_at"] = int(time.time())
    return {"status": "ok", "data": {"refresh": summary, "flock": _flock_view(record)}}


@saas_router.post("/flocks/{flock_id}/tasks", tags=["SaaS Tasks"])
async def create_task(flock_id: str, request: TaskCreateRequest, x_api_key: str = Header(...)):
    owner = await verify_saas_api_key(x_api_key)
    record = _require_flock(owner, flock_id)
    task = record["flock"].add_task(request.description, request.track, request.priority)
    if request.auto_assign:
        record["flock"].assign_task(task.task_id, request.sheep_id)
    record["updated_at"] = int(time.time())
    return {"status": "created", "data": _flock_view(record)}


@saas_router.post("/flocks/{flock_id}/tasks/{task_id}/assign", tags=["SaaS Tasks"])
async def assign_task(flock_id: str, task_id: str, request: TaskAssignRequest, x_api_key: str = Header(...)):
    owner = await verify_saas_api_key(x_api_key)
    record = _require_flock(owner, flock_id)
    if not record["flock"].assign_task(task_id, request.sheep_id):
        raise HTTPException(400, "Task assignment failed")
    record["updated_at"] = int(time.time())
    return {"status": "ok", "data": _flock_view(record)}


@saas_router.post("/flocks/{flock_id}/tasks/{task_id}/complete", tags=["SaaS Tasks"])
async def complete_task(flock_id: str, task_id: str, request: TaskCompleteRequest, x_api_key: str = Header(...)):
    owner = await verify_saas_api_key(x_api_key)
    record = _require_flock(owner, flock_id)
    if not record["flock"].mark_task_complete(
        task_id,
        success=request.success,
        result=request.result,
        error_message=request.error_message,
    ):
        raise HTTPException(400, "Task completion failed")
    _saas_metering_store.increment_metric(record["tenant_id"], WORKFLOW_EXECUTIONS)
    record["updated_at"] = int(time.time())
    return {"status": "ok", "data": _flock_view(record)}


@saas_router.post("/governance/check", tags=["SaaS Governance"])
async def governance_check(request: GovernanceCheckRequest, x_api_key: str = Header(...)):
    owner = await verify_saas_api_key(x_api_key)
    _require_tenant(owner, request.tenant_id)
    record = _require_flock(owner, request.flock_id)
    if record["tenant_id"] != request.tenant_id:
        raise HTTPException(404, "Flock not found for tenant")

    decision = record["flock"].vote_on_action(request.action)
    _saas_metering_store.increment_metric(record["tenant_id"], GOVERNANCE_EVALUATIONS)
    record["updated_at"] = int(time.time())
    return {"status": "ok", "data": decision, "flock": _flock_view(record)}


@saas_router.get("/tenants/{tenant_id}/audit-report", tags=["SaaS Revenue"])
async def audit_report(tenant_id: str, x_api_key: str = Header(...)):
    owner = await verify_saas_api_key(x_api_key)
    tenant = _require_tenant(owner, tenant_id)
    flocks = [record for record in SAAS_FLOCKS.values() if record["tenant_id"] == tenant_id and record["owner"] == owner]
    totals = {
        "flocks": len(flocks),
        "agents": sum(len(record["flock"].sheep) for record in flocks),
        "tasks": sum(len(record["flock"].tasks) for record in flocks),
        "completed_tasks": sum(
            sum(1 for task in record["flock"].tasks.values() if task.status == "completed")
            for record in flocks
        ),
        "failed_tasks": sum(
            sum(1 for task in record["flock"].tasks.values() if task.status == "failed")
            for record in flocks
        ),
        "events": sum(len(record["flock"].event_log) for record in flocks),
    }
    _saas_metering_store.increment_metric(tenant_id, AUDIT_REPORT_GENERATIONS)
    tenant["updated_at"] = int(time.time())
    return {
        "status": "ok",
        "data": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "tenant": _tenant_view(tenant),
            "totals": totals,
        },
    }


@saas_router.get("/tenants/{tenant_id}/usage", tags=["SaaS Revenue"])
async def usage_report(
    tenant_id: str,
    year: Optional[int] = Query(default=None, ge=2024, le=2100),
    month: Optional[int] = Query(default=None, ge=1, le=12),
    x_api_key: str = Header(...),
):
    owner = await verify_saas_api_key(x_api_key)
    tenant = _require_tenant(owner, tenant_id)
    now = datetime.utcnow()
    target_year = year or now.year
    target_month = month or now.month
    rows = _saas_metering_store.export_monthly_usage(target_year, target_month, tenant_id=tenant_id)
    totals = {
        GOVERNANCE_EVALUATIONS: 0,
        WORKFLOW_EXECUTIONS: 0,
        AUDIT_REPORT_GENERATIONS: 0,
    }
    serialized_rows: List[Dict[str, Any]] = []
    for row in rows:
        serialized_rows.append(row.__dict__)
        totals[row.metric_name] = totals.get(row.metric_name, 0) + row.count

    return {
        "status": "ok",
        "data": {
            "tenant": _tenant_view(tenant),
            "month": f"{target_year:04d}-{target_month:02d}",
            "rows": serialized_rows,
            "totals": totals,
        },
    }
