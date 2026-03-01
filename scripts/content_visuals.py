#!/usr/bin/env python3
"""Canva + Gamma Content Pipeline — Product visuals for Gumroad listings.

Generates structured specs for cover images, social cards, pitch decks,
and Open Graph metadata for all 6 SCBE products. Outputs JSON manifests
that can be fed to Canva API, Gamma.app, or used as manual design briefs.

Usage:
    python scripts/content_visuals.py                   # Generate all specs (offline)
    python scripts/content_visuals.py --canva-api       # Push to Canva (requires key)
    python scripts/content_visuals.py --gamma-api       # Push to Gamma (requires key)
    python scripts/content_visuals.py --product n8n     # Generate for one product only
    python scripts/content_visuals.py --list            # List products and visual status

Outputs:
    artifacts/visuals/visual_manifest.json              # Master manifest
    artifacts/visuals/canva_specs.json                  # Canva design specs
    artifacts/visuals/gamma_decks.json                  # Gamma slide deck outlines
    artifacts/visuals/social_cards.json                 # OG / Twitter / LinkedIn meta

@layer Layer 12 (harmonic cost — governance badge on every visual)
@component Content.Visuals
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
#  Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
VISUALS_DIR = ROOT / "artifacts" / "visuals"
GUMROAD_DIR = ROOT / "GumRoad"
PRODUCT_MANIFEST = GUMROAD_DIR / "product_manifest.json"

# ---------------------------------------------------------------------------
#  Brand System
# ---------------------------------------------------------------------------

BRAND = {
    "name": "SCBE / AethermoorGames",
    "author": "Issac Davis",
    "tagline": "Mathematical AI governance. Not just guardrails -- force fields.",
    "patent": "USPTO #63/961,403 (Pending)",
    "website": "https://github.com/issdandavis/SCBE-AETHERMOORE",
    "colors": {
        "primary": "#0D0D1A",          # Deep midnight (background)
        "secondary": "#1A1A2E",        # Dark indigo (card bg)
        "accent_cyan": "#00F0FF",      # Electric cyan (highlights)
        "accent_magenta": "#FF00E5",   # Neon magenta (CTAs)
        "accent_gold": "#FFD700",      # Sacred gold (governance)
        "accent_green": "#00FF88",     # Matrix green (success)
        "accent_red": "#FF3366",       # Alert red (deny)
        "text_primary": "#FFFFFF",     # White text
        "text_secondary": "#A0A0C0",   # Muted lavender
        "gradient_start": "#0D0D1A",   # Gradient: dark
        "gradient_mid": "#1A0A2E",     # Gradient: purple tint
        "gradient_end": "#0A1A2E",     # Gradient: blue tint
    },
    "fonts": {
        "heading": "Space Grotesk",       # Geometric sans (tech feel)
        "heading_fallback": "Inter",
        "body": "JetBrains Mono",         # Monospace for code vibes
        "body_fallback": "Fira Code",
        "accent": "Orbitron",             # Futuristic display
    },
    "keywords": [
        "SCBE", "AETHERMOORE", "AI Governance", "Sacred Tongues",
        "14-Layer Pipeline", "Hyperbolic Geometry", "Patent Pending",
    ],
    "social_proof": [
        "Built on patent-pending technology (USPTO #63/961,403)",
        "Powers 14,000+ training data pairs in production",
        "Used across 12 live workflows processing real content daily",
        "Mathematical guarantee: adversarial cost scales to 406 quadrillion at boundary",
    ],
}


# ---------------------------------------------------------------------------
#  Product Catalog (mirrors GumRoad/product_manifest.json)
# ---------------------------------------------------------------------------

@dataclass
class Product:
    id: str
    name: str
    slug: str
    price_usd: float
    category: str
    description_short: str
    description_long: str
    icon_concept: str
    hero_visual_concept: str
    key_stats: List[str]
    color_accent: str
    tags: List[str] = field(default_factory=list)


PRODUCTS: List[Product] = [
    Product(
        id="n8n",
        name="SCBE n8n Workflow Starter Pack",
        slug="scbe-n8n-workflow-pack",
        price_usd=49.00,
        category="automation",
        description_short="12 production-ready n8n workflows + FastAPI bridge for AI-governed operations",
        description_long=(
            "Complete n8n automation stack with governance scanning on every operation. "
            "Includes content publishing, web research, data ingestion, Telegram routing, "
            "LLM dispatch, and HuggingFace/Vertex AI integration."
        ),
        icon_concept="Interconnected workflow nodes with cyan glow lines and a central governance shield",
        hero_visual_concept=(
            "Dark background with a glowing n8n-style workflow canvas. Nodes are connected "
            "by pulsing cyan lines. A semi-transparent golden shield overlays the center, "
            "representing governance scanning. '12 WORKFLOWS' badge in top-right corner."
        ),
        key_stats=["12 workflows", "7 platforms", "1 bridge server", "3 sample payloads"],
        color_accent="#00F0FF",  # Cyan
        tags=["n8n", "workflow", "automation", "AI governance", "FastAPI"],
    ),
    Product(
        id="governance",
        name="AI Governance Toolkit",
        slug="scbe-ai-governance-toolkit",
        price_usd=29.00,
        category="ai-safety",
        description_short="14-layer governance calculator + templates + threat library for AI safety",
        description_long=(
            "Patent-pending mathematical governance framework using hyperbolic geometry. "
            "Includes Python calculator, 5 risk profile templates, integration examples, "
            "and a 200+ threat pattern library."
        ),
        icon_concept="Concentric rings (14 layers) with gold gradient, inner green glow fading to red at edges",
        hero_visual_concept=(
            "Terminal-style dark background showing ALLOW/QUARANTINE/DENY output in green/gold/red. "
            "14 concentric rings radiate outward from center, layers labeled. Hyperbolic grid "
            "visible in background. 'PATENT PENDING' badge."
        ),
        key_stats=["14 layers", "200+ threats", "5 templates", "4 integrations"],
        color_accent="#FFD700",  # Gold
        tags=["AI safety", "governance", "risk scoring", "hyperbolic geometry"],
    ),
    Product(
        id="spin",
        name="Content Spin Engine",
        slug="scbe-content-spin-engine",
        price_usd=19.00,
        category="content",
        description_short="Fibonacci content multiplication - 5 topics to 63+ variations across 7 platforms",
        description_long=(
            "Mathematically driven content engine using Fibonacci relay branching. "
            "Generate platform-optimized variations for LinkedIn, Twitter, Bluesky, "
            "Medium, Mastodon, GitHub, and HuggingFace."
        ),
        icon_concept="Golden spiral (Fibonacci) unfolding into 7 platform icons, each glowing in brand color",
        hero_visual_concept=(
            "3D Fibonacci spiral on dark background, each arm branching into platform-colored "
            "nodes (Twitter blue, LinkedIn blue, Medium green, etc.). Numbers '5 -> 63+' "
            "displayed prominently. Faint topic graph visible in background."
        ),
        key_stats=["5 seeds", "63+ variations", "7 platforms", "4D context vectors"],
        color_accent="#00FF88",  # Green
        tags=["content marketing", "Fibonacci", "multi-platform", "automation"],
    ),
    Product(
        id="hydra",
        name="HYDRA Agent Templates",
        slug="scbe-hydra-agent-templates",
        price_usd=9.00,
        category="agent-framework",
        description_short="Ready-to-use agent configuration templates for governed AI systems",
        description_long=(
            "5 complete agent swarm templates with configs, prompts, governance rules, "
            "and examples. Covers browser research, content publishing, code review, "
            "data ingestion, and customer support."
        ),
        icon_concept="Hydra silhouette with 6 heads, each representing an agent role, connected by magenta energy lines",
        hero_visual_concept=(
            "Dark background with 5 agent swarm diagrams arranged in a grid. Each swarm "
            "shows connected agent nodes with role labels. Magenta energy lines connect "
            "the swarms. Central HYDRA logo. '21 AGENT ROLES' badge."
        ),
        key_stats=["5 swarms", "21 agent roles", "15 prompt patterns", "5 governance configs"],
        color_accent="#FF00E5",  # Magenta
        tags=["AI agents", "multi-agent", "swarm", "prompt engineering"],
    ),
    Product(
        id="notion",
        name="SCBE Notion Workspace Template",
        slug="scbe-notion-workspace-template",
        price_usd=19.00,
        category="workspace",
        description_short="Complete Notion workspace structure for AI governance operations",
        description_long=(
            "Pre-built Notion workspace hub for AI operations teams. Databases for "
            "projects, bugs, releases, revenue, and people -- all with governance-aware "
            "fields. Includes dashboard, 5 page templates, and setup guide."
        ),
        icon_concept="Notion-style sidebar with 6 database icons, each with a small governance shield badge",
        hero_visual_concept=(
            "Clean screenshot-style mockup of a Notion dashboard on dark background. "
            "Six database tiles visible (Projects, Bugs, Releases, Revenue, People, KB). "
            "Golden governance badge on each tile. Clean, organized, professional."
        ),
        key_stats=["6 databases", "5 templates", "1 dashboard", "governance fields"],
        color_accent="#A0A0C0",  # Muted lavender
        tags=["Notion", "workspace", "project management", "AI operations"],
    ),
    Product(
        id="bundle",
        name="Complete SCBE Ops Bundle",
        slug="scbe-complete-ops-bundle",
        price_usd=99.00,
        category="bundle",
        description_short="All 5 SCBE products at 36% off -- the complete AI governance operations stack",
        description_long=(
            "Everything we sell in one package. 12 n8n workflows, governance calculator, "
            "content engine, agent templates, and Notion workspace. $155 value for $99."
        ),
        icon_concept="5 product icons arranged in a pentagon formation with connecting gold lines and a 'SAVE 36%' starburst",
        hero_visual_concept=(
            "All 5 product cover images arranged in a grid (2x3), each slightly tilted. "
            "Gold border around the entire grid. Large 'SAVE 36%' badge in top-right. "
            "'$155 VALUE' crossed out, '$99' in bold gold. Premium bundle feel."
        ),
        key_stats=["5 products", "$56 savings", "36% off", "$155 value"],
        color_accent="#FFD700",  # Gold
        tags=["bundle", "AI governance", "complete stack", "value deal"],
    ),
]

PRODUCT_MAP: Dict[str, Product] = {p.id: p for p in PRODUCTS}


# ---------------------------------------------------------------------------
#  Image Dimension Specs
# ---------------------------------------------------------------------------

IMAGE_SPECS = {
    "gumroad_cover": {"width": 1280, "height": 720, "label": "Gumroad Product Cover"},
    "gumroad_thumbnail": {"width": 600, "height": 400, "label": "Gumroad Thumbnail"},
    "og_image": {"width": 1200, "height": 630, "label": "Open Graph (Facebook/LinkedIn)"},
    "twitter_card": {"width": 1200, "height": 600, "label": "Twitter Summary Large Image"},
    "twitter_card_small": {"width": 800, "height": 418, "label": "Twitter Summary Card"},
    "linkedin_post": {"width": 1200, "height": 627, "label": "LinkedIn Post Image"},
    "instagram_square": {"width": 1080, "height": 1080, "label": "Instagram Square"},
    "pinterest_pin": {"width": 1000, "height": 1500, "label": "Pinterest Pin"},
    "presentation_slide": {"width": 1920, "height": 1080, "label": "Presentation Slide (16:9)"},
}


# ---------------------------------------------------------------------------
#  Canva Spec Generator
# ---------------------------------------------------------------------------

def generate_canva_specs(products: List[Product]) -> Dict[str, Any]:
    """Generate Canva design specifications for each product.

    Returns a structured dict that can be used as:
    1. A manual design brief for Canva
    2. Input to Canva's Design API (POST /v1/designs)
    3. Input to Zapier Canva integration
    """
    specs: Dict[str, Any] = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "brand": {
            "colors": BRAND["colors"],
            "fonts": BRAND["fonts"],
            "keywords": BRAND["keywords"],
        },
        "designs": [],
    }

    for product in products:
        # --- Gumroad Cover (1280x720) ---
        gumroad_cover = {
            "design_id": f"canva_{product.id}_gumroad_cover",
            "product_id": product.id,
            "product_name": product.name,
            "format": "gumroad_cover",
            "dimensions": IMAGE_SPECS["gumroad_cover"],
            "title": product.name,
            "subtitle": product.description_short,
            "price_badge": f"${product.price_usd:.0f}",
            "concept": product.hero_visual_concept,
            "layout": {
                "background": {
                    "type": "gradient",
                    "colors": [
                        BRAND["colors"]["gradient_start"],
                        BRAND["colors"]["gradient_mid"],
                        BRAND["colors"]["gradient_end"],
                    ],
                    "direction": "diagonal",
                },
                "elements": [
                    {
                        "type": "text",
                        "content": product.name,
                        "font": BRAND["fonts"]["heading"],
                        "size": 48,
                        "color": BRAND["colors"]["text_primary"],
                        "position": {"x": 60, "y": 80},
                        "max_width": 700,
                    },
                    {
                        "type": "text",
                        "content": product.description_short,
                        "font": BRAND["fonts"]["body"],
                        "size": 20,
                        "color": BRAND["colors"]["text_secondary"],
                        "position": {"x": 60, "y": 200},
                        "max_width": 700,
                    },
                    {
                        "type": "badge",
                        "content": f"${product.price_usd:.0f}",
                        "background": product.color_accent,
                        "text_color": BRAND["colors"]["primary"],
                        "font": BRAND["fonts"]["accent"],
                        "size": 36,
                        "position": {"x": 1080, "y": 40},
                        "shape": "rounded_rect",
                        "padding": 16,
                    },
                    {
                        "type": "stats_row",
                        "items": product.key_stats,
                        "font": BRAND["fonts"]["body"],
                        "size": 16,
                        "color": product.color_accent,
                        "position": {"x": 60, "y": 620},
                        "spacing": 40,
                    },
                    {
                        "type": "branding_bar",
                        "content": "SCBE / AethermoorGames",
                        "patent_text": "Patent Pending",
                        "font": BRAND["fonts"]["body"],
                        "size": 12,
                        "color": BRAND["colors"]["text_secondary"],
                        "position": {"x": 60, "y": 680},
                    },
                ],
                "decorative": {
                    "grid_overlay": True,
                    "grid_color": f"{product.color_accent}15",
                    "glow_spots": [
                        {"x": 900, "y": 360, "radius": 200, "color": f"{product.color_accent}30"},
                    ],
                    "scanlines": True,
                    "scanline_opacity": 0.03,
                },
            },
            "export_formats": ["PNG", "WEBP"],
            "status": "spec_ready",
        }

        # --- Social Card (1200x630) ---
        social_card = {
            "design_id": f"canva_{product.id}_social_card",
            "product_id": product.id,
            "product_name": product.name,
            "format": "og_image",
            "dimensions": IMAGE_SPECS["og_image"],
            "title": product.name,
            "subtitle": product.description_short,
            "concept": (
                f"Simplified version of the Gumroad cover. Left 60% is text/branding, "
                f"right 40% is the product icon concept: {product.icon_concept}"
            ),
            "layout": {
                "background": {
                    "type": "solid_with_accent",
                    "base": BRAND["colors"]["secondary"],
                    "accent_stripe": {
                        "color": product.color_accent,
                        "width": 4,
                        "position": "left",
                    },
                },
                "elements": [
                    {
                        "type": "text",
                        "content": product.name,
                        "font": BRAND["fonts"]["heading"],
                        "size": 40,
                        "color": BRAND["colors"]["text_primary"],
                        "position": {"x": 60, "y": 120},
                        "max_width": 650,
                    },
                    {
                        "type": "text",
                        "content": product.description_short,
                        "font": BRAND["fonts"]["body"],
                        "size": 18,
                        "color": BRAND["colors"]["text_secondary"],
                        "position": {"x": 60, "y": 280},
                        "max_width": 650,
                    },
                    {
                        "type": "icon_area",
                        "concept": product.icon_concept,
                        "position": {"x": 800, "y": 80},
                        "dimensions": {"width": 350, "height": 470},
                    },
                    {
                        "type": "footer",
                        "content": "aethermoorgames.com | Patent Pending",
                        "font": BRAND["fonts"]["body"],
                        "size": 14,
                        "color": BRAND["colors"]["text_secondary"],
                        "position": {"x": 60, "y": 580},
                    },
                ],
            },
            "export_formats": ["PNG", "WEBP"],
            "status": "spec_ready",
        }

        # --- Product Mockup ---
        mockup = {
            "design_id": f"canva_{product.id}_mockup",
            "product_id": product.id,
            "product_name": product.name,
            "format": "gumroad_cover",
            "dimensions": IMAGE_SPECS["gumroad_cover"],
            "concept": (
                f"Floating laptop/tablet mockup on dark background showing the product "
                f"in action. For '{product.name}': {product.hero_visual_concept} "
                f"visible on the screen. Subtle reflection below the device."
            ),
            "layout": {
                "background": {
                    "type": "gradient",
                    "colors": [BRAND["colors"]["primary"], BRAND["colors"]["gradient_mid"]],
                    "direction": "radial",
                },
                "elements": [
                    {
                        "type": "device_mockup",
                        "device": "macbook_pro" if product.category != "workspace" else "browser_window",
                        "screen_content": product.hero_visual_concept,
                        "position": {"x": 160, "y": 80},
                        "dimensions": {"width": 960, "height": 540},
                    },
                    {
                        "type": "text",
                        "content": product.name,
                        "font": BRAND["fonts"]["heading"],
                        "size": 24,
                        "color": BRAND["colors"]["text_primary"],
                        "position": {"x": 440, "y": 640},
                    },
                ],
            },
            "export_formats": ["PNG"],
            "status": "spec_ready",
        }

        specs["designs"].extend([gumroad_cover, social_card, mockup])

    specs["total_designs"] = len(specs["designs"])
    return specs


# ---------------------------------------------------------------------------
#  Gamma Deck Generator
# ---------------------------------------------------------------------------

def generate_gamma_decks(products: List[Product]) -> Dict[str, Any]:
    """Generate Gamma.app slide deck outlines for each product.

    Gamma uses a structured JSON format for slide content.
    Each deck has 6 slides: Title, Problem, Solution, Features, Pricing, CTA.
    """
    decks: Dict[str, Any] = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "platform": "gamma.app",
        "theme": {
            "base": "dark",
            "primary_color": BRAND["colors"]["accent_cyan"],
            "background_color": BRAND["colors"]["primary"],
            "text_color": BRAND["colors"]["text_primary"],
            "font_heading": BRAND["fonts"]["heading"],
            "font_body": BRAND["fonts"]["body"],
        },
        "decks": [],
    }

    for product in products:
        deck = {
            "deck_id": f"gamma_{product.id}_pitch",
            "product_id": product.id,
            "title": f"{product.name} -- Product Overview",
            "slides": _build_slides(product),
            "speaker_notes_included": True,
            "estimated_duration_minutes": 5,
            "status": "outline_ready",
        }
        decks["decks"].append(deck)

    # Also generate a master catalog deck
    catalog_deck = {
        "deck_id": "gamma_catalog_overview",
        "product_id": "catalog",
        "title": "SCBE Product Catalog -- AethermoorGames",
        "slides": _build_catalog_slides(products),
        "speaker_notes_included": True,
        "estimated_duration_minutes": 8,
        "status": "outline_ready",
    }
    decks["decks"].append(catalog_deck)

    decks["total_decks"] = len(decks["decks"])
    return decks


def _build_slides(product: Product) -> List[Dict[str, Any]]:
    """Build the 6-slide structure for a single product deck."""
    slides = []

    # Slide 1: Title
    slides.append({
        "slide_number": 1,
        "type": "title",
        "heading": product.name,
        "subheading": product.description_short,
        "visual": {
            "type": "hero_image",
            "concept": product.hero_visual_concept,
            "accent_color": product.color_accent,
        },
        "footer": f"${product.price_usd:.0f} | AethermoorGames | Patent Pending",
        "speaker_notes": (
            f"Welcome. Today I want to show you {product.name} -- "
            f"{product.description_short}. This is part of the SCBE ecosystem, "
            f"built on patent-pending hyperbolic geometry for AI governance."
        ),
    })

    # Slide 2: Problem
    problem_statements = _get_problem_statements(product)
    slides.append({
        "slide_number": 2,
        "type": "problem",
        "heading": "The Problem",
        "bullets": problem_statements,
        "visual": {
            "type": "icon_grid",
            "concept": "Warning/alert icons in red tones showing current pain points",
            "accent_color": BRAND["colors"]["accent_red"],
        },
        "speaker_notes": (
            "These are real problems we see every day in AI operations. "
            "Most teams are building without safety nets, and the consequences "
            "are getting more severe."
        ),
    })

    # Slide 3: Solution
    slides.append({
        "slide_number": 3,
        "type": "solution",
        "heading": "Our Solution",
        "body": product.description_long,
        "key_differentiator": (
            "Unlike other tools, SCBE uses hyperbolic geometry to make adversarial "
            "behavior mathematically infeasible -- not just hard, but exponentially "
            "expensive. At distance 10 from safe operation, the cost multiplier "
            "is 406 quadrillion."
        ),
        "visual": {
            "type": "product_screenshot",
            "concept": product.hero_visual_concept,
            "accent_color": product.color_accent,
        },
        "speaker_notes": (
            f"{product.description_long} "
            "The key insight is mathematical governance -- adversarial cost scales "
            "exponentially, making attacks computationally infeasible."
        ),
    })

    # Slide 4: Features
    feature_list = _get_feature_list(product)
    slides.append({
        "slide_number": 4,
        "type": "features",
        "heading": "What You Get",
        "features": feature_list,
        "stats_bar": product.key_stats,
        "visual": {
            "type": "feature_grid",
            "concept": f"Grid of feature icons with {product.color_accent} accent",
            "accent_color": product.color_accent,
        },
        "speaker_notes": (
            "Let me walk through what is actually in the package. "
            "Each component is production-tested and ready to deploy."
        ),
    })

    # Slide 5: Pricing
    slides.append({
        "slide_number": 5,
        "type": "pricing",
        "heading": "Pricing",
        "price": f"${product.price_usd:.0f}",
        "price_context": _get_price_context(product),
        "includes": product.key_stats,
        "guarantee": "30-day money-back guarantee",
        "visual": {
            "type": "pricing_card",
            "concept": f"Clean pricing card with {product.color_accent} border and gold badge",
            "accent_color": product.color_accent,
        },
        "speaker_notes": (
            f"Pricing is straightforward: ${product.price_usd:.0f}, one-time purchase. "
            "30-day money-back guarantee. No subscriptions, no hidden fees."
        ),
    })

    # Slide 6: Call to Action
    slides.append({
        "slide_number": 6,
        "type": "cta",
        "heading": "Get Started Today",
        "primary_cta": f"Buy {product.name} -- ${product.price_usd:.0f}",
        "secondary_cta": "View on GitHub (open-source core)",
        "social_proof": BRAND["social_proof"][:2],
        "contact": {
            "github": "github.com/issdandavis/SCBE-AETHERMOORE",
            "email": "issdandavis7795@aethermoorgames.com",
        },
        "visual": {
            "type": "cta_block",
            "concept": "Bold CTA button with pulsing cyan glow on dark background",
            "accent_color": BRAND["colors"]["accent_cyan"],
        },
        "speaker_notes": (
            "The link is live now. You can also explore the open-source core on GitHub. "
            "Questions? Reach out -- happy to do a walkthrough."
        ),
    })

    return slides


def _build_catalog_slides(products: List[Product]) -> List[Dict[str, Any]]:
    """Build slides for the master catalog overview deck."""
    slides = []

    # Slide 1: Title
    slides.append({
        "slide_number": 1,
        "type": "title",
        "heading": "SCBE Product Catalog",
        "subheading": "Mathematical AI Governance. Not Just Guardrails -- Force Fields.",
        "visual": {
            "type": "hero_image",
            "concept": (
                "All 6 product icons arranged in a hexagonal formation, connected by "
                "glowing gold lines. SCBE logo at center. Dark cyberpunk background."
            ),
            "accent_color": BRAND["colors"]["accent_gold"],
        },
        "footer": "AethermoorGames | Issac Davis | Patent Pending",
        "speaker_notes": (
            "Welcome to the SCBE product catalog. I am going to walk you through "
            "our complete AI governance operations stack -- 6 products designed to "
            "work together or standalone."
        ),
    })

    # Slide 2: The Stack
    slides.append({
        "slide_number": 2,
        "type": "overview",
        "heading": "The Complete Stack",
        "body": (
            "SCBE is a 14-layer AI safety pipeline using hyperbolic geometry. "
            "Each product in our catalog implements a different operational surface "
            "of this pipeline -- from workflow automation to governance scoring to "
            "content generation."
        ),
        "stack_layers": [
            "L1-L4: Context + Embedding",
            "L5-L7: Hyperbolic Distance + Breathing",
            "L8-L10: Hamiltonian + Spectral Coherence",
            "L11-L13: Temporal + Harmonic + Risk Decision",
            "L14: Audio Axis / Telemetry",
        ],
        "speaker_notes": (
            "The foundation is our 14-layer pipeline. Everything we sell sits on top "
            "of this mathematical base."
        ),
    })

    # Slides 3-8: One per product
    for i, product in enumerate(products):
        slides.append({
            "slide_number": i + 3,
            "type": "product_card",
            "heading": product.name,
            "price": f"${product.price_usd:.0f}",
            "description": product.description_short,
            "key_stats": product.key_stats,
            "visual": {
                "type": "product_hero",
                "concept": product.icon_concept,
                "accent_color": product.color_accent,
            },
            "speaker_notes": f"{product.name}: {product.description_long}",
        })

    # Slide 9: Bundle offer
    bundle = PRODUCT_MAP["bundle"]
    slides.append({
        "slide_number": len(products) + 3,
        "type": "bundle_offer",
        "heading": "Save 36% with the Complete Bundle",
        "original_price": "$155",
        "bundle_price": "$99",
        "savings": "$56",
        "includes": [p.name for p in products if p.id != "bundle"],
        "visual": {
            "type": "pricing_comparison",
            "concept": "Side-by-side: individual prices stacked vs bundle price with gold 'SAVE 36%' badge",
            "accent_color": BRAND["colors"]["accent_gold"],
        },
        "speaker_notes": (
            "If you want the whole stack, the bundle saves you 36 percent. "
            "All five products, one download, one price."
        ),
    })

    # Slide 10: CTA
    slides.append({
        "slide_number": len(products) + 4,
        "type": "cta",
        "heading": "Start Building Safer AI Today",
        "primary_cta": "Get the Complete Bundle -- $99",
        "secondary_cta": "Browse Individual Products",
        "social_proof": BRAND["social_proof"],
        "contact": {
            "github": "github.com/issdandavis/SCBE-AETHERMOORE",
            "email": "issdandavis7795@aethermoorgames.com",
        },
        "visual": {
            "type": "cta_block",
            "concept": "Bold CTA with all product icons below, golden glow, 'Patent Pending' badge",
            "accent_color": BRAND["colors"]["accent_gold"],
        },
        "speaker_notes": (
            "Links are live. 30-day money-back guarantee on everything. "
            "Open-source core on GitHub if you want to explore first."
        ),
    })

    return slides


def _get_problem_statements(product: Product) -> List[str]:
    """Return problem bullets tailored to each product category."""
    problems = {
        "automation": [
            "AI workflows run without safety checks -- one bad API call can publish harmful content to thousands",
            "Building governance into n8n/Zapier/Make requires custom code at every node",
            "No standard way to audit what your automation actually did last Tuesday",
            "Disconnected tools mean disconnected data -- Notion says one thing, your pipeline does another",
        ],
        "ai-safety": [
            "Current AI guardrails are keyword filters -- sophisticated attacks bypass them trivially",
            "No mathematical framework means governance is opinion-based and inconsistent",
            "Multi-agent systems multiply risk: 5 agents x 3 tools each = 15 ungoverned attack surfaces",
            "Compliance teams cannot audit what they cannot measure",
        ],
        "content": [
            "Creating content for 7 platforms means rewriting the same idea 7 times",
            "Content calendars are always behind because volume is unsustainable for solo creators",
            "AI-generated content without quality gates floods channels with mediocre output",
            "No connection between your content strategy and your product strategy",
        ],
        "agent-framework": [
            "Multi-agent systems are powerful but one rogue agent can compromise the entire fleet",
            "Starting from scratch every time: defining roles, prompts, coordination, and safety rules",
            "No standard templates mean every team reinvents agent governance",
            "Production agent failures are expensive -- customers see them in real time",
        ],
        "workspace": [
            "AI teams use generic project management tools that do not understand governance",
            "Risk data lives in spreadsheets, bug data in Jira, compliance data in Word docs",
            "No single view of operational health across the AI stack",
            "Onboarding new team members takes weeks because context is scattered everywhere",
        ],
        "bundle": [
            "Building an AI operations stack from scratch takes months and costs thousands",
            "Individual tools do not talk to each other -- governance gaps between systems",
            "No coherent framework connecting workflows, safety, content, agents, and operations",
            "Enterprise governance solutions start at $50K/year and still miss mathematical rigor",
        ],
    }
    return problems.get(product.category, problems["ai-safety"])


def _get_feature_list(product: Product) -> List[Dict[str, str]]:
    """Return feature list tailored to each product."""
    features = {
        "n8n": [
            {"name": "12 Production Workflows", "desc": "Content publishing, web research, data ingestion, LLM dispatch, and more"},
            {"name": "FastAPI Governance Bridge", "desc": "Every operation passes through /v1/governance/scan before execution"},
            {"name": "7-Platform Publishing", "desc": "Twitter, LinkedIn, Bluesky, Mastodon, Medium, GitHub, HuggingFace"},
            {"name": "Telegram Integration", "desc": "Route messages through governance before forwarding to any destination"},
            {"name": "Vertex AI + HuggingFace", "desc": "Push training data and trigger model runs with built-in safety"},
            {"name": "Import Script", "desc": "One command to load all 12 workflows into your n8n instance"},
        ],
        "governance": [
            {"name": "14-Layer Calculator", "desc": "Feed in agent state, get ALLOW/QUARANTINE/ESCALATE/DENY with scores"},
            {"name": "Hyperbolic Cost Model", "desc": "H(d,R) = R^(d^2) -- adversarial cost scales exponentially"},
            {"name": "5 Risk Templates", "desc": "Pre-configured for chatbots, code agents, research, moderation, fleets"},
            {"name": "200+ Threat Patterns", "desc": "Categorized library: prompt injection, exfiltration, escalation, social engineering"},
            {"name": "4 Integration Examples", "desc": "Drop-in code for LangChain, OpenAI, FastAPI, n8n"},
            {"name": "Zero Dependencies", "desc": "Pure Python stdlib -- no pip install, no version conflicts"},
        ],
        "spin": [
            {"name": "Fibonacci Relay Engine", "desc": "1 speaker -> 3 listeners -> 9 -> 27: mathematical content branching"},
            {"name": "29-Node Topic Graph", "desc": "Pre-built knowledge graph for natural conversation pivoting"},
            {"name": "7 Platform Voices", "desc": "Auto-adapted tone, length, and structure per platform"},
            {"name": "4D Context Vectors", "desc": "Time, context, Fibonacci phase, harmonic frequency per piece"},
            {"name": "Governance Quality Gate", "desc": "Every variation scored before entering the publish queue"},
            {"name": "Shopify Bridge", "desc": "Connect output directly to your store blog and product pages"},
        ],
        "hydra": [
            {"name": "5 Swarm Templates", "desc": "Browser research, content publishing, code review, data ingestion, support"},
            {"name": "21 Agent Roles", "desc": "Pre-defined roles with system prompts, capabilities, and boundaries"},
            {"name": "15 Prompt Patterns", "desc": "Intent declaration, drift detection, trust tubes, fleet heartbeat, and more"},
            {"name": "Governance Configs", "desc": "YAML-based threshold configs for each swarm pattern"},
            {"name": "Working Examples", "desc": "Python example code for each template -- run it, see it work"},
            {"name": "Role Validation", "desc": "Built-in tests that verify agent roles stay within bounds"},
        ],
        "notion": [
            {"name": "6 Databases", "desc": "Projects, Bugs, Releases, Revenue, People, Knowledge Base"},
            {"name": "Governance Fields", "desc": "Trust scores, risk decisions, and compliance status on every record"},
            {"name": "5 Page Templates", "desc": "Review checklist, incident playbook, onboarding, publishing, sprint planning"},
            {"name": "Daily Ops Dashboard", "desc": "Single-page view: key metrics, active issues, pending releases, revenue"},
            {"name": "CSV Import Ready", "desc": "Import databases directly into your Notion workspace"},
            {"name": "Setup Guide", "desc": "Step-by-step instructions from import to customization"},
        ],
        "bundle": [
            {"name": "All 5 Products", "desc": "n8n workflows, governance toolkit, content engine, agent templates, Notion workspace"},
            {"name": "36% Savings", "desc": "$155 value for $99 -- save $56 vs buying individually"},
            {"name": "Integrated Stack", "desc": "Products designed to work together: governance flows through everything"},
            {"name": "Bundle README", "desc": "Recommended setup order and integration guide"},
            {"name": "Priority Support", "desc": "Direct access for setup help and customization guidance"},
            {"name": "Future Updates", "desc": "Receive updates to all included products"},
        ],
    }
    return features.get(product.id, features["governance"])


def _get_price_context(product: Product) -> str:
    """Return pricing context for each product."""
    context = {
        "n8n": "Less than a single hour of consultant time to set up custom n8n governance",
        "governance": "Enterprise governance solutions start at $50K/year. This is $29, once.",
        "spin": "Cheaper than one month of any social media scheduling tool",
        "hydra": "A coffee costs more. 21 agent roles for $9.",
        "notion": "Less than one month of a project management tool subscription",
        "bundle": "The complete AI operations stack for less than a nice dinner out. $155 value, $99 price.",
    }
    return context.get(product.id, "One-time purchase. No subscriptions.")


# ---------------------------------------------------------------------------
#  Social Card / Open Graph Generator
# ---------------------------------------------------------------------------

def generate_social_cards(products: List[Product]) -> Dict[str, Any]:
    """Generate Open Graph, Twitter Card, and LinkedIn post specs."""
    cards: Dict[str, Any] = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "cards": [],
    }

    for product in products:
        card = {
            "product_id": product.id,
            "product_name": product.name,
            "slug": product.slug,

            # Open Graph (Facebook, LinkedIn, Discord, Slack)
            "open_graph": {
                "og:title": product.name,
                "og:description": product.description_short,
                "og:type": "product",
                "og:image": f"https://aethermoorgames.com/images/{product.slug}-og.png",
                "og:image:width": str(IMAGE_SPECS["og_image"]["width"]),
                "og:image:height": str(IMAGE_SPECS["og_image"]["height"]),
                "og:image:alt": f"{product.name} -- {product.description_short}",
                "og:url": f"https://aethermoorgames.gumroad.com/l/{product.slug}",
                "og:site_name": "AethermoorGames",
                "og:locale": "en_US",
                "product:price:amount": f"{product.price_usd:.2f}",
                "product:price:currency": "USD",
            },

            # Twitter Card
            "twitter_card": {
                "twitter:card": "summary_large_image",
                "twitter:title": product.name,
                "twitter:description": product.description_short,
                "twitter:image": f"https://aethermoorgames.com/images/{product.slug}-twitter.png",
                "twitter:image:alt": f"{product.name} -- {product.description_short}",
                "twitter:site": "@AethermoorGames",
                "twitter:creator": "@issdandavis",
            },

            # LinkedIn (structured post data)
            "linkedin": {
                "title": product.name,
                "description": product.description_short,
                "image_url": f"https://aethermoorgames.com/images/{product.slug}-og.png",
                "image_dimensions": IMAGE_SPECS["linkedin_post"],
                "hashtags": [f"#{t.replace(' ', '')}" for t in product.tags[:5]],
                "post_template": (
                    f"{product.name}\n\n"
                    f"{product.description_short}\n\n"
                    f"{product.description_long[:200]}...\n\n"
                    f"${product.price_usd:.0f} | 30-day money-back guarantee\n\n"
                    + " ".join([f"#{t.replace(' ', '')}" for t in product.tags[:5]])
                ),
            },

            # Image generation specs
            "image_specs": {
                "og_image": {
                    "dimensions": IMAGE_SPECS["og_image"],
                    "filename": f"{product.slug}-og.png",
                    "design_ref": f"canva_{product.id}_social_card",
                },
                "twitter_image": {
                    "dimensions": IMAGE_SPECS["twitter_card"],
                    "filename": f"{product.slug}-twitter.png",
                    "design_ref": f"canva_{product.id}_social_card",
                    "note": "Crop OG image to 1200x600 or generate dedicated",
                },
                "linkedin_image": {
                    "dimensions": IMAGE_SPECS["linkedin_post"],
                    "filename": f"{product.slug}-linkedin.png",
                    "design_ref": f"canva_{product.id}_social_card",
                    "note": "Same as OG image (1200x627 vs 1200x630 -- negligible)",
                },
            },

            "status": "spec_ready",
        }
        cards["cards"].append(card)

    cards["total_cards"] = len(cards["cards"])
    return cards


# ---------------------------------------------------------------------------
#  Visual Manifest (Master Tracker)
# ---------------------------------------------------------------------------

def build_visual_manifest(
    canva_specs: Dict[str, Any],
    gamma_decks: Dict[str, Any],
    social_cards: Dict[str, Any],
    products: List[Product],
) -> Dict[str, Any]:
    """Build the master visual manifest that tracks all assets and their status."""
    manifest: Dict[str, Any] = {
        "manifest_version": "1.0.0",
        "generated": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/content_visuals.py",
        "brand": {
            "name": BRAND["name"],
            "tagline": BRAND["tagline"],
            "patent": BRAND["patent"],
        },
        "summary": {
            "total_products": len(products),
            "total_canva_designs": canva_specs["total_designs"],
            "total_gamma_decks": gamma_decks["total_decks"],
            "total_social_cards": social_cards["total_cards"],
            "total_visual_assets": (
                canva_specs["total_designs"]
                + gamma_decks["total_decks"]
                + social_cards["total_cards"]
            ),
        },
        "products": [],
        "asset_index": [],
        "status_counts": {
            "spec_ready": 0,
            "outline_ready": 0,
            "in_progress": 0,
            "completed": 0,
            "uploaded": 0,
        },
        "next_steps": [
            "1. Open Canva and create designs from canva_specs.json",
            "2. Export as PNG/WEBP and place in artifacts/visuals/exports/",
            "3. Upload to Gumroad product listings",
            "4. Open Gamma.app and create decks from gamma_decks.json",
            "5. Set Open Graph meta tags from social_cards.json on product pages",
            "6. Update this manifest with 'completed' status for each asset",
        ],
    }

    # Per-product summary
    for product in products:
        product_entry = {
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "price_usd": product.price_usd,
            "visual_assets": [],
        }

        # Canva designs for this product
        for design in canva_specs["designs"]:
            if design["product_id"] == product.id:
                asset = {
                    "asset_id": design["design_id"],
                    "type": "canva_design",
                    "format": design["format"],
                    "dimensions": design["dimensions"],
                    "status": design["status"],
                    "file": None,
                }
                product_entry["visual_assets"].append(asset)
                manifest["asset_index"].append({
                    **asset,
                    "product_id": product.id,
                    "product_name": product.name,
                })
                manifest["status_counts"][design["status"]] = (
                    manifest["status_counts"].get(design["status"], 0) + 1
                )

        # Gamma deck for this product
        for deck in gamma_decks["decks"]:
            if deck["product_id"] == product.id:
                asset = {
                    "asset_id": deck["deck_id"],
                    "type": "gamma_deck",
                    "format": "presentation",
                    "slide_count": len(deck["slides"]),
                    "status": deck["status"],
                    "file": None,
                }
                product_entry["visual_assets"].append(asset)
                manifest["asset_index"].append({
                    **asset,
                    "product_id": product.id,
                    "product_name": product.name,
                })
                manifest["status_counts"][deck["status"]] = (
                    manifest["status_counts"].get(deck["status"], 0) + 1
                )

        # Social cards for this product
        for card in social_cards["cards"]:
            if card["product_id"] == product.id:
                for img_key, img_spec in card["image_specs"].items():
                    asset = {
                        "asset_id": f"social_{product.id}_{img_key}",
                        "type": "social_card",
                        "format": img_key,
                        "dimensions": img_spec["dimensions"],
                        "filename": img_spec["filename"],
                        "status": card["status"],
                        "file": None,
                    }
                    product_entry["visual_assets"].append(asset)
                    manifest["asset_index"].append({
                        **asset,
                        "product_id": product.id,
                        "product_name": product.name,
                    })
                    manifest["status_counts"][card["status"]] = (
                        manifest["status_counts"].get(card["status"], 0) + 1
                    )

        manifest["products"].append(product_entry)

    # Catalog deck (not tied to a single product)
    for deck in gamma_decks["decks"]:
        if deck["product_id"] == "catalog":
            manifest["asset_index"].append({
                "asset_id": deck["deck_id"],
                "type": "gamma_deck",
                "format": "presentation",
                "slide_count": len(deck["slides"]),
                "status": deck["status"],
                "product_id": "catalog",
                "product_name": "Full Catalog Overview",
            })
            manifest["status_counts"][deck["status"]] = (
                manifest["status_counts"].get(deck["status"], 0) + 1
            )

    manifest["total_tracked_assets"] = len(manifest["asset_index"])
    return manifest


# ---------------------------------------------------------------------------
#  Canva API Integration (stub + real)
# ---------------------------------------------------------------------------

def push_to_canva_api(specs: Dict[str, Any]) -> Dict[str, Any]:
    """Push design specs to Canva via API or Zapier MCP.

    This is a stub that documents the integration path.
    When CANVA_API_KEY is set or --canva-api is passed, it will use the real API.
    """
    api_key = os.environ.get("CANVA_API_KEY")

    if not api_key:
        print("\n  [CANVA] No CANVA_API_KEY found. Generating offline specs only.")
        print("  [CANVA] To use the Canva API:")
        print("    1. Get an API key from https://www.canva.dev/")
        print("    2. Set CANVA_API_KEY in your environment")
        print("    3. Run: python scripts/content_visuals.py --canva-api")
        print("  [CANVA] Alternatively, use Zapier MCP tools (canva_create_design)")
        print("  [CANVA] Manual workflow:")
        print("    1. Open canva_specs.json")
        print("    2. Create each design in Canva using the specs as a guide")
        print("    3. Use brand colors, fonts, and layout specs provided")
        print("    4. Export as PNG and place in artifacts/visuals/exports/")
        return {"status": "offline", "designs_pushed": 0}

    # Real API integration (when key is available)
    print(f"\n  [CANVA] API key found. Pushing {len(specs['designs'])} designs...")
    results = []
    for design in specs["designs"]:
        # Canva API v1: POST /v1/designs
        # This is the request shape Canva expects
        payload = {
            "design_type": "custom",
            "width": design["dimensions"]["width"],
            "height": design["dimensions"]["height"],
            "title": f"{design['product_name']} - {design['format']}",
            "asset_id": design["design_id"],
        }
        # In production: requests.post("https://api.canva.com/v1/designs", ...)
        results.append({
            "design_id": design["design_id"],
            "status": "api_stub",
            "payload": payload,
        })
        print(f"    [STUB] Would push: {design['design_id']}")

    return {"status": "api_stub", "designs_pushed": len(results), "results": results}


# ---------------------------------------------------------------------------
#  Gamma API Integration (stub + real)
# ---------------------------------------------------------------------------

def push_to_gamma_api(decks: Dict[str, Any]) -> Dict[str, Any]:
    """Push slide deck outlines to Gamma.app API.

    Gamma does not yet have a public create-from-JSON API, so this generates
    structured outlines that can be pasted into Gamma's AI deck builder.
    When the API becomes available, this function will use it directly.
    """
    api_key = os.environ.get("GAMMA_API_KEY")

    if not api_key:
        print("\n  [GAMMA] No GAMMA_API_KEY found. Generating offline outlines only.")
        print("  [GAMMA] To create decks in Gamma:")
        print("    1. Open https://gamma.app/create")
        print("    2. Select 'Presentation' and paste the outline from gamma_decks.json")
        print("    3. Gamma's AI will generate slides from the structured content")
        print("    4. Apply dark theme and customize with brand colors")
        print("  [GAMMA] Tip: Use 'Generate from outline' mode for best results")
        return {"status": "offline", "decks_pushed": 0}

    print(f"\n  [GAMMA] API key found. Pushing {len(decks['decks'])} decks...")
    results = []
    for deck in decks["decks"]:
        # Generate a paste-ready outline for Gamma's AI builder
        outline_text = _deck_to_gamma_outline(deck)
        results.append({
            "deck_id": deck["deck_id"],
            "status": "api_stub",
            "outline_length": len(outline_text),
        })
        print(f"    [STUB] Would push: {deck['deck_id']} ({len(deck['slides'])} slides)")

    return {"status": "api_stub", "decks_pushed": len(results), "results": results}


def _deck_to_gamma_outline(deck: Dict[str, Any]) -> str:
    """Convert a deck structure to a paste-ready outline for Gamma.app."""
    lines = [f"# {deck['title']}", ""]

    for slide in deck["slides"]:
        lines.append(f"## Slide {slide['slide_number']}: {slide['heading']}")

        if "subheading" in slide:
            lines.append(f"*{slide['subheading']}*")

        if "body" in slide:
            lines.append(f"\n{slide['body']}")

        if "bullets" in slide:
            for bullet in slide["bullets"]:
                lines.append(f"- {bullet}")

        if "features" in slide:
            for feat in slide["features"]:
                lines.append(f"- **{feat['name']}**: {feat['desc']}")

        if "key_differentiator" in slide:
            lines.append(f"\n> {slide['key_differentiator']}")

        if "price" in slide:
            lines.append(f"\n**Price: {slide['price']}**")
            if "price_context" in slide:
                lines.append(f"_{slide['price_context']}_")

        if "social_proof" in slide:
            lines.append("")
            for proof in slide["social_proof"]:
                lines.append(f'> "{proof}"')

        if "speaker_notes" in slide:
            lines.append(f"\n_Speaker notes: {slide['speaker_notes']}_")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Canva + Gamma content pipeline for SCBE product visuals",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/content_visuals.py                  # Generate all specs\n"
            "  python scripts/content_visuals.py --canva-api      # Push to Canva API\n"
            "  python scripts/content_visuals.py --gamma-api      # Push to Gamma API\n"
            "  python scripts/content_visuals.py --product n8n    # Single product\n"
            "  python scripts/content_visuals.py --list           # Show product list\n"
        ),
    )
    parser.add_argument("--canva-api", action="store_true", help="Push designs to Canva API (requires CANVA_API_KEY)")
    parser.add_argument("--gamma-api", action="store_true", help="Push decks to Gamma API (requires GAMMA_API_KEY)")
    parser.add_argument("--product", type=str, default=None, help="Generate for a single product (by id)")
    parser.add_argument("--list", action="store_true", help="List all products and visual status")
    parser.add_argument("--output-dir", type=str, default=None, help="Override output directory")

    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else VISUALS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter products if --product is specified
    if args.product:
        if args.product not in PRODUCT_MAP:
            print(f"  ERROR: Unknown product '{args.product}'")
            print(f"  Available: {', '.join(PRODUCT_MAP.keys())}")
            sys.exit(1)
        products = [PRODUCT_MAP[args.product]]
        print(f"\n  Generating visuals for: {args.product}")
    else:
        products = PRODUCTS

    # --list mode
    if args.list:
        _print_product_list(output_dir)
        return

    # =====================================================================
    #  Generate all specs
    # =====================================================================

    print(f"\n{'='*70}")
    print(f"  SCBE CONTENT VISUALS PIPELINE")
    print(f"  Canva + Gamma + Social Cards")
    print(f"{'='*70}")

    # 1. Canva Specs
    print(f"\n  [1/4] Generating Canva design specs...")
    canva_specs = generate_canva_specs(products)
    canva_path = output_dir / "canva_specs.json"
    _write_json(canva_path, canva_specs)
    print(f"    -> {canva_specs['total_designs']} designs written to {canva_path.name}")

    # 2. Gamma Decks
    print(f"\n  [2/4] Generating Gamma slide deck outlines...")
    gamma_decks = generate_gamma_decks(products)
    gamma_path = output_dir / "gamma_decks.json"
    _write_json(gamma_path, gamma_decks)
    print(f"    -> {gamma_decks['total_decks']} decks written to {gamma_path.name}")

    # Also write paste-ready outlines as plain text
    outlines_dir = output_dir / "gamma_outlines"
    outlines_dir.mkdir(parents=True, exist_ok=True)
    for deck in gamma_decks["decks"]:
        outline = _deck_to_gamma_outline(deck)
        outline_path = outlines_dir / f"{deck['deck_id']}.txt"
        outline_path.write_text(outline, encoding="utf-8")
    print(f"    -> {len(gamma_decks['decks'])} paste-ready outlines in gamma_outlines/")

    # 3. Social Cards
    print(f"\n  [3/4] Generating social card / OG meta specs...")
    social_cards = generate_social_cards(products)
    social_path = output_dir / "social_cards.json"
    _write_json(social_path, social_cards)
    print(f"    -> {social_cards['total_cards']} card specs written to {social_path.name}")

    # 4. Master Manifest
    print(f"\n  [4/4] Building visual manifest...")
    manifest = build_visual_manifest(canva_specs, gamma_decks, social_cards, products)
    manifest_path = output_dir / "visual_manifest.json"
    _write_json(manifest_path, manifest)
    print(f"    -> {manifest['total_tracked_assets']} assets tracked in {manifest_path.name}")

    # =====================================================================
    #  API pushes (if requested)
    # =====================================================================

    if args.canva_api:
        push_to_canva_api(canva_specs)

    if args.gamma_api:
        push_to_gamma_api(gamma_decks)

    # =====================================================================
    #  Summary
    # =====================================================================

    print(f"\n{'='*70}")
    print(f"  PIPELINE COMPLETE")
    print(f"{'='*70}")
    print(f"  Products:        {len(products)}")
    print(f"  Canva designs:   {canva_specs['total_designs']}")
    print(f"  Gamma decks:     {gamma_decks['total_decks']}")
    print(f"  Social cards:    {social_cards['total_cards']}")
    print(f"  Total assets:    {manifest['total_tracked_assets']}")
    print(f"{'='*70}")
    print(f"  Output directory: {output_dir}")
    print(f"  Files:")
    print(f"    canva_specs.json       — Canva design specifications")
    print(f"    gamma_decks.json       — Gamma slide deck outlines")
    print(f"    gamma_outlines/        — Paste-ready deck outlines (.txt)")
    print(f"    social_cards.json      — OG / Twitter / LinkedIn meta")
    print(f"    visual_manifest.json   — Master asset tracker")
    print(f"{'='*70}")

    if not args.canva_api and not args.gamma_api:
        print(f"\n  Next: Use --canva-api or --gamma-api to push to live services")
        print(f"  Or use the JSON specs as manual design briefs.")

    print()


def _print_product_list(output_dir: Path):
    """Print product list with visual asset status."""
    manifest_path = output_dir / "visual_manifest.json"

    print(f"\n{'='*70}")
    print(f"  SCBE PRODUCT VISUAL STATUS")
    print(f"{'='*70}")

    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        for product in manifest.get("products", []):
            asset_count = len(product.get("visual_assets", []))
            completed = sum(
                1 for a in product.get("visual_assets", [])
                if a.get("status") == "completed"
            )
            print(f"\n  [{product['id']}] {product['name']} (${product['price_usd']:.0f})")
            print(f"    Assets: {asset_count} total, {completed} completed")
            for asset in product.get("visual_assets", []):
                status_icon = "+" if asset["status"] == "completed" else "-"
                print(f"    {status_icon} {asset['asset_id']} [{asset['status']}]")

        counts = manifest.get("status_counts", {})
        print(f"\n  Summary: {manifest.get('total_tracked_assets', 0)} total assets")
        for status, count in counts.items():
            if count > 0:
                print(f"    {status}: {count}")
    else:
        print("\n  No manifest found. Run the pipeline first:")
        print("    python scripts/content_visuals.py")
        print()
        for product in PRODUCTS:
            print(f"  [{product.id}] {product.name} (${product.price_usd:.0f})")
            print(f"    {product.description_short}")

    print(f"\n{'='*70}\n")


def _write_json(path: Path, data: Dict[str, Any]):
    """Write JSON with consistent formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
#  Entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
