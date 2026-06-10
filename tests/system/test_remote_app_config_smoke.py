from __future__ import annotations

from scripts.system.remote_app_config_smoke import (
    APP_CONFIG_SCHEMA,
    OFFERS_SCHEMA,
    PACKAGE_NAME,
    PAGES_BASE,
    VERCEL_BASE,
    run_checks,
    validate_app_config,
    validate_offer_catalog,
)


def _details(checks):
    return "\n".join(f"{check.name}: {check.detail}" for check in checks if not check.ok)


def test_remote_app_config_local_smoke_passes():
    checks = run_checks(live=False)
    assert all(check.ok for check in checks), _details(checks)


def test_offer_catalog_rejects_non_stripe_required_checkout():
    checks = validate_offer_catalog(
        {
            "schema": OFFERS_SCHEMA,
            "offers": [
                {
                    "id": "tip_jar",
                    "checkout_url": "https://example.com/not-stripe",
                    "proof_url": f"{PAGES_BASE}/supporter.html",
                },
                {
                    "id": "supporter_monthly",
                    "checkout_url": "https://buy.stripe.com/test",
                    "proof_url": f"{PAGES_BASE}/supporter.html",
                },
                {
                    "id": "governance_snapshot",
                    "checkout_url": "https://buy.stripe.com/test2",
                    "proof_url": f"{PAGES_BASE}/governance-snapshot.html",
                },
            ],
        },
        "unit:offers",
    )
    assert any(not check.ok and check.name == "unit:offers:tip_jar:checkout" for check in checks)


def test_app_config_rejects_package_name_drift():
    checks = validate_app_config(
        {
            "schema": APP_CONFIG_SCHEMA,
            "app": {"package_name": "io.aethermoor.wrong"},
            "remote_update": {"supported": True},
            "endpoints": {
                "offers_json": f"{PAGES_BASE}/offers.json",
                "supporter_page": f"{PAGES_BASE}/supporter.html",
                "agent_bridge_system": f"{VERCEL_BASE}/api/agent/system",
                "agent_bridge_offers": f"{VERCEL_BASE}/api/agent/offers",
                "agent_bridge_app_config": f"{VERCEL_BASE}/api/agent/app-config",
            },
            "features": {
                "tip_jar": True,
                "supporter_monthly": True,
                "governance_snapshot": True,
            },
            "fallbacks": {"primary_offer": "https://buy.stripe.com/test"},
        },
        "unit:app_config",
    )
    assert any(
        not check.ok and check.name == "unit:app_config:package_name" and PACKAGE_NAME in check.detail
        for check in checks
    )
