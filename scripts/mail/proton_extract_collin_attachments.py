"""Extract attachments from Collin's UID 10750 (hardened Annex A + DAVA IP assertion)."""
from __future__ import annotations

import email
import email.policy
import imaplib
import os
import ssl
import sys

from dotenv import load_dotenv
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
load_dotenv(REPO / ".env")

HOST = "127.0.0.1"
PORT = 1143
USER = os.environ["PM_USER"]
PW = os.environ["PM_PW"]

OUT_DIR = REPO / "docs" / "proposals" / "DARPA_MATHBAC" / "from_collin_20260421"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    m = imaplib.IMAP4(HOST, PORT)
    m.starttls(ssl_context=ctx)
    m.login(USER, PW)
    try:
        m.select("INBOX", readonly=True)
        typ, msg_data = m.fetch(b"10750", "(RFC822)")
        if typ != "OK":
            print("FAIL fetch 10750")
            return 1
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw, policy=email.policy.default)
        count = 0
        for part in msg.iter_attachments():
            filename = part.get_filename()
            if not filename:
                continue
            payload = part.get_payload(decode=True)
            out_path = OUT_DIR / filename
            out_path.write_bytes(payload)
            print(f"SAVED: {out_path} ({len(payload):,} bytes)")
            count += 1
        print(f"total attachments: {count}")
    finally:
        try:
            m.logout()
        except Exception as exc:
            print(f"logout failed: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
