"""Catalog an explicit Git ancestry range without network access or repository mutation."""

from __future__ import annotations

import argparse
from collections import Counter
import html
import json
from pathlib import Path
import re
import subprocess

AREAS = (
    ("neural-sensors", ("src/ai_brain/", "src/symphonic_cipher/", "tests/ai_brain/")),
    ("crypto", ("src/crypto/", "src/spaceTor/", "src/harmonic/", "tests/crypto/", "tests/security/")),
    ("math-kernel", ("packages/kernel/", "src/kernel/", "src/scbe_14layer_reference.py", "formal/")),
    ("governance", ("src/governance/", "python/scbe/", "tests/governance/")),
    ("commerce", ("api/billing/", "netlify/")),
    ("workspace", ("src/aetherbrowser/", "aetherdesk/", "src/extension/", "scripts/aetherbrowser/")),
    ("api-storage", ("api/", "src/api/", "src/gateway/", "src/storage/", "services/")),
    ("agents", ("hydra/", "agents/", "mcp/", "packages/agent-bus-py/")),
    ("ci-release", (".github/", "Dockerfile", "docker-compose", "scripts/ci/", "scripts/security/")),
    ("research-training", ("training/", "training-data/", "datasets/", "research/", "notebooks/")),
    ("product-apps", ("desktop/", "apps/", "game/", "unity/")),
    ("dependencies", ("package.json", "package-lock.json", "pyproject.toml", "requirements")),
    ("docs-site", ("docs/", "public/", "README", "SYSTEM_", "START_HERE", "vercel.json")),
    ("archive", ("archive/", "external/", "external_repos/", ".gitmodules", "spiralverse-protocol/")),
    ("operator-tools", ("scripts/",)),
)


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "Git command failed")
    return result.stdout


def classify(path: str) -> str:
    if Path(path).name in {"package.json", "package-lock.json", "pyproject.toml", "uv.lock", "poetry.lock"}:
        return "dependencies"
    if path.startswith("symphonic_cipher/"):
        return "neural-sensors"
    for name, prefixes in AREAS:
        if path.startswith(prefixes):
            return name
    return "other-review-needed"


def build_catalog(repo: Path, repository: str, base: str, head: str) -> dict:
    """Include every reachable commit in base..head; mark first-parent landings."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("repository must be owner/name")
    for sha in (base, head):
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError("base and head must be full lowercase 40-character commit SHAs")
        if git(repo, "cat-file", "-t", sha).strip() != "commit":
            raise ValueError("base and head must name commits")
    git(repo, "merge-base", "--is-ancestor", base, head)
    commits = git(repo, "rev-list", "--reverse", "--topo-order", f"{base}..{head}").splitlines()
    landings = set(git(repo, "rev-list", "--first-parent", f"{base}..{head}").splitlines())
    shallow_file = Path(git(repo, "rev-parse", "--git-path", "shallow").strip())
    if not shallow_file.is_absolute():
        shallow_file = repo / shallow_file
    shallow = set(shallow_file.read_text().splitlines()) if shallow_file.exists() else set()
    if shallow.intersection(commits):
        raise ValueError("Selected range crosses a shallow history boundary; fetch missing history first")
    records = []
    all_paths = set()
    areas = Counter()
    for sha in commits:
        _, parents, date, subject = (
            git(repo, "show", "-s", "--format=%H%x00%P%x00%cI%x00%s", sha).strip().split("\0", 3)
        )
        parent_list = parents.split()
        if parent_list:
            changed = git(repo, "diff", "--no-renames", "--name-only", "-z", parent_list[0], sha, "--")
        else:
            changed = git(repo, "ls-tree", "-r", "--name-only", "-z", sha)
        paths = sorted(set(filter(None, changed.split("\0"))))
        names = sorted({classify(path) for path in paths})
        areas.update(names)
        all_paths.update(paths)
        records.append(
            {
                "sha": sha,
                "parents": parent_list,
                "committed_at": date,
                "subject": subject,
                "mainline_landing": sha in landings,
                "areas": names,
                "paths": paths,
                "url": f"https://github.com/{repository}/commit/{sha}",
            }
        )
    return {
        "schema": "scbe-change-catalog-v1",
        "repository": repository,
        "base_exclusive": base,
        "head_inclusive": head,
        "commit_count": len(records),
        "first_parent_landing_count": len(landings),
        "unique_changed_paths": len(all_paths),
        "area_commit_counts_overlapping": dict(sorted(areas.items())),
        "semantics": (
            "All reachable commits in base..head; first-parent landings marked separately. "
            "Paths compare each commit with its first parent; area counts overlap. "
            "Commit timestamps are not deployment timestamps. Classification is heuristic, "
            "and the complete path lists require human review."
        ),
        "commits": records,
    }


def safe_cell(value: str) -> str:
    return html.escape(value).replace("|", "&#124;").replace("@", "&#64;").replace(chr(96), "&#96;").replace("\n", " ")


def render_markdown(catalog: dict) -> str:
    lines = [
        "# Commit catalog",
        "",
        f"Repository: {catalog['repository']}",
        "",
        f"Base (excluded): {catalog['base_exclusive']}",
        "",
        f"Head (included): {catalog['head_inclusive']}",
        "",
        f"Commits: {catalog['commit_count']}; first-parent landings: {catalog['first_parent_landing_count']}; "
        f"unique changed paths: {catalog['unique_changed_paths']}.",
        "",
        catalog["semantics"],
        "",
        "This is an inventory. See the companion history review for verified behavior changes and remaining evidence.",
        "",
        "| Commit | Committed at | Mainline landing | Areas | Subject |",
        "| --- | --- | --- | --- | --- |",
    ]
    for record in catalog["commits"]:
        lines.append(
            f"| [{record['sha'][:10]}]({record['url']}) | {safe_cell(record['committed_at'])} | "
            f"{'yes' if record['mainline_landing'] else 'no'} | {safe_cell(', '.join(record['areas']))} | "
            f"{safe_cell(record['subject'])} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--repository", required=True, help="GitHub owner/name used for links")
    parser.add_argument("--base", required=True, help="Excluded full commit SHA")
    parser.add_argument("--head", required=True, help="Included full commit SHA")
    parser.add_argument("--output", type=Path, required=True, help="Output prefix; writes .json and .md")
    args = parser.parse_args()
    try:
        catalog = build_catalog(args.repo.resolve(), args.repository, args.base, args.head)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(json.dumps(catalog, indent=2) + "\n")
    args.output.with_suffix(".md").write_text(render_markdown(catalog))


if __name__ == "__main__":
    main()
