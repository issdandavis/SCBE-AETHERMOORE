#!/usr/bin/env python3
"""Open and use a generated customer connector profile for real task routing.

This script is the runtime bridge between:
1) external/intake/<customer>/connector_profile.json
2) browser_chain_dispatcher task assignment
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

# Ensure repo root is importable when running as a script path.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.system.browser_chain_dispatcher import BrowserChainDispatcher, build_default_fleet


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def match_connector(profile: dict[str, Any], domain: str) -> dict[str, Any]:
    d = domain.lower().strip()
    for connector in profile.get("connectors", []):
        c_domain = str(connector.get("domain", "")).lower().strip()
        if not c_domain:
            continue
        if d == c_domain or d.endswith("." + c_domain) or c_domain in d:
            return connector
    return {}


def verify_admin_pin(profile_path: Path, supplied_pin: str) -> bool:
    pin_file = profile_path.parent / "admin_pin.json"
    if not pin_file.exists():
        return False
    payload = load_json(pin_file)
    iterations = int(payload.get("iterations", 200000))
    salt = str(payload.get("salt", ""))
    expected = str(payload.get("pin_hash", ""))
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        supplied_pin.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return digest == expected


def missing_env_for_channel(connector: dict[str, Any], channel: str) -> list[str]:
    if channel != "api":
        return []
    env_vars = connector.get("auth_env_vars", [])
    if not isinstance(env_vars, list):
        return []
    return [name for name in env_vars if not os.getenv(str(name))]


def select_channel(connector: dict[str, Any], requested: str) -> str:
    channels = connector.get("channels", {}) if isinstance(connector.get("channels", {}), dict) else {}
    if requested:
        req = requested.lower().strip()
        if req in {"api", "cli", "browser"} and bool(channels.get(req, False)):
            return req

    api_available = bool(channels.get("api", False))
    if api_available and not missing_env_for_channel(connector, "api"):
        return "api"
    if bool(channels.get("cli", False)):
        return "cli"
    if api_available:
        return "api"
    if bool(channels.get("browser", False)):
        return "browser"
    return "browser"


def main() -> int:
    parser = argparse.ArgumentParser(description="Use customer connector profile to run a task assignment.")
    parser.add_argument("--profile", required=True, help="Path to connector_profile.json")
    parser.add_argument("--domain", required=True, help="Target domain")
    parser.add_argument("--task", required=True, help="Task text")
    parser.add_argument("--channel", default="", choices=["", "api", "cli", "browser"], help="Preferred channel")
    parser.add_argument("--admin-pin", default="", help="Optional admin PIN for profile verification")
    parser.add_argument("--strict", action="store_true", help="Fail if required channel env vars are missing")
    parser.add_argument("--access-map", default="", help="Optional dispatcher access map override")
    parser.add_argument("--cost-profile", default="", help="Optional dispatcher cost profile override")
    args = parser.parse_args()

    profile_path = Path(args.profile).expanduser().resolve()
    profile = load_json(profile_path)
    connector = match_connector(profile, args.domain)
    if not connector:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "domain_not_in_customer_profile",
                    "domain": args.domain,
                    "profile": str(profile_path),
                },
                indent=2,
            )
        )
        return 1

    pin_verified = None
    if args.admin_pin:
        pin_verified = verify_admin_pin(profile_path, args.admin_pin)
        if not pin_verified:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "admin_pin_verification_failed",
                        "profile": str(profile_path),
                    },
                    indent=2,
                )
            )
            return 1

    channel = select_channel(connector, args.channel)
    missing_env = missing_env_for_channel(connector, channel)
    if args.strict and missing_env:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "connector_env_missing",
                    "channel": channel,
                    "missing_env_vars": missing_env,
                    "domain": args.domain,
                },
                indent=2,
            )
        )
        return 1

    dispatcher = BrowserChainDispatcher(
        access_map_path=args.access_map or None,
        cost_profile_path=args.cost_profile or None,
    )
    for tentacle in build_default_fleet():
        dispatcher.register_tentacle(tentacle)

    payload = {
        "channel": channel,
        "customer_id": profile.get("customer_id", ""),
        "profile_id": profile.get("profile_id", ""),
        "requested_connector": connector.get("service", ""),
    }
    result = dispatcher.assign_task(
        domain=args.domain,
        task_type=args.task,
        payload=payload,
        strict_connectivity=bool(args.strict),
    )
    result["profile_use"] = {
        "profile": str(profile_path),
        "customer_id": profile.get("customer_id", ""),
        "profile_id": profile.get("profile_id", ""),
        "connector_service": connector.get("service", ""),
        "channel": channel,
        "missing_env_vars_for_channel": missing_env,
        "admin_pin_verified": pin_verified,
    }
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
