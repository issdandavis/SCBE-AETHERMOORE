"""Independent reconstruction and replay for prime-token reader evidence.

The producer packet builder and producer-written metric aggregates are not used
here.  This module repeats canonicalization, projection, control construction,
checkpoint verification, and per-example scoring through a separate code path.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

import torch
from torch import Tensor

from .function_lexicon import FunctionLexicon
from .prime_token_catalog import VIEW_NAMES, _query_features
from .prime_token_input_access import (
    CONTROL_MODES,
    FEATURE_WIDTH,
    PACKET_SCHEMA,
    RANDOM_CONTROL_SEED,
    VIEW_WIDTH,
    FullSystemPrimeTokenInputAccessLM,
    PrimeTokenRecord,
    SealedPrimeTokenBatch,
    tensor_sha256,
)
from .prime_token_training import (
    CHECKPOINT_SCHEMA,
    POINTER_SCHEMA,
    canonical_sha256,
    module_state_sha256,
    sha256_file,
)

RUNTIME_SCHEMA = "scbe.prime-token-material-runtime.v1"
BENCHMARK_SCHEMA = "scbe.prime-token-benchmark.v1"
SOURCE_MANIFEST_SCHEMA = "scbe.prime-token-material-source-manifest.v2"
SOURCE_FAMILY_AUDIT_SCHEMA = "scbe.prime-token-source-family-audit.v1"
PACKET_FREE_AUTHORITY_SCHEMA = "scbe.prime-token-packet-free-source-authority.v1"
PACKET_FREE_IDENTITY_TRANSFORM = "identity_utf8_v1"
PACKET_FREE_LINE_JOIN_TRANSFORM = "line_strip_join_space_v1"
SPLIT_MANIFEST_SCHEMA = "scbe.prime-token-dual-source-split.v1"
CASE_MANIFEST_SCHEMA = "scbe.prime-token-material-cases.v1"
EVALUATOR_RECEIPT_SCHEMA = "scbe.prime-token-evaluator-receipt.v1"
REVIEW_QUEUE_SCHEMA = "scbe.prime-token-independent-review-queue.v1"
CLOSED_SOURCE_SNAPSHOT_SCHEMA = "clay.closed-codex-source-snapshot.v1"
SOURCE_RECONSTRUCTION_SCHEMA = "scbe.prime-token-independent-source-reconstruction.v1"
MATERIAL_LANES = ("train", "validation", "final_test")
HELD_LANES = ("validation", "final_test")
ALL_CASE_LANES = (*MATERIAL_LANES, "ordinary", "retention")


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _items(features: Mapping[str, object]) -> tuple[tuple[str, str], ...]:
    output = []
    for key in sorted(features):
        value = features[key]
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, (int, float)):
            rendered = json.dumps(value, allow_nan=False)
        elif isinstance(value, str):
            rendered = value
        else:
            rendered = json.dumps(value, sort_keys=True, allow_nan=False)
        output.append((key, rendered))
    return tuple(output)


def _receipt(record: PrimeTokenRecord) -> str:
    body = {
        "canonical_id": record.canonical_id,
        "section_id": record.section_id,
        "source_family": record.source_family,
        "views": {name: list(_items(record.views[name])) for name in VIEW_NAMES},
    }
    return hashlib.sha256(_json_bytes(body)).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _required_text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def _required_sha256(value: object, *, label: str) -> str:
    digest = _required_text(value, label=label).casefold()
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError(f"{label} must be lowercase SHA-256")
    return digest


def _pinned_path(
    path_value: object,
    expected_sha256: object,
    *,
    label: str,
) -> Path:
    path_text = _required_text(path_value, label=f"{label} path")
    path = Path(path_text)
    if not path.is_absolute():
        raise ValueError(f"{label} path must be absolute")
    path = path.resolve(strict=True)
    expected = _required_sha256(expected_sha256, label=f"{label} SHA-256")
    if _file_sha256(path) != expected:
        raise RuntimeError(f"{label} hash differs")
    return path


def _object_file(
    path_value: object,
    expected_sha256: object,
    *,
    label: str,
) -> tuple[Path, dict[str, Any]]:
    path = _pinned_path(path_value, expected_sha256, label=label)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{label} must contain one JSON object")
    return path, value


def _jsonl_rows(path: Path, *, label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise TypeError(f"{label}:{line_number} must contain one JSON object")
            rows.append(value)
    return rows


def _manifest_rows(
    root: Path,
    descriptor: object,
    *,
    lane: str,
) -> list[dict[str, Any]]:
    if not isinstance(descriptor, dict):
        raise ValueError(f"case manifest omitted {lane}")
    relative = _required_text(descriptor.get("path"), label=f"{lane} path")
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError(f"case manifest {lane} path escapes its bundle")
    expected = _required_sha256(descriptor.get("sha256"), label=f"{lane} SHA-256")
    if _file_sha256(path) != expected:
        raise RuntimeError(f"case manifest {lane} hash differs")
    rows = _jsonl_rows(path, label=lane)
    count = descriptor.get("count")
    if isinstance(count, bool) or not isinstance(count, int) or count != len(rows):
        raise RuntimeError(f"case manifest {lane} count differs")
    return rows


def _record_json(record: PrimeTokenRecord) -> dict[str, object]:
    return {
        "canonical_id": record.canonical_id,
        "section_id": record.section_id,
        "source_family": record.source_family,
        "views": {name: dict(record.views[name]) for name in VIEW_NAMES},
    }


def _source_session(query_source_uri: object) -> str:
    uri = _required_text(query_source_uri, label="query source URI")
    parsed = urlsplit(uri)
    if parsed.scheme != "private-session" or not parsed.netloc:
        raise ValueError("query source URI must use private-session://<session>/...")
    return parsed.netloc


def _rebuild_query_input(
    query: object,
    query_source_uri: object,
    *,
    max_query_bytes: int,
) -> dict[str, object]:
    """Rebuild query bytes and six-view record without producer packet code."""

    text = _required_text(query, label="query")
    if max_query_bytes < 1 or max_query_bytes > 65_533:
        raise ValueError("max_query_bytes must be in [1, 65533]")
    session_id = _source_session(query_source_uri)
    query_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    session_sha256 = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    features, analysis = _query_features(text, FunctionLexicon())
    views: dict[str, dict[str, object]] = {
        name: {"features": sorted(features[name])[:128]} for name in VIEW_NAMES
    }
    views["lexical"].update(
        {
            "query_sha256": query_sha256,
            "utf8_bytes": len(text.encode("utf-8")),
            "word_count": len(analysis["words"]),
        }
    )
    views["five_w"].update(
        {
            "primary": analysis["five_w"]["primary"],
            "color": analysis["five_w"]["color"],
        }
    )
    views["source"] = {
        "source_kind": "private-session",
        "session_sha256": session_sha256,
        "query_sha256": query_sha256,
        "query_source_uri_sha256": hashlib.sha256(
            str(query_source_uri).strip().encode("utf-8")
        ).hexdigest(),
    }
    query_source_family = f"query-session:{session_sha256}"
    record = PrimeTokenRecord(
        canonical_id=f"query:{query_sha256}",
        section_id=f"query-session:{session_sha256}:query:{query_sha256[:16]}",
        source_family=query_source_family,
        views=views,
    )
    record.validate()
    token_ids = [0, *text.encode("utf-8")[:max_query_bytes], 0]
    owner_positions = [0]
    output_positions = [len(token_ids) - 1]
    packet_identity = {
        "query_sha256": query_sha256,
        "query_session_sha256": session_sha256,
        "query_source_family": query_source_family,
        "token_ids": token_ids,
        "owner_positions": owner_positions,
        "output_positions": output_positions,
        "record_receipts": [_receipt(record)],
    }
    return {
        **packet_identity,
        "packet_input_sha256": hashlib.sha256(_json_bytes(packet_identity)).hexdigest(),
        "records": [_record_json(record)],
        "record_objects": [record],
    }


def _class_map(value: object, *, allowed: set[int], label: str) -> dict[int, str]:
    if not isinstance(value, dict):
        raise ValueError(f"evaluator omitted {label}")
    try:
        result = {int(token): str(group) for token, group in value.items()}
    except (TypeError, ValueError) as exc:
        raise ValueError(f"evaluator {label} is invalid") from exc
    if set(result) != allowed or any(not group for group in result.values()):
        raise ValueError(
            f"evaluator {label} must classify every output token exactly once"
        )
    return result


def _source_authorities(audit: Mapping[str, Any]) -> list[dict[str, str]]:
    if audit.get("schema") != SOURCE_FAMILY_AUDIT_SCHEMA:
        raise ValueError("source-family audit schema changed")
    if (
        not str(audit.get("status") or "").startswith("VERIFIED_SOURCE_FAMILY_BOUNDARY")
        or int(audit.get("error_count", -1)) != 0
    ):
        raise ValueError("source-family audit is not verified")
    raw = audit.get("canonical_sources")
    if not isinstance(raw, list) or not raw:
        raise ValueError("source-family audit has no canonical sources")
    rows: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    for value in raw:
        if not isinstance(value, dict):
            raise TypeError("canonical source authority must be an object")
        path = _required_text(value.get("path"), label="canonical source path")
        family = _required_text(value.get("family_id"), label="canonical source family")
        digest = _required_sha256(
            value.get("content_sha256"), label="canonical source hash"
        )
        if path in seen_paths:
            raise ValueError("source-family audit repeats a canonical source path")
        seen_paths.add(path)
        rows.append({"path": path, "family_id": family, "content_sha256": digest})
    return rows


def _rebuild_packet_free_authority(
    authority_path: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    lane: str,
) -> dict[str, object]:
    """Independently reconstruct source spans and deterministic prompt transforms."""

    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    if not isinstance(authority, dict):
        raise TypeError(f"{lane} source authority must contain one object")
    if authority.get("schema") != PACKET_FREE_AUTHORITY_SCHEMA:
        raise ValueError(f"{lane} source authority schema changed")
    if authority.get("lane") != lane or authority.get("review_status") != "ADMITTED":
        raise ValueError(f"{lane} source authority is not admitted for this lane")
    grants = authority.get("authority")
    required_grants = (
        "training_intake",
        "optimization",
        "promotion",
        "partial_unfreeze",
        "tool_dispatch",
    )
    if not isinstance(grants, dict) or any(
        grants.get(field) != "NOT_AUTHORIZED" for field in required_grants
    ):
        raise ValueError(
            f"{lane} source authority grants execution or training authority"
        )
    authority_sha256 = _file_sha256(authority_path)
    family_id = f"packet-free-authority:{authority_sha256}"
    raw_sources = authority.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError(f"{lane} source authority has no source artifacts")
    records: dict[str, dict[str, object]] = {}
    paths: set[str] = set()
    hashes: set[str] = set()
    locators: set[str] = set()
    for source in raw_sources:
        if not isinstance(source, dict):
            raise TypeError(f"{lane} source artifact must be an object")
        path_text = _required_text(source.get("path"), label=f"{lane} source path")
        path = Path(path_text)
        if not path.is_absolute():
            raise ValueError(f"{lane} source path must be absolute")
        path = path.resolve(strict=True)
        path_key = str(path).replace("\\", "/").casefold()
        if path_key in paths:
            raise ValueError(f"{lane} source authority repeats a source path")
        paths.add(path_key)
        expected_hash = _required_sha256(
            source.get("sha256"), label=f"{lane} source hash"
        )
        source_bytes = path.read_bytes()
        if hashlib.sha256(source_bytes).hexdigest() != expected_hash:
            raise RuntimeError(f"{lane} source artifact hash differs")
        byte_count = source.get("bytes")
        if (
            isinstance(byte_count, bool)
            or not isinstance(byte_count, int)
            or byte_count != len(source_bytes)
        ):
            raise RuntimeError(f"{lane} source artifact byte count differs")
        hashes.add(expected_hash)
        raw_records = source.get("records")
        if not isinstance(raw_records, list) or not raw_records:
            raise ValueError(f"{lane} source artifact has no record spans")
        for record in raw_records:
            if not isinstance(record, dict):
                raise TypeError(f"{lane} source record must be an object")
            identity = _required_text(
                record.get("id"), label=f"{lane} source record id"
            )
            if identity in records:
                raise ValueError(f"{lane} source authority repeats a record identity")
            locator = _required_text(
                record.get("source_locator"), label=f"{lane} source locator"
            )
            if locator.casefold() in locators:
                raise ValueError(f"{lane} source authority repeats a source locator")
            locators.add(locator.casefold())
            start = record.get("byte_start")
            end = record.get("byte_end")
            if (
                isinstance(start, bool)
                or not isinstance(start, int)
                or isinstance(end, bool)
                or not isinstance(end, int)
                or start < 0
                or end <= start
                or end > len(source_bytes)
            ):
                raise ValueError(f"{lane} source span is empty or out of bounds")
            span = source_bytes[start:end]
            try:
                excerpt = span.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"{lane} source span is not exact UTF-8 text") from exc
            excerpt_hash = _required_sha256(
                record.get("excerpt_sha256"),
                label=f"{lane} source record excerpt hash",
            )
            if hashlib.sha256(span).hexdigest() != excerpt_hash:
                raise RuntimeError(f"{lane} source record excerpt hash differs")
            text_transform = _required_text(
                record.get("text_transform"),
                label=f"{lane} source record text transform",
            )
            if text_transform == PACKET_FREE_IDENTITY_TRANSFORM:
                text = excerpt
            elif text_transform == PACKET_FREE_LINE_JOIN_TRANSFORM:
                text = " ".join(
                    part.strip() for part in excerpt.splitlines() if part.strip()
                )
            else:
                raise ValueError(
                    f"unsupported packet-free text transform: {text_transform}"
                )
            if not text.strip():
                raise ValueError(f"{lane} source transform produced empty text")
            content_hash = _required_sha256(
                record.get("content_sha256"), label=f"{lane} source record content hash"
            )
            if hashlib.sha256(text.encode("utf-8")).hexdigest() != content_hash:
                raise RuntimeError(f"{lane} source record content hash differs")
            records[identity] = {
                "text": text,
                "source_locator": locator,
                "source_artifact_path": str(path),
                "source_artifact_sha256": expected_hash,
                "source_byte_start": start,
                "source_byte_end": end,
                "source_excerpt_sha256": excerpt_hash,
                "text_transform": text_transform,
                "content_sha256": content_hash,
            }
    seen: set[str] = set()
    for row in rows:
        identity = _required_text(row.get("id"), label=f"{lane} row id")
        if identity in seen or identity not in records:
            raise ValueError(f"{lane} row identity is repeated or unauthorized")
        seen.add(identity)
        expected = records[identity]
        expected_fields = {
            "split": lane,
            "text": expected["text"],
            "source_family": family_id,
            "source_locator": expected["source_locator"],
            "source_authority_sha256": authority_sha256,
            "source_artifact_path": expected["source_artifact_path"],
            "source_artifact_sha256": expected["source_artifact_sha256"],
            "source_byte_start": expected["source_byte_start"],
            "source_byte_end": expected["source_byte_end"],
            "source_excerpt_sha256": expected["source_excerpt_sha256"],
            "text_transform": expected["text_transform"],
            "content_sha256": expected["content_sha256"],
            "token_ids": list(str(expected["text"]).encode("utf-8")[:512]),
        }
        for field, expected_value in expected_fields.items():
            if row.get(field) != expected_value:
                raise ValueError(f"{lane} row differs from source authority at {field}")
    if seen != set(records):
        raise ValueError(f"{lane} source authority and lane record sets differ")
    return {
        "lane": lane,
        "family_id": family_id,
        "authority_path": str(authority_path),
        "authority_sha256": authority_sha256,
        "record_count": len(rows),
        "source_paths": sorted(paths),
        "source_sha256s": sorted(hashes),
        "content_sha256s": sorted(
            str(value["content_sha256"]) for value in records.values()
        ),
    }


def _resolve_source(
    relevant_source_suffix: object,
    authorities: Sequence[Mapping[str, str]],
) -> dict[str, str]:
    suffix = _required_text(relevant_source_suffix, label="relevant source suffix")
    normalized = suffix.replace("\\", "/").casefold().lstrip("/")
    matches = [
        dict(row)
        for row in authorities
        if row["path"].replace("\\", "/").casefold().endswith(normalized)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"replay source suffix resolves to {len(matches)} canonical sources"
        )
    return matches[0]


def _review_function_class(review: object, *, allowed: set[str]) -> str:
    if not isinstance(review, dict):
        raise ValueError("benchmark query omitted review metadata")
    explicit = review.get("review_stratum")
    if isinstance(explicit, str) and explicit in allowed:
        return explicit
    groups = review.get("topic_groups")
    if not isinstance(groups, list):
        raise ValueError("benchmark review omitted topic groups")
    matched = [str(group) for group in groups if str(group) in allowed]
    if len(matched) != 1:
        raise ValueError(
            "benchmark review must resolve to exactly one evaluator function class"
        )
    return matched[0]


def _benchmark_queries(benchmark: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if (
        benchmark.get("schema") != BENCHMARK_SCHEMA
        or benchmark.get("private_runtime_only") is not True
    ):
        raise ValueError("benchmark is not the private material benchmark")
    raw = benchmark.get("queries")
    if not isinstance(raw, list) or not raw:
        raise ValueError("benchmark contains no queries")
    result: dict[str, dict[str, Any]] = {}
    for value in raw:
        if not isinstance(value, dict):
            raise TypeError("benchmark query must be an object")
        record_id = _required_text(value.get("id"), label="benchmark query id")
        if record_id in result:
            raise ValueError("benchmark repeats a query identity")
        result[record_id] = value
    return result


def reconstruct_material_replay_cases(config: Mapping[str, Any]) -> dict[str, object]:
    """Rebuild held cases and targets from pinned source authorities.

    Producer runtime cases are deliberately not accepted by this function.
    Query bytes come from the pinned benchmark; target family and function come
    from the source-family audit and reviewed benchmark; token IDs come from the
    separately pinned evaluator receipt.
    """

    if config.get("schema") != RUNTIME_SCHEMA:
        raise ValueError("runtime config schema changed")
    arm = _required_text(config.get("arm"), label="runtime arm")
    if arm not in {"no_intervention", *CONTROL_MODES}:
        raise ValueError("runtime config names an unknown arm")
    source_path, source_manifest = _object_file(
        config.get("source_manifest"),
        config.get("source_manifest_sha256"),
        label="source manifest",
    )
    split_path, split_manifest = _object_file(
        config.get("split_manifest"),
        config.get("split_manifest_sha256"),
        label="split manifest",
    )
    cases_path, cases_manifest = _object_file(
        config.get("cases_manifest"),
        config.get("cases_manifest_sha256"),
        label="case manifest",
    )
    evaluator_path, evaluator = _object_file(
        config.get("evaluator_receipt"),
        config.get("evaluator_receipt_sha256"),
        label="evaluator receipt",
    )
    if (
        source_manifest.get("schema") != SOURCE_MANIFEST_SCHEMA
        or source_manifest.get("private_runtime_only") is not True
    ):
        raise ValueError("source manifest is not the private material authority")
    pinned: dict[str, Path] = {}
    for name in (
        "benchmark",
        "source_family_audit",
        "source_queue",
        "closed_source_snapshot",
        "ordinary_source",
        "ordinary_source_authority",
        "retention_source",
        "retention_source_authority",
    ):
        pinned[name] = _pinned_path(
            source_manifest.get(name),
            source_manifest.get(f"{name}_sha256"),
            label=name.replace("_", " "),
        )
    benchmark = json.loads(pinned["benchmark"].read_text(encoding="utf-8"))
    audit = json.loads(pinned["source_family_audit"].read_text(encoding="utf-8"))
    queue = json.loads(pinned["source_queue"].read_text(encoding="utf-8"))
    snapshot = json.loads(pinned["closed_source_snapshot"].read_text(encoding="utf-8"))
    if not all(
        isinstance(value, dict) for value in (benchmark, audit, queue, snapshot)
    ):
        raise TypeError("replay authorities must be JSON objects")
    benchmark_by_id = _benchmark_queries(benchmark)
    authorities = _source_authorities(audit)
    if queue.get("schema") != REVIEW_QUEUE_SCHEMA:
        raise ValueError("source review queue schema changed")
    if snapshot.get("schema") != CLOSED_SOURCE_SNAPSHOT_SCHEMA:
        raise ValueError("closed-source snapshot schema changed")
    queue_sessions_raw = queue.get("session_ids")
    snapshot_sources = snapshot.get("sources")
    closed_sessions_raw = source_manifest.get("closed_query_sessions")
    if (
        not isinstance(queue_sessions_raw, list)
        or not isinstance(snapshot_sources, list)
        or not isinstance(closed_sessions_raw, list)
    ):
        raise ValueError("source authorities omitted closed-session identities")
    queue_sessions = {
        _required_text(value, label="queue session") for value in queue_sessions_raw
    }
    snapshot_sessions = {
        _required_text(value.get("source_session"), label="snapshot source session")
        for value in snapshot_sources
        if isinstance(value, dict)
    }
    closed_sessions = {
        _required_text(value, label="closed query session")
        for value in closed_sessions_raw
    }
    if len(snapshot_sessions) != len(snapshot_sources):
        raise ValueError("closed-source snapshot repeats or omits session identities")
    if (
        not queue_sessions.issubset(snapshot_sessions)
        or closed_sessions != snapshot_sessions
    ):
        raise ValueError(
            "source manifest, queue, and closed snapshot disagree on sessions"
        )
    if cases_manifest.get("schema") != CASE_MANIFEST_SCHEMA:
        raise ValueError("case manifest schema changed")
    if (
        cases_manifest.get("source_disjoint") is not True
        or cases_manifest.get("query_session_disjoint") is not True
    ):
        raise ValueError("case manifest does not declare the dual-source boundary")
    if (
        cases_manifest.get("packet_free_source_authority_bound") is not True
        or cases_manifest.get("packet_free_source_authority_schema")
        != PACKET_FREE_AUTHORITY_SCHEMA
    ):
        raise ValueError("case manifest omits packet-free source authority")
    if cases_manifest.get("exact_source_manifest_sha256") != _file_sha256(source_path):
        raise RuntimeError("case manifest names another source manifest")
    if cases_manifest.get("exact_split_manifest_sha256") != _file_sha256(split_path):
        raise RuntimeError("case manifest names another split manifest")
    if cases_manifest.get("exact_evaluator_receipt_sha256") != _file_sha256(
        evaluator_path
    ):
        raise RuntimeError("case manifest names another evaluator receipt")
    if evaluator.get("schema") != EVALUATOR_RECEIPT_SCHEMA:
        raise ValueError("evaluator receipt schema changed")
    if (
        evaluator.get("scoring")
        != "full-vocabulary-argmax_then_exact_and_class_equivalence"
    ):
        raise ValueError("evaluator scoring contract changed")
    allowed_raw = evaluator.get("allowed_output_token_ids")
    if not isinstance(allowed_raw, list) or any(
        isinstance(token, bool) or not isinstance(token, int) for token in allowed_raw
    ):
        raise ValueError("evaluator output token set is invalid")
    allowed = set(allowed_raw)
    if not allowed or len(allowed) != len(allowed_raw) or min(allowed) < 0:
        raise ValueError("evaluator output token set is empty, duplicated, or negative")
    relationship_classes = _class_map(
        evaluator.get("relationship_class_by_token_id"),
        allowed=allowed,
        label="relationship classes",
    )
    function_classes = _class_map(
        evaluator.get("function_class_by_token_id"),
        allowed=allowed,
        label="function classes",
    )
    if (
        cases_manifest.get("allowed_output_token_ids") != allowed_raw
        or cases_manifest.get("relationship_class_by_token_id")
        != evaluator.get("relationship_class_by_token_id")
        or cases_manifest.get("function_class_by_token_id")
        != evaluator.get("function_class_by_token_id")
    ):
        raise RuntimeError("case manifest and evaluator token maps differ")
    token_by_classes: dict[tuple[str, str], int] = {}
    for token_id in sorted(allowed):
        key = (relationship_classes[token_id], function_classes[token_id])
        if key in token_by_classes:
            raise ValueError("evaluator repeats a family/function class pair")
        token_by_classes[key] = token_id
    if split_manifest.get("schema") != SPLIT_MANIFEST_SCHEMA:
        raise ValueError("split manifest schema changed")
    if (
        split_manifest.get("source_disjoint") is not True
        or split_manifest.get("query_session_disjoint") is not True
        or split_manifest.get("component_policy")
        != "catalog-family/query-session connected components"
    ):
        raise ValueError("split manifest does not declare the dual-source boundary")
    files = cases_manifest.get("files")
    if not isinstance(files, dict) or set(files) != set(ALL_CASE_LANES):
        raise ValueError("case manifest does not contain the exact required lanes")
    lane_rows = {
        lane: _manifest_rows(cases_path.parent, files[lane], lane=lane)
        for lane in ALL_CASE_LANES
    }
    packet_free_receipts = {
        lane: _rebuild_packet_free_authority(
            pinned[f"{lane}_source_authority"], lane_rows[lane], lane=lane
        )
        for lane in ("ordinary", "retention")
    }
    if source_manifest.get("packet_free_authorities") != packet_free_receipts:
        raise RuntimeError("source manifest packet-free authority receipts differ")
    material_paths = {
        str(Path(row["path"]).resolve(strict=False)).replace("\\", "/").casefold()
        for row in authorities
    }
    material_hashes = {row["content_sha256"] for row in authorities}
    ordinary_paths = set(packet_free_receipts["ordinary"]["source_paths"])
    retention_paths = set(packet_free_receipts["retention"]["source_paths"])
    ordinary_hashes = set(packet_free_receipts["ordinary"]["source_sha256s"])
    retention_hashes = set(packet_free_receipts["retention"]["source_sha256s"])
    ordinary_content_hashes = set(packet_free_receipts["ordinary"]["content_sha256s"])
    retention_content_hashes = set(packet_free_receipts["retention"]["content_sha256s"])
    material_query_hashes = {
        _required_sha256(row.get("query_sha256"), label="material query hash")
        for lane in MATERIAL_LANES
        for row in lane_rows[lane]
    }
    if material_paths & (ordinary_paths | retention_paths):
        raise ValueError("packet-free lanes reuse a material source path")
    if material_hashes & (ordinary_hashes | retention_hashes):
        raise ValueError("packet-free lanes reuse a material source artifact")
    if ordinary_paths & retention_paths or ordinary_hashes & retention_hashes:
        raise ValueError("ordinary and retention lanes reuse a source authority")
    if ordinary_content_hashes & retention_content_hashes:
        raise ValueError("ordinary and retention lanes reuse exact source content")
    if material_query_hashes & (ordinary_content_hashes | retention_content_hashes):
        raise ValueError("packet-free lanes reuse a material query")
    max_query_bytes = cases_manifest.get("max_query_bytes")
    if isinstance(max_query_bytes, bool) or not isinstance(max_query_bytes, int):
        raise ValueError("case manifest max_query_bytes is invalid")
    material_sets: dict[str, dict[str, set[str]]] = {}
    for lane in MATERIAL_LANES:
        rows = lane_rows[lane]
        if not rows:
            raise ValueError(f"material lane {lane} is empty")
        material_sets[lane] = {
            "records": {
                _required_text(row.get("record_id"), label="record id") for row in rows
            },
            "families": {
                _required_text(row.get("source_family"), label="source family")
                for row in rows
            },
            "queries": {
                _required_text(
                    row.get("query_source_family"), label="query source family"
                )
                for row in rows
            },
        }
        if any(row.get("split") != lane for row in rows):
            raise ValueError(f"material row is stored in the wrong lane: {lane}")
    for left_index, left in enumerate(MATERIAL_LANES):
        for right in MATERIAL_LANES[left_index + 1 :]:
            for key in ("records", "families", "queries"):
                if material_sets[left][key] & material_sets[right][key]:
                    raise ValueError(f"material split overlaps {key}: {left}/{right}")
    expected_counts = {lane: len(lane_rows[lane]) for lane in MATERIAL_LANES}
    expected_families = {
        lane: sorted(material_sets[lane]["families"]) for lane in MATERIAL_LANES
    }
    expected_queries = {
        lane: sorted(material_sets[lane]["queries"]) for lane in MATERIAL_LANES
    }
    if split_manifest.get("lane_counts") != expected_counts:
        raise ValueError("split manifest lane counts differ from material cases")
    if split_manifest.get("lane_source_families") != expected_families:
        raise ValueError("split manifest catalog families differ from material cases")
    if split_manifest.get("lane_query_source_families") != expected_queries:
        raise ValueError("split manifest query families differ from material cases")

    allowed_functions = set(function_classes.values())
    rebuilt_by_lane: dict[str, list[dict[str, Any]]] = {lane: [] for lane in HELD_LANES}
    receipt_rows: list[dict[str, object]] = []
    fields = (
        "query_sha256",
        "query_session_sha256",
        "query_source_family",
        "packet_input_sha256",
        "token_ids",
        "owner_positions",
        "output_positions",
        "records",
    )
    for lane in HELD_LANES:
        for producer_row in lane_rows[lane]:
            record_id = _required_text(producer_row.get("record_id"), label="record id")
            benchmark_row = benchmark_by_id.get(record_id)
            if benchmark_row is None:
                raise ValueError("held case is absent from the pinned benchmark")
            query = _required_text(benchmark_row.get("query"), label="benchmark query")
            query_source_uri = _required_text(
                benchmark_row.get("query_source_uri"),
                label="benchmark query source URI",
            )
            session_id = _source_session(query_source_uri)
            if session_id not in closed_sessions:
                raise ValueError(
                    "held query session is absent from the closed-source snapshot"
                )
            rebuilt_input = _rebuild_query_input(
                query,
                query_source_uri,
                max_query_bytes=max_query_bytes,
            )
            if (
                producer_row.get("query") != query
                or producer_row.get("query_source_uri") != query_source_uri
            ):
                raise ValueError("held case query differs from the pinned benchmark")
            for field in fields:
                if producer_row.get(field) != rebuilt_input[field]:
                    raise ValueError(
                        f"held case query-derived input differs at {field}"
                    )
            target_source = _resolve_source(
                benchmark_row.get("relevant_source_suffix"),
                authorities,
            )
            function_class = _review_function_class(
                benchmark_row.get("review"),
                allowed=allowed_functions,
            )
            target_token = token_by_classes.get(
                (target_source["family_id"], function_class)
            )
            if target_token is None:
                raise ValueError("pinned source/function pair has no evaluator token")
            expected_target_metadata = {
                "source_family": target_source["family_id"],
                "target_source_path": target_source["path"],
                "target_source_sha256": target_source["content_sha256"],
                "function_class": function_class,
                "target_token_id": target_token,
            }
            for field, expected in expected_target_metadata.items():
                if producer_row.get(field) != expected:
                    raise ValueError(
                        f"producer target metadata differs from pinned authority at {field}"
                    )
            targets = list(rebuilt_input["token_ids"])
            output_positions = list(rebuilt_input["output_positions"])
            if len(output_positions) != 1:
                raise ValueError("held case must have exactly one bounded output")
            targets[output_positions[0]] = target_token
            if producer_row.get("targets") != targets:
                raise ValueError(
                    "producer targets differ from independently reconstructed targets"
                )
            records = list(rebuilt_input["record_objects"])
            rebuilt_by_lane[lane].append(
                {
                    "record_id": record_id,
                    "source_family": target_source["family_id"],
                    "query_source_family": rebuilt_input["query_source_family"],
                    "token_ids": list(rebuilt_input["token_ids"]),
                    "targets": targets,
                    "owner_positions": list(rebuilt_input["owner_positions"]),
                    "output_positions": output_positions,
                    "records": records,
                    "packet_input_sha256": rebuilt_input["packet_input_sha256"],
                    "target_token_id": target_token,
                }
            )
            receipt_rows.append(
                {
                    "record_id": record_id,
                    "split": lane,
                    "packet_input_sha256": rebuilt_input["packet_input_sha256"],
                    "target_token_id": target_token,
                    "target_source_sha256": target_source["content_sha256"],
                }
            )

    packet_mode = "canonical_six_view_reader" if arm == "no_intervention" else arm
    configured_frame = config.get("single_frame")
    frame = str(configured_frame or "lexical")
    if packet_mode == "single_frame_reader":
        if not isinstance(configured_frame, str) or configured_frame not in VIEW_NAMES:
            raise ValueError("single-frame replay requires one explicit named frame")
        if configured_frame == "lexical":
            raise ValueError("single-frame lexical duplicates the lexical-only control")
    cases: list[dict[str, object]] = []
    for lane in HELD_LANES:
        binding_pool = [
            record for row in rebuilt_by_lane[lane] for record in row["records"]
        ]
        for row in rebuilt_by_lane[lane]:
            cases.append(
                {
                    "records": [list(row["records"])],
                    "owner_positions": [list(row["owner_positions"])],
                    "sequence_length": len(row["token_ids"]),
                    "mode": packet_mode,
                    "frame": frame,
                    "binding_pool": (
                        binding_pool
                        if packet_mode == "shuffled_binding_reader"
                        else None
                    ),
                    "token_ids": [list(row["token_ids"])],
                    "targets": [list(row["targets"])],
                    "record_ids": [row["record_id"]],
                    "splits": [lane],
                    "source_families": [row["source_family"]],
                    "query_source_families": [row["query_source_family"]],
                    "output_positions": [list(row["output_positions"])],
                    "allowed_output_token_ids": sorted(allowed),
                    "exact_evaluator_receipt_sha256": _file_sha256(evaluator_path),
                }
            )
    receipt = {
        "schema": SOURCE_RECONSTRUCTION_SCHEMA,
        "source_manifest_sha256": _file_sha256(source_path),
        "split_manifest_sha256": _file_sha256(split_path),
        "cases_manifest_sha256": _file_sha256(cases_path),
        "evaluator_receipt_sha256": _file_sha256(evaluator_path),
        "held_case_count": len(cases),
        "held_cases_sha256": hashlib.sha256(_json_bytes(receipt_rows)).hexdigest(),
        "producer_runtime_cases_consumed": False,
        "producer_targets_consumed": False,
        "producer_targets_verified": True,
        "query_inputs_rebuilt_from_benchmark": True,
        "targets_rebuilt_from_source_and_evaluator": True,
        "packet_free_authorities_rebuilt_from_exact_spans": True,
        "packet_free_authority_sha256s": {
            lane: packet_free_receipts[lane]["authority_sha256"]
            for lane in ("ordinary", "retention")
        },
        "packet_free_source_artifact_sha256s": {
            lane: packet_free_receipts[lane]["source_sha256s"]
            for lane in ("ordinary", "retention")
        },
    }
    return {"cases": cases, "receipt": receipt}


def _coordinates(identity: str, width: int) -> Tensor:
    raw = bytearray()
    counter = 0
    payload = identity.encode("utf-8")
    while len(raw) < width * 2:
        raw += hashlib.sha256(payload + counter.to_bytes(4, "big")).digest()
        counter += 1
    values = torch.empty(width, dtype=torch.float32)
    for index in range(width):
        integer = (raw[2 * index] << 8) | raw[2 * index + 1]
        values[index] = integer / 32767.5 - 1.0
    length = torch.sqrt(torch.sum(values * values)).clamp_min(1e-12)
    return values / length


def _canonical_vector(record: PrimeTokenRecord) -> Tensor:
    output = torch.empty(FEATURE_WIDTH, dtype=torch.float32)
    for view_index, view_name in enumerate(VIEW_NAMES):
        identity = json.dumps(
            {
                "canonical_id": record.canonical_id,
                "view": view_name,
                "features": _items(record.views[view_name]),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        start = view_index * VIEW_WIDTH
        output[start : start + VIEW_WIDTH] = _coordinates(identity, VIEW_WIDTH)
    return output


def reconstruct_packet_independently(
    records: Sequence[Sequence[PrimeTokenRecord]],
    owner_positions: Sequence[Sequence[int]],
    *,
    sequence_length: int,
    mode: str,
    frame: str = "lexical",
    binding_pool: Sequence[PrimeTokenRecord] | None = None,
) -> SealedPrimeTokenBatch:
    """Rebuild a producer packet without calling its packet builder."""

    if mode not in CONTROL_MODES:
        raise ValueError("unknown replay control mode")
    if sequence_length <= 0 or not records or len(records) != len(owner_positions):
        raise ValueError("replay records and owner positions differ")
    if frame not in VIEW_NAMES:
        raise ValueError("unknown replay frame")
    if mode == "shuffled_binding_reader" and binding_pool is None:
        raise ValueError(
            "replay shuffled binding requires an explicit dataset-wide pool"
        )
    if mode != "shuffled_binding_reader" and binding_pool is not None:
        raise ValueError("replay binding pool is valid only for shuffled binding")
    features = torch.zeros((len(records), sequence_length, FEATURE_WIDTH))
    owners = torch.zeros((len(records), sequence_length), dtype=torch.bool)
    views = torch.zeros(
        (len(records), sequence_length, len(VIEW_NAMES)), dtype=torch.bool
    )
    flattened = [
        (batch_index, local_index, record)
        for batch_index, row in enumerate(records)
        for local_index, record in enumerate(row)
    ]
    shuffled: dict[str, Tensor] = {}
    binding_pool_sha256: str | None = None
    binding_permutation_sha256: str | None = None
    if mode == "shuffled_binding_reader":
        pool = list(binding_pool or ())
        rows: list[tuple[str, str, Tensor]] = []
        for record in pool:
            record.validate()
            receipt = _receipt(record)
            vector = _canonical_vector(record)
            rows.append((receipt, tensor_sha256(vector), vector))
        receipts = [row[0] for row in rows]
        if len(pool) < 2 or len(set(receipts)) != len(receipts):
            raise ValueError(
                "replay shuffled binding pool must be unique and nontrivial"
            )
        rows.sort(key=lambda row: (row[1], row[0]))
        group_counts: dict[str, int] = {}
        for _, vector_sha256, _ in rows:
            group_counts[vector_sha256] = group_counts.get(vector_sha256, 0) + 1
        shift = max(group_counts.values())
        if shift * 2 > len(rows):
            raise ValueError(
                "replay shuffled binding pool cannot form a vector derangement"
            )
        sources = rows[shift:] + rows[:shift]
        if any(
            target[1] == source[1] for target, source in zip(rows, sources, strict=True)
        ):
            raise RuntimeError(
                "replay shuffled binding derangement construction failed"
            )
        shuffled = {
            target[0]: source[2] for target, source in zip(rows, sources, strict=True)
        }
        binding_pool_sha256 = hashlib.sha256(
            _json_bytes({"record_receipts": sorted(receipts)})
        ).hexdigest()
        binding_permutation_sha256 = hashlib.sha256(
            _json_bytes(
                {
                    "bindings": [
                        {
                            "target_receipt": target[0],
                            "source_receipt": source[0],
                        }
                        for target, source in zip(rows, sources, strict=True)
                    ]
                }
            )
        ).hexdigest()
        if {_receipt(record) for _, _, record in flattened} - set(shuffled):
            raise ValueError("replay shuffled binding pool omits packet occurrences")
    receipt_rows = []
    for batch_index, (row, positions) in enumerate(
        zip(records, owner_positions, strict=True)
    ):
        if len(row) != len(positions):
            raise ValueError("replay row and positions differ")
        current_receipts = []
        for _local_index, (record, raw_position) in enumerate(
            zip(row, positions, strict=True)
        ):
            record.validate()
            position = int(raw_position)
            if (
                position < 0
                or position >= sequence_length
                or owners[batch_index, position]
            ):
                raise ValueError("replay owner position is invalid")
            canonical = _canonical_vector(record)
            if mode == "canonical_six_view_reader":
                vector = canonical
                active = range(len(VIEW_NAMES))
            elif mode == "lexical_only_reader":
                vector = torch.zeros(FEATURE_WIDTH)
                vector[:VIEW_WIDTH] = canonical[:VIEW_WIDTH]
                active = (0,)
            elif mode == "random_fixed_reader":
                vector = torch.cat(
                    [
                        _coordinates(
                            f"random-fixed:{RANDOM_CONTROL_SEED}:"
                            f"{record.canonical_id}:{record.section_id}:{view_index}",
                            VIEW_WIDTH,
                        )
                        for view_index in range(len(VIEW_NAMES))
                    ]
                )
                active = range(len(VIEW_NAMES))
            elif mode == "shuffled_binding_reader":
                vector = shuffled[_receipt(record)]
                active = range(len(VIEW_NAMES))
            else:
                frame_index = VIEW_NAMES.index(frame)
                start = frame_index * VIEW_WIDTH
                vector = torch.zeros(FEATURE_WIDTH)
                vector[start : start + VIEW_WIDTH] = canonical[
                    start : start + VIEW_WIDTH
                ]
                active = (frame_index,)
            features[batch_index, position] = vector
            owners[batch_index, position] = True
            views[batch_index, position, list(active)] = True
            current_receipts.append(_receipt(record))
        receipt_rows.append(tuple(current_receipts))
    metadata = {
        "schema": PACKET_SCHEMA,
        "mode": mode,
        "frame": frame if mode == "single_frame_reader" else None,
        "feature_shape": list(features.shape),
        "owner_shape": list(owners.shape),
        "view_shape": list(views.shape),
        "record_receipts": [list(row) for row in receipt_rows],
        "binding_pool_sha256": binding_pool_sha256,
        "binding_permutation_sha256": binding_permutation_sha256,
        "features_sha256": tensor_sha256(features),
        "owner_mask_sha256": tensor_sha256(owners),
        "view_mask_sha256": tensor_sha256(views),
    }
    packet = SealedPrimeTokenBatch(
        features=features,
        owner_mask=owners,
        view_mask=views,
        mode=mode,
        frame=metadata["frame"],
        record_receipts=tuple(receipt_rows),
        binding_pool_sha256=binding_pool_sha256,
        binding_permutation_sha256=binding_permutation_sha256,
        features_sha256=str(metadata["features_sha256"]),
        owner_mask_sha256=str(metadata["owner_mask_sha256"]),
        view_mask_sha256=str(metadata["view_mask_sha256"]),
        seal_sha256=hashlib.sha256(_json_bytes(metadata)).hexdigest(),
    )
    packet.validate()
    return packet


def load_adapter_read_only(
    checkpoint_dir: str | Path,
    *,
    model: FullSystemPrimeTokenInputAccessLM,
    expected_identity: Mapping[str, str],
) -> dict[str, object]:
    """Verify and load only adapter tensors from a checkpoint lineage."""

    root = Path(checkpoint_dir).resolve(strict=True)
    pointer = json.loads((root / "LATEST.json").read_text(encoding="utf-8"))
    if pointer.get("schema") != POINTER_SCHEMA:
        raise RuntimeError("replay pointer schema differs")
    target = (root / str(pointer.get("file"))).resolve(strict=True)
    if not target.is_relative_to(root) or sha256_file(target) != pointer.get("sha256"):
        raise RuntimeError("replay checkpoint pointer/hash verification failed")
    payload = torch.load(target, map_location="cpu", weights_only=False)
    if payload.get("schema") != CHECKPOINT_SCHEMA:
        raise RuntimeError("replay checkpoint schema differs")
    if payload.get("identity") != dict(expected_identity):
        raise RuntimeError("replay checkpoint identity differs")
    if pointer.get("identity_sha256") != canonical_sha256(dict(expected_identity)):
        raise RuntimeError("replay pointer identity differs")
    if payload.get("parent_sha256") != module_state_sha256(model.core):
        raise RuntimeError("replay parent differs from checkpoint lineage")
    model.load_adapter_state_dict(payload["adapter"])
    return {
        "checkpoint": str(target),
        "checkpoint_sha256": pointer["sha256"],
        "step": int(payload["step"]),
        "identity_sha256": pointer["identity_sha256"],
        "producer_metrics_ignored": True,
    }


def verify_no_intervention_parent(
    *,
    model: FullSystemPrimeTokenInputAccessLM,
    expected_identity: Mapping[str, str],
) -> dict[str, object]:
    """Seal the checkpoint-free baseline against its declared frozen parent."""

    if expected_identity.get("arm") != "no_intervention":
        raise ValueError("checkpoint-free replay is valid only for no_intervention")
    expected_parent = str(expected_identity.get("parent_sha256") or "")
    actual_parent = module_state_sha256(model.core)
    if not expected_parent or expected_parent != actual_parent:
        raise RuntimeError("replay parent differs from no-intervention lineage")
    return {
        "checkpoint": None,
        "checkpoint_sha256": None,
        "step": 0,
        "identity_sha256": canonical_sha256(dict(expected_identity)),
        "producer_metrics_ignored": True,
        "checkpoint_free_baseline": True,
    }


@torch.no_grad()
def replay_predictions(
    model: FullSystemPrimeTokenInputAccessLM,
    token_ids: Tensor,
    targets: Tensor,
    packet: SealedPrimeTokenBatch,
    *,
    use_prime_packet: bool = True,
    record_ids: Sequence[str],
    splits: Sequence[str],
    source_families: Sequence[str],
    query_source_families: Sequence[str],
    output_positions: Sequence[Sequence[int]],
    allowed_output_token_ids: Sequence[int],
    exact_evaluator_receipt_sha256: str,
) -> dict[str, object]:
    """Recompute only declared bounded outputs from held, receipted examples."""

    packet.validate()
    if token_ids.ndim != 2 or token_ids.dtype != torch.long:
        raise ValueError("replay token IDs must be torch.long [batch,time]")
    if targets.shape != token_ids.shape or targets.dtype != torch.long:
        raise ValueError("replay targets must match token IDs and use torch.long")
    if tuple(packet.owner_mask.shape) != tuple(token_ids.shape):
        raise ValueError("replay packet differs from token IDs")
    batch_size = token_ids.shape[0]
    if not (
        len(record_ids)
        == len(splits)
        == len(source_families)
        == len(query_source_families)
        == len(output_positions)
        == batch_size
    ):
        raise ValueError("replay provenance rows differ from batch size")
    if (
        not all(isinstance(value, str) and value.strip() for value in record_ids)
        or not all(
            isinstance(value, str) and value.strip() for value in source_families
        )
        or not all(
            isinstance(value, str) and value.strip() for value in query_source_families
        )
    ):
        raise ValueError(
            "replay record, catalog-family, and query-source identities are required"
        )
    if any(split not in {"validation", "final_test"} for split in splits):
        raise ValueError("replay accepts only validation/final-test rows")
    if len(exact_evaluator_receipt_sha256) != 64 or any(
        character not in "0123456789abcdef"
        for character in exact_evaluator_receipt_sha256
    ):
        raise ValueError("replay evaluator receipt SHA-256 is invalid")
    allowed = set(allowed_output_token_ids)
    if (
        not allowed
        or len(allowed) != len(tuple(allowed_output_token_ids))
        or any(
            isinstance(token_id, bool) or not isinstance(token_id, int) or token_id < 0
            for token_id in allowed
        )
    ):
        raise ValueError("replay allowed output token IDs are invalid")
    normalized_positions: list[tuple[int, ...]] = []
    for batch_index, raw_positions in enumerate(output_positions):
        positions = tuple(int(position) for position in raw_positions)
        if not positions or positions != tuple(sorted(set(positions))):
            raise ValueError("replay output positions must be sorted and unique")
        if positions[0] < 0 or positions[-1] >= token_ids.shape[1]:
            raise ValueError("replay output position is out of bounds")
        owner_positions = packet.owner_mask[batch_index].nonzero().flatten().tolist()
        if not owner_positions or max(owner_positions) > positions[0]:
            raise ValueError("replay output precedes a required owner position")
        if any(
            int(targets[batch_index, position]) not in allowed for position in positions
        ):
            raise ValueError("replay target lies outside the bounded output set")
        normalized_positions.append(positions)

    model.eval()
    logits = model(token_ids, prime_packet=packet if use_prime_packet else None)
    if logits.ndim != 3 or tuple(logits.shape[:2]) != tuple(token_ids.shape):
        raise RuntimeError("replay model returned invalid logits")
    if max(allowed) >= logits.shape[-1]:
        raise ValueError("replay allowed output token exceeds model vocabulary")
    predictions = logits.argmax(dim=-1).cpu()
    expected = targets.cpu()
    rows = []
    for batch_index in range(predictions.shape[0]):
        for position in normalized_positions[batch_index]:
            target = int(expected[batch_index, position])
            raw_logits = logits[batch_index, position].detach().float().cpu()
            target_logit = float(raw_logits[target])
            target_nll = float(torch.logsumexp(raw_logits, dim=0) - raw_logits[target])
            rows.append(
                {
                    "id": f"{record_ids[batch_index]}:{position}",
                    "record_id": record_ids[batch_index],
                    "split": splits[batch_index],
                    "source_family": source_families[batch_index],
                    "query_source_family": query_source_families[batch_index],
                    "batch": batch_index,
                    "position": position,
                    "prediction": int(predictions[batch_index, position]),
                    "target": target,
                    "target_logit": target_logit,
                    "target_nll": target_nll,
                    "correct": bool(
                        predictions[batch_index, position]
                        == expected[batch_index, position]
                    ),
                    "owned": bool(packet.owner_mask[batch_index, position]),
                }
            )
    correct = sum(int(row["correct"]) for row in rows)
    mean_target_nll = sum(float(row["target_nll"]) for row in rows) / len(rows)
    return {
        "schema": "scbe.prime-token-independent-replay.v1",
        "packet_seal_sha256": packet.seal_sha256,
        "exact_evaluator_receipt_sha256": exact_evaluator_receipt_sha256,
        "allowed_output_token_ids": sorted(allowed),
        "example_count": len(rows),
        "correct_count": correct,
        "accuracy": correct / len(rows) if rows else 0.0,
        "mean_target_nll": mean_target_nll,
        "prime_packet_used": use_prime_packet,
        "outcomes": rows,
        "tool_dispatch": False,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }


def verify_replay_ledger(
    expected_path: str | Path, replay: Mapping[str, object]
) -> None:
    """Fail when a producer ledger differs from independently replayed outcomes."""

    expected = json.loads(Path(expected_path).read_text(encoding="utf-8"))
    compared_fields = (
        "packet_seal_sha256",
        "exact_evaluator_receipt_sha256",
        "allowed_output_token_ids",
        "example_count",
        "correct_count",
        "accuracy",
        "prime_packet_used",
        "outcomes",
    )
    for field in compared_fields:
        if expected.get(field) != replay.get(field):
            raise RuntimeError(f"producer ledger differs from replay for {field}")


__all__ = [
    "SOURCE_RECONSTRUCTION_SCHEMA",
    "load_adapter_read_only",
    "reconstruct_material_replay_cases",
    "reconstruct_packet_independently",
    "replay_predictions",
    "verify_no_intervention_parent",
    "verify_replay_ledger",
]
