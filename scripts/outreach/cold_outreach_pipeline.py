#!/usr/bin/env python3
"""Cold Outreach Pipeline — Multi-step drafting and sending for SCBE partnerships.

Workflow:
  1. RESEARCH   — Look up the target org/person, find the right contact
  2. DRAFT      — Generate a personalized cold email/message using templates
  3. REVIEW     — Show the draft, let you approve/edit
  4. ATTACH     — Generate compliance report / capability summary as attachment
  5. SEND       — Deliver via email (SMTP), X DM, LinkedIn message, or Telegram
  6. TRACK      — Log the outreach in artifacts/outreach/tracker.jsonl

Usage:
  python scripts/outreach/cold_outreach_pipeline.py draft --target "NIST AISI" --type design_partner
  python scripts/outreach/cold_outreach_pipeline.py draft --target "CISA" --type crada
  python scripts/outreach/cold_outreach_pipeline.py send --draft artifacts/outreach/drafts/nist-aisi.json
  python scripts/outreach/cold_outreach_pipeline.py list                    # Show all drafts
  python scripts/outreach/cold_outreach_pipeline.py track                   # Show outreach log
  python scripts/outreach/cold_outreach_pipeline.py generate-report         # NIST compliance PDF

Also available via CLI:
  scbe-system outreach draft --target "NIST AISI" --type design_partner
"""
from __future__ import annotations

import argparse
import json
import os
import re
import smtplib
import sys
import time
from dataclasses import asdict, dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DRAFTS_DIR = REPO_ROOT / "artifacts" / "outreach" / "drafts"
TRACKER_PATH = REPO_ROOT / "artifacts" / "outreach" / "tracker.jsonl"
ATTACHMENTS_DIR = REPO_ROOT / "artifacts" / "outreach" / "attachments"

# Issac's info
SENDER_NAME = "Issac Daniel Davis"
SENDER_EMAIL = "aethermoregames@pm.me"
SENDER_TITLE = "Founder & Lead Developer"
SENDER_ORG = "SCBE-AETHERMOORE"
PATENT = "USPTO #63/961,403"
ORCID = "0009-0002-3936-9369"
GITHUB = "https://github.com/issdandavis/SCBE-AETHERMOORE"
NPM = "npm install scbe-aethermoore"
PYPI = "pip install scbe-aethermoore"


# ── Target Database ──────────────────────────────────────────────────────────

TARGETS = {
    # ── VERIFIED contacts (web-searched March 2026) ──────────────────────
    "nist-caisi": {
        "org": "NIST Center for AI Standards and Innovation (CAISI)",
        "contact": "peter.cihon@nist.gov",
        "channel": "email",
        "verified": True,
        "source": "https://www.nist.gov/caisi — Peter Cihon, Senior Advisor",
        "context": "CAISI (formerly AISI) issued RFI on securing AI agent systems (Jan 2026)",
        "hook": "Our system passes 23/23 NIST AI RMF compliance checks automatically",
        "note": "Also respond to active RFI at regulations.gov re: AI agent security",
    },
    "cisa-jcdc": {
        "org": "CISA Joint Cyber Defense Collaborative (JCDC)",
        "contact": "cisa.jcdc@cisa.dhs.gov",
        "channel": "email",
        "verified": True,
        "source": "https://www.cisa.gov/topics/partnerships-and-collaboration/joint-cyber-defense-collaborative/jcdc-faqs",
        "context": "JCDC AI Cybersecurity Collaboration Playbook — 340+ partners, 40+ channels",
        "hook": "3-tier PQC fallback with 14-layer adversarial detection, sovereign deployment ready",
        "note": "Also register on Industry Engagement Platform (cisa.gov/doing-business-cisa) and check Open Innovation page",
    },
    "cisa-iep": {
        "org": "CISA Industry Engagement Platform",
        "contact": "https://www.cisa.gov/doing-business-cisa",
        "channel": "portal",
        "verified": True,
        "source": "https://www.cisa.gov/news-events/news/cisa-launches-new-platform-strengthen-industry-engagement-and-collaboration",
        "context": "New platform (Dec 2025) — create org profile, request capability briefing with CISA SMEs",
        "hook": "AI governance framework with PQC, adversarial detection, and NIST compliance",
        "note": "134 orgs approved in first month. AI is listed under Open Innovation Technologies of Interest",
    },
    "diu": {
        "org": "Defense Innovation Unit (DIU)",
        "contact": "https://www.diu.mil/work-with-us/open-solicitations",
        "channel": "portal",
        "verified": True,
        "source": "https://www.diu.mil/work-with-us — Commercial Solutions Opening (CSO)",
        "context": "Submit to open solicitations via CSO portal (15 slides or 5 pages max)",
        "hook": "Air-gapped sovereign deployment with CMMC 2.0 compliance, no phone-home",
        "note": "Check open solicitations first — submit to matching CSO, not cold email",
    },
    "anthropic-fellows": {
        "org": "Anthropic Fellows Program (AI Safety Research)",
        "contact": "https://alignment.anthropic.com/2025/anthropic-fellows-program-2026/",
        "channel": "application",
        "verified": True,
        "source": "https://alignment.anthropic.com — Applications open for July 2026 cohort",
        "context": "4-month fellowship, $3,850/wk stipend, $15K/mo compute, mentorship",
        "hook": "AI governance framework with interpretable 6D tongue system beating DeBERTa",
        "note": "No PhD required. Backgrounds from physics, math, CS, cybersecurity accepted",
    },
    "aws-marketplace": {
        "org": "AWS Marketplace (SaaS Listing)",
        "contact": "https://aws.amazon.com/marketplace/management/tour",
        "channel": "portal",
        "verified": True,
        "source": "https://docs.aws.amazon.com/marketplace/latest/userguide/saas-create-product.html",
        "context": "SaaS seller registration — must have production-ready software + support",
        "hook": "Production-ready npm/PyPI package with usage-based billing built in",
        "note": "New requirement: Concurrent Agreement support by June 1, 2026",
    },
    # ── UNVERIFIED — need specific contact lookup ────────────────────────
    "nsf": {
        "org": "NSF Convergence Accelerator",
        "contact": "https://www.nsf.gov/funding/initiatives/convergence-accelerator",
        "channel": "portal",
        "verified": False,
        "source": "No 2026 AI governance track found — check for new solicitation announcements",
        "context": "Regional expansion underway, new track announcements expected",
        "hook": "Open-source AI safety framework with patented hyperbolic cost scaling",
        "note": "UNVERIFIED — no current open track for AI governance. Monitor for 2026 cohort",
    },
}


# ── Outreach Types ───────────────────────────────────────────────────────────

OUTREACH_TYPES = {
    "design_partner": {
        "subject": "Design Partner Opportunity: AI Governance with Provable Safety Guarantees",
        "ask": "a 30-day evaluation period with structured feedback",
        "offer": "free access to the full system during evaluation, dedicated integration support",
        "reciprocity": "structured monthly feedback, anonymized case study rights, good-faith commercial discussion if evaluation succeeds",
    },
    "crada": {
        "subject": "CRADA Proposal: Post-Quantum AI Governance Framework",
        "ask": "a Cooperative Research and Development Agreement for joint testing",
        "offer": "our patented AI governance system with NIST AI RMF compliance",
        "reciprocity": "testing infrastructure, domain expertise, and joint publication rights",
    },
    "sbir": {
        "subject": "SBIR/STTR Inquiry: AI Safety Governance for Federal Systems",
        "ask": "guidance on applicable SBIR/STTR topics for AI governance",
        "offer": "working prototype with patent, NIST compliance, and sovereign deployment capability",
        "reciprocity": "Phase I funding for formal evaluation and hardening",
    },
    "pilot": {
        "subject": "Pilot Program: SCBE-AETHERMOORE AI Governance",
        "ask": "a pilot deployment to validate our system against your real workloads",
        "offer": "zero-cost pilot with full enterprise features for 90 days",
        "reciprocity": "feedback, metrics, and a reference if the pilot succeeds",
    },
    "open_source": {
        "subject": "Open Source Collaboration: AI Safety Framework",
        "ask": "collaboration on testing and extending the framework",
        "offer": "full source access (MIT-licensed core, dual-license commercial)",
        "reciprocity": "contributions, bug reports, and co-authorship on publications",
    },
}


# ── Templates ────────────────────────────────────────────────────────────────

def generate_email_body(target: dict, outreach_type: dict) -> str:
    return f"""Dear {target['org']} Team,

I'm reaching out because {target['context'].lower()}, and I believe our system addresses a gap you're actively working on.

**What we built**: SCBE-AETHERMOORE is an open-source AI governance framework that uses hyperbolic geometry to make adversarial behavior exponentially expensive. Instead of classifying threats with opaque neural networks, we use 6 named, interpretable dimensions — and we beat industry-standard detectors in head-to-head benchmarks.

**Why it matters for you**: {target['hook']}.

**Key capabilities**:
- 14-layer security pipeline with post-quantum cryptography (ML-KEM-768, ML-DSA-65)
- 100% NIST AI RMF compliance (23/23 automated checks)
- Air-gapped sovereign deployment (no telemetry, no phone-home)
- Anti-model-extraction defense (entropy surface nullification)
- Patent pending (USPTO {PATENT})

**What I'm asking for**: {outreach_type['ask']}.

**What I'm offering**: {outreach_type['offer']}.

**Fair reciprocity**: {outreach_type['reciprocity']}.

The system is live and installable today ({NPM} or {PYPI}). I've attached a compliance summary. Happy to do a technical walkthrough at your convenience.

Best regards,
{SENDER_NAME}
{SENDER_TITLE}, {SENDER_ORG}
{SENDER_EMAIL}
ORCID: {ORCID}
GitHub: {GITHUB}
"""


# ── Draft Management ─────────────────────────────────────────────────────────

@dataclass
class OutreachDraft:
    target_id: str
    org: str
    contact: str
    channel: str
    outreach_type: str
    subject: str
    body: str
    attachment_path: Optional[str] = None
    status: str = "draft"  # draft, approved, sent, replied, rejected
    created_at: float = 0
    sent_at: float = 0
    notes: str = ""


def save_draft(draft: OutreachDraft) -> Path:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", draft.target_id.lower()).strip("-")
    path = DRAFTS_DIR / f"{slug}.json"
    draft.created_at = time.time()
    with open(path, "w") as f:
        json.dump(asdict(draft), f, indent=2)
    return path


def load_draft(path: Path) -> OutreachDraft:
    with open(path) as f:
        data = json.load(f)
    return OutreachDraft(**data)


def log_outreach(draft: OutreachDraft, result: str):
    TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": time.time(),
        "target": draft.org,
        "contact": draft.contact,
        "channel": draft.channel,
        "type": draft.outreach_type,
        "status": draft.status,
        "result": result,
    }
    with open(TRACKER_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ── Compliance Report Generator ──────────────────────────────────────────────

def generate_compliance_attachment() -> Path:
    """Generate a text compliance summary as an attachment."""
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    path = ATTACHMENTS_DIR / "SCBE_Compliance_Summary.txt"

    try:
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from licensing import generate_compliance_report, generate_policy_framework_report
        compliance = generate_compliance_report()
        policy = generate_policy_framework_report()

        lines = [
            "SCBE-AETHERMOORE Compliance Summary",
            "=" * 50,
            f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
            f"System: SCBE-AETHERMOORE v3.3.0",
            f"Patent: USPTO #63/961,403 (provisional)",
            f"Author: Issac Daniel Davis (ORCID: 0009-0002-3936-9369)",
            "",
            "NIST AI RMF 1.0 Compliance",
            "-" * 40,
            f"Total checks: {compliance.total_checks}",
            f"Pass rate: {compliance.pass_rate:.0%}",
            "",
        ]

        for check in compliance.checks:
            lines.append(f"  [{check.status}] {check.check_id}: {check.description}")
            lines.append(f"         SCBE mapping: {check.scbe_mapping}")

        lines.extend([
            "",
            "White House AI Policy Framework (March 2026)",
            "-" * 40,
            f"Readiness: {policy.readiness_rate:.0%}",
            "",
        ])

        for pillar in policy.pillars:
            name = getattr(pillar, 'pillar_name', getattr(pillar, 'name', str(pillar)))
            readiness = getattr(pillar, 'readiness', 'Unknown')
            lines.append(f"  {name}: {readiness}")
            cap = getattr(pillar, 'scbe_capability', '')
            if cap:
                lines.append(f"    SCBE: {cap}")
            lines.append("")

        lines.extend([
            "",
            "Cryptographic Stack",
            "-" * 40,
            "  Symmetric: AES-256-GCM (FIPS 197)",
            "  Key Encapsulation: ML-KEM-768 (FIPS 203)",
            "  Digital Signatures: ML-DSA-65 (FIPS 204)",
            "  Hashing: SHA-3-256 (FIPS 202)",
            "  Key Derivation: HKDF (RFC 5869)",
            "",
            "Deployment Options",
            "-" * 40,
            "  - Air-gapped (no network, HMAC-only license validation)",
            "  - Sovereign Cloud (FedRAMP High)",
            "  - On-premises (enterprise data center)",
            "  - Edge/tactical (SCIF-compatible)",
            "",
            f"Install: npm install scbe-aethermoore",
            f"Install: pip install scbe-aethermoore",
            f"Source: {GITHUB}",
        ])

        with open(path, "w") as f:
            f.write("\n".join(lines))

    except Exception as e:
        with open(path, "w") as f:
            f.write(f"SCBE-AETHERMOORE Compliance Summary\n\nGeneration error: {e}\n"
                    f"Install and run: python -c 'from src.licensing import generate_compliance_report; print(generate_compliance_report())'")

    return path


# ── Sending ──────────────────────────────────────────────────────────────────

def send_email(draft: OutreachDraft) -> str:
    """Send via SMTP (ProtonMail Bridge or any SMTP)."""
    smtp_host = os.environ.get("SMTP_HOST", "127.0.0.1")
    smtp_port = int(os.environ.get("SMTP_PORT", "1025"))
    smtp_user = os.environ.get("SMTP_USER", SENDER_EMAIL)
    smtp_pass = os.environ.get("SMTP_PASS", "")

    msg = MIMEMultipart()
    msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg["To"] = draft.contact
    msg["Subject"] = draft.subject
    msg.attach(MIMEText(draft.body, "plain"))

    if draft.attachment_path and Path(draft.attachment_path).exists():
        with open(draft.attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={Path(draft.attachment_path).name}")
            msg.attach(part)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_pass:
                server.starttls()
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return "sent"
    except Exception as e:
        return f"failed: {e}"


def send_telegram(draft: OutreachDraft) -> str:
    """Send preview to yourself via Telegram bot."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_OWNER_ID", "")
    if not token or not chat_id:
        return "skipped: no TELEGRAM_BOT_TOKEN or TELEGRAM_OWNER_ID"

    text = f"**Outreach Draft: {draft.org}**\n\nSubject: {draft.subject}\nTo: {draft.contact}\n\n{draft.body[:3000]}"
    data = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode()
    req = Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data,
                  headers={"Content-Type": "application/json"})
    try:
        urlopen(req, timeout=10)
        return "sent_to_telegram"
    except Exception as e:
        return f"telegram_failed: {e}"


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_draft(args):
    target_id = args.target.lower().replace(" ", "-")
    target = TARGETS.get(target_id)
    if not target:
        # Custom target
        target = {
            "org": args.target,
            "contact": args.contact or "unknown",
            "channel": "email",
            "context": args.context or "AI governance",
            "hook": args.hook or "provable AI safety with interpretable dimensions",
        }

    otype = OUTREACH_TYPES.get(args.type, OUTREACH_TYPES["design_partner"])

    # Generate compliance attachment
    attachment = generate_compliance_attachment()

    body = generate_email_body(target, otype)
    draft = OutreachDraft(
        target_id=target_id,
        org=target["org"],
        contact=target["contact"],
        channel=target["channel"],
        outreach_type=args.type,
        subject=otype["subject"],
        body=body,
        attachment_path=str(attachment),
    )

    path = save_draft(draft)
    print(f"\nDraft saved: {path}")
    print(f"To: {draft.contact}")
    print(f"Subject: {draft.subject}")
    print(f"Attachment: {attachment}")
    print(f"\n--- Preview ---\n{body[:500]}...")
    print(f"\nApprove and send: python {__file__} send --draft {path}")
    print(f"Send preview to Telegram: python {__file__} preview --draft {path}")


def cmd_send(args):
    draft = load_draft(Path(args.draft))
    print(f"Sending to {draft.contact} via {draft.channel}...")

    if draft.channel == "email":
        result = send_email(draft)
    else:
        result = f"unsupported channel: {draft.channel}"

    draft.status = "sent" if "sent" in result else "failed"
    draft.sent_at = time.time()
    save_draft(draft)
    log_outreach(draft, result)
    print(f"Result: {result}")


def cmd_preview(args):
    draft = load_draft(Path(args.draft))
    result = send_telegram(draft)
    print(f"Telegram preview: {result}")


def cmd_list(args):
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    drafts = sorted(DRAFTS_DIR.glob("*.json"))
    if not drafts:
        print("No drafts yet. Create one: python scripts/outreach/cold_outreach_pipeline.py draft --target 'NIST AISI'")
        return
    for p in drafts:
        d = load_draft(p)
        print(f"  [{d.status}] {d.org} ({d.contact}) — {d.outreach_type}")


def cmd_track(args):
    if not TRACKER_PATH.exists():
        print("No outreach logged yet.")
        return
    with open(TRACKER_PATH) as f:
        for line in f:
            entry = json.loads(line)
            ts = time.strftime("%Y-%m-%d", time.gmtime(entry["timestamp"]))
            print(f"  {ts} [{entry['status']}] {entry['target']} via {entry['channel']} — {entry['result'][:50]}")


def cmd_generate_report(args):
    path = generate_compliance_attachment()
    print(f"Report generated: {path}")


def cmd_draft_all(args):
    """Draft outreach to all targets in the database."""
    otype = args.type or "design_partner"
    for target_id in TARGETS:
        target = TARGETS[target_id]
        ot = OUTREACH_TYPES.get(otype, OUTREACH_TYPES["design_partner"])
        attachment = generate_compliance_attachment()
        body = generate_email_body(target, ot)
        draft = OutreachDraft(
            target_id=target_id, org=target["org"], contact=target["contact"],
            channel=target["channel"], outreach_type=otype, subject=ot["subject"],
            body=body, attachment_path=str(attachment),
        )
        path = save_draft(draft)
        print(f"  [{target_id}] {target['org']} -> {path.name}")
    print(f"\nDrafted {len(TARGETS)} outreach emails. Review in {DRAFTS_DIR}")


def main():
    parser = argparse.ArgumentParser(description="Cold outreach pipeline for SCBE partnerships")
    sub = parser.add_subparsers(dest="command", required=True)

    d = sub.add_parser("draft", help="Draft an outreach email")
    d.add_argument("--target", required=True, help="Target org (e.g., 'NIST AISI', 'CISA', 'DIU')")
    d.add_argument("--type", default="design_partner", choices=list(OUTREACH_TYPES.keys()))
    d.add_argument("--contact", help="Contact email (for custom targets)")
    d.add_argument("--context", help="Context line (for custom targets)")
    d.add_argument("--hook", help="Hook line (for custom targets)")
    d.set_defaults(func=cmd_draft)

    da = sub.add_parser("draft-all", help="Draft outreach to all known targets")
    da.add_argument("--type", default="design_partner", choices=list(OUTREACH_TYPES.keys()))
    da.set_defaults(func=cmd_draft_all)

    s = sub.add_parser("send", help="Send an approved draft")
    s.add_argument("--draft", required=True, help="Path to draft JSON")
    s.set_defaults(func=cmd_send)

    p = sub.add_parser("preview", help="Send draft preview to your Telegram")
    p.add_argument("--draft", required=True, help="Path to draft JSON")
    p.set_defaults(func=cmd_preview)

    sub.add_parser("list", help="List all drafts").set_defaults(func=cmd_list)
    sub.add_parser("track", help="Show outreach log").set_defaults(func=cmd_track)
    sub.add_parser("generate-report", help="Generate compliance attachment").set_defaults(func=cmd_generate_report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
