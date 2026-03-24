#!/usr/bin/env python3
"""Unified connector sync: Notion -> Obsidian -> GitHub -> Dropbox.

This script intentionally favors deterministic filesystem artifacts over opaque API state.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import requests


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def run_cmd(
    args: list[str], cwd: Path, check: bool = True, dry_run: bool = False
) -> subprocess.CompletedProcess | None:
    if dry_run:
        print(f"[dry-run] {' '.join(args)}")
        return None
    return subprocess.run(args, cwd=str(cwd), check=check, text=True, capture_output=False)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_sync_config(repo_root: Path) -> dict:
    cfg = repo_root / "scripts" / "sync-config.json"
    if not cfg.exists():
        raise FileNotFoundError(f"Missing sync config: {cfg}")
    return json.loads(cfg.read_text(encoding="utf-8"))


def notion_sync(repo_root: Path, args: argparse.Namespace) -> list[Path]:
    sync_script = repo_root / "scripts" / "notion-sync.js"
    if not sync_script.exists():
        raise FileNotFoundError(f"Missing script: {sync_script}")

    cmd = ["node", str(sync_script)]
    if args.config_key:
        cmd.extend(["--config-key", args.config_key])
    elif args.page_id and args.output:
        cmd.extend(["--page-id", args.page_id, "--output", args.output])
    else:
        cmd.append("--all")

    run_cmd(cmd, cwd=repo_root, dry_run=args.dry_run)

    cfg = load_sync_config(repo_root)
    outputs = []
    if args.config_key:
        entry = cfg.get(args.config_key)
        if entry and entry.get("outputPath"):
            outputs.append(repo_root / entry["outputPath"])
    elif args.page_id and args.output:
        outputs.append(repo_root / args.output)
    else:
        for entry in cfg.values():
            out = entry.get("outputPath")
            if out:
                outputs.append(repo_root / out)

    return [p for p in outputs if p.exists()]


def init_obsidian_hub(vault_path: Path, repo_root: Path, dry_run: bool) -> list[str]:
    hub_root = vault_path / "SCBE-Hub"
    dirs = [
        hub_root / "00-Inbox",
        hub_root / "01-Map-Room",
        hub_root / "02-Task-Board",
        hub_root / "03-Agents",
        hub_root / "04-Runs",
        hub_root / "05-Evidence",
        hub_root / "06-Knowledge",
        hub_root / "07-Protocols",
        hub_root / "Templates",
    ]
    created: list[str] = []

    if dry_run:
        for d in dirs:
            created.append(str(d))
        return created

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        created.append(str(d))

    files: dict[Path, str] = {
        hub_root
        / "README.md": "\n".join(
            [
                "# SCBE Hub",
                "",
                "Central multi-AI collaboration workspace for SCBE operations.",
                "",
                "## Core lanes",
                "- `00-Inbox`: raw intake",
                "- `01-Map-Room`: handoff and current mission state",
                "- `02-Task-Board`: active work, queue, done",
                "- `03-Agents`: ownership and agent registry",
                "- `04-Runs`: run logs and checkpoints",
                "- `05-Evidence`: proofs and audit artifacts",
                "- `06-Knowledge`: canonical references",
                "- `07-Protocols`: workflow and governance rules",
            ]
        )
        + "\n",
        hub_root
        / "02-Task-Board"
        / "active_tasks.md": "\n".join(
            [
                "# Active Tasks",
                "",
                "## Now",
                "",
                "## Next",
                "",
                "## Blocked",
                "",
                "## Done",
            ]
        )
        + "\n",
        hub_root
        / "03-Agents"
        / "agent_registry.md": "\n".join(
            [
                "# Agent Registry",
                "",
                "| Agent | Role | Owner | Status | Notes |",
                "|---|---|---|---|---|",
            ]
        )
        + "\n",
        hub_root
        / "Templates"
        / "task.md": "\n".join(
            [
                "# Task",
                "",
                "- `id`:",
                "- `owner`:",
                "- `status`:",
                "- `scope`:",
                "- `inputs`:",
                "- `outputs`:",
                "- `validation`:",
            ]
        )
        + "\n",
        hub_root
        / "Templates"
        / "agent_handoff.md": "\n".join(
            [
                "# Agent Handoff",
                "",
                "- `from`:",
                "- `to`:",
                "- `task_id`:",
                "- `state_summary`:",
                "- `artifacts`:",
                "- `risks`:",
                "- `next_action`:",
            ]
        )
        + "\n",
        hub_root
        / "Templates"
        / "decision_record.md": "\n".join(
            [
                "# Decision Record",
                "",
                "- `decision_id`:",
                "- `action`:",
                "- `timestamp`:",
                "- `reason`:",
                "- `confidence`:",
                "- `evidence_paths`:",
            ]
        )
        + "\n",
        hub_root
        / "Templates"
        / "run_log.md": "\n".join(
            [
                "# Run Log",
                "",
                "- `run_id`:",
                "- `start`:",
                "- `end`:",
                "- `services`:",
                "- `outputs`:",
                "- `failures`:",
                "- `next`:",
            ]
        )
        + "\n",
    }

    repo_map_room = repo_root / "docs" / "map-room" / "session_handoff_latest.md"
    map_room_dst = hub_root / "01-Map-Room" / "session_handoff_latest.md"
    if repo_map_room.exists():
        shutil.copy2(repo_map_room, map_room_dst)
        created.append(str(map_room_dst))
    elif not map_room_dst.exists():
        map_room_dst.write_text("# Session Handoff\n\n", encoding="utf-8")
        created.append(str(map_room_dst))

    for fp, content in files.items():
        if not fp.exists():
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding="utf-8")
            created.append(str(fp))

    return created


def write_obsidian_snapshot(
    vault_path: Path, repo_root: Path, synced_files: list[Path], include_training_docs: bool, dry_run: bool
) -> Path:
    ts = utc_now().strftime("%Y%m%d-%H%M%S")
    target = vault_path / "SCBE-Hub" / "notion-sync" / ts
    if dry_run:
        print(f"[dry-run] create {target}")
        return target

    target.mkdir(parents=True, exist_ok=True)

    for src in synced_files:
        rel = src.relative_to(repo_root)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    if include_training_docs:
        hf_dir = repo_root / "training-data" / "hf-digimon-egg"
        if hf_dir.exists():
            for src in hf_dir.rglob("*"):
                if src.is_file():
                    rel = src.relative_to(repo_root)
                    dst = target / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)

    index = target / "SYNC_INDEX.md"
    lines = [
        "# SCBE Hub Sync Index",
        "",
        f"- timestamp_utc: {utc_now().isoformat()}",
        f"- source_repo: {repo_root}",
        f"- notion_docs_synced: {len(synced_files)}",
        f"- included_hf_training_docs: {str(include_training_docs).lower()}",
    ]
    index.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def git_sync(repo_root: Path, message: str, push: bool, dry_run: bool) -> None:
    run_cmd(["git", "add", "docs", "training-data/hf-digimon-egg"], cwd=repo_root, dry_run=dry_run)
    if dry_run:
        return

    status = subprocess.run(
        ["git", "status", "--porcelain", "docs", "training-data/hf-digimon-egg"],
        cwd=str(repo_root),
        text=True,
        capture_output=True,
    )
    if not status.stdout.strip():
        print("[git] no staged changes for docs/training-data")
        return

    run_cmd(["git", "commit", "-m", message], cwd=repo_root, dry_run=False)
    if push:
        run_cmd(["git", "push"], cwd=repo_root, dry_run=False)


def zip_path(input_dir: Path, output_zip: Path) -> None:
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in input_dir.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(input_dir))


def dropbox_upload(dropbox_token: str, local_file: Path, remote_path: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] upload {local_file} -> dropbox:{remote_path}")
        return

    headers = {
        "Authorization": f"Bearer {dropbox_token}",
        "Dropbox-API-Arg": json.dumps(
            {
                "path": remote_path,
                "mode": "overwrite",
                "autorename": False,
                "mute": True,
                "strict_conflict": False,
            }
        ),
        "Content-Type": "application/octet-stream",
    }
    data = local_file.read_bytes()
    resp = requests.post("https://content.dropboxapi.com/2/files/upload", headers=headers, data=data, timeout=120)
    if resp.status_code >= 300:
        raise RuntimeError(f"Dropbox upload failed: {resp.status_code} {resp.text}")


def post_zapier_event(webhook_url: str, payload: dict, dry_run: bool) -> None:
    if not webhook_url:
        return
    if dry_run:
        print(f"[dry-run] zapier payload -> {webhook_url}: {json.dumps(payload)}")
        return
    resp = requests.post(webhook_url, json=payload, timeout=30)
    if resp.status_code >= 300:
        raise RuntimeError(f"Zapier webhook failed: {resp.status_code} {resp.text}")


def load_zapier_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_zapier_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def should_emit_with_cooldown(state_file: Path, event: str, cooldown_seconds: int) -> bool:
    if cooldown_seconds <= 0:
        return True
    state = load_zapier_state(state_file)
    last = state.get(event, "")
    if not last:
        return True
    try:
        last_dt = dt.datetime.fromisoformat(last)
    except Exception:
        return True
    return (utc_now() - last_dt).total_seconds() >= cooldown_seconds


def mark_emitted(state_file: Path, event: str) -> None:
    state = load_zapier_state(state_file)
    state[event] = utc_now().isoformat()
    save_zapier_state(state_file, state)


def maybe_emit_zapier_event(
    state_file: Path,
    webhook_url: str,
    payload: dict,
    dry_run: bool,
    cooldown_seconds: int,
) -> bool:
    event = str(payload.get("event", "unknown"))
    if not webhook_url:
        return False
    if not should_emit_with_cooldown(state_file, event, cooldown_seconds):
        print(f"[zapier] skipped {event} (cooldown={cooldown_seconds}s)")
        return False

    post_zapier_event(webhook_url, payload, dry_run)
    if not dry_run:
        mark_emitted(state_file, event)
    print(f"[zapier] emitted {event}")
    return True


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sync Notion docs into Obsidian/GitHub/Dropbox")
    p.add_argument("--vault-path", default=os.getenv("OBSIDIAN_VAULT_PATH", ""), help="Obsidian vault absolute path")
    p.add_argument("--config-key", default="", help="single sync-config key")
    p.add_argument("--page-id", default="", help="single Notion page id")
    p.add_argument("--output", default="", help="output path for single page sync")
    p.add_argument("--skip-notion", action="store_true")
    p.add_argument("--skip-git", action="store_true")
    p.add_argument("--skip-dropbox", action="store_true")
    p.add_argument("--dropbox-remote-dir", default="/SCBE/backups")
    p.add_argument(
        "--init-obsidian-hub",
        action="store_true",
        help="Initialize SCBE-Hub collaboration structure in the target vault.",
    )
    p.add_argument("--zapier-webhook-url", default=os.getenv("ZAPIER_WEBHOOK_URL", ""))
    p.add_argument("--zapier-mode", choices=["off", "fail-only", "summary", "full"], default="summary")
    p.add_argument("--zapier-cooldown-seconds", type=int, default=900, help="minimum seconds between same event emits")
    p.add_argument("--commit-message", default="chore(sync): notion obsidian github dropbox")
    p.add_argument("--push", action="store_true")
    p.add_argument("--include-hf-training-docs", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = repo_root_from_script()
    started_at = utc_now()
    zapier_state_file = repo_root / "artifacts" / "system-audit" / "zapier_state.json"
    zapier_enabled = bool(args.zapier_webhook_url and args.zapier_mode != "off")
    zapier_payload: dict = {
        "event": "sync_started",
        "timestamp_utc": started_at.isoformat(),
        "repo_root": str(repo_root),
        "notion_mode": "skip" if args.skip_notion else ("all" if not args.config_key else args.config_key),
        "dry_run": args.dry_run,
        "push": args.push,
        "zapier_mode": args.zapier_mode,
    }

    if zapier_enabled and args.zapier_mode == "full":
        maybe_emit_zapier_event(
            state_file=zapier_state_file,
            webhook_url=args.zapier_webhook_url,
            payload=zapier_payload,
            dry_run=args.dry_run,
            cooldown_seconds=args.zapier_cooldown_seconds,
        )

    try:
        synced_files: list[Path] = []
        if not args.skip_notion:
            synced_files = notion_sync(repo_root, args)

        snapshot_path = ""
        hub_created: list[str] = []
        if args.vault_path:
            vault = Path(args.vault_path).expanduser().resolve()
            if args.init_obsidian_hub:
                hub_created = init_obsidian_hub(vault, repo_root, args.dry_run)
                print(f"[obsidian] hub initialized: {len(hub_created)} paths")
            snapshot = write_obsidian_snapshot(
                vault, repo_root, synced_files, args.include_hf_training_docs, args.dry_run
            )
            snapshot_path = str(snapshot)
            print(f"[obsidian] snapshot: {snapshot}")
        else:
            print("[obsidian] skipped (set --vault-path or OBSIDIAN_VAULT_PATH)")

        if not args.skip_git:
            git_sync(repo_root, args.commit_message, args.push, args.dry_run)

        dropbox_remote = ""
        if not args.skip_dropbox:
            token = os.getenv("DROPBOX_TOKEN", "").strip()
            if not token:
                print("[dropbox] skipped (DROPBOX_TOKEN missing)")
            else:
                with tempfile.TemporaryDirectory(prefix="scbe-sync-") as tmp:
                    zip_file = Path(tmp) / "scbe-sync.zip"
                    # Backup deterministic docs + hf training docs only.
                    temp_root = Path(tmp) / "payload"
                    (temp_root / "docs").mkdir(parents=True, exist_ok=True)
                    (temp_root / "training-data" / "hf-digimon-egg").mkdir(parents=True, exist_ok=True)

                    for src in (repo_root / "docs").glob("*.md"):
                        dst = temp_root / "docs" / src.name
                        shutil.copy2(src, dst)

                    hf = repo_root / "training-data" / "hf-digimon-egg"
                    if hf.exists():
                        for src in hf.rglob("*"):
                            if src.is_file():
                                dst = temp_root / src.relative_to(repo_root)
                                dst.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(src, dst)

                    zip_path(temp_root, zip_file)
                    stamp = utc_now().strftime("%Y%m%d-%H%M%S")
                    remote = f"{args.dropbox_remote_dir.rstrip('/')}/scbe-hub-sync-{stamp}.zip"
                    dropbox_remote = remote
                    dropbox_upload(token, zip_file, remote, args.dry_run)
                    print(f"[dropbox] uploaded -> {remote}")

        completed_payload = {
            "event": "sync_completed",
            "timestamp_utc": utc_now().isoformat(),
            "duration_seconds": round((utc_now() - started_at).total_seconds(), 3),
            "repo_root": str(repo_root),
            "synced_file_count": len(synced_files),
            "synced_files": [str(p.relative_to(repo_root)) for p in synced_files],
            "obsidian_snapshot": snapshot_path,
            "obsidian_hub_bootstrap": hub_created,
            "dropbox_remote": dropbox_remote,
            "dry_run": args.dry_run,
            "zapier_mode": args.zapier_mode,
        }
        if zapier_enabled and args.zapier_mode in {"summary", "full"}:
            maybe_emit_zapier_event(
                state_file=zapier_state_file,
                webhook_url=args.zapier_webhook_url,
                payload=completed_payload,
                dry_run=args.dry_run,
                cooldown_seconds=args.zapier_cooldown_seconds,
            )

    except Exception as exc:
        failed_payload = {
            "event": "sync_failed",
            "timestamp_utc": utc_now().isoformat(),
            "repo_root": str(repo_root),
            "error": str(exc),
            "dry_run": args.dry_run,
            "zapier_mode": args.zapier_mode,
        }
        if zapier_enabled:
            maybe_emit_zapier_event(
                state_file=zapier_state_file,
                webhook_url=args.zapier_webhook_url,
                payload=failed_payload,
                dry_run=args.dry_run,
                cooldown_seconds=0,
            )
        raise

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
