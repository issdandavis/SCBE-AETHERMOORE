#!/usr/bin/env python3
"""Verified cloud archive helper with local RAG catalog stubs.

This tool treats cloud storage as cold storage, not as the live working tree.
It copies a source folder to a chosen cloud root, verifies the copied files,
and records searchable metadata in a local JSONL catalog. Source deletion is
explicit and only allowed after verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import shutil
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

CATALOG_PATH = Path(".scbe/cloud_rag/catalog.jsonl")
MANIFEST_NAME = "OFFLOAD_MANIFEST.json"
DEFAULT_INVENTORY_ROOTS = (
    "artifacts",
    "training/runs",
    "training/ingest",
    "training-data/audio",
    "build",
    "dist",
)
TEXT_EXTS = {
    ".bat",
    ".cfg",
    ".csv",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".ps1",
    ".py",
    ".rst",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class FileRecord:
    relative_path: str
    bytes: int
    sha256: str
    modified_utc: str
    mime_type: str
    rag_text_preview: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def text_preview(path: Path, max_chars: int = 1200) -> str:
    if path.suffix.lower() not in TEXT_EXTS:
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    text = " ".join(text.split())
    return text[:max_chars]


def record_for(root: Path, path: Path) -> FileRecord:
    rel = path.relative_to(root).as_posix()
    stat = path.stat()
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileRecord(
        relative_path=rel,
        bytes=stat.st_size,
        sha256=sha256_file(path),
        modified_utc=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        mime_type=mime,
        rag_text_preview=text_preview(path),
    )


def build_records(root: Path) -> list[FileRecord]:
    return [record_for(root, p) for p in iter_files(root)]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_catalog(manifest: dict, records: list[FileRecord]) -> None:
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CATALOG_PATH.open("a", encoding="utf-8") as fh:
        for rec in records:
            row = {
                "kind": "cloud_archive_file",
                "archive_id": manifest["archive_id"],
                "source_root": manifest["source"],
                "cloud_root": manifest["destination"],
                "relative_path": rec.relative_path,
                "bytes": rec.bytes,
                "sha256": rec.sha256,
                "mime_type": rec.mime_type,
                "rag_text_preview": rec.rag_text_preview,
                "created_utc": manifest["created_utc"],
            }
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def copy_tree(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for path in iter_files(src):
        rel = path.relative_to(src)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def remove_tree(path: Path) -> list[str]:
    errors: list[str] = []

    def retry_then_record(function, failing_path, _excinfo) -> None:
        try:
            Path(failing_path).chmod(stat.S_IWRITE)
            function(failing_path)
        except Exception as exc:  # pragma: no cover - platform-specific fallback
            errors.append(f"{failing_path}: {type(exc).__name__}: {exc}")

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=retry_then_record)
    else:  # rmtree(onexc=...) requires Python 3.12; repo supports 3.11
        shutil.rmtree(path, onerror=retry_then_record)
    return errors


def directory_size(root: Path) -> tuple[int, int]:
    files = 0
    total = 0
    for path in iter_files(root):
        try:
            total += path.stat().st_size
            files += 1
        except OSError:
            continue
    return files, total


def compare_records(src_records: list[FileRecord], dest_records: list[FileRecord]) -> list[str]:
    errors: list[str] = []
    src_map = {r.relative_path: r for r in src_records}
    dest_map = {r.relative_path: r for r in dest_records}
    for rel, src in src_map.items():
        dest = dest_map.get(rel)
        if dest is None:
            errors.append(f"missing:{rel}")
            continue
        if src.bytes != dest.bytes:
            errors.append(f"bytes:{rel}:{src.bytes}!={dest.bytes}")
        if src.sha256 != dest.sha256:
            errors.append(f"sha256:{rel}")
    for rel in sorted(set(dest_map) - set(src_map)):
        errors.append(f"extra:{rel}")
    return errors


def discover_cloud_roots() -> None:
    candidates = [
        Path("G:/My Drive"),
        Path("H:/My Drive"),
        Path("I:/My Drive"),
        Path("I:/Shared drives"),
        Path.home() / "OneDrive",
    ]
    for path in candidates:
        print(json.dumps({"path": str(path), "exists": path.exists()}))


def suggested_lane(path: Path) -> str:
    text = path.as_posix().lower()
    if "training" in text:
        return "training-runs"
    if "video" in text or "audio" in text or "youtube" in text:
        return "generated-media"
    if "pytest" in text or "cache" in text or "tmp" in text:
        return "test-artifacts"
    if "artifact" in text:
        return "repo-artifacts"
    return "cold"


def inventory(args: argparse.Namespace) -> None:
    roots = [Path(item) for item in (args.roots or DEFAULT_INVENTORY_ROOTS)]
    rows = []
    for root in roots:
        root = root.resolve()
        if not root.exists() or not root.is_dir():
            continue
        candidates = [root]
        if args.depth > 0:
            try:
                candidates = [p for p in root.iterdir() if p.is_dir()]
            except OSError:
                candidates = [root]
        for candidate in candidates:
            files, total = directory_size(candidate)
            if total < args.min_bytes:
                continue
            rows.append(
                {
                    "path": str(candidate),
                    "files": files,
                    "bytes": total,
                    "suggested_lane": suggested_lane(candidate),
                }
            )
    rows.sort(key=lambda item: item["bytes"], reverse=True)
    for row in rows[: args.limit]:
        print(json.dumps(row, sort_keys=True))


def plan_archive(args: argparse.Namespace, *, write_plan: bool = True) -> dict:
    src = Path(args.source).resolve()
    if not src.exists() or not src.is_dir():
        fail(f"source is not a directory: {src}")

    cloud_root = Path(args.cloud_root)
    archive_id = args.archive_id or f"{src.name}_{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    dest = cloud_root / args.bucket / args.lane / archive_id
    files, source_bytes = directory_size(src)
    free_bytes = shutil.disk_usage(src.anchor or str(src)).free
    payload = {
        "schema_version": "scbe_cloud_rag_archive_plan_v1",
        "archive_id": archive_id,
        "bucket": args.bucket,
        "cloud_root": str(cloud_root),
        "cloud_root_exists": cloud_root.exists() and cloud_root.is_dir(),
        "created_utc": utc_now(),
        "delete_source_requested": bool(args.delete_source),
        "destination": str(dest),
        "destination_exists": dest.exists(),
        "estimated_reclaimable_bytes": source_bytes if args.delete_source else 0,
        "free_bytes_before": free_bytes,
        "lane": args.lane,
        "source": str(src),
        "source_bytes": source_bytes,
        "source_files": files,
    }
    if write_plan:
        write_json(Path(args.local_manifest), payload)
    return payload


def archive(args: argparse.Namespace) -> None:
    if args.dry_run:
        print(json.dumps(plan_archive(args), indent=2, sort_keys=True))
        return

    src = Path(args.source).resolve()
    if not src.exists() or not src.is_dir():
        fail(f"source is not a directory: {src}")

    cloud_root = Path(args.cloud_root)
    if not cloud_root.exists() or not cloud_root.is_dir():
        fail(f"cloud root is not mounted or not a directory: {cloud_root}")

    archive_id = args.archive_id or f"{src.name}_{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    dest = cloud_root / args.bucket / args.lane / archive_id
    if dest.exists() and any(dest.iterdir()):
        fail(f"destination already exists and is not empty: {dest}")

    before_free = shutil.disk_usage(src.anchor).free
    print(f"Indexing source: {src}")
    src_records = build_records(src)
    source_bytes = sum(r.bytes for r in src_records)
    print(f"Copying {len(src_records)} files / {source_bytes} bytes to {dest}")
    copy_tree(src, dest)

    print("Verifying destination hashes")
    dest_records = build_records(dest)
    errors = compare_records(src_records, dest_records)
    verified = not errors
    manifest = {
        "archive_id": archive_id,
        "created_utc": utc_now(),
        "source": str(src),
        "destination": str(dest),
        "bucket": args.bucket,
        "lane": args.lane,
        "source_files": len(src_records),
        "source_bytes": source_bytes,
        "destination_files": len(dest_records),
        "destination_bytes": sum(r.bytes for r in dest_records),
        "verified": verified,
        "delete_source_requested": bool(args.delete_source),
        "before_free_bytes": before_free,
        "after_free_bytes": None,
        "reclaimed_bytes": None,
        "delete_errors": [],
        "errors": errors[:200],
    }
    write_json(dest / MANIFEST_NAME, manifest)
    write_json(Path(args.local_manifest), manifest)

    if not verified:
        fail(f"verification failed with {len(errors)} errors; source preserved")

    append_catalog(manifest, src_records)
    if args.delete_source:
        delete_errors = remove_tree(src)
        after_free = shutil.disk_usage(src.anchor).free
        manifest["after_free_bytes"] = after_free
        manifest["reclaimed_bytes"] = after_free - before_free
        manifest["delete_errors"] = delete_errors[:200]
        manifest["source_deleted"] = not src.exists()
        write_json(dest / MANIFEST_NAME, manifest)
        write_json(Path(args.local_manifest), manifest)
        if delete_errors:
            print(
                "Verified copy complete, but source deletion had "
                f"{len(delete_errors)} errors. Reclaimed bytes: {after_free - before_free}"
            )
        else:
            print(f"Deleted verified source. Reclaimed bytes: {after_free - before_free}")
    else:
        print("Verified copy complete. Source preserved because --delete-source was not set.")


def cleanup_verified(args: argparse.Namespace) -> None:
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        fail(f"manifest does not exist: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("verified") is not True:
        fail("manifest is not verified; refusing to delete source")
    src = Path(manifest["source"])
    dest = Path(manifest["destination"])
    if not dest.exists():
        fail(f"verified destination is missing: {dest}")
    if not src.exists():
        print("Source already deleted.")
        return

    before_free = shutil.disk_usage(src.anchor).free
    delete_errors = remove_tree(src)
    after_free = shutil.disk_usage(src.anchor).free
    manifest["after_free_bytes"] = after_free
    manifest["cleanup_free_bytes_before"] = before_free
    manifest["cleanup_reclaimed_bytes"] = after_free - before_free
    manifest["delete_errors"] = delete_errors[:200]
    manifest["reclaimed_bytes"] = after_free - int(manifest.get("before_free_bytes") or before_free)
    manifest["source_deleted"] = not src.exists()
    write_json(dest / MANIFEST_NAME, manifest)
    write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                "cleanup_reclaimed_bytes": manifest["cleanup_reclaimed_bytes"],
                "delete_error_count": len(delete_errors),
                "source_deleted": manifest["source_deleted"],
            },
            sort_keys=True,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("discover", help="Print likely mounted cloud roots as JSON lines")

    inventory_p = sub.add_parser("inventory", help="Rank local generated/archive candidates")
    inventory_p.add_argument("--roots", nargs="*", default=None)
    inventory_p.add_argument("--depth", type=int, default=1)
    inventory_p.add_argument("--min-bytes", type=int, default=1_000_000)
    inventory_p.add_argument("--limit", type=int, default=25)

    archive_p = sub.add_parser("archive", help="Copy, verify, catalog, and optionally delete a folder")
    archive_p.add_argument("--source", required=True)
    archive_p.add_argument("--cloud-root", required=True)
    archive_p.add_argument("--bucket", default="SCBE_RAG_ARCHIVE")
    archive_p.add_argument("--lane", default="cold")
    archive_p.add_argument("--archive-id")
    archive_p.add_argument("--local-manifest", default=".scbe/cloud_rag/latest_offload_manifest.json")
    archive_p.add_argument("--delete-source", action="store_true")
    archive_p.add_argument(
        "--dry-run",
        action="store_true",
        help="write/print an archive plan without copying",
    )

    cleanup_p = sub.add_parser("cleanup-verified", help="Delete source from an already verified manifest")
    cleanup_p.add_argument("--manifest", default=".scbe/cloud_rag/latest_offload_manifest.json")

    args = parser.parse_args()
    if args.cmd == "discover":
        discover_cloud_roots()
    elif args.cmd == "inventory":
        inventory(args)
    elif args.cmd == "archive":
        archive(args)
    elif args.cmd == "cleanup-verified":
        cleanup_verified(args)


if __name__ == "__main__":
    main()
