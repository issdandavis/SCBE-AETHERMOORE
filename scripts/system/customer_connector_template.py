#!/usr/bin/env python3
"""Generate customer connector onboarding templates with admin PIN hashing.

Creates a per-customer folder containing:
1) connector_profile.json
2) .env.template
3) admin_pin.json (salted hash only, no plaintext PIN stored on disk)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
ACCESS_MAP_DEFAULT = REPO_ROOT / "config" / "web_access_map.json"
OUTPUT_ROOT_DEFAULT = REPO_ROOT / "external" / "intake"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_access_map(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def match_service(services: list[dict[str, Any]], domain: str) -> dict[str, Any]:
    d = domain.lower().strip()
    best: dict[str, Any] = {}
    best_len = -1
    for svc in services:
        s_domain = str(svc.get("domain", "")).lower().strip()
        if not s_domain:
            continue
        if d == s_domain or d.endswith("." + s_domain) or s_domain in d:
            if len(s_domain) > best_len:
                best = svc
                best_len = len(s_domain)
    return best


def pin_hash(pin: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,
    ).hex()
    return salt, digest


def generate_pin() -> str:
    # 8-digit PIN gives low friction for operator handoff;
    # hash is strong with high iteration PBKDF2 and random salt.
    return "".join(str(secrets.randbelow(10)) for _ in range(8))


def build_connector_entry(service: dict[str, Any], domain: str) -> dict[str, Any]:
    access = service.get("access_methods", {}) if isinstance(service.get("access_methods", {}), dict) else {}
    api = access.get("api", {}) if isinstance(access.get("api", {}), dict) else {}
    browser = access.get("browser", {}) if isinstance(access.get("browser", {}), dict) else {}
    cli = access.get("cli", {}) if isinstance(access.get("cli", {}), dict) else {}

    env_vars: list[str] = []
    if api.get("available") and str(api.get("env_var", "")).strip():
        env_vars.append(str(api.get("env_var", "")).strip())

    return {
        "service": service.get("service", domain),
        "domain": domain,
        "tier": service.get("tier", "unknown"),
        "channels": {
            "api": bool(api.get("available", False)),
            "browser": bool(browser.get("available", False)),
            "cli": bool(cli.get("available", False)),
        },
        "api_base_url": api.get("base_url", ""),
        "auth_env_vars": env_vars,
        "notes": service.get("notes", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate customer connector onboarding template + admin PIN hash.")
    parser.add_argument("--customer-id", required=True, help="Customer slug/id (used for output folder).")
    parser.add_argument(
        "--connectors",
        default="github.com,shopify.com,notion.so,huggingface.co",
        help="Comma-separated connector domains to include.",
    )
    parser.add_argument(
        "--admin-pin",
        default="",
        help="Optional admin PIN. If omitted, one-time PIN is generated and printed.",
    )
    parser.add_argument("--access-map", default=str(ACCESS_MAP_DEFAULT), help="Path to web_access_map.json.")
    parser.add_argument("--out-root", default=str(OUTPUT_ROOT_DEFAULT), help="Output root for customer intake folders.")
    args = parser.parse_args()

    access_map = load_access_map(Path(args.access_map).expanduser().resolve())
    services = access_map.get("services", []) if isinstance(access_map.get("services", []), list) else []
    connector_domains = [item.strip().lower() for item in args.connectors.split(",") if item.strip()]

    out_dir = Path(args.out_root).expanduser().resolve() / args.customer_id
    out_dir.mkdir(parents=True, exist_ok=True)

    pin = args.admin_pin.strip() or generate_pin()
    generated_pin = not bool(args.admin_pin.strip())
    salt, digest = pin_hash(pin)

    connectors: list[dict[str, Any]] = []
    env_vars: list[str] = []
    for domain in connector_domains:
        service = match_service(services, domain)
        entry = build_connector_entry(service, domain)
        connectors.append(entry)
        for env_key in entry.get("auth_env_vars", []):
            if env_key not in env_vars:
                env_vars.append(env_key)

    profile = {
        "profile_id": f"cust-{args.customer_id}-{uuid.uuid4().hex[:8]}",
        "customer_id": args.customer_id,
        "created_at": utc_now(),
        "connectors": connectors,
        "runtime_policy": {
            "strict_connectivity": True,
            "default_channel_priority": ["api", "cli", "browser"],
            "allow_browser_fallback": True,
        },
        "admin": {
            "pin_hash_ref": "admin_pin.json",
            "pin_policy": "8+ digits, rotate monthly",
        },
    }

    admin_pin_payload = {
        "customer_id": args.customer_id,
        "created_at": utc_now(),
        "algorithm": "pbkdf2_sha256",
        "iterations": 200000,
        "salt": salt,
        "pin_hash": digest,
    }

    env_lines = [
        "# Customer connector environment template",
        "# Fill values, then load into runtime secret store / env",
    ]
    for name in env_vars:
        env_lines.append(f"{name}=")
    if not env_vars:
        env_lines.append("# No API env vars detected for selected connectors.")

    profile_path = out_dir / "connector_profile.json"
    admin_pin_path = out_dir / "admin_pin.json"
    env_path = out_dir / ".env.template"

    profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    admin_pin_path.write_text(json.dumps(admin_pin_payload, indent=2), encoding="utf-8")
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    result = {
        "ok": True,
        "customer_id": args.customer_id,
        "output_dir": str(out_dir),
        "files": [str(profile_path), str(admin_pin_path), str(env_path)],
        "connectors_count": len(connectors),
        "env_vars_count": len(env_vars),
        "generated_pin": generated_pin,
    }
    if generated_pin:
        # Show once in terminal output, never persisted to disk.
        result["one_time_admin_pin"] = pin
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

