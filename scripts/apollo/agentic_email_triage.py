"""Agentic Email Triage — LLM-powered email routing for SCBE.

Extends Apollo with intelligent classification beyond keyword matching.
Routes emails to "agentic employees" (specialized dispatch queues) and
generates draft responses.

Usage:
    python scripts/apollo/agentic_email_triage.py --run
    python scripts/apollo/agentic_email_triage.py --run --auto-reply
    python scripts/apollo/agentic_email_triage.py --dry-run --days 1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

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


# ---------------------------------------------------------------------------
# Agentic Employee Definitions
# ---------------------------------------------------------------------------

AGENTIC_EMPLOYEES = {
    "sales": {
        "name": "Ava (Sales)",
        "role": "agent.sales",
        "handles": ["pricing inquiry", "custom project", "enterprise scoping", "pilot application", "partnership"],
        "tone": "professional, concise, outcome-focused",
        "actions": ["send pricing sheet", "book scoping call", "send pilot agreement"],
    },
    "support": {
        "name": "Sam (Support)",
        "role": "agent.support",
        "handles": ["delivery issue", "missing file", "broken link", "refund request", "purchase help"],
        "tone": "helpful, patient, solution-oriented",
        "actions": ["resend delivery", "process refund", "escalate to human"],
    },
    "technical": {
        "name": "Tao (Technical)",
        "role": "agent.technical",
        "handles": ["api question", "integration help", "bug report", "self-hosting", "code review request"],
        "tone": "precise, technical, references docs",
        "actions": ["link to docs", "provide code snippet", "open GitHub issue"],
    },
    "security": {
        "name": "Sage (Security)",
        "role": "agent.security",
        "handles": ["vulnerability report", "penetration test inquiry", "audit request", "compliance question"],
        "tone": "serious, thorough, process-oriented",
        "actions": ["acknowledge receipt", "request details", "route to red team"],
    },
    "content": {
        "name": "Cara (Content)",
        "role": "agent.content",
        "handles": ["guest post", "interview request", "speaking engagement", "media inquiry"],
        "tone": "warm, story-oriented, calendar-aware",
        "actions": ["send media kit", "propose dates", "decline politely"],
    },
    "admin": {
        "name": "Alex (Admin)",
        "role": "agent.admin",
        "handles": ["spam", "newsletter signup", "unsubscribe", "generic hello", "unclear intent"],
        "tone": "neutral, efficient",
        "actions": ["mark spam", "add to newsletter", "archive"],
    },
}


# ---------------------------------------------------------------------------
# LLM Classification (Gemini fallback to local heuristic)
# ---------------------------------------------------------------------------

@dataclass
class TriageResult:
    msg_id: str
    sender: str
    subject: str
    agent: str
    confidence: float
    summary: str
    draft_reply: str = ""
    action: str = ""
    urgency: str = "normal"  # low, normal, high, critical
    tongue: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def classify_with_llm(sender: str, subject: str, body: str, api_key: Optional[str] = None) -> dict:
    """Use Gemini to classify email intent and route to agentic employee.

    Falls back to heuristic if Gemini is unavailable.
    """
    api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return classify_heuristic(sender, subject, body)

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        agent_descriptions = "\n".join(
            f"- {k}: handles {', '.join(v['handles'])}"
            for k, v in AGENTIC_EMPLOYEES.items()
        )

        prompt = f"""You are an email triage specialist for SCBE-AETHERMOORE, an AI governance company.

Incoming email:
From: {sender}
Subject: {subject}
Body: {body[:2000]}

Agentic employees available:
{agent_descriptions}

Classify this email. Respond ONLY with valid JSON in this exact format:
{{
  "agent": "<employee_key>",
  "confidence": 0.0-1.0,
  "summary": "1-sentence summary",
  "urgency": "low|normal|high|critical",
  "action": "recommended next step",
  "draft_reply": "1-paragraph draft response"
}}
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Extract JSON if wrapped in markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        print(f"[LLM classification failed: {e}] — falling back to heuristic")
        return classify_heuristic(sender, subject, body)


def classify_heuristic(sender: str, subject: str, body: str) -> dict:
    """Fallback keyword-based classification (extends Apollo's tongue system)."""
    text = f"{subject} {body}".lower()

    scores = {}
    for agent_key, agent in AGENTIC_EMPLOYEES.items():
        score = 0
        for keyword in agent["handles"]:
            if keyword.lower() in text:
                score += 1
        scores[agent_key] = score

    best = max(scores, key=scores.get)
    confidence = min(0.5 + scores[best] * 0.15, 0.95)

    # Urgency heuristics
    urgency = "normal"
    if any(w in text for w in ["urgent", "asap", "critical", "breach", "outage"]):
        urgency = "critical"
    elif any(w in text for w in ["deadline", "tomorrow", "expiring", "payment due"]):
        urgency = "high"

    return {
        "agent": best,
        "confidence": confidence,
        "summary": f"Email from {sender} about {subject[:60]}",
        "urgency": urgency,
        "action": AGENTIC_EMPLOYEES[best]["actions"][0],
        "draft_reply": "",
    }


# ---------------------------------------------------------------------------
# Triage Runner
# ---------------------------------------------------------------------------

def run_triage(dry_run: bool = False, days: int = 1, auto_reply: bool = False) -> list[TriageResult]:
    """Run agentic triage on recent emails.

    Args:
        dry_run: Classify without dispatching or saving.
        days: How many days back to look.
        auto_reply: Generate draft replies (does not send without confirmation).
    """
    from scripts.apollo.email_reader import read_account

    host = os.environ.get("PROTONMAIL_IMAP_HOST", "127.0.0.1")
    port = int(os.environ.get("PROTONMAIL_IMAP_PORT", "1143"))
    user = os.environ.get("PROTONMAIL_USER", os.environ.get("PROTONMAIL_SMTP_USER", ""))
    password = os.environ.get("PROTONMAIL_BRIDGE_PASSWORD", "")

    results = []
    if not user or not password:
        print("[WARN] IMAP credentials not configured. Using mock data for demo.")
        digests = []
    else:
        digests = read_account(host=host, port=port, user=user, password=password, account_name="proton", days=days)

    for digest in digests:
        classification = classify_with_llm(
            sender=digest.get("from", "unknown"),
            subject=digest.get("subject", ""),
            body=digest.get("body", ""),
        )

        triage = TriageResult(
            msg_id=digest.get("msg_id", "unknown"),
            sender=digest.get("from", "unknown"),
            subject=digest.get("subject", ""),
            agent=classification["agent"],
            confidence=classification["confidence"],
            summary=classification["summary"],
            draft_reply=classification.get("draft_reply", ""),
            action=classification["action"],
            urgency=classification["urgency"],
            tongue=digest.get("tongue", ""),
        )

        if not dry_run:
            _dispatch_to_queue(triage)

        results.append(triage)

    return results


def _dispatch_to_queue(triage: TriageResult):
    """Store triage result in the dispatch spine for agent pickup."""
    try:
        from scripts.system.advanced_ai_dispatch import connect_db, build_task_id, utc_now

        agent = AGENTIC_EMPLOYEES.get(triage.agent, AGENTIC_EMPLOYEES["admin"])
        conn = connect_db()
        conn.execute(
            """
            INSERT OR IGNORE INTO tasks (
                task_id, title, goal, capability, priority, status, owner_role,
                requested_by, write_scope, dependencies, payload, route, notes,
                evidence_required, created_at, updated_at, lease_owner, lease_expires_at,
                result_summary, failure_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                build_task_id(),
                f"Email: {triage.subject[:80]}",
                triage.summary,
                f"email.{triage.agent}",
                _urgency_to_priority(triage.urgency),
                "queued",
                agent["role"],
                triage.sender,
                json.dumps(["inbox", triage.agent]),
                json.dumps([]),
                json.dumps(asdict(triage)),
                json.dumps({"queue": triage.agent, "action": triage.action}),
                f"Agentic triage: {triage.agent} | confidence: {triage.confidence:.2f}",
                True,
                utc_now(),
                utc_now(),
                None,
                None,
                None,
                None,
            ),
        )
        conn.commit()
        conn.close()
        print(f"  → Dispatch recorded (priority {_urgency_to_priority(triage.urgency)})")
    except Exception as e:
        print(f"  → Dispatch failed: {type(e).__name__}")


def _urgency_to_priority(urgency: str) -> int:
    return {"low": 40, "normal": 60, "high": 80, "critical": 95}.get(urgency, 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Agentic Email Triage for SCBE-AETHERMOORE")
    parser.add_argument("--run", action="store_true", help="Run triage on recent emails")
    parser.add_argument("--dry-run", action="store_true", help="Classify without dispatching")
    parser.add_argument("--days", type=int, default=1, help="Days back to look")
    parser.add_argument("--auto-reply", action="store_true", help="Generate draft replies")
    parser.add_argument("--output", type=str, default="", help="Write results to JSON file")
    args = parser.parse_args()

    if not args.run and not args.dry_run:
        parser.print_help()
        return

    print(f"Running agentic email triage (days={args.days}, dry_run={args.dry_run})...")
    results = run_triage(dry_run=args.dry_run, days=args.days, auto_reply=args.auto_reply)

    print(f"\nTriage complete. {len(results)} emails processed.\n")
    for r in results:
        agent = AGENTIC_EMPLOYEES.get(r.agent, {})
        print(f"  [{r.urgency.upper()}] {agent.get('name', r.agent)} | subject length={len(r.subject)}")
        print(f"           confidence: {r.confidence:.2f} | action: {r.action}")
        if r.draft_reply:
            print(f"           draft prepared ({len(r.draft_reply)} chars)")
        print()

    if args.output:
        Path(args.output).write_text(json.dumps([asdict(r) for r in results], indent=2))
        print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
