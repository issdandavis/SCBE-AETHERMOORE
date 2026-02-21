#!/usr/bin/env python3
"""Build an offline-first SCBE coordination content bundle and optional online mirror."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUN_ROOT = "training/runs/multi_ai_sync"
DEFAULT_GLOBS = [
    "docs/OFFLINE_MODE_SPEC.md",
    "docs/MULTI_AI_COORDINATION.md",
    "docs/HYDRA_COORDINATION.md",
    "docs/SCBE_CONTEXT_AETHERBROWSE_AGENT.md",
    "docs/gateway/*.md",
    "docs/map-room/*.md",
    "docs/news/latest.md",
    "docs/scbe-knowledge-v4.aetherbrowse.yaml",
    "training/kernel_manifest.yaml",
]
SNAPSHOT_FILES = [
    "docs/map-room/session_handoff_latest.md",
    "docs/OFFLINE_MODE_SPEC.md",
    "docs/MULTI_AI_COORDINATION.md",
    "docs/news/latest.md",
]
LATEST_POINTER = "training/ingest/latest_multi_ai_sync.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Offline/online content sync pipeline for SCBE multi-AI coordination."
    )
    parser.add_argument(
        "--run-root",
        default=DEFAULT_RUN_ROOT,
        help=f"Output run root directory (default: {DEFAULT_RUN_ROOT})",
    )
    parser.add_argument(
        "--glob",
        action="append",
        default=[],
        help="Extra ingest glob pattern (repeatable).",
    )
    parser.add_argument(
        "--sync-notion",
        action="store_true",
        help="Sync Notion content into docs/ before building offline bundle.",
    )
    parser.add_argument(
        "--notion-config-key",
        action="append",
        default=[],
        help="Specific key from scripts/sync-config.json (repeatable).",
    )
    parser.add_argument(
        "--skip-doc-manifest",
        action="store_true",
        help="Skip training/doc_verifier.py manifest generation.",
    )
    parser.add_argument(
        "--attest",
        default="claude,gpt,sonar",
        help="Comma-separated doc_verifier attesters (default: claude,gpt,sonar).",
    )
    parser.add_argument(
        "--hf-dataset-repo",
        default="",
        help="Optional Hugging Face dataset repo id to mirror run artifacts online.",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Do not produce a zip archive for offline transfer.",
    )
    return parser.parse_args()


def unique_ordered(items: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def rel_path(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def run_command(cmd: List[str], executed: List[List[str]]) -> None:
    executed.append(cmd)
    print("$ " + " ".join(cmd))
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}")


def copy_snapshot_file(rel: str, snapshot_root: Path) -> str | None:
    src = REPO_ROOT / rel
    if not src.exists():
        return None
    dst = snapshot_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return rel_path(dst)


def main() -> int:
    args = parse_args()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = REPO_ROOT / args.run_root / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    executed: List[List[str]] = []
    copied: List[str] = []
    globs = unique_ordered(DEFAULT_GLOBS + list(args.glob))
    offline_jsonl = run_dir / "offline_docs.jsonl"
    manifest_json = run_dir / "doc_manifest.json"
    run_summary = run_dir / "run_summary.json"
    metadata_json = run_dir / "metadata.json"
    snapshot_root = run_dir / "snapshot"
    archive_path = run_dir.with_suffix(".zip")

    if args.sync_notion:
        if args.notion_config_key:
            for key in args.notion_config_key:
                run_command(["node", "scripts/notion-sync.js", "--config-key", key], executed)
        else:
            run_command(["node", "scripts/notion-sync.js", "--all"], executed)

    ingest_cmd = [
        sys.executable,
        "scripts/ingest_docs_to_training_jsonl.py",
        "--out",
        rel_path(offline_jsonl),
    ]
    for pattern in globs:
        ingest_cmd.extend(["--glob", pattern])
    run_command(ingest_cmd, executed)

    if not args.skip_doc_manifest:
        manifest_cmd = [
            sys.executable,
            "training/doc_verifier.py",
            "--json",
            "--out",
            rel_path(manifest_json),
        ]
        attest = args.attest.strip()
        if attest:
            manifest_cmd.extend(["--attest", attest])
        run_command(manifest_cmd, executed)

    for rel in SNAPSHOT_FILES:
        copied_rel = copy_snapshot_file(rel, snapshot_root)
        if copied_rel:
            copied.append(copied_rel)

    if not args.no_archive:
        if archive_path.exists():
            archive_path.unlink()
        shutil.make_archive(str(run_dir), "zip", root_dir=run_dir)

    pointer_path = REPO_ROOT / LATEST_POINTER
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text(rel_path(run_dir) + "\n", encoding="utf-8")

    published_hf = False
    hf_repo = args.hf_dataset_repo.strip()
    if hf_repo:
        if not os.environ.get("HF_TOKEN"):
            raise RuntimeError("HF_TOKEN is required when --hf-dataset-repo is set.")
        run_command(
            [
                sys.executable,
                "scripts/push_to_hf.py",
                "--input",
                rel_path(run_dir),
                "--repo",
                hf_repo,
            ],
            executed,
        )
        published_hf = True

    state_vector = {
        "worker_id": "codex-agent",
        "task_id": "offline-online-content-sync",
        "role": "implementer",
        "status": "completed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    decision_record = {
        "action": "ALLOW",
        "signature": f"codex-agent:offline-online-content-sync:{timestamp}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": "Offline bundle and optional online mirror completed deterministically.",
        "confidence": 0.98,
    }

    summary_payload = {
        "run_id": timestamp,
        "run_dir": rel_path(run_dir),
        "offline_dataset": rel_path(offline_jsonl),
        "doc_manifest": rel_path(manifest_json) if manifest_json.exists() else None,
        "snapshot_files": copied,
        "archive": rel_path(archive_path) if archive_path.exists() else None,
        "notion_sync": {
            "enabled": args.sync_notion,
            "config_keys": args.notion_config_key,
        },
        "online_mirror": {
            "hf_dataset_repo": hf_repo or None,
            "published": published_hf,
        },
        "ingest_globs": globs,
        "commands_executed": [" ".join(cmd) for cmd in executed],
        "latest_pointer": LATEST_POINTER,
        "state_vector": state_vector,
        "decision_record": decision_record,
    }

    metadata_json.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")
    run_summary.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")

    print("")
    print("Multi-AI content sync completed.")
    print(f"Run dir: {summary_payload['run_dir']}")
    print(f"Offline dataset: {summary_payload['offline_dataset']}")
    print(f"Manifest: {summary_payload['doc_manifest']}")
    if summary_payload["archive"]:
        print(f"Archive: {summary_payload['archive']}")
    if published_hf:
        print(f"HF mirror: {hf_repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

