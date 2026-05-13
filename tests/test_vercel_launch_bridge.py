from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_vercel_launch_rewrites_root_and_launch_to_agent_page() -> None:
    config = json.loads((REPO_ROOT / "vercel.json").read_text(encoding="utf-8"))
    routes = {(item["src"], item["dest"]) for item in config["routes"]}
    ignore_script = REPO_ROOT / "scripts" / "vercel" / "ignore-build.cjs"
    ignore_source = ignore_script.read_text(encoding="utf-8")

    assert {"src": "api/agent/*.js", "use": "@vercel/node"} in config["builds"]
    assert config["ignoreCommand"] == "node scripts/vercel/ignore-build.cjs"
    assert ignore_script.exists()
    assert "ref === 'main'" in ignore_source
    assert "ref.startsWith('launch/')" in ignore_source
    assert "ref.startsWith('customer/')" in ignore_source
    assert "'.vercelignore'" in ignore_source
    assert "'scripts/vercel/ignore-build.cjs'" in ignore_source
    assert "'api/agent'" in ignore_source
    assert "'api/polly'" in ignore_source
    assert "'api/billing'" in ignore_source
    assert "'docs/app-config.json'" in ignore_source
    assert "'docs/robots.txt'" in ignore_source
    assert "'docs/sitemap.xml'" in ignore_source
    assert "'docs/solutions.html'" in ignore_source
    assert "'docs/governance-snapshot.html'" in ignore_source
    assert "'docs/hire.html'" in ignore_source
    assert "'docs/hire-b.html'" in ignore_source
    assert "'docs/products.html'" in ignore_source
    assert "'docs/start-here.html'" in ignore_source
    assert "'docs/agents.html'" in ignore_source
    assert "'docs/chat.html'" in ignore_source
    assert "'docs/payments.html'" in ignore_source
    assert "'docs/workflow-snapshot.html'" in ignore_source
    assert "'docs/robot.html'" in ignore_source
    assert "'docs/robot.md'" in ignore_source
    assert "'docs/llms.txt'" in ignore_source
    assert "'docs/legal/privacy.html'" in ignore_source
    assert "'docs/legal/terms.html'" in ignore_source
    assert ("^/$", "/api/agent/launch.js") in routes
    assert ("^/launch$", "/api/agent/launch.js") in routes
    assert ("^/index\\.html$", "/api/agent/launch.js") in routes
    assert ("^/SCBE-AETHERMOORE/?$", "/api/agent/launch.js") in routes
    assert ("^/SCBE-AETHERMOORE/index\\.html$", "/api/agent/launch.js") in routes
    assert ("^/offers\\.json$", "/api/agent/offers-file.js") in routes
    assert ("^/SCBE-AETHERMOORE/offers\\.json$", "/api/agent/offers-file.js") in routes
    assert ("^/app-config\\.json$", "/api/agent/app-config-file.js") in routes
    assert ("^/SCBE-AETHERMOORE/app-config\\.json$", "/api/agent/app-config-file.js") in routes
    assert ("^/robots\\.txt$", "/api/agent/robots.js") in routes
    assert ("^/SCBE-AETHERMOORE/robots\\.txt$", "/api/agent/robots.js") in routes
    assert ("^/sitemap\\.xml$", "/api/agent/sitemap.js") in routes
    assert ("^/SCBE-AETHERMOORE/sitemap\\.xml$", "/api/agent/sitemap.js") in routes
    assert ("^/hire/?$", "/api/agent/hire.js") in routes
    assert ("^/SCBE-AETHERMOORE/hire\\.html$", "/api/agent/hire.js") in routes
    assert ("^/products/?$", "/api/agent/products.js") in routes
    assert ("^/SCBE-AETHERMOORE/products\\.html$", "/api/agent/products.js") in routes
    assert ("^/solutions/?$", "/api/agent/solutions.js") in routes
    assert ("^/SCBE-AETHERMOORE/solutions\\.html$", "/api/agent/solutions.js") in routes
    assert ("^/start-here/?$", "/api/agent/start-here.js") in routes
    assert ("^/SCBE-AETHERMOORE/start-here\\.html$", "/api/agent/start-here.js") in routes
    assert ("^/agents/?$", "/api/agent/agents.js") in routes
    assert ("^/SCBE-AETHERMOORE/agents\\.html$", "/api/agent/agents.js") in routes
    assert ("^/chat/?$", "/api/agent/chat-page.js") in routes
    assert ("^/SCBE-AETHERMOORE/chat\\.html$", "/api/agent/chat-page.js") in routes
    assert ("^/payments/?$", "/api/agent/payments.js") in routes
    assert ("^/SCBE-AETHERMOORE/payments\\.html$", "/api/agent/payments.js") in routes
    assert ("^/workflow-snapshot/?$", "/api/agent/workflow-snapshot.js") in routes
    assert ("^/SCBE-AETHERMOORE/workflow-snapshot\\.html$", "/api/agent/workflow-snapshot.js") in routes
    assert ("^/governance-snapshot/?$", "/api/agent/governance-snapshot.js") in routes
    assert (
        "^/SCBE-AETHERMOORE/governance-snapshot\\.html$",
        "/api/agent/governance-snapshot.js",
    ) in routes
    assert ("^/service-credits/?$", "/api/agent/service-credits.js") in routes
    assert ("^/SCBE-AETHERMOORE/service-credits\\.html$", "/api/agent/service-credits.js") in routes
    assert ("^/supporter/?$", "/api/agent/supporter.js") in routes
    assert ("^/SCBE-AETHERMOORE/supporter\\.html$", "/api/agent/supporter.js") in routes
    assert ("^/hosted-run/?$", "/api/agent/hosted-run.js") in routes
    assert ("^/SCBE-AETHERMOORE/hosted-run\\.html$", "/api/agent/hosted-run.js") in routes
    assert ("^/legal/privacy/?$", "/api/agent/legal-privacy.js") in routes
    assert ("^/privacy/?$", "/api/agent/legal-privacy.js") in routes
    assert ("^/SCBE-AETHERMOORE/privacy\\.html$", "/api/agent/legal-privacy.js") in routes
    assert ("^/SCBE-AETHERMOORE/legal/privacy\\.html$", "/api/agent/legal-privacy.js") in routes
    assert ("^/legal/terms/?$", "/api/agent/legal-terms.js") in routes
    assert ("^/terms/?$", "/api/agent/legal-terms.js") in routes
    assert ("^/SCBE-AETHERMOORE/terms\\.html$", "/api/agent/legal-terms.js") in routes
    assert ("^/SCBE-AETHERMOORE/legal/terms\\.html$", "/api/agent/legal-terms.js") in routes
    assert ("^/robot\\.html$", "/api/agent/robot-page.js") in routes
    assert ("^/SCBE-AETHERMOORE/robot\\.html$", "/api/agent/robot-page.js") in routes
    assert ("^/robot\\.md$", "/api/agent/robot-md.js") in routes
    assert ("^/SCBE-AETHERMOORE/robot\\.md$", "/api/agent/robot-md.js") in routes
    assert ("^/llms\\.txt$", "/api/agent/llms.js") in routes
    assert ("^/SCBE-AETHERMOORE/llms\\.txt$", "/api/agent/llms.js") in routes
    assert ("^/static/(.*)$", "/api/agent/static.js?path=$1") in routes
    assert ("^/api/agent/(.*)$", "/api/agent/$1.js") in routes
    assert ("^/v1/polly/hosted-run/?$", "/api/polly/hosted-run.js") in routes


def test_vercelignore_ships_launch_handler_with_api_bridge() -> None:
    ignore = (REPO_ROOT / ".vercelignore").read_text(encoding="utf-8")
    handler = REPO_ROOT / "api" / "agent" / "launch.js"

    assert handler.exists()
    assert (REPO_ROOT / "api" / "agent" / "hire.js").exists()
    assert (REPO_ROOT / "api" / "agent" / "products.js").exists()
    assert (REPO_ROOT / "api" / "agent" / "start-here.js").exists()
    assert (REPO_ROOT / "api" / "agent" / "agents.js").exists()
    assert (REPO_ROOT / "api" / "agent" / "chat-page.js").exists()
    assert (REPO_ROOT / "api" / "agent" / "payments.js").exists()
    assert (REPO_ROOT / "api" / "agent" / "workflow-snapshot.js").exists()
    assert (REPO_ROOT / "api" / "agent" / "service-credits.js").exists()
    assert (REPO_ROOT / "api" / "agent" / "supporter.js").exists()
    assert (REPO_ROOT / "api" / "agent" / "hosted-run.js").exists()
    assert (REPO_ROOT / "api" / "agent" / "legal-privacy.js").exists()
    assert (REPO_ROOT / "api" / "agent" / "legal-terms.js").exists()
    assert "!api" in ignore
    assert "!api/**" in ignore
    assert "!docs/offers.json" in ignore
    assert "!docs/app-config.json" in ignore
    assert "!docs/robots.txt" in ignore
    assert "!docs/sitemap.xml" in ignore
    assert "!docs/solutions.html" in ignore
    assert "!docs/products.html" in ignore
    assert "!docs/start-here.html" in ignore
    assert "!docs/agents.html" in ignore
    assert "!docs/chat.html" in ignore
    assert "!docs/payments.html" in ignore
    assert "!docs/workflow-snapshot.html" in ignore
    assert "!docs/governance-snapshot.html" in ignore
    assert "!docs/service-credits.html" in ignore
    assert "!docs/supporter.html" in ignore
    assert "!docs/hosted-run.html" in ignore
    assert "!docs/robot.html" in ignore
    assert "!docs/robot.md" in ignore
    assert "!docs/llms.txt" in ignore
    assert "!docs/legal/privacy.html" in ignore
    assert "!docs/legal/terms.html" in ignore
    assert "!docs/static/**" in ignore
    assert "!public" in ignore
    assert "!public/hire.html" in ignore
    assert "!scripts/vercel/ignore-build.cjs" in ignore


def test_launch_page_links_to_public_docs_and_bridge_endpoints() -> None:
    source = (REPO_ROOT / "api" / "agent" / "launch.js").read_text(encoding="utf-8")
    hire_page = REPO_ROOT / "public" / "hire.html"
    hire_handler = (REPO_ROOT / "api" / "agent" / "hire.js").read_text(encoding="utf-8")

    assert hire_page.exists()
    assert "public', 'hire.html" in hire_handler
    assert "Content-Type" in hire_handler
    assert "SCBE Customer Launch" in source
    assert "Payment Center" in source
    assert "Workflow Snapshot" in source
    assert "Hosted Run Intake" in source
    assert 'href="/payments"' in source
    assert 'href="/products"' in source
    assert 'href="/workflow-snapshot"' in source
    assert 'href="/hosted-run"' in source
    assert 'href="/service-credits"' in source
    assert 'href="/supporter"' in source
    assert "/api/agent/health" in source
    assert "/api/agent/status?limit=5" in source
    assert 'href="/agents"' in source
    assert 'href="/chat"' in source
    assert "support.html" not in source


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
    assert offers["payment_methods"]["card_checkout"]["provider"] == "Stripe hosted checkout"
    assert offers["payment_methods"]["kofi"]["url"] == "https://ko-fi.com/izdandavis"
    assert offers["payment_methods"]["cash_app"]["cashtag"] == "$IzzyDDavis7"
    assert offers["payment_methods"]["manual_invoice"]["email"] == "aethermoregames@pm.me"
    assert by_id["tip_jar"]["checkout_url"] == "https://buy.stripe.com/3cI00k9Sqbqf50A11Ydby0k"
    assert by_id["tip_jar"]["kofi_url"] == "https://ko-fi.com/izdandavis"
    assert by_id["service_credits"]["checkout_url"] == "https://ko-fi.com/izdandavis"
    assert by_id["service_credits"]["proof_url"].endswith("/service-credits.html")
    assert by_id["service_credits"]["intake_url"].endswith("/hosted-run.html")
    assert by_id["supporter_monthly"]["checkout_url"] == "https://buy.stripe.com/00w8wQd4CbqfgJidOKdby0i"
    assert by_id["supporter_monthly"]["kofi_url"] == "https://ko-fi.com/izdandavis"
    assert by_id["governance_snapshot"]["intake_url"].endswith("/governance-snapshot.html#intake")
    assert offers["usage_policy"]["service_fee_percent_range"] == [2, 5]


def test_public_app_config_explains_remote_update_boundary() -> None:
    config = json.loads((REPO_ROOT / "docs" / "app-config.json").read_text(encoding="utf-8"))

    assert config["schema"] == "aethermoor-bus-app-config-v1"
    assert config["app"]["package_name"] == "io.aethermoor.bus"
    assert config["remote_update"]["supported"] is True
    assert "offer links" in config["remote_update"]["applies_to"]
    assert "package name" in config["remote_update"]["requires_store_release"]
    assert config["features"]["tip_jar"] is True
    assert config["features"]["service_credits"] is True
    assert config["features"]["hosted_run_intake"] is True
    assert config["endpoints"]["hosted_run_page"].endswith("/hosted-run.html")
    assert config["endpoints"]["polly_hosted_run"].endswith("/v1/polly/hosted-run")
    assert config["endpoints"]["polly_chat"].endswith("/chat.html")
    assert config["polly_role"]["role"] == "scbe-web-agent"
    assert "superpowers:subagent-driven-development" in config["polly_role"]["skills"]
    assert "agent-task packet creation" in config["polly_role"]["default_actions"]
    assert config["endpoints"]["youtube_channel"].endswith("/channel/UCO9aJ-ZH0Ddg_F0Dr655WIQ")
    assert config["public_profiles"]["youtube"]["channel_id"] == "UCO9aJ-ZH0Ddg_F0Dr655WIQ"
    assert config["public_profiles"]["youtube"]["display"] == 'Issac "Izreal" Davis'
    assert config["public_profiles"]["github"]["repo"].endswith("/SCBE-AETHERMOORE")
    assert config["public_profiles"]["huggingface"]["profile"].endswith("/issdandavis")
    assert config["endpoints"]["payment_center"].endswith("/payments.html")
    assert config["features"]["unified_payment_center"] is True
    assert config["fallbacks"]["payment_center"].endswith("/payments.html")


def test_supporter_page_uses_direct_stripe_checkout_not_broken_api_bridge() -> None:
    page = (REPO_ROOT / "docs" / "supporter.html").read_text(encoding="utf-8")

    assert "https://buy.stripe.com/00w8wQd4CbqfgJidOKdby0i" in page
    assert "payments.html" in page
    assert "https://api.aethermoore.com/v1/billing/public-checkout" not in page


def test_public_pages_expose_follow_and_support_links() -> None:
    required_links = [
        "https://www.youtube.com/channel/UCO9aJ-ZH0Ddg_F0Dr655WIQ",
        "https://github.com/issdandavis/SCBE-AETHERMOORE",
        "https://huggingface.co/issdandavis",
        "https://ko-fi.com/izdandavis",
    ]

    for page_name in ["index.html", "products.html", "start-here.html", "robot.html"]:
        page = (REPO_ROOT / "docs" / page_name).read_text(encoding="utf-8")
        for link in required_links:
            assert link in page, f"{page_name} missing {link}"


def test_payment_center_exposes_all_live_payment_paths() -> None:
    page = (REPO_ROOT / "docs" / "payments.html").read_text(encoding="utf-8")
    hire_page = (REPO_ROOT / "docs" / "hire.html").read_text(encoding="utf-8")
    sitemap = (REPO_ROOT / "docs" / "sitemap.xml").read_text(encoding="utf-8")
    robots = (REPO_ROOT / "docs" / "robots.txt").read_text(encoding="utf-8")

    assert "https://ko-fi.com/izdandavis" in page
    assert "$IzzyDDavis7" in page
    assert "static/cash-app-payment.png" in page
    assert "https://buy.stripe.com/aFafZiggOdyn9gQ11Ydby0l" in page
    assert "https://buy.stripe.com/eVqeVeaWu79ZgJi11Ydby0j" in page
    assert "mailto:aethermoregames@pm.me?subject=AetherMoore%20invoice%20request" in page
    assert "Do not send secrets" in page
    assert "hire.html#small-business-liaison-intro" in page
    assert 'id="small-business-liaison-intro"' in hire_page
    assert "SCBE-AETHERMOORE/payments.html" in sitemap
    assert "Payments: https://aethermoore.com/SCBE-AETHERMOORE/payments.html" in robots


def test_vercel_bridge_serves_payment_and_legal_static_pages() -> None:
    offers_file_handler = (REPO_ROOT / "api" / "agent" / "offers-file.js").read_text(encoding="utf-8")
    app_config_file_handler = (REPO_ROOT / "api" / "agent" / "app-config-file.js").read_text(encoding="utf-8")
    payment_handler = (REPO_ROOT / "api" / "agent" / "payments.js").read_text(encoding="utf-8")
    solutions_handler = (REPO_ROOT / "api" / "agent" / "solutions.js").read_text(encoding="utf-8")
    workflow_handler = (REPO_ROOT / "api" / "agent" / "workflow-snapshot.js").read_text(encoding="utf-8")
    governance_snapshot_handler = (REPO_ROOT / "api" / "agent" / "governance-snapshot.js").read_text(
        encoding="utf-8",
    )
    service_credits_handler = (REPO_ROOT / "api" / "agent" / "service-credits.js").read_text(encoding="utf-8")
    supporter_handler = (REPO_ROOT / "api" / "agent" / "supporter.js").read_text(encoding="utf-8")
    hosted_run_handler = (REPO_ROOT / "api" / "agent" / "hosted-run.js").read_text(encoding="utf-8")
    privacy_handler = (REPO_ROOT / "api" / "agent" / "legal-privacy.js").read_text(encoding="utf-8")
    terms_handler = (REPO_ROOT / "api" / "agent" / "legal-terms.js").read_text(encoding="utf-8")
    robot_page_handler = (REPO_ROOT / "api" / "agent" / "robot-page.js").read_text(encoding="utf-8")
    robot_md_handler = (REPO_ROOT / "api" / "agent" / "robot-md.js").read_text(encoding="utf-8")
    llms_handler = (REPO_ROOT / "api" / "agent" / "llms.js").read_text(encoding="utf-8")
    robots_handler = (REPO_ROOT / "api" / "agent" / "robots.js").read_text(encoding="utf-8")
    sitemap_handler = (REPO_ROOT / "api" / "agent" / "sitemap.js").read_text(encoding="utf-8")

    assert "offers.json" in offers_file_handler
    assert "app-config.json" in app_config_file_handler
    assert "payments.html" in payment_handler
    assert "solutions.html" in solutions_handler
    assert "workflow-snapshot.html" in workflow_handler
    assert "governance-snapshot.html" in governance_snapshot_handler
    assert "service-credits.html" in service_credits_handler
    assert "supporter.html" in supporter_handler
    assert "hosted-run.html" in hosted_run_handler
    assert "legal/privacy.html" in privacy_handler
    assert "legal/terms.html" in terms_handler
    assert "robot.html" in robot_page_handler
    assert "robot.md" in robot_md_handler
    assert "llms.txt" in llms_handler
    assert "robots.txt" in robots_handler
    assert "sitemap.xml" in sitemap_handler


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
    assert "/v1/polly/hosted-run" in system_source
    assert "workspace_formation" in system_source
    assert "usage_policy" in system_source


def test_public_app_config_exposes_unified_system_contract() -> None:
    config = json.loads((REPO_ROOT / "docs" / "app-config.json").read_text(encoding="utf-8"))

    assert config["endpoints"]["agent_bridge_system"].endswith("/api/agent/system")


def test_hosted_run_page_and_endpoint_are_present() -> None:
    page = (REPO_ROOT / "docs" / "hosted-run.html").read_text(encoding="utf-8")
    handler = (REPO_ROOT / "api" / "polly" / "hosted-run.js").read_text(encoding="utf-8")

    assert "SCBE hosted run intake" in page
    assert "/v1/polly/hosted-run" in page
    assert "ko-fi.com/izdandavis" in page
    assert "hosted-run-intake-v1" in handler
    assert "2-5% SCBE coordination fee" in handler
