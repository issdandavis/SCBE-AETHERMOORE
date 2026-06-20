#!/usr/bin/env python3
"""Create a fulfillment folder for a paid AI Governance Snapshot buyer.

This is the post-checkout rail: payment is handled by Stripe, then this script
turns the buyer intake into a small working packet with a memo template,
evidence checklist, and delivery checklist.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_ROOT = REPO_ROOT / "artifacts" / "revenue" / "governance_snapshot"


@dataclass(frozen=True)
class SnapshotIntake:
    buyer_email: str
    workflow_name: str
    payment_reference: str
    deadline: str
    notes: str
    created_at_utc: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned[:64] or "snapshot"


def _memo_template(intake: SnapshotIntake) -> str:
    return f"""# AI Governance Snapshot Findings Memo

Buyer: {intake.buyer_email}
Workflow: {intake.workflow_name}
Payment reference: {intake.payment_reference or "pending"}
Deadline: {intake.deadline or "not provided"}

## 1. Workflow Summary

Describe the AI workflow in plain English:

- Inputs:
- Model or tool:
- Human review point:
- Output or decision:
- External systems touched:

## 2. Risk Findings

Write three prioritized fixes: one immediate fix, one medium fix, and one optional fix.

### Finding 1
- Risk:
- Evidence:
- Practical fix:

### Finding 2
- Risk:
- Evidence:
- Practical fix:

### Finding 3
- Risk:
- Evidence:
- Practical fix:

## 3. Evidence Checklist

- [ ] Intake materials reviewed.
- [ ] No secrets or regulated production data retained.
- [ ] Data path mapped.
- [ ] Human decision point identified.
- [ ] Audit/logging gap identified.
- [ ] Vendor/model dependency identified.
- [ ] Three fixes prioritized.

## 4. Delivery Summary

Write the buyer-facing summary here.
"""


def _evidence_checklist() -> str:
    return """# Evidence Checklist

Use this checklist while reviewing the buyer's workflow.

- [ ] Confirm payment or receipt reference.
- [ ] Save only redacted/public-safe intake files.
- [ ] Identify the AI system, model provider, or local runtime.
- [ ] Identify what data enters the workflow.
- [ ] Identify what data leaves the workflow.
- [ ] Identify who can override the AI output.
- [ ] Identify logging, audit, or receipt gaps.
- [ ] Identify one immediate fix, one medium fix, and one optional fix.
- [ ] Prepare final memo as PDF or Markdown.
- [ ] Send final memo and one follow-up clarification route.
"""


def _delivery_checklist(intake: SnapshotIntake) -> str:
    return f"""# Delivery Checklist

Offer: AI Governance Snapshot
Buyer: {intake.buyer_email}
Workflow: {intake.workflow_name}

- [ ] Intake packet created.
- [ ] Materials screened for secrets or regulated data.
- [ ] Findings memo drafted.
- [ ] Three prioritized fixes written.
- [ ] Evidence checklist completed.
- [ ] Final package delivered by email.
- [ ] Follow-up email thread kept open for one clarification round.

Boundary reminder: this is not legal advice, certification, penetration testing,
FedRAMP authorization, or a guaranteed contract outcome.
"""


def create_snapshot_packet(
    *,
    buyer_email: str,
    workflow_name: str,
    payment_reference: str = "",
    deadline: str = "",
    notes: str = "",
    out_root: Path = DEFAULT_OUT_ROOT,
) -> dict[str, Path]:
    intake = SnapshotIntake(
        buyer_email=buyer_email.strip(),
        workflow_name=workflow_name.strip(),
        payment_reference=payment_reference.strip(),
        deadline=deadline.strip(),
        notes=notes.strip(),
        created_at_utc=_utc_now(),
    )
    if not intake.buyer_email or "@" not in intake.buyer_email:
        raise ValueError("buyer_email must look like an email address")
    if not intake.workflow_name:
        raise ValueError("workflow_name is required")

    day = datetime.now().strftime("%Y-%m-%d")
    folder = out_root / day / f"{_slug(intake.buyer_email)}-{_slug(intake.workflow_name)}"
    folder.mkdir(parents=True, exist_ok=True)

    intake_path = folder / "intake.json"
    memo_path = folder / "findings-memo.md"
    evidence_path = folder / "evidence-checklist.md"
    delivery_path = folder / "delivery-checklist.md"

    intake_path.write_text(json.dumps(asdict(intake), indent=2), encoding="utf-8")
    memo_path.write_text(_memo_template(intake), encoding="utf-8")
    evidence_path.write_text(_evidence_checklist(), encoding="utf-8")
    delivery_path.write_text(_delivery_checklist(intake), encoding="utf-8")

    return {
        "folder": folder,
        "intake": intake_path,
        "memo": memo_path,
        "evidence": evidence_path,
        "delivery": delivery_path,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an AI Governance Snapshot buyer fulfillment packet.")
    parser.add_argument("--buyer-email", required=True)
    parser.add_argument("--workflow-name", required=True)
    parser.add_argument("--payment-reference", default="")
    parser.add_argument("--deadline", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = create_snapshot_packet(
        buyer_email=args.buyer_email,
        workflow_name=args.workflow_name,
        payment_reference=args.payment_reference,
        deadline=args.deadline,
        notes=args.notes,
        out_root=Path(args.out_root),
    )
    print(json.dumps({name: str(path) for name, path in paths.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
