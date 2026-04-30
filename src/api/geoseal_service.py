"""Lightweight GeoSeal service app for the CLI shell.

This app is intentionally narrower than ``src.api.main``.  It gives the local
``geoseal service`` command a fast, reliable runtime bridge without importing
the full SaaS/billing/search API stack during startup.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import Body, Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

GEOSEAL_CLI_COMMANDS = frozenset(
    {
        "code-packet",
        "explain-route",
        "backend-registry",
        "agent-harness",
        "history",
        "replay",
        "testing-cli",
        "project-scaffold",
        "code-roundtrip",
    }
)

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


class ToolBridgeRequest(BaseModel):
    """Inline agent goal for SCBE-native CLI / MCP bridge hints."""

    goal: str = Field(..., min_length=1, max_length=12000)


class AgentHarnessRequest(BaseModel):
    """Model-neutral harness manifest request."""

    goal: str = Field(default="", max_length=12000)
    language: str = Field(default="python", max_length=64)
    permission_mode: str = Field(default="observe", max_length=64)


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
                "harness_tool_bridge": True,
                "agent_harness_manifest": True,
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
                    "/v1/harness/tool-bridge",
                    "/v1/harness/agent-harness",
                    "/v1/geoseal/code-packet",
                    "/v1/geoseal/explain-route",
                    "/v1/geoseal/backend-registry",
                    "/v1/geoseal/agent-harness",
                    "/v1/geoseal/history",
                    "/v1/geoseal/replay",
                    "/v1/geoseal/testing-cli",
                    "/v1/geoseal/project-scaffold",
                    "/v1/geoseal/code-roundtrip",
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
async def runtime_inspect(
    request: RuntimeInspectRequest, user: str = Depends(verify_api_key)
) -> dict[str, Any]:
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
async def runtime_run_route(
    request: RuntimeRunRouteRequest, user: str = Depends(verify_api_key)
) -> dict[str, Any]:
    _ = user
    from src.geoseal_cli import (
        _build_execution_shell_payload,
        _execute_execution_shell_payload,
    )

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
async def runtime_portal_box(
    request: RuntimePortalBoxRequest, user: str = Depends(verify_api_key)
) -> dict[str, Any]:
    _ = user
    from src.geoseal_cli import _build_portal_box_payload

    return {
        "status": "ok",
        "data": _build_portal_box_payload(
            language=request.language,
            content=request.content,
            source_name=request.source_name,
            include_extended=request.include_extended,
        ),
    }


@app.post("/runtime/stream-wheel", tags=["Runtime"])
async def runtime_stream_wheel(
    request: RuntimePortalBoxRequest, user: str = Depends(verify_api_key)
) -> dict[str, Any]:
    _ = user
    from src.geoseal_cli import _build_stream_wheel_payload

    return {
        "status": "ok",
        "data": _build_stream_wheel_payload(
            language=request.language,
            content=request.content,
            source_name=request.source_name,
            include_extended=request.include_extended,
        ),
    }


@app.post("/v1/geoseal/{command}", tags=["GeoSeal CLI"])
async def geoseal_cli_http(
    command: str, body: dict[str, Any] = Body(default_factory=dict)
) -> dict[str, Any]:
    """Expose curated GeoSeal CLI subcommands over HTTP for ``bin/geoseal.cjs`` routing."""

    if command not in GEOSEAL_CLI_COMMANDS:
        raise HTTPException(
            status_code=404, detail=f"Unknown GeoSeal command: {command}"
        )
    from src.api.geoseal_cli_bridge import dispatch_geoseal_command

    try:
        result = dispatch_geoseal_command(command, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    exit_code = int(result.get("exit_code") or 0)
    return {"status": "ok" if exit_code == 0 else "error", **result}


@app.post("/v1/harness/tool-bridge", tags=["Harness"])
async def harness_tool_bridge(request: ToolBridgeRequest) -> dict[str, Any]:
    from src.coding_spine.agent_tool_bridge import build_agent_tool_bridge_v1

    return {
        "status": "ok",
        "data": build_agent_tool_bridge_v1(inline_goal=request.goal),
    }


@app.post("/v1/harness/agent-harness", tags=["Harness"])
async def harness_agent_harness(request: AgentHarnessRequest) -> dict[str, Any]:
    from src.coding_spine.agent_tool_bridge import build_agent_harness_manifest_v1

    return {
        "status": "ok",
        "data": build_agent_harness_manifest_v1(
            inline_goal=request.goal,
            preferred_language=request.language,
            permission_mode=request.permission_mode,
        ),
    }


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
        ),
    }


@app.post("/v1/polly/stream-wheel", tags=["Polly Pad"])
async def polly_public_stream_wheel(request: RuntimePortalBoxRequest) -> dict[str, Any]:
    from src.geoseal_cli import _build_stream_wheel_payload

    return {
        "status": "ok",
        "data": _build_stream_wheel_payload(
            language=request.language,
            content=request.content,
            source_name=request.source_name,
            include_extended=request.include_extended,
        ),
    }


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
        "coding_spine": {
            "tongue": resolution.get("runtime_packet", {}).get("route_tongue", "KO")
        },
        "deck": deck,
    }
