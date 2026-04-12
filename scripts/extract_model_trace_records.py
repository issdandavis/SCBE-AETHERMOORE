#!/usr/bin/env python3
"""Extract low-trust model trace records from chat exports, JSONL traces, and markdown notes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from jsonschema import Draft202012Validator


SCHEMA_VERSION = "scbe_model_trace_record_v1"
HASH_LENGTH = 16
CODE_BLOCK_RE = re.compile(r"```(?:[\w.+-]+)?\n(.*?)```", re.DOTALL)
ARTIFACT_RE = re.compile(r"(?:[A-Za-z]:\\[^\s`]+|[\w./-]+\.(?:py|ts|tsx|js|json|md|yaml|yml|sh|ps1))")
GOVERNANCE_RE = re.compile(r"\b(ALLOW|HOLD|DENY)\b", re.IGNORECASE)
STEP_RE = re.compile(r"^(?:\d+\.|[-*])\s+", re.MULTILINE)


def _hash_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()[:HASH_LENGTH]
    return f"{prefix}_{digest}"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def _coerce_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    coerced: list[dict[str, str]] = []
    for message in messages:
        role = str(message.get("role") or "unknown")
        content = message.get("content")
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("content") or ""
                    if text:
                        parts.append(str(text))
                elif item:
                    parts.append(str(item))
            text = "\n".join(parts)
        else:
            text = str(content or "")
        coerced.append({"role": role, "content": text})
    return coerced


def _guess_source_model(source_path: Path, messages: list[dict[str, str]], explicit: str | None = None) -> str:
    if explicit:
        return explicit
    lowered_name = source_path.name.lower()
    if "grok" in lowered_name:
        return "grok"
    if "claude" in lowered_name:
        return "claude"
    if "codex" in lowered_name or "chatgpt" in lowered_name:
        return "codex"
    for message in messages:
        content = message["content"].lower()
        if "grok" in content:
            return "grok"
        if "claude" in content:
            return "claude"
        if "codex" in content or "chatgpt" in content:
            return "codex"
    return "unknown"


def _split_views(messages: list[dict[str, str]]) -> tuple[str, str, str]:
    assistant_text = "\n\n".join(message["content"] for message in messages if message["role"].lower() == "assistant")
    user_text = "\n\n".join(message["content"] for message in messages if message["role"].lower() == "user")
    concept_chunks: list[str] = []
    process_chunks: list[str] = []
    execution_chunks: list[str] = []

    for paragraph in re.split(r"\n\s*\n", assistant_text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if CODE_BLOCK_RE.search(paragraph):
            execution_chunks.append(paragraph)
        elif STEP_RE.search(paragraph) or any(
            token in paragraph.lower() for token in ("next step", "pipeline", "workflow", "plan")
        ):
            process_chunks.append(paragraph)
        else:
            concept_chunks.append(paragraph)

    if not concept_chunks:
        concept_chunks = [assistant_text[:800] or user_text[:800]]
    if not process_chunks:
        process_chunks = [assistant_text[:800] or user_text[:800]]
    if not execution_chunks:
        code_blocks = CODE_BLOCK_RE.findall(assistant_text)
        execution_chunks = code_blocks[:2] if code_blocks else [assistant_text[:800] or user_text[:800]]

    return (
        "\n\n".join(concept_chunks[:2]).strip(),
        "\n\n".join(process_chunks[:2]).strip(),
        "\n\n".join(execution_chunks[:2]).strip(),
    )


def _extract_artifacts(messages: list[dict[str, str]]) -> list[str]:
    text = "\n".join(message["content"] for message in messages)
    artifacts: list[str] = []
    seen: set[str] = set()
    for match in ARTIFACT_RE.findall(text):
        candidate = match.strip().strip("`.,:;)")
        lowered = candidate.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        artifacts.append(candidate)
    return artifacts[:24]


def _extract_governance_claims(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for message in messages:
        for line in message["content"].splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            matches = {match.upper() for match in GOVERNANCE_RE.findall(stripped)}
            status = next(iter(matches), "UNSPECIFIED")
            if status == "UNSPECIFIED" and "governance" not in stripped.lower() and "safe" not in stripped.lower():
                continue
            key = (stripped[:160], status)
            if key in seen:
                continue
            seen.add(key)
            claims.append({"claim": stripped[:320], "status": status})
    return claims[:16] or [{"claim": "verification pending", "status": "UNSPECIFIED"}]


def _confidence(messages: list[dict[str, str]], artifacts: list[str], claims: list[dict[str, str]]) -> float:
    assistant_chars = sum(len(message["content"]) for message in messages if message["role"].lower() == "assistant")
    score = 0.2
    if assistant_chars > 400:
        score += 0.15
    if artifacts:
        score += 0.15
    if any(claim["status"] != "UNSPECIFIED" for claim in claims):
        score += 0.1
    if CODE_BLOCK_RE.search("\n".join(message["content"] for message in messages)):
        score += 0.1
    if len(messages) >= 4:
        score += 0.1
    return round(min(score, 0.8), 4)


def _build_trace_record(
    *,
    source_path: Path,
    title: str,
    created_at: str | None,
    messages: list[dict[str, str]],
    source_model: str,
    interaction_type: str,
) -> dict[str, Any]:
    user_text = "\n\n".join(message["content"] for message in messages if message["role"].lower() == "user")
    normalized_intent = _normalize_text(user_text or title or "conversation")
    assistant_text = "\n\n".join(message["content"] for message in messages if message["role"].lower() == "assistant")
    concept_view, process_view, execution_view = _split_views(messages)
    artifacts = _extract_artifacts(messages)
    claims = _extract_governance_claims(messages)
    confidence = _confidence(messages, artifacts, claims)

    intent_id = _hash_id("intent", normalized_intent)
    route_id = _hash_id("trace_route", source_model, interaction_type, title or normalized_intent)
    trace_id = _hash_id("trace", _safe_relative(source_path, REPO_ROOT), title, normalized_intent, assistant_text)
    target_cluster = _hash_id("trace_cluster", _normalize_text(execution_view or process_view or concept_view))

    return {
        "schema_version": SCHEMA_VERSION,
        "trace_id": trace_id,
        "source_model": source_model,
        "interaction_type": interaction_type,
        "raw_model_trace": {
            "title": title,
            "source_corpus": _safe_relative(source_path, REPO_ROOT),
            "created_at": created_at,
            "messages": messages,
        },
        "extracted_structured_record": {
            "intent_id": intent_id,
            "route_id": route_id,
            "route_family": "agentic_dialogue",
            "target_cluster": target_cluster,
            "source_model": source_model,
            "concept_view": concept_view,
            "process_view": process_view,
            "execution_view": execution_view,
            "proposed_artifacts": artifacts,
            "governance_claims": claims,
            "triangulation_links": [],
            "confidence": confidence,
        },
        "verification": {
            "human_verified": False,
            "trust_level": "raw_model_trace",
            "reviewer_notes": "Pending human verification before supervised training use.",
        },
    }


def _iter_jsonl_records(path: Path, explicit_model: str | None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            messages = _coerce_messages(row.get("messages") or [])
            if not messages:
                prompt = str(row.get("prompt") or row.get("instruction") or "")
                response = str(row.get("response") or row.get("completion") or "")
                if prompt or response:
                    messages = [{"role": "user", "content": prompt}, {"role": "assistant", "content": response}]
            if not messages:
                continue
            source_model = _guess_source_model(path, messages, explicit_model or row.get("source_model"))
            title = str(row.get("title") or row.get("id") or messages[0]["content"][:80])
            created_at = row.get("created_at")
            records.append(
                _build_trace_record(
                    source_path=path,
                    title=title,
                    created_at=str(created_at) if created_at else None,
                    messages=messages,
                    source_model=source_model,
                    interaction_type="agentic_dialogue",
                )
            )
    return records


def _iter_chat_export_records(path: Path, explicit_model: str | None) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected list payload in {path}")
    records: list[dict[str, Any]] = []
    for conversation in payload:
        mapping = conversation.get("mapping") or {}
        messages: list[dict[str, str]] = []
        for node in mapping.values():
            message = node.get("message") or {}
            author = message.get("author") or {}
            role = str(author.get("role") or "unknown")
            content_obj = message.get("content") or {}
            parts = content_obj.get("parts") or []
            text = "\n".join(part for part in parts if isinstance(part, str))
            if text.strip():
                messages.append({"role": role, "content": text})
        if not messages:
            continue
        created_at = conversation.get("create_time")
        created_at_iso = None
        if created_at:
            created_at_iso = datetime.fromtimestamp(float(created_at), tz=timezone.utc).isoformat()
        source_model = _guess_source_model(path, messages, explicit_model)
        records.append(
            _build_trace_record(
                source_path=path,
                title=str(conversation.get("title") or "Untitled Conversation"),
                created_at=created_at_iso,
                messages=messages,
                source_model=source_model,
                interaction_type="chat_export",
            )
        )
    return records


def _iter_markdown_records(path: Path, explicit_model: str | None) -> list[dict[str, Any]]:
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        return []
    messages = [{"role": "assistant", "content": content}]
    source_model = _guess_source_model(path, messages, explicit_model)
    return [
        _build_trace_record(
            source_path=path,
            title=path.stem,
            created_at=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
            messages=messages,
            source_model=source_model,
            interaction_type="markdown_note",
        )
    ]


def load_schema(schema_path: Path) -> Draft202012Validator:
    return Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))


def attach_trace_links(records: list[dict[str, Any]]) -> None:
    by_intent: dict[str, list[str]] = defaultdict(list)
    for record in records:
        by_intent[record["extracted_structured_record"]["intent_id"]].append(record["trace_id"])
    for record in records:
        linked = [
            value
            for value in by_intent[record["extracted_structured_record"]["intent_id"]]
            if value != record["trace_id"]
        ]
        if linked:
            record["extracted_structured_record"]["triangulation_links"] = [
                {"kind": "intent_sibling", "linked_ids": linked}
            ]


def extract_records(paths: list[Path], explicit_model: str | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        suffix = path.suffix.lower()
        if suffix == ".jsonl":
            records.extend(_iter_jsonl_records(path, explicit_model))
        elif suffix == ".json":
            records.extend(_iter_chat_export_records(path, explicit_model))
        elif suffix in {".md", ".markdown"}:
            records.extend(_iter_markdown_records(path, explicit_model))
        else:
            raise ValueError(f"Unsupported trace input type: {path}")
    attach_trace_links(records)
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", required=True, help="Trace input file (.jsonl, .json, .md).")
    parser.add_argument("--output-jsonl", default="training-data/model_traces/model_trace_records.jsonl")
    parser.add_argument("--schema-path", default="schemas/model_trace_record.schema.json")
    parser.add_argument("--source-model", help="Override inferred source model.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = REPO_ROOT
    paths = [(repo_root / Path(value)).resolve() if not Path(value).is_absolute() else Path(value) for value in args.input]
    output_jsonl = repo_root / Path(args.output_jsonl)
    schema_path = repo_root / Path(args.schema_path)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    validator = load_schema(schema_path)
    records = extract_records(paths, explicit_model=args.source_model)
    with output_jsonl.open("w", encoding="utf-8") as handle:
        for record in records:
            validator.validate(record)
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
    print(json.dumps({"record_count": len(records), "output_jsonl": str(output_jsonl)}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
