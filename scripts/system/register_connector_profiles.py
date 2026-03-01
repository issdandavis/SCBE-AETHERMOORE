#!/usr/bin/env python3
"""Register SCBE connector profiles (free / paid / all) via /mobile/connectors.

This script is idempotent by connector name+kind:
- by default it skips existing connectors
- with --replace-existing it deletes and recreates
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from src.security.secret_store import get_secret, pick_secret


@dataclass(frozen=True)
class ConnectorSpec:
    name: str
    kind: str
    profile: str
    endpoint_envs: tuple[str, ...] = ()
    endpoint_fallback_path: str = ""
    payload_mode: str = "scbe_step"
    http_method: str = "POST"
    auth_mode: str = "none"  # none|header|bearer
    auth_required: bool = False
    auth_token_envs: tuple[str, ...] = ()
    auth_header_name: str = "x-api-key"
    shop_domain_envs: tuple[str, ...] = ()
    shopify_api_version_env: str = "SHOPIFY_API_VERSION"


FREE_SPECS: tuple[ConnectorSpec, ...] = (
    ConnectorSpec(
        name="n8n-swarm-intake",
        kind="n8n",
        profile="free",
        endpoint_envs=("N8N_CONNECTOR_WEBHOOK_URL",),
        endpoint_fallback_path="/webhook/scbe-notion-github-swarm",
    ),
    ConnectorSpec(
        name="zapier-main-hook",
        kind="zapier",
        profile="free",
        endpoint_envs=("ZAPIER_WEBHOOK_URL",),
    ),
    ConnectorSpec(
        name="telegram-ops-generic",
        kind="generic_webhook",
        profile="free",
        endpoint_envs=("TELEGRAM_CONNECTOR_WEBHOOK_URL", "SCBE_TELEGRAM_WEBHOOK_URL"),
    ),
    ConnectorSpec(
        name="github-actions-fleet",
        kind="github_actions",
        profile="free",
        endpoint_envs=("GITHUB_ACTIONS_WEBHOOK_URL", "GITHUB_ACTIONS_CONNECTOR_URL"),
        endpoint_fallback_path="/webhook/scbe-task",
        auth_mode="bearer",
        auth_required=False,
        auth_token_envs=("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_PAT"),
    ),
    ConnectorSpec(
        name="notion-research-sync",
        kind="notion",
        profile="free",
        endpoint_envs=("NOTION_CONNECTOR_WEBHOOK_URL",),
        endpoint_fallback_path="/webhook/scbe-notion-github-swarm",
    ),
    ConnectorSpec(
        name="airtable-funnel-sync",
        kind="airtable",
        profile="free",
        endpoint_envs=("AIRTABLE_CONNECTOR_WEBHOOK_URL",),
        endpoint_fallback_path="/webhook/scbe-m5-funnel",
    ),
    ConnectorSpec(
        name="hf-pipeline-generic",
        kind="generic_webhook",
        profile="free",
        endpoint_envs=("HF_CONNECTOR_WEBHOOK_URL", "HUGGINGFACE_CONNECTOR_WEBHOOK_URL"),
        endpoint_fallback_path="/webhook/vertex-hf-pipeline",
        auth_mode="bearer",
        auth_required=False,
        auth_token_envs=("HF_TOKEN", "HUGGINGFACE_TOKEN"),
    ),
)


PAID_SPECS: tuple[ConnectorSpec, ...] = (
    ConnectorSpec(
        name="shopify-admin-read",
        kind="shopify",
        profile="paid",
        auth_mode="header",
        auth_required=True,
        auth_token_envs=("SHOPIFY_ACCESS_TOKEN",),
        auth_header_name="X-Shopify-Access-Token",
        shop_domain_envs=("SHOPIFY_SHOP_DOMAIN", "SHOP_DOMAIN"),
    ),
    ConnectorSpec(
        name="slack-ops-webhook",
        kind="slack",
        profile="paid",
        endpoint_envs=("SLACK_CONNECTOR_WEBHOOK_URL", "SLACK_WEBHOOK_URL"),
    ),
    ConnectorSpec(
        name="linear-ops-webhook",
        kind="linear",
        profile="paid",
        endpoint_envs=("LINEAR_CONNECTOR_WEBHOOK_URL",),
        auth_mode="bearer",
        auth_required=False,
        auth_token_envs=("LINEAR_API_KEY",),
    ),
    ConnectorSpec(
        name="discord-ops-webhook",
        kind="discord",
        profile="paid",
        endpoint_envs=("DISCORD_CONNECTOR_WEBHOOK_URL", "DISCORD_WEBHOOK_URL"),
    ),
    ConnectorSpec(
        name="asana-ops-generic",
        kind="generic_webhook",
        profile="paid",
        endpoint_envs=("ASANA_CONNECTOR_WEBHOOK_URL",),
        auth_mode="bearer",
        auth_required=False,
        auth_token_envs=("ASANA_PAT",),
    ),
    ConnectorSpec(
        name="stripe-ops-generic",
        kind="generic_webhook",
        profile="paid",
        endpoint_envs=("STRIPE_CONNECTOR_WEBHOOK_URL",),
        auth_mode="bearer",
        auth_required=False,
        auth_token_envs=("STRIPE_API_KEY",),
    ),
)


def _pick_env(*names: str) -> str:
    for name in names:
        _, value = pick_secret(name)
        if not value:
            value = os.getenv(name, "").strip()
        if value:
            return value
    return ""
        if value:
            return value
    return ""


def _normalize_base_url(url: str) -> str:
    return url.strip().rstrip("/")


def _api_call(
    *,
    base_url: str,
    api_key: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    timeout_sec: int = 20,
) -> tuple[int | None, dict[str, Any], str]:
    url = f"{_normalize_base_url(base_url)}{path}"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url=url, headers=headers, data=payload, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed: dict[str, Any]
            if raw.strip():
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = {"raw": raw}
            else:
                parsed = {}
            return int(resp.status), parsed, ""
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        parsed: dict[str, Any]
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return int(exc.code), parsed, f"http_error_{exc.code}"
    except urllib.error.URLError as exc:
        return None, {"error": str(getattr(exc, "reason", exc))}, "url_error"
    except Exception as exc:  # noqa: BLE001
        return None, {"error": str(exc)}, "exception"


def _resolve_spec(spec: ConnectorSpec, *, n8n_base_url: str) -> tuple[dict[str, Any] | None, str]:
    endpoint = _pick_env(*spec.endpoint_envs)
    if (not endpoint) and spec.endpoint_fallback_path and n8n_base_url:
        endpoint = f"{_normalize_base_url(n8n_base_url)}{spec.endpoint_fallback_path}"

    shop_domain = _pick_env(*spec.shop_domain_envs)
    auth_token = _pick_env(*spec.auth_token_envs)
    auth_mode = spec.auth_mode
    auth_header_name = spec.auth_header_name

    if spec.kind == "shopify":
        if not endpoint and not shop_domain:
            return None, "missing_shop_domain_or_endpoint"
    else:
        if not endpoint:
            return None, "missing_endpoint"

    if auth_mode != "none":
        if not auth_token and spec.auth_required:
            return None, "missing_auth_token"
        if not auth_token:
            auth_mode = "none"

    payload: dict[str, Any] = {
        "name": spec.name,
        "kind": spec.kind,
        "http_method": spec.http_method,
        "payload_mode": spec.payload_mode,
        "auth_type": auth_mode,
        "enabled": True,
    }
    if endpoint:
        payload["endpoint_url"] = endpoint
    if auth_token and auth_mode != "none":
        payload["auth_token"] = auth_token
    if auth_mode == "header":
        payload["auth_header_name"] = auth_header_name
    if spec.kind == "shopify":
        if shop_domain:
            payload["shop_domain"] = shop_domain
        payload["shopify_api_version"] = os.getenv(spec.shopify_api_version_env, "2025-10").strip() or "2025-10"
    return payload, ""


def _load_specs(profile: str) -> list[ConnectorSpec]:
    if profile == "free":
        return list(FREE_SPECS)
    if profile == "paid":
        return list(PAID_SPECS)
    return list(FREE_SPECS + PAID_SPECS)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Register connector profiles into SCBE /mobile/connectors.")
    parser.add_argument("--profile", choices=["free", "paid", "all"], default="all")
    parser.add_argument("--base-url", default=os.getenv("SCBE_MOBILE_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument(
        "--api-key",
        default=get_secret("SCBE_MOBILE_API_KEY") or get_secret("SCBE_API_KEY") or "demo_key_12345",
        help="Mobile API x-api-key.",
    )
    parser.add_argument("--n8n-base-url", default=os.getenv("N8N_BASE_URL", ""))
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout-sec", type=int, default=20)
    parser.add_argument("--output", default="artifacts/connector_health/connector_registration_report.json")
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    specs = _load_specs(args.profile)
    started = int(time.time())

    report: dict[str, Any] = {
        "generated_at_unix": started,
        "profile": args.profile,
        "base_url": args.base_url,
        "dry_run": bool(args.dry_run),
        "replace_existing": bool(args.replace_existing),
        "results": [],
    }

    if not args.dry_run:
        status, body, error = _api_call(
            base_url=args.base_url,
            api_key=args.api_key,
            method="GET",
            path="/mobile/connectors",
            timeout_sec=args.timeout_sec,
        )
        if status != 200:
            report["fatal"] = {
                "step": "list_connectors",
                "status": status,
                "error": error,
                "response": body,
            }
            _write_report(report, args.output)
            print(json.dumps(report, indent=2))
            return 1
        existing_rows = (body.get("data") or []) if isinstance(body, dict) else []
    else:
        existing_rows = []

    existing_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in existing_rows:
        key = (str(row.get("name", "")), str(row.get("kind", "")))
        if all(key):
            existing_by_key[key] = row

    created = replaced = skipped = failed = 0
    for spec in specs:
        payload, reason = _resolve_spec(spec, n8n_base_url=args.n8n_base_url)
        result: dict[str, Any] = {
            "name": spec.name,
            "kind": spec.kind,
            "profile": spec.profile,
        }
        if payload is None:
            result.update({"action": "skipped", "reason": reason})
            report["results"].append(result)
            skipped += 1
            continue

        existing = existing_by_key.get((spec.name, spec.kind))
        if args.dry_run:
            action = "would_replace" if (existing and args.replace_existing) else "would_skip_existing" if existing else "would_create"
            result.update(
                {
                    "action": action,
                    "payload": {k: v for k, v in payload.items() if k != "auth_token"},
                }
            )
            report["results"].append(result)
            continue

        if existing and not args.replace_existing:
            result.update(
                {
                    "action": "skipped",
                    "reason": "already_exists",
                    "connector_id": existing.get("connector_id"),
                }
            )
            report["results"].append(result)
            skipped += 1
            continue

        if existing and args.replace_existing:
            connector_id = str(existing.get("connector_id", "")).strip()
            if connector_id:
                del_status, del_body, del_error = _api_call(
                    base_url=args.base_url,
                    api_key=args.api_key,
                    method="DELETE",
                    path=f"/mobile/connectors/{connector_id}",
                    timeout_sec=args.timeout_sec,
                )
                if del_status != 200:
                    result.update(
                        {
                            "action": "failed",
                            "reason": "delete_existing_failed",
                            "status": del_status,
                            "error": del_error,
                            "response": del_body,
                        }
                    )
                    report["results"].append(result)
                    failed += 1
                    continue

        post_status, post_body, post_error = _api_call(
            base_url=args.base_url,
            api_key=args.api_key,
            method="POST",
            path="/mobile/connectors",
            body=payload,
            timeout_sec=args.timeout_sec,
        )
        if post_status == 200:
            data = post_body.get("data") if isinstance(post_body, dict) else {}
            result.update(
                {
                    "action": "replaced" if existing else "created",
                    "connector_id": (data or {}).get("connector_id"),
                    "endpoint_url": (data or {}).get("endpoint_url"),
                }
            )
            if existing:
                replaced += 1
            else:
                created += 1
        else:
            result.update(
                {
                    "action": "failed",
                    "status": post_status,
                    "error": post_error,
                    "response": post_body,
                }
            )
            failed += 1
        report["results"].append(result)

    report["counts"] = {
        "total_specs": len(specs),
        "created": created,
        "replaced": replaced,
        "skipped": skipped,
        "failed": failed,
    }
    _write_report(report, args.output)
    print(json.dumps(report, indent=2))
    return 1 if failed else 0


def _write_report(report: dict[str, Any], output_path: str) -> None:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(run())
