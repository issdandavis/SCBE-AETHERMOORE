"""SCBE Email Service — SMTP outbound and contact form handler.

Sends emails via Proton Mail SMTP submission for website contact forms,
notifications, and agentic triage alerts.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Optional


ENV_FILE = Path(__file__).resolve().parent.parent.parent / "config" / "connector_oauth" / ".env.connector.oauth"


def _load_env():
    """Lazy-load env file if present."""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def get_smtp_config() -> dict:
    """Return SMTP configuration from environment."""
    _load_env()
    return {
        "host": os.environ.get("PROTONMAIL_SMTP_HOST", "smtp.protonmail.ch"),
        "port": int(os.environ.get("PROTONMAIL_SMTP_PORT", "587")),
        "user": os.environ.get("PROTONMAIL_SMTP_USER", ""),
        "password": os.environ.get("PROTONMAIL_SMTP_TOKEN", ""),
        "starttls": os.environ.get("PROTONMAIL_SMTP_STARTTLS", "true").lower() == "true",
    }


def send_email(
    to: str,
    subject: str,
    body: str,
    from_addr: Optional[str] = None,
    reply_to: Optional[str] = None,
    html_body: Optional[str] = None,
) -> dict:
    """Send an email via Proton SMTP.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain text body.
        from_addr: Sender address (defaults to SMTP user).
        reply_to: Reply-To header for contact forms.
        html_body: Optional HTML alternative.

    Returns:
        {"ok": True, "message_id": str} or {"ok": False, "error": str}
    """
    cfg = get_smtp_config()
    if not cfg["user"] or not cfg["password"]:
        return {"ok": False, "error": "SMTP credentials not configured"}

    sender = from_addr or cfg["user"]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as server:
            if cfg["starttls"]:
                server.starttls(context=context)
            server.login(cfg["user"], cfg["password"])
            server.send_message(msg)
        return {"ok": True, "message_id": msg["Message-ID"] or "sent"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_contact_notification(
    name: str,
    email: str,
    subject: str,
    message: str,
    page: Optional[str] = None,
) -> dict:
    """Send a contact form submission to the site owner.

    Formats the email and triggers notification to the admin inbox.
    """
    cfg = get_smtp_config()
    owner = cfg["user"]

    body_lines = [
        f"New contact form submission from aethermoore.com",
        f"",
        f"Name:    {name}",
        f"Email:   {email}",
        f"Subject: {subject}",
        f"Page:    {page or 'contact.html'}",
        f"",
        f"Message:",
        f"{message}",
        f"",
        f"---",
        f"This email was sent by the SCBE website contact form.",
        f"To reply, use Reply-To: {email}",
    ]

    html_body = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;color:#333;">
<h2>New contact form submission</h2>
<table style="border-collapse:collapse;">
<tr><td style="padding:8px;border:1px solid #ddd;"><strong>Name</strong></td><td style="padding:8px;border:1px solid #ddd;">{name}</td></tr>
<tr><td style="padding:8px;border:1px solid #ddd;"><strong>Email</strong></td><td style="padding:8px;border:1px solid #ddd;">{email}</td></tr>
<tr><td style="padding:8px;border:1px solid #ddd;"><strong>Subject</strong></td><td style="padding:8px;border:1px solid #ddd;">{subject}</td></tr>
<tr><td style="padding:8px;border:1px solid #ddd;"><strong>Page</strong></td><td style="padding:8px;border:1px solid #ddd;">{page or 'contact.html'}</td></tr>
</table>
<h3>Message</h3>
<div style="background:#f5f5f5;padding:16px;border-radius:8px;">{message.replace(chr(10), '<br>')}</div>
<p><em>Sent by SCBE website contact form. Reply-To: {email}</em></p>
</body></html>"""

    return send_email(
        to=owner,
        subject=f"[SCBE Contact] {subject}",
        body="\n".join(body_lines),
        reply_to=email,
        html_body=html_body,
    )


if __name__ == "__main__":
    # Quick test
    result = send_email(
        to="issac@aethermoorgames.com",
        subject="SCBE Email Service Test",
        body="This is a test email from the SCBE email service module.",
    )
    print(result)
