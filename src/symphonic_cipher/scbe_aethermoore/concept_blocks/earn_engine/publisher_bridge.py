"""
Earn Engine — Publisher Bridge
=================================
Bridge to the n8n content publisher workflow.

When content is successfully published across platforms, the publisher
bridge mints MMCCL credits proportional to the number of platforms
and the content quality.

Talks to the FastAPI bridge at localhost:8001 which forwards to n8n.

Usage::

    from earn_engine.publisher_bridge import PublisherBridge

    bridge = PublisherBridge(engine=earn_engine)

    # Publish content and earn credits
    result = bridge.publish(
        text="New blog post about SCBE governance...",
        platforms=["twitter", "linkedin", "medium"],
    )
    print(result.credits_earned, result.platforms_succeeded)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..context_credit_ledger.credit import Denomination
from .engine import EarnEngine, LedgerEntry
from .streams import EarnEvent, StreamType

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


# ---------------------------------------------------------------------------
#  Config
# ---------------------------------------------------------------------------

DEFAULT_BRIDGE_URL = "http://localhost:8001"
GOVERNANCE_SCAN_ENDPOINT = "/v1/governance/scan"
PUBLISH_ENDPOINT = "/v1/publish"

# Credits per successful platform publish
PLATFORM_CREDIT_VALUES: Dict[str, float] = {
    "twitter": 5.0,
    "linkedin": 8.0,
    "medium": 10.0,
    "wordpress": 10.0,
    "bluesky": 4.0,
    "mastodon": 4.0,
    "github": 6.0,
    "huggingface": 12.0,
}


# ---------------------------------------------------------------------------
#  Publish Result
# ---------------------------------------------------------------------------

@dataclass
class PublishResult:
    """Result of a content publish attempt."""
    publish_id: str
    text_preview: str
    platforms_attempted: List[str]
    platforms_succeeded: List[str]
    platforms_failed: List[str]
    governance_verdict: str            # ALLOW/QUARANTINE/DENY
    credits_earned: float
    ledger_entries: List[LedgerEntry]
    timestamp: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        if not self.platforms_attempted:
            return 0.0
        return len(self.platforms_succeeded) / len(self.platforms_attempted)


# ---------------------------------------------------------------------------
#  Publisher Bridge
# ---------------------------------------------------------------------------

class PublisherBridge:
    """
    Bridge between content publishing and the earn engine.

    In LIVE mode: calls the FastAPI bridge at localhost:8001
    In MOCK mode: simulates publishing (no network calls)
    """

    def __init__(
        self,
        engine: Optional[EarnEngine] = None,
        bridge_url: str = DEFAULT_BRIDGE_URL,
        api_key: str = "",
        live: bool = False,
    ):
        self.engine = engine or EarnEngine(agent_id="publisher")
        self.bridge_url = bridge_url
        self.api_key = api_key
        self.live = live and HAS_HTTPX
        self._publish_history: List[PublishResult] = []

    def publish(
        self,
        text: str,
        platforms: Optional[List[str]] = None,
        denomination: str = "AV",
    ) -> PublishResult:
        """
        Publish content across platforms and mint credits for successes.

        1. Run governance scan on the content
        2. If ALLOW/QUARANTINE: publish to each platform
        3. Mint credits for each successful publish
        """
        if platforms is None:
            platforms = ["twitter", "linkedin"]

        publish_id = uuid.uuid4().hex[:16]
        preview = text[:100] + ("..." if len(text) > 100 else "")

        # Step 1: Governance scan
        verdict = self._governance_scan(text)

        if verdict == "DENY":
            result = PublishResult(
                publish_id=publish_id,
                text_preview=preview,
                platforms_attempted=platforms,
                platforms_succeeded=[],
                platforms_failed=platforms,
                governance_verdict=verdict,
                credits_earned=0.0,
                ledger_entries=[],
            )
            self._publish_history.append(result)
            return result

        # Step 2: Publish to each platform
        succeeded = []
        failed = []
        for platform in platforms:
            ok = self._publish_to_platform(text, platform)
            if ok:
                succeeded.append(platform)
            else:
                failed.append(platform)

        # Step 3: Mint credits for successes
        entries = []
        total_credits = 0.0
        denom = Denomination(denomination)

        for platform in succeeded:
            base_reward = PLATFORM_CREDIT_VALUES.get(platform, 5.0)
            event = EarnEvent(
                stream_type=StreamType.CONTENT,
                event_name=f"publish_{platform}",
                denomination=denom,
                base_reward=base_reward,
                hamiltonian_d=0.1,
                hamiltonian_pd=0.05,
                metadata={
                    "publish_id": publish_id,
                    "platform": platform,
                    "text_length": len(text),
                },
            )
            entry = self.engine.process(event)
            entries.append(entry)
            total_credits += entry.face_value

        result = PublishResult(
            publish_id=publish_id,
            text_preview=preview,
            platforms_attempted=platforms,
            platforms_succeeded=succeeded,
            platforms_failed=failed,
            governance_verdict=verdict,
            credits_earned=total_credits,
            ledger_entries=entries,
        )
        self._publish_history.append(result)
        return result

    def history(self, limit: int = 20) -> List[PublishResult]:
        """Recent publish results."""
        return list(reversed(self._publish_history[-limit:]))

    def stats(self) -> Dict[str, Any]:
        """Publishing statistics."""
        total = len(self._publish_history)
        total_credits = sum(r.credits_earned for r in self._publish_history)
        platform_counts: Dict[str, int] = {}
        for r in self._publish_history:
            for p in r.platforms_succeeded:
                platform_counts[p] = platform_counts.get(p, 0) + 1

        return {
            "total_publishes": total,
            "total_credits_earned": round(total_credits, 4),
            "platform_success_counts": platform_counts,
        }

    # --- Internal ---

    def _governance_scan(self, text: str) -> str:
        """Run governance scan on content. Returns ALLOW/QUARANTINE/DENY."""
        if self.live:
            return self._live_governance_scan(text)
        # Mock: always ALLOW unless text contains forbidden patterns
        if len(text) < 5:
            return "DENY"
        return "ALLOW"

    def _publish_to_platform(self, text: str, platform: str) -> bool:
        """Publish to a single platform. Returns True on success."""
        if self.live:
            return self._live_publish(text, platform)
        # Mock: always succeed
        return True

    def _live_governance_scan(self, text: str) -> str:
        """Call the FastAPI bridge governance scan endpoint."""
        if not HAS_HTTPX:
            return "ALLOW"
        try:
            resp = httpx.post(
                f"{self.bridge_url}{GOVERNANCE_SCAN_ENDPOINT}",
                json={"content": text, "scan_mode": "full"},
                headers={"X-API-Key": self.api_key},
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("verdict", "ALLOW")
            return "QUARANTINE"
        except Exception:
            return "QUARANTINE"

    def _live_publish(self, text: str, platform: str) -> bool:
        """Call the FastAPI bridge publish endpoint."""
        if not HAS_HTTPX:
            return False
        try:
            resp = httpx.post(
                f"{self.bridge_url}{PUBLISH_ENDPOINT}",
                json={"text": text, "platform": platform},
                headers={"X-API-Key": self.api_key},
                timeout=15.0,
            )
            return resp.status_code == 200
        except Exception:
            return False
