#!/usr/bin/env python3
"""Read-only Polymarket public API helper.

This module intentionally avoids authenticated trading, bridge, wallet, and
order-management endpoints. It is a low-friction research connector for market
discovery and public probability surfaces.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = "scbe_polymarket_public_packet_v1"
GAMMA_BASE_URL = "https://gamma-api.polymarket.com"
CLOB_BASE_URL = "https://clob.polymarket.com"
DATA_BASE_URL = "https://data-api.polymarket.com"


@dataclass(frozen=True)
class PolymarketRequest:
    mode: str = "search"
    query: str = ""
    market_id: str = ""
    slug: str = ""
    token_id: str = ""
    limit: int = 10
    live: bool = False
    timeout: float = 20.0


def _clamp_limit(limit: int) -> int:
    return max(1, min(int(limit), 100))


def _url(path: str, params: dict[str, Any] | None = None, *, base_url: str = GAMMA_BASE_URL) -> str:
    query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v not in ("", None)})
    return f"{base_url}{path}" + (f"?{query}" if query else "")


def _fetch_json(url: str, *, timeout: float) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "SCBE-AETHERMOORE/1.0 public-research"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network error for {url}: {exc.reason}") from exc
    return json.loads(raw)


def _preview_payload(payload: Any, *, mode: str, limit: int) -> Any:
    def compact_market(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row.get("id"),
            "slug": row.get("slug"),
            "question": row.get("question") or row.get("title"),
            "active": row.get("active"),
            "closed": row.get("closed"),
            "endDate": row.get("endDate") or row.get("endDateIso"),
            "outcomes": row.get("outcomes"),
            "outcomePrices": row.get("outcomePrices"),
            "bestBid": row.get("bestBid"),
            "bestAsk": row.get("bestAsk"),
            "lastTradePrice": row.get("lastTradePrice"),
            "volume": row.get("volume"),
            "liquidity": row.get("liquidity"),
            "clobTokenIds": row.get("clobTokenIds"),
        }

    def compact_event(row: dict[str, Any]) -> dict[str, Any]:
        markets = row.get("markets") if isinstance(row.get("markets"), list) else []
        return {
            "id": row.get("id"),
            "slug": row.get("slug"),
            "title": row.get("title"),
            "active": row.get("active"),
            "closed": row.get("closed"),
            "endDate": row.get("endDate"),
            "volume": row.get("volume"),
            "liquidity": row.get("liquidity"),
            "openInterest": row.get("openInterest"),
            "tags": [
                {"id": tag.get("id"), "label": tag.get("label"), "slug": tag.get("slug")}
                for tag in (row.get("tags") or [])[:8]
                if isinstance(tag, dict)
            ],
            "markets": [compact_market(market) for market in markets[:limit] if isinstance(market, dict)],
        }

    if isinstance(payload, list):
        return [compact_market(row) if isinstance(row, dict) else row for row in payload[:limit]]
    if not isinstance(payload, dict):
        return payload
    if mode == "search":
        return {
            "events": [
                compact_event(event) for event in (payload.get("events") or [])[:limit] if isinstance(event, dict)
            ],
            "tags": (payload.get("tags") or [])[:limit],
            "profiles": (payload.get("profiles") or [])[:limit],
            "pagination": payload.get("pagination"),
        }
    if mode.startswith("market"):
        return compact_market(payload)
    return payload


def build_polymarket_packet(req: PolymarketRequest) -> dict[str, Any]:
    """Build a governed Polymarket research packet, optionally fetching live data."""

    limit = _clamp_limit(req.limit)
    mode = req.mode.strip().lower().replace("-", "_")
    if mode not in {"search", "markets", "market_by_id", "market_by_slug", "midpoint", "server_time"}:
        raise ValueError("mode must be one of: search, markets, market_by_id, market_by_slug, midpoint, server_time")

    if mode == "search":
        url = _url("/public-search", {"q": req.query, "limit_per_type": limit})
        evidence_target = "market/event/profile search results"
    elif mode == "markets":
        url = _url("/markets", {"limit": limit})
        evidence_target = "market list"
    elif mode == "market_by_id":
        if not req.market_id:
            raise ValueError("market_id is required for market_by_id")
        url = _url(f"/markets/{urllib.parse.quote(req.market_id)}")
        evidence_target = "single Gamma market by id"
    elif mode == "market_by_slug":
        if not req.slug:
            raise ValueError("slug is required for market_by_slug")
        url = _url(f"/markets/slug/{urllib.parse.quote(req.slug)}")
        evidence_target = "single Gamma market by slug"
    elif mode == "midpoint":
        if not req.token_id:
            raise ValueError("token_id is required for midpoint")
        url = _url("/midpoint", {"token_id": req.token_id}, base_url=CLOB_BASE_URL)
        evidence_target = "public CLOB midpoint price for one outcome token"
    else:
        url = _url("/time", base_url=CLOB_BASE_URL)
        evidence_target = "public CLOB server time"

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "request": {
            "query": req.query,
            "market_id": req.market_id,
            "slug": req.slug,
            "token_id": req.token_id,
            "limit": limit,
            "live": bool(req.live),
        },
        "endpoints": {
            "gamma_api": GAMMA_BASE_URL,
            "data_api": DATA_BASE_URL,
            "clob_api": CLOB_BASE_URL,
        },
        "url": url,
        "source": {
            "source_id": "polymarket_public_prediction_markets",
            "authority_class": "market_probability_surface",
            "authentication": "none for Gamma API, Data API, and public CLOB read endpoints",
            "blocked": ["authenticated trading", "order placement", "wallet bridge", "withdrawals", "deposits"],
        },
        "safety": {
            "tier": "READ_ONLY_NO_TRADING",
            "rule": "Use for research, calibration, and forecast tracking only; do not place or cancel orders.",
            "minimum_receipts": [
                "endpoint",
                "query_or_id",
                "retrieved_at_unix",
                "market_slug_or_token_id",
                "price_or_probability_field",
            ],
        },
        "evidence_target": evidence_target,
    }
    if req.live:
        started = time.time()
        data = _fetch_json(url, timeout=req.timeout)
        payload["retrieved_at_unix"] = round(time.time(), 3)
        payload["elapsed_seconds"] = round(time.time() - started, 3)
        payload["data"] = _preview_payload(data, mode=mode, limit=limit)
    return payload


def render_text(packet: dict[str, Any]) -> str:
    lines = [
        "Polymarket Public API Packet",
        "=" * 29,
        f"mode: {packet['mode']}",
        f"url: {packet['url']}",
        f"safety: {packet['safety']['tier']}",
        f"target: {packet['evidence_target']}",
    ]
    if "data" in packet:
        lines.append(f"live: yes elapsed={packet.get('elapsed_seconds')}s")
    else:
        lines.append("live: no; rerun with --live to fetch")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        default="search",
        choices=["search", "markets", "market-by-id", "market-by-slug", "midpoint", "server-time"],
    )
    parser.add_argument("--query", default="")
    parser.add_argument("--market-id", default="")
    parser.add_argument("--slug", default="")
    parser.add_argument("--token-id", default="")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--live", action="store_true", help="Fetch live public data instead of emitting a route packet only."
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    packet = build_polymarket_packet(
        PolymarketRequest(
            mode=args.mode,
            query=args.query,
            market_id=args.market_id,
            slug=args.slug,
            token_id=args.token_id,
            limit=args.limit,
            live=args.live,
            timeout=args.timeout,
        )
    )
    print(json.dumps(packet, indent=2, sort_keys=True) if args.json else render_text(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
