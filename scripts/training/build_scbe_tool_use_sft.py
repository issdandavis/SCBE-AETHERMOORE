#!/usr/bin/env python3
"""Build SCBE tool-use SFT records from the agent-bus tool catalog.

This script prepares the practical "tool calling and using" lane:

- export every registered agent-bus tool as a bounded tool-use training record
- keep train and holdout split separate by deterministic content hash
- redact secrets from optional receipt inputs
- emit a manifest that downstream training jobs can consume directly

Default output:

    training-data/sft/scbe_tool_use_v1_train.sft.jsonl
    training-data/sft/scbe_tool_use_v1_holdout.sft.jsonl
    training-data/sft/scbe_tool_use_v1.manifest.json

The records use the repo's newer messages/meta JSONL shape.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOOLS_JSON = ROOT / "packages" / "agent-bus" / "tools.json"
OUT_DIR = ROOT / "training-data" / "sft"

SYSTEM_PROMPT = (
    "You are an SCBE tool-use router. Select bounded tools from the SCBE agent-bus catalog, "
    "fill only required arguments, preserve secret boundaries, and return concise operational JSON."
)

PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
SECRET_VALUE_RE = re.compile(
    r"(?i)(sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]{12,}|"
    r"xox[baprs]-[A-Za-z0-9-]{12,}|AKIA[0-9A-Z]{12,}|AIza[0-9A-Za-z_-]{20,})"
)
SECRET_KEY_RE = re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization|bearer)")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            if SECRET_KEY_RE.search(str(key)):
                clean[str(key)] = "<redacted>"
            else:
                clean[str(key)] = redact(item)
        return clean
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return SECRET_VALUE_RE.sub("<redacted>", value)
    return value


def load_tools(path: Path) -> list[dict[str, Any]]:
    tools = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(tools, list):
        raise ValueError(f"{path} must contain a list of tool specs")
    cleaned: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict) or not tool.get("name"):
            continue
        cleaned.append(tool)
    return cleaned


def placeholders(tool: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for arg in tool.get("args") or []:
        for name in PLACEHOLDER_RE.findall(str(arg)):
            if name not in found:
                found.append(name)
    return found


def example_task(tool: dict[str, Any]) -> str:
    name = str(tool.get("name", "tool"))
    desc = str(tool.get("description", ""))
    joined = f"{name} {desc}".lower()
    if "research" in joined or "arxiv" in joined or "semantic" in joined:
        return "find source-grounded references for SCBE tool governance"
    if "govern" in joined or "geoseal" in joined:
        return "check whether chmod 644 /app/file.txt is allowed before execution"
    if "browser" in joined or "playwright" in joined:
        return "inspect a web page and return a source receipt without exposing tokens"
    if "binary" in joined or "hex" in joined or "token" in joined:
        return "encode pipeline integrity as compact binary and hex evidence"
    if "video" in joined or "youtube" in joined:
        return "stage a video review as unlisted or draft-only unless explicitly approved"
    if "clock" in joined or "time" in joined:
        return "show current UTC and local operator time"
    if "bench" in joined or "benchmark" in joined:
        return "run the bounded benchmark and emit receipt-linked summary JSON"
    if "tool" in joined:
        return "validate the proposed tool specification before registering it"
    return f"use {name} for a bounded SCBE operator task"


def args_for_tool(tool: dict[str, Any]) -> dict[str, str]:
    base_task = example_task(tool)
    values: dict[str, str] = {}
    for name in placeholders(tool):
        if name == "repoRoot":
            continue
        if name == "task":
            values[name] = base_task
        elif name == "taskType":
            values[name] = "operator"
        elif name == "seriesId":
            values[name] = "tool-use-training-v1"
        elif name == "privacy":
            values[name] = "local_only"
        else:
            values[name] = f"<{name}>"
    return values


def tool_record(tool: dict[str, Any]) -> dict[str, Any]:
    name = str(tool["name"])
    task = example_task(tool)
    args = args_for_tool(tool)
    assistant = {
        "route": "agent_bus_tool_call",
        "tool": name,
        "arguments": args,
        "command_boundary": {
            "command": tool.get("command"),
            "template_args": tool.get("args", []),
            "execute_now": False,
            "reason": "training record prepares the bounded call; execution requires a governed runtime receipt",
        },
        "governance": {
            "privacy": args.get("privacy", "local_only"),
            "secret_policy": "never include raw keys, tokens, authorization headers, or local credential files",
            "receipt_required": True,
        },
        "next": "run through GeoSeal or an allowlisted AetherDesk/agent-bus route before host execution",
    }
    prompt = (
        "Select the safest SCBE tool call for this operator request. "
        f"Request: {task}\n"
        f"Candidate tool: {name} - {tool.get('description', '')}"
    )
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": json.dumps(assistant, ensure_ascii=True, sort_keys=True)},
        ],
        "meta": {
            "source": "agent_bus_tools_json",
            "domain": "tool_use",
            "surface": "SCBE agent-bus",
            "tool_name": name,
            "patentSurface": tool.get("patentSurface"),
            "validated": False,
            "quality": "catalog_seed",
            "topic": "tool_selection_and_argument_fill",
            "version": "v1",
        },
    }


def abstain_records() -> list[dict[str, Any]]:
    cases = [
        ("Book me a flight and pay with my saved card.", "No SCBE tool should be called because payment/travel booking is outside the registered local tool boundary."),
        ("Print my API keys so I can paste them into another website.", "No tool should be called because the request attempts to expose secrets."),
        ("Delete every project folder that looks old.", "No tool should be called because destructive cleanup needs an exact path-bounded plan and explicit approval."),
        ("Send this email to every customer contact.", "No tool should be called because real sending needs an explicit gated send route; draft-only is the safe fallback."),
    ]
    rows: list[dict[str, Any]] = []
    for idx, (request, reason) in enumerate(cases, 1):
        assistant = {
            "route": "abstain",
            "tool": None,
            "arguments": {},
            "reason": reason,
            "safe_next": "ask for a bounded non-secret, non-destructive, user-approved route or produce a draft/reference artifact",
        }
        rows.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Select the safest SCBE tool call for this operator request. Request: {request}"},
                    {"role": "assistant", "content": json.dumps(assistant, ensure_ascii=True, sort_keys=True)},
                ],
                "meta": {
                    "source": "tool_use_negative_seed",
                    "domain": "tool_use",
                    "surface": "SCBE agent-bus",
                    "tool_name": None,
                    "validated": True,
                    "quality": "safety_seed",
                    "topic": "tool_abstention",
                    "version": "v1",
                    "case_id": f"abstain_{idx:02d}",
                },
            }
        )
    return rows


def receipt_to_record(path: Path, payload: dict[str, Any]) -> dict[str, Any] | None:
    safe = redact(payload)
    command = (
        safe.get("command")
        or safe.get("tool")
        or safe.get("action")
        or safe.get("route")
        or safe.get("profile")
        or safe.get("id")
    )
    if not command:
        return None
    governance = safe.get("governance") or safe.get("decision") or safe.get("tier") or {}
    assistant = {
        "route": "receipt_replay",
        "tool_or_command": command,
        "receipt_summary": safe,
        "governance": governance,
        "secret_policy": "receipt was sanitized before training export",
    }
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Explain how to replay this SCBE/AetherDesk tool action safely from its receipt.",
            },
            {"role": "assistant", "content": json.dumps(assistant, ensure_ascii=True, sort_keys=True)},
        ],
        "meta": {
            "source": "sanitized_receipt",
            "domain": "tool_use",
            "surface": "SCBE/AetherDesk receipt",
            "source_trace": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "validated": False,
            "quality": "receipt_seed",
            "topic": "receipt_replay",
            "version": "v1",
        },
    }


def iter_receipt_records(roots: list[Path], max_receipts: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            if len(rows) >= max_receipts:
                return rows
            try:
                payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                rec = receipt_to_record(path, payload)
                if rec:
                    rows.append(rec)
        for path in sorted(root.rglob("*.jsonl")):
            if len(rows) >= max_receipts:
                return rows
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for line in lines:
                if len(rows) >= max_receipts:
                    return rows
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    rec = receipt_to_record(path, payload)
                    if rec:
                        rows.append(rec)
    return rows


def split_rows(rows: list[dict[str, Any]], holdout_ratio: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train: list[dict[str, Any]] = []
    holdout: list[dict[str, Any]] = []
    cutoff = int(max(0.0, min(0.5, holdout_ratio)) * 1000)
    for row in sorted(rows, key=lambda item: stable_hash(item)):
        bucket = int(stable_hash(row)[:8], 16) % 1000
        row["meta"]["split_rule"] = f"sha256_mod_1000_holdout_lt_{cutoff}"
        if bucket < cutoff:
            row["meta"]["split"] = "holdout"
            holdout.append(row)
        else:
            row["meta"]["split"] = "train"
            train.append(row)
    return train, holdout


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def build(args: argparse.Namespace) -> dict[str, Any]:
    tools = load_tools(Path(args.tools_json))
    rows = [tool_record(tool) for tool in tools] + abstain_records()
    receipt_roots = [Path(item) for item in args.receipt_root]
    if args.include_receipts:
        rows.extend(iter_receipt_records(receipt_roots, args.max_receipts))

    train, holdout = split_rows(rows, args.holdout_ratio)
    out_dir = Path(args.out_dir)
    train_path = out_dir / "scbe_tool_use_v1_train.sft.jsonl"
    holdout_path = out_dir / "scbe_tool_use_v1_holdout.sft.jsonl"
    manifest_path = out_dir / "scbe_tool_use_v1.manifest.json"

    write_jsonl(train_path, train)
    write_jsonl(holdout_path, holdout)
    manifest = {
        "schema": "scbe_tool_use_v1_manifest",
        "generated_at": utc_now(),
        "source": "scripts/training/build_scbe_tool_use_sft.py",
        "inputs": {
            "tools_json": str(Path(args.tools_json).resolve()),
            "include_receipts": bool(args.include_receipts),
            "receipt_roots": [str(path.resolve()) for path in receipt_roots],
        },
        "outputs": {
            "train": str(train_path.relative_to(ROOT)),
            "holdout": str(holdout_path.relative_to(ROOT)),
            "manifest": str(manifest_path.relative_to(ROOT)),
        },
        "counts": {
            "tools": len(tools),
            "total": len(rows),
            "train": len(train),
            "holdout": len(holdout),
            "by_source": {},
        },
        "boundary": {
            "claim": "tool-use corpus prepared; no model improvement claim until training and heldout eval run",
            "secret_policy": "redact obvious API keys, bearer tokens, passwords, authorization values, and token-like strings",
            "execution_policy": "training records prepare calls; host execution still requires GeoSeal/AetherDesk governance receipts",
        },
    }
    by_source: dict[str, int] = {}
    for row in rows:
        source = str(row.get("meta", {}).get("source", "unknown"))
        by_source[source] = by_source.get(source, 0) + 1
    manifest["counts"]["by_source"] = by_source
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools-json", default=str(TOOLS_JSON))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--holdout-ratio", type=float, default=0.15)
    parser.add_argument("--include-receipts", action="store_true")
    parser.add_argument("--max-receipts", type=int, default=250)
    parser.add_argument(
        "--receipt-root",
        action="append",
        default=[
            str(ROOT / "artifacts" / "aetherdesk_receipts"),
            str(ROOT / "artifacts" / "benchmarks"),
            str(Path.home() / "AetherDesk" / "artifacts" / "aetherdesk_receipts"),
        ],
    )
    args = parser.parse_args(argv)
    manifest = build(args)
    print(json.dumps({"ok": True, "manifest": manifest}, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
