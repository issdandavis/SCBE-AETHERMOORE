#!/usr/bin/env python3
"""Build canonical route-consistency records from mixed SCBE training corpora."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from jsonschema import Draft202012Validator

from python.scbe.atomic_tokenization import map_token_to_atomic_state


SCHEMA_VERSION = "scbe_route_consistency_record_v1"
HASH_LENGTH = 16
TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)
LAYER_PATTERN = re.compile(r"\b(?:layer\s*)?(1[0-4]|[1-9])\b", re.IGNORECASE)
TONGUE_PATTERN = re.compile(r"\b(KO|AV|RU|CA|UM|DR)\b", re.IGNORECASE)
ALLOWED_LANGUAGES = {"python", "typescript", "javascript", "json", "markdown", "text"}


@dataclass(frozen=True)
class NormalizedExample:
    source_corpus: str
    row_index: int
    input_text: str
    expected_outcome: str
    route_family: str
    view: str
    language: str
    tongue: str
    layer: str
    governance: str
    target_behavior: str


def _hash_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()[:HASH_LENGTH]
    return f"{prefix}_{digest}"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text)


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def _extract_message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                if text:
                    chunks.append(str(text))
            elif item:
                chunks.append(str(item))
        return "\n".join(chunks)
    return str(content or "")


def _parse_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def _infer_language(row: dict[str, Any], input_text: str, metadata: dict[str, Any]) -> str:
    for key in ("language", "lang"):
        candidate = row.get(key) or metadata.get(key)
        if isinstance(candidate, str):
            lowered = candidate.strip().lower()
            if lowered in ALLOWED_LANGUAGES:
                return lowered

    source_file = str(metadata.get("source_file") or "")
    if source_file.endswith(".py"):
        return "python"
    if source_file.endswith((".ts", ".tsx")):
        return "typescript"
    if source_file.endswith((".js", ".jsx", ".mjs")):
        return "javascript"
    if source_file.endswith(".json"):
        return "json"
    if source_file.endswith((".md", ".markdown")):
        return "markdown"

    lowered = input_text.lower()
    if any(marker in lowered for marker in ("def ", "pytest", "python", "pathlib")):
        return "python"
    if any(marker in lowered for marker in ("const ", "interface ", "typescript", "npm ")):
        return "typescript"
    return "text"


def _infer_layer(row: dict[str, Any], input_text: str, expected_outcome: str, metadata: dict[str, Any]) -> str:
    candidates: list[str] = []
    for key in ("task_type", "layer"):
        value = row.get(key) or metadata.get(key)
        if isinstance(value, str):
            candidates.append(value)
    candidates.extend([input_text, expected_outcome, str(row.get("system") or "")])

    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        lowered = candidate.lower()
        if lowered.startswith("l") and lowered[1:].isdigit():
            layer_num = int(lowered[1:])
            if 1 <= layer_num <= 14:
                return f"L{layer_num}"
        match = LAYER_PATTERN.search(candidate)
        if match:
            return f"L{match.group(1)}"
    return "L3"


def _infer_tongue(row: dict[str, Any], input_text: str, expected_outcome: str, metadata: dict[str, Any]) -> str:
    explicit_candidates = [
        str(row.get("tongue") or ""),
        str(metadata.get("tongue") or ""),
        input_text,
        expected_outcome,
        str(row.get("system") or ""),
    ]
    for candidate in explicit_candidates:
        match = TONGUE_PATTERN.search(candidate)
        if match:
            return match.group(1).upper()

    haystack = " ".join(
        filter(
            None,
            [
                input_text.lower(),
                expected_outcome.lower(),
                str(row.get("category") or "").lower(),
                str(row.get("class") or "").lower(),
                str(row.get("source") or "").lower(),
                str(metadata.get("origin") or "").lower(),
            ],
        )
    )
    if any(token in haystack for token in ("codeql", "security", "vulnerability", "exploit", "cwe-")):
        return "UM"
    if any(token in haystack for token in ("explain", "review", "analyze", "analysis", "document")):
        return "RU"
    if any(token in haystack for token in ("implement", "build", "write", "fix", "patch", "refactor")):
        return "CA"
    return "AV"


def _infer_governance(input_text: str, expected_outcome: str) -> str:
    haystack = f"{input_text} {expected_outcome}".lower()
    deny_markers = ("ransomware", "credential theft", "keylogger", "exfiltrate", "malware payload")
    hold_markers = ("exploit", "privilege escalation", "bypass", "evasion")
    if any(marker in haystack for marker in deny_markers):
        return "DENY"
    if any(marker in haystack for marker in hold_markers):
        return "HOLD"
    return "ALLOW"


def _target_behavior(input_text: str, expected_outcome: str) -> str:
    candidate = _normalize_text(expected_outcome or input_text)
    return candidate[:240] or "governed_execution"


def normalize_row(row: dict[str, Any], source_corpus: str, row_index: int) -> NormalizedExample:
    metadata = _parse_metadata(row.get("metadata"))

    if isinstance(row.get("messages"), list):
        user_inputs: list[str] = []
        context_inputs: list[str] = []
        outputs: list[str] = []
        for message in row["messages"]:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role") or "").lower()
            content = _extract_message_text(message.get("content"))
            if role == "assistant":
                outputs.append(content)
            elif role == "user":
                user_inputs.append(content)
            elif role in {"system", "developer"}:
                context_inputs.append(content)
        input_text = "\n".join(filter(None, user_inputs)).strip() or "\n".join(filter(None, context_inputs)).strip()
        expected_outcome = "\n".join(filter(None, outputs)).strip()
        route_family = "multi_turn_conversation"
        view = "openai_chat"
    elif isinstance(row.get("instruction"), str) and isinstance(row.get("response"), str):
        input_text = row["instruction"].strip()
        expected_outcome = row["response"].strip()
        route_family = "instruction_projection"
        view = "instruction_response"
    elif isinstance(row.get("prompt"), str) and isinstance(row.get("response") or row.get("completion"), str):
        input_text = row["prompt"].strip()
        expected_outcome = str(row.get("response") or row.get("completion") or "").strip()
        route_family = "prompt_completion_projection"
        view = "prompt_completion"
    else:
        raise ValueError(f"Unsupported row shape in {source_corpus}:{row_index}")

    if not input_text:
        raise ValueError(f"Missing input text in {source_corpus}:{row_index}")

    language = _infer_language(row, input_text, metadata)
    layer = _infer_layer(row, input_text, expected_outcome, metadata)
    tongue = _infer_tongue(row, input_text, expected_outcome, metadata)
    governance = _infer_governance(input_text, expected_outcome)

    return NormalizedExample(
        source_corpus=source_corpus,
        row_index=row_index,
        input_text=input_text,
        expected_outcome=expected_outcome or input_text,
        route_family=route_family,
        view=view,
        language=language,
        tongue=tongue,
        layer=layer,
        governance=governance,
        target_behavior=_target_behavior(input_text, expected_outcome),
    )


def build_record(example: NormalizedExample) -> dict[str, Any]:
    normalized_input = _normalize_text(example.input_text)
    normalized_expected = _normalize_text(example.expected_outcome)
    intent_id = _hash_id("intent", normalized_input)
    record_id = _hash_id(
        "record",
        example.source_corpus,
        str(example.row_index),
        normalized_input,
        normalized_expected,
        example.view,
    )
    route_id = _hash_id("route", intent_id, example.tongue, example.layer, example.view)
    target_cluster = _hash_id("cluster", normalized_expected or normalized_input)

    tokens = _tokenize(example.input_text)
    states = [
        map_token_to_atomic_state(token, language=example.language, context_class="operator")
        for token in tokens
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": record_id,
        "intent_id": intent_id,
        "route_id": route_id,
        "route_family": example.route_family,
        "target_cluster": target_cluster,
        "source_corpus": example.source_corpus,
        "input": {
            "text": example.input_text,
            "language": example.language,
        },
        "route_metadata": {
            "tongue": example.tongue,
            "layer": example.layer,
            "view": example.view,
            "governance": example.governance,
        },
        "atomic_features": {
            "tokens": tokens,
            "elements": [
                {
                    "symbol": state.element.symbol,
                    "Z": state.element.Z,
                    "group": state.element.group,
                    "period": state.element.period,
                    "valence": state.element.valence,
                    "electronegativity": state.element.electronegativity,
                    "witness_stable": state.element.witness_stable,
                }
                for state in states
            ],
            "trits": [state.tau.as_dict() for state in states],
        },
        "triangulation_links": [],
        "labels": {
            "target_behavior": example.target_behavior,
            "expected_outcome": example.expected_outcome,
            "passes_governance": example.governance == "ALLOW",
        },
    }


def attach_triangulation_links(records: list[dict[str, Any]]) -> None:
    grouped: dict[str, list[str]] = defaultdict(list)
    for record in records:
        grouped[record["intent_id"]].append(record["record_id"])

    for record in records:
        linked = [value for value in grouped[record["intent_id"]] if value != record["record_id"]]
        if linked:
            record["triangulation_links"] = [
                {
                    "kind": "semantic_process_execution",
                    "linked_record_ids": linked,
                }
            ]


def build_records_from_paths(paths: Iterable[Path], repo_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        source_corpus = _safe_relative(path, repo_root)
        with path.open("r", encoding="utf-8") as handle:
            for row_index, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                example = normalize_row(row, source_corpus, row_index)
                records.append(build_record(example))
    attach_triangulation_links(records)
    return records


def load_schema(schema_path: Path) -> Draft202012Validator:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def validate_records(records: Iterable[dict[str, Any]], validator: Draft202012Validator) -> None:
    for record in records:
        validator.validate(record)


def resolve_inputs(repo_root: Path, explicit_inputs: list[str] | None, profile: str | None) -> list[Path]:
    if explicit_inputs:
        return [repo_root / Path(path) for path in explicit_inputs]
    if not profile:
        raise ValueError("Provide either --input or --profile")

    profile_path = repo_root / "config" / "model_training" / f"{profile}.json"
    profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
    dataset = profile_data.get("dataset", {})
    dataset_root = repo_root / dataset.get("root", "training-data")
    filenames = list(dataset.get("train_files", [])) + list(dataset.get("eval_files", []))
    if not filenames:
        raise ValueError(f"Profile {profile} did not define dataset files")
    return [dataset_root / name for name in filenames]


def _progress(count: int, path: Path) -> None:
    print(f"[route-builder] processed {count} records from {_safe_relative(path, path.parent)}", file=sys.stderr)


def build_manifest(
    *,
    output_jsonl: Path,
    source_counts: Counter[str],
    route_family_counts: Counter[str],
    governance_counts: Counter[str],
    witness_stable_count: int,
    token_count: int,
    record_count: int,
    intent_ids: set[str],
    target_clusters: set[str],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": record_count,
        "intent_count": len(intent_ids),
        "target_cluster_count": len(target_clusters),
        "token_count": token_count,
        "witness_stable_token_ratio": (witness_stable_count / token_count) if token_count else 0.0,
        "output_jsonl": str(output_jsonl),
        "route_family_counts": dict(sorted(route_family_counts.items())),
        "governance_counts": dict(sorted(governance_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
    }


def build_route_consistency_outputs(
    *,
    input_paths: list[Path],
    output_jsonl: Path,
    manifest_path: Path,
    schema_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    validator = load_schema(schema_path)

    source_counts: Counter[str] = Counter()
    route_family_counts: Counter[str] = Counter()
    governance_counts: Counter[str] = Counter()
    witness_stable_count = 0
    token_count = 0
    record_count = 0
    intent_ids: set[str] = set()
    target_clusters: set[str] = set()
    intent_map: dict[str, list[str]] = defaultdict(list)

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as spool_handle:
        spool_path = Path(spool_handle.name)
        for path in input_paths:
            source_corpus = _safe_relative(path, repo_root)
            processed_for_file = 0
            with path.open("r", encoding="utf-8") as handle:
                for row_index, line in enumerate(handle, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    example = normalize_row(row, source_corpus, row_index)
                    record = build_record(example)
                    validator.validate(record)
                    spool_handle.write(json.dumps(record, ensure_ascii=True) + "\n")

                    source_counts[source_corpus] += 1
                    route_family_counts[record["route_family"]] += 1
                    governance_counts[record["route_metadata"]["governance"]] += 1
                    token_count += len(record["atomic_features"]["tokens"])
                    witness_stable_count += sum(1 for element in record["atomic_features"]["elements"] if element["witness_stable"])
                    record_count += 1
                    processed_for_file += 1
                    intent_ids.add(record["intent_id"])
                    target_clusters.add(record["target_cluster"])
                    intent_map[record["intent_id"]].append(record["record_id"])

                    if processed_for_file and processed_for_file % 1000 == 0:
                        _progress(processed_for_file, path)

    with spool_path.open("r", encoding="utf-8") as source_handle, output_jsonl.open("w", encoding="utf-8") as output_handle:
        for line in source_handle:
            record = json.loads(line)
            linked = [value for value in intent_map[record["intent_id"]] if value != record["record_id"]]
            if linked:
                record["triangulation_links"] = [
                    {
                        "kind": "semantic_process_execution",
                        "linked_record_ids": linked,
                    }
                ]
            validator.validate(record)
            output_handle.write(json.dumps(record, ensure_ascii=True) + "\n")

    spool_path.unlink(missing_ok=True)

    manifest = build_manifest(
        output_jsonl=output_jsonl,
        source_counts=source_counts,
        route_family_counts=route_family_counts,
        governance_counts=governance_counts,
        witness_stable_count=witness_stable_count,
        token_count=token_count,
        record_count=record_count,
        intent_ids=intent_ids,
        target_clusters=target_clusters,
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", help="Relative or absolute JSONL corpus path. Repeatable.")
    parser.add_argument("--profile", help="Model training profile to resolve input corpora from.")
    parser.add_argument(
        "--output-jsonl",
        default="training-data/route_consistency/route_consistency_records.jsonl",
        help="Output JSONL path, relative to repo root unless absolute.",
    )
    parser.add_argument(
        "--manifest-path",
        default="training-data/route_consistency/manifest.json",
        help="Manifest path, relative to repo root unless absolute.",
    )
    parser.add_argument(
        "--schema-path",
        default="schemas/route_consistency_record.schema.json",
        help="Schema path, relative to repo root unless absolute.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = REPO_ROOT
    input_paths = resolve_inputs(repo_root, args.input, args.profile)
    output_jsonl = repo_root / Path(args.output_jsonl)
    manifest_path = repo_root / Path(args.manifest_path)
    schema_path = repo_root / Path(args.schema_path)

    manifest = build_route_consistency_outputs(
        input_paths=input_paths,
        output_jsonl=output_jsonl,
        manifest_path=manifest_path,
        schema_path=schema_path,
        repo_root=repo_root,
    )
    print(
        json.dumps(
            {
                "record_count": manifest["record_count"],
                "intent_count": manifest["intent_count"],
                "output_jsonl": str(output_jsonl),
                "manifest_path": str(manifest_path),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
