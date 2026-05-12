#!/usr/bin/env python3
"""Audit SCBE public offers for launch readiness.

The gate is deliberately practical: a product is launchable only when the
catalog has real price/checkout/proof data, policy pages exist, and at least
one low-friction starter offer can be bought without a sales call.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OFFERS = REPO_ROOT / "docs" / "offers.json"
DEFAULT_APP_CONFIG = REPO_ROOT / "docs" / "app-config.json"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "marketing" / "product_launch_readiness" / "latest"
SITE_BASE = "https://aethermoore.com/SCBE-AETHERMOORE"
STARTER_PRICE_MAX = 100.0
REQUIRED_OFFER_FIELDS = ("id", "name", "price_label", "type", "checkout_url", "proof_url", "status")


@dataclass(frozen=True)
class LaunchCheck:
    name: str
    ok: bool
    detail: str
    severity: str = "error"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def local_path_for_site_url(url: str) -> Path | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None
    prefix = urlparse(SITE_BASE).path.rstrip("/") + "/"
    if parsed.netloc != "aethermoore.com" or not parsed.path.startswith(prefix):
        return None
    suffix = parsed.path[len(prefix) :]
    if not suffix or suffix.endswith("/"):
        suffix = suffix.rstrip("/") + "/index.html"
    return REPO_ROOT / "docs" / suffix


def first_price(price_label: str) -> float | None:
    match = re.search(r"\$([0-9]+(?:\.[0-9]+)?)", price_label)
    return float(match.group(1)) if match else None


def is_valid_checkout(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc) and "example." not in parsed.netloc


def check_offer(offer: dict[str, Any]) -> list[LaunchCheck]:
    offer_id = str(offer.get("id", "unknown"))
    checks: list[LaunchCheck] = []

    missing = [field for field in REQUIRED_OFFER_FIELDS if not str(offer.get(field, "")).strip()]
    checks.append(
        LaunchCheck(
            f"offer:{offer_id}:required_fields",
            not missing,
            "all required fields present" if not missing else f"missing {', '.join(missing)}",
        )
    )

    status = str(offer.get("status", "")).strip().lower()
    checks.append(
        LaunchCheck(
            f"offer:{offer_id}:status",
            status == "live",
            f"status={status or '<empty>'}",
        )
    )

    checkout_url = str(offer.get("checkout_url", "")).strip()
    checks.append(
        LaunchCheck(
            f"offer:{offer_id}:checkout_url",
            is_valid_checkout(checkout_url),
            checkout_url or "missing checkout_url",
        )
    )

    proof_url = str(offer.get("proof_url", "")).strip()
    proof_path = local_path_for_site_url(proof_url)
    checks.append(
        LaunchCheck(
            f"offer:{offer_id}:proof_page",
            proof_path is not None and proof_path.exists(),
            rel(proof_path) if proof_path is not None else proof_url or "missing proof_url",
        )
    )

    price = first_price(str(offer.get("price_label", "")))
    checks.append(
        LaunchCheck(
            f"offer:{offer_id}:price",
            price is not None,
            f"price={price}" if price is not None else f"unparseable price_label={offer.get('price_label')!r}",
        )
    )

    return checks


def audit_launch(offers_path: Path = DEFAULT_OFFERS, app_config_path: Path = DEFAULT_APP_CONFIG) -> dict[str, Any]:
    offers_data = load_json(offers_path)
    app_config = load_json(app_config_path)
    offers = offers_data.get("offers", [])
    checks: list[LaunchCheck] = []

    checks.append(
        LaunchCheck(
            "catalog:schema",
            offers_data.get("schema") == "aethermoore-offers-v1",
            str(offers_data.get("schema")),
        )
    )
    checks.append(
        LaunchCheck(
            "catalog:live_offer_count",
            isinstance(offers, list) and len(offers) >= 3,
            f"{len(offers) if isinstance(offers, list) else 0} offers",
        )
    )

    for offer in offers if isinstance(offers, list) else []:
        checks.extend(check_offer(offer))

    live_offers = [offer for offer in offers if isinstance(offer, dict) and offer.get("status") == "live"]
    starter_offers = [
        offer
        for offer in live_offers
        if str(offer.get("type", "")).lower() != "subscription"
        and (price := first_price(str(offer.get("price_label", "")))) is not None
        and price <= STARTER_PRICE_MAX
    ]
    subscriptions = [offer for offer in live_offers if str(offer.get("type", "")).lower() == "subscription"]
    service_offers = [offer for offer in live_offers if str(offer.get("type", "")).lower() in {"service", "usage_credit"}]

    checks.extend(
        [
            LaunchCheck("mix:starter_offer", bool(starter_offers), f"{len(starter_offers)} offers at <= ${STARTER_PRICE_MAX:g}"),
            LaunchCheck("mix:subscription_offer", bool(subscriptions), f"{len(subscriptions)} subscription offers"),
            LaunchCheck("mix:service_offer", bool(service_offers), f"{len(service_offers)} service/usage offers"),
        ]
    )

    endpoint_map = app_config.get("endpoints", {}) if isinstance(app_config.get("endpoints"), dict) else {}
    for key in ("offers_json", "privacy_policy", "terms_of_service", "workflow_snapshot_checkout"):
        value = str(endpoint_map.get(key, ""))
        checks.append(LaunchCheck(f"app_config:endpoint:{key}", is_valid_checkout(value), value or "missing endpoint"))

    for label, path in {
        "privacy": REPO_ROOT / "docs" / "legal" / "privacy.html",
        "terms": REPO_ROOT / "docs" / "legal" / "terms.html",
        "robots": REPO_ROOT / "docs" / "robots.txt",
        "sitemap": REPO_ROOT / "docs" / "sitemap.xml",
        "llms": REPO_ROOT / "llms.txt",
    }.items():
        checks.append(LaunchCheck(f"surface:{label}", path.exists(), rel(path)))

    failures = [check for check in checks if not check.ok and check.severity == "error"]
    warnings = [check for check in checks if not check.ok and check.severity == "warning"]
    score = round(10.0 * (len(checks) - len(failures)) / max(1, len(checks)), 2)

    return {
        "schema": "scbe_product_launch_readiness_v1",
        "created_at_utc": now_utc(),
        "offers_path": rel(offers_path),
        "app_config_path": rel(app_config_path),
        "score": score,
        "ready": not failures,
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "offer_count": len(offers) if isinstance(offers, list) else 0,
        "live_offer_count": len(live_offers),
        "starter_offer_ids": [str(offer.get("id")) for offer in starter_offers],
        "service_offer_ids": [str(offer.get("id")) for offer in service_offers],
        "subscription_offer_ids": [str(offer.get("id")) for offer in subscriptions],
        "checks": [asdict(check) for check in checks],
    }


def render_markdown(report: dict[str, Any]) -> str:
    failed = [check for check in report["checks"] if not check["ok"]]
    lines = [
        "# Product Launch Readiness",
        "",
        f"- Created: `{report['created_at_utc']}`",
        f"- Score: `{report['score']}/10`",
        f"- Ready: `{report['ready']}`",
        f"- Live offers: `{report['live_offer_count']}`",
        f"- Starter offers: `{', '.join(report['starter_offer_ids']) or 'none'}`",
        f"- Service offers: `{', '.join(report['service_offer_ids']) or 'none'}`",
        f"- Subscriptions: `{', '.join(report['subscription_offer_ids']) or 'none'}`",
        "",
        "## Failed Checks",
        "",
    ]
    if failed:
        lines.extend(f"- `{check['name']}`: {check['detail']}" for check in failed)
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Launch Rule",
            "",
            "Keep one low-friction starter offer buyable, keep proof pages local and linked, keep legal/support surfaces present, and verify checkout routes before promotion.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "product-launch-readiness.json"
    md_path = output_dir / "product-launch-readiness.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offers", type=Path, default=DEFAULT_OFFERS)
    parser.add_argument("--app-config", type=Path, default=DEFAULT_APP_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fail-on-not-ready", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = audit_launch(args.offers, args.app_config)
    json_path, md_path = write_report(report, args.output_dir)
    print(f"Launch readiness: {report['score']}/10 ready={report['ready']}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    return 1 if args.fail_on_not_ready and not report["ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
