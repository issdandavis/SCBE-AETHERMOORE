"""
TriLane Browser Router
======================

3-lane browser service for SCBE-AETHERMOORE.

Lane 1 (HEADLESS):  CDP/Playwright — fast, parallel, no UI
Lane 2 (MCP):       Claude-in-Chrome / YouTube MCP — interactive, real tabs
Lane 3 (VISUAL):    Screenshot + multimodal analysis — "see" the page

The router picks the best lane(s) per task, governed by OctoArmor + SCBE pipeline.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from src.aetherbrowser.router import OctoArmorRouter


class BrowserLane(str, Enum):
    HEADLESS = "headless"  # CDP/Playwright — bulk, parallel, fast
    MCP = "mcp"  # Claude-in-Chrome — interactive, real tabs
    VISUAL = "visual"  # Screenshot + multimodal — "see" the page
    COMBINED = "combined"  # Multiple lanes for complex tasks


class TaskIntent(str, Enum):
    SCRAPE = "scrape"  # Extract data from pages
    RESEARCH = "research"  # Search + read + summarize
    INTERACT = "interact"  # Fill forms, click, navigate
    VERIFY = "verify"  # Check if something looks right
    POST = "post"  # Publish content somewhere
    MONITOR = "monitor"  # Watch for changes
    TRAIN = "train"  # Capture interactions for model training


# Lane selection rules
_HEADLESS_INTENTS = {TaskIntent.SCRAPE, TaskIntent.MONITOR}
_MCP_INTENTS = {TaskIntent.INTERACT, TaskIntent.POST}
_VISUAL_INTENTS = {TaskIntent.VERIFY}
_COMBINED_INTENTS = {TaskIntent.RESEARCH, TaskIntent.TRAIN}

# Keywords for intent detection
_SCRAPE_KEYWORDS = {"scrape", "extract", "crawl", "harvest", "pull", "fetch", "download", "bulk", "parallel", "batch"}
_INTERACT_KEYWORDS = {"click", "fill", "type", "submit", "login", "form", "navigate", "open", "tab", "upload"}
_VERIFY_KEYWORDS = {"check", "verify", "look", "screenshot", "visual", "inspect", "compare", "review"}
_POST_KEYWORDS = {"post", "publish", "tweet", "comment", "send", "upload", "share", "announce"}
_MONITOR_KEYWORDS = {"watch", "monitor", "poll", "track", "alert", "notify", "wait for"}
_RESEARCH_KEYWORDS = {"research", "search", "find", "discover", "analyze", "summarize", "learn", "read"}
_TRAIN_KEYWORDS = {"train", "learn", "shadow", "capture", "record", "log", "sft", "dataset"}


@dataclass
class LaneResult:
    """Result from a single lane execution."""

    lane: BrowserLane
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0
    actions_taken: int = 0
    governance_decisions: dict[str, int] = field(default_factory=dict)


@dataclass
class TriLaneResult:
    """Combined result from all lanes used."""

    task: str
    intent: TaskIntent
    lanes_used: list[BrowserLane]
    plan: Optional[dict[str, Any]] = None
    results: list[LaneResult] = field(default_factory=list)
    shadow_sft: Optional[dict[str, Any]] = None  # SFT pair for model training
    total_duration_ms: float = 0

    @property
    def success(self) -> bool:
        return any(r.success for r in self.results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "intent": self.intent.value,
            "lanes_used": [l.value for l in self.lanes_used],
            "success": self.success,
            "plan": self.plan,
            "results": [
                {
                    "lane": r.lane.value,
                    "success": r.success,
                    "data": r.data,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                    "actions_taken": r.actions_taken,
                    "governance": r.governance_decisions,
                }
                for r in self.results
            ],
            "shadow_sft": self.shadow_sft,
            "total_duration_ms": self.total_duration_ms,
        }


class TriLaneRouter:
    """
    Routes browser tasks to the best lane(s).

    Usage:
        router = TriLaneRouter()
        result = await router.execute("scrape the top 10 arXiv papers on AI safety")
        print(result.to_dict())
    """

    def __init__(
        self,
        *,
        headless_backend: str = "cdp",  # "cdp" or "playwright"
        mcp_backend: str = "chrome",  # "chrome" or "playwright-mcp"
        enable_shadow_training: bool = True,
        shadow_model_id: str = "issdandavis/scbe-unified-governance",
        local_first: bool = True,
    ):
        self._headless_backend = headless_backend
        self._mcp_backend = mcp_backend
        self._shadow_training = enable_shadow_training
        self._shadow_model = shadow_model_id
        self._router = OctoArmorRouter(local_first=local_first)
        # Lazy-load squad only when needed (requires WsFeed for live sessions)
        self._squad = None
        self._action_log: list[TriLaneResult] = []

    def classify_intent(self, text: str) -> TaskIntent:
        """Determine what the user wants to do."""
        tokens = set(re.findall(r"[a-z0-9]+", text.lower()))

        # Score each intent
        scores = {
            TaskIntent.SCRAPE: len(tokens & _SCRAPE_KEYWORDS),
            TaskIntent.INTERACT: len(tokens & _INTERACT_KEYWORDS),
            TaskIntent.VERIFY: len(tokens & _VERIFY_KEYWORDS),
            TaskIntent.POST: len(tokens & _POST_KEYWORDS),
            TaskIntent.MONITOR: len(tokens & _MONITOR_KEYWORDS),
            TaskIntent.RESEARCH: len(tokens & _RESEARCH_KEYWORDS),
            TaskIntent.TRAIN: len(tokens & _TRAIN_KEYWORDS),
        }

        # URL patterns suggest specific intents
        if re.search(r"https?://", text):
            if scores[TaskIntent.INTERACT] == 0 and scores[TaskIntent.POST] == 0:
                scores[TaskIntent.SCRAPE] += 1

        # "50 pages" or "all of" suggests bulk → headless
        if re.search(r"\b\d{2,}\b", text) or "all of" in text.lower():
            scores[TaskIntent.SCRAPE] += 2

        best = max(scores, key=lambda k: scores[k])
        if scores[best] == 0:
            return TaskIntent.RESEARCH  # Default
        return best

    def select_lanes(self, intent: TaskIntent, text: str) -> list[BrowserLane]:
        """Pick which lane(s) to use for this task."""
        if intent in _HEADLESS_INTENTS:
            return [BrowserLane.HEADLESS]
        if intent in _MCP_INTENTS:
            return [BrowserLane.MCP]
        if intent in _VISUAL_INTENTS:
            return [BrowserLane.VISUAL]
        if intent in _COMBINED_INTENTS:
            # Research: headless for data gathering, visual for verification
            # Train: MCP for interaction capture, visual for screenshots
            if intent == TaskIntent.RESEARCH:
                return [BrowserLane.HEADLESS, BrowserLane.VISUAL]
            return [BrowserLane.MCP, BrowserLane.VISUAL]
        return [BrowserLane.MCP]  # Safe default

    async def execute(self, text: str) -> TriLaneResult:
        """Route and execute a browser task across the best lane(s)."""
        start = time.monotonic()
        intent = self.classify_intent(text)
        lanes = self.select_lanes(intent, text)

        # Build governance plan
        plan_dict = None
        plan_obj = None
        try:
            from src.aetherbrowser.command_planner import build_command_plan
            from src.aetherbrowser.agents import AgentSquad
            from src.aetherbrowser.ws_feed import WsFeed

            if self._squad is None:
                feed = WsFeed()
                self._squad = AgentSquad(feed)
            plan_obj = build_command_plan(
                text=text,
                squad=self._squad,
                router=self._router,
            )
            plan_dict = plan_obj.to_dict()
        except Exception:
            # Governance plan is optional — router still works without it
            plan_dict = {
                "text": text,
                "intent": intent.value,
                "risk_tier": "unknown",
                "targets": [],
                "approval_required": False,
                "review_zone": None,
                "next_actions": [],
            }

        result = TriLaneResult(
            task=text,
            intent=intent,
            lanes_used=lanes,
            plan=plan_dict,
        )

        # Execute each lane
        for lane in lanes:
            lane_start = time.monotonic()
            try:
                if lane == BrowserLane.HEADLESS:
                    lr = await self._execute_headless(text, plan_dict)
                elif lane == BrowserLane.MCP:
                    lr = await self._execute_mcp(text, plan_dict)
                elif lane == BrowserLane.VISUAL:
                    lr = await self._execute_visual(text, plan_dict)
                else:
                    lr = LaneResult(lane=lane, success=False, error="Unknown lane")
            except Exception as e:
                lr = LaneResult(lane=lane, success=False, error=str(e))

            lr.duration_ms = (time.monotonic() - lane_start) * 1000
            result.results.append(lr)

        result.total_duration_ms = (time.monotonic() - start) * 1000

        # Generate shadow training SFT pair
        if self._shadow_training:
            result.shadow_sft = self._build_sft_pair(result)

        self._action_log.append(result)
        return result

    async def _execute_headless(self, text: str, plan: dict[str, Any]) -> LaneResult:
        """Lane 1: Headless execution via CDP or Playwright."""
        # Import the appropriate backend
        if self._headless_backend == "cdp":
            from agents.browsers.cdp_backend import CDPBackend

            backend = CDPBackend()
        else:
            from agents.browsers.playwright_backend import PlaywrightBackend

            backend = PlaywrightBackend()

        targets = plan.get("targets", []) or []
        result_data: dict[str, Any] = {
            "backend": self._headless_backend,
            "targets": targets,
            "plan_risk": plan.get("risk_tier", "unknown"),
        }

        try:
            await backend.initialize()
            actions = 0

            # Execute based on plan
            for target in targets:
                url = f"https://{target}" if not target.startswith("http") else target
                await backend.navigate(url)
                actions += 1
                content = await backend.get_page_content()
                result_data[target] = {
                    "url": url,
                    "content_length": len(content) if isinstance(content, str) else 0,
                    "status": "ok",
                }

            if not targets:
                result_data["note"] = "No targets extracted from task. Provide URLs or service names."

            await backend.close()
            return LaneResult(
                lane=BrowserLane.HEADLESS,
                success=True,
                data=result_data,
                actions_taken=actions,
            )
        except Exception as e:
            return LaneResult(
                lane=BrowserLane.HEADLESS,
                success=False,
                data=result_data,
                error=str(e),
            )

    async def _execute_mcp(self, text: str, plan: dict[str, Any]) -> LaneResult:
        """Lane 2: MCP execution via Claude-in-Chrome or Playwright MCP.

        This lane delegates to the MCP tool layer — it doesn't drive the browser
        directly. Instead, it returns instructions for the calling agent to execute
        via MCP tool calls.
        """
        result_data: dict[str, Any] = {
            "backend": self._mcp_backend,
            "plan_risk": plan.get("risk_tier", "unknown"),
            "approval_required": plan.get("approval_required", False),
        }

        # Build MCP action sequence from plan
        next_actions = plan.get("next_actions", [])
        mcp_actions = []
        for action in next_actions:
            if isinstance(action, dict):
                mcp_actions.append(action)
            else:
                mcp_actions.append(
                    {
                        "label": getattr(action, "label", str(action)),
                        "risk_tier": getattr(action, "risk_tier", "unknown"),
                        "requires_approval": getattr(action, "requires_approval", False),
                        "command_hint": getattr(action, "command_hint", None),
                    }
                )

        result_data["mcp_actions"] = mcp_actions
        result_data["targets"] = plan.get("targets", [])
        result_data["intent"] = plan.get("intent", "unknown")
        result_data["review_zone"] = plan.get("review_zone")

        return LaneResult(
            lane=BrowserLane.MCP,
            success=True,
            data=result_data,
            actions_taken=len(mcp_actions),
        )

    async def _execute_visual(self, text: str, plan: dict[str, Any]) -> LaneResult:
        """Lane 3: Visual analysis via screenshot + multimodal.

        Takes a screenshot and returns it as base64 for the calling agent
        to analyze with its multimodal capabilities.
        """
        result_data: dict[str, Any] = {
            "plan_risk": plan.get("risk_tier", "unknown"),
        }

        try:
            # Use headless backend to capture screenshot
            if self._headless_backend == "cdp":
                from agents.browsers.cdp_backend import CDPBackend

                backend = CDPBackend()
            else:
                from agents.browsers.playwright_backend import PlaywrightBackend

                backend = PlaywrightBackend()

            targets = plan.get("targets", []) or []
            screenshots = {}

            await backend.initialize()
            for target in targets:
                url = f"https://{target}" if not target.startswith("http") else target
                await backend.navigate(url)
                shot = await backend.screenshot()
                if isinstance(shot, bytes):
                    screenshots[target] = {
                        "base64": base64.b64encode(shot).decode("utf-8"),
                        "size_bytes": len(shot),
                        "url": url,
                    }
            await backend.close()

            result_data["screenshots"] = {k: {"size": v["size_bytes"], "url": v["url"]} for k, v in screenshots.items()}
            result_data["screenshot_count"] = len(screenshots)

            return LaneResult(
                lane=BrowserLane.VISUAL,
                success=bool(screenshots),
                data=result_data,
                actions_taken=len(screenshots),
            )
        except Exception as e:
            return LaneResult(
                lane=BrowserLane.VISUAL,
                success=False,
                data=result_data,
                error=str(e),
            )

    def _build_sft_pair(self, result: TriLaneResult) -> dict[str, Any]:
        """Build an SFT training pair from this execution for shadow model training."""
        return {
            "instruction": result.task,
            "input": json.dumps(
                {
                    "intent": result.intent.value,
                    "lanes": [l.value for l in result.lanes_used],
                    "risk": result.plan.get("risk_tier") if result.plan else "unknown",
                    "targets": result.plan.get("targets", []) if result.plan else [],
                }
            ),
            "output": json.dumps(
                {
                    "success": result.success,
                    "lane_results": [
                        {"lane": r.lane.value, "success": r.success, "actions": r.actions_taken} for r in result.results
                    ],
                    "governance": result.plan.get("review_zone") if result.plan else None,
                }
            ),
            "label": f"browser_routing_{result.intent.value}",
            "model": self._shadow_model,
            "timestamp": time.time(),
        }

    def get_stats(self) -> dict[str, Any]:
        """Get router usage statistics."""
        total = len(self._action_log)
        if total == 0:
            return {"total_tasks": 0}

        intent_counts: dict[str, int] = {}
        lane_counts: dict[str, int] = {}
        success_count = 0

        for r in self._action_log:
            intent_counts[r.intent.value] = intent_counts.get(r.intent.value, 0) + 1
            for lane in r.lanes_used:
                lane_counts[lane.value] = lane_counts.get(lane.value, 0) + 1
            if r.success:
                success_count += 1

        return {
            "total_tasks": total,
            "success_rate": success_count / total,
            "intent_distribution": intent_counts,
            "lane_usage": lane_counts,
            "sft_pairs_generated": sum(1 for r in self._action_log if r.shadow_sft),
        }


# =============================================================================
# CLI Interface — the "kiosk" entry point
# =============================================================================


async def kiosk_mode():
    """Interactive kiosk mode — type commands, get browser actions."""
    router = TriLaneRouter()
    print("=" * 60)
    print("  SCBE AetherBrowser TriLane Kiosk")
    print("  Type a task, get governed browser actions.")
    print("  Commands: /stats, /lanes, /quit")
    print("=" * 60)

    while True:
        try:
            text = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not text:
            continue
        if text == "/quit":
            break
        if text == "/stats":
            print(json.dumps(router.get_stats(), indent=2))
            continue
        if text == "/lanes":
            for lane in BrowserLane:
                print(f"  {lane.value}: {lane.name}")
            continue

        # Classify and route
        intent = router.classify_intent(text)
        lanes = router.select_lanes(intent, text)
        print(f"\nIntent:  {intent.value}")
        print(f"Lanes:   {', '.join(l.value for l in lanes)}")

        # Execute
        result = await router.execute(text)
        print(f"\nSuccess: {result.success}")
        print(f"Time:    {result.total_duration_ms:.0f}ms")

        for lr in result.results:
            status = "OK" if lr.success else f"FAIL: {lr.error}"
            print(f"  [{lr.lane.value}] {status} ({lr.actions_taken} actions, {lr.duration_ms:.0f}ms)")

        if result.shadow_sft:
            print(f"  [SFT] Training pair captured for {router._shadow_model}")

    print("\nStats:", json.dumps(router.get_stats(), indent=2))


if __name__ == "__main__":
    asyncio.run(kiosk_mode())
