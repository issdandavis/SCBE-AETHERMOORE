#!/usr/bin/env python3
"""Upload product images to Shopify store.

Reads product images from artifacts/shopify-product-images/
and uploads them to matching products via Shopify Admin API.

Usage:
  # Set token first:
  export SHOPIFY_ACCESS_TOKEN=shpat_xxxxx
  export SHOPIFY_SHOP=aethermore-code.myshopify.com

  python scripts/system/shopify_upload_images.py          # dry-run (list products)
  python scripts/system/shopify_upload_images.py --upload  # actually upload
"""

import base64
import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
IMAGE_DIR = REPO_ROOT / "artifacts" / "shopify-product-images"

SHOP = os.environ.get("SHOPIFY_SHOP", "aethermore-code.myshopify.com")
TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2025-01")

# Map image filenames to product title fragments for matching
IMAGE_TO_PRODUCT = {
    "hydra-armor-api.png": "Hydra Armor",
    "scbe-governance-toolkit.png": "Governance Toolkit",
    "n8n-workflow-bundle.png": "n8n Workflow",
    "spiralverse-training-data.png": "Training Data",
    "worldforge-engine.png": "WorldForge",
    "k12-curriculum.png": "K-12",
    "hydra-notion-templates.png": "Templates for Notion",
}


def api_call(method, path, body=None):
    url = f"https://{SHOP}/admin/api/{API_VERSION}/{path}"
    headers = {
        "X-Shopify-Access-Token": TOKEN,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"  API Error {e.code}: {error_body[:200]}")
        return None


def list_products():
    result = api_call("GET", "products.json?limit=50")
    if not result:
        return []
    return result.get("products", [])


def upload_image(product_id, image_path, alt_text):
    img_data = image_path.read_bytes()
    b64 = base64.b64encode(img_data).decode()
    body = {
        "image": {
            "attachment": b64,
            "filename": image_path.name,
            "alt": alt_text,
        }
    }
    return api_call("POST", f"products/{product_id}/images.json", body)


def find_matching_product(products, search_fragment):
    search_lower = search_fragment.lower()
    for p in products:
        if search_lower in p["title"].lower():
            return p
    return None


def main():
    upload_mode = "--upload" in sys.argv

    if not TOKEN:
        print("ERROR: SHOPIFY_ACCESS_TOKEN not set.")
        print("  Set it with: export SHOPIFY_ACCESS_TOKEN=shpat_xxxxx")
        print("  Or on Windows: $env:SHOPIFY_ACCESS_TOKEN = 'shpat_xxxxx'")
        sys.exit(1)

    print(f"Shop: {SHOP}")
    print(f"Mode: {'UPLOAD' if upload_mode else 'DRY RUN'}")
    print()

    products = list_products()
    if not products:
        print("No products found or API call failed.")
        sys.exit(1)

    print(f"Found {len(products)} products:")
    for p in products:
        img_count = len(p.get("images", []))
        print(f"  [{p['id']}] {p['title']} ({img_count} images)")
    print()

    images = list(IMAGE_DIR.glob("*.png"))
    if not images:
        print(f"No images found in {IMAGE_DIR}")
        sys.exit(1)

    uploaded = 0
    skipped = 0
    failed = 0

    for img_path in sorted(images):
        search = IMAGE_TO_PRODUCT.get(img_path.name)
        if not search:
            print(f"  SKIP {img_path.name} — no product mapping")
            skipped += 1
            continue

        product = find_matching_product(products, search)
        if not product:
            print(f"  SKIP {img_path.name} — no matching product for '{search}'")
            skipped += 1
            continue

        alt = f"{product['title']} product image"
        print(f"  {'UPLOAD' if upload_mode else 'WOULD UPLOAD'}: {img_path.name} -> {product['title']} [{product['id']}]")

        if upload_mode:
            result = upload_image(product["id"], img_path, alt)
            if result and "image" in result:
                print(f"    OK: image id={result['image']['id']}")
                uploaded += 1
            else:
                print(f"    FAILED")
                failed += 1
        else:
            uploaded += 1

    print(f"\nResults: {uploaded} uploaded, {skipped} skipped, {failed} failed")
    if not upload_mode:
        print("Run with --upload to actually push images to Shopify.")


if __name__ == "__main__":
    main()
