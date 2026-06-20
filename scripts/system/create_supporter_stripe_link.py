#!/usr/bin/env python3
"""Create a Stripe Payment Link for the AetherMoore SUPPORTER tier.

This script intentionally uses only the Python standard library so it can run
even when the `stripe` package is not installed locally. It reads
STRIPE_SECRET_KEY from the environment and writes a redacted JSON artifact.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
STRIPE_API = "https://api.stripe.com/v1"
DEFAULT_LOOKUP_KEY = "aethermoore_supporter_monthly_20"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_output(raw_path: str) -> Path:
    target = (REPO_ROOT / raw_path).resolve()
    artifacts_root = (REPO_ROOT / "artifacts").resolve()
    if target != artifacts_root and artifacts_root not in target.parents:
        raise ValueError("output path must stay under artifacts/")
    return target


def stripe_request(secret_key: str, method: str, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    encoded = urllib.parse.urlencode(data or {}, doseq=True).encode("utf-8")
    token = base64.b64encode(f"{secret_key}:".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(
        STRIPE_API + path,
        data=encoded if method.upper() == "POST" else None,
        method=method.upper(),
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Stripe API error {exc.code}: {body[:500]}") from exc


def search_price(secret_key: str, lookup_key: str) -> dict[str, Any] | None:
    query = urllib.parse.quote(f"lookup_key:'{lookup_key}'")
    result = stripe_request(secret_key, "GET", f"/prices/search?query={query}&limit=1")
    rows = result.get("data", [])
    return rows[0] if rows else None


def create_product(secret_key: str) -> dict[str, Any]:
    return stripe_request(
        secret_key,
        "POST",
        "/products",
        {
            "name": "AetherMoore Supporter",
            "description": "Monthly supporter tier for AetherMoore operator notes and early package updates.",
            "metadata[scbe_tier]": "SUPPORTER",
            "metadata[scbe_offer]": "supporter_monthly",
        },
    )


def create_price(secret_key: str, product_id: str, lookup_key: str) -> dict[str, Any]:
    return stripe_request(
        secret_key,
        "POST",
        "/prices",
        {
            "currency": "usd",
            "unit_amount": "2000",
            "recurring[interval]": "month",
            "product": product_id,
            "lookup_key": lookup_key,
            "metadata[scbe_tier]": "SUPPORTER",
            "metadata[scbe_offer]": "supporter_monthly",
        },
    )


def create_payment_link(secret_key: str, price_id: str) -> dict[str, Any]:
    return stripe_request(
        secret_key,
        "POST",
        "/payment_links",
        {
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "after_completion[type]": "redirect",
            "after_completion[redirect][url]": "https://aethermoore.com/SCBE-AETHERMOORE/supporter.html?status=success",
            "metadata[scbe_tier]": "SUPPORTER",
            "metadata[scbe_offer]": "supporter_monthly",
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Create/reuse the AetherMoore $20/month SUPPORTER Stripe link")
    parser.add_argument("--lookup-key", default=DEFAULT_LOOKUP_KEY)
    parser.add_argument("--output", default="artifacts/monetization/supporter_stripe_link.json")
    args = parser.parse_args()

    secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret_key:
        print("ERROR: STRIPE_SECRET_KEY is not set.", file=sys.stderr)
        return 2

    existing = search_price(secret_key, args.lookup_key)
    if existing:
        price = existing
        created_product = None
        created_price = False
    else:
        product = create_product(secret_key)
        price = create_price(secret_key, product["id"], args.lookup_key)
        created_product = product["id"]
        created_price = True

    link = create_payment_link(secret_key, price["id"])

    out = {
        "generated_at_utc": now_utc(),
        "mode": "live" if secret_key.startswith("sk_live_") else "test_or_restricted",
        "lookup_key": args.lookup_key,
        "created_product_id": created_product,
        "created_price": created_price,
        "price_id": price["id"],
        "payment_link_id": link["id"],
        "payment_link_url": link["url"],
        "set_env": {
            "STRIPE_PRICE_SUPPORTER": price["id"],
        },
    }
    target = resolve_output(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"payment_link_url={link['url']}")
    print(f"price_id={price['id']}")
    print(f"artifact={target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
