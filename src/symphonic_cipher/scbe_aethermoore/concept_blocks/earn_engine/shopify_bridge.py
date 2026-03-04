"""
Earn Engine — Shopify Bridge
================================
Connects the in-game shop to Shopify's Storefront API for real product
purchases from within the Aethermoor game.

Architecture:
  Game UI (shop menu) → ShopifyBridge → Shopify Storefront API → Checkout URL
  Player opens checkout URL in browser → completes purchase → webhook callback

Products are organized by Sacred Tongue:
  KO — Authority Packs (governance boosts, leader tokens)
  AV — Transport Bundles (messenger upgrades, relay items)
  RU — Policy Scrolls (rule books, constraint tokens)
  CA — Compute Crystals (power-ups, XP boosters, rare items)
  UM — Shadow Keys (secret areas, hidden creature unlocks)
  DR — Schema Tomes (evolution catalysts, lore compendiums)

The bridge can operate in two modes:
  1. LIVE — connects to real Shopify Storefront API (requires access token)
  2. MOCK — returns mock products/checkout for testing without Shopify
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from ..context_credit_ledger.credit import Denomination


# ---------------------------------------------------------------------------
#  Product Categories (mapped to Sacred Tongues)
# ---------------------------------------------------------------------------

class ProductTongue(str, Enum):
    KO = "KO"   # Authority Packs
    AV = "AV"   # Transport Bundles
    RU = "RU"   # Policy Scrolls
    CA = "CA"   # Compute Crystals
    UM = "UM"   # Shadow Keys
    DR = "DR"   # Schema Tomes


TONGUE_PRODUCT_NAMES: Dict[ProductTongue, str] = {
    ProductTongue.KO: "Authority Pack",
    ProductTongue.AV: "Transport Bundle",
    ProductTongue.RU: "Policy Scroll",
    ProductTongue.CA: "Compute Crystal",
    ProductTongue.UM: "Shadow Key",
    ProductTongue.DR: "Schema Tome",
}


# ---------------------------------------------------------------------------
#  Shop Product (what the game displays)
# ---------------------------------------------------------------------------

@dataclass
class ShopProduct:
    """A product available in the in-game Shopify shop."""
    product_id: str
    name: str
    description: str
    price_cents: int
    currency: str = "USD"
    tongue: ProductTongue = ProductTongue.CA
    image_url: str = ""
    shopify_variant_id: str = ""      # Shopify GID for checkout
    in_game_effects: Dict[str, Any] = field(default_factory=dict)

    @property
    def price_display(self) -> str:
        dollars = self.price_cents / 100
        return f"${dollars:.2f} {self.currency}"


# ---------------------------------------------------------------------------
#  Checkout Session
# ---------------------------------------------------------------------------

@dataclass
class CheckoutSession:
    """Tracks a Shopify checkout initiated from the game."""
    session_id: str
    product: ShopProduct
    checkout_url: str
    created_at: float
    completed: bool = False
    order_id: Optional[str] = None


# ---------------------------------------------------------------------------
#  Mock Product Catalog
# ---------------------------------------------------------------------------

MOCK_CATALOG: List[ShopProduct] = [
    ShopProduct(
        product_id="ko-authority-pack-1",
        name="Kor'aelin Authority Pack",
        description="Boosts governance power. +50 XP, unlocks Authority Aura spell.",
        price_cents=499,
        tongue=ProductTongue.KO,
        in_game_effects={"xp_bonus": 50, "unlock_spell": "Authority Aura"},
    ),
    ShopProduct(
        product_id="av-relay-bundle-1",
        name="Avali Relay Bundle",
        description="Speed boost + messenger companion. +20% encounter rate for rare creatures.",
        price_cents=399,
        tongue=ProductTongue.AV,
        in_game_effects={"rare_boost": 0.20, "speed_bonus": 5},
    ),
    ShopProduct(
        product_id="ru-policy-scroll-1",
        name="Runethic Policy Scroll",
        description="Learn advanced constraint magic. Unlocks Policy Shield move.",
        price_cents=299,
        tongue=ProductTongue.RU,
        in_game_effects={"unlock_spell": "Policy Shield"},
    ),
    ShopProduct(
        product_id="ca-compute-crystal-1",
        name="Cassisivadan Compute Crystal",
        description="2x XP for 1 hour. Boosts all compute-tongue creatures.",
        price_cents=599,
        tongue=ProductTongue.CA,
        in_game_effects={"xp_multiplier": 2.0, "duration_minutes": 60},
    ),
    ShopProduct(
        product_id="um-shadow-key-1",
        name="Umbroth Shadow Key",
        description="Unlocks the Hidden Marsh. Access to 3 secret creatures.",
        price_cents=799,
        tongue=ProductTongue.UM,
        in_game_effects={"unlock_zone": "hidden_marsh", "unlock_creatures": 3},
    ),
    ShopProduct(
        product_id="dr-schema-tome-1",
        name="Draumric Schema Tome",
        description="Evolution catalyst. Instantly evolve any Champion to Ultimate.",
        price_cents=999,
        tongue=ProductTongue.DR,
        in_game_effects={"instant_evolve_to": "Ultimate"},
    ),
    ShopProduct(
        product_id="starter-bundle",
        name="Starter Bundle",
        description="10 catch balls, 5 potions, 100 bonus XP. Perfect for new players.",
        price_cents=199,
        tongue=ProductTongue.KO,
        in_game_effects={"catch_balls": 10, "potions": 5, "xp_bonus": 100},
    ),
    ShopProduct(
        product_id="sft-training-pack",
        name="SFT Training Data Pack",
        description="500 curated SFT pairs from Aethermoor gameplay. Train your own AI.",
        price_cents=1499,
        tongue=ProductTongue.DR,
        in_game_effects={"training_pairs": 500, "type": "digital_download"},
    ),
]


# ---------------------------------------------------------------------------
#  Shopify Bridge
# ---------------------------------------------------------------------------

class ShopifyBridge:
    """
    Bridge between the in-game shop and Shopify Storefront API.

    In MOCK mode: returns mock products and fake checkout URLs.
    In LIVE mode: calls Shopify Storefront API via GraphQL.
    """

    def __init__(
        self,
        store_domain: str = "",
        storefront_token: str = "",
        live: bool = False,
    ):
        self.store_domain = store_domain
        self.storefront_token = storefront_token
        self.live = live and bool(store_domain) and bool(storefront_token)
        self._catalog: List[ShopProduct] = list(MOCK_CATALOG)
        self._sessions: Dict[str, CheckoutSession] = {}

    # --- Catalog ---

    def get_catalog(self, tongue: Optional[str] = None) -> List[ShopProduct]:
        """Get available products, optionally filtered by tongue."""
        if tongue:
            return [p for p in self._catalog if p.tongue.value == tongue]
        return list(self._catalog)

    def get_product(self, product_id: str) -> Optional[ShopProduct]:
        """Look up a product by ID."""
        for p in self._catalog:
            if p.product_id == product_id:
                return p
        return None

    # --- Checkout ---

    def create_checkout(self, product_id: str) -> Optional[CheckoutSession]:
        """
        Create a checkout session for a product.

        In MOCK mode: generates a fake checkout URL.
        In LIVE mode: would call Shopify Storefront API checkoutCreate mutation.
        """
        product = self.get_product(product_id)
        if product is None:
            return None

        session_id = uuid.uuid4().hex[:16]

        if self.live:
            checkout_url = self._create_live_checkout(product)
        else:
            checkout_url = self._create_mock_checkout(product, session_id)

        session = CheckoutSession(
            session_id=session_id,
            product=product,
            checkout_url=checkout_url,
            created_at=time.time(),
        )
        self._sessions[session_id] = session
        return session

    def complete_checkout(self, session_id: str, order_id: str = "") -> bool:
        """Mark a checkout as completed (called by webhook)."""
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session.completed = True
        session.order_id = order_id or f"mock-order-{uuid.uuid4().hex[:8]}"
        return True

    def get_session(self, session_id: str) -> Optional[CheckoutSession]:
        """Get a checkout session by ID."""
        return self._sessions.get(session_id)

    # --- Internal ---

    def _create_mock_checkout(self, product: ShopProduct, session_id: str) -> str:
        """Generate a mock checkout URL for testing."""
        params = urlencode({
            "product": product.product_id,
            "session": session_id,
            "price": product.price_cents,
        })
        return f"https://mock-shop.aethermoore.local/checkout?{params}"

    def _create_live_checkout(self, product: ShopProduct) -> str:
        """
        Create a real Shopify checkout via Storefront API.

        Uses the checkoutCreate GraphQL mutation.
        Returns the checkout webUrl.

        NOTE: This is a stub — full implementation requires httpx/aiohttp
        to call the Storefront API. The GraphQL query is included for reference.
        """
        # GraphQL mutation for reference:
        # mutation {
        #   checkoutCreate(input: {
        #     lineItems: [{ variantId: "gid://shopify/ProductVariant/...", quantity: 1 }]
        #   }) {
        #     checkout { webUrl }
        #     checkoutUserErrors { message }
        #   }
        # }

        # For now, return a direct product URL
        return f"https://{self.store_domain}/cart/{product.shopify_variant_id}:1"

    # --- Catalog Management ---

    def add_product(self, product: ShopProduct) -> None:
        """Add a product to the local catalog."""
        self._catalog.append(product)

    def remove_product(self, product_id: str) -> bool:
        """Remove a product from the local catalog."""
        before = len(self._catalog)
        self._catalog = [p for p in self._catalog if p.product_id != product_id]
        return len(self._catalog) < before

    def catalog_stats(self) -> Dict[str, Any]:
        """Summary of the product catalog."""
        by_tongue: Dict[str, int] = {}
        total_value = 0
        for p in self._catalog:
            by_tongue[p.tongue.value] = by_tongue.get(p.tongue.value, 0) + 1
            total_value += p.price_cents
        return {
            "total_products": len(self._catalog),
            "by_tongue": by_tongue,
            "total_catalog_value_cents": total_value,
            "active_sessions": len(self._sessions),
            "completed_sessions": sum(1 for s in self._sessions.values() if s.completed),
        }
