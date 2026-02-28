#!/usr/bin/env python3
"""Bind n8n credential IDs into workflow JSON files.

Use this to replace placeholder credential IDs after importing workflows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


OPENAI_PLACEHOLDERS = {
    "OPENAI_CREDENTIAL_ID",
    "REPLACE_WITH_OPENAI_CREDENTIAL_ID",
    "credential-id",
}
TELEGRAM_PLACEHOLDERS = {
    "TELEGRAM_CREDENTIAL_ID",
    "REPLACE_ME",
}


def bind_workflow(
    path: Path,
    openai_id: str | None,
    telegram_id: str | None,
    dry_run: bool,
) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"file": str(path), "updated": 0, "issues": ["root_not_object"]}

    nodes = data.get("nodes", [])
    if not isinstance(nodes, list):
        return {"file": str(path), "updated": 0, "issues": ["nodes_not_list"]}

    updated = 0
    unresolved: list[str] = []

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_name = str(node.get("name", "unnamed"))
        creds = node.get("credentials")
        if not isinstance(creds, dict):
            continue

        for cred_key, cred_value in creds.items():
            if not isinstance(cred_value, dict):
                continue
            raw_id = str(cred_value.get("id", "")).strip()

            if cred_key == "openAiApi" and raw_id in OPENAI_PLACEHOLDERS:
                if openai_id:
                    cred_value["id"] = openai_id
                    updated += 1
                else:
                    unresolved.append(f"{node_name}:openAiApi:{raw_id}")

            if cred_key == "telegramApi" and raw_id in TELEGRAM_PLACEHOLDERS:
                if telegram_id:
                    cred_value["id"] = telegram_id
                    updated += 1
                else:
                    unresolved.append(f"{node_name}:telegramApi:{raw_id}")

    if updated and not dry_run:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    return {
        "file": str(path),
        "updated": updated,
        "unresolved": unresolved,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind n8n credential IDs into workflow files.")
    parser.add_argument("--path", default="workflows/n8n", help="Workflow folder")
    parser.add_argument("--openai-id", default="", help="n8n credential ID for openAiApi")
    parser.add_argument("--telegram-id", default="", help="n8n credential ID for telegramApi")
    parser.add_argument("--dry-run", action="store_true", help="Report changes only")
    args = parser.parse_args()

    workflow_dir = Path(args.path)
    files = sorted(workflow_dir.glob("*.workflow.json"))
    if not files:
        print(json.dumps({"status": "error", "reason": "no_workflow_files", "path": str(workflow_dir)}))
        return 1

    openai_id = args.openai_id.strip() or None
    telegram_id = args.telegram_id.strip() or None

    results = [
        bind_workflow(path, openai_id=openai_id, telegram_id=telegram_id, dry_run=args.dry_run)
        for path in files
    ]
    total_updated = sum(int(r.get("updated", 0)) for r in results)
    unresolved_count = sum(len(r.get("unresolved", [])) for r in results)

    payload = {
        "status": "ok",
        "dry_run": args.dry_run,
        "path": str(workflow_dir),
        "files": len(files),
        "updated_bindings": total_updated,
        "unresolved_bindings": unresolved_count,
        "results": results,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

