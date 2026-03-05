#!/usr/bin/env python3
"""Terminal-first sell lane for SCBE monetization workflows.

Runs core selling actions without requiring dashboard/browser hopping:
- load credentials from local secret store into process env
- publish Shopify product catalog live
- optionally post an X update
- run core connector health checks
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.security.secret_store import get_secret  # noqa: E402


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mask(value: str) -> str:
    if not value:
        return "missing"
    if len(value) <= 8:
        return "set"
    return f"{value[:4]}...{value[-4:]}"


def _load_secret_env() -> dict[str, str]:
    keys = [
        "SHOPIFY_SHOP",
        "SHOPIFY_SHOP_DOMAIN",
        "SHOPIFY_ACCESS_TOKEN",
        "SHOPIFY_ADMIN_TOKEN",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "XAI_API_KEY",
        "GROK_API_KEY",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "X_BEARER_TOKEN",
        "ZAPIER_WEBHOOK_URL",
        "HF_TOKEN",
        "GITHUB_TOKEN",
        "NOTION_TOKEN",
    ]
    status: dict[str, str] = {}

    for key in keys:
        existing = os.getenv(key, "").strip()
        if existing:
            status[key] = _mask(existing)
            continue

        stored = get_secret(key, "").strip()
        if stored:
            os.environ[key] = stored
            status[key] = _mask(stored)
        else:
            status[key] = "missing"

    # Common Shopify alias fallback.
    if not os.getenv("SHOPIFY_SHOP", "").strip():
        alias = os.getenv("SHOPIFY_SHOP_DOMAIN", "").strip()
        if alias:
            os.environ["SHOPIFY_SHOP"] = alias
            status["SHOPIFY_SHOP"] = _mask(alias)

    return status


def _run_cmd(cmd: list[str], *, timeout: int = 180) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def _connector_health() -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/connector_health_check.py",
            "--checks",
            "github",
            "notion",
            "huggingface",
            "zapier",
            "--output",
            "artifacts/connector_health/terminal_sell_health.json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        env=env,
    )
    return {
        "command": "python scripts/connector_health_check.py --checks github notion huggingface zapier",
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run sell actions from terminal only")
    parser.add_argument("--skip-shopify", action="store_true", help="Skip Shopify publish step")
    parser.add_argument("--x-text", default="", help="Optional X post text")
    parser.add_argument("--dry-run", action="store_true", help="Do not post/publish, only check status")
    parser.add_argument(
        "--strict-health",
        action="store_true",
        help="Fail command when connector health check returns non-zero",
    )
    parser.add_argument(
        "--report",
        default="artifacts/monetization/terminal_sell_report.json",
        help="Report output path",
    )
    args = parser.parse_args()

    report: dict[str, Any] = {
        "generated_at_utc": _now_utc(),
        "secret_status": _load_secret_env(),
        "actions": [],
    }

    if args.dry_run:
        report["actions"].append({"name": "dry_run", "status": "ok"})
    else:
        if not args.skip_shopify:
            report["actions"].append(
                {
                    "name": "shopify_publish_live",
                    "result": _run_cmd([sys.executable, "scripts/shopify_bridge.py", "products", "--publish-live"]),
                }
            )

        if args.x_text.strip():
            report["actions"].append(
                {
                    "name": "post_x",
                    "result": _run_cmd(
                        [
                            sys.executable,
                            "scripts/publish/post_to_x.py",
                            "--text",
                            args.x_text.strip(),
                        ]
                    ),
                }
            )

    report["actions"].append({"name": "connector_health", "result": _connector_health()})

    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"report={out.resolve()}")
    print("secret_status:")
    for key, value in report["secret_status"].items():
        print(f"  {key}={value}")

    for action in report["actions"]:
        name = action.get("name")
        if name in {"dry_run"}:
            print(f"action={name} status=ok")
            continue

        result = action.get("result", {})
        print(f"action={name} returncode={result.get('returncode')}")

    # Non-zero on execution failures. Connector health is advisory unless strict mode is enabled.
    failure = False
    for action in report["actions"]:
        result = action.get("result")
        if not isinstance(result, dict):
            continue
        rc = int(result.get("returncode", 0))
        if rc == 0:
            continue
        if action.get("name") == "connector_health" and not args.strict_health:
            continue
        if rc != 0:
            failure = True
    return 1 if failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
