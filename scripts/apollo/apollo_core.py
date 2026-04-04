"""Apollo Core — Interactive email agent with learning, secret scrubbing, and training loops.

Apollo is the clear-sighted router. You ask it to find things, discuss the
sorting with it, and it learns. Before anything touches training data,
secrets are scrubbed and stored securely.

Usage:
    # Interactive search
    python scripts/apollo/apollo_core.py search "USPTO patent"
    python scripts/apollo/apollo_core.py search "Stripe payment" --days 30

    # Teach it (feedback loop)
    python scripts/apollo/apollo_core.py teach <msg_id> --correct-tongue RU --correct-route commitments

    # Scrub and collect training context
    python scripts/apollo/apollo_core.py collect --days 7

    # Run training loop
    python scripts/apollo/apollo_core.py train --review
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import imaplib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# Project paths
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

# Load env
_env = ROOT / "config" / "connector_oauth" / ".env.connector.oauth"
if _env.exists():
    for line in _env.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


# =========================================================================== #
#  Secret Scrubber (UM tongue — security/redaction)
# =========================================================================== #

# Patterns that catch secrets, PII, financial data
SECRET_PATTERNS = [
    # API keys and tokens
    (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"), "[SCRUBBED:api_key]"),
    (re.compile(r"\bhf_[A-Za-z0-9_-]{8,}\b"), "[SCRUBBED:hf_token]"),
    (re.compile(r"\bghp_[A-Za-z0-9_-]{8,}\b"), "[SCRUBBED:github_token]"),
    (re.compile(r"\bshpat_[0-9A-Fa-f]{8,}\b"), "[SCRUBBED:shopify_token]"),
    (re.compile(r"\brk_live_[A-Za-z0-9_-]{8,}\b"), "[SCRUBBED:stripe_key]"),
    (re.compile(r"\bxox[ebp]-[A-Za-z0-9._-]{8,}\b"), "[SCRUBBED:slack_token]"),
    (re.compile(r"Authorization:\s*Bearer\s+[^\s]+", re.I), "Authorization: Bearer [SCRUBBED]"),
    (re.compile(r"(api[_-]?key|token|secret|password|passwd|pwd)\s*[:=]\s*['\"]?[^'\"\s,;]{4,}['\"]?", re.I),
     r"\1=[SCRUBBED]"),
    # Credit cards (basic pattern)
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[SCRUBBED:card_number]"),
    # SSN
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SCRUBBED:ssn]"),
    # Email addresses (partial — keep domain, scrub local)
    (re.compile(r"\b[a-zA-Z0-9._%+-]+@(gmail|yahoo|hotmail|outlook|proton)\.(com|me|net)\b", re.I),
     r"[SCRUBBED:email]@\1.\2"),
    # Phone numbers
    (re.compile(r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[SCRUBBED:phone]"),
    # IP addresses (private ranges kept, public scrubbed)
    (re.compile(r"\b(?!(?:10|127|192\.168)\.)(?:\d{1,3}\.){3}\d{1,3}\b"), "[SCRUBBED:ip]"),
    # Account numbers
    (re.compile(r"account\s*#?\s*:?\s*\d{6,}", re.I), "account [SCRUBBED:acct_num]"),
]

# Secrets vault — stores scrubbed secrets securely with fingerprints
VAULT_PATH = ROOT / "config" / "apollo" / ".secrets_vault.json"


def scrub_text(text: str) -> tuple[str, list[dict]]:
    """Scrub secrets from text. Returns (clean_text, list of scrubbed items with fingerprints)."""
    scrubbed_items = []
    clean = text

    for pattern, replacement in SECRET_PATTERNS:
        for match in pattern.finditer(clean):
            original = match.group()
            fingerprint = hashlib.blake2s(original.encode(), digest_size=8).hexdigest()
            scrubbed_items.append({
                "fingerprint": fingerprint,
                "pattern_type": replacement.split(":")[1].rstrip("]") if ":" in replacement else "generic",
                "position": match.start(),
                "length": len(original),
            })
        clean = pattern.sub(replacement, clean)

    return clean, scrubbed_items


def vault_secrets(scrubbed_items: list[dict], context: str = ""):
    """Store secret fingerprints in vault for audit trail (never the actual secrets)."""
    VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)

    vault = {}
    if VAULT_PATH.exists():
        vault = json.loads(VAULT_PATH.read_text())

    entries = vault.setdefault("entries", [])
    entries.append({
        "timestamp": datetime.datetime.now().isoformat(),
        "context": context,
        "count": len(scrubbed_items),
        "fingerprints": [s["fingerprint"] for s in scrubbed_items],
        "types": list(set(s["pattern_type"] for s in scrubbed_items)),
    })

    # Keep last 1000 entries
    vault["entries"] = entries[-1000:]
    VAULT_PATH.write_text(json.dumps(vault, indent=2))


# =========================================================================== #
#  Feedback / Learning Store
# =========================================================================== #

FEEDBACK_PATH = ROOT / "training-data" / "apollo" / "feedback_corrections.jsonl"


@dataclass
class FeedbackRecord:
    """A correction from the user about how an email should have been classified."""
    msg_id: str
    original_tongue: str
    correct_tongue: str
    original_route: str
    correct_route: str
    reason: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.datetime.now().isoformat()


def save_feedback(record: FeedbackRecord):
    """Save a user correction for future training."""
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_PATH, "a") as f:
        json.dump(asdict(record), f)
        f.write("\n")


def load_feedback() -> list[dict]:
    """Load all feedback corrections."""
    if not FEEDBACK_PATH.exists():
        return []
    records = []
    for line in FEEDBACK_PATH.read_text().splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def apply_feedback_to_routes(feedback: list[dict]) -> dict:
    """Build override rules from accumulated feedback."""
    overrides = {}
    for fb in feedback:
        # Track how many times each correction appears
        key = fb.get("correct_tongue", "")
        if key:
            overrides[key] = overrides.get(key, 0) + 1
    return overrides


# =========================================================================== #
#  Interactive Search
# =========================================================================== #

def search_emails(query: str, days: int = 7, accounts: str = "both") -> list[dict]:
    """Search emails across accounts by keyword."""
    results = []

    def _search_account(host, port, user, password, name, use_ssl=False):
        try:
            mail = imaplib.IMAP4_SSL(host, port) if use_ssl else imaplib.IMAP4(host, port)
            mail.login(user, password)
            mail.select("INBOX")

            since = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")

            # Search by subject and body
            for search_field in ["SUBJECT", "BODY", "FROM"]:
                _, ids = mail.search(None, f'({search_field} "{query}" SINCE {since})')
                if ids[0]:
                    for mid in ids[0].split()[-20:]:  # max 20 per field
                        try:
                            _, data = mail.fetch(mid, "(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])")
                            header = data[0][1].decode("utf-8", errors="replace")
                            parts = {}
                            for line in header.strip().split("\n"):
                                if ":" in line:
                                    k, v = line.split(":", 1)
                                    parts[k.strip().lower()] = v.strip()[:100]
                            parts["account"] = name
                            parts["msg_id"] = mid.decode() if isinstance(mid, bytes) else str(mid)
                            results.append(parts)
                        except Exception:
                            continue

            mail.logout()
        except Exception as e:
            print(f"  [{name}] Search failed: {e}")

    if accounts in ("both", "proton"):
        pm_pass = os.environ.get("PROTONMAIL_BRIDGE_PASSWORD", "")
        if pm_pass:
            _search_account("127.0.0.1", 1143,
                            os.environ.get("PROTONMAIL_USER", "issdandavis@proton.me"),
                            pm_pass, "ProtonMail")

    if accounts in ("both", "gmail"):
        gm_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
        if gm_pass:
            _search_account("imap.gmail.com", 993,
                            os.environ.get("GMAIL_USER", "issdandavis7795@gmail.com"),
                            gm_pass, "Gmail", use_ssl=True)

    # Deduplicate by subject+from
    seen = set()
    unique = []
    for r in results:
        key = f"{r.get('subject', '')}{r.get('from', '')}"
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique


# =========================================================================== #
#  Context Collector (scrub → collect → prepare for training)
# =========================================================================== #

def collect_training_context(days: int = 7) -> dict:
    """Collect email context, scrub secrets, prepare for training."""
    from scripts.apollo.email_reader import read_account, generate_sft_pairs

    print("APOLLO CONTEXT COLLECTOR")
    print("=" * 60)

    all_digests = []

    # Read both accounts
    pm_pass = os.environ.get("PROTONMAIL_BRIDGE_PASSWORD", "")
    if pm_pass:
        digests = read_account("127.0.0.1", 1143,
                               os.environ.get("PROTONMAIL_USER", "issdandavis@proton.me"),
                               pm_pass, "ProtonMail", days)
        all_digests.extend(digests)

    gm_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
    if gm_pass:
        digests = read_account("imap.gmail.com", 993,
                               os.environ.get("GMAIL_USER", "issdandavis7795@gmail.com"),
                               gm_pass, "Gmail", days, use_ssl=True)
        all_digests.extend(digests)

    print(f"\nCollected {len(all_digests)} emails from last {days} days")

    # Phase 1: Scrub all secrets
    total_scrubbed = 0
    for d in all_digests:
        clean_subject, s1 = scrub_text(d.subject)
        clean_snippet, s2 = scrub_text(d.snippet)
        clean_sender, s3 = scrub_text(d.sender)
        d.subject = clean_subject
        d.snippet = clean_snippet
        d.sender = clean_sender
        items = s1 + s2 + s3
        total_scrubbed += len(items)
        if items:
            vault_secrets(items, context=f"email:{d.msg_id}")

    print(f"Scrubbed {total_scrubbed} secret items (fingerprints vaulted)")

    # Phase 2: Apply feedback corrections
    feedback = load_feedback()
    if feedback:
        print(f"Loaded {len(feedback)} feedback corrections")

    # Phase 3: Generate SFT pairs (from scrubbed data)
    pairs = generate_sft_pairs(all_digests)

    # Phase 4: Add feedback-based DPO pairs
    dpo_pairs = []
    for fb in feedback:
        dpo_pairs.append({
            "instruction": f"How should an email classified as {fb['original_tongue']} be reclassified?",
            "chosen": f"Reclassify to {fb['correct_tongue']}. Route to {fb['correct_route']}. Reason: {fb.get('reason', 'user correction')}.",
            "rejected": f"Keep as {fb['original_tongue']}. Route to {fb['original_route']}.",
            "source": "apollo_feedback",
            "category": "email_correction",
        })

    # Save
    out_dir = ROOT / "training-data" / "apollo"
    out_dir.mkdir(parents=True, exist_ok=True)

    sft_path = out_dir / f"context_sft_{datetime.date.today().isoformat()}.jsonl"
    with open(sft_path, "w") as f:
        for p in pairs:
            json.dump(p, f)
            f.write("\n")

    if dpo_pairs:
        dpo_path = out_dir / f"context_dpo_{datetime.date.today().isoformat()}.jsonl"
        with open(dpo_path, "w") as f:
            for p in dpo_pairs:
                json.dump(p, f)
                f.write("\n")
        print(f"DPO pairs: {len(dpo_pairs)} -> {dpo_path}")

    print(f"SFT pairs: {len(pairs)} -> {sft_path}")

    return {
        "emails_collected": len(all_digests),
        "secrets_scrubbed": total_scrubbed,
        "sft_pairs": len(pairs),
        "dpo_pairs": len(dpo_pairs),
        "feedback_applied": len(feedback),
    }


# =========================================================================== #
#  CLI
# =========================================================================== #

def main():
    parser = argparse.ArgumentParser(description="Apollo Core — Email agent with learning")
    sub = parser.add_subparsers(dest="command")

    # Search
    s = sub.add_parser("search", help="Search emails by keyword")
    s.add_argument("query", help="Search term")
    s.add_argument("--days", type=int, default=7)
    s.add_argument("--account", choices=["both", "proton", "gmail"], default="both")

    # Teach (feedback)
    t = sub.add_parser("teach", help="Correct a classification")
    t.add_argument("msg_id", help="Message ID to correct")
    t.add_argument("--correct-tongue", required=True, choices=["KO", "AV", "RU", "CA", "UM", "DR"])
    t.add_argument("--correct-route", required=True)
    t.add_argument("--reason", default="")

    # Collect (scrub + prepare training data)
    c = sub.add_parser("collect", help="Scrub secrets and collect training context")
    c.add_argument("--days", type=int, default=7)

    # Stats
    sub.add_parser("stats", help="Show feedback and vault stats")

    args = parser.parse_args()

    if args.command == "search":
        print(f"APOLLO SEARCH: '{args.query}' (last {args.days} days)")
        print("=" * 60)
        results = search_emails(args.query, args.days, args.account)
        if not results:
            print("  No results found.")
        else:
            print(f"  Found {len(results)} emails:\n")
            for r in results[:20]:
                print(f"  [{r.get('account', '?'):10s}] {r.get('subject', '(no subject)')[:70]}")
                print(f"              from {r.get('from', '?')[:50]} ({r.get('date', '?')[:16]})")
                print()

    elif args.command == "teach":
        record = FeedbackRecord(
            msg_id=args.msg_id,
            original_tongue="?",
            correct_tongue=args.correct_tongue,
            original_route="?",
            correct_route=args.correct_route,
            reason=args.reason,
        )
        save_feedback(record)
        print(f"Saved correction: {args.msg_id} -> {args.correct_tongue}/{args.correct_route}")
        total = len(load_feedback())
        print(f"Total feedback records: {total}")

    elif args.command == "collect":
        result = collect_training_context(args.days)
        print(f"\nCollection complete: {json.dumps(result, indent=2)}")

    elif args.command == "stats":
        feedback = load_feedback()
        print(f"Feedback corrections: {len(feedback)}")
        if VAULT_PATH.exists():
            vault = json.loads(VAULT_PATH.read_text())
            entries = vault.get("entries", [])
            total_fp = sum(e["count"] for e in entries)
            print(f"Vault entries: {len(entries)} batches, {total_fp} total scrubbed secrets")
            if entries:
                types = set()
                for e in entries:
                    types.update(e.get("types", []))
                print(f"Secret types seen: {', '.join(sorted(types))}")
        else:
            print("Vault: empty (no secrets scrubbed yet)")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
