"""Build a revenue-first agent fleet board from contract shortlists.

The board converts opportunity notes into repeatable agent tasks so capture work
also creates evidence, training examples, and routing data for the coding fleet.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SHORTLIST = REPO_ROOT / "artifacts" / "contracts" / "actionable_bid_shortlist_2026-04-25.md"
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "revenue_fleet_board" / "latest"


LANE_STEPS = [
    {
        "lane": "capture",
        "action": "verify_notice",
        "owner": "research_agent",
        "definition_of_done": "Official notice, due date, contacts, NAICS, and attachment status are verified.",
    },
    {
        "lane": "qualification",
        "action": "bid_no_bid",
        "owner": "operator_agent",
        "definition_of_done": "Direct, team-only, or pass decision is recorded with blockers.",
    },
    {
        "lane": "proof",
        "action": "map_existing_artifacts",
        "owner": "coding_agent",
        "definition_of_done": "Repo-backed proof artifacts are linked or a gap task is created.",
    },
    {
        "lane": "response",
        "action": "draft_response",
        "owner": "proposal_agent",
        "definition_of_done": "Capability statement, RFI response, or partner inquiry draft is staged locally.",
    },
    {
        "lane": "followup",
        "action": "track_receipt",
        "owner": "admin_agent",
        "definition_of_done": "Sent status, reply deadline, and next follow-up date are recorded.",
    },
]


@dataclass(frozen=True)
class Opportunity:
    title: str
    solicitation: str
    due: str
    agency: str
    fit: str
    action: str
    section: str


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_shortlist(markdown: str) -> list[Opportunity]:
    """Parse the human shortlist markdown into opportunity records.

    This intentionally accepts loose formatting because the contract files are
    human-maintained artifacts. Unknown fields become empty strings.
    """

    opportunities: list[Opportunity] = []
    current_section = ""
    current_title = ""
    fields: dict[str, str] = {}

    def flush() -> None:
        nonlocal current_title, fields
        if not current_title:
            return
        solicitation = fields.get("solicitation", "")
        if solicitation:
            opportunities.append(
                Opportunity(
                    title=current_title,
                    solicitation=solicitation,
                    due=fields.get("due", ""),
                    agency=fields.get("agency", ""),
                    fit=fields.get("fit", ""),
                    action=fields.get("action", ""),
                    section=current_section,
                )
            )
        current_title = ""
        fields = {}

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            flush()
            current_section = _clean(line[3:])
            continue
        if line.startswith("### "):
            flush()
            current_title = _clean(re.sub(r"^\d+\.\s*", "", line[4:]))
            continue
        if current_title and line.startswith("- "):
            match = re.match(r"-\s*([^:]+):\s*(.*)$", line)
            if match:
                key = match.group(1).strip().lower().replace(" ", "_")
                value = _clean(match.group(2).strip("` "))
                fields[key] = value

    flush()
    return opportunities


def priority_for(opportunity: Opportunity) -> str:
    text = " ".join(
        [
            opportunity.section,
            opportunity.fit,
            opportunity.action,
            opportunity.due,
            opportunity.title,
        ]
    ).lower()
    if "janitorial" in text or "only viable" in text or "local vendor" in text or "do not self-perform" in text:
        return "P2"
    if "high priority" in text or "bid-now" in text or "respond-now" in text:
        return "P0"
    if "strong" in text or "realistic" in text or "sources-sought" in text:
        return "P1"
    if "team" in text or "possible" in text:
        return "P2"
    return "P3"


def board_rows(opportunities: Iterable[Opportunity]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for opp in opportunities:
        priority = priority_for(opp)
        for index, step in enumerate(LANE_STEPS, start=1):
            rows.append(
                {
                    "board_version": "scbe_revenue_fleet_board_v1",
                    "task_id": f"{opp.solicitation}-{index:02d}-{step['action']}",
                    "opportunity": opp.title,
                    "solicitation": opp.solicitation,
                    "priority": priority,
                    "due": opp.due,
                    "agency": opp.agency,
                    "lane": step["lane"],
                    "action": step["action"],
                    "owner": step["owner"],
                    "status": "todo",
                    "definition_of_done": step["definition_of_done"],
                    "source_section": opp.section,
                    "fit": opp.fit,
                    "next_action": opp.action,
                }
            )
    return rows


def write_outputs(rows: list[dict[str, str]], out_dir: Path) -> tuple[Path, Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "revenue_fleet_board.json"
    csv_path = out_dir / "revenue_fleet_board.csv"
    md_path = out_dir / "revenue_fleet_board.md"

    payload = {
        "schema_version": "scbe_revenue_fleet_board_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(rows),
        "rows": rows,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    fieldnames = list(rows[0].keys()) if rows else [
        "board_version",
        "task_id",
        "opportunity",
        "solicitation",
        "priority",
        "due",
        "agency",
        "lane",
        "action",
        "owner",
        "status",
        "definition_of_done",
        "source_section",
        "fit",
        "next_action",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Revenue Fleet Board",
        "",
        "This board converts contract opportunities into agentic fleet moves.",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- tasks: `{len(rows)}`",
        "",
        "| Priority | Solicitation | Lane | Owner | Action | Status |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {priority} | {solicitation} | {lane} | {owner} | {action} | {status} |".format(**row)
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, csv_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the SCBE revenue fleet task board.")
    parser.add_argument("--shortlist", default=str(DEFAULT_SHORTLIST), help="Markdown shortlist to parse.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    shortlist = Path(args.shortlist)
    out_dir = Path(args.out_dir)
    markdown = shortlist.read_text(encoding="utf-8")
    opportunities = parse_shortlist(markdown)
    rows = board_rows(opportunities)
    json_path, csv_path, md_path = write_outputs(rows, out_dir)
    print(f"opportunities={len(opportunities)}")
    print(f"tasks={len(rows)}")
    print(f"json={json_path}")
    print(f"csv={csv_path}")
    print(f"md={md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
