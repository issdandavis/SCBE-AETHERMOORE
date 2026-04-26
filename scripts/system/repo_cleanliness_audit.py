#!/usr/bin/env python3
"""Non-destructive repository cleanliness audit.

The script classifies current git status into action buckets so cleanup can be
automated without deleting or reverting user work. It is intentionally
read-only: it reports tracked edits, deletions, untracked files, generated
paths, local-state paths, and likely source/documentation work.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

GENERATED_PREFIXES = (
    "artifacts/",
    "build/",
    "coverage/",
    "dist/",
    "docs-build-local/",
    "docs-build-smoke/",
    "htmlcov/",
    "release/",
    "training/runs/",
)

LOCAL_STATE_PREFIXES = (
    ".scbe/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",
    ".hypothesis/",
    ".playwright-mcp/",
    ".playwright-cli/",
)

PRIVATE_OR_PROPOSAL_PREFIXES = (
    "docs/legal/",
    "docs/proposals/",
    "notes/",
)

TRAINING_PREFIXES = (
    "config/model_training/",
    "training-data/",
    "scripts/train/",
    "scripts/system/prepare_colab_training_run.py",
    "scripts/system/run_colab_training_notebook.py",
    "scripts/system/start_colab_training_service.py",
)

SOURCE_PREFIXES = (
    "api/",
    "python/",
    "public/",
    "schemas/",
    "scripts/",
    "scbe-cli.py",
    "scbe-visual-system/",
    "spiral-word-app/",
    "src/",
    "test_",
    "tests/",
)

DOC_PREFIXES = (
    "ALIASES",
    "docs/",
    "README",
    "ARCHITECTURE",
    "CANONICAL",
    "CONCEPTS",
    "CONTRIBUTING",
    "LAYER",
    "PITCH_",
    "REPO_",
    "SCBE_",
    "SPEC",
    "SPLIT_",
    "STATE_",
)

CONFIG_PREFIXES = (
    ".github/",
    ".pre-commit-config.yaml",
    "config/",
    ".env.example",
    ".gitignore",
    "MANIFEST.in",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
)


@dataclass(frozen=True)
class StatusRow:
    status: str
    path: str
    bucket: str
    action: str


def run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )


def resolve_repo_root(raw: str | None) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    result = run_git(Path.cwd(), "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "unable to resolve git root")
    return Path(result.stdout.strip()).resolve()


def normalize_status_path(raw: str) -> str:
    path = raw.strip().replace("\\", "/")
    if len(path) >= 2 and path[0] == '"' and path[-1] == '"':
        path = path[1:-1]
    if " -> " in path:
        path = path.split(" -> ", 1)[1].strip()
    return path


def path_matches(path: str, prefixes: Iterable[str]) -> bool:
    return any(
        path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes
    )


def classify_path(path: str) -> str:
    if path_matches(path, GENERATED_PREFIXES):
        return "generated_or_build_output"
    if path_matches(path, LOCAL_STATE_PREFIXES):
        return "local_state"
    if path_matches(path, PRIVATE_OR_PROPOSAL_PREFIXES):
        return "notes_or_private_proposal"
    if path_matches(path, TRAINING_PREFIXES):
        return "training_or_model_ops"
    if path_matches(path, SOURCE_PREFIXES):
        return "source_or_tests"
    if path_matches(path, CONFIG_PREFIXES):
        return "config_or_ci"
    if path_matches(path, DOC_PREFIXES):
        return "docs_or_canonical"
    return "needs_manual_classification"


def action_for(status: str, bucket: str) -> str:
    if "D" in status:
        return "review_deletion_before_commit"
    if bucket in {"generated_or_build_output", "local_state"}:
        return "ignore_or_offload_if_not_intentional_source"
    if bucket == "notes_or_private_proposal":
        return "preserve_local_or_demote_to_private_packet"
    if bucket == "needs_manual_classification":
        return "classify_before_stage_or_ignore"
    return "review_and_stage_in_scoped_commit"


def parse_status(repo_root: Path) -> list[StatusRow]:
    result = run_git(repo_root, "status", "--porcelain=v1")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git status failed")
    rows: list[StatusRow] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        status = line[:2]
        path = normalize_status_path(line[3:])
        bucket = classify_path(path)
        rows.append(
            StatusRow(
                status=status,
                path=path,
                bucket=bucket,
                action=action_for(status, bucket),
            )
        )
    return rows


def summarize(rows: list[StatusRow], repo_root: Path) -> dict[str, object]:
    by_bucket: dict[str, dict[str, object]] = {}
    grouped: dict[str, list[StatusRow]] = defaultdict(list)
    for row in rows:
        grouped[row.bucket].append(row)

    for bucket, bucket_rows in sorted(grouped.items()):
        by_bucket[bucket] = {
            "count": len(bucket_rows),
            "actions": dict(sorted(Counter(row.action for row in bucket_rows).items())),
            "sample": [row.path for row in bucket_rows[:25]],
        }

    status_counts = Counter(row.status for row in rows)
    return {
        "version": "scbe-repo-cleanliness-audit-v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo_root": str(repo_root),
        "total_dirty_paths": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "bucket_counts": {
            bucket: payload["count"] for bucket, payload in by_bucket.items()
        },
        "buckets": by_bucket,
        "next_actions": [
            "stage source/test/config changes in scoped commits only",
            "do not commit generated/local-state paths unless a release artifact requires them",
            "review deletions before any cleanup or restore decision",
            "move private/proposal packets to the documented private lane rather than public docs",
            "run secret scan before staging or pushing",
        ],
    }


def write_report(payload: dict[str, object], output: Path | None) -> None:
    if output is None:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit repo cleanliness without modifying files."
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root. Defaults to current git root.",
    )
    parser.add_argument("--output", default=None, help="Optional JSON report path.")
    parser.add_argument(
        "--max-dirty",
        type=int,
        default=None,
        help="Fail if total dirty paths exceed this count.",
    )
    parser.add_argument(
        "--max-unclassified",
        type=int,
        default=0,
        help="Fail if manual-classification paths exceed this.",
    )
    parser.add_argument("--json", action="store_true", help="Emit full JSON payload.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = resolve_repo_root(args.repo_root)
    rows = parse_status(repo_root)
    payload = summarize(rows, repo_root)
    output = Path(args.output).expanduser().resolve() if args.output else None
    write_report(payload, output)

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"[repo-cleanliness] dirty_paths={payload['total_dirty_paths']}")
        for bucket, count in sorted(payload["bucket_counts"].items()):
            print(f"[repo-cleanliness] {bucket}={count}")
        if output:
            print(f"[repo-cleanliness] report={output}")

    failed = False
    if (
        args.max_dirty is not None
        and int(payload["total_dirty_paths"]) > args.max_dirty
    ):
        failed = True
    unclassified = int(payload["bucket_counts"].get("needs_manual_classification", 0))
    if unclassified > args.max_unclassified:
        failed = True
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
