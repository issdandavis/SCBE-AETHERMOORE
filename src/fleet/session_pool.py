"""
SessionPool — Shared Authentication & Rate-Limiting Pool for HYDRA Agent Fleet
================================================================================

Multiple AI agents share tokens and sessions across platforms without exceeding
rate limits.  Each platform gets a token-bucket rate limiter, and sessions are
handed out through a single pool so that no two agents accidentally double-spend
a token refresh or blow through a provider's quota.

Architecture::

    Agent-A ──┐
    Agent-B ──┤──► SessionPool ──► RateLimiter (per platform)
    Agent-C ──┘        │
                 SharedSession cache
                 (tokens, cookies, headers)

Thread-safety is provided via ``asyncio.Lock`` on every bucket mutation so the
pool can be safely shared across coroutines in the same event loop.

@module fleet/session_pool
@layer Layer 13
@patent USPTO #63/961,403
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


# ═══════════════════════════════════════════════════════════════
# Platform Rate-Limit Defaults
# ═══════════════════════════════════════════════════════════════

# Expressed as (requests_per_second, burst_capacity).
# Where a provider specifies per-hour, we convert to per-second and
# keep a generous burst bucket so short spikes are fine.
_PLATFORM_LIMITS: Dict[str, Dict[str, float]] = {
    # GitHub: 5000 req/hr shared across ~3 agents ≈ 27/min each ≈ 0.46/sec.
    # We allow a burst of 30 so short flurries don't block.
    "github": {"rate": 5000.0 / 3600.0, "burst": 30.0},
    "shopify": {"rate": 40.0, "burst": 40.0},
    "notion": {"rate": 3.0, "burst": 3.0},
    "airtable": {"rate": 5.0, "burst": 5.0},
    "canva": {"rate": 10.0, "burst": 10.0},
    "gamma": {"rate": 10.0, "burst": 10.0},
    "adobe": {"rate": 20.0, "burst": 20.0},
    "slack": {"rate": 1.0, "burst": 1.0},
    "discord": {"rate": 5.0, "burst": 5.0},
}

_DEFAULT_LIMIT: Dict[str, float] = {"rate": 10.0, "burst": 10.0}

# Map of platform name → environment variable(s) to try when loading tokens.
_ENV_VAR_MAP: Dict[str, list[str]] = {
    "github": ["GITHUB_TOKEN"],
    "shopify": ["SHOPIFY_ADMIN_TOKEN", "SHOPIFY_TOKEN"],
    "notion": ["NOTION_TOKEN"],
    "airtable": ["AIRTABLE_TOKEN", "AIRTABLE_API_KEY"],
    "canva": ["CANVA_API_KEY", "CANVA_TOKEN"],
    "gamma": ["GAMMA_API_KEY", "GAMMA_TOKEN"],
    "adobe": ["ADOBE_CLIENT_ID", "ADOBE_TOKEN"],
    "slack": ["SLACK_BOT_TOKEN", "SLACK_TOKEN"],
    "discord": ["DISCORD_BOT_TOKEN", "DISCORD_TOKEN"],
}


# ═══════════════════════════════════════════════════════════════
# SharedSession dataclass
# ═══════════════════════════════════════════════════════════════


@dataclass
class SharedSession:
    """A single reusable session for one platform.

    Attributes:
        platform: Normalised lower-case platform slug (e.g. ``"github"``).
        token: Bearer / API token string.  May be ``None`` if the platform
            uses cookie-based auth exclusively.
        cookies: Optional cookie jar dict for stateful sessions.
        headers: Extra headers to inject into every request (e.g. ``Accept``).
        expires_at: Unix timestamp after which the token must be refreshed.
            ``0.0`` means "never expires".
        request_count: Running total of requests made through this session.
    """

    platform: str
    token: Optional[str] = None
    cookies: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    expires_at: float = 0.0
    request_count: int = 0


# ═══════════════════════════════════════════════════════════════
# RateLimiter — async token-bucket
# ═══════════════════════════════════════════════════════════════


class RateLimiter:
    """Async token-bucket rate limiter for a single platform.

    Args:
        rate: Sustained requests per second.
        burst: Maximum bucket size (controls short-burst tolerance).

    The bucket starts full and drains by one token per ``acquire()`` call.
    Tokens refill continuously at *rate* tokens per second.
    """

    def __init__(self, rate: float, burst: float) -> None:
        self.rate: float = rate
        self.burst: float = burst
        self._tokens: float = burst
        self._last_refill: float = time.monotonic()
        self._lock: asyncio.Lock = asyncio.Lock()
        self._total_acquired: int = 0
        self._total_rejected: int = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refill(self) -> None:
        """Add tokens that have accumulated since the last refill."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_refill = now

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def acquire(self) -> bool:
        """Try to consume one token.

        Returns:
            ``True`` if a token was available and consumed, ``False`` if the
            request should be rejected / retried later.
        """
        async with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                self._total_acquired += 1
                return True
            self._total_rejected += 1
            return False

    async def wait_and_acquire(self, timeout: float = 30.0) -> bool:
        """Block (up to *timeout* seconds) until a token is available.

        Returns:
            ``True`` if acquired within the timeout, ``False`` otherwise.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if await self.acquire():
                return True
            # Sleep for the minimum time needed for one token to appear.
            sleep_for = min(1.0 / self.rate if self.rate > 0 else 0.1, deadline - time.monotonic())
            if sleep_for <= 0:
                break
            await asyncio.sleep(sleep_for)
        return False

    def stats(self) -> Dict[str, Any]:
        """Snapshot of this limiter's counters."""
        self._refill()
        return {
            "rate_per_sec": self.rate,
            "burst": self.burst,
            "tokens_available": round(self._tokens, 2),
            "total_acquired": self._total_acquired,
            "total_rejected": self._total_rejected,
        }


# ═══════════════════════════════════════════════════════════════
# SessionPool — the main pool
# ═══════════════════════════════════════════════════════════════


class SessionPool:
    """Shared authentication and rate-limiting pool for the HYDRA fleet.

    Instantiate once in the process and hand the same instance to every agent.
    The pool lazily loads tokens from environment variables on first access
    and creates per-platform rate limiters.

    Example::

        pool = SessionPool()
        if await pool.acquire("github"):
            session = pool.get_session("github")
            # ... use session.token, session.headers ...
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, SharedSession] = {}
        self._limiters: Dict[str, RateLimiter] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._load_sessions_from_env()

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def _load_sessions_from_env(self) -> None:
        """Populate sessions from well-known environment variables.

        Each platform checks its list of candidate env-var names and uses the
        first non-empty value found.
        """
        for platform, env_names in _ENV_VAR_MAP.items():
            token = self._pick_env(*env_names)
            if token:
                self._sessions[platform] = SharedSession(
                    platform=platform,
                    token=token,
                    headers=self._default_headers(platform, token),
                )

    @staticmethod
    def _pick_env(*names: str) -> Optional[str]:
        """Return the first non-empty environment variable from *names*."""
        for name in names:
            value = os.environ.get(name, "").strip()
            if value:
                return value
        return None

    @staticmethod
    def _default_headers(platform: str, token: str) -> Dict[str, str]:
        """Build sensible default auth headers per platform."""
        headers: Dict[str, str] = {"User-Agent": "HYDRA-SessionPool/1.0"}
        if platform == "github":
            headers["Authorization"] = f"Bearer {token}"
            headers["Accept"] = "application/vnd.github+json"
            headers["X-GitHub-Api-Version"] = "2022-11-28"
        elif platform in ("notion",):
            headers["Authorization"] = f"Bearer {token}"
            headers["Notion-Version"] = "2022-06-28"
            headers["Content-Type"] = "application/json"
        elif platform in ("shopify",):
            headers["X-Shopify-Access-Token"] = token
            headers["Content-Type"] = "application/json"
        elif platform in ("slack",):
            headers["Authorization"] = f"Bearer {token}"
            headers["Content-Type"] = "application/json; charset=utf-8"
        elif platform in ("discord",):
            headers["Authorization"] = f"Bot {token}"
            headers["Content-Type"] = "application/json"
        else:
            # Generic bearer pattern
            headers["Authorization"] = f"Bearer {token}"
            headers["Content-Type"] = "application/json"
        return headers

    # ------------------------------------------------------------------
    # Limiter helpers
    # ------------------------------------------------------------------

    def _ensure_limiter(self, platform: str) -> RateLimiter:
        """Return (and lazily create) the rate limiter for *platform*."""
        if platform not in self._limiters:
            cfg = _PLATFORM_LIMITS.get(platform, _DEFAULT_LIMIT)
            self._limiters[platform] = RateLimiter(rate=cfg["rate"], burst=cfg["burst"])
        return self._limiters[platform]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_session(self, platform: str) -> SharedSession:
        """Return the shared session for *platform*.

        If no token was loaded from the environment, a bare ``SharedSession``
        with ``token=None`` is created and returned so callers always get a
        valid object.

        Args:
            platform: Lower-case platform slug (``"github"``, ``"notion"``, ...).

        Returns:
            The ``SharedSession`` for *platform*.
        """
        platform = platform.lower()
        if platform not in self._sessions:
            self._sessions[platform] = SharedSession(platform=platform)
        return self._sessions[platform]

    async def acquire(self, platform: str) -> bool:
        """Check the rate limit and, if allowed, increment the request counter.

        Args:
            platform: Lower-case platform slug.

        Returns:
            ``True`` if the request is permitted, ``False`` if rate-limited.
        """
        platform = platform.lower()
        limiter = self._ensure_limiter(platform)
        allowed = await limiter.acquire()
        if allowed:
            session = self.get_session(platform)
            session.request_count += 1
        return allowed

    def refresh_token(self, platform: str, new_token: Optional[str] = None, expires_at: float = 0.0) -> None:
        """Refresh (or replace) the token for *platform*.

        This is a placeholder hook for OAuth / rotating-key flows.  Pass
        *new_token* to update the stored credential; if ``None``, the method
        just bumps ``expires_at`` without changing the token value.

        Args:
            platform: Lower-case platform slug.
            new_token: Replacement token string, or ``None`` to keep the
                current one.
            expires_at: New expiry timestamp (``0.0`` = never).
        """
        platform = platform.lower()
        session = self.get_session(platform)
        if new_token is not None:
            session.token = new_token
            session.headers = self._default_headers(platform, new_token)
        session.expires_at = expires_at

    def get_rate_limiter(self, platform: str) -> RateLimiter:
        """Return the ``RateLimiter`` instance for *platform*.

        Args:
            platform: Lower-case platform slug.

        Returns:
            The ``RateLimiter`` (created with platform defaults if new).
        """
        return self._ensure_limiter(platform.lower())

    def stats(self) -> Dict[str, Any]:
        """Return current usage statistics for every known platform.

        Returns:
            A dict keyed by platform name. Each value contains:
            - ``token_loaded`` (bool)
            - ``request_count`` (int)
            - ``expires_at`` (float)
            - ``rate_limiter`` (dict from ``RateLimiter.stats()``)
        """
        result: Dict[str, Any] = {}
        # Merge platforms from both sessions and limiters
        platforms = set(self._sessions.keys()) | set(self._limiters.keys())
        for platform in sorted(platforms):
            session = self._sessions.get(platform)
            limiter = self._limiters.get(platform)
            result[platform] = {
                "token_loaded": session is not None and session.token is not None,
                "request_count": session.request_count if session else 0,
                "expires_at": session.expires_at if session else 0.0,
                "rate_limiter": limiter.stats() if limiter else None,
            }
        return result

    def register_platform(
        self,
        platform: str,
        token: str,
        *,
        rate: Optional[float] = None,
        burst: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        expires_at: float = 0.0,
    ) -> SharedSession:
        """Manually register a platform that is not in the default env-var map.

        Args:
            platform: Lower-case platform slug.
            token: API token / key.
            rate: Requests per second (``None`` = use default 10/sec).
            burst: Burst bucket size (``None`` = same as *rate*).
            headers: Extra headers; merged on top of the default auth headers.
            expires_at: Token expiry timestamp (``0.0`` = never).

        Returns:
            The newly created ``SharedSession``.
        """
        platform = platform.lower()
        merged_headers = self._default_headers(platform, token)
        if headers:
            merged_headers.update(headers)
        session = SharedSession(
            platform=platform,
            token=token,
            headers=merged_headers,
            expires_at=expires_at,
        )
        self._sessions[platform] = session

        # Custom rate limit
        effective_rate = rate if rate is not None else _DEFAULT_LIMIT["rate"]
        effective_burst = burst if burst is not None else effective_rate
        self._limiters[platform] = RateLimiter(rate=effective_rate, burst=effective_burst)

        return session

    def __repr__(self) -> str:
        loaded = [p for p, s in self._sessions.items() if s.token]
        return f"<SessionPool platforms={loaded}>"
