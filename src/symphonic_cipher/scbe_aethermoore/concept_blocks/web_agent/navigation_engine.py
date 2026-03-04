"""
SCBE Web Agent — NavigationEngine
===================================

Combines concept blocks for autonomous web navigation:
- PLAN  (A* over URL graph) → route planning
- SENSE (Kalman filter)     → page state estimation
- STEER (PID controller)    → error correction / drift prevention
- DECIDE (behaviour tree)   → action selection at each step

The engine treats the web as a directed graph where:
- Nodes = pages (identified by URL + semantic fingerprint)
- Edges = navigation actions (click, form submit, URL entry)
- Cost = governance-weighted difficulty

Integrates personality kernel from CSTM for navigation style.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from ..plan import PlanBlock, a_star_search
from ..sense import SenseBlock
from ..steer import SteerBlock
from ..decide import DecideBlock, Action, Condition, Sequence, Selector, Blackboard
from ..base import BlockStatus

from .semantic_antivirus import SemanticAntivirus
from .web_polly_pad import (
    ActionType, BrowserAction, WebPollyPad, RecoveryStrategy,
)


# ---------------------------------------------------------------------------
#  Page understanding
# ---------------------------------------------------------------------------

@dataclass
class PageUnderstanding:
    """Semantic understanding of a web page."""

    url: str
    title: str = ""
    text_summary: str = ""          # First N chars of visible text
    links: List[Dict[str, str]] = field(default_factory=list)  # [{text, href}]
    forms: List[Dict[str, Any]] = field(default_factory=list)  # [{action, fields}]
    buttons: List[str] = field(default_factory=list)
    page_type: str = "unknown"      # search, article, form, login, error, results
    content_length: int = 0
    fingerprint: str = ""           # Hash of key content for change detection

    @staticmethod
    def from_content(url: str, title: str, text: str, links: List[Dict[str, str]]) -> "PageUnderstanding":
        fp = hashlib.md5((url + title + text[:500]).encode()).hexdigest()[:12]
        page_type = _classify_page(url, title, text)
        return PageUnderstanding(
            url=url,
            title=title,
            text_summary=text[:1000],
            links=links[:100],
            page_type=page_type,
            content_length=len(text),
            fingerprint=fp,
        )


def _classify_page(url: str, title: str, text: str) -> str:
    """Heuristic page type classification."""
    low_url = url.lower()
    low_title = (title or "").lower()
    low_text = (text or "").lower()[:500]

    if "login" in low_url or "signin" in low_url or "login" in low_title:
        return "login"
    if "search" in low_url or "query" in low_url:
        return "search"
    if "error" in low_title or "404" in low_title or "not found" in low_title:
        return "error"
    if "results" in low_url:
        return "results"
    if len(text or "") > 2000:
        return "article"
    return "unknown"


# ---------------------------------------------------------------------------
#  URL graph adapter for A* planning
# ---------------------------------------------------------------------------

class URLGraph:
    """URL graph for A* path planning (standalone, not extending ABC)."""

    def __init__(self) -> None:
        self._edges: Dict[str, List[Tuple[str, float]]] = {}
        self._page_data: Dict[str, PageUnderstanding] = {}

    def add_page(self, page: PageUnderstanding) -> None:
        self._page_data[page.url] = page
        if page.url not in self._edges:
            self._edges[page.url] = []
        for link in page.links:
            href = link.get("href", "")
            if href and href.startswith("http"):
                cost = 1.0
                self._edges[page.url].append((href, cost))
                if href not in self._edges:
                    self._edges[href] = []

    def neighbours(self, node: str) -> List[str]:
        return [target for target, _ in self._edges.get(node, [])]

    def cost(self, current: str, neighbour: str) -> float:
        for target, c in self._edges.get(current, []):
            if target == neighbour:
                return c
        return 1.0

    def heuristic(self, node: str, goal: str) -> float:
        """URL similarity heuristic — shared path segments reduce cost."""
        if node == goal:
            return 0.0
        n_parts = node.rstrip("/").split("/")
        g_parts = goal.rstrip("/").split("/")
        shared = sum(1 for a, b in zip(n_parts, g_parts) if a == b)
        return max(0, len(g_parts) - shared)


# ---------------------------------------------------------------------------
#  NavigationState
# ---------------------------------------------------------------------------

@dataclass
class NavigationState:
    """Current state of the navigation engine."""

    current_url: str = ""
    current_page: Optional[PageUnderstanding] = None
    goal_url: Optional[str] = None
    goal_description: str = ""
    planned_route: List[str] = field(default_factory=list)
    route_index: int = 0
    steps_taken: int = 0
    max_steps: int = 100
    errors_total: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def is_at_goal(self) -> bool:
        if self.goal_url and self.current_url:
            return self.current_url.rstrip("/") == self.goal_url.rstrip("/")
        return False

    @property
    def is_over_budget(self) -> bool:
        return self.steps_taken >= self.max_steps

    @property
    def progress(self) -> float:
        if not self.planned_route:
            return 0.0
        return min(1.0, self.route_index / max(len(self.planned_route), 1))


# ---------------------------------------------------------------------------
#  NavigationEngine
# ---------------------------------------------------------------------------

class NavigationEngine:
    """
    Autonomous web navigation using SCBE concept blocks.

    Workflow per step:
    1. SENSE: Understand current page (Kalman-filtered state estimate)
    2. PLAN: Route to goal (A* over URL graph)
    3. DECIDE: Select best action (behaviour tree)
    4. STEER: Correct drift from planned route (PID)
    5. Execute via WebPollyPad (governance-gated)
    """

    def __init__(
        self,
        polly_pad: Optional[WebPollyPad] = None,
        antivirus: Optional[SemanticAntivirus] = None,
        personality: Optional[List[float]] = None,
    ) -> None:
        self._pad = polly_pad or WebPollyPad()
        self._antivirus = antivirus or self._pad._antivirus

        # Concept blocks
        self._sense = SenseBlock(dim=1, process_noise=0.01, measurement_noise=0.1)
        self._steer = SteerBlock(kp=0.8, ki=0.2, kd=0.05)
        self._plan = PlanBlock()

        # URL graph built as we navigate
        self._url_graph = URLGraph()

        # Navigation state
        self._state = NavigationState()

        # Personality bias (from CSTM kernel)
        self._personality = personality  # 21D vector or None

    def set_goal(self, goal_url: Optional[str] = None, goal_description: str = "") -> None:
        """Set navigation goal."""
        self._state.goal_url = goal_url
        self._state.goal_description = goal_description

    def observe_page(self, page: PageUnderstanding) -> None:
        """Feed current page observation into the engine."""
        self._state.current_url = page.url
        self._state.current_page = page
        self._url_graph.add_page(page)

    def next_action(self) -> Optional[BrowserAction]:
        """
        Compute the next browser action using concept blocks.

        Returns None if goal reached or budget exhausted.
        """
        if self._state.is_at_goal:
            return None
        if self._state.is_over_budget:
            return None
        if self._state.current_page is None:
            return None

        page = self._state.current_page

        # SENSE: estimate where we are relative to goal
        progress = self._estimate_progress()

        # PLAN: find route if we don't have one or we've drifted
        if not self._state.planned_route or self._is_off_route():
            self._replan()

        # STEER: compute correction signal
        error = self._compute_error()
        steer_result = self._steer.tick({"error": error})
        correction = steer_result.output.get("correction", 0.0)

        # DECIDE: pick the best action
        action = self._select_action(page, correction)

        if action:
            # Gate through Polly Pad
            action, decision = self._pad.prepare_action(action)
            if decision == "DENY":
                # Try alternative
                action = self._fallback_action(page)
                if action:
                    action, decision = self._pad.prepare_action(action)

            self._state.steps_taken += 1

        return action

    def handle_result(self, success: bool, error: Optional[str] = None) -> Optional[RecoveryStrategy]:
        """Process the result of executing an action."""
        from .web_polly_pad import ActionResult
        if self._state.current_page is None:
            return None

        result = ActionResult(
            success=success,
            action=BrowserAction(action_type=ActionType.NAVIGATE),
            error=error,
        )

        if not success:
            self._state.errors_total += 1

        return self._pad.record_result(result)

    # -- internal helpers ----------------------------------------------------

    def _estimate_progress(self) -> float:
        """Use SENSE block to estimate navigation progress."""
        if not self._state.planned_route:
            return 0.0
        raw_progress = self._state.route_index / max(len(self._state.planned_route), 1)
        # Feed through Kalman filter for smooth estimate
        sense_result = self._sense.tick({
            "measurement": raw_progress,
            "process_noise": 0.01,
            "measurement_noise": 0.1,
        })
        return sense_result.output.get("estimate", raw_progress)

    def _replan(self) -> None:
        """Recompute route using BFS over the URL graph."""
        if not self._state.goal_url or not self._state.current_url:
            return

        # Simple BFS since URLGraph is dynamically built
        from collections import deque
        start = self._state.current_url
        goal = self._state.goal_url
        if start == goal:
            self._state.planned_route = [start]
            self._state.route_index = 0
            return

        visited = {start}
        queue: deque = deque([[start]])
        while queue:
            path = queue.popleft()
            for neighbor in self._url_graph.neighbours(path[-1]):
                if neighbor == goal:
                    self._state.planned_route = path + [neighbor]
                    self._state.route_index = 0
                    return
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])

        # No path found — try direct navigation
        self._state.planned_route = [goal]
        self._state.route_index = 0

    def _is_off_route(self) -> bool:
        """Check if current URL deviates from planned route."""
        if not self._state.planned_route:
            return True
        if self._state.route_index >= len(self._state.planned_route):
            return True
        expected = self._state.planned_route[self._state.route_index]
        return self._state.current_url != expected

    def _compute_error(self) -> float:
        """Error signal: how far off-route we are."""
        if self._state.is_at_goal:
            return 0.0
        if not self._state.planned_route:
            return 1.0
        remaining = len(self._state.planned_route) - self._state.route_index
        total = max(len(self._state.planned_route), 1)
        return remaining / total

    def _select_action(self, page: PageUnderstanding, correction: float) -> Optional[BrowserAction]:
        """Select the best action based on current state."""
        # If we have a planned route, follow it
        if self._state.planned_route and self._state.route_index < len(self._state.planned_route):
            next_url = self._state.planned_route[self._state.route_index]
            self._state.route_index += 1

            # Find matching link on current page
            for link in page.links:
                if link.get("href", "").rstrip("/") == next_url.rstrip("/"):
                    return BrowserAction(
                        action_type=ActionType.CLICK,
                        target=link.get("selector", link.get("text", "")),
                        metadata={"planned_url": next_url},
                    )

            # No matching link — navigate directly
            return BrowserAction(
                action_type=ActionType.NAVIGATE,
                target=next_url,
            )

        # No plan — pick best link heuristically
        if page.links and self._state.goal_url:
            best_link = self._rank_links(page.links, self._state.goal_url)
            if best_link:
                return BrowserAction(
                    action_type=ActionType.CLICK,
                    target=best_link.get("text", best_link.get("href", "")),
                    metadata={"href": best_link.get("href")},
                )

        # Goal is a URL we can navigate to directly
        if self._state.goal_url:
            return BrowserAction(
                action_type=ActionType.NAVIGATE,
                target=self._state.goal_url,
            )

        return None

    def _fallback_action(self, page: PageUnderstanding) -> Optional[BrowserAction]:
        """Generate a fallback action when primary is denied."""
        return BrowserAction(action_type=ActionType.BACK)

    def _rank_links(self, links: List[Dict[str, str]], goal: str) -> Optional[Dict[str, str]]:
        """Rank page links by similarity to goal URL."""
        if not links:
            return None

        goal_parts = set(goal.lower().replace("/", " ").split())
        best_score = -1
        best_link = None

        for link in links:
            href = link.get("href", "")
            text = link.get("text", "")
            link_parts = set((href + " " + text).lower().replace("/", " ").split())
            overlap = len(goal_parts & link_parts)
            if overlap > best_score:
                best_score = overlap
                best_link = link

        return best_link if best_score > 0 else None

    # -- status API ----------------------------------------------------------

    @property
    def state(self) -> NavigationState:
        return self._state

    def summary(self) -> Dict[str, Any]:
        return {
            "current_url": self._state.current_url,
            "goal_url": self._state.goal_url,
            "steps_taken": self._state.steps_taken,
            "progress": self._state.progress,
            "at_goal": self._state.is_at_goal,
            "over_budget": self._state.is_over_budget,
            "planned_route_length": len(self._state.planned_route),
            "errors": self._state.errors_total,
            "pad_summary": self._pad.summary(),
        }

    def reset(self) -> None:
        self._state = NavigationState()
        self._url_graph = URLGraph()
        self._pad.reset()
        self._sense.reset()
        self._steer.reset()
