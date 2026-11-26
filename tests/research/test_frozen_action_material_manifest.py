"""Fail-closed tests for the four-lane frozen-action staging manifest."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

from python.scbe.frozen_action_material_manifest import (
    CAMPAIGN_AUTHORITY_SCHEMA,
    CAMPAIGN_MANIFEST_SCHEMA,
    CANDIDATE_AUTHORITY_SCHEMA,
    CANDIDATE_MANIFEST_SCHEMA,
    DISABLED_BUILD_AUTHORITY,
    STAGING_MANIFEST_SCHEMA,
    STAGING_STATUS,
    _canonical_json,
    _sha256_json,
    build_frozen_action_material_manifest,
)
from python.scbe.prime_token_packet_free_admission import (
    ADMISSION_BUILD_SCHEMA,
    ADMISSION_STATUS,
)
from python.scbe.prime_token_packet_free_authority import (
    IDENTITY_TRANSFORM,
    NO_AUTHORITY,
    PACKET_FREE_AUTHORITY_SCHEMA,
    REQUIRED_AUTHORITY_FIELDS,
)
from python.scbe.prime_token_training import sha256_file


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(_canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def _descriptor(path: Path, records: int) -> dict[str, object]:
    return {
        "bytes": path.stat().st_size,
        "path": path.name,
        "records": records,
        "sha256": sha256_file(path),
    }


def _source_authority(
    *,
    source_id: str,
    source_family: str,
    lane: str,
    artifact: Path,
    excerpt: bytes,
    locator: str,
) -> dict[str, object]:
    unsigned: dict[str, object] = {
        "artifact_bytes": artifact.stat().st_size,
        "artifact_sha256": sha256_file(artifact),
        "excerpt_sha256": sha256(excerpt).hexdigest(),
        "lane": lane,
        "locator": locator,
        "source_family": source_family,
        "source_id": source_id,
        "source_kind": "published_source",
        "span": {"end": 1, "start": 0, "unit": "record"},
    }
    return {**unsigned, "receipt_sha256": _sha256_json(unsigned)}


def _candidate_row(
    *,
    identity: str,
    lane: str,
    source_id: str,
    text: str,
    excerpt_sha256: str,
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": identity,
        "input": text,
        "review_status": "NOT_REVIEWED",
        "source_id": source_id,
        "source_kind": "published_source",
        "source_sha256": excerpt_sha256,
        "split": lane,
        "training_eligible": False,
    }
    if lane in {"train", "holdout"}:
        row["target"] = {
            "action_receipt_sha256": sha256(f"action:{identity}".encode()).hexdigest(),
            "canonical": "math :: None :: 1+1",
            "family_token_id": 0,
            "method_token_id": None,
            "payload": "1+1",
        }
    return row


def _fixture(
    tmp_path: Path,
    *,
    locator_mismatch: bool = False,
    family_overlap: bool = False,
) -> dict[str, Path]:
    candidate = tmp_path / "candidate"
    admission = tmp_path / "admission"
    sources = tmp_path / "sources"
    candidate.mkdir(parents=True)
    admission.mkdir()
    sources.mkdir()

    lane_rows: dict[str, list[dict[str, object]]] = {}
    authorities: list[dict[str, object]] = []
    control_material: dict[str, dict[str, object]] = {}
    for lane in ("train", "holdout", "ordinary", "retention"):
        artifact = sources / f"{lane}.txt"
        lines = [f"{lane} admitted line.\n"]
        if lane in {"ordinary", "retention"}:
            lines.append(f"{lane} rejected line.\n")
        artifact.write_bytes("".join(lines).encode("utf-8"))
        family = "shared-family" if family_overlap and lane == "retention" else f"family-{lane}"
        if family_overlap and lane == "ordinary":
            family = "shared-family"
        offset = 0
        lane_rows[lane] = []
        for index, line in enumerate(lines):
            excerpt = line.encode("utf-8")
            identity = f"text-{lane}:fixture:{index:04d}"
            source_id = f"{lane}:fixture:{index:04d}"
            locator = f"fixture://{lane}/{index}"
            lane_rows[lane].append(
                _candidate_row(
                    identity=identity,
                    lane=lane,
                    source_id=source_id,
                    text=line,
                    excerpt_sha256=sha256(excerpt).hexdigest(),
                )
            )
            authorities.append(
                _source_authority(
                    source_id=source_id,
                    source_family=family,
                    lane=lane,
                    artifact=artifact,
                    excerpt=excerpt,
                    locator=(
                        f"fixture://mismatch/{lane}"
                        if locator_mismatch and lane == "ordinary" and index == 0
                        else locator
                    ),
                )
            )
            if index == 0 and lane in {"ordinary", "retention"}:
                control_material[lane] = {
                    "artifact": artifact,
                    "end": len(excerpt),
                    "excerpt": excerpt,
                    "identity": identity,
                    "locator": locator,
                    "start": offset,
                    "text": line,
                }
            offset += len(excerpt)

    files: dict[str, dict[str, object]] = {}
    for lane, rows in lane_rows.items():
        path = candidate / f"{lane}.candidate.jsonl"
        _write_jsonl(path, rows)
        files[lane] = _descriptor(path, len(rows))
    authority_path = candidate / "SOURCE_AUTHORITIES.candidate.json"
    _write_json(
        authority_path,
        {
            "authorities": authorities,
            "claim_boundary": "fixture candidate",
            "review_status": "NOT_REVIEWED",
            "schema": CANDIDATE_AUTHORITY_SCHEMA,
            "training_authorized": False,
        },
    )
    authority_descriptor = _descriptor(authority_path, len(authorities))
    manifest_path = candidate / "CANDIDATE_MANIFEST.json"
    _write_json(
        manifest_path,
        {
            "accepted_by_campaign_loader": False,
            "accepted_campaign_schema": CAMPAIGN_MANIFEST_SCHEMA,
            "block_size": 512,
            "files": files,
            "material_evidence_authorized": False,
            "review_status": "NOT_REVIEWED",
            "schema": CANDIDATE_MANIFEST_SCHEMA,
            "source_authorities": authority_descriptor,
            "source_disjoint": True,
            "training_authorized": False,
        },
    )
    _write_json(
        candidate / "BUILD_RECEIPT.json",
        {
            "authority": {
                "dataset_admission": "NONE",
                "launch": "NONE",
                "partial_unfreeze": "NONE",
                "promotion": "NONE",
                "tool_dispatch": "DISABLED",
            },
            "manifest": {
                "bytes": manifest_path.stat().st_size,
                "path": str(manifest_path.resolve()),
                "sha256": sha256_file(manifest_path),
            },
            "outputs": {**files, "source_authorities": authority_descriptor},
            "schema": "clay.full-system-action-candidate-build-receipt.v1",
            "status": "COMPLETE_NOT_ADMITTED",
        },
    )

    admission_outputs: dict[str, object] = {}
    for lane in ("ordinary", "retention"):
        material = control_material[lane]
        artifact = material["artifact"]
        text = str(material["text"])
        content_sha256 = sha256(text.encode("utf-8")).hexdigest()
        record = {
            "byte_end": material["end"],
            "byte_start": material["start"],
            "content_sha256": content_sha256,
            "excerpt_sha256": sha256(material["excerpt"]).hexdigest(),
            "id": material["identity"],
            "source_locator": material["locator"],
            "text_transform": IDENTITY_TRANSFORM,
        }
        authority_file = admission / f"{lane}.authority.admitted.json"
        _write_json(
            authority_file,
            {
                "authority": {field: NO_AUTHORITY for field in REQUIRED_AUTHORITY_FIELDS},
                "lane": lane,
                "review_status": "ADMITTED",
                "schema": PACKET_FREE_AUTHORITY_SCHEMA,
                "sources": [
                    {
                        "bytes": artifact.stat().st_size,
                        "path": str(artifact.resolve()),
                        "records": [record],
                        "sha256": sha256_file(artifact),
                    }
                ],
                "training_authorized": False,
            },
        )
        source_file = admission / f"{lane}.source.admitted.jsonl"
        _write_jsonl(
            source_file,
            [
                {
                    "content_sha256": content_sha256,
                    "id": material["identity"],
                    "source_locator": material["locator"],
                    "text": text,
                }
            ],
        )
        admission_outputs[f"{lane}_authority"] = _descriptor(authority_file, 1)
        admission_outputs[f"{lane}_source"] = _descriptor(source_file, 1)

    _write_json(
        admission / "BUILD_RECEIPT.json",
        {
            "authority": {
                **DISABLED_BUILD_AUTHORITY,
                "source_provenance": "ADMITTED",
            },
            "counts": {
                "admitted": {"ordinary": 1, "retention": 1},
                "rejected": 2,
                "reviewed_total": 4,
            },
            "outputs": admission_outputs,
            "schema": ADMISSION_BUILD_SCHEMA,
            "status": ADMISSION_STATUS,
            "training_authorized": False,
        },
    )
    return {
        "admission": admission,
        "candidate": candidate,
        "output": tmp_path / "staged",
    }


def test_builds_provenance_bound_nonlaunchable_four_lane_stage(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    receipt = build_frozen_action_material_manifest(
        candidate_dir=paths["candidate"],
        admission_dir=paths["admission"],
        output_dir=paths["output"],
        minimum_free_gib=0,
    )

    assert receipt["status"] == STAGING_STATUS
    assert receipt["counts"] == {
        "holdout": 1,
        "ordinary": 1,
        "retention": 1,
        "train": 1,
    }
    assert receipt["authority"] == DISABLED_BUILD_AUTHORITY
    manifest = json.loads((paths["output"] / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == STAGING_MANIFEST_SCHEMA
    assert manifest["schema"] != manifest["accepted_campaign_schema"]
    assert manifest["training_authorized"] is False
    assert manifest["material_evidence_authorized"] is False
    ledger = json.loads((paths["output"] / "SOURCE_AUTHORITIES.json").read_text(encoding="utf-8"))
    assert ledger["schema"] == CAMPAIGN_AUTHORITY_SCHEMA
    ordinary = json.loads((paths["output"] / "ordinary.jsonl").read_text(encoding="utf-8"))
    assert ordinary["review_status"] == "SOURCE_PROVENANCE_ADMITTED"
    assert ordinary["training_eligible"] is False


def test_rejects_candidate_tampering(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    train = paths["candidate"] / "train.candidate.jsonl"
    train.write_text(train.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="byte count differs"):
        build_frozen_action_material_manifest(
            candidate_dir=paths["candidate"],
            admission_dir=paths["admission"],
            output_dir=paths["output"],
            minimum_free_gib=0,
        )


def test_rejects_admission_candidate_locator_mismatch(tmp_path: Path) -> None:
    paths = _fixture(tmp_path, locator_mismatch=True)
    with pytest.raises(RuntimeError, match="candidate/admitted locator differs"):
        build_frozen_action_material_manifest(
            candidate_dir=paths["candidate"],
            admission_dir=paths["admission"],
            output_dir=paths["output"],
            minimum_free_gib=0,
        )


def test_rejects_cross_lane_source_family_overlap(tmp_path: Path) -> None:
    paths = _fixture(tmp_path, family_overlap=True)
    with pytest.raises(ValueError, match="source families overlap"):
        build_frozen_action_material_manifest(
            candidate_dir=paths["candidate"],
            admission_dir=paths["admission"],
            output_dir=paths["output"],
            minimum_free_gib=0,
        )


def test_refuses_overwrite_and_cli_launches_outside_repo(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "research" / "build_frozen_action_material_manifest.py"
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-B",
            str(script),
            "--candidate-dir",
            str(paths["candidate"]),
            "--admission-dir",
            str(paths["admission"]),
            "--output",
            str(paths["output"]),
            "--minimum-free-gib",
            "0",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == STAGING_STATUS
    with pytest.raises(FileExistsError, match="already exists"):
        build_frozen_action_material_manifest(
            candidate_dir=paths["candidate"],
            admission_dir=paths["admission"],
            output_dir=paths["output"],
            minimum_free_gib=0,
        )
