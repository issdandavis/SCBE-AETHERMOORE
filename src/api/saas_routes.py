"""Minimal SaaS control-plane routes required by the API app surface."""

from __future__ import annotations

from fastapi import APIRouter


saas_router = APIRouter(prefix="/saas", tags=["SaaS"])


@saas_router.get("/health")
def saas_health() -> dict[str, object]:
    return {"status": "ok", "plane": "saas"}
