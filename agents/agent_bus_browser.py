"""
Agent Bus browser backends — three swappable modes.

Modes (industry-standard names per 2026 SOTA review):
  - "headless": raw PlaywrightRuntime, fastest, no governance
  - "headed":   SCBEBrowserAgent — visible browser, every action goes through
                the SCBE governance pipeline (ALLOW/QUARANTINE/ESCALATE/DENY)
  - "swarm":    SwarmBrowser — six Sacred Tongue agents with Byzantine
                consensus (4/6 quorum, survives 2 compromised agents)

The bus picks one at construction time. Backends are imported lazily so the
bus stays usable in environments where only some are installed.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger("scbe.agent_bus.browser")

VALID_MODES = ("headless", "headed", "swarm")


class BrowserBackend(Protocol):
    """Common surface every backend exposes back to the bus."""

    runtime: Any  # the underlying PlaywrightRuntime, for WebScraper/ResearchAgent reuse

    async def launch(self, *, headless: bool = True) -> None: ...
    async def close(self) -> None: ...


class HeadlessBackend:
    """Raw PlaywrightRuntime. Fast, no governance. Default for batch/CI."""

    def __init__(self) -> None:
        self.runtime: Any = None

    async def launch(self, *, headless: bool = True) -> None:
        from agents.playwright_runtime import PlaywrightRuntime

        self.runtime = PlaywrightRuntime()
        await self.runtime.launch(headless=headless)

    async def close(self) -> None:
        if self.runtime is not None:
            await self.runtime.close()
            self.runtime = None


class HeadedBackend:
    """SCBEBrowserAgent wrapping a visible PlaywrightRuntime. Every action governed."""

    def __init__(self, agent_id: str = "agent-bus-browser") -> None:
        self.runtime: Any = None
        self.agent_id = agent_id
        self.agent: Any = None

    async def launch(self, *, headless: bool = False) -> None:
        from agents.playwright_runtime import PlaywrightRuntime
        from agents.browser_agent import SCBEBrowserAgent

        self.runtime = PlaywrightRuntime()
        await self.runtime.launch(headless=headless)
        self.agent = SCBEBrowserAgent(
            agent_id=self.agent_id,
            agent_name="Agent Bus Headed Browser",
            runtime=self.runtime,
        )
        logger.info("headed backend ready (governed via SCBEBrowserAgent)")

    async def close(self) -> None:
        if self.runtime is not None:
            await self.runtime.close()
            self.runtime = None
        self.agent = None


class SwarmBackend:
    """SwarmBrowser with six Sacred Tongue agents and Byzantine roundtable."""

    def __init__(self) -> None:
        self.runtime: Any = None
        self.swarm: Any = None

    async def launch(self, *, headless: bool = True) -> None:
        from agents.playwright_runtime import PlaywrightRuntime
        from agents.swarm_browser import SwarmBrowser

        self.runtime = PlaywrightRuntime()
        await self.runtime.launch(headless=headless)
        self.swarm = SwarmBrowser(browser_backend=self.runtime)
        await self.swarm.initialize()
        logger.info("swarm backend ready (6 Sacred Tongue agents)")

    async def close(self) -> None:
        if self.runtime is not None:
            await self.runtime.close()
            self.runtime = None
        self.swarm = None

    async def consensus(self, action_id: str, action: str, context: dict) -> dict:
        if self.swarm is None:
            raise RuntimeError("swarm backend not launched")
        return await self.swarm.roundtable_consensus(action_id, action, context)


def make_backend(mode: str) -> BrowserBackend:
    """Factory: pick a backend by name. Raises ValueError on unknown modes."""
    if mode not in VALID_MODES:
        raise ValueError(f"browser_mode={mode!r} not in {VALID_MODES}")
    if mode == "headless":
        return HeadlessBackend()
    if mode == "headed":
        return HeadedBackend()
    return SwarmBackend()
