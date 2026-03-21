from __future__ import annotations

import json
from functools import lru_cache

import httpx
from fastapi import APIRouter, Header, HTTPException, Request

from .service import GitHubAppService

router = APIRouter(prefix="/v1/github-app", tags=["GitHub App"])


@lru_cache(maxsize=1)
def get_github_app_service() -> GitHubAppService:
    return GitHubAppService.from_env()


@router.get("/health")
async def github_app_health() -> dict:
    return get_github_app_service().health_status()


@router.post("/webhook")
async def github_app_webhook(
    request: Request,
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: str | None = Header(None, alias="X-GitHub-Delivery"),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
) -> dict:
    service = get_github_app_service()
    if not service.is_configured:
        raise HTTPException(status_code=503, detail="GitHub App is not configured")
    if not x_github_event:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Event header")

    payload_body = await request.body()
    if not service.verify_signature(payload_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(payload_body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}") from exc

    try:
        return await service.handle_event(
            event=x_github_event,
            payload=payload,
            delivery_id=x_github_delivery,
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"GitHub API request failed: {detail}") from exc
