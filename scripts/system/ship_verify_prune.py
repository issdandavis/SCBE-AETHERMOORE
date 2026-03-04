#!/usr/bin/env python3
"""Ship files to multiple destinations, verify checksums, then optionally prune local copies.

Safety model:
- No deletion unless --delete-source is set.
- No deletion unless each file has at least --min-verified-copies verified copies.
- Writes a JSON manifest with checksums, destination paths, and prune decisions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_DIR = REPO_ROOT / "artifacts" / "storage_ship"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_source_files(source: Path) -> list[Path]:
    if source.is_file():
        return [source]
    if source.is_dir():
        return sorted([p for p in source.rglob("*") if p.is_file()])
    raise FileNotFoundError(f"source not found: {source}")


def relative_in_source(source_root: Path, file_path: Path) -> Path:
    if source_root.is_file():
        return Path(source_root.name)
    return file_path.relative_to(source_root)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ship + verify + optional prune for storage hygiene.")
    p.add_argument("--source", action="append", required=True, help="Source file or directory (repeatable).")
    p.add_argument(
        "--dest",
        action="append",
        required=True,
        help="Destination root directory (repeatable). Example: OneDrive/Dropbox/cloud sync folder.",
    )
    p.add_argument(
        "--bundle-name",
        default="",
        help="Optional bundle folder name inside destinations. Defaults to ship-<timestamp>.",
    )
    p.add_argument("--manifest-out", default="", help="Optional output manifest path.")
    p.add_argument("--min-verified-copies", type=int, default=2, help="Minimum verified destination copies required.")
    p.add_argument("--delete-source", action="store_true", help="Delete local source files after verification gate passes.")
    p.add_argument("--dry-run", action="store_true", help="Do not copy or delete; print what would happen.")
    p.add_argument("--admin-name", default="issda", help="Admin contact name for manifest metadata.")
    p.add_argument(
        "--admin-phone-env",
        default="SCBE_ADMIN_PHONE",
        help="Environment variable holding admin phone number (not hardcoded in repo).",
    )
    p.add_argument(
        "--admin-email-env",
        default="SCBE_ADMIN_EMAIL",
        help="Environment variable holding admin email (not hardcoded in repo).",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    stamp = utc_stamp()
    bundle_name = args.bundle_name.strip() or f"ship-{stamp}"

    sources = [Path(s).expanduser().resolve() for s in args.source]
    dests = [Path(d).expanduser().resolve() for d in args.dest]
    for d in dests:
        if not args.dry_run:
            d.mkdir(parents=True, exist_ok=True)

    manifest_out = Path(args.manifest_out).expanduser().resolve() if args.manifest_out else (
        DEFAULT_MANIFEST_DIR / f"{bundle_name}.manifest.json"
    )
    if not args.dry_run:
        manifest_out.parent.mkdir(parents=True, exist_ok=True)

    files: list[dict[str, Any]] = []
    for source in sources:
        source_files = collect_source_files(source)
        for src_file in source_files:
            rel = relative_in_source(source, src_file)
            src_sha = sha256_file(src_file)
            size = src_file.stat().st_size
            dest_records: list[dict[str, Any]] = []

            for dest_root in dests:
                dest_path = dest_root / bundle_name / source.name / rel
                record: dict[str, Any] = {
                    "dest_root": str(dest_root),
                    "dest_path": str(dest_path),
                    "copied": False,
                    "verified": False,
                    "sha256": "",
                    "error": "",
                }
                try:
                    if args.dry_run:
                        record["copied"] = True
                        record["verified"] = True
                        record["sha256"] = src_sha
                    else:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dest_path)
                        record["copied"] = True
                        dst_sha = sha256_file(dest_path)
                        record["sha256"] = dst_sha
                        record["verified"] = dst_sha == src_sha
                        if not record["verified"]:
                            record["error"] = "checksum_mismatch"
                except Exception as exc:
                    record["error"] = str(exc)
                dest_records.append(record)

            verified_count = sum(1 for r in dest_records if r.get("verified"))
            eligible_for_prune = verified_count >= max(1, args.min_verified_copies)
            pruned = False
            prune_error = ""
            if args.delete_source and eligible_for_prune and not args.dry_run:
                try:
                    src_file.unlink()
                    pruned = True
                except Exception as exc:
                    prune_error = str(exc)

            files.append(
                {
                    "source": str(src_file),
                    "relative": str(rel).replace("\\", "/"),
                    "size_bytes": size,
                    "sha256": src_sha,
                    "verified_copies": verified_count,
                    "eligible_for_prune": eligible_for_prune,
                    "pruned": pruned,
                    "prune_error": prune_error,
                    "destinations": dest_records,
                }
            )

    # Remove empty source directories after prune if requested.
    removed_dirs: list[str] = []
    if args.delete_source and not args.dry_run:
        for source in sources:
            if source.is_dir():
                for d in sorted([p for p in source.rglob("*") if p.is_dir()], reverse=True):
                    try:
                        d.rmdir()
                        removed_dirs.append(str(d))
                    except OSError:
                        pass
                try:
                    source.rmdir()
                    removed_dirs.append(str(source))
                except OSError:
                    pass

    admin_phone = os.environ.get(args.admin_phone_env, "").strip()
    admin_email = os.environ.get(args.admin_email_env, "").strip()

    manifest = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "bundle_name": bundle_name,
        "dry_run": bool(args.dry_run),
        "delete_source": bool(args.delete_source),
        "min_verified_copies": int(args.min_verified_copies),
        "sources": [str(s) for s in sources],
        "destinations": [str(d) for d in dests],
        "admin_contact": {
            "name": args.admin_name,
            "phone_env": args.admin_phone_env,
            "phone": admin_phone,
            "email_env": args.admin_email_env,
            "email": admin_email,
        },
        "files": files,
        "removed_empty_dirs": removed_dirs,
        "summary": {
            "file_count": len(files),
            "verified_all_min": all(f["eligible_for_prune"] for f in files) if files else False,
            "pruned_count": sum(1 for f in files if f.get("pruned")),
            "failed_copy_or_verify_count": sum(
                1 for f in files if any((not d.get("verified", False)) for d in f.get("destinations", []))
            ),
        },
    }

    if args.dry_run:
        print(json.dumps(manifest, indent=2))
        return 0

    manifest_out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "manifest": str(manifest_out),
                "bundle_name": bundle_name,
                "file_count": len(files),
                "pruned_count": manifest["summary"]["pruned_count"],
                "verified_all_min": manifest["summary"]["verified_all_min"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
