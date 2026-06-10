#!/usr/bin/env python3
"""Smoke-test the remote app configuration and public offer surfaces.

This is the quick gate to run before an app bundle release or after changing
remote revenue/config files. It validates the local JSON first, then optionally
checks the live GitHub Pages and Vercel endpoints.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

PAGES_BASE = "https://aethermoore.com/SCBE-AETHERMOORE"
VERCEL_BASE = "https://scbe-agent-bridge-vercel.vercel.app"

OFFERS_SCHEMA = "aethermoore-offers-v1"
APP_CONFIG_SCHEMA = "aethermoor-bus-app-config-v1"
PACKAGE_NAME = "io.aethermoor.bus"

REQUIRED_OFFER_IDS = {
    "tip_jar",
    "supporter_monthly",
    "governance_snapshot",
}

DEAD_CHECKOUT_ENDPOINT = "api.aethermoore.com/v1/billing/public-checkout"


def _is_stripe_checkout_url(value: object) -> bool:
    parsed = urllib.parse.urlparse(str(value))
    return parsed.scheme == "https" and parsed.netloc == "buy.stripe.com" and parsed.path.startswith("/")


def _contains_stripe_checkout_url(text: str) -> bool:
    for match in re.finditer(r"https://buy\.stripe\.com/[^\s\"'<>]+", text):
        if _is_stripe_checkout_url(match.group(0)):
            return True
    return False


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def pass_check(name: str, detail: str = "ok") -> CheckResult:
    return CheckResult(name=name, ok=True, detail=detail)


def fail_check(name: str, detail: str) -> CheckResult:
    return CheckResult(name=name, ok=False, detail=detail)


def load_json_file(path: Path) -> tuple[dict[str, Any] | None, CheckResult]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, fail_check(f"local:{path.name}:exists", f"missing {path}")
    except json.JSONDecodeError as exc:
        return None, fail_check(f"local:{path.name}:json", f"invalid json: {exc}")
    if not isinstance(data, dict):
        return None, fail_check(f"local:{path.name}:object", "top-level JSON must be an object")
    return data, pass_check(f"local:{path.name}:json")


def fetch_url(url: str, timeout: float = 20.0) -> tuple[str | None, CheckResult]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SCBE-remote-app-config-smoke/1.0",
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = getattr(response, "status", 200)
    except urllib.error.HTTPError as exc:
        return None, fail_check(f"live:{url}", f"http {exc.code}")
    except urllib.error.URLError as exc:
        return None, fail_check(f"live:{url}", f"request failed: {exc.reason}")
    except TimeoutError:
        return None, fail_check(f"live:{url}", "request timed out")
    if status < 200 or status >= 300:
        return None, fail_check(f"live:{url}", f"http {status}")
    return body, pass_check(f"live:{url}", f"http {status}")


def parse_json_text(text: str, source: str) -> tuple[dict[str, Any] | None, CheckResult]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, fail_check(f"{source}:json", f"invalid json: {exc}")
    if not isinstance(data, dict):
        return None, fail_check(f"{source}:object", "top-level JSON must be an object")
    return data, pass_check(f"{source}:json")


def normalize_vercel_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Vercel endpoints wrap payloads in {ok, data}; local Pages JSON does not."""
    payload = data.get("data")
    if data.get("ok") is True and isinstance(payload, dict):
        return payload
    return data


def validate_offer_catalog(data: dict[str, Any], source: str) -> list[CheckResult]:
    payload = normalize_vercel_payload(data)
    checks: list[CheckResult] = []

    schema = payload.get("schema")
    checks.append(
        pass_check(f"{source}:schema", schema)
        if schema == OFFERS_SCHEMA
        else fail_check(f"{source}:schema", f"expected {OFFERS_SCHEMA}, got {schema!r}")
    )

    offers = payload.get("offers")
    if not isinstance(offers, list):
        return checks + [fail_check(f"{source}:offers", "offers must be a list")]

    by_id = {offer.get("id"): offer for offer in offers if isinstance(offer, dict)}
    missing = sorted(REQUIRED_OFFER_IDS - set(by_id))
    checks.append(
        pass_check(f"{source}:required_offers", ",".join(sorted(REQUIRED_OFFER_IDS)))
        if not missing
        else fail_check(f"{source}:required_offers", f"missing {missing}")
    )

    for offer_id in sorted(REQUIRED_OFFER_IDS):
        offer = by_id.get(offer_id)
        if not isinstance(offer, dict):
            continue
        checkout = str(offer.get("checkout_url", ""))
        checks.append(
            pass_check(f"{source}:{offer_id}:checkout", checkout)
            if _is_stripe_checkout_url(checkout)
            else fail_check(f"{source}:{offer_id}:checkout", f"not a Stripe hosted checkout: {checkout!r}")
        )
        proof_url = str(offer.get("proof_url", ""))
        checks.append(
            pass_check(f"{source}:{offer_id}:proof_url", proof_url)
            if not proof_url or proof_url.startswith(PAGES_BASE)
            else fail_check(f"{source}:{offer_id}:proof_url", f"unexpected proof URL: {proof_url!r}")
        )

    return checks


def validate_app_config(data: dict[str, Any], source: str) -> list[CheckResult]:
    payload = normalize_vercel_payload(data)
    checks: list[CheckResult] = []

    schema = payload.get("schema")
    checks.append(
        pass_check(f"{source}:schema", schema)
        if schema == APP_CONFIG_SCHEMA
        else fail_check(f"{source}:schema", f"expected {APP_CONFIG_SCHEMA}, got {schema!r}")
    )

    app = payload.get("app")
    package_name = app.get("package_name") if isinstance(app, dict) else None
    checks.append(
        pass_check(f"{source}:package_name", package_name)
        if package_name == PACKAGE_NAME
        else fail_check(f"{source}:package_name", f"expected {PACKAGE_NAME}, got {package_name!r}")
    )

    remote_update = payload.get("remote_update")
    supported = remote_update.get("supported") if isinstance(remote_update, dict) else None
    checks.append(
        pass_check(f"{source}:remote_update", "supported")
        if supported is True
        else fail_check(f"{source}:remote_update", f"expected true, got {supported!r}")
    )

    endpoints = payload.get("endpoints")
    if not isinstance(endpoints, dict):
        return checks + [fail_check(f"{source}:endpoints", "endpoints must be an object")]

    expected_endpoints = {
        "offers_json": f"{PAGES_BASE}/offers.json",
        "supporter_page": f"{PAGES_BASE}/supporter.html",
        "agent_bridge_system": f"{VERCEL_BASE}/api/agent/system",
        "agent_bridge_offers": f"{VERCEL_BASE}/api/agent/offers",
        "agent_bridge_app_config": f"{VERCEL_BASE}/api/agent/app-config",
    }
    for key, expected in expected_endpoints.items():
        actual = endpoints.get(key)
        checks.append(
            pass_check(f"{source}:endpoint:{key}", expected)
            if actual == expected
            else fail_check(f"{source}:endpoint:{key}", f"expected {expected!r}, got {actual!r}")
        )

    features = payload.get("features")
    if isinstance(features, dict):
        for key in REQUIRED_OFFER_IDS:
            checks.append(
                pass_check(f"{source}:feature:{key}", "enabled")
                if features.get(key) is True
                else fail_check(f"{source}:feature:{key}", f"expected true, got {features.get(key)!r}")
            )
    else:
        checks.append(fail_check(f"{source}:features", "features must be an object"))

    fallback = payload.get("fallbacks", {}).get("primary_offer") if isinstance(payload.get("fallbacks"), dict) else ""
    checks.append(
        pass_check(f"{source}:fallback_primary_offer", fallback)
        if _is_stripe_checkout_url(fallback)
        else fail_check(f"{source}:fallback_primary_offer", f"not a Stripe hosted checkout: {fallback!r}")
    )

    return checks


def validate_supporter_page(text: str, source: str) -> list[CheckResult]:
    return [
        (
            pass_check(f"{source}:no_dead_checkout_endpoint")
            if DEAD_CHECKOUT_ENDPOINT not in text
            else fail_check(f"{source}:no_dead_checkout_endpoint", DEAD_CHECKOUT_ENDPOINT)
        ),
        (
            pass_check(f"{source}:stripe_checkout_present")
            if _contains_stripe_checkout_url(text)
            else fail_check(f"{source}:stripe_checkout_present", "no Stripe hosted checkout link found")
        ),
    ]


def validate_system_contract(data: dict[str, Any], source: str) -> list[CheckResult]:
    payload = normalize_vercel_payload(data)
    checks: list[CheckResult] = []

    schema = payload.get("schema")
    checks.append(
        pass_check(f"{source}:schema", schema)
        if schema == "aethermoor.agent.system_contract.v1"
        else fail_check(f"{source}:schema", f"expected aethermoor.agent.system_contract.v1, got {schema!r}")
    )

    backend = payload.get("backend")
    endpoints = backend.get("endpoints") if isinstance(backend, dict) else None
    checks.append(
        pass_check(f"{source}:endpoint:chat", "/api/agent/chat")
        if isinstance(endpoints, dict) and endpoints.get("chat") == "/api/agent/chat"
        else fail_check(f"{source}:endpoint:chat", "missing /api/agent/chat")
    )
    checks.append(
        pass_check(f"{source}:endpoint:storage", "/api/agent/storage")
        if isinstance(endpoints, dict) and endpoints.get("storage") == "/api/agent/storage"
        else fail_check(f"{source}:endpoint:storage", "missing /api/agent/storage")
    )

    bus = payload.get("bus")
    formation = bus.get("workspace_formation") if isinstance(bus, dict) else None
    checks.append(
        pass_check(f"{source}:workspace_formation", "present")
        if isinstance(formation, dict) and formation.get("schema_version") == "aethermoor.bus.workspace_formation.v1"
        else fail_check(f"{source}:workspace_formation", "missing workspace formation")
    )

    offers = (
        payload.get("monetization", {}).get("live_offers") if isinstance(payload.get("monetization"), dict) else None
    )
    checks.append(
        pass_check(f"{source}:live_offers", str(len(offers)))
        if isinstance(offers, list) and len(offers) >= len(REQUIRED_OFFER_IDS)
        else fail_check(f"{source}:live_offers", "missing live offer list")
    )

    return checks


def run_checks(live: bool = False) -> list[CheckResult]:
    checks: list[CheckResult] = []

    offers_data, check = load_json_file(REPO_ROOT / "docs" / "offers.json")
    checks.append(check)
    if offers_data is not None:
        checks.extend(validate_offer_catalog(offers_data, "local:offers"))

    app_config_data, check = load_json_file(REPO_ROOT / "docs" / "app-config.json")
    checks.append(check)
    if app_config_data is not None:
        checks.extend(validate_app_config(app_config_data, "local:app_config"))

    supporter_path = REPO_ROOT / "docs" / "supporter.html"
    if supporter_path.exists():
        checks.extend(validate_supporter_page(supporter_path.read_text(encoding="utf-8"), "local:supporter_page"))
    else:
        checks.append(fail_check("local:supporter_page:exists", f"missing {supporter_path}"))

    if not live:
        return checks

    live_json_targets = [
        (f"{PAGES_BASE}/offers.json", validate_offer_catalog, "live:pages:offers"),
        (f"{PAGES_BASE}/app-config.json", validate_app_config, "live:pages:app_config"),
        (f"{VERCEL_BASE}/api/agent/system", validate_system_contract, "live:vercel:system"),
        (f"{VERCEL_BASE}/api/agent/offers", validate_offer_catalog, "live:vercel:offers"),
        (f"{VERCEL_BASE}/api/agent/app-config", validate_app_config, "live:vercel:app_config"),
    ]
    for url, validator, source in live_json_targets:
        text, check = fetch_url(url)
        checks.append(check)
        if text is None:
            continue
        data, parse_check = parse_json_text(text, source)
        checks.append(parse_check)
        if data is not None:
            checks.extend(validator(data, source))

    for url, source in [
        (f"{PAGES_BASE}/supporter.html", "live:pages:supporter_page"),
        (f"{PAGES_BASE}/offers/", "live:pages:offers_page"),
    ]:
        text, check = fetch_url(url)
        checks.append(check)
        if text is not None:
            checks.extend(validate_supporter_page(text, source))

    return checks


def write_report(path: Path, checks: list[CheckResult], live: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "scbe-remote-app-config-smoke-v1",
        "live": live,
        "ok": all(check.ok for check in checks),
        "checks": [asdict(check) for check in checks],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="also check live GitHub Pages and Vercel endpoints")
    parser.add_argument("--json", action="store_true", dest="as_json", help="print JSON instead of line output")
    parser.add_argument("--report", type=Path, help="write a JSON report to this path")
    args = parser.parse_args(argv)

    checks = run_checks(live=args.live)
    ok = all(check.ok for check in checks)

    if args.report:
        write_report(args.report, checks, live=args.live)

    if args.as_json:
        print(json.dumps({"ok": ok, "live": args.live, "checks": [asdict(check) for check in checks]}, indent=2))
    else:
        mode = "LIVE" if args.live else "LOCAL"
        print(f"SCBE remote app config smoke ({mode})")
        for check in checks:
            tag = "PASS" if check.ok else "FAIL"
            print(f"[{tag}] {check.name} - {check.detail}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
