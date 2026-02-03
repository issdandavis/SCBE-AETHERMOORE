"""
Enhanced API key authentication with tier-based rate limiting.

Replaces the hardcoded API key system with database-backed authentication.
"""

import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict

from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader

from .billing.database import get_db_session, ApiKey, Customer, Subscription, UsageRecord
from .billing.tiers import get_tier_limits, PRICING_TIERS

API_KEY_HEADER = APIKeyHeader(name="SCBE_api_key", auto_error=False)

# In-memory rate limit tracking (for performance)
# In production, use Redis for distributed rate limiting
_rate_limit_cache: dict = defaultdict(lambda: {"count": 0, "reset_at": None})


class CustomerContext:
    """Context object passed to authenticated endpoints."""

    def __init__(
        self,
        customer_id: str,
        customer_email: str,
        tier: str,
        api_key_id: str,
        subscription_id: Optional[str] = None,
    ):
        self.customer_id = customer_id
        self.customer_email = customer_email
        self.tier = tier
        self.api_key_id = api_key_id
        self.subscription_id = subscription_id

    def to_dict(self) -> dict:
        return {
            "customer_id": self.customer_id,
            "customer_email": self.customer_email,
            "tier": self.tier,
            "api_key_id": self.api_key_id,
            "subscription_id": self.subscription_id,
        }


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage/lookup."""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def verify_api_key(
    api_key: str = Security(API_KEY_HEADER),
) -> CustomerContext:
    """
    Verify API key and return customer context.

    Raises HTTPException if key is invalid or rate limited.
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include 'SCBE_api_key' header.",
        )

    # Hash the key for lookup
    key_hash = hash_api_key(api_key)

    # Look up key in database
    db = next(get_db_session())
    try:
        key_record = (
            db.query(ApiKey)
            .filter(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == True,
            )
            .first()
        )

        if not key_record:
            raise HTTPException(
                status_code=403,
                detail="Invalid API key.",
            )

        # Check expiration
        if key_record.expires_at and key_record.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=403,
                detail="API key has expired.",
            )

        # Get customer
        customer = db.query(Customer).get(key_record.customer_id)
        if not customer:
            raise HTTPException(
                status_code=403,
                detail="Customer not found for this API key.",
            )

        # Get active subscription
        subscription = (
            db.query(Subscription)
            .filter(
                Subscription.customer_id == customer.id,
                Subscription.status == "active",
            )
            .first()
        )

        tier = subscription.tier if subscription else "FREE"

        # Check rate limits
        check_rate_limit(customer.id, tier)

        # Update last used
        key_record.last_used_at = datetime.utcnow()
        db.commit()

        return CustomerContext(
            customer_id=customer.id,
            customer_email=customer.email,
            tier=tier,
            api_key_id=key_record.id,
            subscription_id=subscription.id if subscription else None,
        )

    finally:
        db.close()


def check_rate_limit(customer_id: str, tier: str):
    """
    Check rate limits based on tier.

    Uses in-memory sliding window for performance.
    """
    limits = get_tier_limits(tier)
    now = datetime.utcnow()

    # Per-minute rate limit
    if limits.get("per_minute"):
        minute_key = f"{customer_id}:minute"
        cache = _rate_limit_cache[minute_key]

        # Reset if window expired
        if cache["reset_at"] is None or now > cache["reset_at"]:
            cache["count"] = 0
            cache["reset_at"] = now + timedelta(minutes=1)

        if cache["count"] >= limits["per_minute"]:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded ({limits['per_minute']} requests/minute for {tier} tier).",
                headers={
                    "X-RateLimit-Limit": str(limits["per_minute"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(cache["reset_at"].timestamp())),
                    "Retry-After": "60",
                },
            )

        cache["count"] += 1

    # Daily rate limit (for FREE tier)
    if limits.get("daily"):
        daily_key = f"{customer_id}:daily:{now.strftime('%Y-%m-%d')}"
        cache = _rate_limit_cache[daily_key]

        if cache["reset_at"] is None:
            cache["count"] = 0
            cache["reset_at"] = datetime(now.year, now.month, now.day) + timedelta(days=1)

        if cache["count"] >= limits["daily"]:
            raise HTTPException(
                status_code=429,
                detail=f"Daily limit exceeded ({limits['daily']} requests/day for {tier} tier). Upgrade to increase limits.",
                headers={
                    "X-RateLimit-Limit": str(limits["daily"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(cache["reset_at"].timestamp())),
                },
            )

        cache["count"] += 1


async def record_usage(
    customer: CustomerContext,
    endpoint: str,
    method: str,
    status_code: int,
    latency_ms: Optional[int] = None,
    decision: Optional[str] = None,
):
    """Record API usage for billing."""
    db = next(get_db_session())
    try:
        now = datetime.utcnow()
        usage = UsageRecord(
            customer_id=customer.customer_id,
            api_key_id=customer.api_key_id,
            endpoint=endpoint,
            method=method,
            timestamp=now,
            response_status=status_code,
            latency_ms=latency_ms,
            decision=decision,
            billing_period=now.strftime("%Y-%m"),
        )
        db.add(usage)
        db.commit()
    finally:
        db.close()


# Legacy support: Allow environment-based API keys for backward compatibility
LEGACY_API_KEYS = {}
_legacy_keys_env = os.getenv("SCBE_API_KEY", "")
if _legacy_keys_env:
    for key in _legacy_keys_env.split(","):
        key = key.strip()
        if key:
            LEGACY_API_KEYS[key] = "legacy_user"


async def verify_api_key_with_legacy(
    api_key: str = Security(API_KEY_HEADER),
) -> CustomerContext:
    """
    Verify API key with fallback to legacy environment-based keys.

    Use this during migration period.
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include 'SCBE_api_key' header.",
        )

    # Check legacy keys first
    if api_key in LEGACY_API_KEYS:
        return CustomerContext(
            customer_id="legacy",
            customer_email="legacy@scbe.local",
            tier="PRO",  # Legacy keys get PRO access
            api_key_id="legacy",
            subscription_id=None,
        )

    # Try database-backed auth
    return await verify_api_key(api_key)
