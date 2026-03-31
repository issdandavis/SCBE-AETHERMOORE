#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXACT_KEEP = {"main", "master", "gh-pages"}
DEFAULT_KEEP_PATTERNS = ["release/*", "hotfix/*", "overnight/*"]
DEFAULT_REVIEW_PATTERNS = ["backup/*", "dependabot/*", "claude/*", "copilot/*", "issdandavis-patch-*"]
DEFAULT_BASE_BRANCHES = ["main", "overnight/2026-03-30"]


@dataclass(frozen=True)
class BranchDecision:
    branch: str
    category: str
    reason: str
    merged_into: list[str]
    pr_numbers: list[int]
    url: str | None


@dataclass(frozen=True)
class PullRequestHead:
    number: int
    title: str
    url: str
    head_ref: str
    base_ref: str
    is_draft: bool


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)


def parse_owner_repo(remote_url: str) -> str | None:
    value = remote_url.strip()
    if not value:
        return None
    if "@" in value and "://" in value:
        scheme, remainder = value.split("://", 1)
        value = f"{scheme}://{remainder.split('@', 1)[1]}"
    if value.startswith("git@"):
        value = value.split(":", 1)[1]
    if "://" in value:
        value = value.split("://", 1)[1]
        value = value.split("/", 1)[1] if "/" in value else value
    value = value.removesuffix(".git").strip("/")
    if value.count("/") >= 1:
        parts = value.split("/")
        return f"{parts[-2]}/{parts[-1]}"
    return None


def parse_remote_branches(raw: str, remote: str) -> list[str]:
    names: list[str] = []
    prefix = f"{remote}/"
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if " " in line:
            line = line.split(" ", 1)[0]
        if line.startswith(prefix):
            name = line[len(prefix) :]
            if name != "HEAD":
                names.append(name)
    return sorted(set(names))


def parse_branch_listing(raw: str, remote: str | None = None) -> list[str]:
    names: list[str] = []
    prefix = f"{remote}/" if remote else ""
    for line in raw.splitlines():
        line = line.strip().replace("*", "")
        if not line:
            continue
        if prefix:
            if line.startswith(prefix):
                names.append(line[len(prefix) :].strip())
        else:
            names.append(line.strip())
    return sorted(set(names))


def parse_pull_request_heads(raw: str) -> list[PullRequestHead]:
    if not raw.strip():
        return []
    data = json.loads(raw)
    heads: list[PullRequestHead] = []
    for row in data:
        heads.append(
            PullRequestHead(
                number=int(row["number"]),
                title=str(row.get("title", "")),
                url=str(row.get("url", "")),
                head_ref=str(row.get("headRefName", "")),
                base_ref=str(row.get("baseRefName", "")),
                is_draft=bool(row.get("isDraft", False)),
            )
        )
    return heads


def branch_is_protected(
    branch: str,
    current_branch: str,
    exact_keep: set[str],
    keep_patterns: list[str],
) -> bool:
    if branch == current_branch:
        return True
    if branch in exact_keep:
        return True
    return any(fnmatch(branch, pattern) for pattern in keep_patterns)


def branch_requires_review(branch: str, review_patterns: list[str]) -> bool:
    return any(fnmatch(branch, pattern) for pattern in review_patterns)


def build_browser_targets(owner_repo: str | None, repo: str, safe_delete: list[BranchDecision]) -> dict[str, Any]:
    if not owner_repo:
        return {"enabled": False, "reason": "origin remote could not be resolved"}
    base = f"https://github.com/{owner_repo}"
    return {
        "enabled": True,
        "repo_url": base,
        "branches_url": f"{base}/branches",
        "pulls_url": f"{base}/pulls",
        "commands": [
            "python C:\\Users\\issda\\SCBE-AETHERMOORE\\scripts\\system\\browser_chain_dispatcher.py --domain github.com --task navigate --engine playwriter",
            f"python C:\\Users\\issda\\SCBE-AETHERMOORE\\scripts\\system\\playwriter_lane_runner.py --session 1 --url {base}/branches --task navigate",
            f"python C:\\Users\\issda\\SCBE-AETHERMOORE\\scripts\\system\\playwriter_lane_runner.py --session 1 --url {base}/pulls --task snapshot",
        ],
        "recommended_visual_checks": [
            "Verify branch protection and deletion controls on the branches page.",
            "Confirm open PR heads match the retained branches on the pulls page.",
            f"Manually review the {len(safe_delete)} safe-delete candidate(s) before executing remote deletion.",
        ],
    }


def classify_branches(
    remote_branches: list[str],
    merged_into: dict[str, list[str]],
    open_prs: list[PullRequestHead],
    current_branch: str,
    owner_repo: str | None,
    exact_keep: set[str],
    keep_patterns: list[str],
    review_patterns: list[str],
) -> dict[str, list[BranchDecision]]:
    open_pr_map: dict[str, list[int]] = {}
    for pr in open_prs:
        open_pr_map.setdefault(pr.head_ref, []).append(pr.number)

    safe_delete: list[BranchDecision] = []
    keep: list[BranchDecision] = []
    review: list[BranchDecision] = []

    for branch in remote_branches:
        merged_bases = [base for base, names in merged_into.items() if branch in names]
        url = f"https://github.com/{owner_repo}/tree/{branch}" if owner_repo else None

        if branch_is_protected(branch, current_branch, exact_keep, keep_patterns):
            keep.append(
                BranchDecision(
                    branch=branch,
                    category="keep",
                    reason="protected branch",
                    merged_into=merged_bases,
                    pr_numbers=open_pr_map.get(branch, []),
                    url=url,
                )
            )
            continue

        if branch in open_pr_map:
            keep.append(
                BranchDecision(
                    branch=branch,
                    category="keep",
                    reason="open pull request head",
                    merged_into=merged_bases,
                    pr_numbers=open_pr_map.get(branch, []),
                    url=url,
                )
            )
            continue

        if merged_bases and not branch_requires_review(branch, review_patterns):
            safe_delete.append(
                BranchDecision(
                    branch=branch,
                    category="safe-delete",
                    reason="merged into canonical branch and not protected",
                    merged_into=merged_bases,
                    pr_numbers=[],
                    url=url,
                )
            )
            continue

        reason = "merged but matched manual-review pattern" if merged_bases else "not merged into canonical branch"
        review.append(
            BranchDecision(
                branch=branch,
                category="manual-review",
                reason=reason,
                merged_into=merged_bases,
                pr_numbers=[],
                url=url,
            )
        )

    return {
        "keep": sorted(keep, key=lambda row: row.branch),
        "safe_delete": sorted(safe_delete, key=lambda row: row.branch),
        "manual_review": sorted(review, key=lambda row: row.branch),
    }


def build_delete_commands(remote: str, safe_delete: list[BranchDecision]) -> list[str]:
    return [f"git push {remote} --delete {row.branch}" for row in safe_delete]


def find_external_pr_heads(open_prs: list[PullRequestHead], remote_branches: list[str]) -> list[PullRequestHead]:
    remote_branch_set = set(remote_branches)
    return [pr for pr in open_prs if pr.head_ref not in remote_branch_set]


def detect_sensitive_reachability(repo_root: Path, shas: list[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for sha in shas:
        proc = run(["git", "branch", "-r", "--contains", sha], cwd=repo_root)
        branches = parse_branch_listing(proc.stdout) if proc.returncode == 0 else []
        findings.append(
            {
                "sha": sha,
                "reachable_branches": branches,
                "ok": proc.returncode == 0,
                "stderr": proc.stderr.strip()[-600:],
            }
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit GitHub branch/PR state and emit a safe cleanup plan.")
    parser.add_argument("--repo-root", default=".", help="Target repo root.")
    parser.add_argument("--remote", default="origin", help="Remote to audit.")
    parser.add_argument(
        "--base-branch",
        action="append",
        default=[],
        help="Canonical branches used to decide merged/safe-delete state. Repeat for multiple branches.",
    )
    parser.add_argument("--keep-pattern", action="append", default=[], help="Extra protected branch glob.")
    parser.add_argument("--review-pattern", action="append", default=[], help="Extra manual-review branch glob.")
    parser.add_argument("--sensitive-sha", action="append", default=[], help="Commit SHA that should not be reachable.")
    parser.add_argument("--skip-gh", action="store_true", help="Skip gh PR discovery even if available.")
    parser.add_argument("--json", action="store_true", help="Print full JSON report.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    base_branches = args.base_branch or list(DEFAULT_BASE_BRANCHES)
    keep_patterns = list(DEFAULT_KEEP_PATTERNS) + list(args.keep_pattern)
    review_patterns = list(DEFAULT_REVIEW_PATTERNS) + list(args.review_pattern)

    current_branch_proc = run(["git", "branch", "--show-current"], cwd=repo_root)
    current_branch = current_branch_proc.stdout.strip() or "unknown"

    remote_url_proc = run(["git", "remote", "get-url", args.remote], cwd=repo_root)
    remote_url = remote_url_proc.stdout.strip()
    owner_repo = parse_owner_repo(remote_url)

    refs_proc = run(["git", "for-each-ref", f"refs/remotes/{args.remote}", "--format=%(refname:short)"], cwd=repo_root)
    remote_branches = parse_remote_branches(refs_proc.stdout, args.remote)

    merged_into: dict[str, list[str]] = {}
    for base in base_branches:
        proc = run(["git", "branch", "-r", "--merged", f"{args.remote}/{base}"], cwd=repo_root)
        merged_into[base] = parse_branch_listing(proc.stdout, args.remote) if proc.returncode == 0 else []

    open_prs: list[PullRequestHead] = []
    gh_status: dict[str, Any] = {"enabled": False, "stderr": "", "return_code": None}
    if not args.skip_gh:
        pr_proc = run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--limit",
                "200",
                "--json",
                "number,title,url,headRefName,baseRefName,isDraft",
            ],
            cwd=repo_root,
        )
        gh_status = {
            "enabled": pr_proc.returncode == 0,
            "return_code": pr_proc.returncode,
            "stderr": pr_proc.stderr.strip()[-1200:],
        }
        if pr_proc.returncode == 0:
            open_prs = parse_pull_request_heads(pr_proc.stdout)

    classifications = classify_branches(
        remote_branches=remote_branches,
        merged_into=merged_into,
        open_prs=open_prs,
        current_branch=current_branch,
        owner_repo=owner_repo,
        exact_keep=set(DEFAULT_EXACT_KEEP) | set(base_branches),
        keep_patterns=keep_patterns,
        review_patterns=review_patterns,
    )
    external_pr_heads = [asdict(pr) for pr in find_external_pr_heads(open_prs, remote_branches)]

    sensitive_findings = detect_sensitive_reachability(repo_root, args.sensitive_sha) if args.sensitive_sha else []
    browser = build_browser_targets(owner_repo, repo_root.name, classifications["safe_delete"])

    report = {
        "generated_at_utc": utc_now(),
        "repo_root": str(repo_root),
        "repo": owner_repo,
        "remote": args.remote,
        "current_branch": current_branch,
        "base_branches": base_branches,
        "keep_patterns": keep_patterns,
        "review_patterns": review_patterns,
        "gh": gh_status,
        "open_prs": [asdict(pr) for pr in open_prs],
        "external_or_missing_open_pr_heads": external_pr_heads,
        "classifications": {key: [asdict(row) for row in rows] for key, rows in classifications.items()},
        "safe_delete_commands": build_delete_commands(args.remote, classifications["safe_delete"]),
        "sensitive_reachability": sensitive_findings,
        "browser": browser,
        "counts": {key: len(rows) for key, rows in classifications.items()},
    }

    output_dir = repo_root / "artifacts" / "github-control"
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "github_control_latest.json"
    latest_md = output_dir / "github_control_latest.md"
    latest_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# GitHub Control Plane Report",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Repo: `{owner_repo or repo_root.name}`",
        f"- Remote: `{args.remote}`",
        f"- Current branch: `{current_branch}`",
        f"- Canonical branches: `{', '.join(base_branches)}`",
        f"- Open PRs discovered: `{len(open_prs)}`",
        f"- Open PR heads not present on `{args.remote}`: `{len(external_pr_heads)}`",
        f"- Keep: `{report['counts']['keep']}`",
        f"- Safe delete: `{report['counts']['safe_delete']}`",
        f"- Manual review: `{report['counts']['manual_review']}`",
        "",
        "## Safe Delete Candidates",
    ]
    if classifications["safe_delete"]:
        for row in classifications["safe_delete"]:
            lines.append(f"- `{row.branch}` — merged into `{', '.join(row.merged_into)}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Manual Review", ""])
    if classifications["manual_review"]:
        for row in classifications["manual_review"][:25]:
            lines.append(f"- `{row.branch}` — {row.reason}")
    else:
        lines.append("- none")
    if sensitive_findings:
        lines.extend(["", "## Sensitive Reachability", ""])
        for finding in sensitive_findings:
            branches = ", ".join(finding["reachable_branches"]) if finding["reachable_branches"] else "none"
            lines.append(f"- `{finding['sha']}` -> `{branches}`")
    if external_pr_heads:
        lines.extend(["", "## PR Heads Outside Origin", ""])
        for pr in external_pr_heads:
            lines.append(f"- `#{pr['number']}` `{pr['head_ref']}` -> `{pr['base_ref']}`")
    latest_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(json.dumps({"ok": True, "report": str(latest_json), "counts": report["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
