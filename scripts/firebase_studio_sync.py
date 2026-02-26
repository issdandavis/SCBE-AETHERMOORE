#!/usr/bin/env python3
"""
Firebase Studio sync for emulator + sidekick training data.

Uploads JSONL rows to Firestore and optionally uploads source JSONL files
to Firebase Storage. This is a cloud-first bridge for lightweight local use.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATTERNS = [
    "training-data/rom_sessions/*.jsonl",
    "training-data/game_sessions/*.jsonl",
    "training-data/sidekick/*.jsonl",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json_env(name: str) -> Optional[Dict[str, Any]]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{name} is set but not valid JSON.") from exc
    if not isinstance(obj, dict):
        raise RuntimeError(f"{name} must contain a JSON object.")
    return obj


def init_firebase(storage_bucket: str = "") -> Tuple[Any, Optional[Any], str]:
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore, storage
    except Exception as exc:
        raise RuntimeError(
            "firebase-admin is required. Install with: pip install firebase-admin google-cloud-firestore"
        ) from exc

    cred = None
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        cred = credentials.ApplicationDefault()
    else:
        cfg = _load_json_env("FIREBASE_CONFIG") or _load_json_env("FIREBASE_SERVICE_ACCOUNT_KEY")
        if cfg:
            cred = credentials.Certificate(cfg)

    if cred is None:
        raise RuntimeError(
            "Firebase credentials not configured. Set GOOGLE_APPLICATION_CREDENTIALS, "
            "FIREBASE_CONFIG, or FIREBASE_SERVICE_ACCOUNT_KEY."
        )

    bucket_name = storage_bucket.strip() or os.getenv("FIREBASE_STORAGE_BUCKET", "").strip()
    init_opts: Dict[str, Any] = {}
    if bucket_name:
        init_opts["storageBucket"] = bucket_name

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, init_opts or None)

    db = firestore.client()
    bucket = storage.bucket(bucket_name) if bucket_name else None
    return db, bucket, bucket_name


def expand_patterns(patterns: Sequence[str]) -> List[Path]:
    files: List[Path] = []
    for pattern in patterns:
        pattern = pattern.strip()
        if not pattern:
            continue
        root_pattern = str(REPO_ROOT / pattern) if not Path(pattern).is_absolute() else pattern
        for match in glob.glob(root_pattern):
            p = Path(match).expanduser().resolve()
            if p.is_file():
                files.append(p)
    out: List[Path] = []
    seen = set()
    for p in sorted(files):
        key = str(p).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def iter_jsonl_rows(path: Path, max_rows: int = 0) -> Iterable[Tuple[int, Dict[str, Any]]]:
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            yield line_no, row
            count += 1
            if max_rows > 0 and count >= max_rows:
                return


def classify_collection(path: Path, prefix: str) -> str:
    lowered = str(path).lower()
    if "rom_sessions" in lowered:
        return f"{prefix}_rom_sessions"
    if path.name.lower() == "sidekick_memory.jsonl":
        return f"{prefix}_sidekick_memory"
    if path.name.lower() == "sidekick_sft.jsonl":
        return f"{prefix}_sidekick_sft"
    return f"{prefix}_training_rows"


def make_doc_id(path: Path, line_no: int, row: Dict[str, Any]) -> str:
    payload = json.dumps(row, sort_keys=True, ensure_ascii=False)
    token = f"{path}|{line_no}|{payload}".encode("utf-8")
    return hashlib.sha1(token).hexdigest()


def relative_path_str(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def sync_firestore(
    db: Any,
    files: Sequence[Path],
    collection_prefix: str,
    run_id: str,
    max_rows_per_file: int = 0,
    dry_run: bool = False,
) -> Dict[str, int]:
    stats = {"files": 0, "rows": 0, "collections": 0}
    if not files:
        return stats

    stats["files"] = len(files)
    now = utc_now_iso()
    touched = set()

    # Firestore batched writes have a 500-op limit.
    pending = []
    batch = db.batch() if not dry_run else None

    for path in files:
        collection_name = classify_collection(path, collection_prefix)
        touched.add(collection_name)
        for line_no, row in iter_jsonl_rows(path, max_rows=max_rows_per_file):
            doc_id = make_doc_id(path, line_no, row)
            doc = {
                "doc_id": doc_id,
                "source_file": relative_path_str(path),
                "line_no": line_no,
                "ingested_at_utc": now,
                "run_id": run_id,
                "event_type": str(row.get("event_type", "")),
                "metadata": row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else {},
                "prompt": str(row.get("prompt", "")),
                "response": str(row.get("response", "")),
                "raw": row,
            }
            if dry_run:
                stats["rows"] += 1
                continue

            ref = db.collection(collection_name).document(doc_id)
            batch.set(ref, doc, merge=True)
            pending.append(1)
            stats["rows"] += 1

            if len(pending) >= 400:
                batch.commit()
                batch = db.batch()
                pending.clear()

    if not dry_run and pending:
        batch.commit()

    stats["collections"] = len(touched)
    return stats


def upload_storage(
    bucket: Any,
    files: Sequence[Path],
    storage_prefix: str,
    run_id: str,
    dry_run: bool = False,
) -> Dict[str, int]:
    stats = {"files_uploaded": 0}
    if not files:
        return stats

    for path in files:
        rel = relative_path_str(path)
        object_name = f"{storage_prefix.strip('/')}/{rel}".strip("/")
        if dry_run:
            stats["files_uploaded"] += 1
            continue
        blob = bucket.blob(object_name)
        blob.metadata = {"run_id": run_id, "uploaded_utc": utc_now_iso()}
        blob.upload_from_filename(str(path), content_type="application/json")
        stats["files_uploaded"] += 1
    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync emulator and sidekick JSONL to Firebase Studio")
    parser.add_argument(
        "--glob",
        action="append",
        default=[],
        help="Glob pattern for JSONL files (repeatable). Relative patterns are resolved from repo root.",
    )
    parser.add_argument(
        "--collection-prefix",
        default="aethermoor",
        help="Firestore collection prefix (default: aethermoor).",
    )
    parser.add_argument(
        "--storage-prefix",
        default="training-data",
        help="Firebase Storage object prefix.",
    )
    parser.add_argument(
        "--storage-bucket",
        default="",
        help="Firebase Storage bucket. Falls back to FIREBASE_STORAGE_BUCKET env var.",
    )
    parser.add_argument(
        "--max-rows-per-file",
        type=int,
        default=0,
        help="Limit rows processed per file (0 = all rows).",
    )
    parser.add_argument(
        "--skip-firestore",
        action="store_true",
        help="Skip Firestore row sync.",
    )
    parser.add_argument(
        "--skip-storage",
        action="store_true",
        help="Skip Storage file upload.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan only. Do not write to Firebase.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    patterns = args.glob if args.glob else list(DEFAULT_PATTERNS)
    files = expand_patterns(patterns)
    if not files:
        print("No files matched. Nothing to sync.")
        return 0

    if args.skip_firestore and args.skip_storage:
        print("Both --skip-firestore and --skip-storage were set. Nothing to do.")
        return 2

    try:
        db, bucket, bucket_name = init_firebase(storage_bucket=args.storage_bucket)
    except RuntimeError as exc:
        print(f"Firebase init failed: {exc}")
        return 2

    run_id = f"sync_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    summary: Dict[str, Any] = {
        "run_id": run_id,
        "dry_run": args.dry_run,
        "files_matched": len(files),
        "patterns": patterns,
    }

    if not args.skip_firestore:
        fs_stats = sync_firestore(
            db=db,
            files=files,
            collection_prefix=args.collection_prefix,
            run_id=run_id,
            max_rows_per_file=max(0, args.max_rows_per_file),
            dry_run=args.dry_run,
        )
        summary["firestore"] = fs_stats

    if not args.skip_storage:
        if bucket is None:
            summary["storage"] = {
                "files_uploaded": 0,
                "bucket": "",
                "status": "skipped (no bucket configured)",
            }
        else:
            st_stats = upload_storage(
                bucket=bucket,
                files=files,
                storage_prefix=args.storage_prefix,
                run_id=run_id,
                dry_run=args.dry_run,
            )
            st_stats["bucket"] = bucket_name
            summary["storage"] = st_stats

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
