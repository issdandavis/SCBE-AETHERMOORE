"""Audit unfinished docs and local markdown link integrity.

Usage:
  python scripts/system/docs_finish_audit.py --json
  python scripts/system/docs_finish_audit.py --write-report artifacts/docs/doc_finish_audit.json
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

UNFINISHED_RE = re.compile(r"\b(TODO|TBD|WIP|FIXME|placeholder|to be configured)\b", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
EXCLUDE_PREFIXES = ("http://", "https://", "mailto:", "#")


@dataclass
class FileAudit:
    path: str
    unfinished_markers: int
    broken_local_links: list[str]


def _iter_docs(repo_root: Path, docs_dir: str = "docs") -> Iterable[Path]:
    root = repo_root / docs_dir
    if not root.exists():
        return []
    return sorted(root.rglob("*.md"))


def _is_local_link(link_target: str) -> bool:
    target = link_target.strip()
    return bool(target) and not target.startswith(EXCLUDE_PREFIXES)


def _normalize_link_target(raw: str) -> str:
    target = raw.strip()
    if "#" in target:
        target = target.split("#", 1)[0]
    return target


def _find_broken_links(md_path: Path) -> list[str]:
    content = md_path.read_text(encoding="utf-8", errors="replace")
    broken: list[str] = []
    for match in MARKDOWN_LINK_RE.finditer(content):
        raw_target = match.group(1)
        if not _is_local_link(raw_target):
            continue
        target = _normalize_link_target(raw_target)
        if not target:
            continue
        resolved = (md_path.parent / target).resolve()
        if not resolved.exists():
            broken.append(raw_target)
    return sorted(set(broken))


def audit_docs(repo_root: Path, docs_dir: str = "docs") -> dict[str, object]:
    files: list[FileAudit] = []
    total_markers = 0
    total_broken_links = 0
    for md in _iter_docs(repo_root, docs_dir):
        content = md.read_text(encoding="utf-8", errors="replace")
        markers = len(UNFINISHED_RE.findall(content))
        broken = _find_broken_links(md)
        if markers or broken:
            rel = md.resolve().relative_to(repo_root.resolve())
            files.append(
                FileAudit(
                    path=rel.as_posix(),
                    unfinished_markers=markers,
                    broken_local_links=broken,
                )
            )
        total_markers += markers
        total_broken_links += len(broken)
    files_sorted = sorted(files, key=lambda f: (f.unfinished_markers + len(f.broken_local_links)), reverse=True)
    return {
        "schema_version": "scbe_docs_finish_audit_v1",
        "files_scanned": len(list(_iter_docs(repo_root, docs_dir))),
        "files_with_findings": len(files_sorted),
        "unfinished_marker_total": total_markers,
        "broken_local_link_total": total_broken_links,
        "findings": [asdict(f) for f in files_sorted],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit docs for unfinished markers and broken local links")
    parser.add_argument("--repo-root", default=".", help="Repo root directory")
    parser.add_argument("--docs-dir", default="docs", help="Docs directory to scan")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    parser.add_argument("--write-report", default=None, help="Optional JSON report output path")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    report = audit_docs(repo_root=repo_root, docs_dir=args.docs_dir)

    if args.write_report:
        out_path = Path(args.write_report)
        if not out_path.is_absolute():
            out_path = repo_root / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"schema={report['schema_version']} scanned={report['files_scanned']} "
            f"findings={report['files_with_findings']} markers={report['unfinished_marker_total']} "
            f"broken_links={report['broken_local_link_total']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
