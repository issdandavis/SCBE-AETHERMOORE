"""Build review-only packet-free authorities from pinned candidate evidence.

The builder translates audited half-open line spans into exact UTF-8 byte
offsets and preserves separate hashes for the raw excerpt and transformed
prompt.  Its outputs deliberately remain ``NOT_REVIEWED`` and grant no
training, optimization, promotion, unfreeze, execution, or tool authority.
"""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .prime_token_packet_free_authority import (
    LINE_STRIP_JOIN_TRANSFORM,
    NO_AUTHORITY,
    PACKET_FREE_AUTHORITY_SCHEMA,
    REQUIRED_AUTHORITY_FIELDS,
    transform_packet_free_text,
    validate_packet_free_rows,
)
from .prime_token_training import sha256_file

DRAFT_BUILD_SCHEMA = "scbe.prime-token-packet-free-authority-draft-build.v1"
DRAFT_REVIEW_STATUS = "NOT_REVIEWED"
DRAFT_STATUS = "BUILT_NOT_REVIEWED_NOT_AUTHORIZED"
CANDIDATE_MANIFEST_SCHEMA = "clay.full-system-action-dataset-candidate.v1"
CANDIDATE_AUTHORITY_SCHEMA = "clay.full-system-action-source-authorities-candidate.v1"
CANDIDATE_BUILD_SCHEMA = "clay.full-system-action-candidate-build-receipt.v1"
SOURCE_AUDIT_SCHEMA = "clay.frozen-action-math-source-audit.v1"
TEXT_AUDIT_SCHEMA = "clay.frozen-action-text-source-span-audit.v1"
LANES = ("ordinary", "retention")


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_json(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _required_text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def _required_content(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value


def _required_sha256(value: object, *, label: str) -> str:
    digest = _required_text(value, label=label).casefold()
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError(f"{label} must be lowercase SHA-256")
    return digest


def _required_int(value: object, *, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return value


def _required_mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be an object")
    return value


def _required_sequence(value: object, *, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{label} must be an array")
    return value


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{label} must contain one JSON object")
    return value


def _load_jsonl(path: Path, *, label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError(f"{label} line {line_number} must be an object")
        rows.append(value)
    if not rows:
        raise ValueError(f"{label} is empty")
    return rows


def _assert_no_authority(value: Mapping[str, Any], *, label: str) -> None:
    for field in (
        "dataset_admission",
        "execution",
        "launch",
        "material_evidence",
        "optimization",
        "partial_unfreeze",
        "promotion",
        "scoring",
        "serving",
        "tool_dispatch",
        "training_intake",
    ):
        if field not in value:
            continue
        expected = "DISABLED" if field == "tool_dispatch" else "NONE"
        if value[field] not in {expected, NO_AUTHORITY}:
            raise ValueError(f"{label} unexpectedly authorizes {field}")


def _verify_file(
    path: Path,
    *,
    expected_sha256: object,
    expected_bytes: object,
    label: str,
) -> None:
    digest = _required_sha256(expected_sha256, label=f"{label} hash")
    byte_count = _required_int(expected_bytes, label=f"{label} bytes")
    if sha256_file(path) != digest:
        raise RuntimeError(f"{label} hash differs")
    if path.stat().st_size != byte_count:
        raise RuntimeError(f"{label} byte count differs")


def _descriptor_path(
    root: Path,
    descriptor: object,
    *,
    label: str,
) -> tuple[Path, int]:
    value = _required_mapping(descriptor, label=f"{label} descriptor")
    relative = Path(_required_text(value.get("path"), label=f"{label} path"))
    if relative.is_absolute():
        raise ValueError(f"{label} descriptor path must be relative")
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError(f"{label} descriptor escapes its bundle")
    _verify_file(
        path,
        expected_sha256=value.get("sha256"),
        expected_bytes=value.get("bytes"),
        label=label,
    )
    return path, _required_int(value.get("records"), label=f"{label} records")


def _unique_by_id(
    rows: Sequence[Mapping[str, Any]],
    *,
    field: str,
    label: str,
) -> dict[str, Mapping[str, Any]]:
    output: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        identity = _required_text(row.get(field), label=f"{label} {field}")
        if identity in output:
            raise ValueError(f"{label} repeats {field}: {identity}")
        output[identity] = row
    return output


def _source_lines(source_bytes: bytes, *, label: str) -> tuple[str, list[int]]:
    try:
        text = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not UTF-8") from exc
    encoded_lines = [line.encode("utf-8") for line in text.splitlines(keepends=True)]
    if b"".join(encoded_lines) != source_bytes:
        raise RuntimeError(f"{label} line reconstruction differs from artifact bytes")
    offsets = [0]
    for line in encoded_lines:
        offsets.append(offsets[-1] + len(line))
    return text, offsets


def _line_span_to_bytes(
    source_bytes: bytes,
    span: Mapping[str, Any],
    *,
    label: str,
) -> tuple[int, int, bytes]:
    if span.get("unit") != "line":
        raise ValueError(f"{label} must use line spans")
    start = _required_int(span.get("start"), label=f"{label} line start")
    end = _required_int(span.get("end"), label=f"{label} line end", minimum=1)
    _text, offsets = _source_lines(source_bytes, label=label)
    line_count = len(offsets) - 1
    if end <= start or end > line_count:
        raise ValueError(f"{label} line span is empty or out of bounds")
    byte_start = offsets[start]
    byte_end = offsets[end]
    return byte_start, byte_end, source_bytes[byte_start:byte_end]


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(_canonical_json(dict(row)) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def _file_descriptor(path: Path, *, records: int | None = None) -> dict[str, object]:
    descriptor: dict[str, object] = {
        "bytes": path.stat().st_size,
        "path": path.name,
        "sha256": sha256_file(path),
    }
    if records is not None:
        descriptor["records"] = records
    return descriptor


def _candidate_inputs(
    candidate_root: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, list[dict[str, Any]]],
    list[dict[str, Any]],
    dict[str, Path],
]:
    manifest_path = (candidate_root / "CANDIDATE_MANIFEST.json").resolve(strict=True)
    build_path = (candidate_root / "BUILD_RECEIPT.json").resolve(strict=True)
    manifest = _load_json(manifest_path, label="candidate manifest")
    build = _load_json(build_path, label="candidate build receipt")
    if manifest.get("schema") != CANDIDATE_MANIFEST_SCHEMA:
        raise ValueError("candidate manifest schema changed")
    if build.get("schema") != CANDIDATE_BUILD_SCHEMA:
        raise ValueError("candidate build receipt schema changed")
    if manifest.get("review_status") != DRAFT_REVIEW_STATUS:
        raise ValueError("candidate manifest is not explicitly unreviewed")
    if (
        manifest.get("training_authorized") is not False
        or manifest.get("material_evidence_authorized") is not False
        or manifest.get("accepted_by_campaign_loader") is not False
    ):
        raise ValueError("candidate manifest unexpectedly grants authority")
    if build.get("status") != "COMPLETE_NOT_ADMITTED":
        raise ValueError("candidate build receipt is not non-admitted")
    _assert_no_authority(
        _required_mapping(build.get("authority"), label="candidate build authority"),
        label="candidate build",
    )
    files = _required_mapping(manifest.get("files"), label="candidate files")
    build_outputs = _required_mapping(build.get("outputs"), label="candidate outputs")
    lane_rows: dict[str, list[dict[str, Any]]] = {}
    paths: dict[str, Path] = {
        "manifest": manifest_path,
        "build_receipt": build_path,
    }
    for lane in LANES:
        path, records = _descriptor_path(
            candidate_root, files.get(lane), label=f"candidate {lane}"
        )
        if build_outputs.get(lane) != files.get(lane):
            raise RuntimeError(f"candidate {lane} descriptors differ")
        rows = _load_jsonl(path, label=f"candidate {lane}")
        if len(rows) != records:
            raise RuntimeError(f"candidate {lane} record count differs")
        lane_rows[lane] = rows
        paths[lane] = path
    authority_path, authority_records = _descriptor_path(
        candidate_root,
        manifest.get("source_authorities"),
        label="candidate source authorities",
    )
    if build_outputs.get("source_authorities") != manifest.get("source_authorities"):
        raise RuntimeError("candidate source-authority descriptors differ")
    authority_document = _load_json(authority_path, label="candidate authorities")
    if authority_document.get("schema") != CANDIDATE_AUTHORITY_SCHEMA:
        raise ValueError("candidate source-authority schema changed")
    if (
        authority_document.get("review_status") != DRAFT_REVIEW_STATUS
        or authority_document.get("training_authorized") is not False
    ):
        raise ValueError("candidate source authorities unexpectedly grant authority")
    authorities = [
        dict(_required_mapping(value, label="candidate source-authority record"))
        for value in _required_sequence(
            authority_document.get("authorities"), label="candidate authorities"
        )
    ]
    if len(authorities) != authority_records:
        raise RuntimeError("candidate source-authority record count differs")
    paths["source_authorities"] = authority_path
    return manifest, build, lane_rows, authorities, paths


def _source_audit_inputs(
    source_audit_path: Path,
    *,
    candidate_build: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], Path]:
    source_audit = _load_json(source_audit_path, label="source audit")
    if source_audit.get("schema") != SOURCE_AUDIT_SCHEMA:
        raise ValueError("source audit schema changed")
    if source_audit.get("status") != "PINNED_CANDIDATE_SOURCES_NOT_ADMITTED":
        raise ValueError("source audit is not pinned and non-admitted")
    _assert_no_authority(
        _required_mapping(
            source_audit.get("authority"), label="source audit authority"
        ),
        label="source audit",
    )
    inputs = _required_mapping(candidate_build.get("inputs"), label="build inputs")
    if sha256_file(source_audit_path) != _required_sha256(
        inputs.get("source_audit_receipt_sha256"), label="source audit input hash"
    ):
        raise RuntimeError("candidate build names another source audit")
    text_descriptor = _required_mapping(
        source_audit.get("text_span_audit"), label="text-span audit descriptor"
    )
    if (
        text_descriptor.get("independent_reconstruction")
        != "PASS_INDEPENDENT_RECONSTRUCTION"
    ):
        raise ValueError("text-span audit lacks independent reconstruction")
    ledger_path = Path(
        _required_text(
            text_descriptor.get("row_ledger_path"), label="text audit ledger path"
        )
    ).resolve(strict=True)
    _verify_file(
        ledger_path,
        expected_sha256=text_descriptor.get("row_ledger_sha256"),
        expected_bytes=text_descriptor.get("row_ledger_bytes"),
        label="text audit ledger",
    )
    if sha256_file(ledger_path) != _required_sha256(
        inputs.get("text_audit_ledger_sha256"), label="candidate text-ledger hash"
    ):
        raise RuntimeError("candidate build names another text audit ledger")
    ledger = _load_jsonl(ledger_path, label="text audit ledger")
    expected_rows = _required_int(
        text_descriptor.get("row_ledger_rows"), label="text audit ledger rows"
    )
    if len(ledger) != expected_rows:
        raise RuntimeError("text audit ledger row count differs")
    return source_audit, ledger, ledger_path


def _reconstruct_lane(
    *,
    lane: str,
    candidate_rows: Sequence[Mapping[str, Any]],
    ledger_by_id: Mapping[str, Mapping[str, Any]],
    authority_by_id: Mapping[str, Mapping[str, Any]],
    source_audit: Mapping[str, Any],
) -> tuple[list[dict[str, object]], dict[str, object], list[dict[str, object]]]:
    output_rows: list[dict[str, object]] = []
    review_rows: list[dict[str, object]] = []
    authority_records: list[dict[str, object]] = []
    artifact_path: Path | None = None
    artifact_sha256: str | None = None
    artifact_bytes: int | None = None
    seen_source_ids: set[str] = set()
    seen_record_ids: set[str] = set()
    seen_locators: set[str] = set()

    source_metadata = _required_mapping(
        source_audit.get("sources"), label="source-audit sources"
    )
    for candidate in candidate_rows:
        if candidate.get("split") != lane:
            raise ValueError(f"candidate row names another lane: {lane}")
        if (
            candidate.get("review_status") != DRAFT_REVIEW_STATUS
            or candidate.get("training_eligible") is not False
        ):
            raise ValueError(f"candidate {lane} row unexpectedly grants authority")
        source_id = _required_text(
            candidate.get("source_id"), label=f"candidate {lane} source id"
        )
        record_id = _required_text(
            candidate.get("id"), label=f"candidate {lane} record id"
        )
        if source_id in seen_source_ids or record_id in seen_record_ids:
            raise ValueError(f"candidate {lane} repeats an identity")
        seen_source_ids.add(source_id)
        seen_record_ids.add(record_id)
        ledger = ledger_by_id.get(source_id)
        authority = authority_by_id.get(source_id)
        if ledger is None or authority is None:
            raise ValueError(f"candidate {lane} row lacks source coverage")
        if ledger.get("lane") != lane or authority.get("lane") != lane:
            raise ValueError(f"candidate {lane} source coverage names another lane")
        if (
            ledger.get("review_status") != DRAFT_REVIEW_STATUS
            or ledger.get("training_eligible") is not False
        ):
            raise ValueError(f"text-ledger {lane} row unexpectedly grants authority")

        source_name = _required_text(
            ledger.get("source"), label=f"text-ledger {lane} source"
        )
        metadata = _required_mapping(
            source_metadata.get(source_name), label=f"source metadata {source_name}"
        )
        if metadata.get("lane") != lane:
            raise ValueError(f"source metadata names another lane: {source_name}")
        current_path = Path(
            _required_text(
                metadata.get("local_path"), label=f"{source_name} local path"
            )
        ).resolve(strict=True)
        current_sha256 = _required_sha256(
            metadata.get("sha256"), label=f"{source_name} artifact hash"
        )
        current_bytes = _required_int(
            metadata.get("bytes"), label=f"{source_name} artifact bytes"
        )
        _verify_file(
            current_path,
            expected_sha256=current_sha256,
            expected_bytes=current_bytes,
            label=f"{source_name} artifact",
        )
        if artifact_path is None:
            artifact_path = current_path
            artifact_sha256 = current_sha256
            artifact_bytes = current_bytes
        elif (
            artifact_path != current_path
            or artifact_sha256 != current_sha256
            or artifact_bytes != current_bytes
        ):
            raise ValueError(f"{lane} draft unexpectedly spans multiple artifacts")

        candidate_authority = dict(authority)
        receipt = _required_sha256(
            candidate_authority.pop("receipt_sha256", None),
            label=f"candidate {lane} authority receipt",
        )
        if _sha256_json(candidate_authority) != receipt:
            raise RuntimeError(f"candidate {lane} authority receipt differs")
        if (
            authority.get("artifact_sha256") != current_sha256
            or authority.get("artifact_bytes") != current_bytes
            or authority.get("source_family") != metadata.get("source_family")
            or authority.get("span") != ledger.get("span")
        ):
            raise RuntimeError(f"candidate {lane} authority differs from source audit")

        span = _required_mapping(ledger.get("span"), label=f"{lane} line span")
        byte_start, byte_end, excerpt_bytes = _line_span_to_bytes(
            current_path.read_bytes(), span, label=f"{lane} source span"
        )
        excerpt_sha256 = _required_sha256(
            ledger.get("excerpt_sha256"), label=f"{lane} excerpt hash"
        )
        if sha256(excerpt_bytes).hexdigest() != excerpt_sha256:
            raise RuntimeError(f"{lane} exact excerpt hash differs")
        if (
            candidate.get("source_sha256") != excerpt_sha256
            or authority.get("excerpt_sha256") != excerpt_sha256
        ):
            raise RuntimeError(f"{lane} candidate excerpt binding differs")
        excerpt = excerpt_bytes.decode("utf-8")
        prompt = transform_packet_free_text(excerpt, LINE_STRIP_JOIN_TRANSFORM)
        expected_prompt = _required_content(
            ledger.get("prompt"), label=f"{lane} audited prompt"
        )
        candidate_prompt = _required_content(
            candidate.get("input"), label=f"candidate {lane} prompt"
        )
        if prompt != expected_prompt or prompt != candidate_prompt:
            raise RuntimeError(f"{lane} transformed prompt differs")
        content_sha256 = _required_sha256(
            ledger.get("prompt_sha256"), label=f"{lane} prompt hash"
        )
        if sha256(prompt.encode("utf-8")).hexdigest() != content_sha256:
            raise RuntimeError(f"{lane} transformed prompt hash differs")
        if _required_int(
            ledger.get("prompt_bytes"), label=f"{lane} prompt bytes"
        ) != len(prompt.encode("utf-8")):
            raise RuntimeError(f"{lane} transformed prompt byte count differs")
        locator = _required_text(
            authority.get("locator"), label=f"candidate {lane} source locator"
        )
        if locator.casefold() in seen_locators:
            raise ValueError(f"candidate {lane} repeats a source locator")
        seen_locators.add(locator.casefold())

        output_rows.append(
            {
                "content_sha256": content_sha256,
                "id": record_id,
                "source_locator": locator,
                "text": prompt,
            }
        )
        authority_records.append(
            {
                "byte_end": byte_end,
                "byte_start": byte_start,
                "content_sha256": content_sha256,
                "excerpt_sha256": excerpt_sha256,
                "id": record_id,
                "source_locator": locator,
                "text_transform": LINE_STRIP_JOIN_TRANSFORM,
            }
        )
        review_rows.append(
            {
                "action_terms": list(ledger.get("action_terms", [])),
                "content_sha256": content_sha256,
                "decision": "PENDING",
                "id": record_id,
                "lane": lane,
                "raw_excerpt": excerpt,
                "review_status": DRAFT_REVIEW_STATUS,
                "source_artifact_path": str(current_path),
                "source_artifact_sha256": current_sha256,
                "source_byte_end": byte_end,
                "source_byte_start": byte_start,
                "source_excerpt_sha256": excerpt_sha256,
                "source_family_label": metadata.get("source_family"),
                "source_id": source_id,
                "source_line_span": dict(span),
                "source_locator": locator,
                "text": prompt,
                "text_transform": LINE_STRIP_JOIN_TRANSFORM,
                "training_authorized": False,
            }
        )

    if set(ledger_by_id) != seen_source_ids:
        raise ValueError(f"{lane} text-ledger coverage differs from candidate rows")
    if set(authority_by_id) != seen_source_ids:
        raise ValueError(
            f"{lane} source-authority coverage differs from candidate rows"
        )
    if artifact_path is None or artifact_sha256 is None or artifact_bytes is None:
        raise ValueError(f"{lane} produced no draft rows")
    authority_document: dict[str, object] = {
        "authority": {field: NO_AUTHORITY for field in REQUIRED_AUTHORITY_FIELDS},
        "draft_metadata": {
            "candidate_source_family_label": review_rows[0]["source_family_label"],
            "claim_boundary": "Provenance draft only; review and training remain unauthorized.",
            "text_transform": LINE_STRIP_JOIN_TRANSFORM,
        },
        "lane": lane,
        "review_status": DRAFT_REVIEW_STATUS,
        "schema": PACKET_FREE_AUTHORITY_SCHEMA,
        "sources": [
            {
                "bytes": artifact_bytes,
                "path": str(artifact_path),
                "records": authority_records,
                "sha256": artifact_sha256,
            }
        ],
    }
    return output_rows, authority_document, review_rows


def build_packet_free_authority_drafts(
    *,
    candidate_root: str | Path,
    source_audit_receipt_path: str | Path,
    output_dir: str | Path,
) -> dict[str, object]:
    """Build immutable, review-only ordinary/retention authority drafts."""

    candidate = Path(candidate_root).resolve(strict=True)
    source_audit_path = Path(source_audit_receipt_path).resolve(strict=True)
    output = Path(output_dir).resolve()
    pending = output.with_name(f"{output.name}.pending")
    if output.exists():
        raise FileExistsError(f"draft output already exists: {output}")
    if pending.exists():
        raise FileExistsError(f"draft pending output already exists: {pending}")

    manifest, candidate_build, lane_rows, authority_rows, candidate_paths = (
        _candidate_inputs(candidate)
    )
    source_audit, text_rows, text_ledger_path = _source_audit_inputs(
        source_audit_path, candidate_build=candidate_build
    )
    text_by_lane = {
        lane: _unique_by_id(
            [row for row in text_rows if row.get("lane") == lane],
            field="source_id",
            label=f"text-ledger {lane}",
        )
        for lane in LANES
    }
    authority_by_lane = {
        lane: _unique_by_id(
            [row for row in authority_rows if row.get("lane") == lane],
            field="source_id",
            label=f"candidate authority {lane}",
        )
        for lane in LANES
    }
    reconstructed = {
        lane: _reconstruct_lane(
            lane=lane,
            candidate_rows=lane_rows[lane],
            ledger_by_id=text_by_lane[lane],
            authority_by_id=authority_by_lane[lane],
            source_audit=source_audit,
        )
        for lane in LANES
    }
    ordinary_rows, ordinary_authority, ordinary_review = reconstructed["ordinary"]
    retention_rows, retention_authority, retention_review = reconstructed["retention"]
    ordinary_source = ordinary_authority["sources"][0]
    retention_source = retention_authority["sources"][0]
    if ordinary_source["path"] == retention_source["path"]:
        raise ValueError("ordinary and retention drafts reuse a source path")
    if ordinary_source["sha256"] == retention_source["sha256"]:
        raise ValueError("ordinary and retention drafts reuse a source artifact")
    ordinary_hashes = {str(row["content_sha256"]) for row in ordinary_rows}
    retention_hashes = {str(row["content_sha256"]) for row in retention_rows}
    if ordinary_hashes & retention_hashes:
        raise ValueError("ordinary and retention drafts reuse transformed content")

    pending.mkdir(parents=True)
    outputs: dict[str, dict[str, object]] = {}
    try:
        review_rows = sorted(
            ordinary_review + retention_review,
            key=lambda row: (str(row["lane"]), str(row["id"])),
        )
        for lane, rows, authority in (
            ("ordinary", ordinary_rows, ordinary_authority),
            ("retention", retention_rows, retention_authority),
        ):
            source_path = pending / f"{lane}.source.draft.jsonl"
            authority_path = pending / f"{lane}.authority.draft.json"
            _write_jsonl(source_path, rows)
            _write_json(authority_path, authority)
            outputs[f"{lane}_source"] = _file_descriptor(source_path, records=len(rows))
            outputs[f"{lane}_authority"] = _file_descriptor(
                authority_path, records=len(rows)
            )
            try:
                validate_packet_free_rows(
                    rows, authority_path=authority_path, lane=lane
                )
            except ValueError as exc:
                if "not admitted" not in str(exc):
                    raise
            else:
                raise RuntimeError(f"{lane} draft was unexpectedly admitted")
        review_path = pending / "REVIEW_PACKET.jsonl"
        _write_jsonl(review_path, review_rows)
        outputs["review_packet"] = _file_descriptor(
            review_path, records=len(review_rows)
        )
        receipt: dict[str, object] = {
            "authority": {
                "dataset_admission": "NONE",
                "execution": "NONE",
                "material_evidence": "NONE",
                "optimization": "NONE",
                "partial_unfreeze": "NONE",
                "promotion": "NONE",
                "tool_dispatch": "DISABLED",
                "training_intake": "NONE",
            },
            "claim_boundary": (
                "Exact provenance draft only. No row is reviewed, admitted, "
                "training-authorized, scored, promoted, unfrozen, or executable."
            ),
            "counts": {
                "ordinary": len(ordinary_rows),
                "retention": len(retention_rows),
                "total": len(review_rows),
            },
            "draft_runtime_rejection_verified": True,
            "inputs": {
                "candidate_build_receipt": str(candidate_paths["build_receipt"]),
                "candidate_build_receipt_sha256": sha256_file(
                    candidate_paths["build_receipt"]
                ),
                "candidate_manifest": str(candidate_paths["manifest"]),
                "candidate_manifest_sha256": sha256_file(candidate_paths["manifest"]),
                "candidate_source_authorities": str(
                    candidate_paths["source_authorities"]
                ),
                "candidate_source_authorities_sha256": sha256_file(
                    candidate_paths["source_authorities"]
                ),
                "source_audit_receipt": str(source_audit_path),
                "source_audit_receipt_sha256": sha256_file(source_audit_path),
                "text_audit_ledger": str(text_ledger_path),
                "text_audit_ledger_sha256": sha256_file(text_ledger_path),
            },
            "outputs": outputs,
            "review_status": DRAFT_REVIEW_STATUS,
            "schema": DRAFT_BUILD_SCHEMA,
            "source_artifact_disjoint": True,
            "status": DRAFT_STATUS,
            "training_authorized": False,
            "transformed_content_disjoint": True,
        }
        receipt_path = pending / "BUILD_RECEIPT.json"
        _write_json(receipt_path, receipt)
        os.replace(pending, output)
    except Exception:
        raise
    return receipt
