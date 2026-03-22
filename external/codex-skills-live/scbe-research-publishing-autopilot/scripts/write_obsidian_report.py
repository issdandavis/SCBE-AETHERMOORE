#!/usr/bin/env python3
"""
Write a daily autopilot status note into an Obsidian vault.

Reads campaign artifacts and emits a deterministic markdown report.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write daily SCBE autopilot note to Obsidian.")
    parser.add_argument("--vault-dir", required=True, help="Obsidian vault root")
    parser.add_argument("--note-subdir", default="Context Room/Reports", help="Subdirectory for reports")
    parser.add_argument("--date", default="", help="Date YYYY-MM-DD; default today UTC")
    parser.add_argument("--dispatch-log", default="", help="Path to dispatch_log.jsonl")
    parser.add_argument("--claim-report", default="", help="Path to claim_gate_report.json")
    parser.add_argument("--retrigger-actions", default="", help="Path to retrigger_actions.json")
    parser.add_argument("--self-context", default="", help="Path to self_context_pack.json")
    parser.add_argument("--campaign-id", default="campaign", help="Campaign label in note title")
    parser.add_argument("--out", default="", help="Optional explicit output note path")
    return parser.parse_args()


def ts_today(raw_date: str) -> str:
    if raw_date.strip():
        return raw_date.strip()
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def summarize_dispatch(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {"total": len(rows)}
    for row in rows:
        status = str(row.get("status", "unknown"))
        out[status] = out.get(status, 0) + 1
    return out


def top_actions(payload: Any) -> List[Tuple[str, int]]:
    actions = []
    if isinstance(payload, dict):
        raw = payload.get("actions", [])
        if isinstance(raw, list):
            actions = [a for a in raw if isinstance(a, dict)]
    counts: Dict[str, int] = {}
    for row in actions:
        key = str(row.get("action", "unknown"))
        counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def write_note(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def build_markdown(
    date_str: str,
    campaign_id: str,
    dispatch_summary: Dict[str, int],
    claim_summary: Dict[str, Any],
    action_counts: List[Tuple[str, int]],
    context_summary: Dict[str, Any],
) -> str:
    total = dispatch_summary.get("total", 0)
    sent = dispatch_summary.get("sent", 0)
    blocked = dispatch_summary.get("blocked_unapproved", 0)
    failed = dispatch_summary.get("failed_send", 0) + dispatch_summary.get("failed_missing_connector", 0)

    claim_pass = bool(claim_summary.get("pass", False))
    claims_checked = int(claim_summary.get("claims_checked", 0))
    claims_failed = int(claim_summary.get("claims_failed", 0))

    posts_seen = int(context_summary.get("posts_seen", 0))
    datasets_seen = int(context_summary.get("datasets_seen", 0))

    lines: List[str] = []
    lines.append(f"# SCBE Autopilot Daily Report - {date_str}")
    lines.append("")
    lines.append(f"Campaign: `{campaign_id}`")
    lines.append("")
    lines.append("## Dispatch")
    lines.append(f"- Total events processed: {total}")
    lines.append(f"- Sent: {sent}")
    lines.append(f"- Blocked (approval gate): {blocked}")
    lines.append(f"- Failed: {failed}")
    lines.append("")
    lines.append("## Claim Gate")
    lines.append(f"- Pass: {claim_pass}")
    lines.append(f"- Claims checked: {claims_checked}")
    lines.append(f"- Claims failed: {claims_failed}")
    lines.append("")
    lines.append("## Context-of-Self")
    lines.append(f"- Prior posts analyzed: {posts_seen}")
    lines.append(f"- Datasets mapped: {datasets_seen}")
    lines.append("")
    lines.append("## Retrigger Actions")
    if action_counts:
        for action, count in action_counts:
            lines.append(f"- {action}: {count}")
    else:
        lines.append("- No retrigger actions")
    lines.append("")
    lines.append("## Ops Notes")
    lines.append("- 2.5-party monitoring active")
    lines.append("- Evidence gate enforced before publish")
    lines.append("- Manual approval required unless explicitly bypassed")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    date_str = ts_today(args.date)

    dispatch_rows = read_jsonl(Path(args.dispatch_log)) if args.dispatch_log else []
    claim_payload = read_json(Path(args.claim_report), {}) if args.claim_report else {}
    claim_summary = claim_payload.get("summary", {}) if isinstance(claim_payload, dict) else {}
    retrigger_payload = read_json(Path(args.retrigger_actions), {}) if args.retrigger_actions else {}
    context_payload = read_json(Path(args.self_context), {}) if args.self_context else {}
    context_summary = context_payload.get("summary", {}) if isinstance(context_payload, dict) else {}

    dispatch_summary = summarize_dispatch(dispatch_rows)
    action_counts = top_actions(retrigger_payload)

    md = build_markdown(
        date_str=date_str,
        campaign_id=args.campaign_id,
        dispatch_summary=dispatch_summary,
        claim_summary=claim_summary if isinstance(claim_summary, dict) else {},
        action_counts=action_counts,
        context_summary=context_summary if isinstance(context_summary, dict) else {},
    )

    if args.out.strip():
        out_path = Path(args.out)
    else:
        vault = Path(args.vault_dir)
        out_path = vault / args.note_subdir / f"{date_str} - SCBE Autopilot Report.md"

    write_note(out_path, md)
    print(f"Wrote note: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
