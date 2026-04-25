#!/usr/bin/env python3
"""Hash-only file tracking snapshots for SCBE agent-bus work.

The tracker records durable state for files without copying file contents into
agent packets. It is meant to feed the bus with stable, replayable context:
route metadata, delivery class, git status, size, mtimes, and SHA-256 hashes.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "file_tracking" / "latest"
DEFAULT_TRACKED_PATHS = (
    "scripts/system/mirror_room_agent_bus.py",
    "tests/test_mirror_room_agent_bus.py",
    "src/api/free_llm_routes.py",
    "tests/api/test_free_llm_routes.py",
    "scripts/system/auto_file_tracker.py",
    "tests/test_auto_file_tracker.py",
)
DELIVERY_CLASSES = {
    "interactive_reliable",
    "telemetry_loss_tolerant",
    "mission_critical_command",
    "delayed_replayable",
    "archive_only",
    "emergency_minimal",
}


@dataclass(frozen=True)
class FormationRoute:
    topic: str = "agent.file.track"
    source: str = "repo.worktree"
    tongue: str = "KO"
    trust_class: str = "governed"
    mission_class: str = "interactive"
    locality: str = "local"
    delivery_class: str = "archive_only"

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "source": self.source,
            "tongue": self.tongue,
            "trust_class": self.trust_class,
            "mission_class": self.mission_class,
            "locality": self.locality,
            "delivery_class": self.delivery_class,
            "tuple": [
                self.topic,
                self.source,
                self.tongue,
                self.trust_class,
                self.mission_class,
                self.locality,
            ],
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_repo_relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _resolve_input_path(path_text: str, repo_root: Path = REPO_ROOT) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = repo_root / path
    return path


def expand_tracked_paths(
    paths: list[str] | tuple[str, ...],
    globs: list[str] | tuple[str, ...] = (),
    *,
    repo_root: Path = REPO_ROOT,
) -> list[Path]:
    resolved: dict[str, Path] = {}
    for raw_path in paths:
        path = _resolve_input_path(raw_path, repo_root)
        resolved[_safe_repo_relative(path, repo_root)] = path
    for pattern in globs:
        full_pattern = str(_resolve_input_path(pattern, repo_root))
        for match in glob.glob(full_pattern, recursive=True):
            path = Path(match)
            if path.is_file():
                resolved[_safe_repo_relative(path, repo_root)] = path
    return [resolved[key] for key in sorted(resolved)]


def _git_status_for(paths: list[Path], repo_root: Path = REPO_ROOT) -> dict[str, str]:
    if not paths:
        return {}
    rel_paths = [_safe_repo_relative(path, repo_root) for path in paths]
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--", *rel_paths],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return {}
    if result.returncode != 0:
        return {}

    statuses: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        path_part = line[3:]
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1]
        statuses[path_part.replace("\\", "/").strip('"')] = status
    return statuses


def build_file_record(
    path: Path, git_status: str | None = None, *, repo_root: Path = REPO_ROOT
) -> dict[str, Any]:
    rel_path = _safe_repo_relative(path, repo_root)
    if not path.exists():
        return {
            "path": rel_path,
            "exists": False,
            "git_status": git_status,
            "size_bytes": None,
            "mtime_utc": None,
            "sha256": None,
        }
    stat = path.stat()
    return {
        "path": rel_path,
        "exists": True,
        "git_status": git_status,
        "size_bytes": stat.st_size,
        "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "sha256": _sha256_file(path),
    }


def build_snapshot(
    paths: list[str] | tuple[str, ...] | list[Path],
    *,
    label: str = "manual",
    globs: list[str] | tuple[str, ...] = (),
    route: FormationRoute | None = None,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    raw_paths = [str(path) for path in paths]
    tracked_paths = expand_tracked_paths(raw_paths, globs, repo_root=repo_root)
    statuses = _git_status_for(tracked_paths, repo_root)
    files = [
        build_file_record(
            path,
            statuses.get(_safe_repo_relative(path, repo_root)),
            repo_root=repo_root,
        )
        for path in tracked_paths
    ]
    exists_count = sum(1 for item in files if item["exists"])
    missing_count = len(files) - exists_count
    dirty_count = sum(1 for item in files if item.get("git_status"))
    return {
        "schema_version": "scbe-file-tracking-snapshot-v1",
        "created_at_utc": _utc_now(),
        "label": label,
        "route": (route or FormationRoute()).to_dict(),
        "content_policy": "hash-only; file contents are never copied into this packet",
        "summary": {
            "tracked": len(files),
            "exists": exists_count,
            "missing": missing_count,
            "dirty_or_untracked": dirty_count,
        },
        "files": files,
    }


def write_snapshot(
    snapshot: dict[str, Any], output_dir: Path = DEFAULT_OUTPUT_DIR
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = output_dir / "file_tracking_snapshot.json"
    history_path = output_dir / "file_tracking_history.jsonl"
    changed_path = output_dir / "changed_files.json"

    snapshot_path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            )
            + "\n"
        )

    changed = {
        "schema_version": "scbe-file-tracking-changed-files-v1",
        "created_at_utc": snapshot["created_at_utc"],
        "label": snapshot["label"],
        "route": snapshot["route"],
        "files": [
            item
            for item in snapshot["files"]
            if item.get("git_status") or not item.get("exists")
        ],
    }
    changed_path.write_text(
        json.dumps(changed, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return {
        "snapshot": snapshot_path,
        "history": history_path,
        "changed": changed_path,
    }


def _route_from_args(args: argparse.Namespace) -> FormationRoute:
    if args.delivery_class not in DELIVERY_CLASSES:
        raise ValueError(f"Unsupported delivery class: {args.delivery_class}")
    return FormationRoute(
        topic=args.topic,
        source=args.source,
        tongue=args.tongue,
        trust_class=args.trust_class,
        mission_class=args.mission_class,
        locality=args.locality,
        delivery_class=args.delivery_class,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create an SCBE hash-only file tracking snapshot"
    )
    parser.add_argument("--label", default="manual")
    parser.add_argument("--paths", nargs="*", default=list(DEFAULT_TRACKED_PATHS))
    parser.add_argument("--glob", action="append", default=[])
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--topic", default="agent.file.track")
    parser.add_argument("--source", default="repo.worktree")
    parser.add_argument("--tongue", default="KO")
    parser.add_argument("--trust-class", default="governed")
    parser.add_argument("--mission-class", default="interactive")
    parser.add_argument("--locality", default="local")
    parser.add_argument(
        "--delivery-class", default="archive_only", choices=sorted(DELIVERY_CLASSES)
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full snapshot instead of a short summary",
    )
    args = parser.parse_args()

    snapshot = build_snapshot(
        args.paths, label=args.label, globs=args.glob, route=_route_from_args(args)
    )
    written = write_snapshot(snapshot, Path(args.output_dir))
    if args.json:
        print(
            json.dumps(
                {
                    "snapshot": snapshot,
                    "written": {key: str(value) for key, value in written.items()},
                },
                indent=2,
            )
        )
    else:
        print(
            json.dumps(
                {
                    "label": snapshot["label"],
                    "summary": snapshot["summary"],
                    "route": snapshot["route"],
                    "written": {key: str(value) for key, value in written.items()},
                },
                indent=2,
                ensure_ascii=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
