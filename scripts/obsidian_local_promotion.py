#!/usr/bin/env python3
"""Run the Obsidian-first local training promotion loop.

Workflow:
1. Discover raw notes from the local vault.
2. Extract low-trust model-trace records.
3. Generate an Obsidian review queue plus a JSONL decisions template.
4. Promote only explicitly approved traces into verified trace records and
   route-consistency records for downstream training use.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.build_route_consistency_records import build_route_consistency_outputs
from scripts.extract_model_trace_records import extract_records, load_schema as load_trace_schema


DEFAULT_NOTE_PATTERNS = (
    "notes/_inbox.md",
    "notes/GROk*.md",
    "notes/RAW DUMPS*.md",
    "notes/Messges Dumps_trainging files/**/*.md",
    "notes/sessions/**/*.md",
    "notes/round-table/**/*.md",
)

DEFAULT_TRACE_OUTPUT = "training-data/model_traces/obsidian/obsidian_model_trace_records.jsonl"
DEFAULT_VERIFIED_TRACE_OUTPUT = "training-data/model_traces/obsidian/obsidian_verified_model_trace_records.jsonl"
DEFAULT_ROUTE_SEED_OUTPUT = "training-data/model_traces/obsidian/obsidian_verified_route_seed.jsonl"
DEFAULT_ROUTE_OUTPUT = "training-data/route_consistency/obsidian_verified_route_records.jsonl"
DEFAULT_ROUTE_MANIFEST = "training-data/route_consistency/obsidian_verified_manifest.json"
DEFAULT_REVIEW_QUEUE = "notes/agent-memory/obsidian-trace-review-queue.md"
DEFAULT_DECISIONS_PATH = "notes/agent-memory/obsidian-trace-decisions.jsonl"
TRACE_SCHEMA_PATH = REPO_ROOT / "schemas" / "model_trace_record.schema.json"
ROUTE_SCHEMA_PATH = REPO_ROOT / "schemas" / "route_consistency_record.schema.json"
CODE_BLOCK_RE = re.compile(r"```(?:([\w.+-]+))?\n(.*?)```", re.DOTALL)


def _repo_path(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (repo_root / path)


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def resolve_note_paths(repo_root: Path, explicit_inputs: list[str] | None = None) -> list[Path]:
    resolved: list[Path] = []
    seen: set[Path] = set()

    def add_path(candidate: Path) -> None:
        if candidate.name.startswith("."):
            return
        if ".obsidian" in candidate.parts:
            return
        if candidate.suffix.lower() not in {".md", ".markdown"}:
            return
        normalized = candidate.resolve()
        if normalized in seen or not normalized.exists():
            return
        seen.add(normalized)
        resolved.append(normalized)

    if explicit_inputs:
        for value in explicit_inputs:
            candidate = _repo_path(repo_root, value)
            if candidate.is_dir():
                for path in sorted(candidate.rglob("*.md")):
                    add_path(path)
                for path in sorted(candidate.rglob("*.markdown")):
                    add_path(path)
            else:
                add_path(candidate)
        return resolved

    for pattern in DEFAULT_NOTE_PATTERNS:
        for candidate in sorted(repo_root.glob(pattern)):
            if candidate.is_dir():
                for path in sorted(candidate.rglob("*.md")):
                    add_path(path)
                for path in sorted(candidate.rglob("*.markdown")):
                    add_path(path)
            else:
                add_path(candidate)
    return resolved


def _trim_block(text: str, limit: int = 600) -> str:
    normalized = text.strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def write_trace_records(
    *,
    note_paths: list[Path],
    output_jsonl: Path,
    schema_path: Path,
    source_model: str | None = None,
) -> list[dict[str, Any]]:
    records = extract_records(note_paths, explicit_model=source_model)
    validator = load_trace_schema(schema_path)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("w", encoding="utf-8") as handle:
        for record in records:
            validator.validate(record)
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
    return records


def build_review_queue_markdown(records: list[dict[str, Any]], decisions_path: Path, repo_root: Path) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Obsidian Trace Review Queue",
        "",
        f"Generated: `{generated_at}`",
        "",
        "Use this queue to review low-trust notes before they are promoted into training data.",
        f"Machine-readable decisions live at `{_safe_relative(decisions_path, repo_root)}`.",
        "Set each decision to `promote`, `hold`, or `skip`.",
        "",
    ]

    for index, record in enumerate(records, start=1):
        structured = record["extracted_structured_record"]
        raw = record["raw_model_trace"]
        artifacts = structured.get("proposed_artifacts") or []
        artifact_line = ", ".join(f"`{artifact}`" for artifact in artifacts[:8]) if artifacts else "none"
        lines.extend(
            [
                f"## {index}. {raw.get('title') or 'Untitled Trace'}",
                "",
                f"- `trace_id`: `{record['trace_id']}`",
                f"- `source_model`: `{record['source_model']}`",
                f"- `source_note`: `{raw.get('source_corpus')}`",
                f"- `confidence`: `{structured.get('confidence', 0.0)}`",
                f"- `artifacts`: {artifact_line}",
                "",
                "### Concept",
                "",
                _trim_block(structured.get("concept_view") or "(empty)"),
                "",
                "### Process",
                "",
                _trim_block(structured.get("process_view") or "(empty)"),
                "",
                "### Execution",
                "",
                _trim_block(structured.get("execution_view") or "(empty)"),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_decision_template(
    records: list[dict[str, Any]],
    decisions_path: Path,
    *,
    overwrite: bool = False,
) -> bool:
    if decisions_path.exists() and not overwrite:
        return False
    decisions_path.parent.mkdir(parents=True, exist_ok=True)
    with decisions_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(
                json.dumps(
                    {
                        "trace_id": record["trace_id"],
                        "decision": "hold",
                        "notes": "",
                        "language_override": "",
                        "tongue_override": "",
                        "layer_override": "",
                    },
                    ensure_ascii=True,
                )
                + "\n"
            )
    return True


def load_trace_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_decisions(path: Path) -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    if not path.exists():
        raise FileNotFoundError(f"Decisions file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            trace_id = str(row.get("trace_id") or "").strip()
            if not trace_id:
                raise ValueError(f"Missing trace_id in decisions file at line {line_number}")
            decisions[trace_id] = row
    return decisions


def _infer_language(trace_record: dict[str, Any], decision: dict[str, Any]) -> str:
    override = str(decision.get("language_override") or "").strip().lower()
    if override:
        return override
    artifacts = trace_record["extracted_structured_record"].get("proposed_artifacts") or []
    for artifact in artifacts:
        lowered = artifact.lower()
        if lowered.endswith(".py"):
            return "python"
        if lowered.endswith((".ts", ".tsx")):
            return "typescript"
        if lowered.endswith((".js", ".jsx", ".mjs")):
            return "javascript"
        if lowered.endswith(".json"):
            return "json"
        if lowered.endswith((".md", ".markdown")):
            return "markdown"

    execution = trace_record["extracted_structured_record"].get("execution_view") or ""
    for language, _code in CODE_BLOCK_RE.findall(execution):
        lowered = (language or "").strip().lower()
        if lowered in {"python", "py"}:
            return "python"
        if lowered in {"typescript", "ts", "tsx"}:
            return "typescript"
        if lowered in {"javascript", "js", "jsx"}:
            return "javascript"
        if lowered == "json":
            return "json"
    return "text"


def _infer_tongue(trace_record: dict[str, Any], decision: dict[str, Any], language: str) -> str:
    override = str(decision.get("tongue_override") or "").strip().upper()
    if override:
        return override
    if language in {"python", "typescript", "javascript"}:
        return "CA"
    return "RU"


def _infer_layer(decision: dict[str, Any]) -> str:
    override = str(decision.get("layer_override") or "").strip().upper()
    if override:
        return override if override.startswith("L") else f"L{override}"
    return "L3"


def _route_seed_row(trace_record: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    structured = trace_record["extracted_structured_record"]
    language = _infer_language(trace_record, decision)
    tongue = _infer_tongue(trace_record, decision, language)
    layer = _infer_layer(decision)
    concept = (structured.get("concept_view") or "").strip()
    process = (structured.get("process_view") or "").strip()
    execution = (structured.get("execution_view") or "").strip()

    prompt_parts = []
    if concept:
        prompt_parts.append(f"Concept View:\n{concept}")
    if process:
        prompt_parts.append(f"Process View:\n{process}")
    prompt = "\n\n".join(prompt_parts).strip() or concept or process or execution
    response = execution or process or concept

    return {
        "prompt": prompt,
        "response": response,
        "metadata": {
            "source_trace_id": trace_record["trace_id"],
            "source_model": trace_record["source_model"],
            "tongue": tongue,
            "layer": layer,
            "language": language,
            "origin": "obsidian_verified_trace",
        },
    }


def promote_verified_traces(
    *,
    trace_records: list[dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
    verified_output: Path,
    route_seed_output: Path,
    route_output: Path,
    route_manifest: Path,
    repo_root: Path,
    route_schema_path: Path,
) -> dict[str, Any]:
    verified: list[dict[str, Any]] = []
    route_rows: list[dict[str, Any]] = []
    promoted_count = 0

    for record in trace_records:
        decision = decisions.get(record["trace_id"])
        if not decision:
            continue
        choice = str(decision.get("decision") or "hold").strip().lower()
        if choice != "promote":
            continue

        promoted = json.loads(json.dumps(record))
        promoted["verification"] = {
            "human_verified": True,
            "trust_level": "human_verified_record",
            "reviewer_notes": str(decision.get("notes") or "").strip() or "Promoted from Obsidian review queue.",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        verified.append(promoted)
        route_rows.append(_route_seed_row(promoted, decision))
        promoted_count += 1

    verified_output.parent.mkdir(parents=True, exist_ok=True)
    route_seed_output.parent.mkdir(parents=True, exist_ok=True)
    with verified_output.open("w", encoding="utf-8") as handle:
        for record in verified:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
    with route_seed_output.open("w", encoding="utf-8") as handle:
        for row in route_rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    route_manifest_payload: dict[str, Any] | None = None
    if route_rows:
        route_manifest_payload = build_route_consistency_outputs(
            input_paths=[route_seed_output],
            output_jsonl=route_output,
            manifest_path=route_manifest,
            schema_path=route_schema_path,
            repo_root=repo_root,
        )

    return {
        "promoted_count": promoted_count,
        "verified_output": str(verified_output),
        "route_seed_output": str(route_seed_output),
        "route_output": str(route_output),
        "route_manifest": str(route_manifest),
        "route_manifest_payload": route_manifest_payload,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover = subparsers.add_parser("discover", help="List note sources that feed the local promotion loop.")
    discover.add_argument("--input", action="append", help="Specific markdown file or directory to scan.")
    discover.add_argument("--json", action="store_true", help="Emit JSON instead of plain text.")

    extract = subparsers.add_parser("extract", help="Extract low-trust traces from Obsidian notes and build a review queue.")
    extract.add_argument("--input", action="append", help="Specific markdown file or directory to extract from.")
    extract.add_argument("--source-model", help="Override inferred source model for all extracted traces.")
    extract.add_argument("--output-jsonl", default=DEFAULT_TRACE_OUTPUT)
    extract.add_argument("--review-queue-path", default=DEFAULT_REVIEW_QUEUE)
    extract.add_argument("--decisions-path", default=DEFAULT_DECISIONS_PATH)
    extract.add_argument("--overwrite-decisions", action="store_true")

    promote = subparsers.add_parser("promote", help="Promote reviewed traces into verified traces and route-consistency records.")
    promote.add_argument("--trace-jsonl", default=DEFAULT_TRACE_OUTPUT)
    promote.add_argument("--decisions-path", default=DEFAULT_DECISIONS_PATH)
    promote.add_argument("--verified-output", default=DEFAULT_VERIFIED_TRACE_OUTPUT)
    promote.add_argument("--route-seed-output", default=DEFAULT_ROUTE_SEED_OUTPUT)
    promote.add_argument("--route-output", default=DEFAULT_ROUTE_OUTPUT)
    promote.add_argument("--route-manifest", default=DEFAULT_ROUTE_MANIFEST)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.command == "discover":
        note_paths = resolve_note_paths(REPO_ROOT, explicit_inputs=args.input)
        if args.json:
            print(json.dumps([_safe_relative(path, REPO_ROOT) for path in note_paths], ensure_ascii=True, indent=2))
        else:
            for path in note_paths:
                print(_safe_relative(path, REPO_ROOT))
        return 0

    if args.command == "extract":
        note_paths = resolve_note_paths(REPO_ROOT, explicit_inputs=args.input)
        output_jsonl = _repo_path(REPO_ROOT, args.output_jsonl)
        review_queue_path = _repo_path(REPO_ROOT, args.review_queue_path)
        decisions_path = _repo_path(REPO_ROOT, args.decisions_path)

        records = write_trace_records(
            note_paths=note_paths,
            output_jsonl=output_jsonl,
            schema_path=TRACE_SCHEMA_PATH,
            source_model=args.source_model,
        )

        review_queue_path.parent.mkdir(parents=True, exist_ok=True)
        review_queue_path.write_text(
            build_review_queue_markdown(records, decisions_path=decisions_path, repo_root=REPO_ROOT),
            encoding="utf-8",
        )
        template_written = write_decision_template(
            records,
            decisions_path,
            overwrite=args.overwrite_decisions,
        )

        print(
            json.dumps(
                {
                    "record_count": len(records),
                    "output_jsonl": str(output_jsonl),
                    "review_queue_path": str(review_queue_path),
                    "decisions_path": str(decisions_path),
                    "decision_template_written": template_written,
                },
                ensure_ascii=True,
            )
        )
        return 0

    if args.command == "promote":
        trace_jsonl = _repo_path(REPO_ROOT, args.trace_jsonl)
        decisions_path = _repo_path(REPO_ROOT, args.decisions_path)
        verified_output = _repo_path(REPO_ROOT, args.verified_output)
        route_seed_output = _repo_path(REPO_ROOT, args.route_seed_output)
        route_output = _repo_path(REPO_ROOT, args.route_output)
        route_manifest = _repo_path(REPO_ROOT, args.route_manifest)

        trace_records = load_trace_records(trace_jsonl)
        decisions = load_decisions(decisions_path)
        result = promote_verified_traces(
            trace_records=trace_records,
            decisions=decisions,
            verified_output=verified_output,
            route_seed_output=route_seed_output,
            route_output=route_output,
            route_manifest=route_manifest,
            repo_root=REPO_ROOT,
            route_schema_path=ROUTE_SCHEMA_PATH,
        )
        print(json.dumps(result, ensure_ascii=True))
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
