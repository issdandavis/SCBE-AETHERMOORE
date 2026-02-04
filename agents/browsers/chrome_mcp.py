"""
Chrome MCP Backend
==================

Browser backend using Claude's Chrome extension (mcp__claude-in-chrome__).

This integrates directly with the Chrome browser via MCP tools.

Requirements:
    - Claude Code with Chrome extension installed
    - Chrome browser running with extension active
"""

import asyncio
import json
from typing import Optional, Dict, Any, List
from .base import BrowserBackend


class ChromeMCPBackend(BrowserBackend):
    """
    Browser backend using Claude's Chrome extension.

    This is designed to be called from Claude Code where MCP tools are available.
    When used standalone, it provides a mock implementation for testing.
    """

    name = "chrome_mcp"

    def __init__(self, tab_id: Optional[int] = None):
        self.tab_id = tab_id
        self.current_url = ""
        self._mcp_available = False

    async def initialize(self) -> bool:
        """Initialize Chrome MCP connection."""
        # In Claude Code context, MCP tools are available globally
        # This is a placeholder - actual MCP calls happen through Claude

        print("[ChromeMCP] Initializing...")
        print("[ChromeMCP] Note: MCP tools are called through Claude Code")
        print("[ChromeMCP] Use GovernedBrowser with this backend in Claude Code context")

        # Check if we have a tab ID
        if self.tab_id is None:
            print("[ChromeMCP] No tab_id provided - will need to create or select tab")

        self._mcp_available = True
        return True

    async def navigate(self, url: str) -> Dict[str, Any]:
        """
        Navigate to URL.

        In Claude Code, this would call:
        mcp__claude-in-chrome__navigate(url=url, tabId=self.tab_id)
        """
        self.current_url = url
        return {
            "action": "navigate",
            "url": url,
            "tab_id": self.tab_id,
            "mcp_call": f"mcp__claude-in-chrome__navigate(url='{url}', tabId={self.tab_id})"
        }

    async def click(self, selector: str) -> Dict[str, Any]:
        """
        Click element.

        In Claude Code, this would use:
        mcp__claude-in-chrome__computer(action='left_click', coordinate=[x,y], tabId=self.tab_id)

        Or find element first:
        mcp__claude-in-chrome__find(text=selector, tabId=self.tab_id)
        """
        return {
            "action": "click",
            "selector": selector,
            "tab_id": self.tab_id,
            "mcp_call": f"mcp__claude-in-chrome__computer(action='left_click', tabId={self.tab_id})"
        }

    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """
        Type text.

        In Claude Code:
        mcp__claude-in-chrome__computer(action='type', text=text, tabId=self.tab_id)
        """
        return {
            "action": "type",
            "selector": selector,
            "text_length": len(text),
            "tab_id": self.tab_id,
            "mcp_call": f"mcp__claude-in-chrome__computer(action='type', text='...', tabId={self.tab_id})"
        }

    async def get_page_content(self) -> str:
        """
        Get page content.

        In Claude Code:
        mcp__claude-in-chrome__get_page_text(tabId=self.tab_id)
        or
        mcp__claude-in-chrome__read_page(tabId=self.tab_id)
        """
        return f"[Page content from {self.current_url}]"

    async def screenshot(self) -> bytes:
        """
        Take screenshot.

        In Claude Code:
        mcp__claude-in-chrome__computer(action='screenshot', tabId=self.tab_id)
        """
        return b""  # Would be actual screenshot bytes

    async def execute_script(self, script: str) -> Any:
        """
        Execute JavaScript.

        In Claude Code:
        mcp__claude-in-chrome__javascript_tool(script=script, tabId=self.tab_id)
        """
        return {
            "action": "execute_script",
            "script_length": len(script),
            "tab_id": self.tab_id,
            "mcp_call": f"mcp__claude-in-chrome__javascript_tool(script='...', tabId={self.tab_id})"
        }

    async def get_current_url(self) -> str:
        """Get current URL."""
        return self.current_url

    async def scroll(self, direction: str = "down", amount: int = 3) -> Dict[str, Any]:
        """
        Scroll page.

        In Claude Code:
        mcp__claude-in-chrome__computer(
            action='scroll',
            scroll_direction=direction,
            scroll_amount=amount,
            tabId=self.tab_id
        )
        """
        return {
            "action": "scroll",
            "direction": direction,
            "amount": amount,
            "mcp_call": f"mcp__claude-in-chrome__computer(action='scroll', scroll_direction='{direction}', tabId={self.tab_id})"
        }

    async def find_element(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Find element by text.

        In Claude Code:
        mcp__claude-in-chrome__find(text=text, tabId=self.tab_id)
        """
        return {
            "action": "find",
            "text": text,
            "mcp_call": f"mcp__claude-in-chrome__find(text='{text}', tabId={self.tab_id})"
        }

    async def close(self) -> None:
        """Close tab/browser."""
        print(f"[ChromeMCP] Closing tab {self.tab_id}")


# =============================================================================
# Helper for Claude Code Integration
# =============================================================================

def get_mcp_commands(action: str, **kwargs) -> str:
    """
    Get the MCP command string for an action.

    This helps when you want to see what MCP calls would be made.
    """
    tab_id = kwargs.get("tab_id", "TAB_ID")

    commands = {
        "navigate": f"mcp__claude-in-chrome__navigate(url='{kwargs.get('url', 'URL')}', tabId={tab_id})",

        "click": f"mcp__claude-in-chrome__computer(action='left_click', coordinate={kwargs.get('coord', '[x,y]')}, tabId={tab_id})",

        "type": f"mcp__claude-in-chrome__computer(action='type', text='{kwargs.get('text', 'TEXT')}', tabId={tab_id})",

        "screenshot": f"mcp__claude-in-chrome__computer(action='screenshot', tabId={tab_id})",

        "scroll": f"mcp__claude-in-chrome__computer(action='scroll', scroll_direction='{kwargs.get('direction', 'down')}', tabId={tab_id})",

        "read_page": f"mcp__claude-in-chrome__read_page(tabId={tab_id})",

        "get_text": f"mcp__claude-in-chrome__get_page_text(tabId={tab_id})",

        "javascript": f"mcp__claude-in-chrome__javascript_tool(script='{kwargs.get('script', 'SCRIPT')}', tabId={tab_id})",

        "find": f"mcp__claude-in-chrome__find(text='{kwargs.get('text', 'TEXT')}', tabId={tab_id})",

        "tabs_context": "mcp__claude-in-chrome__tabs_context_mcp(createIfEmpty=true)",

        "create_tab": "mcp__claude-in-chrome__tabs_create_mcp()",
    }

    return commands.get(action, f"Unknown action: {action}")


# =============================================================================
# Example Usage Instructions
# =============================================================================

USAGE_INSTRUCTIONS = """
Chrome MCP Backend Usage in Claude Code
=======================================

1. First, load the MCP tools:
   <use ToolSearch to load mcp__claude-in-chrome__tabs_context_mcp>

2. Get tab context:
   <call mcp__claude-in-chrome__tabs_context_mcp with createIfEmpty=true>

3. Create or use existing tab:
   <call mcp__claude-in-chrome__tabs_create_mcp if needed>

4. Use the GovernedBrowser:

   from agents.browsers import ChromeMCPBackend, GovernedBrowser

   backend = ChromeMCPBackend(tab_id=YOUR_TAB_ID)
   browser = GovernedBrowser(backend, agent_id="my-agent")
   await browser.initialize()

   # Every action is now governed by SCBE
   result = await browser.navigate("https://example.com")

5. The governance flow:
   - Action requested -> SCBE API called -> Decision made
   - ALLOW: Execute via MCP
   - QUARANTINE: Execute with logging
   - ESCALATE: Ask higher AI or human
   - DENY: Block action
"""

if __name__ == "__main__":
    print(USAGE_INSTRUCTIONS)
    print("\nMCP Commands Reference:")
    print("-" * 40)
    for action in ["navigate", "click", "type", "screenshot", "scroll", "read_page", "javascript", "find"]:
        print(f"{action}: {get_mcp_commands(action)}")
