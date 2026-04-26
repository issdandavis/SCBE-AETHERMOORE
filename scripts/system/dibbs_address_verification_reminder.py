#!/usr/bin/env python3
"""Stage or send a DIBBS physical-address verification reminder.

This utility intentionally does not store personal phone numbers in tracked
files. It stages an email reminder by default and can optionally send a Twilio
SMS when credentials are supplied through environment variables.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import date
from pathlib import Path
from urllib import parse, request


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / "artifacts" / "proton_mail" / "dibbs"
DEFAULT_DRAFT = ARTIFACT_DIR / "dibbs_address_verification_reminder_20260427.md"
DEFAULT_TELEGRAM_MESSAGE = ROOT / "artifacts" / "telegram_alerts" / "dibbs_address_verification_reminder_20260427.txt"

DEFAULT_TO = "issdandavis7795@gmail.com"
DEFAULT_CC = "issac@aethermoorgames.com"
DEFAULT_SUBJECT = "DIBBS physical address verification postcard check"

REMINDER_BODY = """Check the mailbox for the DIBBS / DLA physical-address verification postcard.

State on file:
- Physical Address Verification Number requested: 2026-04-20 09:37:37 PM
- First postcard sent: 2026-04-21 12:00:00 AM
- Expected check date: 2026-04-27

If the postcard arrived:
1. Send Issac a photo or read the Physical Address Verification Number directly.
2. Do not post the code into public repos, shared chats, or public docs.
3. Issac enters the code in DIBBS and records only the status: code entered.

If it did not arrive:
1. Record status: not arrived.
2. Check again the next mail day before restarting registration.
"""

SMS_BODY = (
    "DIBBS reminder: please check the mailbox for Issac's DLA physical-address "
    "verification postcard. If it arrived, send/read the verification number "
    "privately. Do not post the code publicly."
)

TELEGRAM_BODY = """DIBBS reminder: check the physical-address verification postcard on Monday 2026-04-27.

If it arrived: send/read the verification number privately.
If it did not arrive: record status as not arrived and check again the next mail day.

Do not post the code in public docs, public repos, or public chats."""


def write_email_draft(path: Path, to_email: str, cc_email: str, subject: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"To: {to_email}\nSubject: {subject}\n"
    if cc_email:
        content += f"Cc: {cc_email}\n"
    content += f"\n{REMINDER_BODY}\n"
    path.write_text(content, encoding="utf-8")
    return path


def write_telegram_message(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TELEGRAM_BODY + "\n", encoding="utf-8")
    return path


def send_twilio_sms(to_number: str, body: str) -> dict[str, object]:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    if not (account_sid and auth_token and from_number):
        raise RuntimeError(
            "Twilio SMS requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER."
        )

    endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{parse.quote(account_sid)}/Messages.json"
    payload = parse.urlencode({"To": to_number, "From": from_number, "Body": body}).encode("utf-8")
    token = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("ascii")
    req = request.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    parsed = json.loads(raw)
    return {"sid": parsed.get("sid"), "status": parsed.get("status"), "to": parsed.get("to")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage or send a DIBBS postcard reminder.")
    parser.add_argument("--write-email-draft", action="store_true", help="Write the Proton Bridge draft file.")
    parser.add_argument("--write-telegram-message", action="store_true", help="Write a Telegram-safe message file.")
    parser.add_argument("--draft-path", default=str(DEFAULT_DRAFT), help="Output draft path.")
    parser.add_argument("--telegram-message-path", default=str(DEFAULT_TELEGRAM_MESSAGE), help="Output Telegram message path.")
    parser.add_argument("--to-email", default=DEFAULT_TO)
    parser.add_argument("--cc-email", default=DEFAULT_CC)
    parser.add_argument("--subject", default=DEFAULT_SUBJECT)
    parser.add_argument("--send-sms", action="store_true", help="Send SMS via Twilio environment credentials.")
    parser.add_argument("--sms-to-env", default="DIBBS_HELPER_PHONE", help="Env var holding the SMS recipient.")
    parser.add_argument("--today", default=str(date.today()), help="Override current date for dry checks.")
    args = parser.parse_args()

    actions: list[str] = []
    if args.write_email_draft:
        path = write_email_draft(Path(args.draft_path), args.to_email, args.cc_email, args.subject)
        actions.append(f"email_draft={path}")

    if args.write_telegram_message:
        path = write_telegram_message(Path(args.telegram_message_path))
        actions.append(f"telegram_message={path}")

    if args.send_sms:
        to_number = os.getenv(args.sms_to_env, "").strip()
        if not to_number:
            raise RuntimeError(f"Set {args.sms_to_env} in the environment before using --send-sms.")
        result = send_twilio_sms(to_number, SMS_BODY)
        actions.append(f"twilio_sms={json.dumps(result, sort_keys=True)}")

    if not actions:
        print("No mutation requested. Use --write-email-draft, --write-telegram-message, or --send-sms.")
        print(f"Default check date: 2026-04-27; today argument: {args.today}")
        print("SMS recipient should be supplied through DIBBS_HELPER_PHONE, not committed.")
        return 0

    for action in actions:
        print(action)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
