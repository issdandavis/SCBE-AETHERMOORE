"""
Product Packager
================
Builds sellable ZIP packages from SCBE-AETHERMOORE assets.

Usage:
    python scripts/package_products.py             # Build all products
    python scripts/package_products.py n8n          # Build n8n pack only
    python scripts/package_products.py governance   # Build governance toolkit only
    python scripts/package_products.py spin         # Build content spin engine only
    python scripts/package_products.py hydra        # Build HYDRA templates only
    python scripts/package_products.py notion       # Build Notion workspace template only
    python scripts/package_products.py bundle       # Build complete ops bundle
    python scripts/package_products.py --list       # List all products
"""

import os
import sys
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = ROOT / "artifacts" / "products"
LICENSE_FILE = PRODUCTS_DIR / "LICENSE.txt"


# ---------------------------------------------------------------------------
#  Product Definitions
# ---------------------------------------------------------------------------

PRODUCTS = {
    "n8n": {
        "name": "SCBE n8n Workflow Starter Pack",
        "slug": "scbe-n8n-workflow-pack",
        "price": 49.00,
        "version": "1.0.0",
        "description": "12 production-ready n8n workflows + FastAPI bridge for AI-governed operations",
        "files": {
            # Workflows
            "workflows/scbe_content_publisher.workflow.json": "workflows/n8n/scbe_content_publisher.workflow.json",
            "workflows/scbe_web_agent_tasks.workflow.json": "workflows/n8n/scbe_web_agent_tasks.workflow.json",
            "workflows/m5_mesh_data_funnel.workflow.json": "workflows/n8n/m5_mesh_data_funnel.workflow.json",
            "workflows/vertex_hf_pipeline.workflow.json": "workflows/n8n/vertex_hf_pipeline.workflow.json",
            "workflows/x_growth_merch_ops.workflow.json": "workflows/n8n/x_growth_merch_ops.workflow.json",
            "workflows/asana_aetherbrowse_scheduler.workflow.json": "workflows/n8n/asana_aetherbrowse_scheduler.workflow.json",
            "workflows/game_events.workflow.json": "workflows/n8n/game_events.workflow.json",
            "workflows/scbe_telegram_local_router.workflow.json": "workflows/n8n/scbe_telegram_local_router.workflow.json",
            "workflows/scbe_telegram_webhook_cloud.workflow.json": "workflows/n8n/scbe_telegram_webhook_cloud.workflow.json",
            "workflows/scbe_llm_dispatch.workflow.json": "workflows/n8n/scbe_llm_dispatch.workflow.json",
            "workflows/notion_github_swarm_research.workflow.json": "workflows/n8n/notion_github_swarm_research.workflow.json",
            "workflows/baserow_releases_rss.workflow.json": "workflows/n8n/baserow_releases_rss.workflow.json",
            # Bridge
            "bridge/scbe_n8n_bridge.py": "workflows/n8n/scbe_n8n_bridge.py",
            # Samples
            "samples/llm_dispatch_payload.sample.json": "workflows/n8n/llm_dispatch_payload.sample.json",
            "samples/notion_github_swarm_payload.sample.json": "workflows/n8n/notion_github_swarm_payload.sample.json",
            "samples/x_ops_queue.sample.json": "workflows/n8n/x_ops_queue.sample.json",
        },
        "readme": "artifacts/products/n8n-workflow-pack/README.md",
    },
    "governance": {
        "name": "AI Governance Toolkit",
        "slug": "scbe-ai-governance-toolkit",
        "price": 29.00,
        "version": "1.0.0",
        "description": "14-layer governance calculator + templates + threat library for AI safety",
        "files": {
            "governance_calculator.py": "artifacts/products/ai-governance-toolkit/governance_calculator.py",
            "templates/chatbot_governance.yaml": "artifacts/products/ai-governance-toolkit/templates/chatbot_governance.yaml",
            "templates/code_agent_governance.yaml": "artifacts/products/ai-governance-toolkit/templates/code_agent_governance.yaml",
        },
        "readme": "artifacts/products/ai-governance-toolkit/README.md",
    },
    "spin": {
        "name": "Content Spin Engine",
        "slug": "scbe-content-spin-engine",
        "price": 19.00,
        "version": "1.0.0",
        "description": "Fibonacci content multiplication - 5 topics to 63+ variations across 7 platforms",
        "files": {
            "content_spin.py": "scripts/content_spin.py",
            "revenue_engine.py": "scripts/revenue_engine.py",
            "visualize_spin.py": "scripts/visualize_spin.py",
            "shopify_bridge.py": "scripts/shopify_bridge.py",
        },
        "readme": "artifacts/products/content-spin-engine/README.md",
    },
    "hydra": {
        "name": "HYDRA Agent Templates",
        "slug": "scbe-hydra-agent-templates",
        "price": 9.00,
        "version": "1.0.0",
        "description": "Ready-to-use agent configuration templates for governed AI systems",
        "files": {},
        "readme": "artifacts/products/hydra-agent-templates/README.md",
    },
    "notion": {
        "name": "SCBE Notion Workspace Template",
        "slug": "scbe-notion-workspace-template",
        "price": 19.00,
        "version": "1.0.0",
        "description": "Complete Notion workspace structure for AI governance operations",
        "files": {
            "SETUP_GUIDE.md": "artifacts/products/notion-workspace-template/SETUP_GUIDE.md",
            "notion_export/project_tracker.csv": "artifacts/products/notion-workspace-template/notion_export/project_tracker.csv",
            "notion_export/bug_tracker.csv": "artifacts/products/notion-workspace-template/notion_export/bug_tracker.csv",
            "notion_export/release_coordination.csv": "artifacts/products/notion-workspace-template/notion_export/release_coordination.csv",
            "notion_export/revenue_records.csv": "artifacts/products/notion-workspace-template/notion_export/revenue_records.csv",
            "notion_export/people_and_roles.csv": "artifacts/products/notion-workspace-template/notion_export/people_and_roles.csv",
            "notion_export/knowledge_base.md": "artifacts/products/notion-workspace-template/notion_export/knowledge_base.md",
            "templates/governance_review_checklist.md": "artifacts/products/notion-workspace-template/templates/governance_review_checklist.md",
            "templates/incident_response_playbook.md": "artifacts/products/notion-workspace-template/templates/incident_response_playbook.md",
            "templates/new_agent_onboarding.md": "artifacts/products/notion-workspace-template/templates/new_agent_onboarding.md",
            "templates/dataset_publishing_workflow.md": "artifacts/products/notion-workspace-template/templates/dataset_publishing_workflow.md",
            "templates/sprint_planning_risk_assessment.md": "artifacts/products/notion-workspace-template/templates/sprint_planning_risk_assessment.md",
            "dashboard/daily_ops_dashboard.md": "artifacts/products/notion-workspace-template/dashboard/daily_ops_dashboard.md",
        },
        "readme": "artifacts/products/notion-workspace-template/README.md",
    },
}

# The bundle is built separately -- it combines all individual product ZIPs.
BUNDLE = {
    "name": "Complete SCBE Ops Bundle",
    "slug": "scbe-complete-ops-bundle",
    "price": 99.00,
    "version": "1.0.0",
    "description": "All 5 SCBE products at 36% off -- the complete AI governance operations stack",
    "includes": ["n8n", "governance", "spin", "hydra", "notion"],
    "individual_total": 125.00,
    "savings": 56.00,
    "savings_percent": 36,
}


# ---------------------------------------------------------------------------
#  Packager
# ---------------------------------------------------------------------------

def build_product(product_key: str) -> Path:
    """Build a ZIP package for a product."""
    product = PRODUCTS[product_key]
    slug = product["slug"]
    version = product["version"]
    zip_name = f"{slug}-v{version}.zip"
    zip_path = PRODUCTS_DIR / zip_name

    print(f"\n  Building: {product['name']} ({zip_name})")
    print(f"  Price: ${product['price']:.2f}")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add README
        readme_path = ROOT / product["readme"]
        if readme_path.exists():
            zf.write(readme_path, f"{slug}/README.md")
            print(f"    + README.md")

        # Add LICENSE
        if LICENSE_FILE.exists():
            zf.write(LICENSE_FILE, f"{slug}/LICENSE.txt")
            print(f"    + LICENSE.txt")

        # Add product files
        for dest, src in product["files"].items():
            src_path = ROOT / src
            if src_path.exists():
                zf.write(src_path, f"{slug}/{dest}")
                print(f"    + {dest}")
            else:
                print(f"    ! MISSING: {src}")

        # Add manifest
        manifest = {
            "product": product["name"],
            "slug": slug,
            "version": version,
            "price": product["price"],
            "description": product["description"],
            "built": datetime.now(timezone.utc).isoformat(),
            "files": list(product["files"].keys()),
            "author": "Issac Davis / AethermoorGames",
            "patent": "USPTO #63/961,403 (Pending)",
        }
        zf.writestr(
            f"{slug}/manifest.json",
            json.dumps(manifest, indent=2),
        )
        print(f"    + manifest.json")

    size_kb = zip_path.stat().st_size / 1024
    print(f"  Output: {zip_path}")
    print(f"  Size: {size_kb:.1f} KB")
    return zip_path


def build_bundle() -> Path:
    """Build the complete ops bundle by combining all individual product ZIPs."""
    slug = BUNDLE["slug"]
    version = BUNDLE["version"]
    zip_name = f"{slug}-v{version}.zip"
    zip_path = PRODUCTS_DIR / zip_name

    print(f"\n  Building BUNDLE: {BUNDLE['name']} ({zip_name})")
    print(f"  Price: ${BUNDLE['price']:.2f} (${BUNDLE['individual_total']:.2f} value, save ${BUNDLE['savings']:.2f})")

    # First, ensure all individual products are built
    for product_key in BUNDLE["includes"]:
        p = PRODUCTS[product_key]
        individual_zip = PRODUCTS_DIR / f"{p['slug']}-v{p['version']}.zip"
        if not individual_zip.exists():
            print(f"    Building missing dependency: {product_key}")
            build_product(product_key)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as bundle_zf:
        # Add each individual product's contents under its own subfolder
        for product_key in BUNDLE["includes"]:
            p = PRODUCTS[product_key]
            individual_zip_path = PRODUCTS_DIR / f"{p['slug']}-v{p['version']}.zip"
            if individual_zip_path.exists():
                with zipfile.ZipFile(individual_zip_path, "r") as izf:
                    for item in izf.namelist():
                        data = izf.read(item)
                        bundle_zf.writestr(f"{slug}/{item}", data)
                print(f"    + {p['slug']}/ ({len(PRODUCTS[product_key].get('files', {}))} files)")
            else:
                print(f"    ! MISSING ZIP: {individual_zip_path.name}")

        # Add LICENSE at bundle root
        if LICENSE_FILE.exists():
            bundle_zf.write(LICENSE_FILE, f"{slug}/LICENSE.txt")
            print(f"    + LICENSE.txt")

        # Add bundle README
        bundle_readme = (
            f"# {BUNDLE['name']}\n\n"
            f"**By Issac Davis / AethermoorGames**\n"
            f"**Version**: {version}\n"
            f"**Value**: ${BUNDLE['individual_total']:.2f} if purchased separately\n"
            f"**Your Price**: ${BUNDLE['price']:.2f} ({BUNDLE['savings_percent']}% off)\n\n"
            f"---\n\n"
            f"## What Is Included\n\n"
            f"This bundle contains all 5 SCBE products:\n\n"
        )
        for product_key in BUNDLE["includes"]:
            p = PRODUCTS[product_key]
            bundle_readme += f"1. **{p['name']}** (${p['price']:.2f}) -- {p['description']}\n"
        bundle_readme += (
            f"\nEach product is in its own subfolder with a README and setup guide.\n\n"
            f"## Getting Started\n\n"
            f"1. Pick the product you want to set up first (we recommend the n8n Workflow Pack)\n"
            f"2. Open its subfolder and read the README.md\n"
            f"3. Follow the setup instructions\n"
            f"4. Repeat for each product\n\n"
            f"## Support\n\n"
            f"- GitHub: https://github.com/issdandavis/SCBE-AETHERMOORE\n"
            f"- Issues: https://github.com/issdandavis/SCBE-AETHERMOORE/issues\n\n"
            f"## License\n\n"
            f"Commercial license. Single-team, non-transferable. See LICENSE.txt.\n"
        )
        bundle_zf.writestr(f"{slug}/README.md", bundle_readme)
        print(f"    + README.md (bundle)")

        # Add bundle manifest
        manifest = {
            "product": BUNDLE["name"],
            "slug": slug,
            "version": version,
            "price": BUNDLE["price"],
            "individual_total": BUNDLE["individual_total"],
            "savings": BUNDLE["savings"],
            "savings_percent": BUNDLE["savings_percent"],
            "description": BUNDLE["description"],
            "built": datetime.now(timezone.utc).isoformat(),
            "includes": [
                {"key": k, "name": PRODUCTS[k]["name"], "price": PRODUCTS[k]["price"]}
                for k in BUNDLE["includes"]
            ],
            "author": "Issac Davis / AethermoorGames",
            "patent": "USPTO #63/961,403 (Pending)",
        }
        bundle_zf.writestr(
            f"{slug}/manifest.json",
            json.dumps(manifest, indent=2),
        )
        print(f"    + manifest.json")

    size_kb = zip_path.stat().st_size / 1024
    print(f"  Output: {zip_path}")
    print(f"  Size: {size_kb:.1f} KB")
    return zip_path


def build_all() -> list:
    """Build all products including bundle."""
    results = []
    print(f"\n{'='*60}")
    print(f"  SCBE PRODUCT PACKAGER")
    print(f"{'='*60}")

    for key in PRODUCTS:
        path = build_product(key)
        results.append((key, path))

    # Build the bundle
    bundle_path = build_bundle()
    results.append(("bundle", bundle_path))

    print(f"\n{'='*60}")
    print(f"  SUMMARY: {len(results)} packages built ({len(PRODUCTS)} individual + 1 bundle)")
    print(f"{'='*60}")
    total_individual = sum(PRODUCTS[k]["price"] for k in PRODUCTS)
    print(f"  Individual catalog value: ${total_individual:.2f}")
    print(f"  Bundle price: ${BUNDLE['price']:.2f}")
    for key, path in results:
        if key == "bundle":
            print(f"  [{BUNDLE['slug']}] ${BUNDLE['price']:.2f} — {path.name}")
        else:
            p = PRODUCTS[key]
            print(f"  [{p['slug']}] ${p['price']:.2f} — {path.name}")
    print(f"{'='*60}\n")
    return results


def list_products():
    """List all products including bundle."""
    print(f"\n{'='*60}")
    print(f"  SCBE PRODUCT CATALOG")
    print(f"{'='*60}")
    for key, p in PRODUCTS.items():
        print(f"\n  [{key}] {p['name']}")
        print(f"         ${p['price']:.2f} — {p['description']}")
        zip_path = PRODUCTS_DIR / f"{p['slug']}-v{p['version']}.zip"
        if zip_path.exists():
            size_kb = zip_path.stat().st_size / 1024
            print(f"         BUILT: {zip_path.name} ({size_kb:.1f} KB)")
        else:
            print(f"         NOT YET BUILT")

    # Bundle
    print(f"\n  [bundle] {BUNDLE['name']}")
    print(f"           ${BUNDLE['price']:.2f} — {BUNDLE['description']}")
    print(f"           Includes: {', '.join(BUNDLE['includes'])}")
    print(f"           Value: ${BUNDLE['individual_total']:.2f} | Save: ${BUNDLE['savings']:.2f} ({BUNDLE['savings_percent']}%)")
    bundle_zip = PRODUCTS_DIR / f"{BUNDLE['slug']}-v{BUNDLE['version']}.zip"
    if bundle_zip.exists():
        size_kb = bundle_zip.stat().st_size / 1024
        print(f"           BUILT: {bundle_zip.name} ({size_kb:.1f} KB)")
    else:
        print(f"           NOT YET BUILT")

    print(f"\n{'='*60}\n")


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "all":
        build_all()
    elif sys.argv[1] == "--list":
        list_products()
    elif sys.argv[1] == "bundle":
        build_bundle()
    elif sys.argv[1] in PRODUCTS:
        build_product(sys.argv[1])
    else:
        print(f"Unknown product: {sys.argv[1]}")
        print(f"Available: {', '.join(PRODUCTS.keys())}, bundle, all, --list")
        sys.exit(1)
