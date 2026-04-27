"""Lightweight GeoSeal service app for the CLI shell.

This app is intentionally narrower than ``src.api.main``.  It gives the local
``geoseal service`` command a fast, reliable runtime bridge without importing
the full SaaS/billing/search API stack during startup.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

STARTED_AT = time.time()
DEMO_API_KEY = "demo_key_12345"

app = FastAPI(
    title="GeoSeal CLI Service",
    version="1.0.0",
    description="Fast local GeoSeal CLI/API bridge",
    docs_url="/docs",
    redoc_url="/redoc",
)


class RuntimeInspectRequest(BaseModel):
    language: str = Field(..., min_length=1, max_length=64)
    content: str = Field(..., min_length=1, max_length=64000)
    source_name: str = Field(default="<memory>", max_length=512)


class RuntimeSystemCardsRequest(RuntimeInspectRequest):
    include_extended: bool = False
    deck_size: int = Field(default=10, ge=4, le=32)


class RuntimeRunRouteRequest(RuntimeSystemCardsRequest):
    branch_width: int = Field(default=1, ge=1, le=4)
    timeout: float = Field(default=10.0, gt=0.0, le=60.0)
    tongue: Optional[str] = Field(default=None, max_length=8)


class RuntimePortalBoxRequest(RuntimeSystemCardsRequest):
    branch_width: int = Field(default=1, ge=1, le=4)


class PollyChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=64000)
    tentacle: str = Field(default="local", max_length=64)
    mode: str = Field(default="local-polypad", max_length=64)


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    if x_api_key != DEMO_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return "demo"


def _runtime_inspect_packet(payload: dict[str, Any]) -> dict[str, Any]:
    from src.geoseal_cli import inspect_runtime_packet

    return inspect_runtime_packet(payload)


def _build_runtime_deck_payload(
    *,
    language: str,
    content: str,
    source_name: str,
    include_extended: bool,
    deck_size: int,
) -> dict[str, Any]:
    from src.geoseal_cli import build_system_deck, resolve_source_to_operation_panel

    resolution = resolve_source_to_operation_panel(
        content,
        language=language,
        source_name=source_name,
        include_extended=include_extended,
    )
    deck = build_system_deck(
        resolution,
        source_text=content,
        source_name=source_name,
        max_cards=deck_size,
    )
    return {"resolution": resolution, "deck": deck}


@app.get("/health", tags=["System"])
@app.get("/v1/health", tags=["System"])
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "version": "geoseal-service-v1",
        "uptime_seconds": int(time.time() - STARTED_AT),
    }


@app.get("/v1/spaceport/status", tags=["Polly Pad"])
async def spaceport_status() -> dict[str, Any]:
    return {
        "status": "ok",
        "data": {
            "online": True,
            "assistant": "polly-local-control-plane",
            "service": "geoseal-cli-service",
            "lanes": {
                "public_portal_box": True,
                "public_stream_wheel": True,
                "system_cards": True,
                "portal_box": True,
                "stream_wheel": True,
                "run_route": True,
            },
            "auth_split": {
                "public_read": [
                    "/v1/spaceport/status",
                    "/v1/polly/portal-box",
                    "/v1/polly/stream-wheel",
                ],
                "authenticated_runtime": [
                    "/runtime/inspect",
                    "/runtime/portal-box",
                    "/runtime/stream-wheel",
                    "/runtime/run-route",
                ],
            },
        },
    }


@app.post("/runtime/inspect", tags=["Runtime"])
async def runtime_inspect(request: RuntimeInspectRequest, user: str = Depends(verify_api_key)) -> dict[str, Any]:
    _ = user
    return {
        "status": "ok",
        "data": _runtime_inspect_packet(
            {
                "language": request.language,
                "content": request.content,
                "source_name": request.source_name,
            }
        ),
    }


@app.post("/runtime/system-cards", tags=["Runtime"])
async def runtime_system_cards(
    request: RuntimeSystemCardsRequest, user: str = Depends(verify_api_key)
) -> dict[str, Any]:
    _ = user
    return {
        "status": "ok",
        "data": _build_runtime_deck_payload(
            language=request.language,
            content=request.content,
            source_name=request.source_name,
            include_extended=request.include_extended,
            deck_size=request.deck_size,
        ),
    }


@app.post("/runtime/run-route", tags=["Runtime"])
async def runtime_run_route(request: RuntimeRunRouteRequest, user: str = Depends(verify_api_key)) -> dict[str, Any]:
    _ = user
    from src.geoseal_cli import _build_execution_shell_payload, _execute_execution_shell_payload

    shell_payload = _build_execution_shell_payload(
        language=request.language,
        content=request.content,
        source_name=request.source_name,
        include_extended=request.include_extended,
        deck_size=request.deck_size,
        branch_width=request.branch_width,
    )
    return {
        "status": "ok",
        "data": _execute_execution_shell_payload(
            shell_payload,
            timeout=request.timeout,
            tongue=request.tongue,
        ),
    }


@app.post("/runtime/portal-box", tags=["Runtime"])
async def runtime_portal_box(request: RuntimePortalBoxRequest, user: str = Depends(verify_api_key)) -> dict[str, Any]:
    _ = user
    from src.geoseal_cli import _build_portal_box_payload

    return {
        "status": "ok",
        "data": _build_portal_box_payload(
            language=request.language,
            content=request.content,
            source_name=request.source_name,
            include_extended=request.include_extended,
            deck_size=request.deck_size,
            branch_width=request.branch_width,
        ),
    }


@app.post("/runtime/stream-wheel", tags=["Runtime"])
async def runtime_stream_wheel(request: RuntimePortalBoxRequest, user: str = Depends(verify_api_key)) -> dict[str, Any]:
    _ = user
    from src.geoseal_cli import _build_portal_box_payload, _build_stream_wheel_payload

    portal_payload = _build_portal_box_payload(
        language=request.language,
        content=request.content,
        source_name=request.source_name,
        include_extended=request.include_extended,
        deck_size=request.deck_size,
        branch_width=request.branch_width,
    )
    return {"status": "ok", "data": _build_stream_wheel_payload(portal_payload)}


@app.post("/v1/polly/portal-box", tags=["Polly Pad"])
async def polly_public_portal_box(request: RuntimePortalBoxRequest) -> dict[str, Any]:
    from src.geoseal_cli import _build_portal_box_payload

    return {
        "status": "ok",
        "data": _build_portal_box_payload(
            language=request.language,
            content=request.content,
            source_name=request.source_name,
            include_extended=request.include_extended,
            deck_size=request.deck_size,
            branch_width=request.branch_width,
        ),
    }


@app.post("/v1/polly/stream-wheel", tags=["Polly Pad"])
async def polly_public_stream_wheel(request: RuntimePortalBoxRequest) -> dict[str, Any]:
    from src.geoseal_cli import _build_portal_box_payload, _build_stream_wheel_payload

    portal_payload = _build_portal_box_payload(
        language=request.language,
        content=request.content,
        source_name=request.source_name,
        include_extended=request.include_extended,
        deck_size=request.deck_size,
        branch_width=request.branch_width,
    )
    return {"status": "ok", "data": _build_stream_wheel_payload(portal_payload)}


@app.post("/v1/chat", tags=["Polly Pad"])
async def polly_chat(request: PollyChatRequest) -> dict[str, Any]:
    from src.geoseal_cli import build_system_deck, resolve_source_to_operation_panel

    resolution = resolve_source_to_operation_panel(
        request.message,
        language="python",
        source_name="chat.message",
        include_extended=False,
    )
    deck = build_system_deck(
        resolution,
        source_text=request.message,
        source_name="chat.message",
        max_cards=10,
    )
    return {
        "status": "ok",
        "model": "polly-local-control-plane",
        "message": "local GeoSeal route resolved",
        "coding_spine": {"tongue": resolution.get("runtime_packet", {}).get("route_tongue", "KO")},
        "deck": deck,
    }
