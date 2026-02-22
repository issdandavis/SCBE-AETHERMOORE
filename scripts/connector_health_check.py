#!/usr/bin/env python3
"""Connector health checks for GitHub, Notion, and Google Drive routes.

The script is designed for nightly automation and local diagnostics.
It reports machine-readable JSON and exits non-zero only on actionable failures.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_CHECKS = ("github", "notion", "drive")


@dataclass
class CheckResult:
    name: str
    status: str
    detail: dict[str, Any]


def _request_json(
    url: str,
    headers: dict[str, str],
    timeout: int = 20,
) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(url=url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8")
            return int(resp.status), json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        body: dict[str, Any]
        try:
            body = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            body = {"raw": payload}
        return int(exc.code), body


def _pick_env(*keys: str) -> tuple[str, str]:
    for key in keys:
        value = os.getenv(key, "").strip()
        if value:
            return key, value
    return "", ""


def check_github(repo: str) -> CheckResult:
    key_name, token = _pick_env("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_PAT")
    if not token:
        return CheckResult(
            name="github",
            status="needs_configuration",
            detail={"reason": "missing_token", "accepted_env_keys": ["GITHUB_TOKEN", "GH_TOKEN", "GITHUB_PAT"]},
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "scbe-connector-health-check",
    }
    status_user, user_body = _request_json("https://api.github.com/user", headers=headers)
    if status_user != 200:
        return CheckResult(
            name="github",
            status="error",
            detail={
                "reason": "auth_failed",
                "http_status": status_user,
                "token_env": key_name,
                "response": user_body,
            },
        )

    repo_url = f"https://api.github.com/repos/{repo}"
    status_repo, repo_body = _request_json(repo_url, headers=headers)
    if status_repo != 200:
        return CheckResult(
            name="github",
            status="error",
            detail={
                "reason": "repo_access_failed",
                "http_status": status_repo,
                "repo": repo,
                "token_env": key_name,
                "response": repo_body,
            },
        )

    return CheckResult(
        name="github",
        status="ok",
        detail={
            "token_env": key_name,
            "login": user_body.get("login"),
            "repo": repo_body.get("full_name"),
            "default_branch": repo_body.get("default_branch"),
        },
    )


def check_notion(page_id: str = "") -> CheckResult:
    key_name, token = _pick_env("NOTION_API_KEY", "NOTION_TOKEN", "NOTION_MCP_TOKEN")
    if not token:
        return CheckResult(
            name="notion",
            status="needs_configuration",
            detail={
                "reason": "missing_token",
                "accepted_env_keys": ["NOTION_API_KEY", "NOTION_TOKEN", "NOTION_MCP_TOKEN"],
            },
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    status_user, user_body = _request_json("https://api.notion.com/v1/users/me", headers=headers)
    if status_user != 200:
        return CheckResult(
            name="notion",
            status="error",
            detail={
                "reason": "auth_failed",
                "http_status": status_user,
                "token_env": key_name,
                "response": user_body,
            },
        )

    detail: dict[str, Any] = {
        "token_env": key_name,
        "workspace_name": user_body.get("name"),
        "workspace_id": user_body.get("id"),
    }

    if page_id:
        status_page, page_body = _request_json(f"https://api.notion.com/v1/pages/{page_id}", headers=headers)
        if status_page != 200:
            return CheckResult(
                name="notion",
                status="error",
                detail={
                    **detail,
                    "reason": "page_access_failed",
                    "http_status": status_page,
                    "page_id": page_id,
                    "response": page_body,
                },
            )
        detail["page_id"] = page_id
        detail["page_last_edited"] = page_body.get("last_edited_time")

    return CheckResult(name="notion", status="ok", detail=detail)


def check_drive() -> CheckResult:
    key_name, token = _pick_env("GOOGLE_DRIVE_ACCESS_TOKEN", "GDRIVE_ACCESS_TOKEN", "GOOGLE_OAUTH_ACCESS_TOKEN")
    if not token:
        return CheckResult(
            name="drive",
            status="needs_configuration",
            detail={
                "reason": "missing_token",
                "accepted_env_keys": [
                    "GOOGLE_DRIVE_ACCESS_TOKEN",
                    "GDRIVE_ACCESS_TOKEN",
                    "GOOGLE_OAUTH_ACCESS_TOKEN",
                ],
            },
        )

    headers = {"Authorization": f"Bearer {token}"}
    status, body = _request_json("https://www.googleapis.com/drive/v3/about?fields=user", headers=headers)
    if status != 200:
        return CheckResult(
            name="drive",
            status="error",
            detail={
                "reason": "auth_failed",
                "http_status": status,
                "token_env": key_name,
                "response": body,
            },
        )

    user = body.get("user", {})
    return CheckResult(
        name="drive",
        status="ok",
        detail={
            "token_env": key_name,
            "display_name": user.get("displayName"),
            "email": user.get("emailAddress"),
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run connector health checks.")
    parser.add_argument(
        "--checks",
        nargs="+",
        choices=VALID_CHECKS,
        default=list(VALID_CHECKS),
        help="Checks to run (default: github notion drive).",
    )
    parser.add_argument("--github-repo", default="issdandavis/SCBE-AETHERMOORE", help="Repository for GitHub route test.")
    parser.add_argument("--notion-page-id", default="", help="Optional Notion page id for read-access validation.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any selected check is not 'ok' (including needs_configuration).",
    )
    parser.add_argument(
        "--output",
        default="artifacts/connector_health/connector_health_report.json",
        help="Output JSON path.",
    )
    return parser.parse_args()


def run() -> int:
    args = parse_args()

    checks: list[CheckResult] = []
    if "github" in args.checks:
        checks.append(check_github(repo=args.github_repo))
    if "notion" in args.checks:
        checks.append(check_notion(page_id=args.notion_page_id))
    if "drive" in args.checks:
        checks.append(check_drive())

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "strict_mode": args.strict,
        "checks": [{ "name": c.name, "status": c.status, "detail": c.detail } for c in checks],
    }
    summary["counts"] = {
        "ok": sum(1 for c in checks if c.status == "ok"),
        "needs_configuration": sum(1 for c in checks if c.status == "needs_configuration"),
        "error": sum(1 for c in checks if c.status == "error"),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    if args.strict:
        return 1 if any(c.status != "ok" for c in checks) else 0
    return 1 if any(c.status == "error" for c in checks) else 0


if __name__ == "__main__":
    raise SystemExit(run())
