#!/usr/bin/env python3
"""Aetherpath audit for SCBE system organization and consolidation planning.

Scans key local directories for:
- Entropic Defense Engine references
- Unimplemented/high-value placeholders
- Repo variant drift

Outputs machine-readable JSON and a compact markdown summary.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

TEXT_EXTS = {".md", ".txt", ".py", ".ps1", ".json", ".yml", ".yaml", ".ts", ".tsx", ".js", ".jsx"}

ENTROPIC_REGEX = re.compile(r"entropic defense engine|entropy defense engine|entropic dual|entropic", re.IGNORECASE)
GAP_REGEX = re.compile(r"TODO|not implemented|placeholder|pending|skipped", re.IGNORECASE)


@dataclass
class Hit:
    path: str
    line: int
    text: str
    category: str
    score: int


def _safe_read_lines(path: Path) -> Iterable[str]:
    try:
        yield from path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return


def _iter_text_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in TEXT_EXTS:
            continue
        yield p


def _score_gap(line: str) -> int:
    line_l = line.lower()
    score = 1
    if "demo_crypto" in line_l:
        score += 4
    if "rate limiting not implemented" in line_l:
        score += 4
    if "placeholder" in line_l:
        score += 2
    if "todo" in line_l:
        score += 1
    if "pending" in line_l:
        score += 1
    return score


def scan_hits(root: Path, cap: int = 300) -> tuple[list[Hit], list[Hit]]:
    entropic_hits: list[Hit] = []
    gap_hits: list[Hit] = []

    for file_path in _iter_text_files(root):
        if len(entropic_hits) >= cap and len(gap_hits) >= cap:
            break

        for i, line in enumerate(_safe_read_lines(file_path), start=1):
            if len(entropic_hits) < cap and ENTROPIC_REGEX.search(line):
                entropic_hits.append(
                    Hit(
                        path=str(file_path),
                        line=i,
                        text=line.strip()[:220],
                        category="entropic",
                        score=1,
                    )
                )

            if len(gap_hits) < cap and GAP_REGEX.search(line):
                gap_hits.append(
                    Hit(
                        path=str(file_path),
                        line=i,
                        text=line.strip()[:220],
                        category="gap",
                        score=_score_gap(line),
                    )
                )

    gap_hits.sort(key=lambda h: h.score, reverse=True)
    return entropic_hits, gap_hits


def find_repo_variants(home: Path) -> list[str]:
    variants = []
    for p in home.iterdir():
        if p.is_dir() and p.name.lower().startswith("scbe-aethermoore"):
            variants.append(str(p))
    variants.sort()
    return variants


def render_markdown(report: dict) -> str:
    lines: list[str] = []
    lines.append("# Aetherpath Audit")
    lines.append("")
    lines.append(f"Generated: {report['generated_at_utc']}")
    lines.append("")

    lines.append("## Repo Variants")
    for v in report["repo_variants"]:
        lines.append(f"- {v}")
    lines.append("")

    lines.append("## Entropic Artifact Hits (Top 20)")
    for h in report["entropic_hits"][:20]:
        lines.append(f"- {h['path']}:{h['line']} :: {h['text']}")
    lines.append("")

    lines.append("## High-Value Gaps (Top 25)")
    for h in report["gap_hits"][:25]:
        lines.append(f"- [score={h['score']}] {h['path']}:{h['line']} :: {h['text']}")
    lines.append("")

    lines.append("## Consolidation Signals")
    lines.append("- Keep one canonical runtime repo and archive/lock mirror variants.")
    lines.append("- Prioritize replacing placeholder cryptography/runtime sections before scaling automation.")
    lines.append("- Normalize connector token names (HF_TOKEN/HUGGINGFACE_TOKEN etc.) across scripts and CI.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit SCBE aetherpaths for consolidation planning")
    parser.add_argument("--home", default=str(Path.home()))
    parser.add_argument("--root", action="append", default=[])
    parser.add_argument("--output-json", default="artifacts/system_audit/aetherpath_audit.json")
    parser.add_argument("--output-md", default="docs/ops/aetherpath_audit_latest.md")
    parser.add_argument("--cap", type=int, default=400)
    args = parser.parse_args()

    home = Path(args.home).resolve()
    roots: list[Path] = []

    if args.root:
        for r in args.root:
            p = Path(r).expanduser().resolve()
            if p.exists() and p.is_dir():
                roots.append(p)
    else:
        defaults = [
            home / "SCBE-AETHERMOORE",
            home / "SCBE-AETHERMOORE-working",
            home / "Downloads",
            home / "Documents",
            home / "Desktop",
        ]
        roots = [p for p in defaults if p.exists() and p.is_dir()]

    entropic_all: list[Hit] = []
    gap_all: list[Hit] = []

    for root in roots:
        entropic_hits, gap_hits = scan_hits(root, cap=args.cap)
        entropic_all.extend(entropic_hits)
        gap_all.extend(gap_hits)

    gap_all.sort(key=lambda h: h.score, reverse=True)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scanned_roots": [str(r) for r in roots],
        "repo_variants": find_repo_variants(home),
        "entropic_hits": [h.__dict__ for h in entropic_all],
        "gap_hits": [h.__dict__ for h in gap_all],
        "counts": {
            "entropic_hits": len(entropic_all),
            "gap_hits": len(gap_all),
            "repo_variants": len(find_repo_variants(home)),
        },
    }

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    out_md = Path(args.output_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_markdown(report), encoding="utf-8")

    print(f"json={out_json.resolve()}")
    print(f"md={out_md.resolve()}")
    print(f"entropic_hits={report['counts']['entropic_hits']}")
    print(f"gap_hits={report['counts']['gap_hits']}")
    print(f"repo_variants={report['counts']['repo_variants']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
