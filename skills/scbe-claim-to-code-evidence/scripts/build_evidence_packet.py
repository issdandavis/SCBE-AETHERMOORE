#!/usr/bin/env python3
"""Generate a starter SCBE claim-to-code evidence packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def normalize_page_id(page_id: str) -> str:
    return page_id.replace("-", "").lower()


def load_priority_pages(skill_root: Path) -> list[dict]:
    path = skill_root / "references" / "priority_pages.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_repo_manifest(repo_root: Path) -> dict[str, dict]:
    path = repo_root / "docs" / "notion_pages_manifest.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    pages = raw.get("pages", []) if isinstance(raw, dict) else []
    output: dict[str, dict] = {}
    for row in pages:
        notion_id = normalize_page_id(str(row.get("notion_page_id", "")))
        if notion_id:
            output[notion_id] = row
    return output


def build_rows(priority_pages: list[dict], repo_manifest: dict[str, dict]) -> list[dict]:
    rows: list[dict] = []
    for page in priority_pages:
        notion_id = str(page["notion_id"])
        manifest_row = repo_manifest.get(normalize_page_id(notion_id), {})
        code_paths = manifest_row.get("code_paths", []) if isinstance(manifest_row, dict) else []
        verification_state = manifest_row.get("verification_state", "unmapped") if isinstance(manifest_row, dict) else "unmapped"
        if code_paths and verification_state == "implemented":
            next_action = "Verify tests and demos, then tighten page-to-claim notes."
        elif code_paths:
            next_action = "Review mapped code paths and upgrade/downgrade the verification state."
        else:
            next_action = "Run manual repo search and map the page to concrete code or tests."

        rows.append(
            {
                "title": page["title"],
                "notion_id": notion_id,
                "priority_tier": page["priority_tier"],
                "reason": page["reason"],
                "verification_state": verification_state,
                "repo_code_paths": code_paths,
                "notes": manifest_row.get("last_verification", {}).get("evidence", []) if isinstance(manifest_row, dict) else [],
                "next_action": next_action,
            }
        )
    return rows


def write_markdown(rows: list[dict], output_path: Path) -> None:
    lines = [
        "# SCBE Claim Evidence Starter Manifest",
        "",
        f"- Total priority pages: **{len(rows)}**",
        f"- Already mapped in repo manifest: **{sum(1 for row in rows if row['repo_code_paths'])}**",
        "",
        "## Priority Pages",
        "",
    ]
    for row in rows:
        lines.append(f"### {row['title']}")
        lines.append(f"- Notion ID: `{row['notion_id']}`")
        lines.append(f"- Tier: `{row['priority_tier']}`")
        lines.append(f"- Verification state: `{row['verification_state']}`")
        lines.append(f"- Why it matters: {row['reason']}")
        if row["repo_code_paths"]:
            for path in row["repo_code_paths"]:
                lines.append(f"- Repo path: `{path}`")
        else:
            lines.append("- Repo path: none mapped yet")
        if row["notes"]:
            for note in row["notes"][:3]:
                lines.append(f"- Note: {note}")
        lines.append(f"- Next action: {row['next_action']}")
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a starter SCBE claim evidence packet")
    parser.add_argument("--repo-root", default=".", help="Path to the SCBE repo root")
    parser.add_argument(
        "--output-json",
        default="artifacts/notion_claim_evidence/starter_manifest.json",
        help="JSON output path relative to the repo root",
    )
    parser.add_argument(
        "--output-md",
        default="artifacts/notion_claim_evidence/starter_manifest.md",
        help="Markdown output path relative to the repo root",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    skill_root = Path(__file__).resolve().parents[1]
    rows = build_rows(load_priority_pages(skill_root), load_repo_manifest(repo_root))

    json_path = repo_root / args.output_json
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    md_path = repo_root / args.output_md
    write_markdown(rows, md_path)

    print(f"[evidence-packet] json={json_path}")
    print(f"[evidence-packet] md={md_path}")


if __name__ == "__main__":
    main()
