#!/usr/bin/env python3
"""Harvest unique lightweight files from related repo variants into master.

This script is intended for duplicate-family cleanup workflows:
1) choose a canonical repo
2) compare variant repos to canonical
3) copy unique small files into external/intake/<family>/<variant>/

Usage:
  python scripts/system/github_family_intake.py ^
    --owner issdandavis ^
    --canonical AI-Workflow-Architect ^
    --variants AI-Workflow-Architect-1 AI-Workflow-Architect-1.2.2 ai-workflow-architect-main ai-workflow-architect-pro ai-workflow-architect-replit ^
    --family ai-workflow-architect
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INTAKE_ROOT = REPO_ROOT / "external" / "intake"
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "governance"

ALLOWED_EXTS = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".py", ".ts", ".js"}
MAX_FILE_BYTES = 512 * 1024  # 512 KB cap per harvested file
MAX_FILES_PER_REPO = 800
SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
    "attached_assets",
}


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"Command failed: {' '.join(cmd)}")
    return proc.stdout


def _clone_shallow(owner: str, repo: str, base_dir: Path) -> Path:
    target = base_dir / repo
    _run(["gh", "repo", "clone", f"{owner}/{repo}", str(target), "--", "--depth", "1"])
    return target


def _iter_candidate_files(repo_dir: Path) -> list[Path]:
    out: list[Path] = []
    for p in repo_dir.rglob("*"):
        if not p.is_file():
            continue
        rel_parts = set(part.lower() for part in p.relative_to(repo_dir).parts)
        if SKIP_DIRS.intersection(rel_parts):
            continue
        if p.suffix.lower() not in ALLOWED_EXTS:
            continue
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        out.append(p)
        if len(out) >= MAX_FILES_PER_REPO:
            break
    return out


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(65536)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Harvest unique lightweight files from repo family variants.")
    parser.add_argument("--owner", required=True, help="GitHub owner/org")
    parser.add_argument("--canonical", required=True, help="Canonical repo name")
    parser.add_argument("--variants", nargs="+", required=True, help="Variant repo names")
    parser.add_argument("--family", required=True, help="Family name label")
    args = parser.parse_args()

    INTAKE_ROOT.mkdir(parents=True, exist_ok=True)
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    family_root = INTAKE_ROOT / args.family
    family_root.mkdir(parents=True, exist_ok=True)

    report: dict[str, object] = {
        "owner": args.owner,
        "family": args.family,
        "canonical": args.canonical,
        "variants": args.variants,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "harvested": {},
    }

    with tempfile.TemporaryDirectory(prefix="scbe-family-intake-") as td:
        work = Path(td)
        canonical_dir = _clone_shallow(args.owner, args.canonical, work)
        canonical_files = _iter_candidate_files(canonical_dir)
        canonical_hashes = {_sha256(p) for p in canonical_files}

        for variant in args.variants:
            variant_dir = _clone_shallow(args.owner, variant, work)
            files = _iter_candidate_files(variant_dir)
            kept = 0
            checked = 0
            copied_paths: list[str] = []

            for f in files:
                checked += 1
                digest = _sha256(f)
                if digest in canonical_hashes:
                    continue
                rel = f.relative_to(variant_dir)
                dst = family_root / variant / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
                copied_paths.append(str((Path("external") / "intake" / args.family / variant / rel).as_posix()))
                kept += 1

            report["harvested"][variant] = {
                "checked_files": checked,
                "copied_unique_files": kept,
                "copied_paths": copied_paths[:200],  # cap report verbosity
            }

    out = ARTIFACT_ROOT / f"github_family_intake_{args.family}_{_stamp()}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(out), "intake_root": str(family_root)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
