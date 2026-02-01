"""
Pricing tier configuration for SCBE-AETHERMOORE SaaS.

Defines rate limits, features, and Stripe price IDs for each tier.
"""

import os
from typing import Optional

# Stripe Price IDs (set in environment or Stripe Dashboard)
STRIPE_PRICE_STARTER = os.getenv("STRIPE_PRICE_STARTER", "price_starter_monthly")
STRIPE_PRICE_PRO = os.getenv("STRIPE_PRICE_PRO", "price_pro_monthly")
STRIPE_PRICE_ENTERPRISE = os.getenv("STRIPE_PRICE_ENTERPRISE", "price_enterprise_monthly")

PRICING_TIERS = {
    "FREE": {
        "stripe_price_id": None,
        "monthly_price_cents": 0,
        "rate_limits": {
            "per_minute": 10,
            "daily": 1000,
            "monthly": None,  # No monthly cap, daily enforced
        },
        "features": [
            "basic_governance",
            "audit_logs_7_days",
            "api_keys_1",
        ],
        "max_api_keys": 1,
        "audit_retention_days": 7,
    },
    "STARTER": {
        "stripe_price_id": STRIPE_PRICE_STARTER,
        "monthly_price_cents": 9900,  # $99/month
        "rate_limits": {
            "per_minute": 100,
            "daily": None,
            "monthly": 100_000,
        },
        "features": [
            "basic_governance",
            "audit_logs_30_days",
            "webhooks",
            "api_keys_5",
            "email_support",
        ],
        "max_api_keys": 5,
        "audit_retention_days": 30,
    },
    "PRO": {
        "stripe_price_id": STRIPE_PRICE_PRO,
        "monthly_price_cents": 49900,  # $499/month
        "rate_limits": {
            "per_minute": 600,
            "daily": None,
            "monthly": 1_000_000,
        },
        "features": [
            "full_governance",
            "audit_logs_90_days",
            "webhooks",
            "api_keys_20",
            "fleet_api",
            "priority_support",
            "custom_policies",
        ],
        "max_api_keys": 20,
        "audit_retention_days": 90,
    },
    "ENTERPRISE": {
        "stripe_price_id": STRIPE_PRICE_ENTERPRISE,
        "monthly_price_cents": None,  # Custom pricing
        "rate_limits": {
            "per_minute": None,  # Unlimited
            "daily": None,
            "monthly": None,
        },
        "features": [
            "full_governance",
            "audit_logs_unlimited",
            "webhooks",
            "api_keys_unlimited",
            "fleet_api",
            "sla_99_9",
            "dedicated_support",
            "custom_integrations",
            "on_premise_option",
        ],
        "max_api_keys": None,  # Unlimited
        "audit_retention_days": None,  # Unlimited
    },
}


def get_tier_limits(tier: str) -> dict:
    """Get rate limits for a tier."""
    if tier not in PRICING_TIERS:
        tier = "FREE"
    return PRICING_TIERS[tier]["rate_limits"]


def get_tier_features(tier: str) -> list:
    """Get features for a tier."""
    if tier not in PRICING_TIERS:
        tier = "FREE"
    return PRICING_TIERS[tier]["features"]


def has_feature(tier: str, feature: str) -> bool:
    """Check if a tier has a specific feature."""
    features = get_tier_features(tier)
    return feature in features


def get_max_api_keys(tier: str) -> Optional[int]:
    """Get maximum API keys allowed for a tier."""
    if tier not in PRICING_TIERS:
        tier = "FREE"
    return PRICING_TIERS[tier]["max_api_keys"]


def get_tier_from_price_id(price_id: str) -> str:
    """Determine tier from Stripe price ID."""
    for tier_name, config in PRICING_TIERS.items():
        if config["stripe_price_id"] == price_id:
            return tier_name
    return "FREE"


def get_price_id_for_tier(tier: str) -> Optional[str]:
    """Get Stripe price ID for a tier."""
    if tier not in PRICING_TIERS:
        return None
    return PRICING_TIERS[tier]["stripe_price_id"]
