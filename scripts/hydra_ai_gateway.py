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
_trainer = None
_training_enabled = os.environ.get("HYDRA_TRAINING", "1") == "1"


def _get_trainer():
    """Lazy-init the browser training bridge."""
    global _trainer
    if _trainer is None and _training_enabled:
        from hydra.browser_trainer import BrowserTrainer
        _trainer = BrowserTrainer()
        _trainer.start()
    return _trainer


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

    duration_ms = (time.time() - t0) * 1000

    # --- Training bridge: record browse + antivirus scan ---
    trainer = _get_trainer()
    if trainer and text:
        trainer.record_browse(
            url=req.url,
            selector=req.extract or "body",
            extracted_text=text,
            title=title or "",
            duration_ms=duration_ms,
        )
        trainer.auto_scan_and_record(text, url=req.url)

    return BrowseResponse(
        url=page.url,
        title=title,
        text=text,
        screenshot_b64=screenshot_b64,
        session=req.session,
        mode=browser._active_mode.value if browser._active_mode else "unknown",
        duration_ms=duration_ms,
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
        # Training bridge: record click
        trainer = _get_trainer()
        if trainer:
            trainer.record_click(page.url, req.selector, "success")
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
        # Training bridge: record type action
        trainer = _get_trainer()
        if trainer:
            trainer.record_type(page.url, req.selector, req.text)
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

    # Training bridge: record swarm consensus decision
    trainer = _get_trainer()
    if trainer and isinstance(result, dict):
        trainer.record_swarm_decision(
            task=req.task,
            agent_votes=result.get("votes", {}),
            final_decision=result.get("decision", "UNKNOWN"),
            action=result.get("action", ""),
            target=result.get("target", ""),
        )

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
            {
                "name": "training_stats",
                "description": "Get training data collection statistics (browse sessions, threats, swarm decisions).",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "load_model",
                "description": "Load a HuggingFace model for text generation. Models can serve as swarm agent brains.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_id": {"type": "string", "description": "HuggingFace model repo (e.g. 'mistralai/Mistral-7B-v0.1')"},
                        "task": {"type": "string", "default": "text-generation"},
                    },
                    "required": ["repo_id"],
                },
            },
            {
                "name": "generate",
                "description": "Generate text using a loaded HuggingFace model.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_id": {"type": "string", "description": "Model repo ID (must be loaded first)"},
                        "prompt": {"type": "string", "description": "Input prompt"},
                        "max_tokens": {"type": "integer", "default": 256},
                    },
                    "required": ["repo_id", "prompt"],
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
#  Training endpoints
# ---------------------------------------------------------------------------

@app.get("/training/stats", tags=["Training"])
async def training_stats():
    """Get training data collection statistics."""
    _check_auth()
    trainer = _get_trainer()
    if not trainer:
        return {"enabled": False, "message": "Training disabled. Set HYDRA_TRAINING=1 to enable."}
    return {"enabled": True, **trainer.get_stats()}


@app.post("/training/push", tags=["Training"])
async def training_push(token: Optional[str] = None):
    """Push collected training data to HuggingFace Hub.

    Requires HF_TOKEN env var or pass token in request body.
    """
    _check_auth()
    trainer = _get_trainer()
    if not trainer:
        return {"error": "Training disabled."}
    return await trainer.push_to_hf(token=token)


@app.post("/training/toggle", tags=["Training"])
async def training_toggle(enable: bool = True):
    """Enable or disable training data collection at runtime."""
    _check_auth()
    global _training_enabled, _trainer
    _training_enabled = enable
    if not enable and _trainer:
        _trainer.stop()
        _trainer = None
        return {"enabled": False, "message": "Training stopped and flushed."}
    elif enable and _trainer is None:
        _get_trainer()
        return {"enabled": True, "message": "Training started."}
    return {"enabled": _training_enabled, "message": "No change."}


# ---------------------------------------------------------------------------
#  HuggingFace model loader
# ---------------------------------------------------------------------------

_loaded_models: Dict[str, Any] = {}


@app.post("/models/load", tags=["Models"])
async def load_model(repo_id: str, task: str = "text-generation", revision: str = "main"):
    """Load an open-source model from HuggingFace Hub.

    The model becomes available as a swarm agent brain.
    Requires: pip install transformers torch
    """
    _check_auth()
    if repo_id in _loaded_models:
        return {"status": "already_loaded", "repo_id": repo_id}

    try:
        from transformers import pipeline as hf_pipeline
        pipe = hf_pipeline(task, model=repo_id, revision=revision, device_map="auto")
        _loaded_models[repo_id] = {"pipeline": pipe, "task": task, "loaded_at": time.time()}
        return {"status": "loaded", "repo_id": repo_id, "task": task}
    except ImportError:
        raise HTTPException(501, "transformers/torch not installed. Run: pip install transformers torch")
    except Exception as e:
        raise HTTPException(500, f"Failed to load model: {e}")


@app.get("/models/list", tags=["Models"])
async def list_models():
    """List currently loaded models."""
    _check_auth()
    return {
        "models": [
            {"repo_id": k, "task": v["task"], "loaded_at": v["loaded_at"]}
            for k, v in _loaded_models.items()
        ],
        "count": len(_loaded_models),
    }


@app.post("/models/generate", tags=["Models"])
async def model_generate(repo_id: str, prompt: str, max_tokens: int = 256):
    """Generate text using a loaded HuggingFace model.

    Load a model first via /models/load.
    """
    _check_auth()
    if repo_id not in _loaded_models:
        raise HTTPException(404, f"Model '{repo_id}' not loaded. Call /models/load first.")

    pipe = _loaded_models[repo_id]["pipeline"]
    try:
        result = pipe(prompt, max_new_tokens=max_tokens, do_sample=True, temperature=0.7)
        text = result[0]["generated_text"] if result else ""
        return {"repo_id": repo_id, "prompt": prompt, "generated": text}
    except Exception as e:
        raise HTTPException(500, f"Generation failed: {e}")


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
    global _browser, _trainer
    if _trainer:
        _trainer.stop()
        _trainer = None
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
    print(f"\n  Training endpoints:")
    print(f"    GET  /training/stats  — Training data statistics")
    print(f"    POST /training/push   — Push data to HuggingFace")
    print(f"    POST /training/toggle — Enable/disable training")
    print(f"\n  Model endpoints:")
    print(f"    POST /models/load     — Load HuggingFace model")
    print(f"    GET  /models/list     — List loaded models")
    print(f"    POST /models/generate — Generate with loaded model")
    print()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
