#!/usr/bin/env python3
"""List Obsidian vaults from the local Obsidian config."""

import json
import os
from pathlib import Path


def main() -> int:
    appdata = os.getenv("APPDATA")
    if not appdata:
        print("APPDATA is not set.")
        return 1

    cfg = Path(appdata) / "Obsidian" / "obsidian.json"
    if not cfg.exists():
        print(f"Obsidian config not found: {cfg}")
        return 1

    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Failed to parse {cfg}: {exc}")
        return 1

    vaults = data.get("vaults", {})
    if not vaults:
        print("No vaults registered in Obsidian config.")
        return 0

    print(f"Config: {cfg}")
    print(f"Vault count: {len(vaults)}")

    rows = []
    for vault_id, meta in vaults.items():
        rows.append(
            {
                "id": vault_id,
                "path": meta.get("path", ""),
                "open": bool(meta.get("open", False)),
                "ts": int(meta.get("ts", 0) or 0),
            }
        )

    rows.sort(key=lambda x: x["ts"], reverse=True)
    for row in rows:
        print(f"- id={row['id']} open={str(row['open']).lower()} ts={row['ts']} path={row['path']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
