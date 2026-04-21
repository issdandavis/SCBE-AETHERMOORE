"""Send DRAFT_COVER_v2_CONTRACT_20260420.md as a threaded reply to Collin's 17:43 packet.

Attaches the full teaming_agreement_v2_draft.md contract.
"""
from __future__ import annotations

import email.policy
import mimetypes
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[2]
load_dotenv(REPO / ".env")

HOST = "127.0.0.1"
PORT = 1025
USER = os.environ["PM_USER"]
PW = os.environ["PM_PW"]
FROM_ADDR = os.environ.get("PM_FROM", "issdandavis@proton.me")
FROM_NAME = "Issac D Davis"

TO_ADDR = "collinhoag@hoagsandfamily.com"
TO_NAME = "Collin Hoag"

# Thread Collin's 2026-04-20 17:43 packet (new thread, keep his subject so Gmail groups it).
SUBJECT = "Re: MATHBAC TA1 \u2014 Signed teaming docs + strategy5.py [2026-04-20]"
IN_REPLY_TO = "<69e6c82b.050a0220.282da2.72d4@mx.google.com>"
REFERENCES = " ".join(
    [
        "<XuTKP13pR0Jtw0wQ4lN8wbpqrpB-Ewgt48YA1lnuOyLojHWQLT0ym7-g0KZGrpjNOB--Euy7YWBt2m7mPzlLgw==@protonmail.internalid>",
        IN_REPLY_TO,
    ]
)

DRAFT = REPO / "artifacts" / "proton_mail" / "collin_hoag" / "DRAFT_COVER_v2_CONTRACT_20260420.md"
CONTRACT = REPO / "docs" / "proposals" / "DARPA_MATHBAC" / "teaming_agreement_v2_draft.md"


def extract_body(md: str) -> str:
    """Strip YAML frontmatter block before the body."""
    if md.startswith("---\n"):
        end = md.find("\n---\n", 4)
        if end != -1:
            return md[end + 5 :].lstrip() + "\n"
    return md.strip() + "\n"


def main() -> int:
    body = extract_body(DRAFT.read_text(encoding="utf-8"))

    msg = EmailMessage(policy=email.policy.default)
    msg["From"] = f"{FROM_NAME} <{FROM_ADDR}>"
    msg["To"] = f"{TO_NAME} <{TO_ADDR}>"
    msg["Subject"] = SUBJECT
    msg["In-Reply-To"] = IN_REPLY_TO
    msg["References"] = REFERENCES
    msg.set_content(body)

    contract_bytes = CONTRACT.read_bytes()
    ctype, _ = mimetypes.guess_type(str(CONTRACT))
    maintype, subtype = (ctype.split("/", 1) if ctype else ("text", "markdown"))
    msg.add_attachment(
        contract_bytes,
        maintype=maintype,
        subtype=subtype,
        filename=CONTRACT.name,
    )

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with smtplib.SMTP(HOST, PORT, timeout=60) as s:
        s.ehlo()
        s.starttls(context=ctx)
        s.ehlo()
        s.login(USER, PW)
        s.send_message(msg)

    print(f"SENT: {SUBJECT}")
    print(f"  From:        {FROM_ADDR}")
    print(f"  To:          {TO_ADDR}")
    print(f"  In-Reply-To: {IN_REPLY_TO}")
    print(f"  Body chars:  {len(body)}")
    print(f"  Attachment:  {CONTRACT.name} ({len(contract_bytes):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
