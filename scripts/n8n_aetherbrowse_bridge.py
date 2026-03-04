"""Send browser tasks to the SCBE n8n webhook endpoint.

Usage:
  python scripts/n8n_aetherbrowse_bridge.py `
    --actions '[{"action":"navigate","target":"https://example.com"}]'
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List
import urllib.error
import urllib.request


def _resolve_api_key() -> str:
    for key_name in ("SCBE_API_KEY", "SCBE_BROWSER_API_KEY", "N8N_API_KEY", "BROWSER_AGENT_API_KEY"):
        key = os.getenv(key_name, "").strip()
        if key:
            return key
    raise RuntimeError("No browser API key found. Set SCBE_API_KEY, SCBE_BROWSER_API_KEY, N8N_API_KEY, or BROWSER_AGENT_API_KEY.")


def _resolve_url() -> str:
    return os.getenv(
        "SCBE_BROWSER_WEBHOOK_URL",
        "http://127.0.0.1:8001/v1/integrations/n8n/browse",
    ).strip()


def _build_headers(token: str) -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-API-Key": token,
    }


def _parse_actions(raw: str) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON actions: {exc}") from exc
    if not isinstance(payload, list):
        raise ValueError("Actions payload must be a list")
    return payload


def _request(payload: Dict[str, Any], url: str, headers: Dict[str, str]) -> Dict[str, Any]:
    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers=headers | {"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit browser actions to AetherBrowse via n8n-compatible endpoint.")
    parser.add_argument(
        "--actions",
        required=True,
        help='JSON list like: [{"action":"navigate","target":"https://example.com"}]',
    )
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--workflow-id", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source", default="n8n")
    parser.add_argument(
        "--url",
        default=_resolve_url(),
        help="Full URL to POST browse requests to.",
    )
    args = parser.parse_args()

    key = _resolve_api_key()
    headers = _build_headers(key)

    payload = {
        "actions": _parse_actions(args.actions),
        "session_id": args.session_id,
        "dry_run": args.dry_run,
        "run_id": args.run_id,
        "workflow_id": args.workflow_id,
        "source": args.source,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    result = _request(payload, args.url, headers)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"[aetherbrowse-bridge] {exc}", file=sys.stderr)
        raise SystemExit(1)
