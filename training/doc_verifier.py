#!/usr/bin/env python3
"""Build a deterministic source-document verification manifest.

The cloud kernel pipeline uses this manifest to decide which ingested
``source_path`` values are backed by files present in the repository at run time.
This is a lightweight provenance gate, not a semantic fact checker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATTERNS = (
    "docs/OFFLINE_MODE_SPEC.md",
    "docs/MULTI_AI_COORDINATION.md",
    "docs/HYDRA_COORDINATION.md",
    "docs/SCBE_CONTEXT_AETHERBROWSE_AGENT.md",
    "docs/gateway/*.md",
    "docs/map-room/*.md",
    "docs/news/*.md",
    "docs/scbe-knowledge-v4.aetherbrowse.yaml",
    "training/kernel_manifest.yaml",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a JSON manifest for repository training documents.")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout as well as writing --out.")
    parser.add_argument("--out", required=True, help="Manifest output path.")
    parser.add_argument(
        "--glob",
        action="append",
        default=[],
        help="Source glob to verify. Repeatable; defaults to cloud-kernel source globs.",
    )
    parser.add_argument(
        "--attest",
        default="",
        help="Comma-separated attester labels to include in each verified document record.",
    )
    return parser.parse_args()


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def expand_patterns(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(sorted(REPO_ROOT.glob(pattern)))
    return sorted({path.resolve() for path in paths if path.is_file()}, key=lambda p: repo_rel(p))


def attester_list(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def build_manifest(patterns: list[str], attesters: list[str]) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    documents: list[dict[str, Any]] = []

    for path in expand_patterns(patterns):
        rel = repo_rel(path)
        stat = path.stat()
        file_hash = sha256_file(path)
        documents.append(
            {
                "filename": rel,
                "bytes": stat.st_size,
                "sha256": file_hash,
                "verification": {
                    "status": "verified",
                    "method": "sha256_file_present",
                    "verified_at": generated_at,
                    "attesters": attesters,
                },
            }
        )

    return {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "repo_root": str(REPO_ROOT),
        "patterns": patterns,
        "document_count": len(documents),
        "documents": documents,
    }


def main() -> int:
    args = parse_args()
    patterns = unique_ordered(list(DEFAULT_PATTERNS) + list(args.glob or []))
    manifest = build_manifest(patterns, attester_list(args.attest))

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    out_path.write_text(rendered, encoding="utf-8")

    if args.json:
        print(rendered, end="")
    else:
        print(f"Verified {manifest['document_count']} documents -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
