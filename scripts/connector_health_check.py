#!/usr/bin/env python3
"""Connector health checks for SCBE free/paid integration routes.

The script is designed for nightly automation and local diagnostics.
It emits machine-readable JSON and exits non-zero only on actionable failures
unless strict mode is enabled.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.security.secret_store import get_secret


VALID_CHECKS = (
    "github",
    "notion",
    "drive",
    "huggingface",
    "airtable",
    "zapier",
    "telegram",
    "n8n",
    "bridge",
    "playwright",
)


@dataclass
class CheckResult:
    name: str
    status: str
    detail: dict[str, Any]


def _request_json(
    url: str,
    headers: dict[str, str] | None = None,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: int = 20,
) -> tuple[int | None, dict[str, Any], str]:
    req_headers = dict(headers or {})
    payload_bytes: bytes | None = None
    if body is not None:
        payload_bytes = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(
        url=url,
        headers=req_headers,
        method=method,
        data=payload_bytes,
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
            parsed: dict[str, Any]
            if payload:
                try:
                    parsed = json.loads(payload)
                except json.JSONDecodeError:
                    parsed = {"raw": payload}
            else:
                parsed = {}
            return int(resp.status), parsed, ""
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        body_obj: dict[str, Any]
        try:
            body_obj = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            body_obj = {"raw": payload}
        return int(exc.code), body_obj, f"http_error_{exc.code}"
    except urllib.error.URLError as exc:
        return None, {"error": str(getattr(exc, "reason", exc))}, "url_error"
    except Exception as exc:  # noqa: BLE001
        return None, {"error": str(exc)}, "exception"


def _pick_env(*keys: str) -> tuple[str, str]:
    for key in keys:
        value = get_secret(key, "").strip()
        if value:
            return key, value
    return "", ""


def _normalize_base_url(url: str) -> str:
    return url.strip().rstrip("/")


def check_github(repo: str) -> CheckResult:
    key_name, token = _pick_env("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_PAT")
    if not token:
        return CheckResult(
            name="github",
            status="needs_configuration",
            detail={
                "reason": "missing_token",
                "accepted_env_keys": ["GITHUB_TOKEN", "GH_TOKEN", "GITHUB_PAT"],
            },
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "scbe-connector-health-check",
    }
    repo_url = f"https://api.github.com/repos/{repo}"
    status_repo, repo_body, _ = _request_json(repo_url, headers=headers)
    if status_repo == 200:
        status_user, user_body, _ = _request_json("https://api.github.com/user", headers=headers)
        detail = {
            "token_env": key_name,
            "repo": repo_body.get("full_name"),
            "default_branch": repo_body.get("default_branch"),
        }

        if status_user == 200:
            detail["login"] = user_body.get("login")
            return CheckResult(name="github", status="ok", detail=detail)

        detail.update(
            {
                "user_status": status_user,
                "user_error": user_body,
                "note": "Token is valid for repository context; /user endpoint not accessible.",
            }
        )
        return CheckResult(name="github", status="ok", detail=detail)

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
    status_user, user_body, _ = _request_json("https://api.notion.com/v1/users/me", headers=headers)
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
        status_page, page_body, _ = _request_json(f"https://api.notion.com/v1/pages/{page_id}", headers=headers)
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
    status, body, _ = _request_json("https://www.googleapis.com/drive/v3/about?fields=user", headers=headers)
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


def check_huggingface() -> CheckResult:
    key_name, token = _pick_env("HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN")
    if not token:
        return CheckResult(
            name="huggingface",
            status="needs_configuration",
            detail={
                "reason": "missing_token",
                "accepted_env_keys": ["HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN"],
            },
        )

    headers = {"Authorization": f"Bearer {token}"}
    status, body, _ = _request_json("https://huggingface.co/api/whoami-v2", headers=headers)
    if status != 200:
        return CheckResult(
            name="huggingface",
            status="error",
            detail={
                "reason": "auth_failed",
                "http_status": status,
                "token_env": key_name,
                "response": body,
            },
        )

    return CheckResult(
        name="huggingface",
        status="ok",
        detail={
            "token_env": key_name,
            "user": body.get("name") or body.get("fullname"),
            "email": body.get("email"),
        },
    )


def check_airtable(base_id: str = "") -> CheckResult:
    key_name, token = _pick_env("AIRTABLE_TOKEN", "AIRTABLE_API_KEY", "AIRTABLE_PAT")
    if not token:
        return CheckResult(
            name="airtable",
            status="needs_configuration",
            detail={
                "reason": "missing_token",
                "accepted_env_keys": ["AIRTABLE_TOKEN", "AIRTABLE_API_KEY", "AIRTABLE_PAT"],
            },
        )

    headers = {"Authorization": f"Bearer {token}"}
    clean_base = base_id.strip()
    if clean_base:
        url = f"https://api.airtable.com/v0/meta/bases/{urllib.parse.quote(clean_base, safe='')}/tables"
        status, body, _ = _request_json(url, headers=headers)
        if status != 200:
            return CheckResult(
                name="airtable",
                status="error",
                detail={
                    "reason": "base_access_failed",
                    "http_status": status,
                    "token_env": key_name,
                    "base_id": clean_base,
                    "response": body,
                },
            )
        tables = body.get("tables", [])
        return CheckResult(
            name="airtable",
            status="ok",
            detail={
                "token_env": key_name,
                "base_id": clean_base,
                "table_count": len(tables),
            },
        )

    status, body, _ = _request_json("https://api.airtable.com/v0/meta/whoami", headers=headers)
    if status == 200:
        return CheckResult(
            name="airtable",
            status="ok",
            detail={
                "token_env": key_name,
                "user_id": body.get("id"),
                "workspace_count": len(body.get("scopes", [])),
            },
        )
    if status in (401, 403):
        return CheckResult(
            name="airtable",
            status="error",
            detail={
                "reason": "auth_failed",
                "http_status": status,
                "token_env": key_name,
                "response": body,
            },
        )
    return CheckResult(
        name="airtable",
        status="needs_configuration",
        detail={
            "reason": "base_id_recommended",
            "token_env": key_name,
            "hint": "Pass --airtable-base-id or set AIRTABLE_BASE_ID for deterministic access checks.",
            "http_status": status,
            "response": body,
        },
    )


def check_zapier(webhook_url: str = "") -> CheckResult:
    candidate = webhook_url.strip() or os.getenv("ZAPIER_WEBHOOK_URL", "").strip()
    if not candidate:
        return CheckResult(
            name="zapier",
            status="needs_configuration",
            detail={
                "reason": "missing_webhook",
                "accepted_env_keys": ["ZAPIER_WEBHOOK_URL"],
            },
        )

    status, body, error = _request_json(candidate, headers={}, timeout=20)
    reachable_codes = {200, 202, 301, 302, 400, 401, 403, 405}
    if status in reachable_codes:
        return CheckResult(
            name="zapier",
            status="ok",
            detail={
                "webhook_url": candidate,
                "http_status": status,
                "note": "Reachable webhook endpoint.",
            },
        )
    return CheckResult(
        name="zapier",
        status="error",
        detail={
            "reason": "webhook_unreachable",
            "http_status": status,
            "error": error,
            "webhook_url": candidate,
            "response": body,
        },
    )


def check_telegram(chat_id: str = "") -> CheckResult:
    token_key, token = _pick_env("TELEGRAM_BOT_TOKEN", "SCBE_TELEGRAM_BOT_TOKEN")
    if not token:
        return CheckResult(
            name="telegram",
            status="needs_configuration",
            detail={
                "reason": "missing_bot_token",
                "accepted_env_keys": ["TELEGRAM_BOT_TOKEN", "SCBE_TELEGRAM_BOT_TOKEN"],
            },
        )

    status, body, error = _request_json(f"https://api.telegram.org/bot{token}/getMe")
    if status != 200 or not isinstance(body, dict) or not body.get("ok"):
        return CheckResult(
            name="telegram",
            status="error",
            detail={
                "reason": "auth_failed",
                "http_status": status,
                "token_env": token_key,
                "error": error,
                "response": body,
            },
        )

    result = body.get("result") if isinstance(body, dict) else {}
    detail: dict[str, Any] = {
        "token_env": token_key,
        "bot_id": (result or {}).get("id"),
        "bot_username": (result or {}).get("username"),
        "can_join_groups": (result or {}).get("can_join_groups"),
    }

    chat_key, env_chat = _pick_env("TELEGRAM_CHAT_ID", "SCBE_TELEGRAM_CHAT_ID")
    resolved_chat_id = chat_id.strip() or env_chat
    if resolved_chat_id:
        if not resolved_chat_id.lstrip("-").isdigit():
            return CheckResult(
                name="telegram",
                status="error",
                detail={
                    **detail,
                    "reason": "chat_id_must_be_numeric",
                    "chat_id_source": "argument" if chat_id.strip() else chat_key,
                    "chat_id": resolved_chat_id,
                },
            )

        chat_status, chat_body, chat_error = _request_json(
            "https://api.telegram.org/bot{token}/getChat?chat_id={chat_id}".format(
                token=token,
                chat_id=urllib.parse.quote(resolved_chat_id, safe="-"),
            )
        )
        if chat_status != 200 or not isinstance(chat_body, dict) or not chat_body.get("ok"):
            return CheckResult(
                name="telegram",
                status="needs_configuration",
                detail={
                    **detail,
                    "reason": "chat_not_accessible",
                    "chat_id_source": "argument" if chat_id.strip() else chat_key,
                    "chat_id": resolved_chat_id,
                    "http_status": chat_status,
                    "error": chat_error,
                    "response": chat_body,
                },
            )

        chat_result = chat_body.get("result") if isinstance(chat_body, dict) else {}
        detail["chat_id_source"] = "argument" if chat_id.strip() else chat_key
        detail["chat_id"] = resolved_chat_id
        detail["chat_title"] = (chat_result or {}).get("title")
        detail["chat_type"] = (chat_result or {}).get("type")

    return CheckResult(name="telegram", status="ok", detail=detail)


def check_n8n(base_url: str = "") -> CheckResult:
    candidate = _normalize_base_url(base_url or os.getenv("N8N_BASE_URL", ""))
    if not candidate:
        return CheckResult(
            name="n8n",
            status="needs_configuration",
            detail={
                "reason": "missing_base_url",
                "accepted_env_keys": ["N8N_BASE_URL"],
            },
        )

    status, body, error = _request_json(f"{candidate}/healthz", headers={}, timeout=15)
    if status != 200:
        status, body, error = _request_json(candidate, headers={}, timeout=15)
    if status == 200:
        return CheckResult(
            name="n8n",
            status="ok",
            detail={
                "base_url": candidate,
                "http_status": status,
                "health": body,
            },
        )
    return CheckResult(
        name="n8n",
        status="error",
        detail={
            "reason": "service_unreachable",
            "base_url": candidate,
            "http_status": status,
            "error": error,
            "response": body,
        },
    )


def _pick_bridge_key(explicit: str) -> tuple[str, str]:
    if explicit.strip():
        return "argument", explicit.strip()
    return _pick_env("SCBE_API_KEY", "N8N_API_KEY", "SCBE_BROWSER_API_KEY")


def check_bridge(base_url: str = "", api_key: str = "") -> CheckResult:
    candidate = _normalize_base_url(base_url or os.getenv("SCBE_BRIDGE_URL", ""))
    if not candidate:
        return CheckResult(
            name="bridge",
            status="needs_configuration",
            detail={
                "reason": "missing_base_url",
                "accepted_env_keys": ["SCBE_BRIDGE_URL"],
            },
        )

    status_health, health_body, error_health = _request_json(f"{candidate}/health", headers={}, timeout=15)
    if status_health != 200:
        return CheckResult(
            name="bridge",
            status="error",
            detail={
                "reason": "health_failed",
                "base_url": candidate,
                "http_status": status_health,
                "error": error_health,
                "response": health_body,
            },
        )

    key_name, token = _pick_bridge_key(api_key)
    detail: dict[str, Any] = {
        "base_url": candidate,
        "health_status": status_health,
        "service": health_body.get("service"),
    }
    if not token:
        detail["integration_status"] = "skipped_missing_api_key"
        detail["accepted_env_keys"] = ["SCBE_API_KEY", "N8N_API_KEY", "SCBE_BROWSER_API_KEY"]
        return CheckResult(name="bridge", status="ok", detail=detail)

    headers = {"X-API-Key": token}
    status_int, int_body, error_int = _request_json(f"{candidate}/v1/integrations/status", headers=headers, timeout=15)
    if status_int != 200:
        return CheckResult(
            name="bridge",
            status="error",
            detail={
                **detail,
                "integration_status": "failed",
                "token_source": key_name,
                "http_status": status_int,
                "error": error_int,
                "response": int_body,
            },
        )
    detail["integration_status"] = "ok"
    detail["token_source"] = key_name
    detail["integrations"] = int_body
    return CheckResult(name="bridge", status="ok", detail=detail)


def check_playwright(base_url: str = "") -> CheckResult:
    candidate = _normalize_base_url(base_url or os.getenv("SCBE_BROWSER_URL", ""))
    if not candidate:
        return CheckResult(
            name="playwright",
            status="needs_configuration",
            detail={
                "reason": "missing_base_url",
                "accepted_env_keys": ["SCBE_BROWSER_URL"],
            },
        )

    status, body, error = _request_json(f"{candidate}/health", headers={}, timeout=15)
    if status != 200:
        return CheckResult(
            name="playwright",
            status="error",
            detail={
                "reason": "health_failed",
                "base_url": candidate,
                "http_status": status,
                "error": error,
                "response": body,
            },
        )
    return CheckResult(
        name="playwright",
        status="ok",
        detail={
            "base_url": candidate,
            "health_status": status,
            "health": body,
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run connector health checks.")
    parser.add_argument(
        "--checks",
        nargs="+",
        choices=VALID_CHECKS,
        default=["github", "notion", "drive"],
        help="Checks to run.",
    )
    parser.add_argument("--github-repo", default="issdandavis/SCBE-AETHERMOORE", help="Repository for GitHub route test.")
    parser.add_argument("--notion-page-id", default="", help="Optional Notion page id for read-access validation.")
    parser.add_argument(
        "--airtable-base-id",
        default=os.getenv("AIRTABLE_BASE_ID", ""),
        help="Optional Airtable base id for deterministic access check.",
    )
    parser.add_argument(
        "--zapier-webhook-url",
        default=os.getenv("ZAPIER_WEBHOOK_URL", ""),
        help="Optional Zapier webhook URL.",
    )
    parser.add_argument(
        "--telegram-chat-id",
        default=os.getenv("TELEGRAM_CHAT_ID", os.getenv("SCBE_TELEGRAM_CHAT_ID", "")),
        help="Optional Telegram chat ID to validate post-auth bot access.",
    )
    parser.add_argument(
        "--n8n-base-url",
        default=os.getenv("N8N_BASE_URL", ""),
        help="n8n base URL (for example http://127.0.0.1:5680).",
    )
    parser.add_argument(
        "--bridge-base-url",
        default=os.getenv("SCBE_BRIDGE_URL", ""),
        help="Bridge base URL (for example http://127.0.0.1:8002).",
    )
    parser.add_argument(
        "--playwright-base-url",
        default=os.getenv("SCBE_BROWSER_URL", ""),
        help="Playwright browser agent URL (for example http://127.0.0.1:8012).",
    )
    parser.add_argument(
        "--bridge-api-key",
        default="",
        help="Optional bridge API key; falls back to SCBE_API_KEY / N8N_API_KEY.",
    )
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
    if "huggingface" in args.checks:
        checks.append(check_huggingface())
    if "airtable" in args.checks:
        checks.append(check_airtable(base_id=args.airtable_base_id))
    if "zapier" in args.checks:
        checks.append(check_zapier(webhook_url=args.zapier_webhook_url))
    if "telegram" in args.checks:
        checks.append(check_telegram(chat_id=args.telegram_chat_id))
    if "n8n" in args.checks:
        checks.append(check_n8n(base_url=args.n8n_base_url))
    if "bridge" in args.checks:
        checks.append(check_bridge(base_url=args.bridge_base_url, api_key=args.bridge_api_key))
    if "playwright" in args.checks:
        checks.append(check_playwright(base_url=args.playwright_base_url))

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "strict_mode": args.strict,
        "checks": [{"name": c.name, "status": c.status, "detail": c.detail} for c in checks],
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
