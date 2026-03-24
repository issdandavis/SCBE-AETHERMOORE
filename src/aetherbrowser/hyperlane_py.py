"""
HyperLane Governance — Python Port
====================================

Ported from src/browser/hyperlane.ts. Classifies URLs into GREEN/YELLOW/RED
zones and makes ALLOW/DENY/QUARANTINE decisions per request.

GREEN  = trusted (GitHub, HuggingFace, Notion, localhost) -> auto-allow
YELLOW = semi-trusted (AI APIs, social) -> quarantine writes for user approval
RED    = unknown/financial -> quarantine everything for user approval
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


class Zone(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    QUARANTINE = "QUARANTINE"


@dataclass
class HyperLaneResult:
    decision: Decision
    zone: Zone
    reason: str
    latency_ms: float = 0.0


_GREEN_DOMAINS = [
    "github.com",
    "api.github.com",
    "huggingface.co",
    "hf.co",
    "api.notion.com",
    "notion.so",
    "localhost",
    "127.0.0.1",
    "airtable.com",
    "api.airtable.com",
    "dropbox.com",
    "api.dropboxapi.com",
]

_YELLOW_DOMAINS = [
    "api.anthropic.com",
    "api.openai.com",
    "generativelanguage.googleapis.com",
    "api.x.ai",
    "api.twitter.com",
    "api.x.com",
    "api.linkedin.com",
    "slack.com",
    "api.slack.com",
    "discord.com",
    "discord.gg",
]

_RED_DOMAINS = [
    "api.stripe.com",
    "paypal.com",
    "api.paypal.com",
    "plaid.com",
]


class HyperLanePy:
    def __init__(self, rate_limit_per_min: int = 60):
        self._rate_limit = rate_limit_per_min
        self._request_log: dict[str, list[float]] = defaultdict(list)
        self._custom_domains: dict[str, Zone] = {}

    def add_domain(self, domain: str, zone: Zone) -> None:
        self._custom_domains[domain] = zone

    def classify_zone(self, url: str) -> Zone:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        for domain, zone in self._custom_domains.items():
            if host == domain or host.endswith("." + domain):
                return zone
        for domain in _GREEN_DOMAINS:
            if host == domain or host.endswith("." + domain):
                return Zone.GREEN
        for domain in _YELLOW_DOMAINS:
            if host == domain or host.endswith("." + domain):
                return Zone.YELLOW
        for domain in _RED_DOMAINS:
            if host == domain or host.endswith("." + domain):
                return Zone.RED
        return Zone.RED

    def _check_rate_limit(self, agent_id: str) -> bool:
        now = time.monotonic()
        window = self._request_log[agent_id]
        self._request_log[agent_id] = [t for t in window if now - t < 60.0]
        return len(self._request_log[agent_id]) < self._rate_limit

    def evaluate(self, url: str, *, action: str, agent_id: str) -> HyperLaneResult:
        start = time.monotonic()
        zone = self.classify_zone(url)
        if not self._check_rate_limit(agent_id):
            return HyperLaneResult(
                decision=Decision.DENY,
                zone=zone,
                reason=f"Rate limit exceeded for agent {agent_id}",
                latency_ms=(time.monotonic() - start) * 1000,
            )
        self._request_log[agent_id].append(time.monotonic())
        if zone == Zone.GREEN:
            decision = Decision.ALLOW
            reason = f"GREEN zone: {action} allowed"
        elif zone == Zone.YELLOW:
            if action in ("read", "search"):
                decision = Decision.ALLOW
                reason = f"YELLOW zone: {action} auto-allowed (read-only)"
            else:
                decision = Decision.QUARANTINE
                reason = f"YELLOW zone: {action} requires user approval"
        else:
            decision = Decision.QUARANTINE
            reason = "RED zone: all actions require user approval"
        return HyperLaneResult(
            decision=decision,
            zone=zone,
            reason=reason,
            latency_ms=(time.monotonic() - start) * 1000,
        )
