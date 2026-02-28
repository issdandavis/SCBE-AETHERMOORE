#!/usr/bin/env python3
"""Validate n8n workflow JSON files for common import/runtime issues."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PLACEHOLDER_MARKERS = {
    "REPLACE_ME",
    "credential-id",
    "REPLACE_WITH_OPENAI_CREDENTIAL_ID",
}

OPENAI_TYPES = {
    "@n8n/n8n-nodes-langchain.embeddingsOpenAi",
    "@n8n/n8n-nodes-langchain.lmChatOpenAi",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_file(path: Path) -> list[str]:
    issues: list[str] = []
    try:
        wf = _load_json(path)
    except Exception as exc:  # noqa: BLE001
        return [f"json_error: {exc}"]

    if not isinstance(wf, dict):
        return ["root_not_object"]

    for key in ("name", "nodes", "connections"):
        if key not in wf:
            issues.append(f"missing_{key}")

    nodes = wf.get("nodes", [])
    if not isinstance(nodes, list):
        issues.append("nodes_not_list")
        return issues

    seen_names: set[str] = set()
    seen_ids: set[str] = set()

    for node in nodes:
        if not isinstance(node, dict):
            issues.append("node_not_object")
            continue

        name = str(node.get("name", ""))
        node_id = str(node.get("id", ""))
        node_type = str(node.get("type", ""))

        if not name:
            issues.append("node_missing_name")
        elif name in seen_names:
            issues.append(f"duplicate_node_name:{name}")
        seen_names.add(name)

        if node_id:
            if node_id in seen_ids:
                issues.append(f"duplicate_node_id:{node_id}")
            seen_ids.add(node_id)
        else:
            issues.append(f"node_missing_id:{name or node_type}")

        creds = node.get("credentials") or {}
        if isinstance(creds, dict):
            for cred_name, cred_val in creds.items():
                if not isinstance(cred_val, dict):
                    continue
                cid = str(cred_val.get("id", "")).strip()
                if cid in PLACEHOLDER_MARKERS:
                    issues.append(f"placeholder_credential_id:{name}:{cred_name}:{cid}")

        if node_type in OPENAI_TYPES:
            openai = (creds or {}).get("openAiApi")
            if not openai:
                issues.append(f"missing_openai_credential:{name}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate n8n workflow files.")
    parser.add_argument(
        "--path",
        default="workflows/n8n",
        help="Directory containing *.workflow.json files",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any issue is found.",
    )
    args = parser.parse_args()

    root = Path(args.path)
    files = sorted(root.glob("*.workflow.json"))
    if not files:
        print(f"[WARN] No workflow files found under {root}")
        return 1

    total_issues = 0
    for file_path in files:
        issues = validate_file(file_path)
        if issues:
            total_issues += len(issues)
            print(f"[ISSUES] {file_path.name}")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"[OK] {file_path.name}")

    print(f"[SUMMARY] files={len(files)} issues={total_issues}")
    if args.strict and total_issues:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
