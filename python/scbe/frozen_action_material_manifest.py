"""Compile a provenance-bound, non-launchable four-lane action-data stage.

The compiler joins the existing frozen-action candidate bundle to independently
admitted packet-free ordinary and retention sources.  It deliberately emits a
staging manifest whose schema is rejected by the training campaign.  A later
action-mapping review must create a new manifest before any training intake.
"""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
from typing import Any, Mapping, Sequence

from python.scbe.prime_token_packet_free_admission import (
    ADMISSION_BUILD_SCHEMA,
    ADMISSION_STATUS,
)
from python.scbe.prime_token_packet_free_authority import (
    NO_AUTHORITY,
    PACKET_FREE_AUTHORITY_SCHEMA,
    REQUIRED_AUTHORITY_FIELDS,
    validate_packet_free_rows,
)
from python.scbe.prime_token_training import sha256_file

CANDIDATE_MANIFEST_SCHEMA = "clay.full-system-action-dataset-candidate.v1"
CANDIDATE_AUTHORITY_SCHEMA = "clay.full-system-action-source-authorities-candidate.v1"
CAMPAIGN_MANIFEST_SCHEMA = "clay.full-system-action-dataset.v1"
CAMPAIGN_AUTHORITY_SCHEMA = "clay.full-system-action-source-authorities.v1"
STAGING_MANIFEST_SCHEMA = "clay.full-system-action-material-manifest-staged.v1"
STAGING_BUILD_SCHEMA = "clay.full-system-action-material-manifest-build.v1"
STAGING_STATUS = "PROVENANCE_BOUND_ACTION_MAPPING_REVIEW_REQUIRED"
LANES = ("train", "holdout", "ordinary", "retention")
CONTROL_LANES = ("ordinary", "retention")
ACTION_LANES = ("train", "holdout")
DISABLED_BUILD_AUTHORITY = {
    "dataset_admission": "NONE",
    "execution": "NONE",
    "material_evidence": "NONE",
    "optimization": "NONE",
    "partial_unfreeze": "NONE",
    "promotion": "NONE",
    "tool_dispatch": "DISABLED",
    "training_intake": "NONE",
}


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
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _required_sha256(value: object, *, label: str) -> str:
    digest = _required_text(value, label=label)
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError(f"{label} must be lowercase SHA-256")
    return digest


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a JSON object")
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
            raise TypeError(f"{label}:{line_number} must be a JSON object")
        rows.append(value)
    return rows


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(_canonical_json(dict(row)) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def _descriptor(path: Path, records: int) -> dict[str, object]:
    return {
        "bytes": path.stat().st_size,
        "path": path.name,
        "records": records,
        "sha256": sha256_file(path),
    }


def _verify_descriptor(
    root: Path, raw: object, *, label: str
) -> tuple[Path, int, dict[str, Any]]:
    if not isinstance(raw, dict):
        raise TypeError(f"{label} descriptor must be an object")
    required = {"bytes", "path", "records", "sha256"}
    if not required <= raw.keys():
        raise ValueError(f"{label} descriptor is incomplete")
    relative = Path(_required_text(raw["path"], label=f"{label} path"))
    if relative.is_absolute():
        path = relative.resolve(strict=True)
    else:
        path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError(f"{label} descriptor escapes its root")
    expected_bytes = int(raw["bytes"])
    expected_records = int(raw["records"])
    expected_sha256 = _required_sha256(raw["sha256"], label=f"{label} sha256")
    if expected_bytes < 0 or expected_records < 0:
        raise ValueError(f"{label} descriptor counts must be non-negative")
    if path.stat().st_size != expected_bytes:
        raise RuntimeError(f"{label} byte count differs")
    if sha256_file(path) != expected_sha256:
        raise RuntimeError(f"{label} hash differs")
    return path, expected_records, dict(raw)


def _verify_authority_receipt(raw: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "artifact_bytes",
        "artifact_sha256",
        "excerpt_sha256",
        "lane",
        "locator",
        "receipt_sha256",
        "source_family",
        "source_id",
        "source_kind",
        "span",
    }
    if not required <= raw.keys():
        raise ValueError("candidate source authority is incomplete")
    authority = dict(raw)
    receipt = _required_sha256(
        authority.pop("receipt_sha256"), label="source authority receipt"
    )
    if _sha256_json(authority) != receipt:
        raise RuntimeError("candidate source authority receipt does not replay")
    authority["receipt_sha256"] = receipt
    if authority["lane"] not in LANES:
        raise ValueError("candidate source authority names an unknown lane")
    _required_text(authority["source_id"], label="source authority id")
    _required_text(authority["source_family"], label="source authority family")
    _required_text(authority["locator"], label="source authority locator")
    _required_sha256(authority["artifact_sha256"], label="source artifact sha256")
    _required_sha256(authority["excerpt_sha256"], label="source excerpt sha256")
    if int(authority["artifact_bytes"]) <= 0:
        raise ValueError("source artifact bytes must be positive")
    span = authority["span"]
    if not isinstance(span, dict) or not {"unit", "start", "end"} <= span.keys():
        raise ValueError("source authority span is incomplete")
    if int(span["start"]) < 0 or int(span["end"]) <= int(span["start"]):
        raise ValueError("source authority span is not increasing")
    return authority


def _verify_candidate_row(raw: Mapping[str, Any], *, lane: str) -> dict[str, Any]:
    required = {
        "id",
        "input",
        "review_status",
        "source_id",
        "source_kind",
        "source_sha256",
        "split",
        "training_eligible",
    }
    if not required <= raw.keys():
        raise ValueError(f"{lane} candidate row is incomplete")
    row = dict(raw)
    if row["split"] != lane:
        raise ValueError(f"{lane} candidate row has the wrong split")
    if row["review_status"] != "NOT_REVIEWED":
        raise ValueError(f"{lane} candidate row is unexpectedly reviewed")
    if row["training_eligible"] is not False:
        raise ValueError(f"{lane} candidate row unexpectedly permits training")
    _required_text(row["id"], label=f"{lane} candidate id")
    _required_text(row["input"], label=f"{lane} candidate input")
    _required_text(row["source_id"], label=f"{lane} candidate source id")
    _required_sha256(row["source_sha256"], label=f"{lane} candidate source hash")
    if lane in ACTION_LANES:
        target = row.get("target")
        if not isinstance(target, dict):
            raise ValueError(f"{lane} candidate target is missing")
        required_target = {
            "action_receipt_sha256",
            "canonical",
            "family_token_id",
            "method_token_id",
            "payload",
        }
        if not required_target <= target.keys():
            raise ValueError(f"{lane} candidate target is incomplete")
        _required_sha256(
            target["action_receipt_sha256"], label=f"{lane} action receipt"
        )
    elif "target" in row:
        raise ValueError(f"{lane} control row must not carry an action target")
    return row


def _validate_four_lane_state(
    rows: Mapping[str, Sequence[Mapping[str, Any]]],
    authorities: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    authority_by_id: dict[str, Mapping[str, Any]] = {}
    families: dict[str, set[str]] = {lane: set() for lane in LANES}
    for authority in authorities:
        source_id = str(authority["source_id"])
        if source_id in authority_by_id:
            raise ValueError("source authority ID is duplicated")
        authority_by_id[source_id] = authority
        families[str(authority["lane"])].add(str(authority["source_family"]))

    record_ids: set[str] = set()
    source_ids: dict[str, set[str]] = {lane: set() for lane in LANES}
    prompts: dict[str, set[str]] = {lane: set() for lane in LANES}
    for lane in LANES:
        if not rows.get(lane):
            raise ValueError(f"{lane} lane is empty")
        for row in rows[lane]:
            identity = str(row["id"])
            source_id = str(row["source_id"])
            if identity in record_ids:
                raise ValueError("record ID crosses dataset lanes")
            record_ids.add(identity)
            if source_id in source_ids[lane]:
                raise ValueError(f"{lane} source ID is reused")
            source_ids[lane].add(source_id)
            prompts[lane].add(str(row["input"]))
            authority = authority_by_id.get(source_id)
            if authority is None:
                raise ValueError("dataset row has no source authority")
            if authority["lane"] != lane:
                raise ValueError("source authority lane differs from dataset row")
            if authority["source_kind"] != row["source_kind"]:
                raise ValueError("source authority kind differs from dataset row")
            if authority["excerpt_sha256"] != row["source_sha256"]:
                raise ValueError("source authority excerpt differs from dataset row")

    expected_source_ids = set().union(*source_ids.values())
    if set(authority_by_id) != expected_source_ids:
        raise ValueError("source-authority ledger has missing or unused entries")
    for index, left in enumerate(LANES):
        for right in LANES[index + 1 :]:
            if source_ids[left] & source_ids[right]:
                raise ValueError(f"source IDs overlap: {left}/{right}")
            if prompts[left] & prompts[right]:
                raise ValueError(f"exact prompts overlap: {left}/{right}")
            if families[left] & families[right]:
                raise ValueError(f"source families overlap: {left}/{right}")
    return {
        "exact_prompt_disjoint": True,
        "record_count": sum(len(rows[lane]) for lane in LANES),
        "source_family_disjoint": True,
        "source_families": {lane: sorted(families[lane]) for lane in LANES},
        "source_id_disjoint": True,
    }


def _load_candidate_bundle(root: Path) -> dict[str, Any]:
    build_path = root / "BUILD_RECEIPT.json"
    build = _load_json(build_path, label="candidate build receipt")
    if (
        build.get("schema") != "clay.full-system-action-candidate-build-receipt.v1"
        or build.get("status") != "COMPLETE_NOT_ADMITTED"
    ):
        raise ValueError("candidate build receipt is not a completed candidate build")
    if build.get("authority") != {
        "dataset_admission": "NONE",
        "launch": "NONE",
        "partial_unfreeze": "NONE",
        "promotion": "NONE",
        "tool_dispatch": "DISABLED",
    }:
        raise ValueError("candidate build receipt has unexpected authority")

    manifest_path = root / "CANDIDATE_MANIFEST.json"
    manifest = _load_json(manifest_path, label="candidate manifest")
    manifest_descriptor = build.get("manifest")
    if not isinstance(manifest_descriptor, dict):
        raise ValueError("candidate build omitted its manifest descriptor")
    if Path(str(manifest_descriptor.get("path"))).resolve() != manifest_path.resolve():
        raise ValueError("candidate manifest path differs from build receipt")
    if int(manifest_descriptor.get("bytes", -1)) != manifest_path.stat().st_size:
        raise RuntimeError("candidate manifest byte count differs")
    if manifest_descriptor.get("sha256") != sha256_file(manifest_path):
        raise RuntimeError("candidate manifest hash differs")
    if (
        manifest.get("schema") != CANDIDATE_MANIFEST_SCHEMA
        or manifest.get("accepted_campaign_schema") != CAMPAIGN_MANIFEST_SCHEMA
        or manifest.get("accepted_by_campaign_loader") is not False
        or manifest.get("material_evidence_authorized") is not False
        or manifest.get("training_authorized") is not False
        or manifest.get("review_status") != "NOT_REVIEWED"
    ):
        raise ValueError("candidate manifest authority boundary changed")

    files = manifest.get("files")
    outputs = build.get("outputs")
    if not isinstance(files, dict) or not isinstance(outputs, dict):
        raise ValueError("candidate build omitted output descriptors")
    rows: dict[str, list[dict[str, Any]]] = {}
    descriptors: dict[str, dict[str, Any]] = {}
    for lane in LANES:
        if files.get(lane) != outputs.get(lane):
            raise RuntimeError(f"candidate {lane} descriptors differ")
        path, expected_records, descriptor = _verify_descriptor(
            root, files.get(lane), label=f"candidate {lane}"
        )
        lane_rows = [
            _verify_candidate_row(row, lane=lane)
            for row in _load_jsonl(path, label=f"candidate {lane}")
        ]
        if len(lane_rows) != expected_records:
            raise RuntimeError(f"candidate {lane} record count differs")
        rows[lane] = lane_rows
        descriptors[lane] = descriptor

    if manifest.get("source_authorities") != outputs.get("source_authorities"):
        raise RuntimeError("candidate authority descriptors differ")
    authority_path, expected_authorities, authority_descriptor = _verify_descriptor(
        root,
        manifest.get("source_authorities"),
        label="candidate source authorities",
    )
    authority_document = _load_json(
        authority_path, label="candidate source-authority ledger"
    )
    if (
        authority_document.get("schema") != CANDIDATE_AUTHORITY_SCHEMA
        or authority_document.get("review_status") != "NOT_REVIEWED"
        or authority_document.get("training_authorized") is not False
    ):
        raise ValueError("candidate source-authority boundary changed")
    raw_authorities = authority_document.get("authorities")
    if not isinstance(raw_authorities, list):
        raise TypeError("candidate source authorities must be a list")
    authorities = [_verify_authority_receipt(raw) for raw in raw_authorities]
    if len(authorities) != expected_authorities:
        raise RuntimeError("candidate source-authority count differs")
    validation = _validate_four_lane_state(rows, authorities)
    return {
        "authority_descriptor": authority_descriptor,
        "authority_path": authority_path,
        "authorities": authorities,
        "build": build,
        "build_path": build_path,
        "descriptors": descriptors,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "rows": rows,
        "validation": validation,
    }


def _authority_records(document: Mapping[str, Any], *, lane: str) -> dict[str, Any]:
    if (
        document.get("schema") != PACKET_FREE_AUTHORITY_SCHEMA
        or document.get("review_status") != "ADMITTED"
        or document.get("lane") != lane
        or document.get("training_authorized") is not False
    ):
        raise ValueError(f"{lane} packet-free authority boundary changed")
    authority = document.get("authority")
    if not isinstance(authority, dict):
        raise TypeError(f"{lane} packet-free authority fields are missing")
    for field in REQUIRED_AUTHORITY_FIELDS:
        if authority.get(field) != NO_AUTHORITY:
            raise ValueError(f"{lane} authority unexpectedly authorizes {field}")
    records: dict[str, Any] = {}
    sources = document.get("sources")
    if not isinstance(sources, list):
        raise TypeError(f"{lane} packet-free sources must be a list")
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("records"), list):
            raise TypeError(f"{lane} packet-free source is incomplete")
        for record in source["records"]:
            identity = _required_text(record.get("id"), label=f"{lane} authority id")
            if identity in records:
                raise ValueError(f"{lane} packet-free authority repeats an identity")
            records[identity] = {"record": record, "source": source}
    return records


def _load_admission(root: Path) -> dict[str, Any]:
    build_path = root / "BUILD_RECEIPT.json"
    build = _load_json(build_path, label="admission build receipt")
    if (
        build.get("schema") != ADMISSION_BUILD_SCHEMA
        or build.get("status") != ADMISSION_STATUS
        or build.get("training_authorized") is not False
    ):
        raise ValueError("packet-free admission build boundary changed")
    authority = build.get("authority")
    if (
        not isinstance(authority, dict)
        or authority.get("source_provenance") != "ADMITTED"
    ):
        raise ValueError("packet-free admission lacks admitted source provenance")
    for field, expected in DISABLED_BUILD_AUTHORITY.items():
        if authority.get(field) != expected:
            raise ValueError(f"packet-free admission unexpectedly authorizes {field}")

    outputs = build.get("outputs")
    counts = build.get("counts")
    if not isinstance(outputs, dict) or not isinstance(counts, dict):
        raise ValueError("packet-free admission omitted outputs or counts")
    lane_states: dict[str, Any] = {}
    for lane in CONTROL_LANES:
        authority_path, authority_records, authority_descriptor = _verify_descriptor(
            root, outputs.get(f"{lane}_authority"), label=f"admitted {lane} authority"
        )
        source_path, source_records, source_descriptor = _verify_descriptor(
            root, outputs.get(f"{lane}_source"), label=f"admitted {lane} source"
        )
        if authority_records != source_records:
            raise RuntimeError(f"admitted {lane} authority/source counts differ")
        source_rows = _load_jsonl(source_path, label=f"admitted {lane} source")
        if len(source_rows) != source_records:
            raise RuntimeError(f"admitted {lane} source record count differs")
        canonical, validation = validate_packet_free_rows(
            source_rows, authority_path=authority_path, lane=lane
        )
        if len(canonical) != source_records:
            raise RuntimeError(f"admitted {lane} production validation count differs")
        authority_document = _load_json(
            authority_path, label=f"admitted {lane} authority"
        )
        records = _authority_records(authority_document, lane=lane)
        source_by_id = {
            _required_text(row.get("id"), label=f"admitted {lane} source id"): row
            for row in source_rows
        }
        if set(source_by_id) != set(records):
            raise RuntimeError(f"admitted {lane} source/authority identities differ")
        expected_count = int(counts.get("admitted", {}).get(lane, -1))
        if expected_count != source_records:
            raise RuntimeError(f"admitted {lane} count differs from build receipt")
        lane_states[lane] = {
            "authority_descriptor": authority_descriptor,
            "authority_document": authority_document,
            "authority_path": authority_path,
            "records": records,
            "source_by_id": source_by_id,
            "source_descriptor": source_descriptor,
            "source_path": source_path,
            "validation": validation,
        }
    return {"build": build, "build_path": build_path, "lanes": lane_states}


def _join_control_lane(
    *,
    lane: str,
    candidate_rows: Sequence[Mapping[str, Any]],
    candidate_authorities: Mapping[str, Mapping[str, Any]],
    admission_state: Mapping[str, Any],
    admission_build_sha256: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidate_by_id = {str(row["id"]): row for row in candidate_rows}
    if len(candidate_by_id) != len(candidate_rows):
        raise ValueError(f"candidate {lane} lane repeats a record ID")
    admitted_ids = set(admission_state["source_by_id"])
    if not admitted_ids <= set(candidate_by_id):
        raise ValueError(f"admitted {lane} identity is absent from candidate lane")

    joined_rows: list[dict[str, Any]] = []
    joined_authorities: list[dict[str, Any]] = []
    for identity in [
        str(row["id"]) for row in candidate_rows if str(row["id"]) in admitted_ids
    ]:
        candidate = dict(candidate_by_id[identity])
        admitted_source = admission_state["source_by_id"][identity]
        bound = admission_state["records"][identity]
        authority_record = bound["record"]
        source_artifact = bound["source"]
        if candidate["input"] != admitted_source.get("text"):
            raise RuntimeError(f"{identity} admitted text differs from candidate input")
        if candidate["input"] != authority_record.get("text", candidate["input"]):
            raise RuntimeError(
                f"{identity} authority text differs from candidate input"
            )
        content_sha256 = _required_sha256(
            admitted_source.get("content_sha256"), label=f"{identity} content hash"
        )
        if (
            sha256(str(candidate["input"]).encode("utf-8")).hexdigest()
            != content_sha256
        ):
            raise RuntimeError(f"{identity} transformed-content hash differs")
        source_id = str(candidate["source_id"])
        candidate_authority = candidate_authorities.get(source_id)
        if candidate_authority is None:
            raise ValueError(f"{identity} candidate source authority is missing")
        comparisons = {
            "artifact_bytes": source_artifact.get("bytes"),
            "artifact_sha256": source_artifact.get("sha256"),
            "excerpt_sha256": authority_record.get("excerpt_sha256"),
            "lane": lane,
            "locator": authority_record.get("source_locator"),
        }
        for field, expected in comparisons.items():
            if candidate_authority.get(field) != expected:
                raise RuntimeError(f"{identity} candidate/admitted {field} differs")
        if candidate["source_sha256"] != authority_record.get("excerpt_sha256"):
            raise RuntimeError(f"{identity} candidate/admitted excerpt hash differs")
        candidate["review_status"] = "SOURCE_PROVENANCE_ADMITTED"
        candidate["source_provenance"] = {
            "admission_build_sha256": admission_build_sha256,
            "admission_row_id": identity,
            "content_sha256": content_sha256,
            "status": "ADMITTED",
        }
        candidate["training_eligible"] = False
        joined_rows.append(candidate)
        joined_authorities.append(dict(candidate_authority))
    if set(row["id"] for row in joined_rows) != admitted_ids:
        raise RuntimeError(f"{lane} admitted identity coverage differs")
    return joined_rows, joined_authorities


def _existing_parent(path: Path) -> Path:
    current = path
    while not current.exists():
        if current.parent == current:
            raise FileNotFoundError("no existing parent for output path")
        current = current.parent
    return current


def build_frozen_action_material_manifest(
    *,
    candidate_dir: str | Path,
    admission_dir: str | Path,
    output_dir: str | Path,
    minimum_free_gib: float = 25.0,
) -> dict[str, Any]:
    """Write an immutable staged four-lane bundle with no training authority."""

    if minimum_free_gib < 0:
        raise ValueError("minimum_free_gib must be non-negative")
    candidate_root = Path(candidate_dir).resolve(strict=True)
    admission_root = Path(admission_dir).resolve(strict=True)
    output = Path(output_dir).resolve()
    pending = output.with_name(f"{output.name}.pending")
    if output.exists() or pending.exists():
        raise FileExistsError("staging output or pending directory already exists")

    candidate = _load_candidate_bundle(candidate_root)
    admission = _load_admission(admission_root)
    candidate_authorities = {
        str(row["source_id"]): row for row in candidate["authorities"]
    }
    admission_build_sha256 = sha256_file(admission["build_path"])

    rows: dict[str, list[dict[str, Any]]] = {
        lane: [dict(row) for row in candidate["rows"][lane]] for lane in ACTION_LANES
    }
    authorities: list[dict[str, Any]] = [
        dict(authority)
        for authority in candidate["authorities"]
        if authority["lane"] in ACTION_LANES
    ]
    for lane in CONTROL_LANES:
        lane_rows, lane_authorities = _join_control_lane(
            lane=lane,
            candidate_rows=candidate["rows"][lane],
            candidate_authorities=candidate_authorities,
            admission_state=admission["lanes"][lane],
            admission_build_sha256=admission_build_sha256,
        )
        rows[lane] = lane_rows
        authorities.extend(lane_authorities)
    validation = _validate_four_lane_state(rows, authorities)

    input_bytes = sum(
        int(candidate["descriptors"][lane]["bytes"]) for lane in LANES
    ) + int(candidate["authority_descriptor"]["bytes"])
    projected_bytes = input_bytes + 2 * 1024 * 1024
    free_bytes = shutil.disk_usage(_existing_parent(output.parent)).free
    minimum_bytes = int(minimum_free_gib * 1024**3)
    if free_bytes - projected_bytes < minimum_bytes:
        raise RuntimeError("staging build would cross the configured free-space floor")

    pending.mkdir(parents=True)
    try:
        files: dict[str, dict[str, object]] = {}
        for lane in LANES:
            lane_path = pending / f"{lane}.jsonl"
            _write_jsonl(lane_path, rows[lane])
            files[lane] = _descriptor(lane_path, len(rows[lane]))

        authority_document = {
            "authorities": authorities,
            "claim_boundary": (
                "Replayable source provenance only. The surrounding staging manifest "
                "is non-launchable and grants no training or evidence authority."
            ),
            "lineage": {
                "candidate_build_receipt_sha256": sha256_file(candidate["build_path"]),
                "packet_free_admission_build_receipt_sha256": admission_build_sha256,
            },
            "review_status": "ACTION_MAPPING_REVIEW_REQUIRED",
            "schema": CAMPAIGN_AUTHORITY_SCHEMA,
            "training_authorized": False,
        }
        authority_path = pending / "SOURCE_AUTHORITIES.json"
        _write_json(authority_path, authority_document)
        authority_descriptor = _descriptor(authority_path, len(authorities))

        manifest = {
            "accepted_campaign_schema": CAMPAIGN_MANIFEST_SCHEMA,
            "action_mapping_review_status": "NOT_REVIEWED",
            "block_size": int(candidate["manifest"].get("block_size", 0)),
            "files": files,
            "material_evidence_authorized": False,
            "packet_free_source_provenance": "ADMITTED",
            "schema": STAGING_MANIFEST_SCHEMA,
            "source_authorities": authority_descriptor,
            "source_disjoint": True,
            "training_authorized": False,
        }
        manifest_path = pending / "MANIFEST.json"
        _write_json(manifest_path, manifest)
        manifest_descriptor = _descriptor(manifest_path, 1)

        receipt = {
            "authority": dict(DISABLED_BUILD_AUTHORITY),
            "claim_boundary": (
                "This build joins reviewed source provenance to the four candidate "
                "lanes. Its staging schema is deliberately rejected by the campaign; "
                "it proves no action-mapping quality or model benefit."
            ),
            "counts": {lane: len(rows[lane]) for lane in LANES},
            "inputs": {
                "candidate_build_receipt": str(candidate["build_path"]),
                "candidate_build_receipt_sha256": sha256_file(candidate["build_path"]),
                "candidate_manifest": str(candidate["manifest_path"]),
                "candidate_manifest_sha256": sha256_file(candidate["manifest_path"]),
                "packet_free_admission_build_receipt": str(admission["build_path"]),
                "packet_free_admission_build_receipt_sha256": admission_build_sha256,
            },
            "outputs": {
                **files,
                "manifest": manifest_descriptor,
                "source_authorities": authority_descriptor,
            },
            "publication_paths": {
                "manifest": str((output / "MANIFEST.json").resolve()),
                "source_authorities": str(
                    (output / "SOURCE_AUTHORITIES.json").resolve()
                ),
            },
            "schema": STAGING_BUILD_SCHEMA,
            "status": STAGING_STATUS,
            "training_authorized": False,
            "validation": {
                **validation,
                "campaign_schema_is_distinct": (
                    STAGING_MANIFEST_SCHEMA != CAMPAIGN_MANIFEST_SCHEMA
                ),
                "candidate_validation": candidate["validation"],
                "free_bytes_before_build": free_bytes,
                "minimum_free_gib": minimum_free_gib,
                "projected_output_upper_bound_bytes": projected_bytes,
            },
        }
        receipt_path = pending / "BUILD_RECEIPT.json"
        _write_json(receipt_path, receipt)
        os.replace(pending, output)
        return receipt
    except Exception:
        # Preserve the pending directory for forensic inspection.
        raise
