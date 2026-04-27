"""
HTTP API for browser tools. Exposes all tools from browser_tools.py
as REST endpoints. Run locally or behind Vercel/Cloudflare tunnel.

Start:
    python agents/browser_api.py
    # or
    uvicorn agents.browser_api:app --host 0.0.0.0 --port 8003

Endpoints:
    GET  /tools           — list available tools (MCP-compatible)
    POST /tools/{name}    — call a tool with JSON body
    POST /tool_use        — MCP tool_use protocol (name + arguments in body)
    GET  /health          — health check

Vercel integration:
    Set BROWSER_API_URL in Vercel env, then proxy from api/browser.py:
        from agents.browser_api import app
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from agents.browser_tools import call_tool, list_tools, shutdown

logger = logging.getLogger("scbe.agents.browser_api")

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

_API_KEY = os.getenv("SCBE_BROWSER_API_KEY", "")


def _check_auth(key: Optional[str]) -> None:
    """Check API key if configured."""
    if _API_KEY and key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Browser API starting")
    yield
    logger.info("Browser API shutting down")
    await shutdown()


app = FastAPI(
    title="SCBE Browser Tools API",
    version="1.0.0",
    description="Governed browser automation, web scraping, and research tools.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "https://aethermoore.com",
        "https://*.vercel.app",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "x-api-key"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ToolUseRequest(BaseModel):
    name: str
    arguments: Dict[str, Any] = {}


class ToolCallRequest(BaseModel):
    """Generic tool call — body IS the arguments."""
    pass


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "scbe-browser-tools",
        "tools": len(list_tools()),
    }


@app.get("/tools")
async def get_tools(x_api_key: Optional[str] = Header(None)):
    _check_auth(x_api_key)
    return {"tools": list_tools()}


@app.post("/tools/{tool_name}")
async def call_tool_by_name(
    tool_name: str,
    request: Request,
    x_api_key: Optional[str] = Header(None),
):
    """Call a tool by name. Request body is the arguments dict."""
    _check_auth(x_api_key)
    try:
        body = await request.json()
    except Exception:
        body = {}
    result = await call_tool(tool_name, body)
    if "error" in result and "Unknown tool" in result.get("error", ""):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/tool_use")
async def mcp_tool_use(
    req: ToolUseRequest,
    x_api_key: Optional[str] = Header(None),
):
    """MCP-compatible tool_use endpoint."""
    _check_auth(x_api_key)
    result = await call_tool(req.name, req.arguments)
    return {"type": "tool_result", "content": result}


# ---------------------------------------------------------------------------
# GitHub Actions workflow helper
# ---------------------------------------------------------------------------

@app.post("/workflow/research")
async def workflow_research(
    request: Request,
    x_api_key: Optional[str] = Header(None),
):
    """
    Convenience endpoint for GitHub Actions workflows.
    Accepts: {"query": "...", "max_sources": 5}
    Returns: ResearchReport as JSON
    """
    _check_auth(x_api_key)
    body = await request.json()
    query = body.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    return await call_tool("research", {
        "query": query,
        "max_sources": body.get("max_sources", 5),
        "follow_links": body.get("follow_links", False),
    })


@app.post("/workflow/monitor")
async def workflow_monitor(
    request: Request,
    x_api_key: Optional[str] = Header(None),
):
    """
    Monitor multiple sites. For dashboards and alerting workflows.
    Accepts: {"urls": ["https://...", ...]}
    """
    _check_auth(x_api_key)
    body = await request.json()
    urls = body.get("urls", [])
    if not urls:
        raise HTTPException(status_code=400, detail="urls is required")
    return await call_tool("monitor_sites", {"urls": urls})


@app.post("/workflow/scrape")
async def workflow_scrape(
    request: Request,
    x_api_key: Optional[str] = Header(None),
):
    """
    Scrape a single page. Returns structured data.
    Accepts: {"url": "https://..."}
    """
    _check_auth(x_api_key)
    body = await request.json()
    url = body.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    return await call_tool("scrape_page", {"url": url})


# ---------------------------------------------------------------------------
# Agent Bus endpoints (search + scrape + free LLM)
# ---------------------------------------------------------------------------

@app.post("/bus/ask")
async def bus_ask(
    request: Request,
    x_api_key: Optional[str] = Header(None),
):
    """
    Ask a question. Searches the web, scrapes context, answers with free LLM.
    Accepts: {"question": "What is post-quantum cryptography?"}
    """
    _check_auth(x_api_key)
    body = await request.json()
    question = body.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    return await call_tool("ask", {
        "question": question,
        "search_first": body.get("search_first", True),
    })


@app.post("/bus/summarize")
async def bus_summarize(
    request: Request,
    x_api_key: Optional[str] = Header(None),
):
    """
    Search and summarize a topic with free LLM.
    Accepts: {"query": "topic", "max_sources": 5}
    """
    _check_auth(x_api_key)
    body = await request.json()
    query = body.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    return await call_tool("search_and_summarize", {
        "query": query,
        "max_sources": body.get("max_sources", 5),
    })


@app.post("/bus/analyze")
async def bus_analyze(
    request: Request,
    x_api_key: Optional[str] = Header(None),
):
    """
    Scrape and analyze a page with free LLM.
    Accepts: {"url": "https://..."}
    """
    _check_auth(x_api_key)
    body = await request.json()
    url = body.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    return await call_tool("analyze_page", {"url": url})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("BROWSER_API_PORT", "8003"))
    print(f"SCBE Browser Tools API starting on http://localhost:{port}")
    print(f"Tools: {len(list_tools())}")
    print(f"Auth: {'enabled' if _API_KEY else 'disabled (set SCBE_BROWSER_API_KEY)'}")
    uvicorn.run(app, host="0.0.0.0", port=port)
