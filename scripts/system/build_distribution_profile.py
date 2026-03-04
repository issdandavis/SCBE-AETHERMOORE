#!/usr/bin/env python3
"""Build lean zip bundles from configured distribution profiles.

Usage:
  python scripts/system/build_distribution_profile.py --profile core_public
  python scripts/system/build_distribution_profile.py --profile sellable_bundle
"""

from __future__ import annotations

import argparse
import fnmatch
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_CONFIG = REPO_ROOT / "config" / "governance" / "distribution_profiles.json"
OUT_DIR = REPO_ROOT / "artifacts" / "release_profiles"


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_profiles() -> dict:
    return json.loads(PROFILE_CONFIG.read_text(encoding="utf-8"))


def _all_files() -> list[Path]:
    out: list[Path] = []
    for p in REPO_ROOT.rglob("*"):
        if p.is_file():
            out.append(p)
    return out


def _match_any(rel_path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, pat) for pat in patterns)


def _select_files(include: list[str], exclude: list[str]) -> list[Path]:
    chosen: list[Path] = []
    for p in _all_files():
        rel = p.relative_to(REPO_ROOT).as_posix()
        if _match_any(rel, include) and not _match_any(rel, exclude):
            chosen.append(p)
    return sorted(chosen)


def _bundle(profile_name: str, files: list[Path]) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _now_stamp()
    zip_path = OUT_DIR / f"scbe_{profile_name}_{stamp}.zip"
    manifest_path = OUT_DIR / f"scbe_{profile_name}_{stamp}.manifest.json"

    total_bytes = 0
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
        for f in files:
            rel = f.relative_to(REPO_ROOT)
            zf.write(f, arcname=str(rel))
            total_bytes += f.stat().st_size

    manifest = {
        "profile": profile_name,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "file_count": len(files),
        "uncompressed_bytes": total_bytes,
        "zip_path": str(zip_path),
        "files": [str(f.relative_to(REPO_ROOT).as_posix()) for f in files],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return zip_path, manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build distribution profile bundle.")
    parser.add_argument("--profile", required=True, help="Profile name from distribution_profiles.json")
    args = parser.parse_args()

    cfg = _load_profiles()
    profiles = cfg.get("profiles", {})
    if args.profile not in profiles:
        available = ", ".join(sorted(profiles.keys()))
        raise SystemExit(f"Unknown profile '{args.profile}'. Available: {available}")

    profile = profiles[args.profile]
    include = profile.get("include", [])
    exclude = profile.get("exclude", [])
    files = _select_files(include, exclude)

    zip_path, manifest_path = _bundle(args.profile, files)
    print(
        json.dumps(
            {
                "ok": True,
                "profile": args.profile,
                "file_count": len(files),
                "zip": str(zip_path),
                "manifest": str(manifest_path),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

