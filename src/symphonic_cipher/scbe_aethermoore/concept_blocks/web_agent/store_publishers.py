"""
SCBE Store Publishers — Gumroad + Shopify API Automation
=========================================================

Automate product listing, updates, and storefront management for:
- Gumroad: Digital products (SFT datasets, training packs, game assets, ebooks)
- Shopify: Full storefront (merch, digital goods, courses, subscriptions)

Both use direct REST APIs — no browser needed, zero delays.

Usage:
    gumroad = GumroadPublisher(api_token="your_token")
    result = await gumroad.create_product(
        name="Spiralverse AI Training Pack",
        price=49_99,  # cents
        description="...",
    )

    shopify = ShopifyPublisher(shop="your-store", token="your_token")
    result = await shopify.create_product(
        title="SCBE Governance Toolkit",
        body_html="<p>...</p>",
        variants=[{"price": "29.99", "sku": "SCBE-001"}],
    )
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ---------------------------------------------------------------------------
#  Shared types
# ---------------------------------------------------------------------------

class StoreType(str, Enum):
    GUMROAD = "gumroad"
    SHOPIFY = "shopify"


@dataclass
class StoreResult:
    """Result from a store API call."""
    success: bool
    store: str
    action: str
    product_id: Optional[str] = None
    product_url: Optional[str] = None
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class ProductSpec:
    """Universal product specification that maps to any store."""
    name: str
    price_cents: int                          # Price in cents (4999 = $49.99)
    description: str = ""
    tags: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)   # URLs or file paths
    files: List[str] = field(default_factory=list)     # Digital download files
    sku: Optional[str] = None
    category: Optional[str] = None
    is_digital: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def price_dollars(self) -> str:
        return f"{self.price_cents / 100:.2f}"


# ---------------------------------------------------------------------------
#  Gumroad Publisher
# ---------------------------------------------------------------------------

class GumroadPublisher:
    """
    Gumroad API client for digital product management.

    API docs: https://gumroad.com/api
    Base URL: https://api.gumroad.com/v2

    Supports:
    - Create / update / delete products
    - Upload digital files
    - List products and sales
    - Manage variants and pricing
    """

    BASE_URL = "https://api.gumroad.com/v2"

    def __init__(self, api_token: Optional[str] = None):
        if not HAS_REQUESTS:
            raise RuntimeError("requests not installed. Run: pip install requests")
        self.token = api_token or os.environ.get("GUMROAD_API_TOKEN", "")
        if not self.token:
            raise ValueError(
                "Gumroad API token required. Set GUMROAD_API_TOKEN env var "
                "or pass api_token parameter. "
                "Get one at: https://app.gumroad.com/settings/advanced#application-form"
            )

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an API request to Gumroad."""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        resp = requests.request(method, url, headers=self._headers(), **kwargs)
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        data["_status_code"] = resp.status_code
        return data

    # -- Products -------------------------------------------------------------

    def create_product(
        self,
        name: str,
        price_cents: int,
        description: str = "",
        tags: Optional[List[str]] = None,
        preview_url: Optional[str] = None,
        is_published: bool = True,
    ) -> StoreResult:
        """Create a new product on Gumroad."""
        t0 = time.time()
        payload = {
            "name": name,
            "price": price_cents,
            "description": description,
            "published": is_published,
        }
        if preview_url:
            payload["preview_url"] = preview_url
        if tags:
            payload["tags"] = ",".join(tags)

        data = self._request("POST", "/products", data=payload)
        success = data.get("success", False)
        product = data.get("product", {})

        return StoreResult(
            success=success,
            store="gumroad",
            action="create_product",
            product_id=product.get("id"),
            product_url=product.get("short_url"),
            data=product,
            error=data.get("message") if not success else None,
            duration_ms=(time.time() - t0) * 1000,
        )

    def update_product(self, product_id: str, **updates) -> StoreResult:
        """Update an existing product."""
        t0 = time.time()
        data = self._request("PUT", f"/products/{product_id}", data=updates)
        success = data.get("success", False)
        product = data.get("product", {})
        return StoreResult(
            success=success, store="gumroad", action="update_product",
            product_id=product_id, data=product,
            error=data.get("message") if not success else None,
            duration_ms=(time.time() - t0) * 1000,
        )

    def delete_product(self, product_id: str) -> StoreResult:
        """Delete a product."""
        t0 = time.time()
        data = self._request("DELETE", f"/products/{product_id}")
        return StoreResult(
            success=data.get("success", False), store="gumroad",
            action="delete_product", product_id=product_id,
            error=data.get("message") if not data.get("success") else None,
            duration_ms=(time.time() - t0) * 1000,
        )

    def list_products(self) -> StoreResult:
        """List all products."""
        t0 = time.time()
        data = self._request("GET", "/products")
        return StoreResult(
            success=data.get("success", False), store="gumroad",
            action="list_products",
            data=data.get("products", []),
            duration_ms=(time.time() - t0) * 1000,
        )

    def get_sales(self, product_id: Optional[str] = None,
                  page: int = 1) -> StoreResult:
        """Get sales data."""
        t0 = time.time()
        params = {"page": page}
        if product_id:
            params["product_id"] = product_id
        data = self._request("GET", "/sales", params=params)
        return StoreResult(
            success=data.get("success", False), store="gumroad",
            action="get_sales", data=data.get("sales", []),
            duration_ms=(time.time() - t0) * 1000,
        )

    def create_from_spec(self, spec: ProductSpec) -> StoreResult:
        """Create a product from a universal ProductSpec."""
        return self.create_product(
            name=spec.name,
            price_cents=spec.price_cents,
            description=spec.description,
            tags=spec.tags,
            preview_url=spec.images[0] if spec.images else None,
        )


# ---------------------------------------------------------------------------
#  Shopify Publisher
# ---------------------------------------------------------------------------

class ShopifyPublisher:
    """
    Shopify Admin REST API client for storefront management.

    API docs: https://shopify.dev/docs/api/admin-rest
    Base URL: https://{shop}.myshopify.com/admin/api/2024-01

    Supports:
    - Create / update / delete products
    - Manage variants, images, inventory
    - Collections and tags
    - Orders and customers (read)
    - Theme customization
    """

    API_VERSION = "2024-01"

    def __init__(
        self,
        shop: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        if not HAS_REQUESTS:
            raise RuntimeError("requests not installed. Run: pip install requests")
        self.shop = shop or os.environ.get("SHOPIFY_SHOP", "")
        self.token = access_token or os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
        if not self.shop or not self.token:
            raise ValueError(
                "Shopify shop name and access token required. "
                "Set SHOPIFY_SHOP and SHOPIFY_ACCESS_TOKEN env vars."
            )

    @property
    def base_url(self) -> str:
        shop = self.shop.replace(".myshopify.com", "")
        return f"https://{shop}.myshopify.com/admin/api/{self.API_VERSION}"

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Shopify-Access-Token": self.token,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an API request to Shopify."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        resp = requests.request(method, url, headers=self._headers(), **kwargs)
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        data["_status_code"] = resp.status_code
        return data

    # -- Products -------------------------------------------------------------

    def create_product(
        self,
        title: str,
        body_html: str = "",
        vendor: str = "SCBE-AETHERMOORE",
        product_type: str = "",
        tags: Optional[List[str]] = None,
        variants: Optional[List[Dict[str, Any]]] = None,
        images: Optional[List[Dict[str, str]]] = None,
        status: str = "active",
    ) -> StoreResult:
        """Create a new product on Shopify."""
        t0 = time.time()
        product_data: Dict[str, Any] = {
            "title": title,
            "body_html": body_html,
            "vendor": vendor,
            "product_type": product_type,
            "status": status,
        }
        if tags:
            product_data["tags"] = ", ".join(tags)
        if variants:
            product_data["variants"] = variants
        if images:
            product_data["images"] = images

        data = self._request("POST", "/products.json",
                             json={"product": product_data})
        product = data.get("product", {})
        success = "_status_code" in data and data["_status_code"] in (200, 201)

        return StoreResult(
            success=success,
            store="shopify",
            action="create_product",
            product_id=str(product.get("id", "")),
            product_url=f"https://{self.shop}.myshopify.com/products/{product.get('handle', '')}",
            data=product,
            error=str(data.get("errors", "")) if not success else None,
            duration_ms=(time.time() - t0) * 1000,
        )

    def update_product(self, product_id: str, **updates) -> StoreResult:
        """Update an existing product."""
        t0 = time.time()
        data = self._request("PUT", f"/products/{product_id}.json",
                             json={"product": {"id": int(product_id), **updates}})
        success = data.get("_status_code") in (200, 201)
        return StoreResult(
            success=success, store="shopify", action="update_product",
            product_id=product_id, data=data.get("product", {}),
            error=str(data.get("errors", "")) if not success else None,
            duration_ms=(time.time() - t0) * 1000,
        )

    def delete_product(self, product_id: str) -> StoreResult:
        """Delete a product."""
        t0 = time.time()
        data = self._request("DELETE", f"/products/{product_id}.json")
        success = data.get("_status_code") == 200
        return StoreResult(
            success=success, store="shopify", action="delete_product",
            product_id=product_id,
            duration_ms=(time.time() - t0) * 1000,
        )

    def list_products(self, limit: int = 50) -> StoreResult:
        """List products."""
        t0 = time.time()
        data = self._request("GET", f"/products.json?limit={limit}")
        return StoreResult(
            success=data.get("_status_code") == 200, store="shopify",
            action="list_products", data=data.get("products", []),
            duration_ms=(time.time() - t0) * 1000,
        )

    def get_product(self, product_id: str) -> StoreResult:
        """Get a single product."""
        t0 = time.time()
        data = self._request("GET", f"/products/{product_id}.json")
        return StoreResult(
            success=data.get("_status_code") == 200, store="shopify",
            action="get_product", product_id=product_id,
            data=data.get("product", {}),
            duration_ms=(time.time() - t0) * 1000,
        )

    # -- Collections ----------------------------------------------------------

    def create_collection(
        self,
        title: str,
        body_html: str = "",
        image_url: Optional[str] = None,
    ) -> StoreResult:
        """Create a custom collection."""
        t0 = time.time()
        collection_data: Dict[str, Any] = {
            "title": title,
            "body_html": body_html,
        }
        if image_url:
            collection_data["image"] = {"src": image_url}

        data = self._request("POST", "/custom_collections.json",
                             json={"custom_collection": collection_data})
        collection = data.get("custom_collection", {})
        success = data.get("_status_code") in (200, 201)

        return StoreResult(
            success=success, store="shopify",
            action="create_collection",
            product_id=str(collection.get("id", "")),
            data=collection,
            duration_ms=(time.time() - t0) * 1000,
        )

    # -- Orders (read-only) ---------------------------------------------------

    def list_orders(self, status: str = "any", limit: int = 50) -> StoreResult:
        """List recent orders."""
        t0 = time.time()
        data = self._request("GET", f"/orders.json?status={status}&limit={limit}")
        return StoreResult(
            success=data.get("_status_code") == 200, store="shopify",
            action="list_orders", data=data.get("orders", []),
            duration_ms=(time.time() - t0) * 1000,
        )

    # -- Theme ----------------------------------------------------------------

    def list_themes(self) -> StoreResult:
        """List installed themes."""
        t0 = time.time()
        data = self._request("GET", "/themes.json")
        return StoreResult(
            success=data.get("_status_code") == 200, store="shopify",
            action="list_themes", data=data.get("themes", []),
            duration_ms=(time.time() - t0) * 1000,
        )

    # -- Convenience ----------------------------------------------------------

    def create_from_spec(self, spec: ProductSpec) -> StoreResult:
        """Create a product from a universal ProductSpec."""
        variants = [{"price": spec.price_dollars}]
        if spec.sku:
            variants[0]["sku"] = spec.sku

        images = [{"src": url} for url in spec.images] if spec.images else None

        return self.create_product(
            title=spec.name,
            body_html=f"<p>{spec.description}</p>",
            tags=spec.tags,
            variants=variants,
            images=images,
            product_type=spec.category or "Digital",
        )


# ---------------------------------------------------------------------------
#  Multi-Store Publisher — publish to both with one call
# ---------------------------------------------------------------------------

class MultiStorePublisher:
    """
    Publish products to multiple stores simultaneously.

    Usage:
        publisher = MultiStorePublisher()
        results = publisher.publish_everywhere(ProductSpec(
            name="Spiralverse AI Pack",
            price_cents=4999,
            description="Complete AI training dataset...",
            tags=["AI", "training", "spiralverse"],
        ))
    """

    def __init__(
        self,
        gumroad_token: Optional[str] = None,
        shopify_shop: Optional[str] = None,
        shopify_token: Optional[str] = None,
    ):
        self.stores: Dict[str, Any] = {}

        # Initialize available stores
        try:
            self.stores["gumroad"] = GumroadPublisher(api_token=gumroad_token)
        except (ValueError, RuntimeError):
            pass  # Token not configured

        try:
            self.stores["shopify"] = ShopifyPublisher(
                shop=shopify_shop, access_token=shopify_token,
            )
        except (ValueError, RuntimeError):
            pass  # Credentials not configured

    @property
    def available_stores(self) -> List[str]:
        return list(self.stores.keys())

    def publish_everywhere(self, spec: ProductSpec) -> Dict[str, StoreResult]:
        """Create a product on all configured stores."""
        results = {}
        for name, store in self.stores.items():
            try:
                results[name] = store.create_from_spec(spec)
            except Exception as e:
                results[name] = StoreResult(
                    success=False, store=name, action="create_from_spec",
                    error=str(e),
                )
        return results

    def list_all_products(self) -> Dict[str, StoreResult]:
        """List products from all stores."""
        results = {}
        for name, store in self.stores.items():
            try:
                results[name] = store.list_products()
            except Exception as e:
                results[name] = StoreResult(
                    success=False, store=name, action="list_products",
                    error=str(e),
                )
        return results


# ---------------------------------------------------------------------------
#  Selftest
# ---------------------------------------------------------------------------

def _selftest():
    """Quick smoke test — tests structure only (no live API calls)."""
    print("SCBE Store Publishers — Self-Test")
    print("=" * 50)

    # Test 1: ProductSpec
    spec = ProductSpec(
        name="Test Product",
        price_cents=2999,
        description="A test product",
        tags=["test", "demo"],
        images=["https://example.com/img.png"],
        sku="TEST-001",
    )
    assert spec.price_dollars == "29.99"
    print("  ProductSpec:          PASS")

    # Test 2: StoreResult
    result = StoreResult(
        success=True, store="gumroad", action="create",
        product_id="abc123", product_url="https://gumroad.com/l/abc123",
    )
    assert result.success
    assert result.product_id == "abc123"
    print("  StoreResult:          PASS")

    # Test 3: GumroadPublisher init (without token - should error)
    old_env = os.environ.get("GUMROAD_API_TOKEN")
    os.environ.pop("GUMROAD_API_TOKEN", None)
    try:
        GumroadPublisher()
        print("  Gumroad init guard:   FAIL (no error)")
    except ValueError:
        print("  Gumroad init guard:   PASS")
    finally:
        if old_env:
            os.environ["GUMROAD_API_TOKEN"] = old_env

    # Test 4: ShopifyPublisher init (without creds - should error)
    old_shop = os.environ.get("SHOPIFY_SHOP")
    old_token = os.environ.get("SHOPIFY_ACCESS_TOKEN")
    os.environ.pop("SHOPIFY_SHOP", None)
    os.environ.pop("SHOPIFY_ACCESS_TOKEN", None)
    try:
        ShopifyPublisher()
        print("  Shopify init guard:   FAIL (no error)")
    except ValueError:
        print("  Shopify init guard:   PASS")
    finally:
        if old_shop:
            os.environ["SHOPIFY_SHOP"] = old_shop
        if old_token:
            os.environ["SHOPIFY_ACCESS_TOKEN"] = old_token

    # Test 5: MultiStorePublisher with no creds (should init with empty stores)
    publisher = MultiStorePublisher()
    assert publisher.available_stores == []
    print("  MultiStore (no creds): PASS")

    # Test 6: Platform enum
    assert StoreType.GUMROAD.value == "gumroad"
    assert StoreType.SHOPIFY.value == "shopify"
    print("  StoreType enum:       PASS")

    print(f"\n  Available store types: {[s.value for s in StoreType]}")
    print("  Set env vars to enable:")
    print("    GUMROAD_API_TOKEN=your_token")
    print("    SHOPIFY_SHOP=your-store")
    print("    SHOPIFY_ACCESS_TOKEN=your_token")
    print("\nAll tests complete.")


if __name__ == "__main__":
    _selftest()
