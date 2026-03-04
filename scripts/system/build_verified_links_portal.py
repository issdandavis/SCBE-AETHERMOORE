#!/usr/bin/env python3
"""Build a static verified-links portal + manifest from a registry JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_hash(entries: list[dict]) -> str:
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def safe_host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build verified links portal.")
    p.add_argument(
        "--registry",
        default="config/governance/verified_links_registry.json",
        help="Registry JSON file.",
    )
    p.add_argument(
        "--out-dir",
        default="artifacts/verified_links_portal",
        help="Output directory for portal assets.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    registry_path = (REPO_ROOT / args.registry).resolve()
    out_dir = (REPO_ROOT / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    entries = [e for e in registry.get("entries", []) if isinstance(e, dict) and e.get("enabled", True)]

    rows: list[dict] = []
    for e in entries:
        url = str(e.get("url", "")).strip()
        rows.append(
            {
                "id": str(e.get("id", "")).strip(),
                "name": str(e.get("name", "")).strip(),
                "url": url,
                "host": safe_host(url),
                "category": str(e.get("category", "")).strip(),
                "tags": [str(t) for t in e.get("tags", []) if str(t).strip()],
            }
        )

    digest = canonical_hash(rows)
    manifest = {
        "schema_version": "1.0.0",
        "generated_at_utc": utc_now(),
        "portal_name": registry.get("portal_name", "Verified Links Portal"),
        "owner": registry.get("owner", ""),
        "entry_count": len(rows),
        "registry_source": str(registry_path),
        "links_digest_sha256": digest,
        "entries": rows,
    }

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "<!doctype html>",
        "<html lang='en'>",
        "<head>",
        "  <meta charset='utf-8' />",
        "  <meta name='viewport' content='width=device-width, initial-scale=1' />",
        f"  <title>{manifest['portal_name']}</title>",
        "  <style>",
        "    :root { --bg:#0e1624; --card:#162338; --text:#eaf1ff; --muted:#9fb4d4; --accent:#4ad5a0; }",
        "    body { margin:0; font-family: 'Segoe UI', Tahoma, sans-serif; background: radial-gradient(circle at 20% 20%, #1c2f4f, var(--bg)); color:var(--text); }",
        "    .wrap { max-width: 980px; margin: 0 auto; padding: 28px; }",
        "    .meta { color: var(--muted); font-size: 0.95rem; }",
        "    .grid { display:grid; grid-template-columns: repeat(auto-fit,minmax(260px,1fr)); gap:14px; margin-top:18px; }",
        "    .card { background: linear-gradient(180deg, #1a2a44, var(--card)); border:1px solid #2b4268; border-radius:14px; padding:14px; }",
        "    .host { color: var(--muted); font-size: 0.88rem; }",
        "    a { color: var(--accent); text-decoration:none; }",
        "    .tags { margin-top:8px; display:flex; flex-wrap:wrap; gap:6px; }",
        "    .tag { font-size:0.75rem; color:#d2e8ff; background:#20314f; border:1px solid #39547f; border-radius:999px; padding:2px 8px; }",
        "    code { color:#d2f7e8; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <div class='wrap'>",
        f"    <h1>{manifest['portal_name']}</h1>",
        f"    <div class='meta'>Owner: {manifest['owner']} | Generated: {manifest['generated_at_utc']} | Digest: <code>{digest}</code></div>",
        "    <div class='grid'>",
    ]

    for row in rows:
        tags = "".join([f"<span class='tag'>{t}</span>" for t in row["tags"]])
        lines.extend(
            [
                "      <div class='card'>",
                f"        <div><strong>{row['name']}</strong></div>",
                f"        <div class='host'>{row['host']} · {row['category']}</div>",
                f"        <div style='margin-top:8px;'><a href='{row['url']}' target='_blank' rel='noopener noreferrer'>{row['url']}</a></div>",
                f"        <div class='tags'>{tags}</div>",
                "      </div>",
            ]
        )

    lines.extend(
        [
            "    </div>",
            "  </div>",
            "</body>",
            "</html>",
        ]
    )
    (out_dir / "index.html").write_text("\n".join(lines), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "manifest": str(manifest_path),
                "portal_index": str(out_dir / "index.html"),
                "entry_count": len(rows),
                "digest": digest,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
