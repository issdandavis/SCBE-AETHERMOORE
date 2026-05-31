"""Daily USPTO patent prosecution check — zero cost, runs locally.

Usage:
    python scripts/system/daily_patent_check.py
    python scripts/system/daily_patent_check.py --check-email

Checks the filed SCBE nonprovisional status reminders and optionally ProtonMail
via Bridge IMAP.
"""

import argparse
import datetime
import os

PATENT_INFO = {
    "application_number": "19/691,526",
    "application_number_digits": "19691526",
    "provisional_priority": "63/961,403",
    "filing_date": "2026-05-28",
    "receipt_datetime": "2026-05-28 10:54:51 PM Z ET",
    "patent_center_number": "76776451",
    "confirmation_number": "1177",
    "docket": "SCBE-2026-0001",
    "fees_paid": "$720.00",
    "receipt_path": (
        "docs/legal/filing-packet-scbe-2026-0001/04_FILED_RECEIPTS/"
        "USPTO_ELECTRONIC_PAYMENT_RECEIPT_APP_19-691526_2026-05-28.pdf"
    ),
    "follow_up_date": "2026-06-04",
    "follow_up_phone": "888-786-0101",
    "follow_up_email": "HelpAAU@uspto.gov",
    "ebc_email": "ebc@uspto.gov",
}


def check_patent_center():
    """Print manual reminders for Patent Center status checks."""
    today = datetime.date.today()
    submitted = datetime.date(2026, 5, 28)
    follow_up = datetime.date(2026, 6, 4)
    days_since = (today - submitted).days
    days_until_followup = (follow_up - today).days

    print("=" * 60)
    print("USPTO PATENT PROSECUTION — DAILY CHECK")
    print("=" * 60)
    print(f"  Application:    {PATENT_INFO['application_number']}")
    print(f"  Docket:         {PATENT_INFO['docket']}")
    print(f"  Provisional:    {PATENT_INFO['provisional_priority']}")
    print(f"  Filed:          {PATENT_INFO['receipt_datetime']}")
    print(f"  Patent Center:  {PATENT_INFO['patent_center_number']}")
    print(f"  Confirmation:   {PATENT_INFO['confirmation_number']}")
    print(f"  Fees paid:      {PATENT_INFO['fees_paid']}")
    print(f"  Days since:     {days_since}")
    print(f"  Receipt saved:  {PATENT_INFO['receipt_path']}")
    print()

    if today < follow_up:
        print(f"  STATUS: Waiting. {days_until_followup} business days until follow-up date.")
        print("  ACTION: Check Patent Center for the formal Filing Receipt and new IFW documents.")
        print(f"          https://patentcenter.uspto.gov/")
    elif today == follow_up:
        print(f"  STATUS: FOLLOW-UP DAY.")
        print("  ACTION: If the formal Filing Receipt or application record is NOT visible, call:")
        print(f"          {PATENT_INFO['follow_up_phone']} (Applications Assistance Unit)")
        print(f"          Reference: application {PATENT_INFO['application_number']}")
        print(f"          Confirmation: {PATENT_INFO['confirmation_number']}")
    else:
        print(f"  STATUS: FOLLOW-UP WINDOW PASSED — {days_since - 7} days past target.")
        print(f"  ACTION: Call {PATENT_INFO['follow_up_phone']} immediately.")
        print(f"          Or email: {PATENT_INFO['follow_up_email']}")

    print()
    print("  ODP MONITOR:")
    print("    Set USPTO_ODP_API_KEY, then run:")
    print(f"    python scripts/system/uspto_prosecution_monitor.py --app {PATENT_INFO['application_number_digits']}")

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

        # Search for USPTO-related emails.
        for search_term in [
            "FROM ebc@uspto.gov",
            "FROM HelpAAU@uspto.gov",
            "FROM donotreply@uspto.gov",
            "FROM noreply@uspto.gov",
            "SUBJECT USPTO",
            "SUBJECT patent",
            "SUBJECT Filing Receipt",
            "SUBJECT Office Action",
        ]:
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

    print("Done. Run this daily until the formal filing receipt and monitor baseline are confirmed.")


if __name__ == "__main__":
    main()
