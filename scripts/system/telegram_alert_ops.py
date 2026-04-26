#!/usr/bin/env python3
"""Telegram alert channel operations for SCBE.

This is a lightweight Bot API wrapper for operator alerts. It keeps tokens in
environment variables, writes only redacted receipts, and avoids parse-mode
formatting by default so routine alerts cannot fail on Markdown escaping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from pathlib import Path
from urllib import error, parse, request


ROOT = Path(__file__).resolve().parents[2]
RECEIPT_DIR = ROOT / "artifacts" / "telegram_alerts"
STATE_PATH = RECEIPT_DIR / "inbound_state.json"

TOKEN_ENV_CANDIDATES = (
    "TELEGRAM_BOT_TOKEN",
    "SCBE_TELEGRAM_BOT_TOKEN",
    "SCBE_TELEGRAM_BOT_TOKEN_ORCHESTRATOR",
)
CHAT_ENV_CANDIDATES = ("TELEGRAM_CHAT_ID", "TELEGRAM_OWNER_ID")
HELP_TEXT = (
    "SCBE Telegram bridge commands:\n"
    "/ping - verify the terminal bridge is listening\n"
    "/task <request> - queue a Codex task packet\n"
    "/act <request> - queue a Codex task packet\n"
    "/help - show this help\n\n"
    "Non-command text from the owner chat is treated as /task text. No raw shell commands are executed."
)


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


def load_state() -> dict[str, object]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(state: dict[str, object]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def get_update_message(update: dict[str, object]) -> dict[str, object]:
    for key in ("message", "edited_message", "channel_post"):
        value = update.get(key)
        if isinstance(value, dict):
            return value
    return {}


def chat_id_from_message(message: dict[str, object]) -> str:
    chat = message.get("chat")
    if not isinstance(chat, dict):
        return ""
    value = chat.get("id", "")
    return str(value)


def is_authorized_message(message: dict[str, object], allowed_chat_id: str) -> bool:
    return bool(allowed_chat_id and chat_id_from_message(message) == str(allowed_chat_id))


def classify_inbound_text(text: str) -> dict[str, str]:
    clean = text.strip()
    lower = clean.lower()
    if not clean:
        return {"kind": "ignore", "summary": "", "reply": ""}
    if lower.startswith("/ping"):
        return {"kind": "ping", "summary": "Telegram ping", "reply": "SCBE terminal bridge is listening."}
    if lower.startswith("/help"):
        return {"kind": "help", "summary": "Telegram help requested", "reply": HELP_TEXT}
    for prefix in ("/task", "/act", "/codex"):
        if lower == prefix or lower.startswith(prefix + " "):
            summary = clean[len(prefix) :].strip()
            if not summary:
                return {
                    "kind": "help",
                    "summary": "Empty Telegram task command",
                    "reply": f"Send `{prefix} <request>`.",
                }
            return {"kind": "task_request", "summary": summary, "reply": ""}
    if clean.startswith("/"):
        return {"kind": "help", "summary": f"Unknown Telegram command: {clean[:80]}", "reply": HELP_TEXT}
    return {"kind": "task_request", "summary": clean, "reply": ""}


def emit_ops_packet(summary: str, update_id: int, *, dry_run: bool = False) -> dict[str, object]:
    packet_slug = hashlib.sha256(f"telegram:{update_id}:{summary}".encode("utf-8")).hexdigest()[:10]
    task_id = f"telegram-inbound-{update_id}-{packet_slug}"
    if dry_run:
        return {"ok": True, "dry_run": True, "task_id": task_id}

    sys.path.insert(0, str(ROOT / "scripts" / "system"))
    import ops_control  # type: ignore

    args = SimpleNamespace(
        from_agent="telegram",
        to="codex",
        intent="task_request",
        status="needs_triage",
        summary=summary[:1200],
        artifacts="",
        next_action="Codex/Clawbot should inspect the packet and decide the next bounded action.",
        task_id=task_id,
        risk="low",
        where="telegram",
        why="Owner requested action through Telegram bridge.",
        how="scripts/system/telegram_alert_ops.py poll",
        session_id="telegram-terminal-bridge",
        codename="Telegram-Bridge",
    )
    packet = ops_control.build_packet(args)
    delivery = ops_control.deliver_to_all(packet)
    successes = sum(1 for item in delivery.values() if item.get("ok"))
    from scripts.system.message_triplet_ledger import append_record

    triplet_record = append_record(
        ROOT / "artifacts" / "message_bus" / "telegram_triplet_ledger.jsonl",
        {
            "source": "telegram",
            "update_id": update_id,
            "task_id": task_id,
            "packet_id": packet.get("packet_id"),
            "summary": summary[:1200],
            "status": "needs_triage",
        },
        ack_payload={"delivery_successes": successes, "packet_id": packet.get("packet_id")},
        channel="telegram",
    )
    return {
        "ok": successes >= 3,
        "packet_id": packet.get("packet_id"),
        "task_id": task_id,
        "triplet_hash": triplet_record["triplet"]["current_hash"],
        "delivery_successes": successes,
        "delivery": delivery,
    }


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


def fetch_updates(client: TelegramClient, *, offset: int = 0, limit: int = 10, timeout: int = 0) -> dict[str, object]:
    payload: dict[str, object] = {
        "limit": limit,
        "timeout": timeout,
        "allowed_updates": ["message", "edited_message"],
    }
    if offset:
        payload["offset"] = offset
    return client.call("getUpdates", payload)


def reply_to_chat(client: TelegramClient, chat_id: str, text: str) -> dict[str, object]:
    return client.call(
        "sendMessage",
        {"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": True},
    )


def process_update(
    client: TelegramClient,
    update: dict[str, object],
    allowed_chat_id: str,
    *,
    dry_run: bool = False,
    no_reply: bool = False,
    beep: bool = False,
) -> dict[str, object]:
    update_id = int(update.get("update_id", 0) or 0)
    message = get_update_message(update)
    chat_id = chat_id_from_message(message)
    text = str(message.get("text") or "").strip()
    authorized = is_authorized_message(message, allowed_chat_id)
    result: dict[str, object] = {
        "update_id": update_id,
        "chat_id_match": authorized,
        "text_present": bool(text),
        "processed": False,
    }
    if not authorized:
        result["reason"] = "unauthorized_chat"
        return result
    command = classify_inbound_text(text)
    result["kind"] = command["kind"]
    result["summary"] = command["summary"][:200]
    if command["kind"] == "ignore":
        result["reason"] = "empty_text"
        return result
    if beep:
        print("\a", end="")
    print(f"TELEGRAM ALERT update={update_id} kind={command['kind']} summary={command['summary'][:160]}")
    if command["kind"] == "task_request":
        packet = emit_ops_packet(command["summary"], update_id, dry_run=dry_run)
        result["packet"] = packet
        reply = (
            f"Queued SCBE task packet.\npacket_id: {packet.get('packet_id', 'dry-run')}\n"
            f"task_id: {packet.get('task_id')}"
        )
    else:
        reply = command["reply"]
    if reply and not no_reply:
        response = reply_to_chat(client, chat_id, reply)
        result["reply_ok"] = bool(response.get("ok"))
        result["reply_message_id"] = (
            (response.get("result") or {}).get("message_id") if isinstance(response.get("result"), dict) else None
        )
    result["processed"] = True
    return result


def poll_once(args: argparse.Namespace) -> dict[str, object]:
    client, chat_id, token_env, chat_env = build_client(args)
    if not chat_id:
        raise RuntimeError("Missing owner chat id. Set TELEGRAM_OWNER_ID/TELEGRAM_CHAT_ID or pass --chat-id.")
    state = load_state() if not args.no_state else {}
    offset = args.offset or int(state.get("next_offset", 0) or 0)
    response = fetch_updates(client, offset=offset, limit=args.limit, timeout=args.timeout)
    updates = response.get("result") if isinstance(response.get("result"), list) else []
    processed: list[dict[str, object]] = []
    max_update_id = offset - 1 if offset else 0
    for update in updates:
        if not isinstance(update, dict):
            continue
        update_id = int(update.get("update_id", 0) or 0)
        max_update_id = max(max_update_id, update_id)
        processed.append(
            process_update(
                client,
                update,
                chat_id,
                dry_run=args.dry_run,
                no_reply=args.no_reply,
                beep=args.beep,
            )
        )
    next_offset = max_update_id + 1 if max_update_id else offset
    if not args.no_state and response.get("ok"):
        save_state({"next_offset": next_offset, "updated_at": now_iso(), "token_env": token_env, "chat_env": chat_env})
    return {
        "schema_version": "scbe_telegram_terminal_bridge_poll_v1",
        "ok": bool(response.get("ok")),
        "checked_at": now_iso(),
        "token_env": token_env,
        "chat_env": chat_env,
        "offset": offset,
        "next_offset": next_offset,
        "update_count": len(updates),
        "processed_count": sum(1 for item in processed if item.get("processed")),
        "processed": processed,
    }


def cmd_poll(args: argparse.Namespace) -> int:
    summary = poll_once(args)
    if args.write_receipt:
        summary["receipt_path"] = str(write_receipt("poll", summary))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("ok") else 1


def cmd_watch(args: argparse.Namespace) -> int:
    print("SCBE Telegram terminal bridge watching. Ctrl+C to stop.")
    cycles = 0
    while True:
        cycles += 1
        summary = poll_once(args)
        if args.write_receipt and summary.get("processed_count"):
            write_receipt("poll", summary)
        if args.verbose or summary.get("processed_count"):
            print(json.dumps(summary, indent=2, sort_keys=True))
        if args.max_cycles and cycles >= args.max_cycles:
            return 0
        time.sleep(max(1, args.interval))


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

    poll = sub.add_parser("poll", help="Poll inbound Telegram messages once and queue safe SCBE packets.")
    poll.add_argument("--limit", type=int, default=10)
    poll.add_argument("--timeout", type=int, default=0)
    poll.add_argument("--offset", type=int, default=0)
    poll.add_argument("--no-state", action="store_true")
    poll.add_argument("--dry-run", action="store_true")
    poll.add_argument("--no-reply", action="store_true")
    poll.add_argument("--beep", action="store_true")
    poll.add_argument("--write-receipt", action="store_true")
    poll.set_defaults(func=cmd_poll)

    watch = sub.add_parser("watch", help="Continuously poll Telegram and queue safe SCBE packets.")
    watch.add_argument("--limit", type=int, default=10)
    watch.add_argument("--timeout", type=int, default=15)
    watch.add_argument("--offset", type=int, default=0)
    watch.add_argument("--no-state", action="store_true")
    watch.add_argument("--dry-run", action="store_true")
    watch.add_argument("--no-reply", action="store_true")
    watch.add_argument("--beep", action="store_true")
    watch.add_argument("--write-receipt", action="store_true")
    watch.add_argument("--interval", type=int, default=3)
    watch.add_argument("--verbose", action="store_true")
    watch.add_argument("--max-cycles", type=int, default=0, help="Stop after N cycles; 0 means run until interrupted.")
    watch.set_defaults(func=cmd_watch)

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
