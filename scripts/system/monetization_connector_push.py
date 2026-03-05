#!/usr/bin/env python3
"""Push monetization leads and checkout offers into configured connectors.

This script packages two high-intent payloads:
1) Latest lead backlog (GitHub issue-derived prospect list)
2) Offer catalog with Stripe + Gumroad checkout links

Then dispatches to n8n and Zapier via ConnectorBridge.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from src.fleet.connector_bridge import ConnectorBridge, ConnectorResult
from src.security.secret_store import get_secret
from scripts.gumroad_publish import GumroadPublisher, PRODUCTS, STRIPE_LINKS


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_stamp() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _latest_lead_file() -> Optional[Path]:
    sales_dir = REPO_ROOT / "artifacts" / "sales"
    if not sales_dir.exists():
        return None
    files = sorted(sales_dir.glob("github_leads_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _build_offers(include_gumroad: bool) -> List[Dict[str, Any]]:
    if include_gumroad and not os.environ.get("GUMROAD_API_TOKEN"):
        token = get_secret("GUMROAD_API_TOKEN", "")
        if token:
            os.environ["GUMROAD_API_TOKEN"] = token

    gumroad_map: Dict[str, str] = {}
    if include_gumroad:
        try:
            listing = GumroadPublisher().list_products()
            if listing.success and isinstance(listing.data, list):
                for row in listing.data:
                    name = str(row.get("name", "")).strip()
                    if name:
                        gumroad_map[name] = str(row.get("short_url", "")).strip()
        except Exception:
            pass

    offers: List[Dict[str, Any]] = []
    for key, spec in PRODUCTS.items():
        stripe = STRIPE_LINKS.get(key, {})
        offers.append(
            {
                "id": key,
                "name": spec.name,
                "sku": spec.sku,
                "price_usd": round(spec.price_cents / 100.0, 2),
                "stripe_url": str(stripe.get("url", "")).strip(),
                "gumroad_url": gumroad_map.get(spec.name, ""),
                "tags": list(spec.tags),
            }
        )

    return offers


def _result_to_dict(result: ConnectorResult) -> Dict[str, Any]:
    return {
        "success": bool(result.success),
        "platform": result.platform,
        "elapsed_ms": result.elapsed_ms,
        "credits_earned": result.credits_earned,
        "error": result.error,
        "data": result.data,
    }


async def _dispatch(
    *,
    payload: Dict[str, Any],
    route_n8n: bool,
    route_zapier: bool,
    dry_run: bool,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "n8n": {"status": "skipped", "reason": "disabled"},
        "zapier": {"status": "skipped", "reason": "disabled"},
    }

    if dry_run:
        if route_n8n:
            out["n8n"] = {"status": "dry_run", "reason": "dry_run_enabled"}
        if route_zapier:
            out["zapier"] = {"status": "dry_run", "reason": "dry_run_enabled"}
        return out

    bridge = ConnectorBridge()

    if route_n8n:
        if not bridge.is_configured("n8n"):
            out["n8n"] = {"status": "skipped", "reason": "not_configured"}
        else:
            res = await bridge.execute("n8n", "trigger", payload)
            out["n8n"] = {"status": "sent" if res.success else "failed", **_result_to_dict(res)}

    if route_zapier:
        if not bridge.is_configured("zapier"):
            out["zapier"] = {"status": "skipped", "reason": "not_configured"}
        else:
            res = await bridge.execute("zapier", "trigger", payload)
            out["zapier"] = {"status": "sent" if res.success else "failed", **_result_to_dict(res)}

    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Push latest leads + offers to n8n/Zapier monetization connectors.")
    parser.add_argument("--leads-json", default="", help="Optional leads JSON file path.")
    parser.add_argument("--top-leads", type=int, default=10, help="Number of leads to include in connector payload.")
    parser.add_argument("--include-gumroad", action="store_true", help="Attempt to enrich offers with Gumroad live URLs.")

    parser.add_argument("--route-n8n", dest="route_n8n", action="store_true")
    parser.add_argument("--no-route-n8n", dest="route_n8n", action="store_false")
    parser.set_defaults(route_n8n=True)

    parser.add_argument("--route-zapier", dest="route_zapier", action="store_true")
    parser.add_argument("--no-route-zapier", dest="route_zapier", action="store_false")
    parser.set_defaults(route_zapier=True)

    parser.add_argument("--dry-run", action="store_true", help="Do not send connector traffic.")
    parser.add_argument("--output-dir", default="artifacts/monetization", help="Output root for run artifacts.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    day = _utc_now().strftime("%Y%m%d")
    run_id = f"monetization-connector-push-{_utc_stamp()}"

    lead_path = Path(args.leads_json).resolve() if args.leads_json.strip() else _latest_lead_file()
    leads: List[Dict[str, Any]] = []
    if lead_path and lead_path.exists():
        loaded = _load_json(lead_path, default=[])
        if isinstance(loaded, list):
            leads = [x for x in loaded if isinstance(x, dict)]

    offers = _build_offers(include_gumroad=bool(args.include_gumroad))

    payload: Dict[str, Any] = {
        "event": "monetization_connector_push",
        "run_id": run_id,
        "generated_at": _utc_now().isoformat(),
        "lead_source_file": str(lead_path) if lead_path else "",
        "leads_count": len(leads),
        "top_leads": leads[: max(1, int(args.top_leads))],
        "offers": offers,
        "instructions": [
            "Push one direct CTA per channel with one checkout link.",
            "Prioritize high-intent leads first and respond within 15 minutes.",
            "Record replies and conversions in the same workflow run.",
        ],
    }

    route_results = asyncio.run(
        _dispatch(
            payload=payload,
            route_n8n=bool(args.route_n8n),
            route_zapier=bool(args.route_zapier),
            dry_run=bool(args.dry_run),
        )
    )

    out_dir = (REPO_ROOT / args.output_dir / day).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}.json"
    artifact = {
        "ok": True,
        "run_id": run_id,
        "lead_source_file": str(lead_path) if lead_path else "",
        "leads_count": len(leads),
        "offers_count": len(offers),
        "route_results": route_results,
        "payload": payload,
    }
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "run_id": run_id,
                "artifact": str(out_path),
                "route_results": route_results,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

