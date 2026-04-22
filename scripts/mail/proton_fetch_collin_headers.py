"""Fetch just Message-ID / In-Reply-To / References / Subject / Date from Collin messages today."""
from __future__ import annotations

import email
import email.policy
import imaplib
import os
import ssl
from email.message import EmailMessage

from dotenv import load_dotenv
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
load_dotenv(REPO / ".env")

HOST = "127.0.0.1"
PORT = 1143
USER = os.environ["PM_USER"]
PW = os.environ["PM_PW"]


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
        typ, data = m.search(
            None, "SINCE", "20-Apr-2026", "FROM", "collinhoag@hoagsandfamily.com"
        )
        ids = data[0].split()
        print(f"count={len(ids)}")
        for num in ids:
            typ, msg_data = m.fetch(num, "(RFC822.HEADER)")
            if typ != "OK":
                continue
            raw = msg_data[0][1]
            msg: EmailMessage = email.message_from_bytes(raw, policy=email.policy.default)
            print("----")
            print(f"UID: {num.decode()}")
            print(f"DATE: {msg.get('Date', '')}")
            print(f"SUBJ: {msg.get('Subject', '')}")
            print(f"MSGID: {msg.get('Message-ID', '')}")
            print(f"IRT:   {msg.get('In-Reply-To', '')}")
            refs = msg.get("References", "")
            print(f"REFS:  {refs[:200]}{'...' if len(refs) > 200 else ''}")
            print(f"REFS_FULL_LEN: {len(refs)}")
    finally:
        _safe_logout(m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
