#!/usr/bin/env python3
"""
Gumroad Product Publisher CLI
==============================
One-command publish of all SCBE digital products to Gumroad.

Usage:
    # Set your token first (from Gumroad Settings > Advanced > Applications)
    export GUMROAD_API_TOKEN=your_access_token

    python scripts/gumroad_publish.py list          # List existing products
    python scripts/gumroad_publish.py publish        # Create all 4 products
    python scripts/gumroad_publish.py publish n8n    # Create just n8n pack
    python scripts/gumroad_publish.py sales          # Check sales data
    python scripts/gumroad_publish.py links          # Show all product + Stripe links
    python scripts/gumroad_publish.py status         # Full dashboard
"""

import json
import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root so we can import store_publishers
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "symphonic_cipher" / "scbe_aethermoore" / "concept_blocks" / "web_agent"))
sys.path.insert(0, str(ROOT / "src"))

from store_publishers import GumroadPublisher, ProductSpec, StoreResult


# ---------------------------------------------------------------------------
#  Product Catalog — maps to the ZIP files in artifacts/products/
# ---------------------------------------------------------------------------

PRODUCTS = {
    "n8n": ProductSpec(
        name="SCBE n8n Workflow Starter Pack",
        price_cents=4900,
        description=(
            "12 production-ready n8n workflows + FastAPI bridge for AI-governed operations. "
            "Includes: content publisher, web agent tasks, mesh data funnel, Vertex AI pipeline, "
            "X growth ops, Asana scheduler, game events, Telegram router, LLM dispatch, "
            "Notion/GitHub swarm research, and Baserow RSS. "
            "All workflows integrate with the SCBE 14-layer governance pipeline. "
            "Patent-pending technology (USPTO #63/961,403)."
        ),
        tags=["n8n", "workflow", "automation", "ai-governance", "scbe", "aethermoore",
              "fastapi", "devops", "ai-safety"],
        sku="SCBE-N8N-001",
        category="Digital",
    ),
    "governance": ProductSpec(
        name="AI Governance Toolkit",
        price_cents=2900,
        description=(
            "14-layer governance calculator + YAML templates + threat library for AI safety. "
            "Uses Poincare ball hyperbolic geometry for exponential cost scaling — "
            "adversarial actions cost exponentially more the further they drift from safe operation. "
            "Includes: working Python calculator, chatbot governance profile, code agent profile, "
            "5 built-in scenarios, batch evaluation mode. "
            "Based on patent-pending SCBE framework (USPTO #63/961,403)."
        ),
        tags=["ai-safety", "governance", "ai-governance", "scbe", "poincare",
              "hyperbolic", "calculator", "yaml", "templates"],
        sku="SCBE-GOV-001",
        category="Digital",
    ),
    "spin": ProductSpec(
        name="Content Spin Engine",
        price_cents=1900,
        description=(
            "Fibonacci content multiplication — turn 5 topics into 63+ variations across 7 platforms. "
            "Uses Sacred Tongue semantic analysis and harmonic ratios for natural content variation. "
            "Includes: spin engine, revenue forecaster, 3D visualization, Shopify bridge. "
            "Generate LinkedIn, Twitter, Bluesky, Mastodon, Medium, WordPress, and GitHub content "
            "from a single source topic. Patent-pending technology."
        ),
        tags=["content-marketing", "ai-content", "fibonacci", "automation", "scbe",
              "social-media", "content-spin", "marketing"],
        sku="SCBE-SPIN-001",
        category="Digital",
    ),
    "hydra": ProductSpec(
        name="HYDRA Agent Templates",
        price_cents=900,
        description=(
            "Ready-to-use agent configuration templates for governed AI systems. "
            "Build AI agents with built-in safety guardrails using the SCBE governance framework. "
            "Includes: fleet orchestration templates, single-agent configs, "
            "multi-agent coordination patterns, and governance YAML profiles. "
            "Compatible with LangChain, CrewAI, AutoGen, and custom frameworks."
        ),
        tags=["ai-agents", "templates", "hydra", "scbe", "governance",
              "langchain", "crewai", "autogen", "ai-safety"],
        sku="SCBE-HYDRA-001",
        category="Digital",
    ),
}

# Stripe payment links (LIVE — created Feb 28, 2026)
STRIPE_LINKS = {
    "n8n": {
        "price_id": "price_1T5t52JTF2SuUODIAisGhbSP",
        "link_id": "plink_1T5t5KJTF2SuUODI4KGpnfc7",
        "url": "https://buy.stripe.com/8x228sc0y3XNeBafWSdby05",
    },
    "governance": {
        "price_id": "price_1T5t53JTF2SuUODIWNhAbIRs",
        "link_id": "plink_1T5t5MJTF2SuUODITNiC7v43",
        "url": "https://buy.stripe.com/cNibJ25Ca2TJ9gQ3a6dby06",
    },
    "spin": {
        "price_id": "price_1T5t54JTF2SuUODIXMPKZg2s",
        "link_id": "plink_1T5t5NJTF2SuUODI4wjGaq8z",
        "url": "https://buy.stripe.com/5kQ5kE5Ca65V78I5iedby07",
    },
    "hydra": {
        "price_id": "price_1T5t55JTF2SuUODIfqElri1r",
        "link_id": "plink_1T5t5OJTF2SuUODIGb3k7yxL",
        "url": "https://buy.stripe.com/6oUeVe5Ca2TJdx6262dby08",
    },
}

# ZIP file locations
ZIP_FILES = {
    "n8n": "artifacts/products/scbe-n8n-workflow-pack-v1.0.0.zip",
    "governance": "artifacts/products/scbe-ai-governance-toolkit-v1.0.0.zip",
    "spin": "artifacts/products/scbe-content-spin-engine-v1.0.0.zip",
    "hydra": "artifacts/products/scbe-hydra-agent-templates-v1.0.0.zip",
}


# ---------------------------------------------------------------------------
#  CLI Commands
# ---------------------------------------------------------------------------

def cmd_list():
    """List existing Gumroad products."""
    gumroad = GumroadPublisher()
    result = gumroad.list_products()

    if not result.success:
        print(f"  ERROR: {result.error}")
        return 1

    products = result.data or []
    print(f"\n{'='*60}")
    print(f"  GUMROAD PRODUCTS ({len(products)} total)")
    print(f"{'='*60}")

    for p in products:
        price = p.get("price", 0)
        name = p.get("name", "?")
        pid = p.get("id", "?")
        url = p.get("short_url", "")
        published = p.get("published", False)
        sales = p.get("sales_count", 0)
        revenue = p.get("sales_usd_cents", 0) / 100

        status = "[LIVE]" if published else "[DRAFT]"
        print(f"\n  {status} {name}")
        print(f"         ID: {pid}")
        print(f"         Price: ${price/100:.2f}")
        print(f"         URL: {url}")
        print(f"         Sales: {sales} (${revenue:.2f})")

    print(f"\n{'='*60}\n")
    return 0


def cmd_publish(target=None):
    """Create products on Gumroad."""
    gumroad = GumroadPublisher()

    targets = {target: PRODUCTS[target]} if target else PRODUCTS
    results = []

    print(f"\n{'='*60}")
    print(f"  PUBLISHING TO GUMROAD")
    print(f"{'='*60}")

    for key, spec in targets.items():
        print(f"\n  Creating: {spec.name} (${spec.price_cents/100:.2f})")
        result = gumroad.create_from_spec(spec)

        if result.success:
            print(f"  SUCCESS!")
            print(f"    ID:  {result.product_id}")
            print(f"    URL: {result.product_url}")
            results.append((key, result))
        else:
            print(f"  FAILED: {result.error}")
            results.append((key, result))

    # Save results
    manifest = {
        "published_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "products": {},
    }
    for key, result in results:
        manifest["products"][key] = {
            "name": PRODUCTS[key].name,
            "price": PRODUCTS[key].price_cents,
            "gumroad_id": result.product_id,
            "gumroad_url": result.product_url,
            "stripe_link": STRIPE_LINKS.get(key, {}).get("url"),
            "zip_file": ZIP_FILES.get(key),
            "success": result.success,
            "error": result.error,
        }

    manifest_path = ROOT / "artifacts" / "products" / "gumroad_publish_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n  Manifest saved: {manifest_path}")

    success_count = sum(1 for _, r in results if r.success)
    print(f"\n{'='*60}")
    print(f"  RESULTS: {success_count}/{len(results)} products created")

    # Remind about file upload
    print(f"\n  NEXT STEP: Upload ZIP files to each product")
    print(f"  Option A: Drag-drop in Gumroad dashboard")
    print(f"  Option B: python gumroad_image_uploader.py (Selenium)")
    print(f"  Option C: python scripts/remote_gumroad_upload.py")
    print(f"{'='*60}\n")

    return 0 if success_count == len(results) else 1


def cmd_sales():
    """Check sales data."""
    gumroad = GumroadPublisher()
    result = gumroad.get_sales()

    if not result.success:
        print(f"  ERROR: {result.error}")
        return 1

    sales = result.data or []
    print(f"\n{'='*60}")
    print(f"  GUMROAD SALES ({len(sales)} records)")
    print(f"{'='*60}")

    total_revenue = 0
    for sale in sales:
        price = sale.get("price", 0) / 100
        product = sale.get("product_name", "?")
        email = sale.get("email", "?")
        created = sale.get("created_at", "?")
        total_revenue += price
        print(f"  ${price:.2f} — {product} — {email} — {created}")

    print(f"\n  Total: ${total_revenue:.2f} from {len(sales)} sales")
    print(f"{'='*60}\n")
    return 0


def cmd_links():
    """Show all product links (Gumroad + Stripe)."""
    print(f"\n{'='*60}")
    print(f"  ALL PRODUCT LINKS")
    print(f"{'='*60}")

    for key, spec in PRODUCTS.items():
        stripe = STRIPE_LINKS.get(key, {})
        zip_path = ROOT / ZIP_FILES.get(key, "")
        zip_size = f"{zip_path.stat().st_size / 1024:.1f} KB" if zip_path.exists() else "NOT BUILT"

        print(f"\n  [{key.upper()}] {spec.name} — ${spec.price_cents/100:.2f}")
        print(f"    ZIP:    {zip_path.name} ({zip_size})")
        print(f"    Stripe: {stripe.get('url', 'NOT SET')}")

    # Try to get Gumroad links
    try:
        gumroad = GumroadPublisher()
        result = gumroad.list_products()
        if result.success:
            gumroad_products = {p.get("name", ""): p for p in (result.data or [])}
            print(f"\n  GUMROAD LIVE PRODUCTS:")
            for p_name, p_data in gumroad_products.items():
                url = p_data.get("short_url", "?")
                print(f"    {p_name}: {url}")
    except (ValueError, RuntimeError):
        print(f"\n  (Set GUMROAD_API_TOKEN to see Gumroad links)")

    print(f"\n{'='*60}\n")
    return 0


def cmd_status():
    """Full revenue dashboard."""
    print(f"\n{'='*60}")
    print(f"  SCBE REVENUE DASHBOARD")
    print(f"{'='*60}")

    # Product status
    print(f"\n  PRODUCTS:")
    total_catalog_value = 0
    for key, spec in PRODUCTS.items():
        zip_path = ROOT / ZIP_FILES.get(key, "")
        exists = zip_path.exists()
        total_catalog_value += spec.price_cents
        status = "BUILT" if exists else "MISSING"
        print(f"    [{status}] {spec.name} — ${spec.price_cents/100:.2f}")

    print(f"\n  Catalog value: ${total_catalog_value/100:.2f}")

    # Stripe status
    print(f"\n  STRIPE PAYMENT LINKS:")
    for key, link in STRIPE_LINKS.items():
        print(f"    {PRODUCTS[key].name}: {link['url']}")

    # Gumroad status
    print(f"\n  GUMROAD:")
    try:
        gumroad = GumroadPublisher()
        result = gumroad.list_products()
        if result.success:
            products = result.data or []
            total_sales = sum(p.get("sales_count", 0) for p in products)
            total_rev = sum(p.get("sales_usd_cents", 0) for p in products) / 100
            print(f"    Products: {len(products)}")
            print(f"    Total sales: {total_sales}")
            print(f"    Total revenue: ${total_rev:.2f}")
            for p in products:
                name = p.get("name", "?")
                sales = p.get("sales_count", 0)
                url = p.get("short_url", "")
                print(f"      {name}: {sales} sales — {url}")
        else:
            print(f"    Error: {result.error}")
    except (ValueError, RuntimeError) as e:
        print(f"    Not configured: {e}")

    print(f"\n{'='*60}\n")
    return 0


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

COMMANDS = {
    "list": cmd_list,
    "publish": cmd_publish,
    "sales": cmd_sales,
    "links": cmd_links,
    "status": cmd_status,
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/gumroad_publish.py <command> [target]")
        print(f"Commands: {', '.join(COMMANDS.keys())}")
        print("\nExamples:")
        print("  python scripts/gumroad_publish.py list")
        print("  python scripts/gumroad_publish.py publish")
        print("  python scripts/gumroad_publish.py publish n8n")
        print("  python scripts/gumroad_publish.py sales")
        print("  python scripts/gumroad_publish.py links")
        print("  python scripts/gumroad_publish.py status")
        print("\nRequires: GUMROAD_API_TOKEN environment variable")
        print("Get one at: https://app.gumroad.com/settings/advanced#application-form")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "publish" and len(sys.argv) > 2:
        target = sys.argv[2].lower()
        if target not in PRODUCTS:
            print(f"Unknown product: {target}")
            print(f"Available: {', '.join(PRODUCTS.keys())}")
            sys.exit(1)
        sys.exit(cmd_publish(target))
    elif cmd in COMMANDS:
        sys.exit(COMMANDS[cmd]())
    else:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(COMMANDS.keys())}")
        sys.exit(1)
