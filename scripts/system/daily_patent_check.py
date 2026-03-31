"""Daily USPTO patent linkage check — zero cost, runs locally.

Usage:
    python scripts/system/daily_patent_check.py
    python scripts/system/daily_patent_check.py --check-email

Checks Patent Center status and optionally ProtonMail via Bridge IMAP.
"""

import argparse
import datetime
import json
import os
import sys

PATENT_INFO = {
    "application_number": "63/961,403",
    "filing_date": "2025-11-12",
    "customer_number": "228194",
    "form_submitted": "2026-03-26",
    "receipt_number": "75020326",
    "follow_up_date": "2026-04-02",
    "follow_up_phone": "888-786-0101",
    "follow_up_email": "HelpAAU@uspto.gov",
    "ebc_email": "ebc@uspto.gov",
    "agent": "Jessica Smith, Agent 81",
}


def check_patent_center():
    """Check if Patent Center shows the application (manual reminder)."""
    today = datetime.date.today()
    submitted = datetime.date(2026, 3, 26)
    follow_up = datetime.date(2026, 4, 2)
    days_since = (today - submitted).days
    days_until_followup = (follow_up - today).days

    print("=" * 60)
    print("USPTO PATENT LINKAGE — DAILY CHECK")
    print("=" * 60)
    print(f"  Application:    {PATENT_INFO['application_number']}")
    print(f"  Customer #:     {PATENT_INFO['customer_number']}")
    print(f"  Form submitted: {PATENT_INFO['form_submitted']} (receipt #{PATENT_INFO['receipt_number']})")
    print(f"  Days since:     {days_since}")
    print()

    if today < follow_up:
        print(f"  STATUS: Waiting. {days_until_followup} business days until follow-up date.")
        print(f"  ACTION: Check Patent Center — can you see the application?")
        print(f"          https://patentcenter.uspto.gov/")
    elif today == follow_up:
        print(f"  STATUS: FOLLOW-UP DAY.")
        print(f"  ACTION: If app is NOT visible in Patent Center, CALL NOW:")
        print(f"          {PATENT_INFO['follow_up_phone']} (Applications Assistance Unit)")
        print(f"          Reference: application {PATENT_INFO['application_number']}")
        print(f"          Receipt: #{PATENT_INFO['receipt_number']}")
    else:
        print(f"  STATUS: OVERDUE — {days_since - 5} days past follow-up window.")
        print(f"  ACTION: Call {PATENT_INFO['follow_up_phone']} immediately.")
        print(f"          Or email: {PATENT_INFO['follow_up_email']}")

    print()
    return days_since


def check_protonmail():
    """Check ProtonMail via Bridge IMAP for USPTO responses."""
    try:
        import imaplib
        import email

        bridge_host = "127.0.0.1"
        bridge_port = 1143
        username = os.environ.get("PROTONMAIL_USER", "issdandavis@proton.me")
        password = os.environ.get("PROTONMAIL_BRIDGE_PASSWORD", "")

        # Also load from connector env if available
        if not password:
            env_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "connector_oauth", ".env.connector.oauth")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f.read().splitlines():
                        if line.strip().startswith("PROTONMAIL_BRIDGE_PASSWORD="):
                            password = line.split("=", 1)[1].strip().strip("\"'")

        if not password:
            print("  EMAIL: No PROTONMAIL_BRIDGE_PASSWORD set. Skipping email check.")
            print("         Set it in your env or run: ! export PROTONMAIL_BRIDGE_PASSWORD=...")
            return

        mail = imaplib.IMAP4(bridge_host, bridge_port)
        mail.login(username, password)
        mail.select("INBOX")

        # Search for USPTO-related emails
        for search_term in ["FROM ebc@uspto.gov", "FROM HelpAAU@uspto.gov", "SUBJECT patent"]:
            _, msg_ids = mail.search(None, f'({search_term})')
            if msg_ids[0]:
                ids = msg_ids[0].split()
                print(f"  EMAIL: Found {len(ids)} messages matching '{search_term}'")
                # Show latest
                _, msg_data = mail.fetch(ids[-1], "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                print(f"         Latest: {msg['Subject']} from {msg['From']} on {msg['Date']}")

        mail.logout()
        print("  EMAIL: Check complete.")

    except ImportError:
        print("  EMAIL: imaplib available but connection failed. Is ProtonMail Bridge running?")
    except Exception as e:
        print(f"  EMAIL: Could not connect to ProtonMail Bridge — {e}")
        print("         Make sure Bridge is running on 127.0.0.1:1143")


def main():
    parser = argparse.ArgumentParser(description="Daily USPTO patent check")
    parser.add_argument("--check-email", action="store_true", help="Also check ProtonMail via Bridge")
    args = parser.parse_args()

    check_patent_center()

    if args.check_email:
        print("Checking ProtonMail via Bridge...")
        check_protonmail()

    print("Done. Run this daily until linkage is confirmed.")


if __name__ == "__main__":
    main()
