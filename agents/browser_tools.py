"""
Browser tool definitions for agent workflows and MCP integration.

Exposes PlaywrightRuntime, WebScraper, ResearchAgent, and RemoteDisplayManager
as callable tools with JSON schema definitions. Works with:
- MCP tool_use protocol
- GitHub Actions (via CLI)
- Vercel API (via HTTP)
- Direct Python import

Each tool function is async, takes a dict, returns a dict.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("scbe.agents.browser_tools")

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS: Dict[str, Dict[str, Any]] = {}
_HANDLERS: Dict[str, Callable] = {}


def tool(name: str, description: str, parameters: Dict[str, Any]):
    """Decorator to register a tool."""
    def decorator(fn):
        TOOLS[name] = {
            "name": name,
            "description": description,
            "input_schema": {
                "type": "object",
                "properties": parameters,
            },
        }
        _HANDLERS[name] = fn
        return fn
    return decorator


async def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Call a registered tool by name."""
    handler = _HANDLERS.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}", "available": list(TOOLS.keys())}
    try:
        return await handler(arguments)
    except Exception as exc:
        logger.exception("Tool %s failed", name)
        return {"error": str(exc)}


def list_tools() -> List[Dict[str, Any]]:
    """Return MCP-compatible tool list."""
    return list(TOOLS.values())


# ---------------------------------------------------------------------------
# Shared runtime (lazy-initialized)
# ---------------------------------------------------------------------------

_runtime = None
_scraper = None
_researcher = None
_display_mgr = None


async def _get_runtime():
    global _runtime
    if _runtime is None:
        from agents.playwright_runtime import PlaywrightRuntime
        _runtime = PlaywrightRuntime()
        await _runtime.launch(headless=True)
    return _runtime


async def _get_scraper():
    global _scraper
    if _scraper is None:
        from agents.web_scraper import WebScraper
        rt = await _get_runtime()
        _scraper = WebScraper(rt)
    return _scraper


async def _get_researcher():
    global _researcher
    if _researcher is None:
        from agents.research_agent import ResearchAgent
        scraper = await _get_scraper()
        _researcher = ResearchAgent(scraper)
    return _researcher


async def shutdown():
    """Clean shutdown of shared runtime."""
    global _runtime, _scraper, _researcher, _display_mgr
    if _runtime:
        await _runtime.close()
    _runtime = _scraper = _researcher = _display_mgr = None


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool(
    name="browser_navigate",
    description="Navigate to a URL and return the page title and text content.",
    parameters={
        "url": {"type": "string", "description": "URL to navigate to"},
    },
)
async def browser_navigate(args: Dict[str, Any]) -> Dict[str, Any]:
    rt = await _get_runtime()
    url = args["url"]
    await rt.navigate(url)
    title = await rt.title()
    text = await rt.evaluate(
        "() => document.body.innerText.substring(0, 5000)"
    )
    return {"url": rt.current_url, "title": title, "text": text}


@tool(
    name="browser_screenshot",
    description="Take a screenshot of the current page. Returns base64-encoded PNG.",
    parameters={
        "url": {"type": "string", "description": "Optional URL to navigate to first"},
    },
)
async def browser_screenshot(args: Dict[str, Any]) -> Dict[str, Any]:
    import base64
    rt = await _get_runtime()
    url = args.get("url")
    if url:
        await rt.navigate(url)
    data = await rt.screenshot()
    return {
        "url": rt.current_url,
        "png_base64": base64.b64encode(data).decode(),
        "size_bytes": len(data),
    }


@tool(
    name="browser_click",
    description="Click an element on the current page by CSS selector.",
    parameters={
        "selector": {"type": "string", "description": "CSS selector to click"},
    },
)
async def browser_click(args: Dict[str, Any]) -> Dict[str, Any]:
    rt = await _get_runtime()
    await rt.click(args["selector"])
    return {"clicked": args["selector"], "url": rt.current_url}


@tool(
    name="browser_type",
    description="Type text into an input element.",
    parameters={
        "selector": {"type": "string", "description": "CSS selector of input"},
        "text": {"type": "string", "description": "Text to type"},
    },
)
async def browser_type(args: Dict[str, Any]) -> Dict[str, Any]:
    rt = await _get_runtime()
    await rt.type_text(args["selector"], args["text"])
    return {"typed": len(args["text"]), "selector": args["selector"]}


@tool(
    name="scrape_page",
    description="Scrape a web page and extract structured data: text, links, tables, metadata, headings.",
    parameters={
        "url": {"type": "string", "description": "URL to scrape"},
        "extract_tables": {"type": "boolean", "description": "Extract HTML tables (default true)"},
        "extract_images": {"type": "boolean", "description": "Extract image metadata (default false)"},
    },
)
async def scrape_page(args: Dict[str, Any]) -> Dict[str, Any]:
    scraper = await _get_scraper()
    page = await scraper.scrape(
        args["url"],
        extract_tables=args.get("extract_tables", True),
        extract_images=args.get("extract_images", False),
    )
    return page.summary(max_text=3000)


@tool(
    name="scrape_many",
    description="Scrape multiple URLs and return summaries for each.",
    parameters={
        "urls": {"type": "array", "items": {"type": "string"}, "description": "List of URLs to scrape"},
    },
)
async def scrape_many(args: Dict[str, Any]) -> Dict[str, Any]:
    scraper = await _get_scraper()
    pages = await scraper.scrape_many(args["urls"])
    return {"pages": [p.summary() for p in pages]}


@tool(
    name="extract_article",
    description="Extract article content from a URL: title, author, date, body text, read time.",
    parameters={
        "url": {"type": "string", "description": "Article URL"},
    },
)
async def extract_article(args: Dict[str, Any]) -> Dict[str, Any]:
    scraper = await _get_scraper()
    return await scraper.extract_article(args["url"])


@tool(
    name="web_search",
    description="Search the web and return scraped results. Uses DuckDuckGo (no API key needed).",
    parameters={
        "query": {"type": "string", "description": "Search query"},
        "max_results": {"type": "integer", "description": "Max results to scrape (default 5)"},
    },
)
async def web_search(args: Dict[str, Any]) -> Dict[str, Any]:
    scraper = await _get_scraper()
    pages = await scraper.search_and_scrape(
        args["query"],
        max_results=args.get("max_results", 5),
    )
    return {"query": args["query"], "results": [p.summary() for p in pages]}


@tool(
    name="research",
    description="Perform deep web research on a topic. Searches, reads multiple sources, scores relevance, and produces a structured report.",
    parameters={
        "query": {"type": "string", "description": "Research query"},
        "max_sources": {"type": "integer", "description": "Max sources to check (default 8)"},
        "follow_links": {"type": "boolean", "description": "Follow promising links for deeper research (default false)"},
    },
)
async def do_research(args: Dict[str, Any]) -> Dict[str, Any]:
    researcher = await _get_researcher()
    researcher.max_sources = args.get("max_sources", 8)
    report = await researcher.research(
        args["query"],
        follow_links=args.get("follow_links", False),
    )
    return report.to_dict()


@tool(
    name="compare_sources",
    description="Read multiple URLs and compare their content on a topic.",
    parameters={
        "urls": {"type": "array", "items": {"type": "string"}, "description": "URLs to compare"},
        "topic": {"type": "string", "description": "Topic to compare on"},
    },
)
async def compare_sources(args: Dict[str, Any]) -> Dict[str, Any]:
    researcher = await _get_researcher()
    return await researcher.compare_sources(args["urls"], args["topic"])


@tool(
    name="monitor_sites",
    description="Quick read of multiple sites. Returns title, word count, description, and text preview for each.",
    parameters={
        "urls": {"type": "array", "items": {"type": "string"}, "description": "URLs to monitor"},
    },
)
async def monitor_sites(args: Dict[str, Any]) -> Dict[str, Any]:
    researcher = await _get_researcher()
    summaries = await researcher.monitor_sites(args["urls"])
    return {"sites": summaries}


# ---------------------------------------------------------------------------
# Agent Bus tools (search + scrape + free LLM)
# ---------------------------------------------------------------------------

_bus = None


async def _get_bus():
    global _bus
    if _bus is None:
        from agents.agent_bus import AgentBus
        _bus = AgentBus()
        await _bus.start(headless=True)
    return _bus


@tool(
    name="ask",
    description="Answer a question using web research + free LLM (HuggingFace/Ollama). Searches the web, scrapes relevant pages, sends context to a free model.",
    parameters={
        "question": {"type": "string", "description": "The question to answer"},
        "search_first": {"type": "boolean", "description": "Search web for context first (default true)"},
    },
)
async def bus_ask(args: Dict[str, Any]) -> Dict[str, Any]:
    bus = await _get_bus()
    return await bus.ask(
        args["question"],
        search_first=args.get("search_first", True),
    )


@tool(
    name="search_and_summarize",
    description="Search the web for a topic, scrape results, and summarize with a free LLM.",
    parameters={
        "query": {"type": "string", "description": "Topic to research and summarize"},
        "max_sources": {"type": "integer", "description": "Max sources (default 5)"},
    },
)
async def bus_summarize(args: Dict[str, Any]) -> Dict[str, Any]:
    bus = await _get_bus()
    return await bus.search_and_summarize(
        args["query"],
        max_sources=args.get("max_sources", 5),
    )


@tool(
    name="analyze_page",
    description="Scrape a web page and analyze its content with a free LLM. Returns structured analysis.",
    parameters={
        "url": {"type": "string", "description": "URL to analyze"},
    },
)
async def bus_analyze(args: Dict[str, Any]) -> Dict[str, Any]:
    bus = await _get_bus()
    return await bus.analyze_page(args["url"])


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

async def _cli_main():
    """Run a tool from the command line: python -m agents.browser_tools <tool> '{json}'"""
    import sys
    if len(sys.argv) < 3:
        print(json.dumps({"tools": list_tools()}, indent=2))
        return

    tool_name = sys.argv[1]
    arguments = json.loads(sys.argv[2])
    result = await call_tool(tool_name, arguments)
    print(json.dumps(result, indent=2, default=str))
    await shutdown()


if __name__ == "__main__":
    asyncio.run(_cli_main())
