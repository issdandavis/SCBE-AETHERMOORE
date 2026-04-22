"""Fetch full bodies of Collin's two most recent replies for context."""
from __future__ import annotations

import email
import email.policy
import imaplib
import os
import ssl

from dotenv import load_dotenv
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
load_dotenv(REPO / ".env")

HOST = "127.0.0.1"
PORT = 1143
USER = os.environ["PM_USER"]
PW = os.environ["PM_PW"]

TARGET_UIDS = [b"10749", b"10750"]


def _safe_logout(client: imaplib.IMAP4) -> None:
    try:
        client.logout()
    except imaplib.IMAP4.error:
        return


def main() -> int:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    m = imaplib.IMAP4(HOST, PORT)
    m.starttls(ssl_context=ctx)
    m.login(USER, PW)
    try:
        m.select("INBOX", readonly=True)
        for num in TARGET_UIDS:
            typ, msg_data = m.fetch(num, "(RFC822)")
            if typ != "OK":
                print(f"FAIL UID {num.decode()}")
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw, policy=email.policy.default)
            print("=" * 70)
            print(f"UID: {num.decode()}")
            print(f"DATE: {msg.get('Date', '')}")
            print(f"SUBJ: {msg.get('Subject', '')}")
            print(f"FROM: {msg.get('From', '')}")
            print("-" * 70)
            body = msg.get_body(preferencelist=("plain", "html"))
            if body is not None:
                content = body.get_content()
                out_path = REPO / "artifacts" / "proton_mail" / "collin_hoag" / f"reply_uid_{num.decode()}.txt"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(content, encoding="utf-8")
                print(f"WROTE: {out_path} ({len(content):,} chars)")
            print()
    finally:
        _safe_logout(m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
