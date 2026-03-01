"""
Merch / Print-on-Demand Pipeline
=================================
Manages AETHERMOORE character art and design assets for POD platforms.

Revenue targets:
- Redbubble: Upload designs, earn per sale (no upfront cost)
- Printful + Shopify: Integrated POD fulfillment
- TeeSpring/Spring: Social media direct sales
- Society6: Art prints and home goods

Usage:
    python scripts/merch_pod_pipeline.py catalog    # List all design assets
    python scripts/merch_pod_pipeline.py products   # Generate product matrix
    python scripts/merch_pod_pipeline.py redbubble  # Generate Redbubble upload manifest
    python scripts/merch_pod_pipeline.py printful   # Generate Printful API payloads
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
#  Design Assets Catalog
# ---------------------------------------------------------------------------

@dataclass
class DesignAsset:
    name: str
    character: str
    description: str
    source: str  # "adobe_express" | "adobe_cloud" | "local" | "generated"
    file_hint: str  # Path or identifier
    tags: List[str] = field(default_factory=list)
    merch_ready: bool = True
    resolution: str = "high"  # "high" | "medium" | "low"


# Character portraits from Adobe Express (the 3x3 grid)
CHARACTER_ART = [
    DesignAsset(
        name="Eldrin the Sentinel",
        character="Eldrin",
        description="Elven mage with staff, blue/silver tones, mystical aura",
        source="adobe_express",
        file_hint="character_grid_top_left",
        tags=["character", "mage", "fantasy", "blue"],
    ),
    DesignAsset(
        name="Aria the Weaver",
        character="Aria",
        description="Dark-haired woman holding glowing teal crystal, green robes",
        source="adobe_express",
        file_hint="character_grid_top_center",
        tags=["character", "crystal", "fantasy", "green"],
    ),
    DesignAsset(
        name="Polly the Raven",
        character="Polly",
        description="Raven with glowing blue eyes, dark feathers, mystical companion",
        source="adobe_express",
        file_hint="character_grid_top_right",
        tags=["character", "raven", "companion", "dark"],
    ),
    DesignAsset(
        name="Kael the Forge Guardian",
        character="Kael",
        description="Warrior/smith with warm orange glow, sunset background, strong build",
        source="adobe_express",
        file_hint="character_grid_mid_left",
        tags=["character", "warrior", "forge", "orange"],
    ),
    DesignAsset(
        name="Zara the Resonant",
        character="Zara",
        description="Woman channeling multiple colored orbs (Sacred Tongue energies)",
        source="adobe_express",
        file_hint="character_grid_mid_center",
        tags=["character", "magic", "sacred_tongues", "colorful"],
    ),
    DesignAsset(
        name="The Aether Spirit",
        character="Spirit",
        description="Ethereal woman in blue/purple, ghostly luminescence",
        source="adobe_express",
        file_hint="character_grid_mid_right",
        tags=["character", "spirit", "ethereal", "blue"],
    ),
    DesignAsset(
        name="Young Marcus (Protagonist)",
        character="Marcus_Son",
        description="Young adventurer with golden light, coming-of-age hero",
        source="adobe_express",
        file_hint="character_grid_bot_left",
        tags=["character", "protagonist", "hero", "youth"],
    ),
    DesignAsset(
        name="Clay the Golem",
        character="Clay",
        description="Bearded golem/dwarf figure, warm earth tones, sturdy",
        source="adobe_express",
        file_hint="character_grid_bot_center",
        tags=["character", "golem", "earth", "dwarf"],
    ),
    DesignAsset(
        name="The World Tree of Aethermoor",
        character="Landscape",
        description="Glowing tree in mystical landscape, blue/purple sky, crystalline",
        source="adobe_express",
        file_hint="character_grid_bot_right",
        tags=["landscape", "tree", "world", "mystical"],
    ),
]

# Additional branding assets
BRANDING_ART = [
    DesignAsset(
        name="AETHERMOORE Enterprise Logo",
        character="Brand",
        description="Enterprise logo design",
        source="adobe_express",
        file_hint="enterprise_logo",
        tags=["logo", "brand", "enterprise"],
    ),
    DesignAsset(
        name="Spiralverse Protocol Infographic",
        character="Brand",
        description="Technical infographic of the Spiralverse encryption protocol",
        source="adobe_express",
        file_hint="spiralverse_infographic",
        tags=["infographic", "technical", "spiralverse"],
    ),
]


# ---------------------------------------------------------------------------
#  Product Matrix (what to put on each product type)
# ---------------------------------------------------------------------------

PRODUCT_TYPES = {
    "t_shirt": {
        "name": "T-Shirt",
        "platforms": ["redbubble", "printful", "teespring"],
        "min_resolution": "high",
        "margin": "$8-15",
        "retail": "$22-29",
        "best_designs": ["character", "logo", "landscape"],
    },
    "hoodie": {
        "name": "Hoodie",
        "platforms": ["redbubble", "printful", "teespring"],
        "min_resolution": "high",
        "margin": "$12-20",
        "retail": "$39-49",
        "best_designs": ["character", "landscape"],
    },
    "poster": {
        "name": "Art Print / Poster",
        "platforms": ["redbubble", "society6", "printful"],
        "min_resolution": "high",
        "margin": "$5-15",
        "retail": "$15-40",
        "best_designs": ["character", "landscape", "infographic"],
    },
    "mug": {
        "name": "Mug",
        "platforms": ["redbubble", "printful"],
        "min_resolution": "medium",
        "margin": "$5-8",
        "retail": "$14-18",
        "best_designs": ["character", "logo"],
    },
    "phone_case": {
        "name": "Phone Case",
        "platforms": ["redbubble", "printful"],
        "min_resolution": "high",
        "margin": "$5-10",
        "retail": "$18-25",
        "best_designs": ["character", "landscape"],
    },
    "sticker": {
        "name": "Sticker Pack",
        "platforms": ["redbubble", "printful"],
        "min_resolution": "medium",
        "margin": "$1-3",
        "retail": "$3-6",
        "best_designs": ["character", "logo"],
    },
    "laptop_sleeve": {
        "name": "Laptop Sleeve",
        "platforms": ["redbubble", "society6"],
        "min_resolution": "high",
        "margin": "$8-15",
        "retail": "$28-40",
        "best_designs": ["landscape", "character"],
    },
    "canvas": {
        "name": "Canvas Print",
        "platforms": ["society6", "printful"],
        "min_resolution": "high",
        "margin": "$15-30",
        "retail": "$40-80",
        "best_designs": ["landscape", "character"],
    },
}


# ---------------------------------------------------------------------------
#  POD Platform Specs
# ---------------------------------------------------------------------------

POD_PLATFORMS = {
    "redbubble": {
        "name": "Redbubble",
        "url": "https://www.redbubble.com",
        "upload": "Manual upload per design (free)",
        "payout": "Monthly, PayPal or bank transfer",
        "margin_control": "Set your own markup %",
        "setup_time": "30 min to upload all designs",
        "integration": "Standalone marketplace",
        "best_for": "Passive income, global reach",
    },
    "printful": {
        "name": "Printful",
        "url": "https://www.printful.com",
        "upload": "API or manual, connects to Shopify",
        "payout": "Per order through Shopify",
        "margin_control": "Full control (you set retail price)",
        "setup_time": "1-2 hours with Shopify integration",
        "integration": "Shopify app (already have store)",
        "best_for": "Shopify integration, quality products",
    },
    "teespring": {
        "name": "Spring (TeeSpring)",
        "url": "https://www.spri.ng",
        "upload": "Manual per design",
        "payout": "PayPal, bi-weekly",
        "margin_control": "Set your own price",
        "setup_time": "20 min",
        "integration": "YouTube, Instagram, TikTok",
        "best_for": "Social media direct sales",
    },
    "society6": {
        "name": "Society6",
        "url": "https://society6.com",
        "upload": "Manual per artwork",
        "payout": "Monthly, PayPal",
        "margin_control": "Fixed margins (art prints only adjustable)",
        "setup_time": "30 min",
        "integration": "Standalone marketplace",
        "best_for": "Art prints, high-end home goods",
    },
}


# ---------------------------------------------------------------------------
#  Product Generation
# ---------------------------------------------------------------------------

def generate_product_matrix() -> List[Dict]:
    """Generate the full product matrix: designs x product types."""
    products = []
    for design in CHARACTER_ART + BRANDING_ART:
        for prod_key, prod in PRODUCT_TYPES.items():
            # Check if design tags match product best_designs
            tag_match = any(t in design.tags for t in prod["best_designs"])
            if not tag_match:
                continue

            products.append({
                "design": design.name,
                "character": design.character,
                "product": prod["name"],
                "product_key": prod_key,
                "platforms": prod["platforms"],
                "margin": prod["margin"],
                "retail": prod["retail"],
                "title": f"{design.name} — {prod['name']}",
                "description": f"{design.description}. "
                               f"From the AETHERMOORE universe by Issac Davis.",
                "tags": design.tags + [prod_key, "aethermoore", "fantasy", "ai_art"],
            })

    return products


def generate_redbubble_manifest() -> Dict:
    """Generate upload manifest for Redbubble."""
    products = generate_product_matrix()
    rb_products = [p for p in products if "redbubble" in p["platforms"]]

    manifest = {
        "platform": "redbubble",
        "total_designs": len(CHARACTER_ART) + len(BRANDING_ART),
        "total_products": len(rb_products),
        "upload_order": [],
    }

    # Group by design for upload efficiency
    by_design = {}
    for p in rb_products:
        key = p["design"]
        if key not in by_design:
            by_design[key] = {
                "design": p["design"],
                "character": p["character"],
                "description": p["description"],
                "tags": list(set(p["tags"])),
                "products": [],
            }
        by_design[key]["products"].append(p["product"])

    manifest["upload_order"] = list(by_design.values())
    return manifest


def generate_printful_payloads() -> List[Dict]:
    """Generate Printful API product creation payloads."""
    products = generate_product_matrix()
    pf_products = [p for p in products if "printful" in p["platforms"]]

    payloads = []
    for p in pf_products:
        payloads.append({
            "sync_product": {
                "name": p["title"],
                "thumbnail": None,  # Set after image upload
            },
            "sync_variants": [
                {
                    "variant_id": None,  # Set based on Printful catalog
                    "retail_price": p["retail"].split("-")[0].replace("$", ""),
                    "files": [
                        {
                            "url": None,  # Set after image upload
                        }
                    ],
                }
            ],
        })

    return payloads


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def cmd_catalog():
    """List all design assets."""
    print(f"\n{'='*60}")
    print(f"  AETHERMOORE DESIGN ASSET CATALOG")
    print(f"{'='*60}")

    print(f"\n  CHARACTER ART ({len(CHARACTER_ART)} designs):")
    for d in CHARACTER_ART:
        status = "[READY]" if d.merch_ready else "[DRAFT]"
        print(f"    {status} {d.name}")
        print(f"           {d.description}")
        print(f"           Tags: {', '.join(d.tags)}")

    print(f"\n  BRANDING ({len(BRANDING_ART)} designs):")
    for d in BRANDING_ART:
        status = "[READY]" if d.merch_ready else "[DRAFT]"
        print(f"    {status} {d.name}")
        print(f"           {d.description}")

    print(f"\n  Total: {len(CHARACTER_ART) + len(BRANDING_ART)} design assets")
    print(f"{'='*60}\n")


def cmd_products():
    """Generate and display product matrix."""
    products = generate_product_matrix()
    print(f"\n{'='*60}")
    print(f"  MERCH PRODUCT MATRIX ({len(products)} products)")
    print(f"{'='*60}")

    by_type = {}
    for p in products:
        key = p["product"]
        if key not in by_type:
            by_type[key] = []
        by_type[key].append(p)

    for ptype, items in by_type.items():
        print(f"\n  {ptype} ({len(items)} variants):")
        for item in items:
            print(f"    - {item['title']}  {item['retail']}")

    # Revenue estimate
    print(f"\n  REVENUE ESTIMATE (per unit sold):")
    total_min = 0
    total_max = 0
    for p in products:
        margin = p["margin"]
        low, high = margin.replace("$", "").split("-")
        total_min += float(low)
        total_max += float(high)
    print(f"    If every variant sells 1 unit: ${total_min:.0f} - ${total_max:.0f}")
    print(f"    If 10 units each: ${total_min*10:.0f} - ${total_max*10:.0f}")
    print(f"    If 100 units each: ${total_min*100:.0f} - ${total_max*100:.0f}")
    print(f"{'='*60}\n")


def cmd_redbubble():
    """Generate Redbubble upload manifest."""
    manifest = generate_redbubble_manifest()
    out = ROOT / "artifacts" / "products" / "redbubble_manifest.json"
    with open(out, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n  Redbubble manifest: {out}")
    print(f"  Designs to upload: {manifest['total_designs']}")
    print(f"  Product variants: {manifest['total_products']}")
    print(f"\n  Upload order:")
    for item in manifest["upload_order"]:
        print(f"    {item['design']}: {', '.join(item['products'])}")
    print()


def cmd_printful():
    """Generate Printful API payloads."""
    payloads = generate_printful_payloads()
    out = ROOT / "artifacts" / "products" / "printful_payloads.json"
    with open(out, "w") as f:
        json.dump(payloads, f, indent=2)
    print(f"\n  Printful payloads: {out}")
    print(f"  Products to create: {len(payloads)}")
    print(f"\n  NOTE: Image URLs and variant IDs need to be set after")
    print(f"  uploading designs to Printful's file library.\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/merch_pod_pipeline.py <command>")
        print("Commands: catalog, products, redbubble, printful")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "catalog":
        cmd_catalog()
    elif cmd == "products":
        cmd_products()
    elif cmd == "redbubble":
        cmd_redbubble()
    elif cmd == "printful":
        cmd_printful()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
