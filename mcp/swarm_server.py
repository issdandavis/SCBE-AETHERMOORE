#!/usr/bin/env python3
"""HYDRA Swarm Browser Control MCP Server

Exposes the 6-agent Sacred Tongue browser swarm as MCP tools.
The swarm is lazily initialized on first tool call and kept alive
across calls within the MCP session.

Usage:
    python mcp/swarm_server.py           # starts stdio MCP server
"""

import asyncio
import json
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP

from hydra.swarm_browser import SwarmBrowser, AGENTS

# ---------------------------------------------------------------------------
# Lazy swarm singleton
# ---------------------------------------------------------------------------

_swarm: SwarmBrowser | None = None


def _get_swarm_config() -> dict:
    """Read swarm configuration from environment."""
    return {
        "provider_type": os.environ.get("SWARM_PROVIDER", "local"),
        "model": os.environ.get("SWARM_MODEL", "local-model"),
        "base_url": os.environ.get("SWARM_BASE_URL", "http://localhost:1234/v1"),
        "backend_type": os.environ.get("SWARM_BACKEND", "playwright"),
        "headless": os.environ.get("SWARM_HEADLESS", "1") == "1",
        "dry_run": os.environ.get("SWARM_DRY_RUN", "1") == "1",
    }


async def _ensure_swarm() -> SwarmBrowser:
    """Lazily initialize the swarm on first call."""
    global _swarm
    if _swarm is None:
        config = _get_swarm_config()
        _swarm = SwarmBrowser(**config)
    if not _swarm._launched:
        await _swarm.launch()
    return _swarm


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "hydra-swarm",
    instructions="HYDRA Swarm Browser — 6-agent Sacred Tongue browser control with governance consensus",
)


# ── Tools ──────────────────────────────────────────────────────────────────


@mcp.tool()
async def swarm_launch(dry_run: bool = True) -> str:
    """Launch the 6-agent Sacred Tongue browser swarm.

    Args:
        dry_run: If True, no real browser is started (safe for testing)
    """
    global _swarm
    config = _get_swarm_config()
    config["dry_run"] = dry_run
    _swarm = SwarmBrowser(**config)
    await _swarm.launch()
    return json.dumps({
        "launched": True,
        "agents": list(AGENTS.keys()),
        "dry_run": dry_run,
        "provider": config["provider_type"],
    })


@mcp.tool()
async def swarm_execute_task(task_description: str) -> str:
    """Execute a web task via the full 6-agent swarm pipeline.

    The KO (scout) agent plans, then actions are dispatched to
    specialized tongue agents with Roundtable consensus for sensitive operations.

    Args:
        task_description: Natural language description of the web task
    """
    swarm = await _ensure_swarm()
    result = await swarm.execute_task(task_description)
    return json.dumps(result, default=str)


@mcp.tool()
async def swarm_navigate(url: str) -> str:
    """Navigate to a URL via the KO (scout) agent.

    Args:
        url: Target URL to navigate to
    """
    swarm = await _ensure_swarm()
    result = await swarm.navigate(url)
    return json.dumps(result, default=str)


@mcp.tool()
async def swarm_screenshot() -> str:
    """Take a screenshot via the AV (vision) agent."""
    swarm = await _ensure_swarm()
    result = await swarm.screenshot()
    return json.dumps(result, default=str)


@mcp.tool()
async def swarm_get_content() -> str:
    """Extract page content via the RU (reader) agent."""
    swarm = await _ensure_swarm()
    result = await swarm.get_content()
    return json.dumps(result, default=str)


@mcp.tool()
async def swarm_click(selector: str) -> str:
    """Click an element via the CA (clicker) agent with Roundtable consensus.

    Args:
        selector: CSS selector or element description to click
    """
    swarm = await _ensure_swarm()
    result = await swarm.click(selector)
    return json.dumps(result, default=str)


@mcp.tool()
async def swarm_type(selector: str, text: str) -> str:
    """Type text into an element via the UM (typer) agent with Roundtable consensus.

    Args:
        selector: CSS selector or element description to type into
        text: Text to type
    """
    swarm = await _ensure_swarm()
    result = await swarm.type_text(selector, text)
    return json.dumps(result, default=str)


@mcp.tool()
async def swarm_status() -> str:
    """Get swarm status — agents, tabs, governance info."""
    if _swarm is None:
        return json.dumps({"launched": False, "message": "Swarm not yet initialized. Call swarm_launch first."})
    status = _swarm.get_status()
    return json.dumps(status, default=str)


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
