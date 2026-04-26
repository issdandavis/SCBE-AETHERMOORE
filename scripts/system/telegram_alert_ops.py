#!/usr/bin/env python3
"""Telegram alert channel operations for SCBE.

This is a lightweight Bot API wrapper for operator alerts. It keeps tokens in
environment variables, writes only redacted receipts, and avoids parse-mode
formatting by default so routine alerts cannot fail on Markdown escaping.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, parse, request


ROOT = Path(__file__).resolve().parents[2]
RECEIPT_DIR = ROOT / "artifacts" / "telegram_alerts"

TOKEN_ENV_CANDIDATES = (
    "TELEGRAM_BOT_TOKEN",
    "SCBE_TELEGRAM_BOT_TOKEN",
    "SCBE_TELEGRAM_BOT_TOKEN_ORCHESTRATOR",
)
CHAT_ENV_CANDIDATES = ("TELEGRAM_CHAT_ID", "TELEGRAM_OWNER_ID")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def first_env(names: tuple[str, ...]) -> tuple[str, str]:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return name, value
    return "", ""


def redacted_token(token: str) -> str:
    if not token:
        return ""
    prefix = token.split(":", 1)[0]
    return f"{prefix}:***"


class TelegramClient:
    def __init__(self, token: str) -> None:
        if not token:
            raise RuntimeError("Missing Telegram bot token.")
        self.token = token

    def call(self, method: str, payload: dict[str, object] | None = None) -> dict[str, object]:
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        data = None
        headers = {}
        http_method = "GET"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
            http_method = "POST"
        req = request.Request(url, data=data, headers=headers, method=http_method)
        try:
            with request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = {"ok": False, "description": body}
            parsed["http_status"] = exc.code
            return parsed


def write_receipt(kind: str, payload: dict[str, object]) -> Path:
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = RECEIPT_DIR / f"{now_iso().replace(':', '').replace('-', '')}_{kind}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def build_client(args: argparse.Namespace) -> tuple[TelegramClient, str, str, str]:
    if args.load_dotenv:
        load_dotenv(ROOT / ".env")
    token_env, token = first_env(TOKEN_ENV_CANDIDATES)
    chat_env, chat_id = first_env(CHAT_ENV_CANDIDATES)
    if args.token_env:
        token_env = args.token_env
        token = os.getenv(args.token_env, "").strip()
    if args.chat_id:
        chat_env = "cli"
        chat_id = args.chat_id.strip()
    return TelegramClient(token), chat_id, token_env, chat_env


def cmd_doctor(args: argparse.Namespace) -> int:
    client, chat_id, token_env, chat_env = build_client(args)
    me = client.call("getMe")
    webhook = client.call("getWebhookInfo")
    ok = bool(me.get("ok"))
    result = {
        "schema_version": "scbe_telegram_alert_doctor_v1",
        "ok": ok,
        "checked_at": now_iso(),
        "token_env": token_env,
        "token_redacted": redacted_token(client.token),
        "chat_env": chat_env,
        "chat_present": bool(chat_id),
        "bot_username": (me.get("result") or {}).get("username") if isinstance(me.get("result"), dict) else None,
        "webhook_url_present": bool((webhook.get("result") or {}).get("url"))
        if isinstance(webhook.get("result"), dict)
        else False,
        "webhook_pending_update_count": (webhook.get("result") or {}).get("pending_update_count")
        if isinstance(webhook.get("result"), dict)
        else None,
    }
    if args.write_receipt:
        result["receipt_path"] = str(write_receipt("doctor", result))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if ok else 1


def cmd_send(args: argparse.Namespace) -> int:
    client, chat_id, token_env, chat_env = build_client(args)
    if not chat_id:
        raise RuntimeError("Missing Telegram chat id. Set TELEGRAM_CHAT_ID/TELEGRAM_OWNER_ID or pass --chat-id.")
    text = args.message
    if args.message_file:
        text = Path(args.message_file).read_text(encoding="utf-8")
    if not text.strip():
        raise RuntimeError("Message is empty.")
    payload: dict[str, object] = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": bool(args.disable_web_page_preview),
    }
    if args.protect_content:
        payload["protect_content"] = True
    response = client.call("sendMessage", payload)
    result_obj = response.get("result") if isinstance(response.get("result"), dict) else {}
    receipt = {
        "schema_version": "scbe_telegram_alert_receipt_v1",
        "ok": bool(response.get("ok")),
        "sent_at": now_iso(),
        "token_env": token_env,
        "chat_env": chat_env,
        "message_id": result_obj.get("message_id"),
        "chat_type": (result_obj.get("chat") or {}).get("type") if isinstance(result_obj.get("chat"), dict) else None,
        "description": response.get("description", ""),
    }
    if args.write_receipt:
        receipt["receipt_path"] = str(write_receipt("send", receipt))
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if response.get("ok") else 1


def cmd_updates(args: argparse.Namespace) -> int:
    client, _chat_id, token_env, _chat_env = build_client(args)
    params = {"limit": args.limit, "timeout": 0}
    if args.offset:
        params["offset"] = args.offset
    query = parse.urlencode(params)
    # getUpdates is GET-friendly, but the generic client intentionally keeps
    # API calls simple; call directly here to support query params.
    with request.urlopen(f"https://api.telegram.org/bot{client.token}/getUpdates?{query}", timeout=20) as resp:
        response = json.loads(resp.read().decode("utf-8"))
    updates = response.get("result") or []
    summary = {
        "schema_version": "scbe_telegram_updates_summary_v1",
        "ok": bool(response.get("ok")),
        "checked_at": now_iso(),
        "token_env": token_env,
        "update_count": len(updates),
        "latest_update_id": updates[-1].get("update_id") if updates else None,
    }
    if args.write_receipt:
        summary["receipt_path"] = str(write_receipt("updates", summary))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if response.get("ok") else 1


def cmd_webhook_info(args: argparse.Namespace) -> int:
    client, _chat_id, token_env, _chat_env = build_client(args)
    response = client.call("getWebhookInfo")
    info = response.get("result") if isinstance(response.get("result"), dict) else {}
    summary = {
        "schema_version": "scbe_telegram_webhook_info_v1",
        "ok": bool(response.get("ok")),
        "checked_at": now_iso(),
        "token_env": token_env,
        "url_present": bool(info.get("url")),
        "pending_update_count": info.get("pending_update_count"),
        "last_error_date": info.get("last_error_date"),
        "last_error_message": info.get("last_error_message"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if response.get("ok") else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Operate the SCBE Telegram alert channel.")
    parser.add_argument("--load-dotenv", action="store_true", help="Load repo-local .env before reading env vars.")
    parser.add_argument("--token-env", default="", help="Override token environment variable name.")
    parser.add_argument("--chat-id", default="", help="Override chat id for send operations.")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Verify bot identity and webhook state.")
    doctor.add_argument("--write-receipt", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    send = sub.add_parser("send", help="Send an operator alert.")
    send.add_argument("--message", default="")
    send.add_argument("--message-file", default="")
    send.add_argument("--disable-web-page-preview", action="store_true", default=True)
    send.add_argument("--protect-content", action="store_true")
    send.add_argument("--write-receipt", action="store_true")
    send.set_defaults(func=cmd_send)

    updates = sub.add_parser("updates", help="Summarize inbound update queue.")
    updates.add_argument("--limit", type=int, default=5)
    updates.add_argument("--offset", type=int, default=0)
    updates.add_argument("--write-receipt", action="store_true")
    updates.set_defaults(func=cmd_updates)

    webhook = sub.add_parser("webhook-info", help="Summarize Telegram webhook state.")
    webhook.set_defaults(func=cmd_webhook_info)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
