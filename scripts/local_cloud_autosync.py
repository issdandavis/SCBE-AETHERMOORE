#!/usr/bin/env python3
"""Automatic local workspace to cloud sync runner for SCBE-AETHERMOORE."""

from __future__ import annotations

import argparse
import fnmatch
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = "training/local_cloud_sync.json"
DEFAULT_RUN_ROOT = "training/runs/local_cloud_sync"
DEFAULT_STATE_FILE = "training/ingest/local_cloud_sync_state.json"
LATEST_POINTER = "training/ingest/latest_local_cloud_sync.txt"

DEFAULT_EXCLUDES = [
    ".git/**",
    ".venv/**",
    "node_modules/**",
    "**/__pycache__/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    "artifacts/**",
    "training/runs/**",
    "*.zip",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect local file changes and ship snapshots to configured cloud targets."
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, help=f"Config path (default: {DEFAULT_CONFIG})")
    parser.add_argument("--run-root", default=DEFAULT_RUN_ROOT, help=f"Run root (default: {DEFAULT_RUN_ROOT})")
    parser.add_argument(
        "--state-file",
        default=DEFAULT_STATE_FILE,
        help=f"State file path (default: {DEFAULT_STATE_FILE})",
    )
    parser.add_argument(
        "--latest-pointer",
        default=LATEST_POINTER,
        help=f"Latest pointer path (default: {LATEST_POINTER})",
    )
    parser.add_argument("--once", action="store_true", help="Run one sync cycle and exit.")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=0,
        help="Polling interval (overrides config watch_interval_seconds).",
    )
    parser.add_argument("--force", action="store_true", help="Force snapshot even if no changes.")
    parser.add_argument("--no-upload", action="store_true", help="Skip cloud upload operations.")
    parser.add_argument(
        "--ship-targets",
        default="",
        help="Override target list as CSV subset of: hf,github,dropbox,adobe,gdrive,proton",
    )
    return parser.parse_args()


def load_json(path: Path, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return dict(default or {})
    return parsed if isinstance(parsed, dict) else dict(default or {})


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def normalize_rel(path: Path) -> str:
    return path.as_posix().strip()


def parse_ship_targets(raw: str) -> set[str]:
    if not raw.strip():
        return set()
    values = {part.strip().lower() for part in raw.split(",") if part.strip()}
    supported = {"hf", "github", "dropbox", "adobe", "gdrive", "proton"}
    return values & supported


def path_matches_any(rel_path: str, patterns: Iterable[str]) -> bool:
    for pattern in patterns:
        p = pattern.strip().replace("\\", "/")
        if not p:
            continue
        if fnmatch.fnmatch(rel_path, p):
            return True
        if rel_path.startswith(p.rstrip("/") + "/"):
            return True
    return False


def collect_workspace_index(
    include_globs: List[str],
    exclude_globs: List[str],
) -> Dict[str, Dict[str, int]]:
    files: Dict[str, Path] = {}
    repo_abs = REPO_ROOT.resolve()

    for pattern in include_globs:
        candidate = pattern.strip()
        if not candidate:
            continue
        pattern_abs = str((REPO_ROOT / candidate).resolve())
        for hit in glob.glob(pattern_abs, recursive=True):
            abs_path = Path(hit)
            if not abs_path.is_file():
                continue
            try:
                rel = abs_path.resolve().relative_to(repo_abs)
            except ValueError:
                continue
            rel_s = normalize_rel(rel)
            if path_matches_any(rel_s, exclude_globs):
                continue
            files[rel_s] = abs_path.resolve()

    index: Dict[str, Dict[str, int]] = {}
    for rel_s in sorted(files):
        stat = files[rel_s].stat()
        index[rel_s] = {"size": int(stat.st_size), "mtime_ns": int(stat.st_mtime_ns)}
    return index


def compute_fingerprint(index: Dict[str, Dict[str, int]]) -> str:
    hasher = hashlib.sha256()
    for rel_s in sorted(index):
        meta = index[rel_s]
        hasher.update(f"{rel_s}|{meta['size']}|{meta['mtime_ns']}\n".encode("utf-8"))
    return hasher.hexdigest()


def compute_delta(
    previous_index: Dict[str, Dict[str, int]],
    current_index: Dict[str, Dict[str, int]],
) -> Dict[str, List[str]]:
    prev_paths = set(previous_index.keys())
    curr_paths = set(current_index.keys())
    added = sorted(curr_paths - prev_paths)
    removed = sorted(prev_paths - curr_paths)

    modified: List[str] = []
    for rel_s in sorted(curr_paths & prev_paths):
        prev_meta = previous_index.get(rel_s, {})
        curr_meta = current_index.get(rel_s, {})
        if (
            int(prev_meta.get("size", -1)) != int(curr_meta.get("size", -2))
            or int(prev_meta.get("mtime_ns", -1)) != int(curr_meta.get("mtime_ns", -2))
        ):
            modified.append(rel_s)

    changed = sorted(set(added + modified))
    return {
        "added": added,
        "modified": modified,
        "removed": removed,
        "changed": changed,
    }


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def build_file_hashes(paths: List[str]) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for rel_s in paths:
        abs_path = REPO_ROOT / rel_s
        if not abs_path.exists() or not abs_path.is_file():
            continue
        hashes[rel_s] = sha256_file(abs_path)
    return hashes


def create_snapshot_bundle(
    run_root: Path,
    run_id: str,
    delta: Dict[str, List[str]],
    current_index: Dict[str, Dict[str, int]],
    state_fingerprint: str,
) -> Dict[str, Path]:
    run_dir = run_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    archive_path = run_root / f"{run_id}.zip"

    changed_files = list(delta["changed"])
    file_hashes = build_file_hashes(changed_files)

    manifest = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "fingerprint": state_fingerprint,
        "counts": {
            "indexed_files": len(current_index),
            "added": len(delta["added"]),
            "modified": len(delta["modified"]),
            "removed": len(delta["removed"]),
            "changed": len(delta["changed"]),
        },
        "delta": delta,
        "changed_hashes_sha256": file_hashes,
    }
    manifest_path = run_dir / "manifest.json"
    write_json(manifest_path, manifest)

    index_path = run_dir / "index.json"
    write_json(index_path, {"index": current_index})

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(manifest_path, arcname="manifest.json")
        zf.write(index_path, arcname="index.json")
        for rel_s in sorted(delta["changed"]):
            abs_path = REPO_ROOT / rel_s
            if abs_path.exists() and abs_path.is_file():
                zf.write(abs_path, arcname=f"workspace/{rel_s}")

    return {
        "run_dir": run_dir,
        "archive_path": archive_path,
        "manifest_path": manifest_path,
        "index_path": index_path,
    }


def run_gh_command(cmd: List[str], env: Dict[str, str]) -> str:
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    out = proc.stdout or ""
    if proc.returncode != 0:
        raise RuntimeError(f"gh command failed: {' '.join(cmd)}\n{out}")
    return out


def detect_github_repo() -> str:
    if not shutil.which("git"):
        return ""
    proc = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    url = (proc.stdout or "").strip()
    if not url:
        return ""
    if url.startswith("git@github.com:"):
        repo = url.split(":", 1)[1]
    elif "github.com/" in url:
        repo = url.split("github.com/", 1)[1]
    else:
        return ""
    return repo[:-4] if repo.endswith(".git") else repo


def upload_to_hf(run_dir: Path, repo_id: str, path_prefix: str, run_id: str) -> Dict[str, Any]:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN is required for Hugging Face upload.")
    try:
        from huggingface_hub import HfApi  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"huggingface_hub not installed: {exc}") from exc

    api = HfApi(token=token)
    remote_path = f"{path_prefix.rstrip('/')}/{run_id}".strip("/")
    api.upload_folder(
        folder_path=str(run_dir),
        path_in_repo=remote_path,
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=f"local-workspace-sync: {run_id}",
    )
    return {"status": "ok", "repo": repo_id, "path_in_repo": remote_path}


def upload_to_github_release(
    repo: str,
    run_id: str,
    release_prefix: str,
    files: List[Path],
) -> Dict[str, Any]:
    if not shutil.which("gh"):
        raise RuntimeError("GitHub CLI (gh) is required for GitHub release upload.")
    token = (
        os.environ.get("GH_TOKEN", "").strip()
        or os.environ.get("GITHUB_TOKEN", "").strip()
        or os.environ.get("GITHUB_PAT", "").strip()
    )
    if not token:
        raise RuntimeError("GH_TOKEN, GITHUB_TOKEN, or GITHUB_PAT is required for GitHub release upload.")

    env = dict(os.environ)
    env["GH_TOKEN"] = token

    tag = f"{release_prefix}-{run_id}"
    title = f"Local Workspace Sync {run_id}"
    notes = "Automated local workspace sync snapshot."

    view_cmd = ["gh", "release", "view", tag, "--repo", repo]
    view_proc = subprocess.run(
        view_cmd,
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if view_proc.returncode != 0:
        run_gh_command(
            ["gh", "release", "create", tag, "--repo", repo, "--title", title, "--notes", notes],
            env,
        )

    upload_cmd = ["gh", "release", "upload", tag, "--repo", repo, "--clobber"] + [str(p) for p in files]
    run_gh_command(upload_cmd, env)
    return {"status": "ok", "repo": repo, "tag": tag, "assets": [p.name for p in files]}


def upload_file_dropbox(local_file: Path, dropbox_path: str, token: str) -> Dict[str, Any]:
    url = "https://content.dropboxapi.com/2/files/upload"
    content = local_file.read_bytes()
    args = {"path": dropbox_path, "mode": "overwrite", "autorename": False, "mute": True}
    headers = {
        "Authorization": f"Bearer {token}",
        "Dropbox-API-Arg": json.dumps(args),
        "Content-Type": "application/octet-stream",
    }
    req = urllib.request.Request(url, data=content, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Dropbox upload failed ({exc.code}): {detail}") from exc
    payload = json.loads(raw)
    return {
        "name": payload.get("name"),
        "path_display": payload.get("path_display"),
        "id": payload.get("id"),
    }


def upload_to_dropbox(run_id: str, base_path: str, files: List[Path]) -> Dict[str, Any]:
    token = os.environ.get("DROPBOX_TOKEN", "").strip()
    if not token:
        raise RuntimeError("DROPBOX_TOKEN is required for Dropbox upload.")
    root = base_path if base_path.startswith("/") else f"/{base_path}"
    root = root.rstrip("/")
    uploads = []
    for local in files:
        target = f"{root}/{run_id}/{local.name}"
        uploads.append(upload_file_dropbox(local, target, token))
    return {"status": "ok", "base_path": root, "uploads": uploads}


def upload_to_local_sync_folder(root: Path, run_id: str, files: List[Path]) -> Dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    target_dir = root / "SCBE" / "local-workspace-sync" / run_id
    target_dir.mkdir(parents=True, exist_ok=True)
    copied: List[str] = []
    for src in files:
        dest = target_dir / src.name
        shutil.copy2(src, dest)
        copied.append(dest.name)
    return {"status": "ok", "base_dir": str(root), "path": str(target_dir), "files": copied}


def detect_dropbox_sync_dir() -> Path | None:
    env_path = os.environ.get("DROPBOX_SYNC_DIR", "").strip()
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists():
            return p

    home = Path.home()
    candidates = [
        home / "Dropbox",
        home / "Dropbox (Personal)",
        home / "Dropbox (Business)",
    ]
    for path in candidates:
        if path.exists():
            return path
    for path in home.glob("Dropbox*"):
        if path.is_dir():
            return path
    return None


def upload_to_dropbox_local(run_id: str, base_dir: str, files: List[Path]) -> Dict[str, Any]:
    root: Path | None = Path(base_dir).expanduser() if base_dir.strip() else detect_dropbox_sync_dir()
    if root is None:
        raise RuntimeError("Dropbox sync folder not found. Set shipping.dropbox.base_dir or DROPBOX_SYNC_DIR.")
    return upload_to_local_sync_folder(root, run_id, files)


def detect_adobe_sync_dir() -> Path | None:
    env_path = os.environ.get("ADOBE_CLOUD_SYNC_DIR", "").strip()
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists():
            return p

    home = Path.home()
    candidates = [
        home / "Creative Cloud Files",
        home / "Adobe Creative Cloud Files",
        home / "Adobe" / "Creative Cloud Files",
    ]
    for path in candidates:
        if path.exists():
            return path
    for path in home.glob("Creative Cloud Files*"):
        if path.is_dir():
            return path
    return None


def upload_to_adobe_cloud(run_id: str, base_dir: str, files: List[Path]) -> Dict[str, Any]:
    root: Path | None = None
    if base_dir.strip():
        root = Path(base_dir).expanduser()
    else:
        root = detect_adobe_sync_dir()

    if root is None:
        raise RuntimeError(
            "Adobe Cloud sync folder not found. Set shipping.adobe.base_dir or ADOBE_CLOUD_SYNC_DIR."
        )

    return upload_to_local_sync_folder(root, run_id, files)


def detect_gdrive_sync_dir() -> Path | None:
    env_path = os.environ.get("GOOGLE_DRIVE_SYNC_DIR", "").strip()
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists():
            return p

    home = Path.home()
    candidates = [
        home / "Google Drive",
        home / "My Drive",
        home / "Drive",
    ]
    for path in candidates:
        if path.exists():
            return path
    for pattern in ("Google Drive*", "My Drive*", "Drive*"):
        for path in home.glob(pattern):
            if path.is_dir():
                return path
    return None


def upload_to_gdrive(run_id: str, base_dir: str, files: List[Path]) -> Dict[str, Any]:
    root: Path | None = Path(base_dir).expanduser() if base_dir.strip() else detect_gdrive_sync_dir()
    if root is None:
        raise RuntimeError(
            "Google Drive sync folder not found. Set shipping.gdrive.base_dir or GOOGLE_DRIVE_SYNC_DIR."
        )
    return upload_to_local_sync_folder(root, run_id, files)


def detect_proton_drive_dir() -> Path | None:
    env_path = os.environ.get("PROTON_DRIVE_SYNC_DIR", "").strip()
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists():
            return p

    home = Path.home()
    candidates = [
        home / "Proton Drive",
        home / "ProtonDrive",
    ]
    for path in candidates:
        if path.exists():
            return path
    for path in home.glob("Proton Drive*"):
        if path.is_dir():
            return path
    return None


def upload_to_proton(run_id: str, base_dir: str, files: List[Path]) -> Dict[str, Any]:
    root: Path | None = Path(base_dir).expanduser() if base_dir.strip() else detect_proton_drive_dir()
    if root is None:
        raise RuntimeError(
            "Proton Drive sync folder not found. Set shipping.proton.base_dir or PROTON_DRIVE_SYNC_DIR."
        )
    return upload_to_local_sync_folder(root, run_id, files)


def cleanup_old_runs(run_root: Path, keep_runs: int) -> Dict[str, int]:
    if keep_runs <= 0:
        return {"deleted_dirs": 0, "deleted_archives": 0}

    dirs = [p for p in run_root.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.name)
    if len(dirs) <= keep_runs:
        return {"deleted_dirs": 0, "deleted_archives": 0}

    deleted_dirs = 0
    deleted_archives = 0
    for old in dirs[: len(dirs) - keep_runs]:
        shutil.rmtree(old, ignore_errors=True)
        deleted_dirs += 1
        zip_path = old.with_suffix(".zip")
        if zip_path.exists():
            zip_path.unlink()
            deleted_archives += 1
    return {"deleted_dirs": deleted_dirs, "deleted_archives": deleted_archives}


def print_json_line(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True))


def run_sync_cycle(
    config: Dict[str, Any],
    run_root: Path,
    state_file: Path,
    latest_pointer: Path,
    args: argparse.Namespace,
) -> Tuple[int, Dict[str, Any]]:
    include_globs = [str(x) for x in config.get("include_globs", []) if str(x).strip()]
    if not include_globs:
        include_globs = ["**/*"]
    exclude_globs = [str(x) for x in config.get("exclude_globs", []) if str(x).strip()]
    if not exclude_globs:
        exclude_globs = list(DEFAULT_EXCLUDES)

    # Prevent self-trigger loops from autosync metadata files.
    runtime_excludes = list(exclude_globs)
    for p in (state_file, latest_pointer):
        try:
            rel = normalize_rel(p.resolve().relative_to(REPO_ROOT.resolve()))
        except ValueError:
            continue
        runtime_excludes.append(rel)
    try:
        run_rel = normalize_rel(run_root.resolve().relative_to(REPO_ROOT.resolve()))
        runtime_excludes.append(f"{run_rel}/**")
    except ValueError:
        pass

    previous_state = load_json(state_file, default={})
    previous_index = previous_state.get("index", {})
    if not isinstance(previous_index, dict):
        previous_index = {}
    previous_index = {
        str(k): {
            "size": int(v.get("size", 0)),
            "mtime_ns": int(v.get("mtime_ns", 0)),
        }
        for k, v in previous_index.items()
        if isinstance(v, dict)
    }
    previous_fingerprint = str(previous_state.get("fingerprint", "")).strip()
    dedupe_enabled = bool(config.get("dedupe_uploads", True))
    dedupe_history_limit = max(10, int(config.get("dedupe_history_limit", 200)))
    uploaded_fingerprints_raw = previous_state.get("uploaded_fingerprints", {})
    uploaded_fingerprints: Dict[str, List[str]] = {}
    if isinstance(uploaded_fingerprints_raw, dict):
        for target, values in uploaded_fingerprints_raw.items():
            if isinstance(values, list):
                cleaned = [str(v).strip() for v in values if str(v).strip()]
                if cleaned:
                    uploaded_fingerprints[str(target)] = cleaned

    current_index = collect_workspace_index(include_globs, runtime_excludes)
    current_fingerprint = compute_fingerprint(current_index)
    delta = compute_delta(previous_index, current_index)
    changed = bool(delta["changed"] or delta["removed"])

    if not args.force and current_fingerprint == previous_fingerprint and not changed:
        result = {
            "status": "no_changes",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "indexed_files": len(current_index),
        }
        print_json_line(result)
        return 0, result

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bundle = create_snapshot_bundle(run_root, run_id, delta, current_index, current_fingerprint)
    run_dir = bundle["run_dir"]
    archive_path = bundle["archive_path"]
    manifest_path = bundle["manifest_path"]
    index_path = bundle["index_path"]
    upload_files = [archive_path, manifest_path, index_path]

    ship_config = dict(config.get("shipping", {}))
    selected_targets = parse_ship_targets(args.ship_targets) if args.ship_targets else {
        key for key, value in ship_config.items() if isinstance(value, dict) and bool(value.get("enabled"))
    }
    shipping_results: Dict[str, Any] = {}
    shipping_errors: Dict[str, str] = {}

    if not args.no_upload and selected_targets:
        if "hf" in selected_targets:
            hf_cfg = ship_config.get("hf", {})
            try:
                seen = set(uploaded_fingerprints.get("hf", []))
                if dedupe_enabled and current_fingerprint in seen:
                    shipping_results["hf"] = {
                        "status": "skipped_duplicate",
                        "fingerprint": current_fingerprint,
                    }
                else:
                    shipping_results["hf"] = upload_to_hf(
                        run_dir=run_dir,
                        repo_id=str(hf_cfg.get("repo_id", "")).strip(),
                        path_prefix=str(hf_cfg.get("path_prefix", "local-workspace-sync")).strip(),
                        run_id=run_id,
                    )
                    uploaded_fingerprints.setdefault("hf", []).append(current_fingerprint)
            except Exception as exc:  # noqa: BLE001
                shipping_errors["hf"] = str(exc)

        if "github" in selected_targets:
            gh_cfg = ship_config.get("github", {})
            repo = str(gh_cfg.get("repo", "")).strip() or detect_github_repo()
            release_prefix = str(gh_cfg.get("release_prefix", "local-workspace-sync")).strip()
            try:
                if not repo:
                    raise RuntimeError("GitHub repo not configured and origin remote is unavailable.")
                seen = set(uploaded_fingerprints.get("github", []))
                if dedupe_enabled and current_fingerprint in seen:
                    shipping_results["github"] = {
                        "status": "skipped_duplicate",
                        "fingerprint": current_fingerprint,
                    }
                else:
                    shipping_results["github"] = upload_to_github_release(
                        repo=repo,
                        run_id=run_id,
                        release_prefix=release_prefix,
                        files=upload_files,
                    )
                    uploaded_fingerprints.setdefault("github", []).append(current_fingerprint)
            except Exception as exc:  # noqa: BLE001
                shipping_errors["github"] = str(exc)

        if "dropbox" in selected_targets:
            dbx_cfg = ship_config.get("dropbox", {})
            use_api = bool(dbx_cfg.get("use_api", False))
            base_path = str(dbx_cfg.get("base_path", "/SCBE/local-workspace-sync")).strip()
            base_dir = str(dbx_cfg.get("base_dir", "")).strip()
            try:
                seen = set(uploaded_fingerprints.get("dropbox", []))
                if dedupe_enabled and current_fingerprint in seen:
                    shipping_results["dropbox"] = {
                        "status": "skipped_duplicate",
                        "fingerprint": current_fingerprint,
                    }
                else:
                    if use_api:
                        shipping_results["dropbox"] = upload_to_dropbox(
                            run_id=run_id,
                            base_path=base_path,
                            files=upload_files,
                        )
                    else:
                        shipping_results["dropbox"] = upload_to_dropbox_local(
                            run_id=run_id,
                            base_dir=base_dir,
                            files=upload_files,
                        )
                    uploaded_fingerprints.setdefault("dropbox", []).append(current_fingerprint)
            except Exception as exc:  # noqa: BLE001
                shipping_errors["dropbox"] = str(exc)

        if "adobe" in selected_targets:
            adobe_cfg = ship_config.get("adobe", {})
            base_dir = str(adobe_cfg.get("base_dir", "")).strip()
            try:
                seen = set(uploaded_fingerprints.get("adobe", []))
                if dedupe_enabled and current_fingerprint in seen:
                    shipping_results["adobe"] = {
                        "status": "skipped_duplicate",
                        "fingerprint": current_fingerprint,
                    }
                else:
                    shipping_results["adobe"] = upload_to_adobe_cloud(
                        run_id=run_id,
                        base_dir=base_dir,
                        files=upload_files,
                    )
                    uploaded_fingerprints.setdefault("adobe", []).append(current_fingerprint)
            except Exception as exc:  # noqa: BLE001
                shipping_errors["adobe"] = str(exc)

        if "gdrive" in selected_targets:
            gdrive_cfg = ship_config.get("gdrive", {})
            base_dir = str(gdrive_cfg.get("base_dir", "")).strip()
            try:
                seen = set(uploaded_fingerprints.get("gdrive", []))
                if dedupe_enabled and current_fingerprint in seen:
                    shipping_results["gdrive"] = {
                        "status": "skipped_duplicate",
                        "fingerprint": current_fingerprint,
                    }
                else:
                    shipping_results["gdrive"] = upload_to_gdrive(
                        run_id=run_id,
                        base_dir=base_dir,
                        files=upload_files,
                    )
                    uploaded_fingerprints.setdefault("gdrive", []).append(current_fingerprint)
            except Exception as exc:  # noqa: BLE001
                shipping_errors["gdrive"] = str(exc)

        if "proton" in selected_targets:
            proton_cfg = ship_config.get("proton", {})
            base_dir = str(proton_cfg.get("base_dir", "")).strip()
            try:
                seen = set(uploaded_fingerprints.get("proton", []))
                if dedupe_enabled and current_fingerprint in seen:
                    shipping_results["proton"] = {
                        "status": "skipped_duplicate",
                        "fingerprint": current_fingerprint,
                    }
                else:
                    shipping_results["proton"] = upload_to_proton(
                        run_id=run_id,
                        base_dir=base_dir,
                        files=upload_files,
                    )
                    uploaded_fingerprints.setdefault("proton", []).append(current_fingerprint)
            except Exception as exc:  # noqa: BLE001
                shipping_errors["proton"] = str(exc)

    for target, history in list(uploaded_fingerprints.items()):
        uploaded_fingerprints[target] = history[-dedupe_history_limit:]

    summary = {
        "run_id": run_id,
        "status": "ok",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir.relative_to(REPO_ROOT)).replace("\\", "/"),
        "archive": str(archive_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "indexed_files": len(current_index),
        "delta_counts": {
            "added": len(delta["added"]),
            "modified": len(delta["modified"]),
            "removed": len(delta["removed"]),
            "changed": len(delta["changed"]),
        },
        "shipping": {
            "enabled": not args.no_upload,
            "targets": sorted(selected_targets),
            "results": shipping_results,
            "errors": shipping_errors,
        },
    }
    write_json(run_dir / "run_summary.json", summary)

    latest_pointer.parent.mkdir(parents=True, exist_ok=True)
    latest_pointer.write_text(str(run_dir.resolve()) + "\n", encoding="utf-8")

    keep_runs = int(config.get("keep_runs", 30))
    retention = cleanup_old_runs(run_root, keep_runs)
    summary["retention"] = retention
    write_json(run_dir / "run_summary.json", summary)

    next_state = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "fingerprint": current_fingerprint,
        "index": current_index,
        "uploaded_fingerprints": uploaded_fingerprints,
    }
    write_json(state_file, next_state)

    print_json_line(summary)

    if selected_targets and not args.no_upload and not shipping_results:
        return 1, summary
    return 0, summary


def main() -> int:
    args = parse_args()
    config_path = REPO_ROOT / args.config
    run_root = REPO_ROOT / args.run_root
    state_file = REPO_ROOT / args.state_file
    latest_pointer = REPO_ROOT / args.latest_pointer

    config = load_json(config_path, default={})
    run_root.mkdir(parents=True, exist_ok=True)

    interval = args.interval_seconds if args.interval_seconds > 0 else int(config.get("watch_interval_seconds", 120))
    interval = max(15, interval)

    if args.once:
        code, _ = run_sync_cycle(config, run_root, state_file, latest_pointer, args)
        return code

    while True:
        try:
            run_sync_cycle(config, run_root, state_file, latest_pointer, args)
        except KeyboardInterrupt:
            return 130
        except Exception as exc:  # noqa: BLE001
            print_json_line(
                {
                    "status": "error",
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "error": str(exc),
                }
            )
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
