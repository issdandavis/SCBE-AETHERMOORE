"""
HYDRA Multi-Screen Browser Swarm
=================================

6 Sacred Tongue agents, each with their own full browser viewport,
cross-talking like kids on a field trip — but with adult brains.

Architecture:
  ┌─────────────────────────────────────────────────────┐
  │              SCBE Governance (Chaperone)             │
  │  Harmonic Wall · L13 Decision Gate · Consensus      │
  └─────────┬───────┬───────┬───────┬───────┬───────┬──┘
            │       │       │       │       │       │
  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐
  │ KO │ │ AV │ │ RU │ │ CA │ │ UM │ │ DR │
  │SCOU│ │VISI│ │READ│ │CLIC│ │TYPE│ │JUDG│
  │ T  │ │ ON │ │ ER │ │ KR │ │ R  │ │ E  │
  └────┘ └────┘ └────┘ └────┘ └────┘ └────┘
    │       │       │       │       │       │
  [Tab1] [Tab2]  [Tab3] [Tab4]  [Tab5] [Tab6]
    ↕       ↕       ↕       ↕       ↕       ↕
  ═══════ CROSS-TALK BUS (Switchboard) ═══════

Each agent:
  - Has a full Playwright BrowserContext (own cookies, storage, viewport)
  - Sees a different site or section simultaneously
  - Posts findings to shared bus → other agents react
  - Flux dynamics from Spiralverse control coherence

Usage:
    from hydra.multi_screen_swarm import MultiScreenSwarm

    swarm = MultiScreenSwarm()
    await swarm.launch()
    await swarm.assign_urls({
        "KO": "https://example.com",
        "AV": "https://example.com/images",
        "RU": "https://example.com/docs",
        "CA": "https://example.com/api",
        "UM": "https://example.com/login",
        "DR": "https://example.com/admin",
    })
    await swarm.run_research("Find all API endpoints and test them")
    await swarm.dissolve()
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

# Sacred Tongue weights (phi-scaled)
PHI = 1.618033988749895
TONGUE_WEIGHTS = {
    "KO": 1.0,
    "AV": PHI,
    "RU": PHI ** 2,
    "CA": PHI ** 3,
    "UM": PHI ** 4,
    "DR": PHI ** 5,
}


class DimensionalState(str, Enum):
    """Polly/Quasi/Demi dimensional breathing from Spiralverse."""
    POLLY = "POLLY"          # nu >= 0.8: Full swarm participation
    QUASI = "QUASI"          # 0.5 <= nu < 0.8: Partial sync
    DEMI = "DEMI"            # 0.1 <= nu < 0.5: Minimal connection
    COLLAPSED = "COLLAPSED"  # nu < 0.1: Disconnected


def get_dimensional_state(nu: float) -> DimensionalState:
    if nu >= 0.8:
        return DimensionalState.POLLY
    if nu >= 0.5:
        return DimensionalState.QUASI
    if nu >= 0.1:
        return DimensionalState.DEMI
    return DimensionalState.COLLAPSED


# ---------------------------------------------------------------------------
#  Cross-Talk Message Bus
# ---------------------------------------------------------------------------

@dataclass
class CrossTalkMessage:
    """A message from one agent to all others on the bus."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    sender: str = ""          # Sacred Tongue (KO/AV/RU/CA/UM/DR)
    msg_type: str = "finding"  # finding | question | alert | command | vote
    content: str = ""
    url: str = ""             # URL the agent was looking at
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    reactions: Dict[str, str] = field(default_factory=dict)  # tongue -> reaction

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "sender": self.sender, "type": self.msg_type,
            "content": self.content[:2000], "url": self.url,
            "data": self.data, "timestamp": self.timestamp,
            "reactions": self.reactions,
        }


class CrossTalkBus:
    """Shared message bus for agent cross-talk.

    Like a group chat where all 6 agents can hear each other.
    DR (Judge) monitors all messages for governance violations.
    """

    def __init__(self, max_history: int = 500):
        self._messages: List[CrossTalkMessage] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()
        self._subscribers: Dict[str, asyncio.Queue] = {}

    async def post(self, msg: CrossTalkMessage) -> None:
        """Post a message to the bus — all agents see it."""
        async with self._lock:
            self._messages.append(msg)
            if len(self._messages) > self._max_history:
                self._messages = self._messages[-self._max_history:]

        # Fan out to all subscribers
        for tongue, queue in self._subscribers.items():
            if tongue != msg.sender:  # Don't echo back to sender
                try:
                    queue.put_nowait(msg)
                except asyncio.QueueFull:
                    pass  # Agent is busy, skip

    def subscribe(self, tongue: str) -> asyncio.Queue:
        """Subscribe an agent to the bus."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers[tongue] = q
        return q

    def unsubscribe(self, tongue: str) -> None:
        self._subscribers.pop(tongue, None)

    def history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages."""
        return [m.to_dict() for m in self._messages[-limit:]]

    def history_for(self, tongue: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get messages relevant to a specific tongue."""
        return [
            m.to_dict() for m in self._messages[-limit * 2:]
            if m.sender == tongue or tongue in m.reactions
        ][-limit:]


# ---------------------------------------------------------------------------
#  Agent Screen — One browser context per tongue
# ---------------------------------------------------------------------------

@dataclass
class AgentScreen:
    """One agent's full browser screen + state."""
    tongue: str
    role: str
    weight: float
    # Flux dynamics (from Spiralverse)
    nu: float = 0.9              # Dimensional flux (start at POLLY)
    dimensional_state: DimensionalState = DimensionalState.POLLY
    coherence: float = 1.0       # Coherence with swarm (0-1)
    # Browser state
    current_url: str = ""
    page_title: str = ""
    page_content_hash: str = ""
    # Task tracking
    findings: List[Dict[str, Any]] = field(default_factory=list)
    actions_taken: int = 0
    errors: int = 0
    # Browser context (set during launch)
    _context: Any = None         # Playwright BrowserContext
    _page: Any = None            # Playwright Page
    _bus_queue: Optional[asyncio.Queue] = None
    _listener_task: Optional[asyncio.Task] = None

    @property
    def alive(self) -> bool:
        return self.dimensional_state != DimensionalState.COLLAPSED

    def status(self) -> Dict[str, Any]:
        return {
            "tongue": self.tongue,
            "role": self.role,
            "weight": self.weight,
            "nu": round(self.nu, 3),
            "state": self.dimensional_state.value,
            "coherence": round(self.coherence, 3),
            "url": self.current_url,
            "title": self.page_title,
            "findings": len(self.findings),
            "actions": self.actions_taken,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
#  Flux ODE Dynamics
# ---------------------------------------------------------------------------

@dataclass
class FluxODE:
    """dnu/dt = alpha*(nu_target - nu) - beta*decay + gamma*coherence_boost"""
    alpha: float = 0.1   # Attraction to target
    beta: float = 0.01   # Natural decay
    gamma: float = 0.05  # Coherence boost
    dt: float = 1.0

    def step(self, screen: AgentScreen, avg_nu: float, swarm_coherence: float) -> None:
        """Advance flux dynamics by one step."""
        target = avg_nu  # Attraction to swarm average
        attraction = self.alpha * (target - screen.nu)
        decay = self.beta
        boost = self.gamma * swarm_coherence * (1 if screen.coherence > 0.5 else -1)

        dnu = (attraction - decay + boost) * self.dt
        screen.nu = max(0.0, min(1.0, screen.nu + dnu))
        screen.dimensional_state = get_dimensional_state(screen.nu)


# ---------------------------------------------------------------------------
#  Multi-Screen Swarm
# ---------------------------------------------------------------------------

ROLES = {
    "KO": "scout",    # Navigates, finds links, maps site structure
    "AV": "vision",   # Analyzes layouts, screenshots, visual elements
    "RU": "reader",   # Extracts text, parses tables, reads documentation
    "CA": "clicker",  # Clicks buttons, fills forms, interacts with UI
    "UM": "typer",    # Types inputs, handles credentials, uploads files
    "DR": "judge",    # Verifies results, validates data, enforces safety
}


class MultiScreenSwarm:
    """6 browser screens running simultaneously with cross-talk.

    Each Sacred Tongue agent gets a full Playwright BrowserContext with:
    - Independent viewport (1280x720 default)
    - Own cookies, localStorage, sessionStorage
    - Separate network state
    - Private console/devtools

    They communicate via the CrossTalkBus — when KO finds a link,
    RU gets notified to read it. When CA clicks a button, DR checks
    the result. Like kids on a field trip calling out what they see,
    with the SCBE governance chaperone keeping them safe.
    """

    def __init__(
        self,
        headless: bool = True,
        viewport: Dict[str, int] = None,
        scbe_url: str = "http://127.0.0.1:8080",
    ):
        self.headless = headless
        self.viewport = viewport or {"width": 1280, "height": 720}
        self.scbe_url = scbe_url

        self.bus = CrossTalkBus()
        self.flux = FluxODE()
        self.screens: Dict[str, AgentScreen] = {}
        self._browser = None  # Playwright browser instance
        self._playwright = None
        self._running = False
        self._flux_task: Optional[asyncio.Task] = None
        self._visited_urls: Set[str] = set()

        # Initialize screens
        for tongue, role in ROLES.items():
            self.screens[tongue] = AgentScreen(
                tongue=tongue,
                role=role,
                weight=TONGUE_WEIGHTS[tongue],
            )

    # ------------------------------------------------------------------
    #  Lifecycle
    # ------------------------------------------------------------------

    async def launch(self) -> None:
        """Launch all 6 browser screens."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("[SWARM] playwright not installed — running in mock mode")
            self._running = True
            return

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)

        for tongue, screen in self.screens.items():
            # Each agent gets its own full BrowserContext
            screen._context = await self._browser.new_context(
                viewport=self.viewport,
                user_agent=f"HYDRA-{tongue}-{screen.role}/1.0",
                locale="en-US",
            )
            screen._page = await screen._context.new_page()

            # Subscribe to cross-talk bus
            screen._bus_queue = self.bus.subscribe(tongue)

            print(f"[SWARM] {tongue} ({screen.role}) — screen ready")

        self._running = True

        # Start flux dynamics tick
        self._flux_task = asyncio.create_task(self._flux_loop())
        print(f"[SWARM] All 6 screens launched — swarm is POLLY")

    async def dissolve(self) -> None:
        """Shut down all screens and clean up."""
        self._running = False

        if self._flux_task:
            self._flux_task.cancel()
            try:
                await self._flux_task
            except asyncio.CancelledError:
                pass

        for tongue, screen in self.screens.items():
            self.bus.unsubscribe(tongue)
            if screen._listener_task:
                screen._listener_task.cancel()
            if screen._context:
                await screen._context.close()

        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        print(f"[SWARM] Dissolved — {sum(len(s.findings) for s in self.screens.values())} total findings")

    # ------------------------------------------------------------------
    #  Navigation
    # ------------------------------------------------------------------

    async def assign_urls(self, urls: Dict[str, str]) -> Dict[str, bool]:
        """Send each agent to a different URL simultaneously."""
        results = {}
        tasks = []

        for tongue, url in urls.items():
            screen = self.screens.get(tongue)
            if not screen or not screen.alive:
                results[tongue] = False
                continue
            tasks.append(self._navigate_agent(tongue, url))

        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, (tongue, url) in enumerate(urls.items()):
            if i < len(task_results):
                r = task_results[i]
                results[tongue] = r is True if not isinstance(r, Exception) else False

        return results

    async def _navigate_agent(self, tongue: str, url: str) -> bool:
        """Navigate one agent to a URL and announce it on the bus."""
        screen = self.screens[tongue]

        if screen._page:
            try:
                await screen._page.goto(url, wait_until="domcontentloaded", timeout=15000)
                screen.current_url = url
                screen.page_title = await screen._page.title()
                screen.actions_taken += 1
                self._visited_urls.add(url)

                # Announce on the bus
                await self.bus.post(CrossTalkMessage(
                    sender=tongue,
                    msg_type="finding",
                    content=f"Navigated to: {screen.page_title}",
                    url=url,
                    data={"action": "navigate", "title": screen.page_title},
                ))
                return True
            except Exception as e:
                screen.errors += 1
                await self.bus.post(CrossTalkMessage(
                    sender=tongue,
                    msg_type="alert",
                    content=f"Navigation failed: {e}",
                    url=url,
                ))
                return False
        else:
            # Mock mode
            screen.current_url = url
            screen.page_title = f"[Mock] {url}"
            screen.actions_taken += 1
            self._visited_urls.add(url)
            await self.bus.post(CrossTalkMessage(
                sender=tongue,
                msg_type="finding",
                content=f"[Mock] Navigated to {url}",
                url=url,
            ))
            return True

    # ------------------------------------------------------------------
    #  Agent Actions
    # ------------------------------------------------------------------

    async def agent_extract_text(self, tongue: str) -> str:
        """Have an agent extract text from their current page."""
        screen = self.screens.get(tongue)
        if not screen or not screen._page:
            return ""

        try:
            text = await screen._page.inner_text("body")
            text = text[:5000]  # Limit
            content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
            screen.page_content_hash = content_hash
            screen.actions_taken += 1

            # Post finding to bus
            summary = text[:300].replace("\n", " ")
            finding = {
                "type": "text_extract",
                "url": screen.current_url,
                "length": len(text),
                "hash": content_hash,
                "summary": summary,
            }
            screen.findings.append(finding)
            await self.bus.post(CrossTalkMessage(
                sender=tongue,
                msg_type="finding",
                content=f"Extracted {len(text)} chars: {summary[:150]}...",
                url=screen.current_url,
                data=finding,
            ))
            return text
        except Exception as e:
            screen.errors += 1
            return f"Error: {e}"

    async def agent_find_links(self, tongue: str) -> List[str]:
        """Have an agent find all links on their page."""
        screen = self.screens.get(tongue)
        if not screen or not screen._page:
            return []

        try:
            links = await screen._page.eval_on_selector_all(
                "a[href]",
                "els => els.map(e => e.href).filter(h => h.startsWith('http'))"
            )
            screen.actions_taken += 1

            # Filter out already-visited URLs
            new_links = [l for l in links if l not in self._visited_urls]

            # Post to bus so other agents can claim URLs
            await self.bus.post(CrossTalkMessage(
                sender=tongue,
                msg_type="finding",
                content=f"Found {len(links)} links ({len(new_links)} new)",
                url=screen.current_url,
                data={"links": new_links[:50], "total": len(links)},
            ))
            return new_links
        except Exception as e:
            screen.errors += 1
            return []

    async def agent_screenshot(self, tongue: str) -> Optional[bytes]:
        """Have an agent take a screenshot of their page."""
        screen = self.screens.get(tongue)
        if not screen or not screen._page:
            return None

        try:
            screenshot = await screen._page.screenshot(full_page=False)
            screen.actions_taken += 1
            await self.bus.post(CrossTalkMessage(
                sender=tongue,
                msg_type="finding",
                content=f"Screenshot taken ({len(screenshot)} bytes)",
                url=screen.current_url,
                data={"screenshot_size": len(screenshot)},
            ))
            return screenshot
        except Exception as e:
            screen.errors += 1
            return None

    async def agent_click(self, tongue: str, selector: str) -> bool:
        """Have an agent click an element on their page."""
        screen = self.screens.get(tongue)
        if not screen or not screen._page:
            return False

        # Governance check — CA/UM/DR have higher click authority
        sensitivity = 0.3 if tongue in ("CA", "UM", "DR") else 0.6

        try:
            await screen._page.click(selector, timeout=5000)
            screen.actions_taken += 1
            await self.bus.post(CrossTalkMessage(
                sender=tongue,
                msg_type="command",
                content=f"Clicked: {selector}",
                url=screen.current_url,
                data={"action": "click", "selector": selector},
            ))
            return True
        except Exception as e:
            screen.errors += 1
            return False

    # ------------------------------------------------------------------
    #  Research Mission — Coordinated multi-agent task
    # ------------------------------------------------------------------

    async def run_research(self, goal: str, max_steps: int = 30) -> Dict[str, Any]:
        """Run a coordinated research mission across all 6 screens.

        KO: Scouts the site, finds links, maps structure
        AV: Takes screenshots, analyzes layouts
        RU: Reads and extracts content from each page
        CA: Clicks through navigation, expands sections
        UM: Fills search boxes, enters queries
        DR: Validates findings, checks for inconsistencies

        They cross-talk on every step — KO finds a link, tells RU to read it.
        RU extracts content, DR validates it. Like a research team.
        """
        results = {
            "goal": goal,
            "steps_taken": 0,
            "findings": [],
            "urls_visited": list(self._visited_urls),
            "agent_summaries": {},
        }

        for step in range(max_steps):
            if not self._running:
                break

            # Each agent takes one action in parallel
            actions = []

            for tongue, screen in self.screens.items():
                if not screen.alive:
                    continue

                if tongue == "KO" and screen.current_url:
                    actions.append(("KO", self.agent_find_links("KO")))
                elif tongue == "RU" and screen.current_url:
                    actions.append(("RU", self.agent_extract_text("RU")))
                elif tongue == "AV" and screen.current_url:
                    actions.append(("AV", self.agent_screenshot("AV")))

            if not actions:
                break

            # Run all actions in parallel
            action_tasks = [a[1] for a in actions]
            await asyncio.gather(*action_tasks, return_exceptions=True)
            results["steps_taken"] += 1

            # Check bus for new links — KO distributes to idle agents
            bus_history = self.bus.history(10)
            for msg in bus_history:
                if msg.get("type") == "finding" and "links" in msg.get("data", {}):
                    new_links = msg["data"]["links"]
                    # Distribute new links to agents without URLs
                    idle_agents = [t for t, s in self.screens.items()
                                   if s.current_url == "" and s.alive and t not in ("DR",)]
                    for i, link in enumerate(new_links[:len(idle_agents)]):
                        if i < len(idle_agents):
                            await self._navigate_agent(idle_agents[i], link)

        # Collect all findings
        for tongue, screen in self.screens.items():
            results["agent_summaries"][tongue] = screen.status()
            results["findings"].extend(screen.findings)

        results["urls_visited"] = list(self._visited_urls)
        results["bus_messages"] = len(self.bus.history(9999))
        return results

    # ------------------------------------------------------------------
    #  Flux Dynamics Loop
    # ------------------------------------------------------------------

    async def _flux_loop(self) -> None:
        """Continuous flux dynamics — Spiralverse breathing."""
        while self._running:
            await asyncio.sleep(5.0)  # Tick every 5 seconds

            alive = [s for s in self.screens.values() if s.alive]
            if not alive:
                continue

            avg_nu = sum(s.nu for s in alive) / len(alive)
            variance = sum((s.nu - avg_nu) ** 2 for s in alive) / len(alive)
            swarm_coherence = max(0, 1 - (variance ** 0.5) * 2)

            for screen in alive:
                # Update coherence based on distance from average
                screen.coherence = max(0, 1 - abs(screen.nu - avg_nu))
                # Step flux ODE
                self.flux.step(screen, avg_nu, swarm_coherence)

                # Boost on success, decay on errors
                if screen.actions_taken > 0 and screen.errors == 0:
                    screen.nu = min(1.0, screen.nu + 0.02)
                elif screen.errors > screen.actions_taken * 0.5:
                    screen.nu = max(0.0, screen.nu - 0.05)

    # ------------------------------------------------------------------
    #  Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Full swarm status."""
        alive = [s for s in self.screens.values() if s.alive]
        avg_nu = sum(s.nu for s in alive) / len(alive) if alive else 0

        return {
            "running": self._running,
            "screens": {t: s.status() for t, s in self.screens.items()},
            "avg_nu": round(avg_nu, 3),
            "dominant_state": get_dimensional_state(avg_nu).value,
            "urls_visited": len(self._visited_urls),
            "total_findings": sum(len(s.findings) for s in self.screens.values()),
            "total_actions": sum(s.actions_taken for s in self.screens.values()),
            "bus_messages": len(self.bus.history(9999)),
        }

    def status_text(self) -> str:
        """Human-readable status."""
        s = self.status()
        lines = [
            f"HYDRA Multi-Screen Swarm",
            f"========================",
            f"State: {s['dominant_state']} (avg nu={s['avg_nu']:.3f})",
            f"URLs: {s['urls_visited']} | Findings: {s['total_findings']} | Actions: {s['total_actions']}",
            f"Bus: {s['bus_messages']} messages",
            f"",
        ]
        for tongue, screen in s["screens"].items():
            state_icon = {"POLLY": "O", "QUASI": "~", "DEMI": ".", "COLLAPSED": "X"}[screen["state"]]
            lines.append(
                f"  [{state_icon}] {tongue} ({screen['role']:7s}) "
                f"nu={screen['nu']:.2f} coh={screen['coherence']:.2f} "
                f"| {screen['url'][:50] or '(no url)'}"
            )
        return "\n".join(lines)
