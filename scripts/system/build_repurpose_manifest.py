#!/usr/bin/env python3
"""Build a top-level repurpose manifest for non-destructive repo cleanup."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = REPO_ROOT / "config" / "repurpose_policy.json"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "cleanup" / "repurpose_manifest.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "artifacts" / "cleanup" / "repurpose_manifest.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify top-level repo paths into GitHub, Hugging Face, Drive, or manual-review lanes."
    )
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--policy", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    return parser.parse_args()


def load_policy(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Policy file must be a JSON object: {path}")
    rules = payload.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError(f"Policy rules must be a list: {path}")
    return payload


def normalize_rel(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def root_name_from_rel(rel_path: str) -> str:
    normalized = normalize_rel(rel_path)
    return normalized.split("/", 1)[0] if normalized else normalized


def human_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{size} B"


def size_path(path: Path) -> int:
    if path.is_file():
        try:
            return int(path.stat().st_size)
        except OSError:
            return 0

    total = 0
    for current_root, _dirs, files in os.walk(path, onerror=lambda _err: None):
        for file_name in files:
            file_path = Path(current_root) / file_name
            try:
                total += int(file_path.stat().st_size)
            except OSError:
                continue
    return total


def match_rule(rel_path: str, kind: str, policy: dict[str, Any]) -> dict[str, Any] | None:
    normalized = normalize_rel(rel_path)
    for rule in policy.get("rules", []):
        patterns = rule.get("patterns", [])
        rule_kind = str(rule.get("kind", "any"))
        if rule_kind not in {"any", kind}:
            continue
        for pattern in patterns:
            normalized_pattern = normalize_rel(str(pattern))
            if fnmatch.fnmatch(normalized, normalized_pattern):
                return rule
    return None


def _git_output(repo_root: Path, args: list[str]) -> bytes:
    process = subprocess.run(
        args,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if process.returncode != 0:
        return b""
    return process.stdout


def build_git_tracked_counts(repo_root: Path) -> dict[str, int]:
    if not (repo_root / ".git").exists():
        return {}
    payload = _git_output(repo_root, ["git", "ls-files", "-z"])
    counts: Counter[str] = Counter()
    for raw_path in payload.decode("utf-8", errors="replace").split("\x00"):
        if not raw_path:
            continue
        counts[root_name_from_rel(raw_path)] += 1
    return dict(counts)


def build_git_status_counts(repo_root: Path) -> dict[str, dict[str, int]]:
    if not (repo_root / ".git").exists():
        return {}

    payload = _git_output(repo_root, ["git", "status", "--porcelain=v1", "-z"])
    tokens = payload.decode("utf-8", errors="replace").split("\x00")
    summary: dict[str, Counter[str]] = {}
    index = 0

    while index < len(tokens):
        token = tokens[index]
        index += 1
        if not token:
            continue
        if len(token) < 4:
            continue

        status = token[:2]
        rel_path = token[3:]
        if "R" in status or "C" in status:
            if index < len(tokens):
                rel_path = tokens[index]
                index += 1

        root = root_name_from_rel(rel_path)
        root_summary = summary.setdefault(root, Counter())
        root_summary["changed_paths"] += 1

        if status == "??":
            root_summary["untracked_paths"] += 1
        elif "D" in status:
            root_summary["deleted_paths"] += 1
        else:
            root_summary["modified_paths"] += 1

    return {root: dict(counts) for root, counts in summary.items()}


def build_manifest(repo_root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    tracked_counts = build_git_tracked_counts(repo_root)
    status_counts = build_git_status_counts(repo_root)

    entries: list[dict[str, Any]] = []
    bucket_counts: Counter[str] = Counter()
    bucket_bytes: Counter[str] = Counter()

    for path in sorted(repo_root.iterdir(), key=lambda item: item.name.lower()):
        kind = "file" if path.is_file() else "directory" if path.is_dir() else "other"
        rel_path = path.name
        rule = match_rule(rel_path, kind, policy)
        if rule is None:
            rule = {
                "name": "manual-fallback",
                "bucket": "manual-review",
                "destinations": ["github", "gdrive"],
                "reason": "No explicit rule matched. Review before any replication or commit.",
            }

        bytes_total = size_path(path)
        git_status = status_counts.get(rel_path, {})
        entry = {
            "name": rel_path,
            "kind": kind,
            "bytes": bytes_total,
            "human_size": human_bytes(bytes_total),
            "bucket": rule["bucket"],
            "destinations": list(rule.get("destinations", [])),
            "reason": str(rule.get("reason", "")),
            "matched_rule": str(rule.get("name", "unknown")),
            "git": {
                "tracked_files": int(tracked_counts.get(rel_path, 0)),
                "changed_paths": int(git_status.get("changed_paths", 0)),
                "modified_paths": int(git_status.get("modified_paths", 0)),
                "deleted_paths": int(git_status.get("deleted_paths", 0)),
                "untracked_paths": int(git_status.get("untracked_paths", 0)),
            },
        }
        entries.append(entry)
        bucket_counts[entry["bucket"]] += 1
        bucket_bytes[entry["bucket"]] += bytes_total

    entries.sort(key=lambda item: item["bytes"], reverse=True)

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "policy_path": str(DEFAULT_POLICY_PATH),
        "summary": {
            "entry_count": len(entries),
            "total_bytes": sum(entry["bytes"] for entry in entries),
            "bucket_counts": dict(bucket_counts),
            "bucket_bytes": {bucket: int(value) for bucket, value in bucket_bytes.items()},
        },
        "entries": entries,
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    lines = [
        "# Repurpose Manifest",
        "",
        f"- Generated: `{manifest['generated_at_utc']}`",
        f"- Repo root: `{manifest['repo_root']}`",
        f"- Total entries: `{summary['entry_count']}`",
        f"- Total bytes: `{human_bytes(int(summary['total_bytes']))}`",
        "",
        "## Bucket Summary",
        "",
        "| Bucket | Entries | Bytes |",
        "| --- | ---: | ---: |",
    ]

    bucket_counts = summary["bucket_counts"]
    bucket_bytes = summary["bucket_bytes"]
    for bucket in sorted(bucket_counts):
        lines.append(f"| {bucket} | {bucket_counts[bucket]} | {human_bytes(int(bucket_bytes.get(bucket, 0)))} |")

    lines.extend(
        [
            "",
            "## Largest Paths",
            "",
            "| Path | Bucket | Destinations | Size | Git Changes |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )

    for entry in manifest["entries"][:25]:
        destinations = ", ".join(entry["destinations"]) if entry["destinations"] else "none"
        changes = entry["git"]["changed_paths"]
        lines.append(f"| `{entry['name']}` | {entry['bucket']} | {destinations} | {entry['human_size']} | {changes} |")

    return "\n".join(lines) + "\n"


def write_outputs(manifest: dict[str, Any], output_json: Path, output_md: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    output_md.write_text(render_markdown(manifest), encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    policy_path = Path(args.policy).resolve()
    output_json = Path(args.output_json).resolve()
    output_md = Path(args.output_md).resolve()

    policy = load_policy(policy_path)
    manifest = build_manifest(repo_root, policy)
    manifest["policy_path"] = str(policy_path)
    write_outputs(manifest, output_json, output_md)

    print(f"Wrote {output_json}")
    print(f"Wrote {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
