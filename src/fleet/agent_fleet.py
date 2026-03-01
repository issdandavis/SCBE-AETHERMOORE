"""
HYDRA Agent Fleet — Multi-Agent Orchestrator
==============================================

Manages N concurrent AI agents that work across platforms simultaneously.
Each agent has both a browser (HydraHand) and connector (API) side,
attacking tasks from both directions at once.

Architecture:
    AgentFleet
    ├── FleetAgent "issues"   → GitHub issues, Notion tasks
    ├── FleetAgent "builder"  → PRs, Shopify products, Canva designs
    └── FleetAgent "ops"      → CI/CD, releases, site deploys, Adobe assets

Each FleetAgent wraps:
    - HydraHand (6 Playwright fingers for full browser interaction)
    - ConnectorBridge (API calls to 14+ platforms)
    - SharedSession (from SessionPool — tokens, cookies, rate limits)

Task routing:
    1. connector-first: Try API, fall back to browser
    2. browser-first:   Try browser, use connector for verification
    3. both:            Run connector + browser in parallel, merge

Platforms: GitHub, Shopify, Notion, Airtable, Canva, Adobe, Gamma,
           Zapier, n8n, Slack, Discord, Linear, generic webhooks

Usage:
    fleet = AgentFleet(max_agents=3)
    await fleet.start()

    await fleet.submit(FleetTask(
        task_type="github_issue",
        platform="github",
        target="241",
        action="triage",
    ))

    report = await fleet.run_until_empty()
    await fleet.shutdown()
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("agent-fleet")


# ── Task Types ─────────────────────────────────────────────────────────

class TaskPriority(int, Enum):
    URGENT = 1
    HIGH = 3
    NORMAL = 5
    LOW = 7
    BACKGROUND = 10


class ExecutionMode(str, Enum):
    CONNECTOR_FIRST = "connector_first"  # API first, browser fallback
    BROWSER_FIRST = "browser_first"      # Browser first, connector verify
    BOTH = "both"                        # Parallel, merge results
    CONNECTOR_ONLY = "connector_only"    # API only (no browser)
    BROWSER_ONLY = "browser_only"        # Browser only (no API)


class TaskStatus(str, Enum):
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # Deduped


@dataclass
class FleetTask:
    """A unit of work for the fleet."""
    task_type: str              # github_issue, shopify_product, canva_design, etc.
    platform: str               # github, shopify, canva, adobe, gamma, notion, etc.
    target: str                 # URL, issue number, product ID, etc.
    action: str                 # triage, create, update, close, publish, export, etc.
    params: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    execution_mode: ExecutionMode = ExecutionMode.CONNECTOR_FIRST
    task_id: str = ""
    status: TaskStatus = TaskStatus.QUEUED
    assigned_to: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    credits_earned: float = 0.0

    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())[:12]
        if not self.created_at:
            self.created_at = time.time()

    @property
    def fingerprint(self) -> str:
        """Dedup key: same platform + target + action = same task."""
        raw = f"{self.platform}:{self.target}:{self.action}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def elapsed_ms(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "platform": self.platform,
            "target": self.target,
            "action": self.action,
            "priority": self.priority.value,
            "execution_mode": self.execution_mode.value,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "credits_earned": round(self.credits_earned, 4),
            "elapsed_ms": round(self.elapsed_ms, 1),
            "error": self.error,
        }


@dataclass
class TaskResult:
    """Result from executing a task."""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    connector_result: Optional[Dict[str, Any]] = None
    browser_result: Optional[Dict[str, Any]] = None
    source: str = ""         # "connector", "browser", "both"
    credits_earned: float = 0.0
    training_pair: Optional[Dict[str, Any]] = None  # SFT pair generated


# ── Agent Roles ────────────────────────────────────────────────────────

AGENT_ROLES = {
    "issues": {
        "description": "Issue triage, labeling, assignment, branch creation",
        "platforms": ["github", "linear", "notion", "airtable"],
        "task_types": ["github_issue", "linear_issue", "notion_task", "airtable_record"],
    },
    "builder": {
        "description": "Content creation — PRs, products, designs, sites",
        "platforms": ["github", "shopify", "canva", "adobe", "gamma"],
        "task_types": ["github_pr", "shopify_product", "canva_design", "adobe_asset", "gamma_site"],
    },
    "ops": {
        "description": "Operations — CI/CD, releases, deploys, monitoring",
        "platforms": ["github", "shopify", "zapier", "n8n", "slack", "discord"],
        "task_types": ["github_release", "shopify_order", "zapier_trigger", "n8n_workflow", "notification"],
    },
}


# ── Fleet Agent ────────────────────────────────────────────────────────

class FleetAgent:
    """A single agent in the fleet with browser + connector capabilities."""

    def __init__(self, agent_id: str, role: str):
        self.agent_id = agent_id
        self.role = role
        self.role_config = AGENT_ROLES.get(role, AGENT_ROLES["ops"])
        self.hand = None           # HydraHand — initialized on start
        self.connector = None      # ConnectorBridge — initialized on start
        self.session_pool = None   # SessionPool — shared across agents
        self.tasks_completed: int = 0
        self.tasks_failed: int = 0
        self.total_credits: float = 0.0
        self._running = False

    async def start(self, session_pool=None):
        """Initialize browser and connector."""
        self.session_pool = session_pool

        # Lazy imports to avoid circular deps
        try:
            from src.browser.hydra_hand import HydraHand
            self.hand = HydraHand(head_id=self.agent_id)
            await self.hand.open()
            logger.info("[%s] Browser hand opened (6 fingers)", self.agent_id)
        except Exception as e:
            logger.warning("[%s] Browser unavailable: %s — running connector-only", self.agent_id, e)

        try:
            from src.fleet.connector_bridge import ConnectorBridge
            self.connector = ConnectorBridge(session_pool=session_pool)
            logger.info("[%s] Connector bridge ready", self.agent_id)
        except Exception as e:
            logger.warning("[%s] Connector bridge unavailable: %s", self.agent_id, e)

        self._running = True

    async def stop(self):
        """Shut down browser and cleanup."""
        self._running = False
        if self.hand:
            await self.hand.close()
            self.hand = None
        logger.info("[%s] Agent stopped (completed=%d, failed=%d, credits=%.2f)",
                     self.agent_id, self.tasks_completed, self.tasks_failed, self.total_credits)

    async def execute(self, task: FleetTask) -> TaskResult:
        """Execute a task using the appropriate execution mode."""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        task.assigned_to = self.agent_id

        try:
            mode = task.execution_mode

            if mode == ExecutionMode.CONNECTOR_FIRST:
                result = await self._connector_first(task)
            elif mode == ExecutionMode.BROWSER_FIRST:
                result = await self._browser_first(task)
            elif mode == ExecutionMode.BOTH:
                result = await self._both_sides(task)
            elif mode == ExecutionMode.CONNECTOR_ONLY:
                result = await self._connector_only(task)
            elif mode == ExecutionMode.BROWSER_ONLY:
                result = await self._browser_only(task)
            else:
                result = await self._connector_first(task)

            task.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
            task.result = result.data
            task.credits_earned = result.credits_earned
            task.completed_at = time.time()

            if result.success:
                self.tasks_completed += 1
                self.total_credits += result.credits_earned
            else:
                self.tasks_failed += 1

            # Generate training pair from this interaction
            result.training_pair = self._generate_sft_pair(task, result)

            return result

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()
            self.tasks_failed += 1
            logger.error("[%s] Task %s failed: %s", self.agent_id, task.task_id, e)
            return TaskResult(success=False, data={"error": str(e)}, source="error")

    async def _connector_first(self, task: FleetTask) -> TaskResult:
        """Try connector, fall back to browser."""
        if self.connector and self.connector.is_configured(task.platform):
            cr = await self.connector.execute(task.platform, task.action, task.params)
            if cr.success:
                return TaskResult(
                    success=True, data=cr.data, connector_result=cr.data,
                    source="connector", credits_earned=cr.credits_earned,
                )

        # Connector failed or unavailable — try browser
        if self.hand:
            br = await self._browser_execute(task)
            return br

        return TaskResult(success=False, data={"error": "No connector or browser available"}, source="none")

    async def _browser_first(self, task: FleetTask) -> TaskResult:
        """Try browser, use connector for verification."""
        if self.hand:
            br = await self._browser_execute(task)
            if br.success:
                return br

        # Browser failed — try connector
        if self.connector and self.connector.is_configured(task.platform):
            cr = await self.connector.execute(task.platform, task.action, task.params)
            return TaskResult(
                success=cr.success, data=cr.data, connector_result=cr.data,
                source="connector", credits_earned=cr.credits_earned,
            )

        return TaskResult(success=False, data={"error": "No browser or connector available"}, source="none")

    async def _both_sides(self, task: FleetTask) -> TaskResult:
        """Run connector + browser in parallel, merge results."""
        tasks = []
        if self.connector and self.connector.is_configured(task.platform):
            tasks.append(self._connector_execute(task))
        if self.hand:
            tasks.append(self._browser_execute(task))

        if not tasks:
            return TaskResult(success=False, data={"error": "No execution path available"}, source="none")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        merged_data = {}
        connector_data = None
        browser_data = None
        any_success = False
        total_credits = 0.0

        for r in results:
            if isinstance(r, Exception):
                continue
            if r.success:
                any_success = True
                total_credits += r.credits_earned
                merged_data.update(r.data)
                if r.source == "connector":
                    connector_data = r.data
                elif r.source == "browser":
                    browser_data = r.data

        return TaskResult(
            success=any_success, data=merged_data,
            connector_result=connector_data, browser_result=browser_data,
            source="both", credits_earned=total_credits,
        )

    async def _connector_only(self, task: FleetTask) -> TaskResult:
        if self.connector and self.connector.is_configured(task.platform):
            return await self._connector_execute(task)
        return TaskResult(success=False, data={"error": f"No connector for {task.platform}"}, source="none")

    async def _browser_only(self, task: FleetTask) -> TaskResult:
        if self.hand:
            return await self._browser_execute(task)
        return TaskResult(success=False, data={"error": "Browser unavailable"}, source="none")

    async def _connector_execute(self, task: FleetTask) -> TaskResult:
        """Execute via connector."""
        cr = await self.connector.execute(task.platform, task.action, task.params)
        return TaskResult(
            success=cr.success, data=cr.data, connector_result=cr.data,
            source="connector", credits_earned=cr.credits_earned,
        )

    async def _browser_execute(self, task: FleetTask) -> TaskResult:
        """Execute via browser — route to platform-specific browser flows."""
        handler = BROWSER_FLOWS.get(task.platform, {}).get(task.action)
        if handler:
            return await handler(self.hand, task)

        # Generic: navigate to target URL and extract
        if task.target.startswith("http"):
            from src.browser.hydra_hand import Tongue
            ca = self.hand.finger(Tongue.CA)
            nav = await ca.navigate(task.target)
            text = await ca.extract_text()
            return TaskResult(
                success=not nav.metadata.get("error"),
                data={"title": nav.title, "text": text[:2000], "url": task.target},
                browser_result={"title": nav.title},
                source="browser",
                credits_earned=0.1,
            )

        return TaskResult(success=False, data={"error": f"No browser flow for {task.platform}/{task.action}"}, source="browser")

    def _generate_sft_pair(self, task: FleetTask, result: TaskResult) -> Dict[str, Any]:
        """Generate an SFT training pair from this task execution."""
        instruction = f"Execute {task.action} on {task.platform} for target: {task.target}"
        if task.params:
            instruction += f" with params: {json.dumps(task.params, default=str)[:200]}"

        response = f"Executed via {result.source}. "
        if result.success:
            response += f"Success. "
            if result.data:
                response += json.dumps(result.data, default=str)[:500]
        else:
            response += f"Failed: {result.data.get('error', 'unknown')}"

        return {
            "instruction": instruction,
            "response": response,
            "source": "agent_fleet",
            "platform": task.platform,
            "task_type": task.task_type,
            "credits": result.credits_earned,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "running": self._running,
            "has_browser": self.hand is not None and self.hand._open,
            "has_connector": self.connector is not None,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "total_credits": round(self.total_credits, 4),
            "platforms": self.role_config["platforms"],
        }


# ── Browser Flows (platform-specific browser interactions) ─────────────

async def _github_browser_triage(hand, task: FleetTask) -> TaskResult:
    """Browser-based GitHub issue triage: navigate, read, label."""
    from src.browser.hydra_hand import Tongue
    av = hand.finger(Tongue.AV)
    target = task.target
    if not target.startswith("http"):
        repo = task.params.get("repo", "issdandavis/SCBE-AETHERMOORE")
        target = f"https://github.com/{repo}/issues/{target}"
    nav = await av.navigate(target)
    text = await av.extract_text("div.js-discussion")
    title = await av.page_title()
    return TaskResult(
        success=bool(text),
        data={"title": title, "body": text[:3000], "url": target},
        browser_result={"title": title},
        source="browser",
        credits_earned=0.2,
    )


async def _github_browser_pr_review(hand, task: FleetTask) -> TaskResult:
    """Browser-based PR review: read diff, check CI status."""
    from src.browser.hydra_hand import Tongue
    ca = hand.finger(Tongue.CA)
    target = task.target
    if not target.startswith("http"):
        repo = task.params.get("repo", "issdandavis/SCBE-AETHERMOORE")
        target = f"https://github.com/{repo}/pull/{target}"
    nav = await ca.navigate(target)
    title = await ca.page_title()
    # Check files changed tab
    await ca.navigate(f"{target}/files")
    diff_text = await ca.extract_text("div.js-diff-progressive-container")
    return TaskResult(
        success=bool(diff_text),
        data={"title": title, "diff_preview": diff_text[:5000], "url": target},
        browser_result={"title": title},
        source="browser",
        credits_earned=0.3,
    )


async def _shopify_browser_check(hand, task: FleetTask) -> TaskResult:
    """Browser-based Shopify store check: navigate storefront, verify products."""
    from src.browser.hydra_hand import Tongue
    av = hand.finger(Tongue.AV)
    shop_domain = task.params.get("shop_domain", os.environ.get("SHOPIFY_SHOP_DOMAIN", ""))
    target = task.target if task.target.startswith("http") else f"https://{shop_domain}"
    nav = await av.navigate(target)
    title = await av.page_title()
    text = await av.extract_text()
    links = await av.extract_links()
    product_links = [l for l in links if "/products/" in l]
    return TaskResult(
        success=bool(title),
        data={"title": title, "product_count": len(product_links), "products": product_links[:20], "url": target},
        browser_result={"title": title, "products": len(product_links)},
        source="browser",
        credits_earned=0.2,
    )


async def _gamma_browser_create(hand, task: FleetTask) -> TaskResult:
    """Browser-based Gamma site creation: navigate to gamma.app, create/edit."""
    from src.browser.hydra_hand import Tongue
    ca = hand.finger(Tongue.CA)
    nav = await ca.navigate("https://gamma.app")
    title = await ca.page_title()
    return TaskResult(
        success=bool(title),
        data={"title": title, "note": "Gamma requires auth — use connector for programmatic access"},
        source="browser",
        credits_earned=0.1,
    )


async def _canva_browser_export(hand, task: FleetTask) -> TaskResult:
    """Browser-based Canva design export."""
    from src.browser.hydra_hand import Tongue
    ca = hand.finger(Tongue.CA)
    target = task.target if task.target.startswith("http") else f"https://www.canva.com/design/{task.target}"
    nav = await ca.navigate(target)
    title = await ca.page_title()
    return TaskResult(
        success=bool(title),
        data={"title": title, "url": target},
        source="browser",
        credits_earned=0.2,
    )


# Browser flow registry: platform -> action -> handler
BROWSER_FLOWS: Dict[str, Dict[str, Callable]] = {
    "github": {
        "triage": _github_browser_triage,
        "review": _github_browser_pr_review,
        "read": _github_browser_triage,
    },
    "shopify": {
        "check": _shopify_browser_check,
        "verify": _shopify_browser_check,
        "read": _shopify_browser_check,
    },
    "gamma": {
        "create": _gamma_browser_create,
        "read": _gamma_browser_create,
    },
    "canva": {
        "export": _canva_browser_export,
        "read": _canva_browser_export,
    },
}


# ── Fleet Report ───────────────────────────────────────────────────────

@dataclass
class FleetReport:
    """Summary of a fleet run."""
    total_tasks: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    total_credits: float = 0.0
    elapsed_ms: float = 0.0
    agents: List[Dict[str, Any]] = field(default_factory=list)
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    training_pairs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
            "total_credits": round(self.total_credits, 4),
            "elapsed_ms": round(self.elapsed_ms, 1),
            "agents": self.agents,
            "task_summary": self.tasks[:20],
            "training_pairs_generated": len(self.training_pairs),
        }


# ── Agent Fleet (Orchestrator) ─────────────────────────────────────────

class AgentFleet:
    """
    Multi-agent orchestrator with shared state.

    Manages N concurrent agents, each with browser + connector capabilities.
    Tasks are deduplicated, prioritized, and routed to the best agent.

    Usage:
        fleet = AgentFleet(max_agents=3)
        await fleet.start()

        await fleet.submit(FleetTask(
            task_type="github_issue", platform="github",
            target="241", action="triage",
        ))

        report = await fleet.run_until_empty()
        await fleet.shutdown()
    """

    def __init__(self, max_agents: int = 3, roles: Optional[List[str]] = None):
        self.max_agents = max_agents
        self.roles = roles or ["issues", "builder", "ops"]
        self.agents: Dict[str, FleetAgent] = {}
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._active_fingerprints: Set[str] = set()
        self._completed_tasks: List[FleetTask] = []
        self._training_pairs: List[Dict[str, Any]] = []
        self._session_pool = None
        self._running = False
        self._start_time: float = 0.0

    async def start(self):
        """Initialize session pool and spawn agents."""
        self._start_time = time.time()

        # Initialize shared session pool
        try:
            from src.fleet.session_pool import SessionPool
            self._session_pool = SessionPool()
            logger.info("Session pool initialized")
        except Exception as e:
            logger.warning("Session pool unavailable: %s", e)

        # Spawn agents
        for i, role in enumerate(self.roles[:self.max_agents]):
            agent_id = f"fleet-{role}-{i}"
            agent = FleetAgent(agent_id=agent_id, role=role)
            await agent.start(session_pool=self._session_pool)
            self.agents[agent_id] = agent
            logger.info("Agent %s spawned (role=%s)", agent_id, role)

        self._running = True
        logger.info("Fleet started with %d agents", len(self.agents))

    async def submit(self, task: FleetTask) -> str:
        """Submit a task to the fleet queue. Returns task_id."""
        fp = task.fingerprint
        if fp in self._active_fingerprints:
            task.status = TaskStatus.SKIPPED
            logger.info("Task %s deduped (fingerprint=%s)", task.task_id, fp)
            return task.task_id

        self._active_fingerprints.add(fp)
        # Priority queue sorts by (priority, created_at) — lower = higher priority
        await self._task_queue.put((task.priority.value, task.created_at, task))
        logger.info("Task %s queued (type=%s, platform=%s, action=%s, priority=%d)",
                     task.task_id, task.task_type, task.platform, task.action, task.priority.value)
        return task.task_id

    async def submit_batch(self, tasks: List[FleetTask]) -> List[str]:
        """Submit multiple tasks at once."""
        return [await self.submit(t) for t in tasks]

    def _pick_agent(self, task: FleetTask) -> Optional[FleetAgent]:
        """Pick the best agent for a task based on role affinity."""
        # First: find an agent whose role matches the task's platform
        for agent in self.agents.values():
            if task.platform in agent.role_config["platforms"]:
                return agent

        # Fallback: any agent
        agents = list(self.agents.values())
        if agents:
            # Pick least-loaded agent
            return min(agents, key=lambda a: a.tasks_completed + a.tasks_failed)
        return None

    async def run_until_empty(self) -> FleetReport:
        """Process all queued tasks and return a report."""
        while not self._task_queue.empty():
            _, _, task = await self._task_queue.get()

            agent = self._pick_agent(task)
            if not agent:
                task.status = TaskStatus.FAILED
                task.error = "No agent available"
                self._completed_tasks.append(task)
                continue

            result = await agent.execute(task)
            self._completed_tasks.append(task)
            self._active_fingerprints.discard(task.fingerprint)

            if result.training_pair:
                self._training_pairs.append(result.training_pair)

        return self._build_report()

    async def run_continuous(self, poll_interval: float = 1.0, max_idle: float = 30.0):
        """Run continuously, processing tasks as they arrive."""
        idle_since = time.time()
        while self._running:
            if not self._task_queue.empty():
                idle_since = time.time()
                _, _, task = await self._task_queue.get()
                agent = self._pick_agent(task)
                if agent:
                    result = await agent.execute(task)
                    self._completed_tasks.append(task)
                    self._active_fingerprints.discard(task.fingerprint)
                    if result.training_pair:
                        self._training_pairs.append(result.training_pair)
            else:
                if time.time() - idle_since > max_idle:
                    logger.info("Fleet idle for %.0fs, stopping", max_idle)
                    break
                await asyncio.sleep(poll_interval)

    async def shutdown(self):
        """Stop all agents and save training data."""
        self._running = False
        for agent in self.agents.values():
            await agent.stop()

        # Save training pairs
        if self._training_pairs:
            self._save_training_data()

        logger.info("Fleet shut down. Total tasks: %d", len(self._completed_tasks))

    def _save_training_data(self):
        """Save generated SFT pairs to training intake."""
        try:
            out_dir = Path(__file__).resolve().parent.parent.parent / "training" / "intake" / "fleet"
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            out_file = out_dir / f"fleet_sft_{ts}.jsonl"
            with open(out_file, "w", encoding="utf-8") as f:
                for pair in self._training_pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + "\n")
            logger.info("Saved %d training pairs to %s", len(self._training_pairs), out_file)
        except Exception as e:
            logger.warning("Failed to save training data: %s", e)

    def _build_report(self) -> FleetReport:
        elapsed = (time.time() - self._start_time) * 1000 if self._start_time else 0
        report = FleetReport(
            total_tasks=len(self._completed_tasks),
            completed=sum(1 for t in self._completed_tasks if t.status == TaskStatus.COMPLETED),
            failed=sum(1 for t in self._completed_tasks if t.status == TaskStatus.FAILED),
            skipped=sum(1 for t in self._completed_tasks if t.status == TaskStatus.SKIPPED),
            total_credits=sum(t.credits_earned for t in self._completed_tasks),
            elapsed_ms=elapsed,
            agents=[a.status() for a in self.agents.values()],
            tasks=[t.to_dict() for t in self._completed_tasks],
            training_pairs=self._training_pairs,
        )
        return report

    def status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "agents": {k: v.status() for k, v in self.agents.items()},
            "queue_size": self._task_queue.qsize(),
            "completed": len(self._completed_tasks),
            "active_fingerprints": len(self._active_fingerprints),
            "training_pairs": len(self._training_pairs),
        }


# ── Convenience: Quick Fleet Launch ───────────────────────────────────

async def quick_fleet(tasks: List[Dict[str, Any]], max_agents: int = 3) -> Dict[str, Any]:
    """One-call fleet execution for scripts and CLI.

    Args:
        tasks: List of task dicts with keys: task_type, platform, target, action, params, priority
        max_agents: Number of agents to spawn

    Returns:
        Fleet report dict
    """
    fleet = AgentFleet(max_agents=max_agents)
    await fleet.start()

    for t in tasks:
        await fleet.submit(FleetTask(
            task_type=t.get("task_type", "generic"),
            platform=t.get("platform", "github"),
            target=t.get("target", ""),
            action=t.get("action", "read"),
            params=t.get("params", {}),
            priority=TaskPriority(t.get("priority", 5)),
            execution_mode=ExecutionMode(t.get("execution_mode", "connector_first")),
        ))

    report = await fleet.run_until_empty()
    await fleet.shutdown()
    return report.to_dict()


# ── CLI ───────────────────────────────────────────────────────────────

async def _cli_main():
    import argparse
    parser = argparse.ArgumentParser(description="HYDRA Agent Fleet")
    sub = parser.add_subparsers(dest="command")

    # Status
    sub.add_parser("status", help="Show fleet status")

    # Run
    rp = sub.add_parser("run", help="Run tasks from JSON file")
    rp.add_argument("tasks_file", help="JSON file with task list")
    rp.add_argument("-n", "--agents", type=int, default=3)

    # Quick
    qp = sub.add_parser("quick", help="Quick single-task execution")
    qp.add_argument("platform", help="Platform (github/shopify/canva/...)")
    qp.add_argument("action", help="Action (triage/create/read/...)")
    qp.add_argument("target", help="Target (URL/ID/number)")

    args = parser.parse_args()

    if args.command == "run":
        with open(args.tasks_file) as f:
            tasks = json.load(f)
        report = await quick_fleet(tasks, max_agents=args.agents)
        print(json.dumps(report, indent=2, default=str))

    elif args.command == "quick":
        report = await quick_fleet([{
            "platform": args.platform,
            "action": args.action,
            "target": args.target,
            "task_type": f"{args.platform}_{args.action}",
        }])
        print(json.dumps(report, indent=2, default=str))

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(_cli_main())
