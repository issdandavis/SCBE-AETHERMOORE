from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "repo-ordering"
MANIFEST_CANDIDATES = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.toml",
    "docker-compose.yml",
)

ROOT_RULES: dict[str, tuple[str, str]] = {
    "src": ("canonical", "Primary monorepo source root."),
    "tests": ("canonical", "Primary test authority across TypeScript and Python."),
    "docs": ("canonical", "Documentation and architecture notes."),
    "scripts": ("canonical", "Operational and validation tooling."),
    "config": ("canonical", "Shared configuration and environment templates."),
    "schemas": ("canonical", "Shared schemas and cross-surface contracts."),
    "api": ("subproject-local", "Top-level service lane; overlaps with src/api and needs boundary discipline."),
    "app": ("subproject-local", "Top-level application lane outside src/."),
    "conference-app": ("subproject-local", "Standalone application/package root."),
    "dashboard": ("subproject-local", "Dashboard/UI package root."),
    "hydra": ("subproject-local", "HYDRA orchestration surface."),
    "mcp": ("subproject-local", "MCP server surface."),
    "packages": ("subproject-local", "Workspace-local package grouping."),
    "python": ("subproject-local", "Dedicated Python package/runtime lane."),
    "services": ("subproject-local", "Service runtime surface."),
    "shopify": ("subproject-local", "Shopify integration surface."),
    "skills": ("subproject-local", "Skill assets and prompts."),
    "ui": ("subproject-local", "Top-level UI surface."),
    "workflows": ("subproject-local", "Workflow definitions and bridges."),
    "assets": ("content-publishing", "Shared static assets."),
    "articles": ("content-publishing", "Published article drafts/content."),
    "content": ("content-publishing", "Primary publishing and book/content surface."),
    "notes": ("content-publishing", "Working notes and planning content."),
    "paper": ("content-publishing", "Paper/manuscript lane."),
    "plugins": ("content-publishing", "Plugin and card assets."),
    "policies": ("content-publishing", "Policy text and governance content."),
    "products": ("content-publishing", "Productization assets."),
    "public": ("content-publishing", "Public web/static publishing assets."),
    "aether-browser": ("legacy-readonly", "Older browser root; overlaps with newer browser surfaces."),
    "scbe-aethermoore": ("legacy-readonly", "Nested/duplicate repo-style surface under the monorepo root."),
    "symphonic_cipher": ("legacy-readonly", "Legacy duplicate of src/symphonic_cipher."),
    "SCBE-AETHERMOORE-v3.0.0": ("archive-snapshot", "Version snapshot/archive root."),
    "spiralverse-protocol": ("archive-snapshot", "Protocol snapshot/archive root."),
    "external": ("external-vendored", "External material staged inside the repo."),
    "external_repos": ("external-vendored", "Vendored or mirrored repositories."),
    "experimental": ("research-experimental", "Experimental workbench lane."),
    "experiments": ("research-experimental", "Experimental workbench lane."),
    "examples": ("research-experimental", "Example/demo implementations."),
    "game": ("research-experimental", "Game-specific experiment lane."),
    "godot": ("research-experimental", "Game engine experiment lane."),
    "notebooks": ("research-experimental", "Notebook/prototyping lane."),
    "phdm-21d-embedding": ("research-experimental", "PHDM/21D research lane."),
    "physics_sim": ("research-experimental", "Physics simulation experiments."),
    "proto": ("research-experimental", "Prototype lane."),
    "prototype": ("research-experimental", "Prototype lane."),
    "__pycache__": ("generated-runtime", "Python cache output."),
    ".benchmarks": ("generated-runtime", "Benchmark outputs."),
    ".n8n_local_iso": ("generated-runtime", "Local n8n runtime cache/output."),
    ".playwright-cli": ("generated-runtime", "Playwright runtime cache."),
    ".playwright-mcp": ("generated-runtime", "Playwright MCP runtime cache."),
    ".pytest_cache": ("generated-runtime", "Pytest cache output."),
    ".pytest_tmp_hallpass_review": ("generated-runtime", "Pytest temp output."),
    ".streamlit": ("generated-runtime", "Local Streamlit runtime state."),
    ".tmp-codex-home": ("generated-runtime", "Temporary Codex home/runtime cache."),
    "artifacts": ("generated-runtime", "Generated reports, runs, and build/test outputs."),
    "backups": ("generated-runtime", "Backups and snapshots."),
    "dist": ("generated-runtime", "Compiled distribution output."),
    "exports": ("generated-runtime", "Generated exports and external dumps."),
    "lambda_package": ("generated-runtime", "Packaged Lambda output."),
    "node_modules": ("generated-runtime", "Installed Node dependencies."),
    "sealed_blobs": ("generated-runtime", "Generated sealed outputs."),
    "training": ("generated-runtime", "Training artifacts and generated corpora/output."),
    "training-data": ("generated-runtime", "Training data and corpora."),
    ".claude": ("workspace-meta", "Assistant-local metadata and skills."),
    ".codex-plan-check": ("workspace-meta", "Codex planning state."),
    ".devcontainer": ("workspace-meta", "Devcontainer/editor metadata."),
    ".firebase": ("workspace-meta", "Firebase workspace metadata."),
    ".github": ("workspace-meta", "GitHub workflow and repo automation metadata."),
    ".grok": ("workspace-meta", "Assistant-local metadata."),
    ".kiro": ("workspace-meta", "Editor/workspace metadata."),
    ".scbe": ("workspace-meta", "Local SCBE runtime metadata."),
    ".vscode": ("workspace-meta", "Editor workspace settings."),
}

ROOT_FILE_RULES: dict[str, tuple[str, str]] = {
    "AGENTS.md": ("canonical", "Repository operating instructions."),
    "ARCHITECTURE.md": ("canonical", "Root architecture surface."),
    "CLAUDE.md": ("canonical", "Assistant/repo operating surface."),
    "INSTRUCTIONS.md": ("canonical", "Root implementation guidance."),
    "README.md": ("canonical", "Primary repo overview."),
    "package.json": ("canonical", "Root Node manifest."),
    "pyproject.toml": ("canonical", "Root Python manifest."),
    "pytest.ini": ("canonical", "Root pytest authority."),
    "requirements-lock.txt": ("canonical", "Root Python lock surface."),
    "requirements.txt": ("canonical", "Root Python dependency surface."),
    "tsconfig.json": ("canonical", "Root TypeScript config."),
    "vitest.config.ts": ("canonical", "Root TS test config."),
}

CATEGORY_POLICY: dict[str, tuple[str, str]] = {
    "canonical": ("keep-active", "github-monorepo"),
    "subproject-local": ("keep-scoped", "github-monorepo"),
    "content-publishing": ("keep-and-publish", "github-monorepo"),
    "legacy-readonly": ("archive-or-extract", "github-archive-or-cloud"),
    "archive-snapshot": ("remove-from-active-tree", "cloud-archive"),
    "external-vendored": ("vendor-or-archive", "cloud-archive"),
    "research-experimental": ("curate-before-promote", "github-or-huggingface"),
    "generated-runtime": ("export-and-ignore", "cloud-or-huggingface"),
    "workspace-meta": ("keep-local-only", "local-workspace"),
    "unknown": ("manual-review", "undecided"),
    "root-file": ("manual-review", "github-monorepo"),
}

ENTRY_POLICY_OVERRIDES: dict[str, tuple[str, str]] = {
    "artifacts": ("export-and-ignore", "cloud-archive"),
    "training": ("export-and-ignore", "cloud-archive"),
    "training-data": ("curate-before-promote", "huggingface-dataset"),
    "notes": ("keep-and-publish", "github-and-obsidian"),
    "notebooks": ("curate-before-promote", "github-and-colab"),
    "external": ("vendor-or-archive", "cloud-archive"),
    ".n8n_local_iso": ("export-and-ignore", "local-runtime-only"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Snapshot the SCBE monorepo ordering baseline.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root to inspect.")
    parser.add_argument("--out-dir", default=str(ARTIFACT_DIR), help="Directory for JSON artifacts.")
    return parser.parse_args()


def run(cmd: list[str], cwd: Path) -> str:
    completed = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
    return completed.stdout


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def normalize_status_path(raw: str) -> str:
    path = raw.strip()
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    return path.replace("\\", "/")


def collect_dirty_counts(repo_root: Path) -> Counter[str]:
    stdout = run(["git", "status", "--short", "--untracked-files=all"], cwd=repo_root)
    counts: Counter[str] = Counter()
    for line in stdout.splitlines():
        if len(line) < 4:
            continue
        path = normalize_status_path(line[3:])
        top = path.split("/", 1)[0]
        counts[top] += 1
    return counts


def parse_worktrees(repo_root: Path) -> list[dict[str, Any]]:
    stdout = run(["git", "worktree", "list", "--porcelain"], cwd=repo_root)
    blocks = [block for block in stdout.strip().split("\n\n") if block.strip()]
    worktrees: list[dict[str, Any]] = []
    for block in blocks:
        row: dict[str, Any] = {
            "path": "",
            "head": "",
            "branch": None,
            "detached": False,
            "locked": False,
            "locked_reason": None,
        }
        for line in block.splitlines():
            if line.startswith("worktree "):
                row["path"] = line.removeprefix("worktree ").strip()
            elif line.startswith("HEAD "):
                row["head"] = line.removeprefix("HEAD ").strip()
            elif line.startswith("branch "):
                row["branch"] = line.removeprefix("branch ").strip()
            elif line == "detached":
                row["detached"] = True
            elif line.startswith("locked"):
                row["locked"] = True
                reason = line.removeprefix("locked").strip()
                row["locked_reason"] = reason or None
        worktrees.append(row)
    return worktrees


def parse_root_commits(repo_root: Path, *, all_refs: bool) -> list[dict[str, Any]]:
    cmd = ["git", "rev-list", "--max-parents=0"]
    if all_refs:
        cmd.append("--all")
    else:
        cmd.append("HEAD")
    stdout = run(cmd, cwd=repo_root)
    commits = [line.strip() for line in stdout.splitlines() if line.strip()]
    rows: list[dict[str, Any]] = []
    for commit in commits:
        summary = run(
            ["git", "show", "--no-patch", "--format=%H%n%ad%n%an%n%s", commit],
            cwd=repo_root,
        ).splitlines()
        tree_preview = run(["git", "ls-tree", "--name-only", commit], cwd=repo_root).splitlines()
        rows.append(
            {
                "commit": summary[0],
                "date": summary[1],
                "author": summary[2],
                "subject": summary[3],
                "tree_preview": tree_preview[:20],
            }
        )
    return rows


def parse_shallow_boundaries(repo_root: Path) -> list[str]:
    shallow_file = repo_root / ".git" / "shallow"
    if not shallow_file.exists():
        return []
    return [line.strip() for line in shallow_file.read_text(encoding="utf-8").splitlines() if line.strip()]


def classify_root(entry: Path) -> tuple[str, str]:
    if entry.is_dir():
        if entry.name in ROOT_RULES:
            return ROOT_RULES[entry.name]
        if entry.name.startswith("."):
            return ("workspace-meta", "Hidden workspace/editor/runtime directory.")
        return ("unknown", "Unclassified top-level directory; needs manual review.")

    if entry.name in ROOT_FILE_RULES:
        return ROOT_FILE_RULES[entry.name]
    if entry.name.startswith("."):
        return ("workspace-meta", "Hidden workspace or tooling file.")
    return ("root-file", "Root-level file outside the canonical manifest set.")


def collect_manifests(entry: Path) -> list[str]:
    if not entry.is_dir():
        return []
    manifests = [name for name in MANIFEST_CANDIDATES if (entry / name).exists()]
    return sorted(manifests)


def approximate_size_bytes(entry: Path) -> int:
    if entry.is_file():
        try:
            return entry.stat().st_size
        except OSError:
            return 0

    total = 0
    try:
        for child in entry.rglob("*"):
            if not child.is_file():
                continue
            try:
                total += child.stat().st_size
            except OSError:
                continue
    except OSError:
        return total
    return total


def policy_for_entry(entry_name: str, category: str) -> tuple[str, str]:
    if entry_name in ENTRY_POLICY_OVERRIDES:
        return ENTRY_POLICY_OVERRIDES[entry_name]
    return CATEGORY_POLICY.get(category, ("manual-review", "undecided"))


def collect_root_entries(repo_root: Path, dirty_counts: Counter[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for entry in sorted(repo_root.iterdir(), key=lambda item: item.name.lower()):
        if entry.name == ".git":
            continue
        category, reason = classify_root(entry)
        action, export_target = policy_for_entry(entry.name, category)
        size_bytes = approximate_size_bytes(entry)
        entries.append(
            {
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "category": category,
                "reason": reason,
                "recommended_action": action,
                "recommended_export_target": export_target,
                "dirty_count": dirty_counts.get(entry.name, 0),
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "manifests": collect_manifests(entry),
                "last_modified_utc": datetime.fromtimestamp(entry.stat().st_mtime, timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
            }
        )
    return entries


def build_payload(repo_root: Path) -> dict[str, Any]:
    dirty_counts = collect_dirty_counts(repo_root)
    root_entries = collect_root_entries(repo_root, dirty_counts)
    category_counts = Counter(entry["category"] for entry in root_entries)
    largest_entries = [
        {
            "name": entry["name"],
            "category": entry["category"],
            "size_mb": entry["size_mb"],
            "recommended_action": entry["recommended_action"],
            "recommended_export_target": entry["recommended_export_target"],
        }
        for entry in sorted(root_entries, key=lambda row: row["size_bytes"], reverse=True)[:20]
    ]
    dirty_hotspots = [{"name": name, "dirty_count": count} for name, count in dirty_counts.most_common(25)]

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root).strip()
    shallow = run(["git", "rev-parse", "--is-shallow-repository"], cwd=repo_root).strip() == "true"
    head_root_commits = parse_root_commits(repo_root, all_refs=False)
    repo_root_commits = parse_root_commits(repo_root, all_refs=True)

    return {
        "generated_utc": utc_now(),
        "repo_root": str(repo_root),
        "branch": branch,
        "is_shallow_repository": shallow,
        "shallow_boundaries": parse_shallow_boundaries(repo_root),
        "head_root_commit_count": len(head_root_commits),
        "head_root_commits": head_root_commits,
        "repo_root_commit_count": len(repo_root_commits),
        "repo_root_commits": repo_root_commits,
        "category_counts": dict(category_counts),
        "largest_entries": largest_entries,
        "dirty_hotspots": dirty_hotspots,
        "worktrees": parse_worktrees(repo_root),
        "root_entries": root_entries,
    }


def write_outputs(payload: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamped = out_dir / f"repo_ordering_{timestamp_slug()}.json"
    latest = out_dir / "latest.json"
    encoded = json.dumps(payload, indent=2)
    stamped.write_text(encoded, encoding="utf-8")
    latest.write_text(encoded, encoding="utf-8")
    return stamped, latest


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    out_dir = Path(args.out_dir).resolve()

    payload = build_payload(repo_root)
    stamped, latest = write_outputs(payload, out_dir)

    print(f"repo_root={repo_root}")
    print(f"branch={payload['branch']}")
    print(f"is_shallow_repository={payload['is_shallow_repository']}")
    print(f"head_root_commit_count={payload['head_root_commit_count']}")
    print(f"repo_root_commit_count={payload['repo_root_commit_count']}")
    print("largest_entries=")
    for row in payload["largest_entries"][:10]:
        print(
            f"  {row['size_mb']:>8.2f} MB  {row['name']}  "
            f"({row['category']} -> {row['recommended_action']} -> {row['recommended_export_target']})"
        )
    print("top_dirty_hotspots=")
    for row in payload["dirty_hotspots"][:10]:
        print(f"  {row['dirty_count']:>5}  {row['name']}")
    print(f"wrote={stamped}")
    print(f"latest={latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
