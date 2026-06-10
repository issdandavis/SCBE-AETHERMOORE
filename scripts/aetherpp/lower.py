#!/usr/bin/env python3
"""Lower Aether++ AST to a canonical route packet."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

from src.ca_lexicon import LANG_MAP
from src.crypto.sacred_tongue_payload_bijection import prove_dict


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash_obj(obj: Any) -> str:
    raw = json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def lower_ast(
    nodes: list[dict[str, Any]], *, source_name: str = "inline.aether"
) -> dict[str, Any]:
    goal = ""
    command_key = "route"
    language = "python"
    tongue = "KO"
    operations: list[dict[str, Any]] = []

    for idx, node in enumerate(nodes, start=1):
        kind = node["kind"]
        data = node["data"]
        if kind == "set_goal":
            goal = str(data["goal"])
        elif kind == "encode":
            command_key = (
                str(data["content"]).strip().split("(")[0].split()[0].lower() or "route"
            )
            tongue = str(data["tongue"]).upper()
            language = LANG_MAP.get(tongue, "python")
        elif kind == "apply_fold":
            tongue = str(data["tongue"]).upper()
            language = LANG_MAP.get(tongue, language)
        operations.append({"step": idx, "kind": kind, "data": data})

    core = {
        "schema_version": "geoseal-aether-route-v1",
        "created_at": utc_now(),
        "source_name": source_name,
        "goal": goal,
        "shell_contract": {
            "route_packet": {
                "command_key": command_key,
                "route_tongue": tongue,
                "route_language": language,
                "statement_count": len(nodes),
                "ast_sha256": _hash_obj(nodes),
            }
        },
        "operations": operations,
    }
    core["build_bijection"] = prove_dict(
        {k: v for k, v in core.items() if k != "build_bijection"}
    )
    return core
