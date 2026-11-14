"""Fail-closed tests for independent packet-free provenance admission."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Callable

import pytest

from python.scbe.prime_token_packet_free_admission import (
    ADMISSION_BUILD_SCHEMA,
    ADMISSION_STATUS,
    ADMIT_REASON_CODES,
    REVIEW_DECISION_SCHEMA,
    admit_packet_free_authority_drafts,
)
from python.scbe.prime_token_packet_free_authority import (
    LINE_STRIP_JOIN_TRANSFORM,
    NO_AUTHORITY,
    PACKET_FREE_AUTHORITY_SCHEMA,
    REQUIRED_AUTHORITY_FIELDS,
    validate_packet_free_rows,
)
from python.scbe.prime_token_packet_free_authority_draft import (
    DRAFT_BUILD_SCHEMA,
    DRAFT_REVIEW_STATUS,
    DRAFT_STATUS,
)
from python.scbe.prime_token_training import sha256_file


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _descriptor(path: Path, records: int) -> dict[str, object]:
    return {
        "bytes": path.stat().st_size,
        "path": path.name,
        "records": records,
        "sha256": sha256_file(path),
    }


def _record(
    *, identity: str, source: Path, start: int, end: int, locator: str
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    source_bytes = source.read_bytes()
    excerpt = source_bytes[start:end]
    raw = excerpt.decode("utf-8")
    text = " ".join(part.strip() for part in raw.splitlines() if part.strip())
    content_sha256 = sha256(text.encode("utf-8")).hexdigest()
    authority_record: dict[str, object] = {
        "byte_end": end,
        "byte_start": start,
        "content_sha256": content_sha256,
        "excerpt_sha256": sha256(excerpt).hexdigest(),
        "id": identity,
        "source_locator": locator,
        "text_transform": LINE_STRIP_JOIN_TRANSFORM,
    }
    source_row: dict[str, object] = {
        "content_sha256": content_sha256,
        "id": identity,
        "source_locator": locator,
        "text": text,
    }
    review_row: dict[str, object] = {
        "action_terms": ["run"],
        "content_sha256": content_sha256,
        "decision": "PENDING",
        "id": identity,
        "lane": identity.split(":")[0],
        "raw_excerpt": raw,
        "review_status": DRAFT_REVIEW_STATUS,
        "source_artifact_path": str(source.resolve()),
        "source_artifact_sha256": sha256_file(source),
        "source_byte_end": end,
        "source_byte_start": start,
        "source_excerpt_sha256": sha256(excerpt).hexdigest(),
        "source_family_label": f"fixture-{identity.split(':')[0]}",
        "source_id": identity,
        "source_line_span": {"end": 1, "start": 0, "unit": "line"},
        "source_locator": locator,
        "text": text,
        "text_transform": LINE_STRIP_JOIN_TRANSFORM,
        "training_authorized": False,
    }
    return authority_record, source_row, review_row


def _fixture(tmp_path: Path, *, overlapping_content: bool = False) -> dict[str, Path]:
    source_root = tmp_path / "sources"
    draft = tmp_path / "draft"
    source_root.mkdir(parents=True)
    draft.mkdir()
    ordinary_source = source_root / "ordinary.txt"
    retention_source = source_root / "retention.txt"
    ordinary_lines = ("Run the first branch.\n", "Return the ordinary value.\n")
    retention_lines = (
        ordinary_lines[0] if overlapping_content else "Execute the retained loop.\n",
        "Stop after the retained condition.\n",
    )
    ordinary_source.write_text("".join(ordinary_lines), encoding="utf-8")
    retention_source.write_text("".join(retention_lines), encoding="utf-8")

    lane_specs = {
        "ordinary": (ordinary_source, ordinary_lines),
        "retention": (retention_source, retention_lines),
    }
    review_rows: list[dict[str, object]] = []
    descriptors: dict[str, object] = {}
    for lane, (source, lines) in lane_specs.items():
        authority_records: list[dict[str, object]] = []
        source_rows: list[dict[str, object]] = []
        offset = 0
        for index, line in enumerate(lines):
            end = offset + len(line.encode("utf-8"))
            identity = f"{lane}:fixture:{index:04d}"
            authority_record, source_row, review_row = _record(
                identity=identity,
                source=source,
                start=offset,
                end=end,
                locator=f"fixture://{lane}/{index}",
            )
            authority_records.append(authority_record)
            source_rows.append(source_row)
            review_rows.append(review_row)
            offset = end
        authority_path = draft / f"{lane}.authority.draft.json"
        source_path = draft / f"{lane}.source.draft.jsonl"
        _write_json(
            authority_path,
            {
                "authority": {field: NO_AUTHORITY for field in REQUIRED_AUTHORITY_FIELDS},
                "draft_metadata": {
                    "candidate_source_family_label": f"fixture-{lane}",
                    "claim_boundary": "fixture draft only",
                    "text_transform": LINE_STRIP_JOIN_TRANSFORM,
                },
                "lane": lane,
                "review_status": DRAFT_REVIEW_STATUS,
                "schema": PACKET_FREE_AUTHORITY_SCHEMA,
                "sources": [
                    {
                        "bytes": source.stat().st_size,
                        "path": str(source.resolve()),
                        "records": authority_records,
                        "sha256": sha256_file(source),
                    }
                ],
            },
        )
        _write_jsonl(source_path, source_rows)
        descriptors[f"{lane}_authority"] = _descriptor(authority_path, len(lines))
        descriptors[f"{lane}_source"] = _descriptor(source_path, len(lines))

    review_packet = draft / "REVIEW_PACKET.jsonl"
    _write_jsonl(review_packet, review_rows)
    descriptors["review_packet"] = _descriptor(review_packet, len(review_rows))

    ordinary_license = source_root / "ordinary.LICENSE"
    retention_license = source_root / "retention.LICENSE"
    ordinary_license.write_text("Fixture license A\n", encoding="utf-8")
    retention_license.write_text("Fixture license B\n", encoding="utf-8")
    source_audit = source_root / "SOURCE_AUDIT.json"
    _write_json(
        source_audit,
        {
            "sources": {
                "fixture-ordinary": {
                    "bytes": ordinary_source.stat().st_size,
                    "lane": "ordinary",
                    "license": "Fixture-A",
                    "license_bytes": ordinary_license.stat().st_size,
                    "license_path": str(ordinary_license.resolve()),
                    "license_sha256": sha256_file(ordinary_license),
                    "local_path": str(ordinary_source.resolve()),
                    "sha256": sha256_file(ordinary_source),
                },
                "fixture-retention": {
                    "bytes": retention_source.stat().st_size,
                    "lane": "retention",
                    "license": "Fixture-B",
                    "license_files": [
                        {
                            "bytes": retention_license.stat().st_size,
                            "path": str(retention_license.resolve()),
                            "sha256": sha256_file(retention_license),
                        }
                    ],
                    "local_path": str(retention_source.resolve()),
                    "sha256": sha256_file(retention_source),
                },
            },
            "status": "PINNED_CANDIDATE_SOURCES_NOT_ADMITTED",
        },
    )
    build = draft / "BUILD_RECEIPT.json"
    _write_json(
        build,
        {
            "inputs": {
                "source_audit_receipt": str(source_audit.resolve()),
                "source_audit_receipt_sha256": sha256_file(source_audit),
            },
            "outputs": descriptors,
            "review_status": DRAFT_REVIEW_STATUS,
            "schema": DRAFT_BUILD_SCHEMA,
            "status": DRAFT_STATUS,
            "training_authorized": False,
        },
    )
    decision_path = tmp_path / "decisions.json"
    _write_decisions(decision_path, review_packet)
    return {
        "build": build,
        "decisions": decision_path,
        "draft": draft,
        "output": tmp_path / "admitted",
        "review_packet": review_packet,
    }


def _write_decisions(
    path: Path,
    review_packet: Path,
    *,
    mutate: Callable[[list[dict[str, object]]], None] | None = None,
) -> None:
    rows = [json.loads(line) for line in review_packet.read_text(encoding="utf-8").splitlines() if line]
    decisions = [
        {
            "content_sha256": row["content_sha256"],
            "decision": "ADMIT",
            "id": row["id"],
            "lane": row["lane"],
            "reason_codes": sorted(ADMIT_REASON_CODES),
        }
        for row in rows
    ]
    if mutate is not None:
        mutate(decisions)
    _write_json(
        path,
        {
            "decisions": decisions,
            "review_packet_records": len(rows),
            "review_packet_sha256": sha256_file(review_packet),
            "reviewer": {
                "evidence_boundary": "THREAD_IDS_DECLARED_NOT_AUTHENTICATED",
                "id": "fixture-reviewer",
                "ordinary_review_thread": "01900000-0000-7000-8000-000000000001",
                "retention_review_thread": "01900000-0000-7000-8000-000000000002",
                "role": "independent-test-reviewer",
                "separation": "DECLARED_SEPARATE_REVIEW_SESSIONS",
            },
            "schema": REVIEW_DECISION_SCHEMA,
        },
    )


def _load_decision_document(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_admits_reviewed_subset_and_replays_production_validator(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    document = _load_decision_document(paths["decisions"])
    document["decisions"][1]["decision"] = "REJECT"
    document["decisions"][1]["reason_codes"] = ["MARKUP_ONLY"]
    document["decisions"][1]["review_note"] = "Fixture markup-only rejection."
    _write_json(paths["decisions"], document)

    receipt = admit_packet_free_authority_drafts(
        draft_dir=paths["draft"],
        decision_ledger_path=paths["decisions"],
        output_dir=paths["output"],
    )

    assert receipt["schema"] == ADMISSION_BUILD_SCHEMA
    assert receipt["status"] == ADMISSION_STATUS
    assert receipt["training_authorized"] is False
    assert receipt["counts"] == {
        "admitted": {"ordinary": 1, "retention": 2},
        "rejected": 1,
        "reviewed_total": 4,
    }
    assert receipt["authority"]["dataset_admission"] == "NONE"
    assert receipt["authority"]["source_provenance"] == "ADMITTED"
    assert receipt["authority"]["training_intake"] == "NONE"
    rejected = [
        json.loads(line) for line in (paths["output"] / "REJECTED_ROWS.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert rejected[0]["review_note"] == "Fixture markup-only rejection."
    for lane, expected in (("ordinary", 1), ("retention", 2)):
        rows = [
            json.loads(line)
            for line in (paths["output"] / f"{lane}.source.admitted.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        canonical, validation = validate_packet_free_rows(
            rows,
            authority_path=paths["output"] / f"{lane}.authority.admitted.json",
            lane=lane,
        )
        assert len(canonical) == expected
        assert validation["record_count"] == expected
        recorded_authority = Path(receipt["production_validation"][lane]["authority_path"])
        assert recorded_authority.exists()
        assert recorded_authority.parent == paths["output"].resolve()


@pytest.mark.parametrize("case", ["missing", "duplicate", "unknown"])
def test_rejects_incomplete_or_extra_decision_identity(tmp_path: Path, case: str) -> None:
    paths = _fixture(tmp_path)
    document = _load_decision_document(paths["decisions"])
    if case == "missing":
        document["decisions"].pop()
    elif case == "duplicate":
        document["decisions"].append(dict(document["decisions"][0]))
    else:
        document["decisions"][0]["id"] = "ordinary:fixture:unknown"
    _write_json(paths["decisions"], document)
    with pytest.raises(ValueError, match="missing|repeats|unknown"):
        admit_packet_free_authority_drafts(
            draft_dir=paths["draft"],
            decision_ledger_path=paths["decisions"],
            output_dir=paths["output"],
        )


@pytest.mark.parametrize("case", ["stale", "content", "lane", "decision", "reason"])
def test_rejects_stale_or_malformed_review_decision(tmp_path: Path, case: str) -> None:
    paths = _fixture(tmp_path)
    document = _load_decision_document(paths["decisions"])
    row = document["decisions"][0]
    if case == "stale":
        document["review_packet_sha256"] = "0" * 64
    elif case == "content":
        row["content_sha256"] = "0" * 64
    elif case == "lane":
        row["lane"] = "retention"
    elif case == "decision":
        row["decision"] = "PENDING"
    else:
        row["reason_codes"] = ["SUBSTANTIVE_CONTROL_TEXT"]
    _write_json(paths["decisions"], document)
    with pytest.raises((RuntimeError, ValueError)):
        admit_packet_free_authority_drafts(
            draft_dir=paths["draft"],
            decision_ledger_path=paths["decisions"],
            output_dir=paths["output"],
        )


@pytest.mark.parametrize("case", ["boundary", "same_thread", "bad_thread"])
def test_rejects_unbounded_or_invalid_reviewer_metadata(tmp_path: Path, case: str) -> None:
    paths = _fixture(tmp_path)
    document = _load_decision_document(paths["decisions"])
    reviewer = document["reviewer"]
    if case == "boundary":
        reviewer["evidence_boundary"] = "AUTHENTICATED"
    elif case == "same_thread":
        reviewer["retention_review_thread"] = reviewer["ordinary_review_thread"]
    else:
        reviewer["ordinary_review_thread"] = "not-a-uuid"
    _write_json(paths["decisions"], document)

    with pytest.raises(ValueError, match="evidence boundary|must differ|must be UUIDs"):
        admit_packet_free_authority_drafts(
            draft_dir=paths["draft"],
            decision_ledger_path=paths["decisions"],
            output_dir=paths["output"],
        )


def test_rejects_all_rows_in_one_lane(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    document = _load_decision_document(paths["decisions"])
    for row in document["decisions"]:
        if row["lane"] == "ordinary":
            row["decision"] = "REJECT"
            row["reason_codes"] = ["MARKUP_ONLY"]
    _write_json(paths["decisions"], document)
    with pytest.raises(ValueError, match="rejects every ordinary"):
        admit_packet_free_authority_drafts(
            draft_dir=paths["draft"],
            decision_ledger_path=paths["decisions"],
            output_dir=paths["output"],
        )


def test_rejects_draft_tampering_and_authority_escalation(tmp_path: Path) -> None:
    tamper = _fixture(tmp_path / "tamper")
    authority_path = tamper["draft"] / "ordinary.authority.draft.json"
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    authority["sources"][0]["records"][0]["content_sha256"] = "0" * 64
    _write_json(authority_path, authority)
    with pytest.raises(RuntimeError, match="ordinary_authority hash differs"):
        admit_packet_free_authority_drafts(
            draft_dir=tamper["draft"],
            decision_ledger_path=tamper["decisions"],
            output_dir=tamper["output"],
        )

    escalation = _fixture(tmp_path / "escalation")
    authority_path = escalation["draft"] / "ordinary.authority.draft.json"
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    authority["authority"]["training_intake"] = "AUTHORIZED"
    _write_json(authority_path, authority)
    build = json.loads(escalation["build"].read_text(encoding="utf-8"))
    build["outputs"]["ordinary_authority"] = _descriptor(authority_path, 2)
    _write_json(escalation["build"], build)
    with pytest.raises(ValueError, match="unexpectedly authorizes training_intake"):
        admit_packet_free_authority_drafts(
            draft_dir=escalation["draft"],
            decision_ledger_path=escalation["decisions"],
            output_dir=escalation["output"],
        )


def test_rejects_license_receipt_not_bound_to_source(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    build = json.loads(paths["build"].read_text(encoding="utf-8"))
    source_audit_path = Path(build["inputs"]["source_audit_receipt"])
    source_audit = json.loads(source_audit_path.read_text(encoding="utf-8"))
    ordinary = source_audit["sources"]["fixture-ordinary"]
    retention = source_audit["sources"]["fixture-retention"]
    ordinary["bytes"] = retention["bytes"]
    ordinary["local_path"] = retention["local_path"]
    ordinary["sha256"] = retention["sha256"]
    _write_json(source_audit_path, source_audit)
    build["inputs"]["source_audit_receipt_sha256"] = sha256_file(source_audit_path)
    _write_json(paths["build"], build)

    with pytest.raises(RuntimeError, match="ordinary source audit does not match"):
        admit_packet_free_authority_drafts(
            draft_dir=paths["draft"],
            decision_ledger_path=paths["decisions"],
            output_dir=paths["output"],
        )


def test_rejects_non_object_license_file_entry(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    build = json.loads(paths["build"].read_text(encoding="utf-8"))
    source_audit_path = Path(build["inputs"]["source_audit_receipt"])
    source_audit = json.loads(source_audit_path.read_text(encoding="utf-8"))
    source_audit["sources"]["fixture-retention"]["license_files"].append("bad")
    _write_json(source_audit_path, source_audit)
    build["inputs"]["source_audit_receipt_sha256"] = sha256_file(source_audit_path)
    _write_json(paths["build"], build)

    with pytest.raises(TypeError, match="license_files entries must be objects"):
        admit_packet_free_authority_drafts(
            draft_dir=paths["draft"],
            decision_ledger_path=paths["decisions"],
            output_dir=paths["output"],
        )


def test_rejects_cross_lane_content_overlap(tmp_path: Path) -> None:
    paths = _fixture(tmp_path, overlapping_content=True)
    with pytest.raises(ValueError, match="reuse transformed content"):
        admit_packet_free_authority_drafts(
            draft_dir=paths["draft"],
            decision_ledger_path=paths["decisions"],
            output_dir=paths["output"],
        )


def test_records_verified_superseded_receipts(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    prior_output = tmp_path / "prior-admission"
    admit_packet_free_authority_drafts(
        draft_dir=paths["draft"],
        decision_ledger_path=paths["decisions"],
        output_dir=prior_output,
    )
    prior_receipt = prior_output / "BUILD_RECEIPT.json"
    successor_output = tmp_path / "successor-admission"
    receipt = admit_packet_free_authority_drafts(
        draft_dir=paths["draft"],
        decision_ledger_path=paths["decisions"],
        output_dir=successor_output,
        superseded_receipts=[prior_receipt],
    )

    assert receipt["supersedes"] == [
        {
            "bytes": prior_receipt.stat().st_size,
            "path": str(prior_receipt.resolve()),
            "reason": "REPLACED_BY_THIS_RECEIPT",
            "schema": ADMISSION_BUILD_SCHEMA,
            "sha256": sha256_file(prior_receipt),
            "status": ADMISSION_STATUS,
        }
    ]


def test_refuses_overwrite_and_cli_launches_outside_repo(tmp_path: Path) -> None:
    paths = _fixture(tmp_path / "direct")
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "tokenizer" / "admit_packet_free_authority_drafts.py"
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-B",
            str(script),
            "--draft-dir",
            str(paths["draft"]),
            "--decisions",
            str(paths["decisions"]),
            "--output",
            str(paths["output"]),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == ADMISSION_STATUS
    with pytest.raises(FileExistsError, match="already exists"):
        admit_packet_free_authority_drafts(
            draft_dir=paths["draft"],
            decision_ledger_path=paths["decisions"],
            output_dir=paths["output"],
        )
