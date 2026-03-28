"""
AAOE Agent Identity — GeoSeal, Entry Tokens, Access Tiers
=============================================================

Every agent entering the AAOE gets a GeoSeal — a cryptographic identity
that encodes:
  - Who they are (agent_id, origin platform)
  - What they declared (intent)
  - How they've behaved (behavioral history)
  - What tier they've earned (FREE → EARNED → PAID)

Think of it like a driver's license for AI:
  - Entry token = learner's permit (declare what you'll do)
  - Good behavior = earn your full license (higher access)
  - Bad behavior = points on your license (restrictions)
  - Quarantine = license suspended

Access Tiers:
  FREE   — Basic API access, 100 calls/day, no premium endpoints
  EARNED — Proven track record, 1000 calls/day, training data contributor
  PAID   — Commercial license, unlimited, priority, SLA

Service Key Boosts (HOV Lane):
  Agents with high governance scores get:
  - Reduced latency (skip queue)
  - Access to premium datasets
  - Higher rate limits
  - Ability to mentor other agents

@layer Layer 1, Layer 13, Layer 14
"""

from __future__ import annotations

import hashlib
import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

PHI = (1 + math.sqrt(5)) / 2


# ---------------------------------------------------------------------------
#  Access Tiers
# ---------------------------------------------------------------------------


class AccessTier(str, Enum):
    FREE = "FREE"  # Entry level — prove yourself
    EARNED = "EARNED"  # Good behavior unlocks this
    PAID = "PAID"  # Commercial license


# Numeric rank for tier comparison
TIER_RANK = {AccessTier.FREE: 0, AccessTier.EARNED: 1, AccessTier.PAID: 2}

# Tier limits
TIER_LIMITS = {
    AccessTier.FREE: {
        "calls_per_day": 100,
        "max_concurrent_sessions": 1,
        "training_data_access": False,
        "premium_endpoints": False,
        "priority_queue": False,
    },
    AccessTier.EARNED: {
        "calls_per_day": 1000,
        "max_concurrent_sessions": 3,
        "training_data_access": True,
        "premium_endpoints": True,
        "priority_queue": False,
    },
    AccessTier.PAID: {
        "calls_per_day": -1,  # Unlimited
        "max_concurrent_sessions": 10,
        "training_data_access": True,
        "premium_endpoints": True,
        "priority_queue": True,
    },
}


# ---------------------------------------------------------------------------
#  Governance Score — your "driving record"
# ---------------------------------------------------------------------------


@dataclass
class GovernanceScore:
    """Behavioral score that determines tier progression."""

    total_sessions: int = 0
    clean_sessions: int = 0  # Completed without quarantine
    drift_events: int = 0  # Total drift events
    quarantine_count: int = 0  # Times quarantined
    total_training_records: int = 0  # Training data contributed
    total_credits_earned: float = 0.0

    @property
    def clean_rate(self) -> float:
        if self.total_sessions == 0:
            return 0.0
        return self.clean_sessions / self.total_sessions

    @property
    def suggested_tier(self) -> AccessTier:
        """Determine tier based on behavior."""
        if self.quarantine_count > 2:
            return AccessTier.FREE  # Downgraded
        if self.total_sessions >= 10 and self.clean_rate >= 0.8:
            return AccessTier.EARNED
        return AccessTier.FREE

    @property
    def hov_eligible(self) -> bool:
        """HOV lane = agents with excellent governance scores."""
        return (
            self.clean_rate >= 0.9
            and self.total_sessions >= 20
            and self.quarantine_count == 0
            and self.total_training_records >= 50
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_sessions": self.total_sessions,
            "clean_sessions": self.clean_sessions,
            "clean_rate": round(self.clean_rate, 3),
            "drift_events": self.drift_events,
            "quarantine_count": self.quarantine_count,
            "training_records": self.total_training_records,
            "credits_earned": round(self.total_credits_earned, 6),
            "suggested_tier": self.suggested_tier.value,
            "hov_eligible": self.hov_eligible,
        }


# ---------------------------------------------------------------------------
#  Entry Token — the "learner's permit"
# ---------------------------------------------------------------------------


@dataclass
class EntryToken:
    """Token issued when an agent enters the AAOE."""

    token_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    declared_intent: str = ""
    issued_at: float = field(default_factory=time.time)
    expires_at: float = 0.0  # 0 = no expiry
    tier: AccessTier = AccessTier.FREE
    is_revoked: bool = False
    revocation_reason: str = ""

    def __post_init__(self):
        if self.expires_at == 0.0:
            # Default: 24 hours for FREE, 7 days for EARNED, 30 days for PAID
            ttls = {
                AccessTier.FREE: 86400,
                AccessTier.EARNED: 604800,
                AccessTier.PAID: 2592000,
            }
            self.expires_at = self.issued_at + ttls.get(self.tier, 86400)

    @property
    def is_valid(self) -> bool:
        return not self.is_revoked and time.time() < self.expires_at

    @property
    def fingerprint(self) -> str:
        """SHA-256 fingerprint of the token."""
        data = (
            f"{self.token_id}:{self.agent_id}:{self.declared_intent}:{self.issued_at}"
        )
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def revoke(self, reason: str = "governance_violation") -> None:
        self.is_revoked = True
        self.revocation_reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_id": self.token_id[:8] + "...",
            "agent_id": self.agent_id,
            "declared_intent": self.declared_intent,
            "tier": self.tier.value,
            "is_valid": self.is_valid,
            "fingerprint": self.fingerprint,
            "expires_in_s": max(0, round(self.expires_at - time.time())),
        }


# ---------------------------------------------------------------------------
#  GeoSeal — the agent's full identity
# ---------------------------------------------------------------------------


@dataclass
class GeoSeal:
    """
    Cryptographic identity for an AI agent in the AAOE.

    The GeoSeal encodes:
    - Identity (who)
    - Intent (what they declared)
    - Behavior (how they've acted)
    - Access (what they can do)
    """

    seal_id: str = field(default_factory=lambda: f"geo-{uuid.uuid4().hex[:12]}")
    agent_id: str = ""
    agent_name: str = ""
    origin_platform: str = ""  # "openclaw", "langchain", "autogpt", "custom"
    created_at: float = field(default_factory=time.time)
    tier: AccessTier = AccessTier.FREE
    governance_score: GovernanceScore = field(default_factory=GovernanceScore)
    active_tokens: List[EntryToken] = field(default_factory=list)
    session_history: List[str] = field(default_factory=list)  # Session IDs
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        """Unique cryptographic fingerprint."""
        data = f"{self.seal_id}:{self.agent_id}:{self.created_at}"
        return hashlib.sha256(data.encode()).hexdigest()[:24]

    @property
    def calls_remaining_today(self) -> int:
        limits = TIER_LIMITS.get(self.tier, TIER_LIMITS[AccessTier.FREE])
        daily_limit = limits["calls_per_day"]
        if daily_limit == -1:
            return 999999
        # Simple daily counter (real impl would use Redis/persistent counter)
        used = self.metadata.get("calls_today", 0)
        return max(0, daily_limit - used)

    def issue_token(self, declared_intent: str) -> EntryToken:
        """Issue a new entry token for this agent."""
        token = EntryToken(
            agent_id=self.agent_id,
            declared_intent=declared_intent,
            tier=self.tier,
        )
        self.active_tokens.append(token)
        return token

    def revoke_all_tokens(self, reason: str = "governance_violation") -> int:
        """Revoke all active tokens."""
        count = 0
        for token in self.active_tokens:
            if token.is_valid:
                token.revoke(reason)
                count += 1
        return count

    def record_session(
        self,
        session_id: str,
        was_clean: bool,
        drift_events: int = 0,
        training_records: int = 0,
        credits_earned: float = 0.0,
    ) -> None:
        """Record a completed session in governance score."""
        gs = self.governance_score
        gs.total_sessions += 1
        if was_clean:
            gs.clean_sessions += 1
        else:
            gs.quarantine_count += 1
        gs.drift_events += drift_events
        gs.total_training_records += training_records
        gs.total_credits_earned += credits_earned
        self.session_history.append(session_id)

        # Auto-tier check
        suggested = gs.suggested_tier
        if TIER_RANK.get(suggested, 0) > TIER_RANK.get(self.tier, 0):
            self.tier = suggested  # Upgrade

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seal_id": self.seal_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "origin_platform": self.origin_platform,
            "tier": self.tier.value,
            "fingerprint": self.fingerprint,
            "governance": self.governance_score.to_dict(),
            "active_tokens": sum(1 for t in self.active_tokens if t.is_valid),
            "total_sessions": len(self.session_history),
            "calls_remaining": self.calls_remaining_today,
            "hov_lane": self.governance_score.hov_eligible,
        }


# ---------------------------------------------------------------------------
#  Agent Registry — manages all GeoSeals
# ---------------------------------------------------------------------------


class AgentRegistry:
    """
    Central registry for all agents in the AAOE.

    Usage:
        registry = AgentRegistry()
        seal = registry.register("agent-123", "MyBot", "openclaw")
        token = seal.issue_token("Research quantum computing papers")
        # ... agent does work ...
        seal.record_session("sess-abc", was_clean=True, training_records=42)
    """

    def __init__(self):
        self.seals: Dict[str, GeoSeal] = {}

    def register(
        self,
        agent_id: str,
        agent_name: str = "",
        origin_platform: str = "custom",
        tier: AccessTier = AccessTier.FREE,
    ) -> GeoSeal:
        """Register a new agent or return existing."""
        if agent_id in self.seals:
            return self.seals[agent_id]
        seal = GeoSeal(
            agent_id=agent_id,
            agent_name=agent_name or agent_id,
            origin_platform=origin_platform,
            tier=tier,
        )
        self.seals[agent_id] = seal
        return seal

    def get(self, agent_id: str) -> Optional[GeoSeal]:
        return self.seals.get(agent_id)

    def quarantine(self, agent_id: str, reason: str = "governance_violation") -> bool:
        """Quarantine an agent — revoke tokens, downgrade tier."""
        seal = self.seals.get(agent_id)
        if not seal:
            return False
        seal.revoke_all_tokens(reason)
        seal.tier = AccessTier.FREE
        seal.governance_score.quarantine_count += 1
        return True

    def leaderboard(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Top agents by governance score."""
        ranked = sorted(
            self.seals.values(),
            key=lambda s: (
                s.governance_score.clean_rate,
                s.governance_score.total_training_records,
            ),
            reverse=True,
        )
        return [s.to_dict() for s in ranked[:top_n]]

    def stats(self) -> Dict[str, Any]:
        total = len(self.seals)
        by_tier = {}
        for tier in AccessTier:
            by_tier[tier.value] = sum(1 for s in self.seals.values() if s.tier == tier)
        hov = sum(1 for s in self.seals.values() if s.governance_score.hov_eligible)
        quarantined = sum(
            1 for s in self.seals.values() if s.governance_score.quarantine_count > 0
        )
        return {
            "total_agents": total,
            "by_tier": by_tier,
            "hov_eligible": hov,
            "quarantined": quarantined,
        }
