#!/usr/bin/env python3
"""Build an action-oriented GitHub portfolio organization plan.

Consumes output from github_repo_sectioning.py and emits:
1) JSON summary
2) Markdown action plan with:
   - tier counts
   - repos grouped by tier
   - duplicate-family cleanup candidates
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = REPO_ROOT / "artifacts" / "governance"
OUTPUT_DIR = REPO_ROOT / "artifacts" / "governance"


@dataclass(frozen=True)
class RepoRow:
    owner: str
    repo: str
    visibility: str
    tier: str
    url: str
    rationale: str


def _load_rows(path: Path) -> list[RepoRow]:
    rows: list[RepoRow] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                RepoRow(
                    owner=r["owner"],
                    repo=r["repo"],
                    visibility=r["visibility"],
                    tier=r["tier"],
                    url=r["url"],
                    rationale=r.get("rationale", ""),
                )
            )
    return rows


def _latest_sectioning_csv(owner: str) -> Path:
    candidates = sorted(
        DEFAULT_INPUT_DIR.glob(f"github_repo_sectioning_{owner}_*.csv"),
        key=lambda p: p.name,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No sectioning CSV found for owner={owner} in {DEFAULT_INPUT_DIR}"
        )
    return candidates[-1]


def _family_key(repo_name: str) -> str:
    """
    Heuristic family key:
    - lowercase
    - normalize separators
    - drop common variant suffixes
    - drop trailing numeric/version markers
    """
    name = repo_name.lower().replace("_", "-").strip()
    parts = [p for p in name.split("-") if p]
    suffix_tokens = {"main", "pro", "replit", "fork", "copy", "backup", "beta", "v2", "v3"}
    while parts:
        tail = parts[-1]
        if tail in suffix_tokens:
            parts.pop()
            continue
        if re.fullmatch(r"\d+(\.\d+)*", tail):
            parts.pop()
            continue
        break
    return "-".join(parts) if parts else name


def _group_by_tier(rows: Iterable[RepoRow]) -> dict[str, list[RepoRow]]:
    out: dict[str, list[RepoRow]] = defaultdict(list)
    for row in rows:
        out[row.tier].append(row)
    for tier in out:
        out[tier].sort(key=lambda r: r.repo.lower())
    return out


def _find_families(rows: Iterable[RepoRow]) -> dict[str, list[RepoRow]]:
    families: dict[str, list[RepoRow]] = defaultdict(list)
    for row in rows:
        families[_family_key(row.repo)].append(row)
    # keep only meaningful clusters
    return {
        fam: sorted(items, key=lambda r: r.repo.lower())
        for fam, items in families.items()
        if len(items) >= 2
    }


def _recommend_canonical(items: list[RepoRow]) -> RepoRow:
    """
    Pick a canonical repo from a family:
    1) prefer public_sellable
    2) then any public tier
    3) shortest clean name as tie-break
    """
    ranked = sorted(
        items,
        key=lambda r: (
            0 if r.tier == "public_sellable" else 1,
            0 if r.visibility == "public" else 1,
            len(r.repo),
            r.repo.lower(),
        ),
    )
    return ranked[0]


def _tier_priority(tier: str) -> int:
    order = {
        "private_restricted": 0,
        "public_sellable": 1,
        "public_open": 2,
        "public_education": 3,
    }
    return order.get(tier, 99)


def _write_markdown(
    owner: str,
    src_csv: Path,
    rows: list[RepoRow],
    tiers: dict[str, list[RepoRow]],
    families: dict[str, list[RepoRow]],
    out_path: Path,
) -> None:
    counts = {tier: len(items) for tier, items in tiers.items()}
    lines: list[str] = [
        f"# GitHub Portfolio Action Plan ({owner})",
        "",
        f"- Source: `{src_csv}`",
        f"- Generated: `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        f"- Total repos: **{len(rows)}**",
        "",
        "## Tier Counts",
    ]
    for tier in sorted(counts, key=_tier_priority):
        lines.append(f"- `{tier}`: {counts[tier]}")

    lines.extend(["", "## Organization Actions", "- `private_restricted`: keep private and remove public mirrors.", "- `public_sellable`: pin/readme with CTA, pricing, and product links.", "- `public_open`: keep as credibility/open-source surface.", "- `public_education`: keep as docs/tutorial funnel."])

    for tier in sorted(tiers, key=_tier_priority):
        lines.extend(["", f"## {tier}"])
        for row in tiers[tier]:
            lines.append(f"- [{row.repo}]({row.url}) ({row.visibility})")

    lines.extend(["", "## Duplicate-Family Cleanup Candidates"])
    if not families:
        lines.append("- None detected.")
    else:
        for fam in sorted(families):
            items = families[fam]
            canonical = _recommend_canonical(items)
            lines.append(f"- Family `{fam}` → canonical: `{canonical.repo}`")
            for item in items:
                action = "keep"
                if item.repo != canonical.repo:
                    action = "merge/archive"
                lines.append(
                    f"  - {item.repo} ({item.tier}, {item.visibility}) -> {action}"
                )

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build GitHub portfolio action plan from sectioning CSV.")
    parser.add_argument("--owner", default="issdandavis", help="GitHub owner/login")
    parser.add_argument("--input-csv", default="", help="Path to sectioning CSV (defaults to latest for owner)")
    args = parser.parse_args()

    src_csv = Path(args.input_csv) if args.input_csv else _latest_sectioning_csv(args.owner)
    rows = _load_rows(src_csv)
    tiers = _group_by_tier(rows)
    families = _find_families(rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_json = OUTPUT_DIR / f"github_portfolio_action_plan_{args.owner}_{stamp}.json"
    out_md = OUTPUT_DIR / f"github_portfolio_action_plan_{args.owner}_{stamp}.md"

    data = {
        "owner": args.owner,
        "source_csv": str(src_csv),
        "total_repos": len(rows),
        "tier_counts": {tier: len(items) for tier, items in tiers.items()},
        "family_candidates": {
            fam: {
                "canonical": _recommend_canonical(items).repo,
                "repos": [item.repo for item in items],
            }
            for fam, items in families.items()
        },
    }
    out_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
    _write_markdown(args.owner, src_csv, rows, tiers, families, out_md)

    print(
        json.dumps(
            {
                "owner": args.owner,
                "input_csv": str(src_csv),
                "total_repos": len(rows),
                "tier_counts": data["tier_counts"],
                "families": len(families),
                "json": str(out_json),
                "md": str(out_md),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

