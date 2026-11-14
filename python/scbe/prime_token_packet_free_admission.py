"""Admit reviewed packet-free provenance without authorizing model training.

The draft producer is intentionally unable to admit its own output.  This
module consumes an immutable draft directory plus a separately authored,
hash-bound decision ledger.  It reconstructs every source span again, emits
only explicitly admitted rows, and replays the production source validator.

``ADMITTED`` in this module means that the source provenance is accepted.  It
does not authorize training, optimization, execution, promotion, partial
unfreezing, or tool dispatch.
"""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
from typing import Any, Mapping, Sequence
from uuid import UUID

from .prime_token_packet_free_authority import (
    NO_AUTHORITY,
    PACKET_FREE_AUTHORITY_SCHEMA,
    PACKET_FREE_REVIEW_STATUS,
    REQUIRED_AUTHORITY_FIELDS,
    transform_packet_free_text,
    validate_packet_free_rows,
)
from .prime_token_packet_free_authority_draft import (
    DRAFT_BUILD_SCHEMA,
    DRAFT_REVIEW_STATUS,
    DRAFT_STATUS,
)
from .prime_token_training import sha256_file

REVIEW_DECISION_SCHEMA = "scbe.prime-token-packet-free-review-decisions.v1"
ADMISSION_BUILD_SCHEMA = "scbe.prime-token-packet-free-authority-admission-build.v1"
ADMISSION_STATUS = "PROVENANCE_ADMITTED_TRAINING_NOT_AUTHORIZED"
ADMIT = "ADMIT"
REJECT = "REJECT"
DECISIONS = (ADMIT, REJECT)

ADMIT_REASON_CODES = frozenset(
    {
        "SOURCE_PROVENANCE_VERIFIED",
        "LICENSE_RECEIPT_VERIFIED",
        "SUBSTANTIVE_CONTROL_TEXT",
        "LANE_ROLE_APPROPRIATE",
    }
)
REJECT_REASON_CODES = frozenset(
    {
        "MARKUP_ONLY",
        "INCOMPLETE_CONTEXT",
        "DUPLICATE_SEMANTICS",
        "UNSAFE_OR_SENSITIVE",
        "WRONG_LANE",
        "OTHER_REVIEWED_REJECTION",
    }
)
ALLOWED_REASON_CODES = ADMIT_REASON_CODES | REJECT_REASON_CODES

_DRAFT_OUTPUT_KEYS = {
    "ordinary": ("ordinary_authority", "ordinary_source"),
    "retention": ("retention_authority", "retention_source"),
}

_DISABLED_BUILD_AUTHORITY = {
    "dataset_admission": "NONE",
    "execution": "NONE",
    "material_evidence": "NONE",
    "optimization": "NONE",
    "partial_unfreeze": "NONE",
    "promotion": "NONE",
    "tool_dispatch": "DISABLED",
    "training_intake": "NONE",
}


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


def _required_nonnegative_int(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{label} must contain one JSON object")
    return value


def _load_jsonl(path: Path, *, label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError(f"{label} line {line_number} must contain one JSON object")
        rows.append(value)
    if not rows:
        raise ValueError(f"{label} is empty")
    return rows


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(dict(row), sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _descriptor(path: Path, records: int) -> dict[str, object]:
    return {
        "bytes": path.stat().st_size,
        "path": path.name,
        "records": records,
        "sha256": sha256_file(path),
    }


def _superseded_receipt_descriptors(
    paths: Sequence[str | Path],
) -> list[dict[str, object]]:
    descriptors: list[dict[str, object]] = []
    seen_paths: set[str] = set()
    seen_hashes: set[str] = set()
    for raw_path in paths:
        path = Path(raw_path).resolve(strict=True)
        path_key = str(path).replace("\\", "/").casefold()
        if path_key in seen_paths:
            raise ValueError("superseded admission receipt path is repeated")
        seen_paths.add(path_key)
        receipt = _load_json(path, label="superseded admission receipt")
        if (
            receipt.get("schema") != ADMISSION_BUILD_SCHEMA
            or receipt.get("status") != ADMISSION_STATUS
            or receipt.get("training_authorized") is not False
        ):
            raise ValueError("superseded receipt is not a non-training admission build")
        authority = receipt.get("authority")
        if not isinstance(authority, dict) or any(
            authority.get(field) != value
            for field, value in _DISABLED_BUILD_AUTHORITY.items()
        ):
            raise ValueError("superseded receipt contains operational authority")
        digest = sha256_file(path)
        if digest in seen_hashes:
            raise ValueError("superseded admission receipt hash is repeated")
        seen_hashes.add(digest)
        descriptors.append(
            {
                "bytes": path.stat().st_size,
                "path": str(path),
                "reason": "REPLACED_BY_THIS_RECEIPT",
                "schema": ADMISSION_BUILD_SCHEMA,
                "sha256": digest,
                "status": ADMISSION_STATUS,
            }
        )
    return descriptors


def _verify_descriptor(root: Path, value: object, *, label: str) -> tuple[Path, int]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} descriptor must be an object")
    relative = Path(_required_text(value.get("path"), label=f"{label} path"))
    if relative.is_absolute():
        raise ValueError(f"{label} descriptor path must be relative")
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError(f"{label} descriptor escapes the draft directory")
    expected_sha256 = _required_sha256(value.get("sha256"), label=f"{label} hash")
    if sha256_file(path) != expected_sha256:
        raise RuntimeError(f"{label} hash differs")
    expected_bytes = _required_nonnegative_int(
        value.get("bytes"), label=f"{label} bytes"
    )
    if path.stat().st_size != expected_bytes:
        raise RuntimeError(f"{label} byte count differs")
    records = _required_nonnegative_int(value.get("records"), label=f"{label} records")
    return path, records


def _verify_no_authority(value: object, *, label: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label} omitted its authority boundary")
    for field in REQUIRED_AUTHORITY_FIELDS:
        if value.get(field) != NO_AUTHORITY:
            raise ValueError(f"{label} unexpectedly authorizes {field}")


def _record_map(authority: Mapping[str, Any], *, lane: str) -> tuple[
    dict[str, dict[str, Any]],
    set[str],
    set[str],
    set[tuple[str, str]],
]:
    sources = authority.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"{lane} draft authority has no sources")
    records: dict[str, dict[str, Any]] = {}
    source_paths: set[str] = set()
    source_sha256s: set[str] = set()
    source_bindings: set[tuple[str, str]] = set()
    for source_index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise TypeError(f"{lane} source {source_index} must be an object")
        path = Path(_required_text(source.get("path"), label=f"{lane} source path"))
        if not path.is_absolute():
            raise ValueError(f"{lane} source path must be absolute")
        path = path.resolve(strict=True)
        path_key = str(path).replace("\\", "/").casefold()
        if path_key in source_paths:
            raise ValueError(f"{lane} draft authority repeats a source path")
        source_paths.add(path_key)
        expected_hash = _required_sha256(
            source.get("sha256"), label=f"{lane} source hash"
        )
        if sha256_file(path) != expected_hash:
            raise RuntimeError(f"{lane} source artifact hash differs")
        expected_bytes = _required_nonnegative_int(
            source.get("bytes"), label=f"{lane} source bytes"
        )
        source_bytes = path.read_bytes()
        if len(source_bytes) != expected_bytes:
            raise RuntimeError(f"{lane} source artifact byte count differs")
        source_sha256s.add(expected_hash)
        source_bindings.add((path_key, expected_hash))
        raw_records = source.get("records")
        if not isinstance(raw_records, list) or not raw_records:
            raise ValueError(f"{lane} draft source has no record spans")
        for raw_record in raw_records:
            if not isinstance(raw_record, dict):
                raise TypeError(f"{lane} source record must be an object")
            identity = _required_text(raw_record.get("id"), label=f"{lane} record id")
            if identity in records:
                raise ValueError(f"{lane} draft authority repeats a record identity")
            start = _required_nonnegative_int(
                raw_record.get("byte_start"), label=f"{lane} byte_start"
            )
            end = _required_nonnegative_int(
                raw_record.get("byte_end"), label=f"{lane} byte_end"
            )
            if end <= start or end > len(source_bytes):
                raise ValueError(f"{lane} source span is empty or out of bounds")
            excerpt = source_bytes[start:end]
            excerpt_hash = _required_sha256(
                raw_record.get("excerpt_sha256"), label=f"{lane} excerpt hash"
            )
            if sha256(excerpt).hexdigest() != excerpt_hash:
                raise RuntimeError(f"{lane} source excerpt hash differs")
            try:
                raw_text = excerpt.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"{lane} source span is not UTF-8") from exc
            transform = _required_text(
                raw_record.get("text_transform"), label=f"{lane} text transform"
            )
            text = transform_packet_free_text(raw_text, transform)
            content_hash = _required_sha256(
                raw_record.get("content_sha256"), label=f"{lane} content hash"
            )
            if sha256(text.encode("utf-8")).hexdigest() != content_hash:
                raise RuntimeError(f"{lane} transformed content hash differs")
            records[identity] = {
                "authority_record": dict(raw_record),
                "content_sha256": content_hash,
                "raw_excerpt": raw_text,
                "source_artifact_path": str(path),
                "source_artifact_sha256": expected_hash,
                "source_byte_end": end,
                "source_byte_start": start,
                "source_excerpt_sha256": excerpt_hash,
                "source_locator": _required_text(
                    raw_record.get("source_locator"), label=f"{lane} source locator"
                ),
                "text": text,
                "text_transform": transform,
            }
    return records, source_paths, source_sha256s, source_bindings


def _verify_draft_lane(
    *, authority_path: Path, source_path: Path, lane: str, expected_records: int
) -> dict[str, Any]:
    authority = _load_json(authority_path, label=f"{lane} draft authority")
    if authority.get("schema") != PACKET_FREE_AUTHORITY_SCHEMA:
        raise ValueError(f"{lane} draft authority schema changed")
    if authority.get("lane") != lane:
        raise ValueError(f"{lane} draft authority names another lane")
    if authority.get("review_status") != DRAFT_REVIEW_STATUS:
        raise ValueError(f"{lane} draft authority is not unreviewed")
    if authority.get("training_authorized", False) is not False:
        raise ValueError(f"{lane} draft unexpectedly authorizes training")
    _verify_no_authority(authority.get("authority"), label=f"{lane} draft")
    records, source_paths, source_sha256s, source_bindings = _record_map(
        authority, lane=lane
    )
    rows = _load_jsonl(source_path, label=f"{lane} draft rows")
    if len(rows) != expected_records or len(records) != expected_records:
        raise RuntimeError(f"{lane} draft descriptor record count differs")
    rows_by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        identity = _required_text(row.get("id"), label=f"{lane} row id")
        if identity in rows_by_id:
            raise ValueError(f"{lane} draft rows repeat an identity")
        bound = records.get(identity)
        if bound is None:
            raise ValueError(f"{lane} draft row is absent from its authority")
        if row.get("text") != bound["text"]:
            raise RuntimeError(f"{lane} draft row text differs from source bytes")
        if row.get("source_locator") != bound["source_locator"]:
            raise RuntimeError(f"{lane} draft row locator differs from authority")
        if row.get("content_sha256") != bound["content_sha256"]:
            raise RuntimeError(f"{lane} draft row content hash differs from authority")
        rows_by_id[identity] = row
    if set(rows_by_id) != set(records):
        raise ValueError(f"{lane} draft rows do not consume every authority record")
    return {
        "authority": authority,
        "records": records,
        "rows": rows_by_id,
        "source_paths": source_paths,
        "source_sha256s": source_sha256s,
        "source_bindings": source_bindings,
    }


def _verify_license_receipts(
    source_audit_path: Path,
    *,
    source_audit_sha256: str,
    expected_sources: Mapping[str, set[tuple[str, str]]],
) -> dict[str, object]:
    if sha256_file(source_audit_path) != source_audit_sha256:
        raise RuntimeError("source audit receipt hash differs")
    audit = _load_json(source_audit_path, label="source audit receipt")
    if audit.get("status") != "PINNED_CANDIDATE_SOURCES_NOT_ADMITTED":
        raise ValueError("source audit is not pinned and non-admitted")
    sources = audit.get("sources")
    if not isinstance(sources, dict):
        raise ValueError("source audit omitted its source registry")
    verified: dict[str, object] = {}
    for lane in ("ordinary", "retention"):
        matches = [
            value
            for value in sources.values()
            if isinstance(value, dict) and value.get("lane") == lane
        ]
        if len(matches) != 1:
            raise ValueError(f"source audit must contain exactly one {lane} source")
        source = matches[0]
        source_path = Path(
            _required_text(source.get("local_path"), label=f"{lane} source path")
        ).resolve(strict=True)
        source_path_key = str(source_path).replace("\\", "/").casefold()
        source_hash = _required_sha256(
            source.get("sha256"), label=f"{lane} source hash"
        )
        source_bytes = _required_nonnegative_int(
            source.get("bytes"), label=f"{lane} source bytes"
        )
        if (source_path_key, source_hash) not in expected_sources.get(lane, set()):
            raise RuntimeError(f"{lane} source audit does not match draft authority")
        if (
            sha256_file(source_path) != source_hash
            or source_path.stat().st_size != source_bytes
        ):
            raise RuntimeError(f"{lane} source audit artifact differs")
        license_name = _required_text(source.get("license"), label=f"{lane} license")
        license_files: list[dict[str, object]] = []
        raw_files: list[Mapping[str, Any]] = []
        if "license_path" in source:
            raw_files.append(
                {
                    "path": source.get("license_path"),
                    "bytes": source.get("license_bytes"),
                    "sha256": source.get("license_sha256"),
                }
            )
        raw_multi = source.get("license_files")
        if raw_multi is not None:
            if not isinstance(raw_multi, list):
                raise TypeError(f"{lane} license_files must be a list")
            if any(not isinstance(value, Mapping) for value in raw_multi):
                raise TypeError(f"{lane} license_files entries must be objects")
            raw_files.extend(raw_multi)
        if not raw_files:
            raise ValueError(f"{lane} source has no pinned license artifact")
        for raw in raw_files:
            path = Path(
                _required_text(raw.get("path"), label=f"{lane} license path")
            ).resolve(strict=True)
            expected_hash = _required_sha256(
                raw.get("sha256"), label=f"{lane} license hash"
            )
            expected_bytes = _required_nonnegative_int(
                raw.get("bytes"), label=f"{lane} license bytes"
            )
            if (
                sha256_file(path) != expected_hash
                or path.stat().st_size != expected_bytes
            ):
                raise RuntimeError(f"{lane} license artifact differs")
            license_files.append(
                {"bytes": expected_bytes, "path": str(path), "sha256": expected_hash}
            )
        verified[lane] = {"license": license_name, "license_files": license_files}
    return verified


def _load_decisions(
    path: Path,
    *,
    review_packet_sha256: str,
    review_rows: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    ledger = _load_json(path, label="review decision ledger")
    if ledger.get("schema") != REVIEW_DECISION_SCHEMA:
        raise ValueError("review decision schema changed")
    if ledger.get("review_packet_sha256") != review_packet_sha256:
        raise RuntimeError("review decision ledger names a stale review packet")
    if ledger.get("review_packet_records") != len(review_rows):
        raise RuntimeError("review decision ledger record count differs")
    reviewer = ledger.get("reviewer")
    if not isinstance(reviewer, dict):
        raise ValueError("review decision ledger omitted reviewer metadata")
    _required_text(reviewer.get("id"), label="reviewer id")
    _required_text(reviewer.get("role"), label="reviewer role")
    if reviewer.get("separation") != "DECLARED_SEPARATE_REVIEW_SESSIONS":
        raise ValueError("reviewer separation must declare separate review sessions")
    if reviewer.get("evidence_boundary") != "THREAD_IDS_DECLARED_NOT_AUTHENTICATED":
        raise ValueError("reviewer evidence boundary must disclose unauthenticated IDs")
    review_threads = [
        _required_text(reviewer.get(field), label=field.replace("_", " "))
        for field in ("ordinary_review_thread", "retention_review_thread")
    ]
    if len(set(review_threads)) != len(review_threads):
        raise ValueError("ordinary and retention review threads must differ")
    try:
        for thread_id in review_threads:
            UUID(thread_id)
    except ValueError as exc:
        raise ValueError("review thread IDs must be UUIDs") from exc
    raw_decisions = ledger.get("decisions")
    if not isinstance(raw_decisions, list) or not raw_decisions:
        raise ValueError("review decision ledger has no decisions")
    decisions: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(raw_decisions):
        if not isinstance(raw, dict):
            raise TypeError(f"review decision {index} must be an object")
        identity = _required_text(raw.get("id"), label="review decision id")
        if identity in decisions:
            raise ValueError("review decision ledger repeats an identity")
        row = review_rows.get(identity)
        if row is None:
            raise ValueError("review decision ledger contains an unknown identity")
        lane = _required_text(raw.get("lane"), label=f"{identity} lane")
        if lane != row.get("lane"):
            raise ValueError(f"{identity} review lane differs")
        content_hash = _required_sha256(
            raw.get("content_sha256"), label=f"{identity} content hash"
        )
        if content_hash != row.get("content_sha256"):
            raise RuntimeError(f"{identity} review content hash differs")
        decision = _required_text(raw.get("decision"), label=f"{identity} decision")
        if decision not in DECISIONS:
            raise ValueError(f"{identity} has unsupported review decision")
        raw_reasons = raw.get("reason_codes")
        if not isinstance(raw_reasons, list) or not raw_reasons:
            raise ValueError(f"{identity} has no review reason codes")
        reasons = [
            _required_text(value, label=f"{identity} reason") for value in raw_reasons
        ]
        if len(set(reasons)) != len(reasons) or any(
            reason not in ALLOWED_REASON_CODES for reason in reasons
        ):
            raise ValueError(f"{identity} has duplicate or unsupported review reason")
        reason_set = set(reasons)
        if decision == ADMIT and not ADMIT_REASON_CODES.issubset(reason_set):
            raise ValueError(f"{identity} admission lacks required positive reasons")
        if decision == ADMIT and reason_set - ADMIT_REASON_CODES:
            raise ValueError(f"{identity} admission includes rejection reasons")
        if decision == REJECT and not reason_set.issubset(REJECT_REASON_CODES):
            raise ValueError(f"{identity} rejection includes admission reasons")
        normalized_decision: dict[str, Any] = {
            "content_sha256": content_hash,
            "decision": decision,
            "id": identity,
            "lane": lane,
            "reason_codes": reasons,
        }
        if "review_note" in raw:
            normalized_decision["review_note"] = _required_text(
                raw.get("review_note"), label=f"{identity} review note"
            )
        decisions[identity] = normalized_decision
    missing = sorted(set(review_rows) - set(decisions))
    if missing:
        raise ValueError(f"review decision ledger is missing {len(missing)} identities")
    return ledger, decisions


def _reconcile_review_packet(
    review_packet_path: Path, lane_states: Mapping[str, Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = _load_jsonl(review_packet_path, label="review packet")
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        identity = _required_text(row.get("id"), label="review packet id")
        if identity in by_id:
            raise ValueError("review packet repeats an identity")
        lane = _required_text(row.get("lane"), label=f"{identity} lane")
        if lane not in lane_states:
            raise ValueError(f"{identity} names an unsupported lane")
        if (
            row.get("decision") != "PENDING"
            or row.get("review_status") != DRAFT_REVIEW_STATUS
        ):
            raise ValueError(f"{identity} review packet is not pending")
        if row.get("training_authorized") is not False:
            raise ValueError(
                f"{identity} review packet unexpectedly authorizes training"
            )
        bound = lane_states[lane]["records"].get(identity)
        if bound is None:
            raise ValueError(f"{identity} is absent from its draft authority")
        exact_fields = (
            "content_sha256",
            "raw_excerpt",
            "source_artifact_path",
            "source_artifact_sha256",
            "source_byte_end",
            "source_byte_start",
            "source_excerpt_sha256",
            "source_locator",
            "text",
            "text_transform",
        )
        for field in exact_fields:
            if row.get(field) != bound[field]:
                raise RuntimeError(
                    f"{identity} review packet {field} differs from source reconstruction"
                )
        by_id[identity] = row
    expected = set().union(*(set(state["records"]) for state in lane_states.values()))
    if set(by_id) != expected:
        raise ValueError("review packet does not cover every draft authority record")
    return rows, by_id


def _selected_authority(
    *,
    draft_authority: Mapping[str, Any],
    lane: str,
    admitted_ids: set[str],
    decision_ledger_sha256: str,
    review_packet_sha256: str,
    reviewer: Mapping[str, Any],
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    for raw_source in draft_authority["sources"]:
        source = dict(raw_source)
        source["records"] = [
            dict(record)
            for record in raw_source["records"]
            if record.get("id") in admitted_ids
        ]
        if source["records"]:
            sources.append(source)
    return {
        "admission_metadata": {
            "claim_boundary": "Source provenance admitted; training and every operational authority remain disabled.",
            "decision_ledger_sha256": decision_ledger_sha256,
            "review_packet_sha256": review_packet_sha256,
            "reviewer": dict(reviewer),
        },
        "authority": {field: NO_AUTHORITY for field in REQUIRED_AUTHORITY_FIELDS},
        "lane": lane,
        "review_status": PACKET_FREE_REVIEW_STATUS,
        "schema": PACKET_FREE_AUTHORITY_SCHEMA,
        "sources": sources,
        "training_authorized": False,
    }


def admit_packet_free_authority_drafts(
    *,
    draft_dir: str | Path,
    decision_ledger_path: str | Path,
    output_dir: str | Path,
    superseded_receipts: Sequence[str | Path] = (),
) -> dict[str, object]:
    """Compile reviewed draft rows into provenance-admitted authority files."""

    draft_root = Path(draft_dir).resolve(strict=True)
    decision_path = Path(decision_ledger_path).resolve(strict=True)
    output = Path(output_dir).resolve()
    pending = output.with_name(f"{output.name}.pending")
    if output.exists() or pending.exists():
        raise FileExistsError("admission output or pending directory already exists")
    supersedes = _superseded_receipt_descriptors(superseded_receipts)

    build_path = draft_root / "BUILD_RECEIPT.json"
    build = _load_json(build_path, label="draft build receipt")
    if build.get("schema") != DRAFT_BUILD_SCHEMA or build.get("status") != DRAFT_STATUS:
        raise ValueError("draft build receipt is not a completed non-admitted build")
    if (
        build.get("review_status") != DRAFT_REVIEW_STATUS
        or build.get("training_authorized") is not False
    ):
        raise ValueError("draft build receipt is not review-only")
    outputs = build.get("outputs")
    if not isinstance(outputs, dict):
        raise ValueError("draft build receipt omitted outputs")

    lane_states: dict[str, dict[str, Any]] = {}
    for lane, (authority_key, source_key) in _DRAFT_OUTPUT_KEYS.items():
        authority_path, authority_records = _verify_descriptor(
            draft_root, outputs.get(authority_key), label=authority_key
        )
        source_path, source_records = _verify_descriptor(
            draft_root, outputs.get(source_key), label=source_key
        )
        if authority_records != source_records:
            raise RuntimeError(f"{lane} draft authority/source record counts differ")
        lane_states[lane] = _verify_draft_lane(
            authority_path=authority_path,
            source_path=source_path,
            lane=lane,
            expected_records=source_records,
        )

    ordinary = lane_states["ordinary"]
    retention = lane_states["retention"]
    if ordinary["source_paths"] & retention["source_paths"]:
        raise ValueError("ordinary and retention reuse a source path")
    if ordinary["source_sha256s"] & retention["source_sha256s"]:
        raise ValueError("ordinary and retention reuse a source artifact")

    review_packet_path, review_packet_records = _verify_descriptor(
        draft_root, outputs.get("review_packet"), label="review_packet"
    )
    review_packet_sha256 = sha256_file(review_packet_path)
    review_rows, review_by_id = _reconcile_review_packet(
        review_packet_path, lane_states
    )
    if len(review_rows) != review_packet_records:
        raise RuntimeError("review packet descriptor record count differs")

    inputs = build.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("draft build receipt omitted inputs")
    source_audit_path = Path(
        _required_text(
            inputs.get("source_audit_receipt"), label="source audit receipt path"
        )
    ).resolve(strict=True)
    source_audit_sha256 = _required_sha256(
        inputs.get("source_audit_receipt_sha256"), label="source audit receipt hash"
    )
    licenses = _verify_license_receipts(
        source_audit_path,
        source_audit_sha256=source_audit_sha256,
        expected_sources={
            lane: set(state["source_bindings"]) for lane, state in lane_states.items()
        },
    )

    ledger, decisions = _load_decisions(
        decision_path,
        review_packet_sha256=review_packet_sha256,
        review_rows=review_by_id,
    )
    decision_ledger_sha256 = sha256_file(decision_path)
    admitted_by_lane: dict[str, list[str]] = {"ordinary": [], "retention": []}
    rejected_rows: list[dict[str, Any]] = []
    for row in review_rows:
        decision = decisions[row["id"]]
        if decision["decision"] == ADMIT:
            admitted_by_lane[row["lane"]].append(row["id"])
        else:
            rejected_rows.append(decision)
    for lane, identities in admitted_by_lane.items():
        if not identities:
            raise ValueError(f"review rejects every {lane} row")

    admitted_content = {
        lane: {
            str(lane_states[lane]["records"][identity]["content_sha256"])
            for identity in identities
        }
        for lane, identities in admitted_by_lane.items()
    }
    if admitted_content["ordinary"] & admitted_content["retention"]:
        raise ValueError(
            "admitted ordinary and retention rows reuse transformed content"
        )

    pending.mkdir(parents=True)
    try:
        shutil.copyfile(decision_path, pending / "REVIEW_DECISIONS.json")
        _write_jsonl(pending / "REJECTED_ROWS.jsonl", rejected_rows)
        output_descriptors: dict[str, object] = {
            "decision_ledger": _descriptor(
                pending / "REVIEW_DECISIONS.json", len(decisions)
            ),
            "rejected_rows": _descriptor(
                pending / "REJECTED_ROWS.jsonl", len(rejected_rows)
            ),
        }
        validation_receipts: dict[str, object] = {}
        for lane in ("ordinary", "retention"):
            admitted_ids = set(admitted_by_lane[lane])
            authority = _selected_authority(
                draft_authority=lane_states[lane]["authority"],
                lane=lane,
                admitted_ids=admitted_ids,
                decision_ledger_sha256=decision_ledger_sha256,
                review_packet_sha256=review_packet_sha256,
                reviewer=ledger["reviewer"],
            )
            authority_path = pending / f"{lane}.authority.admitted.json"
            source_path = pending / f"{lane}.source.admitted.jsonl"
            source_rows = [
                {
                    "content_sha256": lane_states[lane]["records"][identity][
                        "content_sha256"
                    ],
                    "id": identity,
                    "source_locator": lane_states[lane]["records"][identity][
                        "source_locator"
                    ],
                    "text": lane_states[lane]["records"][identity]["text"],
                }
                for identity in admitted_by_lane[lane]
            ]
            _write_json(authority_path, authority)
            _write_jsonl(source_path, source_rows)
            canonical, validation = validate_packet_free_rows(
                source_rows,
                authority_path=authority_path,
                lane=lane,
            )
            if len(canonical) != len(source_rows):
                raise RuntimeError(f"{lane} production validator count differs")
            validation = dict(validation)
            validation["authority_path"] = str((output / authority_path.name).resolve())
            validation_receipts[lane] = validation
            output_descriptors[f"{lane}_authority"] = _descriptor(
                authority_path, len(source_rows)
            )
            output_descriptors[f"{lane}_source"] = _descriptor(
                source_path, len(source_rows)
            )

        receipt: dict[str, object] = {
            "authority": {
                **_DISABLED_BUILD_AUTHORITY,
                "source_provenance": "ADMITTED",
            },
            "claim_boundary": (
                "Reviewed source provenance only. No training intake, optimization, execution, "
                "material evidence, promotion, unfreeze, or tool authority is granted."
            ),
            "counts": {
                "admitted": {
                    lane: len(values) for lane, values in admitted_by_lane.items()
                },
                "rejected": len(rejected_rows),
                "reviewed_total": len(decisions),
            },
            "inputs": {
                "decision_ledger": str(decision_path),
                "decision_ledger_sha256": decision_ledger_sha256,
                "draft_build_receipt": str(build_path),
                "draft_build_receipt_sha256": sha256_file(build_path),
                "review_packet": str(review_packet_path),
                "review_packet_sha256": review_packet_sha256,
                "source_audit_receipt": str(source_audit_path),
                "source_audit_receipt_sha256": source_audit_sha256,
            },
            "licenses": licenses,
            "outputs": output_descriptors,
            "production_validation": validation_receipts,
            "reviewer": ledger["reviewer"],
            "schema": ADMISSION_BUILD_SCHEMA,
            "status": ADMISSION_STATUS,
            "supersedes": supersedes,
            "training_authorized": False,
        }
        _write_json(pending / "BUILD_RECEIPT.json", receipt)
        os.replace(pending, output)
        return receipt
    except Exception:
        # Preserve the pending directory for forensic inspection.
        raise
