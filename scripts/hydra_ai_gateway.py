#!/usr/bin/env python3
"""
HYDRA AI Tool-Use Gateway
===========================

Universal REST API that any AI service (Grok, GPT, Claude, Gemini, etc.)
can call as a tool/action/function. Exposes HYDRA browser capabilities via:

1. **OpenAPI 3.1** — GPT Actions, Grok tools, any OpenAPI-compatible AI
2. **MCP-over-HTTP** (SSE) — Claude Desktop / Claude Code
3. **Plain REST** — curl, n8n, Zapier, any HTTP client

The gateway self-describes its tools at:
    GET  /openapi.json          — OpenAPI 3.1 spec (GPT Actions format)
    GET  /tools                 — Tool list in Claude/OpenAI function-calling format
    GET  /.well-known/ai-plugin.json  — ChatGPT plugin manifest

Run:
    python scripts/hydra_ai_gateway.py                      # port 8002
    python scripts/hydra_ai_gateway.py --port 9000          # custom port
    python scripts/hydra_ai_gateway.py --mode headed         # show browser
    SCBE_API_KEY=secret python scripts/hydra_ai_gateway.py  # with auth
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

# Ensure repo root on path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
#  App
# ---------------------------------------------------------------------------

GATEWAY_VERSION = "1.0.0"
GATEWAY_NAME = "HYDRA Browser Gateway"
GATEWAY_DESC = (
    "Governed headless browser automation for AI agents. "
    "Scrape, navigate, click, type, screenshot — with SCBE safety governance. "
    "6-agent Sacred Tongue swarm with Byzantine consensus."
)

app = FastAPI(
    title=GATEWAY_NAME,
    version=GATEWAY_VERSION,
    description=GATEWAY_DESC,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
#  Auth (optional — set SCBE_API_KEY to enable)
# ---------------------------------------------------------------------------

_API_KEY = os.environ.get("SCBE_API_KEY")


def _check_auth(authorization: Optional[str] = Header(None)):
    if not _API_KEY:
        return  # Auth disabled
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")
    token = authorization.replace("Bearer ", "").strip()
    if token != _API_KEY:
        raise HTTPException(403, "Invalid API key")


# ---------------------------------------------------------------------------
#  Lazy browser singleton (dual-view)
# ---------------------------------------------------------------------------

_browser = None
_browser_mode = "headless"


async def _get_browser():
    global _browser
    if _browser is None:
        from hydra.dual_view import DualViewBrowser, ViewConfig, ViewMode
        mode = ViewMode.HEADED if _browser_mode == "headed" else ViewMode.HEADLESS
        _browser = DualViewBrowser(ViewConfig(mode=mode))
        await _browser.launch()
    return _browser


# ---------------------------------------------------------------------------
#  Request / Response models
# ---------------------------------------------------------------------------

class BrowseRequest(BaseModel):
    url: str = Field(..., description="URL to navigate to")
    extract: Optional[str] = Field("body", description="CSS selector to extract text from")
    screenshot: bool = Field(False, description="Take a screenshot")
    session: str = Field("default", description="Session name for cookie isolation")


class BrowseResponse(BaseModel):
    url: str
    title: Optional[str] = None
    text: Optional[str] = None
    screenshot_b64: Optional[str] = None
    session: str
    mode: str
    duration_ms: float


class ClickRequest(BaseModel):
    selector: str = Field(..., description="CSS selector to click")
    session: str = Field("default", description="Session name")


class TypeRequest(BaseModel):
    selector: str = Field(..., description="CSS selector to type into")
    text: str = Field(..., description="Text to type")
    session: str = Field("default", description="Session name")


class SwarmRequest(BaseModel):
    task: str = Field(..., description="Natural language task for the 6-agent swarm")
    dry_run: bool = Field(True, description="If true, no real browser actions executed")


class ActionResponse(BaseModel):
    success: bool
    action: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    session: str = "default"
    duration_ms: float = 0.0


# ---------------------------------------------------------------------------
#  Core endpoints — what AI services call
# ---------------------------------------------------------------------------

@app.post("/browse", response_model=BrowseResponse, tags=["Browser"])
async def browse(req: BrowseRequest):
    """Navigate to a URL, extract text, optionally screenshot.

    This is the primary tool for AI agents to read web pages.
    """
    _check_auth()
    t0 = time.time()
    browser = await _get_browser()
    page = await browser.new_page(req.session)

    try:
        await page.goto(req.url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        raise HTTPException(502, f"Navigation failed: {e}")

    title = await page.title()
    text = None
    if req.extract:
        try:
            el = page.locator(req.extract).first
            text = await el.inner_text(timeout=5000)
            if len(text) > 50000:
                text = text[:50000] + "...[truncated]"
        except Exception:
            text = None

    screenshot_b64 = None
    if req.screenshot:
        shot = await page.screenshot(type="png")
        import base64
        screenshot_b64 = base64.b64encode(shot).decode()

    return BrowseResponse(
        url=page.url,
        title=title,
        text=text,
        screenshot_b64=screenshot_b64,
        session=req.session,
        mode=browser._active_mode.value if browser._active_mode else "unknown",
        duration_ms=(time.time() - t0) * 1000,
    )


@app.post("/click", response_model=ActionResponse, tags=["Browser"])
async def click(req: ClickRequest):
    """Click an element on the current page."""
    _check_auth()
    t0 = time.time()
    browser = await _get_browser()
    page = browser._pages.get(req.session)
    if not page:
        raise HTTPException(400, f"No active page in session '{req.session}'. Call /browse first.")

    try:
        await page.click(req.selector, timeout=10000)
        return ActionResponse(success=True, action="click", data={"selector": req.selector},
                              session=req.session, duration_ms=(time.time() - t0) * 1000)
    except Exception as e:
        return ActionResponse(success=False, action="click", error=str(e),
                              session=req.session, duration_ms=(time.time() - t0) * 1000)


@app.post("/type", response_model=ActionResponse, tags=["Browser"])
async def type_text(req: TypeRequest):
    """Type text into an element on the current page."""
    _check_auth()
    t0 = time.time()
    browser = await _get_browser()
    page = browser._pages.get(req.session)
    if not page:
        raise HTTPException(400, f"No active page in session '{req.session}'. Call /browse first.")

    try:
        await page.fill(req.selector, req.text)
        return ActionResponse(success=True, action="type",
                              data={"selector": req.selector, "length": len(req.text)},
                              session=req.session, duration_ms=(time.time() - t0) * 1000)
    except Exception as e:
        return ActionResponse(success=False, action="type", error=str(e),
                              session=req.session, duration_ms=(time.time() - t0) * 1000)


@app.post("/screenshot", response_model=ActionResponse, tags=["Browser"])
async def screenshot(session: str = "default"):
    """Take a screenshot of the current page."""
    _check_auth()
    t0 = time.time()
    browser = await _get_browser()
    page = browser._pages.get(session)
    if not page:
        raise HTTPException(400, f"No active page in session '{session}'.")

    import base64
    shot = await page.screenshot(type="png")
    return ActionResponse(
        success=True, action="screenshot",
        data={"b64": base64.b64encode(shot).decode(), "url": page.url},
        session=session, duration_ms=(time.time() - t0) * 1000,
    )


@app.post("/swarm", tags=["Swarm"])
async def swarm_task(req: SwarmRequest):
    """Execute a task via the 6-agent Sacred Tongue swarm.

    The swarm uses Byzantine consensus (4/6 agents must agree)
    for sensitive operations like clicking or form submission.
    """
    _check_auth()
    from hydra.swarm_browser import SwarmBrowser
    swarm = SwarmBrowser(dry_run=req.dry_run)
    await swarm.launch()
    result = await swarm.execute_task(req.task)
    await swarm.shutdown()
    return result


@app.get("/view/{session}", tags=["Browser"])
async def get_view(session: str = "default"):
    """Get a live view (screenshot + metadata) of a session.

    Useful for AI agents to "see" what the browser shows.
    """
    _check_auth()
    browser = await _get_browser()
    try:
        snapshot = await browser.capture_view(session)
        return {
            "url": snapshot.url,
            "title": snapshot.title,
            "mode": snapshot.mode,
            "viewport": snapshot.viewport,
            "screenshot_b64": snapshot.screenshot_b64,
        }
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/switch-mode", tags=["Browser"])
async def switch_mode(mode: str = "headless"):
    """Switch between headless and headed mode at runtime.

    Preserves session state (cookies, storage) across the switch.
    """
    _check_auth()
    from hydra.dual_view import ViewMode
    browser = await _get_browser()
    target = ViewMode.HEADED if mode == "headed" else ViewMode.HEADLESS
    await browser.switch_mode(target)
    return {"mode": browser._active_mode.value, "status": "switched"}


# ---------------------------------------------------------------------------
#  AI discovery endpoints
# ---------------------------------------------------------------------------

@app.get("/tools", tags=["Discovery"])
async def list_tools():
    """List available tools in Claude/OpenAI function-calling format.

    AI services use this to discover what they can do.
    """
    return {
        "tools": [
            {
                "name": "browse",
                "description": "Navigate to a URL and extract text content. Returns page title, text from a CSS selector, and optional screenshot.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to navigate to"},
                        "extract": {"type": "string", "description": "CSS selector to extract text (default: body)", "default": "body"},
                        "screenshot": {"type": "boolean", "description": "Take a screenshot", "default": False},
                        "session": {"type": "string", "description": "Session name for cookie isolation", "default": "default"},
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "click",
                "description": "Click an element on the current page using a CSS selector.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector to click"},
                        "session": {"type": "string", "default": "default"},
                    },
                    "required": ["selector"],
                },
            },
            {
                "name": "type",
                "description": "Type text into a form field on the current page.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector of the input field"},
                        "text": {"type": "string", "description": "Text to type"},
                        "session": {"type": "string", "default": "default"},
                    },
                    "required": ["selector", "text"],
                },
            },
            {
                "name": "screenshot",
                "description": "Take a screenshot of the current page. Returns base64 PNG.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session": {"type": "string", "default": "default"},
                    },
                },
            },
            {
                "name": "swarm",
                "description": "Execute a complex web task via the 6-agent Sacred Tongue swarm. Uses Byzantine consensus for safety.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Natural language task description"},
                        "dry_run": {"type": "boolean", "default": True},
                    },
                    "required": ["task"],
                },
            },
            {
                "name": "view",
                "description": "Get a live screenshot and metadata of a browser session.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session": {"type": "string", "default": "default"},
                    },
                },
            },
        ],
        "service": GATEWAY_NAME,
        "version": GATEWAY_VERSION,
    }


@app.get("/.well-known/ai-plugin.json", tags=["Discovery"])
async def ai_plugin_manifest(request: Request):
    """ChatGPT / GPT Actions plugin manifest.

    OpenAI-compatible AIs discover this endpoint to learn how to call us.
    """
    base = str(request.base_url).rstrip("/")
    return {
        "schema_version": "v1",
        "name_for_human": "HYDRA Browser",
        "name_for_model": "hydra_browser",
        "description_for_human": "Governed headless browser automation with AI safety governance.",
        "description_for_model": (
            "Use this tool to browse the web, scrape pages, click elements, type into forms, "
            "and take screenshots. All actions go through SCBE safety governance with "
            "ALLOW/DENY/QUARANTINE/ESCALATE decisions. For complex multi-step tasks, "
            "use the /swarm endpoint which coordinates 6 specialized AI agents."
        ),
        "auth": {"type": "service_http", "authorization_type": "bearer"} if _API_KEY else {"type": "none"},
        "api": {
            "type": "openapi",
            "url": f"{base}/openapi.json",
        },
        "logo_url": f"{base}/logo.png",
        "contact_email": "issdandavis@gmail.com",
        "legal_info_url": "https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/LICENSE",
    }


# ---------------------------------------------------------------------------
#  Health + status
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Status"])
async def health():
    return {
        "status": "ok",
        "service": GATEWAY_NAME,
        "version": GATEWAY_VERSION,
        "browser_launched": _browser is not None and _browser._launched,
        "mode": _browser._active_mode.value if _browser and _browser._active_mode else "not_launched",
    }


@app.get("/status", tags=["Status"])
async def status():
    """Detailed status including browser state and sessions."""
    if _browser and _browser._launched:
        return _browser.get_status()
    return {"launched": False, "message": "Browser not yet started. Call /browse to auto-launch."}


# ---------------------------------------------------------------------------
#  Shutdown hook
# ---------------------------------------------------------------------------

from contextlib import asynccontextmanager


@asynccontextmanager
async def _lifespan(application: FastAPI):
    yield
    global _browser
    if _browser:
        await _browser.close()
        _browser = None


app.router.lifespan_context = _lifespan


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="HYDRA AI Tool-Use Gateway")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--mode", choices=["headless", "headed"], default="headless",
                        help="Browser view mode")
    args = parser.parse_args()

    global _browser_mode
    _browser_mode = args.mode

    import uvicorn
    print(f"\n{'='*60}")
    print(f"  HYDRA AI Tool-Use Gateway")
    print(f"  http://{args.host}:{args.port}")
    print(f"  Mode: {args.mode}")
    print(f"  Auth: {'ENABLED' if _API_KEY else 'DISABLED (set SCBE_API_KEY to enable)'}")
    print(f"{'='*60}")
    print(f"\n  AI discovery endpoints:")
    print(f"    GET  /tools                       — Tool definitions (function-calling)")
    print(f"    GET  /openapi.json                — OpenAPI 3.1 spec (GPT Actions)")
    print(f"    GET  /.well-known/ai-plugin.json  — ChatGPT plugin manifest")
    print(f"    GET  /docs                        — Interactive Swagger UI")
    print(f"\n  Browser endpoints:")
    print(f"    POST /browse    — Navigate + extract")
    print(f"    POST /click     — Click element")
    print(f"    POST /type      — Type text")
    print(f"    POST /screenshot — Capture view")
    print(f"    POST /swarm     — Multi-agent task")
    print(f"    POST /switch-mode — Toggle headless/headed")
    print()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
