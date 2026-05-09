from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_vercel_launch_rewrites_root_and_launch_to_agent_page() -> None:
    config = json.loads((REPO_ROOT / "vercel.json").read_text(encoding="utf-8"))
    routes = {(item["src"], item["dest"]) for item in config["routes"]}

    assert {"src": "api/agent/*.js", "use": "@vercel/node"} in config["builds"]
    assert "feat/vercel-*" in config["ignoreCommand"]
    assert "fix/vercel-*" in config["ignoreCommand"]
    assert ("^/$", "/api/agent/launch.js") in routes
    assert ("^/launch$", "/api/agent/launch.js") in routes
    assert ("^/hire/?$", "/api/agent/hire.js") in routes
    assert ("^/SCBE-AETHERMOORE/hire\\.html$", "/api/agent/hire.js") in routes
    assert ("^/api/agent/(.*)$", "/api/agent/$1.js") in routes


def test_vercelignore_ships_launch_handler_with_api_bridge() -> None:
    ignore = (REPO_ROOT / ".vercelignore").read_text(encoding="utf-8")
    handler = REPO_ROOT / "api" / "agent" / "launch.js"

    assert handler.exists()
    assert (REPO_ROOT / "api" / "agent" / "hire.js").exists()
    assert "!api" in ignore
    assert "!api/**" in ignore
    assert "!docs/offers.json" in ignore
    assert "!docs/app-config.json" in ignore
    assert "!public" in ignore
    assert "!public/hire.html" in ignore


def test_launch_page_links_to_public_docs_and_bridge_endpoints() -> None:
    source = (REPO_ROOT / "api" / "agent" / "launch.js").read_text(encoding="utf-8")
    hire_page = REPO_ROOT / "public" / "hire.html"
    hire_handler = (REPO_ROOT / "api" / "agent" / "hire.js").read_text(encoding="utf-8")

    assert hire_page.exists()
    assert "public', 'hire.html" in hire_handler
    assert "Content-Type" in hire_handler
    assert "/api/agent/health" in source
    assert "/api/agent/status?limit=5" in source
    assert "https://aethermoore.com/SCBE-AETHERMOORE" in source


def test_download_bridge_serves_private_blob_with_delivery_token() -> None:
    source = (REPO_ROOT / "api" / "agent" / "download.js").read_text(encoding="utf-8")

    assert "SCBE_DELIVERY_TOKEN" in source
    assert "BLOB_READ_WRITE_TOKEN" in source
    assert "SCBE_TOOLKIT_BLOB_URL" in source
    assert "SCBE_VAULT_BLOB_URL" in source
    assert "product must be toolkit or vault" in source
    assert "Content-Disposition" in source
    assert 'Cache-Control", "private, no-store"' in source


def test_public_offer_catalog_has_live_revenue_links() -> None:
    offers = json.loads((REPO_ROOT / "docs" / "offers.json").read_text(encoding="utf-8"))
    by_id = {offer["id"]: offer for offer in offers["offers"]}

    assert offers["schema"] == "aethermoore-offers-v1"
    assert by_id["tip_jar"]["checkout_url"] == "https://buy.stripe.com/3cI00k9Sqbqf50A11Ydby0k"
    assert by_id["supporter_monthly"]["checkout_url"] == "https://buy.stripe.com/00w8wQd4CbqfgJidOKdby0i"
    assert by_id["governance_snapshot"]["intake_url"].endswith("/governance-snapshot.html#intake")


def test_public_app_config_explains_remote_update_boundary() -> None:
    config = json.loads((REPO_ROOT / "docs" / "app-config.json").read_text(encoding="utf-8"))

    assert config["schema"] == "aethermoor-bus-app-config-v1"
    assert config["app"]["package_name"] == "io.aethermoor.bus"
    assert config["remote_update"]["supported"] is True
    assert "offer links" in config["remote_update"]["applies_to"]
    assert "package name" in config["remote_update"]["requires_store_release"]
    assert config["features"]["tip_jar"] is True


def test_supporter_page_uses_direct_stripe_checkout_not_broken_api_bridge() -> None:
    page = (REPO_ROOT / "docs" / "supporter.html").read_text(encoding="utf-8")

    assert "https://buy.stripe.com/00w8wQd4CbqfgJidOKdby0i" in page
    assert "https://api.aethermoore.com/v1/billing/public-checkout" not in page


def test_vercel_bridge_exposes_remote_offer_and_app_config_endpoints() -> None:
    offers_source = (REPO_ROOT / "api" / "agent" / "offers.js").read_text(encoding="utf-8")
    app_config_source = (REPO_ROOT / "api" / "agent" / "app-config.js").read_text(encoding="utf-8")
    system_source = (REPO_ROOT / "api" / "agent" / "system.js").read_text(encoding="utf-8")

    assert "docs/offers.json" in offers_source
    assert "s-maxage=300" in offers_source
    assert "docs/app-config.json" in app_config_source
    assert "s-maxage=300" in app_config_source
    assert "aethermoor.agent.system_contract.v1" in system_source
    assert "/api/agent/chat" in system_source
    assert "workspace_formation" in system_source


def test_public_app_config_exposes_unified_system_contract() -> None:
    config = json.loads((REPO_ROOT / "docs" / "app-config.json").read_text(encoding="utf-8"))

    assert config["endpoints"]["agent_bridge_system"].endswith("/api/agent/system")
