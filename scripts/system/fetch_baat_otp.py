"""Fetch the latest BAAT/Okta one-time email code without dumping mail bodies."""

from __future__ import annotations

import datetime as dt
import email
import imaplib
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / "config" / "connector_oauth" / ".env.connector.oauth"


def load_env() -> None:
    if not ENV.exists():
        return
    for line in ENV.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def text_from_msg(msg: email.message.Message) -> str:
    parts: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() in {"text/plain", "text/html"}:
                payload = part.get_payload(decode=True)
                if payload:
                    parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="ignore"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            parts.append(payload.decode(msg.get_content_charset() or "utf-8", errors="ignore"))
    return "\n".join(parts)


def candidate_code(subject: str, body: str) -> str | None:
    blob = f"{subject}\n{body}"
    if not re.search(r"(DARPA|BAAT|Okta|one[- ]time|verification|verify|passcode|code)", blob, re.I):
        return None
    patterns = [
        r"(?:code|passcode|verification code|one[- ]time code)[^\d]{0,30}(\d{6,8})",
        r"\b(\d{6})\b",
        r"\b(\d{8})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, blob, re.I)
        if match:
            return match.group(1)
    return None


def scan_account(host: str, port: int, user: str, password: str, ssl: bool) -> str | None:
    client = imaplib.IMAP4_SSL(host, port) if ssl else imaplib.IMAP4(host, port)
    try:
        client.login(user, password)
        client.select("INBOX")
        since = (dt.date.today() - dt.timedelta(days=1)).strftime("%d-%b-%Y")
        status, data = client.search(None, f'(SINCE "{since}")')
        if status != "OK" or not data or not data[0]:
            return None
        ids = data[0].split()[-30:]
        for msg_id in reversed(ids):
            status, rows = client.fetch(msg_id, "(RFC822)")
            if status != "OK" or not rows or not rows[0]:
                continue
            msg = email.message_from_bytes(rows[0][1])
            subject = str(email.header.make_header(email.header.decode_header(msg.get("Subject", ""))))
            body = text_from_msg(msg)
            code = candidate_code(subject, body)
            if code:
                return code
        return None
    finally:
        try:
            client.logout()
        except Exception:
            pass


def main() -> int:
    load_env()
    accounts = []
    if os.environ.get("GMAIL_APP_PASSWORD"):
        accounts.append(("imap.gmail.com", 993, os.environ.get("GMAIL_USER", "issdandavis7795@gmail.com"), os.environ["GMAIL_APP_PASSWORD"], True))
    if os.environ.get("PROTONMAIL_BRIDGE_PASSWORD"):
        accounts.append(("127.0.0.1", 1143, os.environ.get("PROTONMAIL_USER", "issdandavis@proton.me"), os.environ["PROTONMAIL_BRIDGE_PASSWORD"], False))
    if os.environ.get("PROTON_BRIDGE_PASSWORD"):
        accounts.append(("127.0.0.1", int(os.environ.get("PROTON_BRIDGE_IMAP_PORT", "1143")), os.environ.get("PROTON_BRIDGE_USERNAME", ""), os.environ["PROTON_BRIDGE_PASSWORD"], False))

    for account in accounts:
        try:
            code = scan_account(*account)
            if code:
                print(code)
                return 0
        except Exception:
            continue
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
