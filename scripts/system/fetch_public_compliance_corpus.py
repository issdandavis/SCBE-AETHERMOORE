#!/usr/bin/env python3
"""Download publicly distributable compliance source texts into a local corpus folder.

Only HTTP(S) sources listed in config/compliance/public_sources.json with fetch_kind
http_get are fetched. Purchase-only frameworks (ISO full text, proprietary SOC packs)
must be acquired under license manually — see docs/compliance/COMPLIANCE_CORPUS.md.

Usage:
    python scripts/system/fetch_public_compliance_corpus.py
    python scripts/system/fetch_public_compliance_corpus.py --dry-run
    python scripts/system/fetch_public_compliance_corpus.py --only nist_ai_rmf_100_1,nist_csf_2_0
    python scripts/system/fetch_public_compliance_corpus.py --include-large
"""

from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "config" / "compliance" / "public_sources.json"
DEFAULT_OUT = REPO_ROOT / "docs" / "compliance" / "corpus" / "fetched"
USER_AGENT = (
    "SCBE-AETHERMOORE-compliance-corpus/1.0 (+local research; contact via repo)"
)


def _load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "sources" not in data:
        raise ValueError("manifest must be a JSON object with 'sources' array")
    return data


def _filter_sources(
    sources: list[dict[str, Any]],
    *,
    only_ids: set[str] | None,
    include_large: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in sources:
        if s.get("fetch_kind") != "http_get":
            continue
        sid = str(s.get("id", ""))
        if only_ids is not None and sid not in only_ids:
            continue
        if s.get("large") and not include_large:
            continue
        out.append(s)
    return out


def _fetch_url(url: str, dest: Path, timeout_s: float = 120.0) -> dict[str, Any]:
    """Return metadata dict with sha256 and bytes_written."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ctx = ssl.create_default_context()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(
        req, timeout=timeout_s, context=ctx
    ) as resp:  # noqa: S310 — curated URLs only
        body = resp.read()
    dest.write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    return {"sha256": digest, "bytes": len(body)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT, help="Directory for downloaded files"
    )
    parser.add_argument(
        "--only", type=str, default="", help="Comma-separated source ids"
    )
    parser.add_argument(
        "--include-large",
        action="store_true",
        help="Include EUR-Lex HTML sources marked large",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest = _load_manifest(args.manifest)
    sources = manifest.get("sources", [])
    if not isinstance(sources, list):
        raise SystemExit("manifest 'sources' must be an array")

    only_ids: set[str] | None = None
    if args.only.strip():
        only_ids = {x.strip() for x in args.only.split(",") if x.strip()}

    selected = _filter_sources(
        sources, only_ids=only_ids, include_large=args.include_large
    )
    if not selected:
        print(
            "No http_get sources selected (check --only, or use --include-large for EUR-Lex pages).",
            file=sys.stderr,
        )
        return 1

    index: list[dict[str, Any]] = []
    for s in selected:
        sid = str(s["id"])
        url = str(s["url"])
        save_as = str(s.get("save_as") or f"{sid}.bin")
        dest = args.out / save_as
        rel_path = dest.relative_to(REPO_ROOT).as_posix()
        entry: dict[str, Any] = {
            "id": sid,
            "title": s.get("title", ""),
            "url": url,
            "path": rel_path,
            "tags": s.get("tags", []),
        }
        if args.dry_run:
            entry["dry_run"] = True
            index.append(entry)
            continue
        try:
            meta = _fetch_url(url, dest)
            entry.update(meta)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            entry["error"] = str(exc)
        index.append(entry)

    summary_path = args.out / "fetch_index.json"
    if not args.dry_run:
        manifest_rel = args.manifest.resolve().relative_to(REPO_ROOT).as_posix()
        summary_path.write_text(
            json.dumps({"manifest": manifest_rel, "results": index}, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote {summary_path.relative_to(REPO_ROOT)}")
    else:
        print(json.dumps({"dry_run": True, "results": index}, indent=2))

    errors = [x for x in index if "error" in x]
    if errors:
        for e in errors:
            print(f"ERROR {e['id']}: {e['error']}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
