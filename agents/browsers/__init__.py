"""
SCBE Browser Automation Backends
================================

Multiple browser automation options, all governed by SCBE.

Available backends:
- ChromeMCP: Claude's Chrome extension (mcp__claude-in-chrome__)
- Playwright: Microsoft Playwright (async)
- Selenium: Selenium WebDriver
- CDP: Chrome DevTools Protocol (direct)

All backends implement the BrowserBackend interface and can be wrapped
with GovernedBrowser for SCBE governance.

Usage:
    from agents.browsers import create_browser, GovernedBrowser

    # Quick start with factory
    browser = create_browser("playwright", headless=True)
    await browser.initialize()

    # Or manual setup with governance
    from agents.browsers import PlaywrightBackend, GovernedBrowser
    backend = PlaywrightBackend(headless=True)
    browser = GovernedBrowser(backend, agent_id="my-agent")
    await browser.initialize()

    # Governed action
    result = await browser.navigate("https://example.com")
    # result.decision in ["ALLOW", "QUARANTINE", "ESCALATE", "DENY"]
"""

from .base import BrowserBackend, GovernedBrowser, ActionResult
from .chrome_mcp import ChromeMCPBackend, get_mcp_commands
from .playwright_backend import PlaywrightBackend
from .selenium_backend import SeleniumBackend
from .cdp_backend import CDPBackend, get_chrome_launch_command

__all__ = [
    # Base classes
    "BrowserBackend",
    "GovernedBrowser",
    "ActionResult",
    # Backends
    "ChromeMCPBackend",
    "PlaywrightBackend",
    "SeleniumBackend",
    "CDPBackend",
    # Helpers
    "get_mcp_commands",
    "get_chrome_launch_command",
    "create_browser",
    "list_backends",
]


# =============================================================================
# Backend Registry
# =============================================================================

BACKENDS = {
    "chrome_mcp": {
        "class": ChromeMCPBackend,
        "name": "Chrome MCP",
        "description": "Claude's Chrome extension (mcp__claude-in-chrome__)",
        "requires": "Claude Code with Chrome extension",
        "async": True,
        "headless_support": False,  # Uses existing Chrome
    },
    "playwright": {
        "class": PlaywrightBackend,
        "name": "Playwright",
        "description": "Microsoft Playwright (async, multi-browser)",
        "requires": "pip install playwright && playwright install",
        "async": True,
        "headless_support": True,
    },
    "selenium": {
        "class": SeleniumBackend,
        "name": "Selenium",
        "description": "Selenium WebDriver (sync-to-async wrapped)",
        "requires": "pip install selenium webdriver-manager",
        "async": True,  # Wrapped in async
        "headless_support": True,
    },
    "cdp": {
        "class": CDPBackend,
        "name": "Chrome DevTools Protocol",
        "description": "Direct CDP connection (lowest-level)",
        "requires": "pip install websockets aiohttp + Chrome with --remote-debugging-port",
        "async": True,
        "headless_support": True,
    },
}


def list_backends() -> dict:
    """
    List available browser backends with their info.

    Returns:
        dict: Backend information keyed by backend name
    """
    return {
        name: {
            "name": info["name"],
            "description": info["description"],
            "requires": info["requires"],
            "headless_support": info["headless_support"],
        }
        for name, info in BACKENDS.items()
    }


def create_browser(
    backend_type: str = "playwright",
    governed: bool = True,
    agent_id: str = "governed-browser-001",
    scbe_url: str = "http://127.0.0.1:8080",
    scbe_key: str = "test-key-12345",
    **backend_kwargs
) -> GovernedBrowser:
    """
    Factory function to create a governed browser with specified backend.

    Args:
        backend_type: One of "chrome_mcp", "playwright", "selenium", "cdp"
        governed: If True, wrap with GovernedBrowser (default True)
        agent_id: Agent ID for SCBE governance
        scbe_url: SCBE API URL
        scbe_key: SCBE API key
        **backend_kwargs: Arguments passed to backend constructor

    Returns:
        GovernedBrowser instance (or raw backend if governed=False)

    Example:
        # Playwright with headless
        browser = create_browser("playwright", headless=True)

        # Selenium with Firefox
        browser = create_browser("selenium", browser="firefox", headless=False)

        # CDP (requires Chrome running with --remote-debugging-port=9222)
        browser = create_browser("cdp", port=9222)

        # Chrome MCP (for Claude Code)
        browser = create_browser("chrome_mcp", tab_id=12345)
    """
    if backend_type not in BACKENDS:
        raise ValueError(
            f"Unknown backend: {backend_type}. "
            f"Available: {list(BACKENDS.keys())}"
        )

    backend_class = BACKENDS[backend_type]["class"]
    backend = backend_class(**backend_kwargs)

    if governed:
        return GovernedBrowser(
            backend,
            agent_id=agent_id,
            scbe_url=scbe_url,
            scbe_key=scbe_key
        )
    else:
        return backend


# =============================================================================
# Comparison Table
# =============================================================================

COMPARISON = """
┌─────────────────┬───────────────────────────────────────────────────────────┐
│ Backend         │ Best For                                                  │
├─────────────────┼───────────────────────────────────────────────────────────┤
│ Chrome MCP      │ Claude Code integration, existing Chrome session          │
│ Playwright      │ Modern async automation, multi-browser, testing           │
│ Selenium        │ Enterprise, legacy support, Grid distributed testing      │
│ CDP             │ Low-level control, performance profiling, security audit  │
└─────────────────┴───────────────────────────────────────────────────────────┘

Performance:      CDP > Playwright > Selenium > Chrome MCP (network overhead)
Ease of Use:      Playwright > Selenium > Chrome MCP > CDP
Browser Support:  Selenium > Playwright > CDP/Chrome MCP (Chrome only)
"""


def print_comparison():
    """Print backend comparison table."""
    print(COMPARISON)
