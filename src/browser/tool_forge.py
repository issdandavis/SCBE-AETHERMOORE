# src/browser/tool_forge.py
"""Auto-generate browser tools from failure patterns."""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from src.browser.navigation_randomtest import NavCoverageReport


@dataclass
class BrowserTool:
    tool_id: str = ""
    domain: str = ""
    trigger: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""
    created_by: str = "forge"
    success_rate: float = 0.0
    ttl_hours: int = 72

    def to_dict(self) -> dict:
        return asdict(self)


class ToolForge:
    _counter: int = 0

    def from_failure(
        self,
        domain: str,
        failure_url: str,
        failure_reason: str = "",
        surrounding_links: List[str] = None,
        ttl_hours: int = 72,
    ) -> BrowserTool:
        ToolForge._counter += 1
        trigger = f"Navigate to {failure_url} fails: {failure_reason}"
        steps = []

        if "auth" in failure_reason.lower() or "login" in failure_url.lower():
            steps = [
                {"action": "detect", "target": "login form"},
                {"action": "fill_credentials", "target": failure_url},
                {"action": "submit", "target": "login form"},
                {"action": "retry_navigation", "target": failure_url},
            ]
        elif "404" in failure_reason or "not found" in failure_reason.lower():
            steps = [
                {"action": "try_alternatives", "urls": surrounding_links or []},
                {"action": "search_site", "query": failure_url.split("/")[-1]},
            ]
        elif "timeout" in failure_reason.lower():
            steps = [
                {"action": "wait", "ms": 5000},
                {"action": "retry", "target": failure_url, "max_retries": 3},
            ]
        else:
            steps = [
                {"action": "screenshot", "target": failure_url},
                {"action": "log_failure", "reason": failure_reason},
                {"action": "try_alternatives", "urls": surrounding_links or []},
            ]

        return BrowserTool(
            tool_id=f"forged-{domain.replace('.', '-')}-{ToolForge._counter}",
            domain=domain,
            trigger=trigger,
            steps=steps,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            ttl_hours=ttl_hours,
        )

    def from_report(self, domain: str, report: NavCoverageReport) -> List[BrowserTool]:
        tools = []
        for fp in report.failure_points:
            tools.append(self.from_failure(domain=domain, failure_url=fp, failure_reason="navigation failure"))
        for de in report.dead_ends:
            if de not in report.failure_points:
                tools.append(self.from_failure(domain=domain, failure_url=de, failure_reason="dead end"))
        return tools
