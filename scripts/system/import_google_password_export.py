#!/usr/bin/env python3
"""Import Google password export CSV into secret store-backed browser profile index.

This script never writes raw passwords to disk. It stores username/password in
the local SCBE secret store and writes only secret-key references to profile
index JSON used by automation workflows.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.security.secret_store import set_secret

PROFILE_ROOT = REPO_ROOT / "external" / "credentials" / "browser_profiles"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    raw = (value or "").strip().lower()
    out = []
    for ch in raw:
        if ch.isalnum():
            out.append(ch)
        elif ch in {"-", "_"}:
            out.append(ch)
        else:
            out.append("-")
    compact = "".join(out).strip("-")
    return compact or "default"


def _mask_username(username: str) -> str:
    u = (username or "").strip()
    if not u:
        return ""
    if len(u) <= 4:
        return "*" * len(u)
    return u[:2] + ("*" * (len(u) - 4)) + u[-2:]


def _extract_domain(url: str) -> str:
    parsed = urlparse((url or "").strip())
    host = (parsed.hostname or "").strip().lower()
    return host


def _field(row: dict[str, Any], *names: str) -> str:
    for name in names:
        val = row.get(name)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def import_csv(csv_path: Path, profile_id: str) -> dict[str, Any]:
    profile_slug = _slug(profile_id)
    out_dir = PROFILE_ROOT / profile_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "credentials_index.json"

    entries: list[dict[str, Any]] = []
    imported = 0
    skipped = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            url = _field(row, "url", "origin", "website", "site")
            username = _field(row, "username", "user", "login", "email")
            password = _field(row, "password", "pass", "secret")
            if not (url and username and password):
                skipped += 1
                continue

            domain = _extract_domain(url)
            if not domain:
                skipped += 1
                continue

            fingerprint = hashlib.sha256(f"{profile_slug}|{domain}|{username}".encode("utf-8")).hexdigest()[:20]
            user_secret_name = f"BROWSER_{profile_slug.upper()}_{fingerprint}_USERNAME"
            pass_secret_name = f"BROWSER_{profile_slug.upper()}_{fingerprint}_PASSWORD"

            note = f"profile={profile_slug};domain={domain};source=google_password_export"
            set_secret(user_secret_name, username, note=note)
            set_secret(pass_secret_name, password, note=note)

            entries.append(
                {
                    "domain": domain,
                    "url": url,
                    "username_secret": user_secret_name,
                    "password_secret": pass_secret_name,
                    "username_hint": _mask_username(username),
                    "source": "google_password_export",
                }
            )
            imported += 1

    payload = {
        "schema_version": "1.0.0",
        "profile_id": profile_slug,
        "updated_at": _now_iso(),
        "source_csv": str(csv_path),
        "entry_count": len(entries),
        "entries": entries,
    }
    index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "profile_id": profile_slug,
        "index_path": str(index_path),
        "imported": imported,
        "skipped": skipped,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Google password CSV into SCBE secret-backed browser profile.")
    parser.add_argument("--csv", required=True, help="Path to Google password export CSV")
    parser.add_argument("--profile-id", default="default", help="Browser profile id")
    args = parser.parse_args()

    csv_path = Path(args.csv).expanduser().resolve()
    if not csv_path.exists():
        print(json.dumps({"ok": False, "error": f"csv_not_found: {csv_path}"}))
        return 1

    result = import_csv(csv_path, args.profile_id)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
