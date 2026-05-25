#!/usr/bin/env python3
"""Audit SCBE repo branches, deploy surfaces, and docs-to-code candidates.

This is intentionally local and read-only. It records enough structure to make
GitHub cleanup repeatable without guessing which branch or deployment surface
matters.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]


def run_git(args: list[str]) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True, stderr=subprocess.DEVNULL)


def remote_branches() -> list[str]:
    lines = run_git(["branch", "-r", "--format=%(refname:short)"]).splitlines()
    return sorted(
        line.strip()
        for line in lines
        if line.strip()
        and not line.strip().endswith("/HEAD")
        and line.strip() not in {"origin/main", "origin/gh-pages"}
    )


def branches_merged_into_main() -> set[str]:
    try:
        lines = run_git(["branch", "-r", "--merged", "origin/main", "--format=%(refname:short)"]).splitlines()
    except subprocess.CalledProcessError:
        return set()
    return {line.strip() for line in lines if line.strip()}


def prefix_of(branch: str) -> str:
    name = branch.split("/", 1)[1] if "/" in branch else branch
    return name.split("/", 1)[0]


def safe_delete_candidate(branch: str, merged: set[str]) -> bool:
    if branch not in merged:
        return False
    name = branch.split("/", 1)[1] if "/" in branch else branch
    if name.startswith(("backup/", "archive/", "snapshot/", "recovery/")):
        return False
    return True


def interesting_files(patterns: Iterable[str]) -> list[str]:
    found: list[str] = []
    for pattern in patterns:
        found.extend(str(path.relative_to(ROOT)) for path in ROOT.glob(pattern) if path.is_file())
    return sorted(set(found))


def classify_deploy_file(path: str) -> str:
    lower = path.lower()
    if ".github/workflows/" in lower:
        return "github-actions"
    if "docker" in lower or lower.endswith("dockerfile"):
        return "docker"
    if lower.startswith("k8s/") or "kubernetes" in lower:
        return "kubernetes"
    if "gcloud" in lower or "cloudrun" in lower:
        return "gcloud"
    if "vercel" in lower:
        return "vercel"
    if "deploy" in lower:
        return "deploy-script"
    return "other"


def docs_to_code_candidates(limit: int = 80) -> list[dict[str, str]]:
    patterns = [
        "TODO",
        "stub",
        "placeholder",
        "not implemented",
        "manual",
    ]
    candidates: list[dict[str, str]] = []
    roots = ["docs", "scripts", "src", "packages"]
    for root_name in roots:
        root = ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if len(candidates) >= limit:
                return candidates
            if path.suffix.lower() not in {".md", ".py", ".ts", ".js", ".mjs", ".tsx"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                lower = line.lower()
                if any(pattern in lower for pattern in patterns):
                    candidates.append(
                        {
                            "path": str(path.relative_to(ROOT)),
                            "line": str(line_no),
                            "text": line.strip()[:220],
                        }
                    )
                    break
    return candidates


def build_report() -> dict[str, object]:
    branches = remote_branches()
    merged = branches_merged_into_main()
    deploy_files = interesting_files(
        [
            ".github/workflows/*.yml",
            ".github/workflows/*.yaml",
            "Dockerfile*",
            "docker-compose*.yml",
            "docker-compose*.yaml",
            "deploy/**/*",
            "k8s/**/*",
            "scripts/**/*deploy*",
            "scripts/**/*docker*",
        ]
    )

    deploy_by_kind: dict[str, list[str]] = defaultdict(list)
    for path in deploy_files:
        deploy_by_kind[classify_deploy_file(path)].append(path)

    prefix_counts = Counter(prefix_of(branch) for branch in branches if branch.startswith("origin/"))
    delete_candidates = [branch for branch in branches if branch.startswith("origin/") and safe_delete_candidate(branch, merged)]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": str(ROOT),
        "branch_counts": {
            "remote_total_excluding_main_pages": len(branches),
            "merged_into_origin_main": len([b for b in branches if b in merged]),
            "safe_delete_candidates": len(delete_candidates),
        },
        "remote_branch_prefix_counts": dict(sorted(prefix_counts.items(), key=lambda item: (-item[1], item[0]))),
        "safe_delete_candidates": delete_candidates,
        "deployment_surface_counts": {kind: len(paths) for kind, paths in sorted(deploy_by_kind.items())},
        "deployment_surfaces": {kind: sorted(paths) for kind, paths in sorted(deploy_by_kind.items())},
        "docs_to_code_candidates": docs_to_code_candidates(),
    }


def write_markdown(report: dict[str, object], path: Path) -> None:
    lines = [
        "# GitHub Branch and Deployment Surface Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Repo: `{report['repo']}`",
        "",
        "## Branch Counts",
        "",
    ]
    counts = report["branch_counts"]
    assert isinstance(counts, dict)
    for key, value in counts.items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Remote Branch Prefixes", ""])
    prefixes = report["remote_branch_prefix_counts"]
    assert isinstance(prefixes, dict)
    for key, value in prefixes.items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Safe Delete Candidates", ""])
    delete_candidates = report["safe_delete_candidates"]
    assert isinstance(delete_candidates, list)
    if delete_candidates:
        lines.extend(f"- `{item}`" for item in delete_candidates)
    else:
        lines.append("- None at generation time.")
    lines.extend(["", "## Deployment Surfaces", ""])
    surfaces = report["deployment_surfaces"]
    assert isinstance(surfaces, dict)
    for kind, paths in surfaces.items():
        lines.append(f"### {kind}")
        assert isinstance(paths, list)
        for item in paths[:80]:
            lines.append(f"- `{item}`")
        if len(paths) > 80:
            lines.append(f"- ... {len(paths) - 80} more")
        lines.append("")
    lines.extend(["## Docs-To-Code Candidates", ""])
    candidates = report["docs_to_code_candidates"]
    assert isinstance(candidates, list)
    for item in candidates[:80]:
        assert isinstance(item, dict)
        lines.append(f"- `{item['path']}:{item['line']}` {item['text']}")
    if not candidates:
        lines.append("- None found.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", default="artifacts/repo-audit/github-branch-deploy-audit.json")
    parser.add_argument("--md-out", default="docs/operations/github-branch-deploy-audit.md")
    args = parser.parse_args()

    report = build_report()
    json_path = ROOT / args.json_out
    md_path = ROOT / args.md_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(report, md_path)
    print(f"wrote {json_path.relative_to(ROOT)}")
    print(f"wrote {md_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
