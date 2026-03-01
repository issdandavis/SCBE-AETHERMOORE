"""
Gumroad Product Creator
========================
Creates all 6 SCBE product listings on Gumroad via their REST API.

NOTE: The Gumroad API does NOT support file uploads. After running this script,
you must manually upload the ZIP files from the GumRoad/ folder by visiting
each product page and dragging in the ZIP.

Usage:
    # Set your token first:
    export GUMROAD_ACCESS_TOKEN="your-token-here"

    # Create all products:
    python scripts/gumroad_upload.py create

    # List existing products:
    python scripts/gumroad_upload.py list

    # Check status:
    python scripts/gumroad_upload.py status

Get your access token:
    1. Go to https://app.gumroad.com/settings/advanced
    2. Under "Application", click "Generate access token"
    3. Copy the token

After running 'create', you'll need to:
    1. Open each product URL (printed by the script)
    2. Click "Content" tab
    3. Drag the ZIP file from SCBE-AETHERMOORE/GumRoad/ into the upload area
    4. Connect a payment method (PayPal or bank) if not already done
    5. Click "Publish"
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent
GUMROAD_DIR = ROOT / "GumRoad"
API_BASE = "https://api.gumroad.com/v2"


@dataclass
class GumroadProduct:
    name: str
    price: int  # in cents
    description: str
    preview_url: Optional[str] = None
    tags: str = ""
    sku: str = ""
    zip_file: str = ""


# All 6 products with full listing copy
PRODUCTS = [
    GumroadProduct(
        name="SCBE n8n Workflow Starter Pack — 12 AI-Governed Automation Workflows",
        price=4900,
        description=(
            "12 production-ready n8n workflows plus a FastAPI governance bridge. "
            "Publish content across 7 platforms, run web research swarms, ingest training data, "
            "and connect to Telegram, Notion, GitHub, HuggingFace, and Vertex AI — "
            "all with built-in safety scanning on every operation.\n\n"
            "What's included:\n"
            "• Content Publisher — Post to Twitter, LinkedIn, Bluesky, Mastodon with governance gates\n"
            "• Web Agent Tasks — Autonomous web research with governed results\n"
            "• M5 Mesh Data Funnel — Multi-source governed data pipeline\n"
            "• Vertex AI + HuggingFace Pipeline — Training data push + model runs\n"
            "• X Growth + Merch Ops — Twitter growth with product tie-ins\n"
            "• Game Events Pipeline — In-game events to training data\n"
            "• Plus 6 more workflows + FastAPI Bridge server\n\n"
            "Requirements: n8n (self-hosted or cloud), Python 3.11+, Node 18+\n\n"
            "Patent pending (USPTO #63/961,403)"
        ),
        tags="n8n,workflow,automation,AI governance,content publishing,FastAPI",
        sku="scbe-n8n-workflow-pack-v1.0.0",
        zip_file="scbe-n8n-workflow-pack-v1.0.0.zip",
    ),
    GumroadProduct(
        name="AI Governance Toolkit — 14-Layer Risk Scoring for AI Agents (Patent Pending)",
        price=2900,
        description=(
            "A Python governance calculator that scores AI agent actions using hyperbolic geometry. "
            "Includes risk templates for chatbots, code agents, research bots, and fleet coordination — "
            "plus a 200+ threat pattern library.\n\n"
            "The core idea: adversarial behavior costs exponentially more the further it drifts from safe operation. "
            "At distance 5, the cost multiplier is 25,000x. At distance 10, it's 406 quadrillion. "
            "Attacks don't just fail — they become mathematically infeasible.\n\n"
            "What you get:\n"
            "• Governance Calculator (governance_calculator.py)\n"
            "• 5 Risk Templates — chatbots, code agents, research bots, content mod, fleets\n"
            "• Integration Examples — LangChain, OpenAI, FastAPI, n8n\n"
            "• 14-Layer Reference Guide\n"
            "• 200+ Threat Patterns library\n\n"
            "No external dependencies. Patent pending (USPTO #63/961,403)."
        ),
        tags="AI safety,governance,risk scoring,LLM,agent safety,hyperbolic geometry",
        sku="scbe-ai-governance-toolkit-v1.0.0",
        zip_file="scbe-ai-governance-toolkit-v1.0.0.zip",
    ),
    GumroadProduct(
        name="Content Spin Engine — Turn 5 Topics into 63+ Governed Variations",
        price=1900,
        description=(
            "A Fibonacci-based content multiplication engine. 5 seed topics become 63+ unique, "
            "platform-optimized variations across LinkedIn, Twitter, Bluesky, Medium, Mastodon, "
            "GitHub, and HuggingFace. Every piece passes a governance quality gate.\n\n"
            "How it works:\n"
            "1. Define your topic graph (29 nodes included)\n"
            "2. Run the engine — generates hub + spoke variations\n"
            "3. Each variation gets a 4D context vector\n"
            "4. Every piece passes governance gate\n"
            "5. Output lands in a JSON queue ready for scheduling\n\n"
            "Includes: content_spin.py, revenue_engine.py, visualize_spin.py, shopify_bridge.py\n\n"
            "No API keys needed for generation. Pure local computation."
        ),
        tags="content marketing,automation,multi-platform,Fibonacci,social media",
        sku="scbe-content-spin-engine-v1.0.0",
        zip_file="scbe-content-spin-engine-v1.0.0.zip",
    ),
    GumroadProduct(
        name="HYDRA Agent Templates — 5 Ready-to-Run AI Agent Swarm Configurations",
        price=900,
        description=(
            "5 battle-tested agent swarm templates with governance baked in. "
            "Each includes config files, system prompts, risk thresholds, and working example code.\n\n"
            "Templates:\n"
            "• Browser Research Swarm (6 agents) — Autonomous web research with governance\n"
            "• Content Publisher (3 agents) — Multi-platform content with quality gates\n"
            "• Code Review Team (4 agents) — Automated code review pipeline\n"
            "• Data Ingestion Fleet (5 agents) — Governed data collection and storage\n"
            "• Customer Support (3 agents) — Tiered service with safety rails\n\n"
            "Plus 15 prompt engineering patterns: intent declaration, governance checkpoints, "
            "drift detection, quarantine protocols, fleet heartbeat, and more."
        ),
        tags="AI agents,multi-agent,swarm,agent templates,prompt engineering,governance",
        sku="scbe-hydra-agent-templates-v1.0.0",
        zip_file="scbe-hydra-agent-templates-v1.0.0.zip",
    ),
    GumroadProduct(
        name="SCBE Notion Workspace Template — AI Governance Operations Hub",
        price=1900,
        description=(
            "A complete Notion workspace for running AI governance operations. "
            "Pre-configured databases for bug tracking, project management, release coordination, "
            "revenue tracking, and knowledge management.\n\n"
            "What you get:\n"
            "• Project Tracker Database — governance tier, risk status, milestone tracking\n"
            "• Bug/Issue Tracker — tagged by layer (L1-L14), severity, governance implications\n"
            "• Release Coordination — governance sign-off, deployment checklist, rollback\n"
            "• Revenue Records — track by product, channel, and governance tier\n"
            "• People & Roles — team directory with governance clearance levels\n"
            "• Daily Ops Dashboard — key metrics, active issues, revenue summary\n\n"
            "Plus 5 page templates: Governance Review Checklist, Incident Response Playbook, "
            "New Agent Onboarding, Dataset Publishing, Sprint Planning with Risk Assessment."
        ),
        tags="Notion,workspace template,project management,AI governance,operations",
        sku="scbe-notion-workspace-template-v1.0.0",
        zip_file="scbe-notion-workspace-template-v1.0.0.zip",
    ),
    GumroadProduct(
        name="Complete SCBE Ops Bundle — Everything for Governed AI Operations (Save 36%)",
        price=9900,
        description=(
            "All 5 SCBE products in one package at 36% off ($155 value for $99).\n\n"
            "You get:\n"
            "1. n8n Workflow Starter Pack ($49 value) — 12 workflows + FastAPI bridge\n"
            "2. AI Governance Toolkit ($29 value) — 14-layer calculator + threat library\n"
            "3. Content Spin Engine ($19 value) — Fibonacci content multiplication\n"
            "4. HYDRA Agent Templates ($9 value) — 5 swarm configurations\n"
            "5. Notion Workspace Template ($19 value) — Complete ops hub\n\n"
            "Together: 12 automation workflows, mathematical risk framework, 63+ content variations, "
            "21 agent roles across 5 swarm patterns, and a command center to track it all.\n\n"
            "Patent pending (USPTO #63/961,403). 30-day money-back guarantee."
        ),
        tags="AI governance,complete bundle,n8n,Notion,AI safety,agent templates,bundle deal",
        sku="scbe-complete-ops-bundle-v1.0.0",
        zip_file="scbe-complete-ops-bundle-v1.0.0.zip",
    ),
]


def _api_request(method: str, endpoint: str, data: dict = None, token: str = None) -> dict:
    """Make a Gumroad API request."""
    url = f"{API_BASE}/{endpoint}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/x-www-form-urlencoded"}

    if data:
        body = urllib.parse.urlencode(data).encode("utf-8")
    else:
        body = None

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"  API Error {e.code}: {error_body}")
        return {"success": False, "error": error_body}


def create_products(token: str):
    """Create all 6 products on Gumroad."""
    print("=" * 60)
    print("GUMROAD PRODUCT CREATOR")
    print("=" * 60)

    created = []
    for i, product in enumerate(PRODUCTS, 1):
        print(f"\n[{i}/6] Creating: {product.name[:60]}...")

        data = {
            "name": product.name,
            "price": product.price,
            "description": product.description,
        }
        if product.tags:
            data["tags"] = product.tags

        result = _api_request("POST", "products", data=data, token=token)

        if result.get("success"):
            prod_data = result.get("product", {})
            prod_id = prod_data.get("id", "unknown")
            short_url = prod_data.get("short_url", "")
            print(f"  Created! ID: {prod_id}")
            print(f"  URL: {short_url}")
            print(f"  >> Upload ZIP: {product.zip_file}")
            created.append({
                "id": prod_id,
                "name": product.name,
                "url": short_url,
                "zip_file": product.zip_file,
                "price_cents": product.price,
            })
        else:
            print(f"  FAILED: {result.get('error', 'Unknown error')}")
            created.append({
                "id": None,
                "name": product.name,
                "error": result.get("error", "Unknown"),
                "zip_file": product.zip_file,
            })

    # Save results
    results_path = GUMROAD_DIR / "upload_results.json"
    with open(results_path, "w") as f:
        json.dump({"products": created, "timestamp": __import__("datetime").datetime.now().isoformat()}, f, indent=2)

    print("\n" + "=" * 60)
    print("RESULTS SAVED TO: GumRoad/upload_results.json")
    print("=" * 60)

    # Print manual steps
    successful = [p for p in created if p.get("id")]
    if successful:
        print(f"\n{len(successful)} products created. NEXT STEPS:")
        print("-" * 40)
        print("1. Open each URL below in your browser")
        print("2. Click the 'Content' tab")
        print("3. Drag the ZIP file from SCBE-AETHERMOORE/GumRoad/")
        print("4. Make sure you have a payment method connected")
        print("5. Click 'Publish'\n")
        for p in successful:
            print(f"  {p['url']}")
            print(f"    -> Upload: GumRoad/{p['zip_file']}\n")


def list_products(token: str):
    """List all existing Gumroad products."""
    print("Fetching products...")
    result = _api_request("GET", "products", token=token)

    if result.get("success"):
        products = result.get("products", [])
        print(f"\nFound {len(products)} products:\n")
        for p in products:
            status = "PUBLISHED" if p.get("published") else "DRAFT"
            print(f"  [{status}] {p.get('name', 'Untitled')}")
            print(f"    ID: {p.get('id')}  Price: ${p.get('price', 0) / 100:.2f}")
            print(f"    URL: {p.get('short_url', 'N/A')}")
            print(f"    Sales: {p.get('sales_count', 0)}  Revenue: ${p.get('sales_usd_cents', 0) / 100:.2f}")
            print()
    else:
        print(f"Error: {result.get('error', 'Unknown')}")


def check_status(token: str):
    """Quick status check."""
    results_path = GUMROAD_DIR / "upload_results.json"
    if not results_path.exists():
        print("No upload results found. Run 'create' first.")
        return

    with open(results_path) as f:
        data = json.load(f)

    print("Upload Results:")
    print(f"  Timestamp: {data.get('timestamp', 'Unknown')}")
    print(f"  Products: {len(data.get('products', []))}")

    for p in data.get("products", []):
        if p.get("id"):
            print(f"\n  [OK] {p['name'][:50]}...")
            print(f"    ID: {p['id']}")
            print(f"    URL: {p.get('url', 'N/A')}")
            print(f"    ZIP: {p['zip_file']}")
            zip_path = GUMROAD_DIR / p["zip_file"]
            print(f"    ZIP exists locally: {'YES' if zip_path.exists() else 'NO'}")
        else:
            print(f"\n  [FAIL] {p['name'][:50]}...")
            print(f"    Error: {p.get('error', 'Unknown')}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nCommands: create | list | status")
        print("\nQuick start:")
        print("  1. Get your token: https://app.gumroad.com/settings/advanced")
        print("  2. export GUMROAD_ACCESS_TOKEN='your-token'")
        print("  3. python scripts/gumroad_upload.py create")
        return

    command = sys.argv[1].lower()
    token = os.environ.get("GUMROAD_ACCESS_TOKEN", "")

    if not token and command != "status":
        print("ERROR: GUMROAD_ACCESS_TOKEN not set.")
        print()
        print("Get your token:")
        print("  1. Go to https://app.gumroad.com/settings/advanced")
        print("  2. Click 'Generate access token'")
        print("  3. Run: export GUMROAD_ACCESS_TOKEN='your-token-here'")
        print("  4. Then run this script again")
        sys.exit(1)

    if command == "create":
        create_products(token)
    elif command == "list":
        list_products(token)
    elif command == "status":
        check_status(token)
    else:
        print(f"Unknown command: {command}")
        print("Commands: create | list | status")


if __name__ == "__main__":
    main()
