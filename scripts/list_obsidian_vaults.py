#!/usr/bin/env python3
"""List local Obsidian vaults from the desktop config."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _vault_config_path() -> Path:
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        return Path(appdata) / "Obsidian" / "obsidian.json"
    return Path.home() / "AppData" / "Roaming" / "Obsidian" / "obsidian.json"


def _to_iso(ts_ms: Any) -> str:
    try:
        ts = float(ts_ms) / 1000.0
    except Exception:
        return ""
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _load_vaults(config_path: Path) -> List[Dict[str, Any]]:
    if not config_path.exists():
        return []
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    vaults_obj = payload.get("vaults", {})
    out: List[Dict[str, Any]] = []
    if isinstance(vaults_obj, dict):
        for vault_id, meta in vaults_obj.items():
            if not isinstance(meta, dict):
                continue
            raw_path = str(meta.get("path", "")).strip()
            out.append(
                {
                    "vault_id": str(vault_id),
                    "path": raw_path,
                    "name": Path(raw_path).name if raw_path else "",
                    "ts": meta.get("ts"),
                    "ts_utc": _to_iso(meta.get("ts")),
                }
            )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="List Obsidian vault paths from local desktop config.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    cfg = _vault_config_path()
    vaults = _load_vaults(cfg)
    payload = {
        "config_path": str(cfg),
        "count": len(vaults),
        "vaults": vaults,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Config: {cfg}")
    print(f"Vaults: {len(vaults)}")
    for row in vaults:
        print(f"- {row['name']} :: {row['path']}")
        if row["ts_utc"]:
            print(f"  last_seen_utc: {row['ts_utc']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
