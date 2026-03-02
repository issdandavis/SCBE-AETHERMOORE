"""
BaaS Session Manager — Multi-Tenant Browser Session Pool
==========================================================
Manages isolated Playwright browser contexts, one per API session.
Each session wraps a BrowserWorker with governance state, training
data buffer, and TTL-based auto-cleanup.

Used by: src/api/browser_saas.py
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("baas-sessions")


# ---------------------------------------------------------------------------
#  Tier Limits
# ---------------------------------------------------------------------------

class Tier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


TIER_LIMITS = {
    Tier.FREE: {
        "max_sessions": 1,
        "max_actions_per_day": 100,
        "execute_enabled": False,
        "ttl_seconds": 600,       # 10 min
    },
    Tier.PRO: {
        "max_sessions": 5,
        "max_actions_per_day": 1000,
        "execute_enabled": True,
        "ttl_seconds": 1800,      # 30 min
    },
    Tier.ENTERPRISE: {
        "max_sessions": 50,
        "max_actions_per_day": 100_000,
        "execute_enabled": True,
        "ttl_seconds": 3600,      # 60 min
    },
}


# ---------------------------------------------------------------------------
#  Browser Session
# ---------------------------------------------------------------------------

@dataclass
class BrowserSession:
    """Wraps one Playwright browser context with governance + training state."""

    session_id: str
    api_key: str
    tier: Tier
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    # Runtime state
    current_url: str = ""
    action_count: int = 0
    deny_count: int = 0
    risk_accumulation: float = 0.0

    # Perception cache
    last_perception: Optional[Dict[str, Any]] = None

    # Training buffer — list of SFT pairs generated in this session
    training_buffer: List[Dict[str, Any]] = field(default_factory=list)

    # Worker launch configuration
    worker_config: Dict[str, Any] = field(default_factory=dict)

    # The actual worker — injected after creation
    _worker: Any = field(default=None, repr=False)
    _launched: bool = False

    @property
    def ttl_seconds(self) -> int:
        return TIER_LIMITS[self.tier]["ttl_seconds"]

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.last_active) > self.ttl_seconds

    @property
    def actions_remaining(self) -> int:
        limit = TIER_LIMITS[self.tier]["max_actions_per_day"]
        return max(0, limit - self.action_count)

    @property
    def execute_enabled(self) -> bool:
        return TIER_LIMITS[self.tier]["execute_enabled"]

    def touch(self):
        """Update last_active timestamp."""
        self.last_active = time.time()

    def record_action(self, risk_score: float = 0.0):
        """Tick action counter and accumulate risk."""
        self.action_count += 1
        self.risk_accumulation += risk_score
        self.touch()

    def record_deny(self):
        """Tick deny counter and refresh last_active."""
        self.deny_count += 1
        self.touch()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "tier": self.tier.value,
            "current_url": self.current_url,
            "action_count": self.action_count,
            "deny_count": self.deny_count,
            "risk_accumulation": round(self.risk_accumulation, 4),
            "actions_remaining": self.actions_remaining,
            "execute_enabled": self.execute_enabled,
            "is_expired": self.is_expired,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "worker_config": self.worker_config,
            "training_pairs": len(self.training_buffer),
        }


# ---------------------------------------------------------------------------
#  Session Manager
# ---------------------------------------------------------------------------

class SessionManager:
    """Pool of isolated browser sessions, keyed by session_id."""

    def __init__(self):
        self._sessions: Dict[str, BrowserSession] = {}
        self._api_key_sessions: Dict[str, List[str]] = {}
        self._api_key_tiers: Dict[str, Tier] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    # -- Tier resolution -----------------------------------------------------

    def set_tier(self, api_key: str, tier: Tier):
        """Assign a tier to an API key (call during auth)."""
        self._api_key_tiers[api_key] = tier

    def get_tier(self, api_key: str) -> Tier:
        return self._api_key_tiers.get(api_key, Tier.FREE)

    # -- Session lifecycle ---------------------------------------------------

    async def create_session(
        self,
        api_key: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> BrowserSession:
        """Create a new browser session for the given API key."""
        tier = self.get_tier(api_key)
        limits = TIER_LIMITS[tier]

        # Enforce concurrent session limit
        existing = self._api_key_sessions.get(api_key, [])
        # Prune expired
        existing = [sid for sid in existing if sid in self._sessions and not self._sessions[sid].is_expired]
        self._api_key_sessions[api_key] = existing

        if len(existing) >= limits["max_sessions"]:
            raise SessionLimitError(
                f"Tier {tier.value} allows max {limits['max_sessions']} concurrent sessions. "
                f"You have {len(existing)}. Destroy one first."
            )

        session_id = f"baas_{secrets.token_hex(12)}"
        session = BrowserSession(
            session_id=session_id,
            api_key=api_key,
            tier=tier,
            worker_config={
                "headless": bool((config or {}).get("headless", True)),
                "mobile": bool((config or {}).get("mobile", False)),
            },
        )

        self._sessions[session_id] = session
        self._api_key_sessions.setdefault(api_key, []).append(session_id)

        logger.info(
            "Session created: %s (tier=%s, key=%.8s...)",
            session_id, tier.value, api_key,
        )
        return session

    def get_session(self, session_id: str) -> BrowserSession:
        """Get a session by ID. Raises if not found or expired."""
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session {session_id} not found")
        if session.is_expired:
            # Lazy cleanup
            asyncio.ensure_future(self._destroy_session_internal(session_id))
            raise SessionExpiredError(f"Session {session_id} expired after {session.ttl_seconds}s idle")
        return session

    def get_session_for_api_key(self, session_id: str, api_key: str) -> BrowserSession:
        """Get a session by ID and validate API key ownership."""
        session = self.get_session(session_id)
        if session.api_key != api_key:
            raise SessionPermissionError(f"Session {session_id} does not belong to this API key")
        return session

    async def destroy_session(self, session_id: str):
        """Destroy a session and release its browser resources."""
        await self._destroy_session_internal(session_id)

    async def _destroy_session_internal(self, session_id: str):
        session = self._sessions.pop(session_id, None)
        if session is None:
            return

        # Remove from API key index
        key_sessions = self._api_key_sessions.get(session.api_key, [])
        if session_id in key_sessions:
            key_sessions.remove(session_id)

        # Close the Playwright worker if launched
        if session._worker and session._launched:
            try:
                await session._worker.close()
            except Exception as e:
                logger.warning("Error closing worker for %s: %s", session_id, e)

        logger.info("Session destroyed: %s (%d actions, %d training pairs)",
                     session_id, session.action_count, len(session.training_buffer))

    def list_sessions(self, api_key: str) -> List[Dict[str, Any]]:
        """List all active (non-expired) sessions for an API key."""
        sids = self._api_key_sessions.get(api_key, [])
        results = []
        for sid in sids:
            s = self._sessions.get(sid)
            if s and not s.is_expired:
                results.append(s.to_dict())
        return results

    # -- Background cleanup --------------------------------------------------

    def start_cleanup_loop(self, interval: int = 60):
        """Start background task that prunes expired sessions."""
        if self._cleanup_task is not None:
            return
        self._cleanup_task = asyncio.ensure_future(self._cleanup_loop(interval))

    async def _cleanup_loop(self, interval: int):
        while True:
            await asyncio.sleep(interval)
            expired = [
                sid for sid, s in self._sessions.items()
                if s.is_expired
            ]
            for sid in expired:
                await self._destroy_session_internal(sid)
            if expired:
                logger.info("Cleaned up %d expired sessions", len(expired))

    # -- Stats ---------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        active = sum(1 for s in self._sessions.values() if not s.is_expired)
        total_actions = sum(s.action_count for s in self._sessions.values())
        total_pairs = sum(len(s.training_buffer) for s in self._sessions.values())
        return {
            "active_sessions": active,
            "total_sessions_created": len(self._sessions),
            "total_actions": total_actions,
            "total_training_pairs": total_pairs,
            "api_keys_active": len(self._api_key_sessions),
        }


# ---------------------------------------------------------------------------
#  Exceptions
# ---------------------------------------------------------------------------

class SessionLimitError(Exception):
    pass

class SessionNotFoundError(Exception):
    pass

class SessionExpiredError(Exception):
    pass


class SessionPermissionError(Exception):
    pass
