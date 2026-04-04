"""Apollo Email Reader — Task-oriented email triage and SFT generation.

Apollo reads emails, classifies them by Sacred Tongue channels,
routes them to workflows, and generates training data for a
closed-loop task agent.

Usage:
    python scripts/apollo/email_reader.py                    # Read + classify recent emails
    python scripts/apollo/email_reader.py --days 3           # Last 3 days
    python scripts/apollo/email_reader.py --generate-sft     # Also emit training pairs
    python scripts/apollo/email_reader.py --route             # Classify + suggest actions
"""

from __future__ import annotations

import argparse
import datetime
import email
import email.header
import hashlib
import imaplib
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Tuple

# Load env
_env = Path(__file__).resolve().parent.parent.parent / "config" / "connector_oauth" / ".env.connector.oauth"
if _env.exists():
    for line in _env.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


# =========================================================================== #
#  Tongue classification rules
# =========================================================================== #

TONGUE_SIGNALS: Dict[str, List[str]] = {
    "KO": [  # Intent / control / requests
        "please", "request", "asking", "need", "want", "action required",
        "follow up", "deadline", "urgent", "asap", "priority", "approve",
        "confirm", "decision", "next steps", "todo", "task",
    ],
    "AV": [  # Metadata / context / informational
        "fyi", "update", "newsletter", "digest", "summary", "report",
        "notification", "alert", "info", "announcement", "release notes",
        "changelog", "status", "weekly", "daily", "monthly",
    ],
    "RU": [  # Binding / commitments / obligations
        "agreement", "contract", "terms", "commitment", "promise",
        "invoice", "receipt", "payment due", "subscription", "renewal",
        "obligation", "signed", "binding", "warranty", "guarantee",
    ],
    "CA": [  # Compute / technical / code
        "deploy", "build", "error", "bug", "fix", "merge", "pr ",
        "pull request", "commit", "pipeline", "ci/cd", "api", "token",
        "server", "database", "migration", "release", "version",
    ],
    "UM": [  # Security / sensitive / redaction
        "password", "credential", "security", "breach", "vulnerability",
        "2fa", "mfa", "verification", "suspicious", "unauthorized",
        "phishing", "malware", "encrypt", "confidential", "private",
    ],
    "DR": [  # Structure / administrative / filing
        "account", "settings", "profile", "unsubscribe", "preferences",
        "policy", "privacy", "terms of service", "welcome", "onboarding",
        "registration", "confirmation", "verify email", "activate",
    ],
}

# Route definitions: tongue pattern → action
ROUTE_TABLE = {
    ("KO",): {"action": "RESPOND", "queue": "action_required", "desc": "Needs a response or decision"},
    ("RU",): {"action": "FILE", "queue": "commitments", "desc": "Financial or contractual — file and track"},
    ("UM",): {"action": "FLAG", "queue": "security_review", "desc": "Security-sensitive — review immediately"},
    ("CA",): {"action": "TRIAGE", "queue": "tech_inbox", "desc": "Technical — route to dev workflow"},
    ("AV",): {"action": "READ", "queue": "informational", "desc": "Informational — read when free"},
    ("DR",): {"action": "ARCHIVE", "queue": "administrative", "desc": "Administrative — archive after skim"},
    ("KO", "UM"): {"action": "ESCALATE", "queue": "urgent_security", "desc": "Urgent security action needed"},
    ("KO", "RU"): {"action": "RESPOND", "queue": "commitments", "desc": "Action needed on a commitment"},
}


@dataclass
class EmailDigest:
    """Classified email digest entry."""
    msg_id: str
    account: str
    sender: str
    subject: str
    date: str
    tongues: List[str]
    top_tongue: str
    route: Dict
    snippet: str = ""  # first ~200 chars, no full body
    tongue_scores: Dict[str, int] = field(default_factory=dict)


def decode_header_value(raw: str) -> str:
    """Decode MIME-encoded header values."""
    if not raw:
        return ""
    parts = email.header.decode_header(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def classify_tongues(subject: str, snippet: str) -> Tuple[Dict[str, int], List[str], str]:
    """Classify email text by Sacred Tongue activations."""
    text = f"{subject} {snippet}".lower()
    scores = {}
    for tongue, signals in TONGUE_SIGNALS.items():
        score = sum(1 for s in signals if s in text)
        if score > 0:
            scores[tongue] = score

    if not scores:
        return {"AV": 1}, ["AV"], "AV"  # default: informational

    sorted_tongues = sorted(scores.keys(), key=lambda t: scores[t], reverse=True)
    top = sorted_tongues[0]
    active = [t for t in sorted_tongues if scores[t] > 0]
    return scores, active, top


def route_email(tongues: List[str]) -> Dict:
    """Route email based on tongue pattern."""
    # Try exact match first, then single-tongue
    tongue_tuple = tuple(sorted(tongues[:2]))
    if tongue_tuple in ROUTE_TABLE:
        return ROUTE_TABLE[tongue_tuple]
    if (tongues[0],) in ROUTE_TABLE:
        return ROUTE_TABLE[(tongues[0],)]
    return {"action": "READ", "queue": "general", "desc": "No specific route — general inbox"}


def get_snippet(msg) -> str:
    """Extract first ~200 chars of plaintext body."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    return body[:200].replace("\n", " ").strip()
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
            return body[:200].replace("\n", " ").strip()
        except Exception:
            pass
    return ""


def read_account(host: str, port: int, user: str, password: str, account_name: str,
                 days: int = 1, use_ssl: bool = False) -> List[EmailDigest]:
    """Read recent emails from an IMAP account and classify them."""
    try:
        if use_ssl:
            mail = imaplib.IMAP4_SSL(host, port)
        else:
            mail = imaplib.IMAP4(host, port)
        mail.login(user, password)
    except Exception as e:
        print(f"  [{account_name}] Connection failed: {e}")
        return []

    mail.select("INBOX")

    since = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")
    _, msg_ids = mail.search(None, f'(SINCE {since})')

    if not msg_ids[0]:
        print(f"  [{account_name}] No messages in last {days} day(s)")
        mail.logout()
        return []

    ids = msg_ids[0].split()
    print(f"  [{account_name}] {len(ids)} messages in last {days} day(s)")

    digests = []
    # Process last 50 max to avoid timeout
    for mid in ids[-50:]:
        try:
            _, data = mail.fetch(mid, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])

            sender = decode_header_value(msg.get("From", ""))
            subject = decode_header_value(msg.get("Subject", ""))
            date_str = msg.get("Date", "")
            snippet = get_snippet(msg)

            msg_hash = hashlib.blake2s(f"{sender}{subject}{date_str}".encode(), digest_size=8).hexdigest()

            scores, tongues, top = classify_tongues(subject, snippet)
            route = route_email(tongues)

            digests.append(EmailDigest(
                msg_id=msg_hash,
                account=account_name,
                sender=sender[:80],
                subject=subject[:120],
                date=date_str[:30],
                tongues=tongues,
                top_tongue=top,
                route=route,
                snippet=snippet[:200],
                tongue_scores=scores,
            ))
        except Exception:
            continue

    mail.logout()
    return digests


def generate_sft_pairs(digests: List[EmailDigest]) -> List[Dict]:
    """Generate SFT training pairs from classified emails."""
    pairs = []
    for d in digests:
        # Classification pair
        pairs.append({
            "instruction": f"Classify this email by priority and route it to the correct workflow queue.\n\nFrom: {d.sender}\nSubject: {d.subject}",
            "response": f"Tongue activation: {', '.join(d.tongues)} (primary: {d.top_tongue}). Route: {d.route['action']} -> {d.route['queue']}. Reason: {d.route['desc']}.",
            "source": "apollo_email_reader",
            "category": "email_triage",
        })

    return pairs


def print_digest(digests: List[EmailDigest], show_route: bool = False):
    """Print classified email digest."""
    # Group by route action
    by_action = {}
    for d in digests:
        action = d.route["action"]
        by_action.setdefault(action, []).append(d)

    priority_order = ["ESCALATE", "FLAG", "RESPOND", "TRIAGE", "FILE", "READ", "ARCHIVE"]
    for action in priority_order:
        group = by_action.get(action, [])
        if not group:
            continue
        marker = {"ESCALATE": "!!!", "FLAG": "!!", "RESPOND": "!", "TRIAGE": ">", "FILE": "$", "READ": ".", "ARCHIVE": "-"}.get(action, " ")
        print(f"\n  [{action}] ({len(group)} emails)")
        for d in group[:10]:
            tongue_str = "/".join(d.tongues)
            print(f"    {marker} [{tongue_str:8s}] {d.subject[:70]}")
            print(f"              from {d.sender[:50]} ({d.date[:16]})")
            if show_route:
                print(f"              -> {d.route['queue']}: {d.route['desc']}")


def main():
    parser = argparse.ArgumentParser(description="Apollo Email Reader")
    parser.add_argument("--days", type=int, default=1, help="Read emails from last N days")
    parser.add_argument("--generate-sft", action="store_true", help="Generate SFT training pairs")
    parser.add_argument("--route", action="store_true", help="Show routing suggestions")
    parser.add_argument("--output", default=None, help="Output JSON path")
    parser.add_argument("--proton-only", action="store_true")
    parser.add_argument("--gmail-only", action="store_true")
    args = parser.parse_args()

    print("APOLLO EMAIL READER")
    print("=" * 60)

    all_digests = []

    # ProtonMail
    if not args.gmail_only:
        pm_user = os.environ.get("PROTONMAIL_USER", "issdandavis@proton.me")
        pm_pass = os.environ.get("PROTONMAIL_BRIDGE_PASSWORD", "")
        if pm_pass:
            digests = read_account("127.0.0.1", 1143, pm_user, pm_pass, "ProtonMail", args.days)
            all_digests.extend(digests)
        else:
            print("  [ProtonMail] No PROTONMAIL_BRIDGE_PASSWORD set")

    # Gmail
    if not args.proton_only:
        gm_user = os.environ.get("GMAIL_USER", "issdandavis7795@gmail.com")
        gm_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
        if gm_pass:
            digests = read_account("imap.gmail.com", 993, gm_user, gm_pass, "Gmail", args.days, use_ssl=True)
            all_digests.extend(digests)
        else:
            print("  [Gmail] No GMAIL_APP_PASSWORD set")

    if not all_digests:
        print("\nNo emails found.")
        return

    print(f"\nTotal: {len(all_digests)} emails classified")
    print_digest(all_digests, show_route=args.route)

    # Generate SFT
    if args.generate_sft:
        pairs = generate_sft_pairs(all_digests)
        out = args.output or f"training-data/sft/apollo_email_sft_{datetime.date.today().isoformat()}.jsonl"
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as f:
            for p in pairs:
                json.dump(p, f)
                f.write("\n")
        print(f"\nSFT: {len(pairs)} training pairs -> {out}")

    # Save digest
    digest_path = args.output or f"artifacts/apollo/email_digest_{datetime.date.today().isoformat()}.json"
    os.makedirs(os.path.dirname(digest_path), exist_ok=True)
    with open(digest_path, "w") as f:
        json.dump([asdict(d) for d in all_digests], f, indent=2)
    print(f"Digest saved: {digest_path}")


if __name__ == "__main__":
    main()
