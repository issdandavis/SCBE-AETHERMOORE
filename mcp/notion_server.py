#!/usr/bin/env python3
"""SCBE Notion Workspace Sweeper MCP Server

Exposes tools to search, fetch, and analyze the SCBE Notion workspace.
Falls back to the cached NOTION_PAGE_INDEX.md for offline use.

Requires NOTION_API_KEY env var for live API access.

Usage:
    python mcp/notion_server.py          # starts stdio MCP server
"""

import json
import os
import re
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Notion API helpers
# ---------------------------------------------------------------------------

_NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
_NOTION_VERSION = "2022-06-28"
_NOTION_BASE = "https://api.notion.com/v1"
_INDEX_PATH = os.path.join(_PROJECT_ROOT, "docs", "NOTION_PAGE_INDEX.md")

# Page index cache (built from NOTION_PAGE_INDEX.md or API)
_page_index: list[dict] = []


def _load_index_from_file() -> list[dict]:
    """Parse NOTION_PAGE_INDEX.md into structured page entries."""
    if not os.path.exists(_INDEX_PATH):
        return []
    with open(_INDEX_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    pages = []
    # Parse markdown table rows: | Title | ID | ... |
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("|---") or line.startswith("| Page"):
            continue
        cols = [c.strip() for c in line.split("|")]
        cols = [c for c in cols if c]
        if len(cols) >= 2:
            title = re.sub(r"\*\*([^*]+)\*\*", r"\1", cols[0])  # strip bold
            page_id = cols[1].strip("`")
            status = cols[2] if len(cols) > 2 else ""
            gap = cols[3] if len(cols) > 3 else ""
            pages.append({
                "title": title,
                "page_id": page_id,
                "status": status,
                "gap": gap,
            })
    return pages


def _ensure_index():
    global _page_index
    if not _page_index:
        _page_index = _load_index_from_file()


def _notion_headers() -> dict:
    return {
        "Authorization": f"Bearer {_NOTION_API_KEY}",
        "Notion-Version": _NOTION_VERSION,
        "Content-Type": "application/json",
    }


async def _notion_request(method: str, path: str, body: dict | None = None) -> dict:
    """Make a Notion API request. Requires httpx."""
    import httpx
    url = f"{_NOTION_BASE}{path}"
    async with httpx.AsyncClient(timeout=30) as client:
        if method == "POST":
            resp = await client.post(url, headers=_notion_headers(), json=body or {})
        else:
            resp = await client.get(url, headers=_notion_headers())
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "notion-sweep",
    instructions="SCBE Notion Workspace Sweeper — search, fetch, and gap-analyze the SCBE-AETHERMOORE Notion workspace",
)


# ── Resources ──────────────────────────────────────────────────────────────


@mcp.resource("notion://index")
def resource_index() -> str:
    """Full NOTION_PAGE_INDEX.md content."""
    if os.path.exists(_INDEX_PATH):
        with open(_INDEX_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "# No index file found\n"


# ── Tools ──────────────────────────────────────────────────────────────────


@mcp.tool()
async def notion_search(query: str, max_results: int = 10) -> str:
    """Search Notion pages by query text.

    Uses the Notion API if NOTION_API_KEY is set, otherwise searches the cached index.

    Args:
        query: Search text
        max_results: Maximum number of results to return
    """
    if _NOTION_API_KEY:
        try:
            data = await _notion_request("POST", "/search", {
                "query": query,
                "page_size": min(max_results, 100),
            })
            results = []
            for item in data.get("results", []):
                title_parts = []
                for prop in item.get("properties", {}).values():
                    if prop.get("type") == "title":
                        for t in prop.get("title", []):
                            title_parts.append(t.get("plain_text", ""))
                results.append({
                    "id": item.get("id", ""),
                    "title": " ".join(title_parts) or "(untitled)",
                    "url": item.get("url", ""),
                    "last_edited": item.get("last_edited_time", ""),
                })
            return json.dumps({"source": "api", "count": len(results), "results": results})
        except Exception as e:
            pass  # Fall through to cached index

    # Offline: search cached index
    _ensure_index()
    query_lower = query.lower()
    matches = [p for p in _page_index if query_lower in p["title"].lower()]
    return json.dumps({
        "source": "cached_index",
        "count": len(matches[:max_results]),
        "results": matches[:max_results],
    })


@mcp.tool()
async def notion_fetch_page(page_id: str) -> str:
    """Fetch a specific Notion page by ID (returns block content).

    Args:
        page_id: Notion page UUID
    """
    if not _NOTION_API_KEY:
        return json.dumps({"error": "NOTION_API_KEY not set. Cannot fetch live pages. Use notion_search for cached index."})
    try:
        page = await _notion_request("GET", f"/pages/{page_id}")
        blocks = await _notion_request("GET", f"/blocks/{page_id}/children")
        text_parts = []
        for block in blocks.get("results", []):
            btype = block.get("type", "")
            bdata = block.get(btype, {})
            rich_text = bdata.get("rich_text", [])
            for rt in rich_text:
                text_parts.append(rt.get("plain_text", ""))
        return json.dumps({
            "page_id": page_id,
            "url": page.get("url", ""),
            "last_edited": page.get("last_edited_time", ""),
            "block_count": len(blocks.get("results", [])),
            "text_content": "\n".join(text_parts),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def notion_list_pages(status_filter: str = "") -> str:
    """List all pages in the workspace from the cached index.

    Args:
        status_filter: Optional filter like "BUILT", "NOT BUILT", "Production"
    """
    _ensure_index()
    pages = _page_index
    if status_filter:
        sf = status_filter.lower()
        pages = [p for p in pages if sf in p.get("status", "").lower() or sf in p.get("gap", "").lower()]
    return json.dumps({"count": len(pages), "pages": pages})


@mcp.tool()
def notion_gap_analysis() -> str:
    """Compare Notion specs against codebase — returns BUILT/NOT BUILT status for each page."""
    _ensure_index()
    built = [p for p in _page_index if "BUILT" in p.get("status", "") and "NOT" not in p.get("status", "")]
    not_built = [p for p in _page_index if "NOT BUILT" in p.get("status", "")]
    partial = [p for p in _page_index if "Partial" in p.get("status", "")]
    other = [p for p in _page_index if p not in built and p not in not_built and p not in partial]
    return json.dumps({
        "summary": {
            "built": len(built),
            "not_built": len(not_built),
            "partial": len(partial),
            "other": len(other),
            "total": len(_page_index),
        },
        "built": [{"title": p["title"], "page_id": p["page_id"]} for p in built],
        "not_built": [{"title": p["title"], "page_id": p["page_id"], "gap": p.get("gap", "")} for p in not_built],
        "partial": [{"title": p["title"], "page_id": p["page_id"], "gap": p.get("gap", "")} for p in partial],
    })


@mcp.tool()
def notion_refresh_index() -> str:
    """Re-read the NOTION_PAGE_INDEX.md file and rebuild the in-memory index."""
    global _page_index
    _page_index = _load_index_from_file()
    return json.dumps({"refreshed": True, "page_count": len(_page_index)})


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
