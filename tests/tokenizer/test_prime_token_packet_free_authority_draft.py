from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

from python.scbe.prime_token_packet_free_authority import (
    LINE_STRIP_JOIN_TRANSFORM,
    validate_packet_free_rows,
)
from python.scbe.prime_token_packet_free_authority_draft import (
    CANDIDATE_AUTHORITY_SCHEMA,
    CANDIDATE_BUILD_SCHEMA,
    CANDIDATE_MANIFEST_SCHEMA,
    DRAFT_BUILD_SCHEMA,
    DRAFT_REVIEW_STATUS,
    DRAFT_STATUS,
    SOURCE_AUDIT_SCHEMA,
    _line_span_to_bytes,
    build_packet_free_authority_drafts,
)
from python.scbe.prime_token_training import sha256_file


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


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(_canonical_json(row) + "\n" for row in rows),
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


def _line_excerpt(source: bytes, start: int, end: int) -> bytes:
    text = source.decode("utf-8")
    lines = [line.encode("utf-8") for line in text.splitlines(keepends=True)]
    return b"".join(lines[start:end])


def _fixture(tmp_path: Path, *, overlapping_prompts: bool = False) -> dict[str, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    candidate_root = tmp_path / "candidate"
    source_root = tmp_path / "sources"
    candidate_root.mkdir()
    source_root.mkdir()
    ordinary_source = source_root / "ordinary.rst"
    retention_source = source_root / "retention.md"
    ordinary_source.write_text(
        "  Run the exact action now.\n  Continue along the verified path.\n\nignored\n",
        encoding="utf-8",
        newline="",
    )
    if overlapping_prompts:
        retention_source.write_text(
            "Run the exact action now.\nContinue along the verified path.\n\nother\n",
            encoding="utf-8",
            newline="",
        )
    else:
        retention_source.write_text(
            "  Preserve the old behavior.\n  Return through the stable route.\n\nignored\n",
            encoding="utf-8",
            newline="",
        )

    lane_specs = {
        "ordinary": {
            "source": "python-cpython-controlflow",
            "family": "python-cpython-documentation",
            "path": ordinary_source,
            "locator": "fixture://cpython#lines=0:2",
        },
        "retention": {
            "source": "rust-lang-book-control-flow",
            "family": "rust-lang-book",
            "path": retention_source,
            "locator": "fixture://rust#lines=0:2",
        },
    }
    ledger_rows: list[dict] = []
    candidate_rows: dict[str, list[dict]] = {}
    candidate_authorities: list[dict] = []
    for lane, spec in lane_specs.items():
        path = spec["path"]
        source_bytes = path.read_bytes()
        excerpt = _line_excerpt(source_bytes, 0, 2)
        prompt = " ".join(part.strip() for part in excerpt.decode("utf-8").splitlines() if part.strip())
        source_id = f"{spec['source']}:{lane}:0000"
        record_id = f"text-{source_id}"
        excerpt_hash = sha256(excerpt).hexdigest()
        prompt_hash = sha256(prompt.encode("utf-8")).hexdigest()
        ledger_rows.append(
            {
                "action_terms": ["run"] if lane == "ordinary" else ["return"],
                "artifact_sha256": sha256_file(path),
                "excerpt_sha256": excerpt_hash,
                "lane": lane,
                "prompt": prompt,
                "prompt_bytes": len(prompt.encode("utf-8")),
                "prompt_sha256": prompt_hash,
                "review_status": DRAFT_REVIEW_STATUS,
                "source": spec["source"],
                "source_family": spec["family"],
                "source_id": source_id,
                "span": {"end": 2, "start": 0, "unit": "line"},
                "training_eligible": False,
            }
        )
        candidate_rows[lane] = [
            {
                "id": record_id,
                "input": prompt,
                "review_status": DRAFT_REVIEW_STATUS,
                "source_id": source_id,
                "source_kind": "published_source",
                "source_sha256": excerpt_hash,
                "split": lane,
                "training_eligible": False,
            }
        ]
        unsigned = {
            "artifact_bytes": path.stat().st_size,
            "artifact_sha256": sha256_file(path),
            "excerpt_sha256": excerpt_hash,
            "lane": lane,
            "locator": spec["locator"],
            "source_family": spec["family"],
            "source_id": source_id,
            "source_kind": "published_source",
            "span": {"end": 2, "start": 0, "unit": "line"},
        }
        candidate_authorities.append({**unsigned, "receipt_sha256": _sha256_json(unsigned)})

    text_ledger = source_root / "TEXT_SOURCE_SPAN_AUDIT.rows.jsonl"
    _write_jsonl(text_ledger, ledger_rows)
    source_audit = source_root / "SOURCE_AUDIT.json"
    _write_json(
        source_audit,
        {
            "authority": {
                "dataset_admission": "NONE",
                "launch": "NONE",
                "partial_unfreeze": "NONE",
                "promotion": "NONE",
                "tool_dispatch": "DISABLED",
            },
            "schema": SOURCE_AUDIT_SCHEMA,
            "sources": {
                spec["source"]: {
                    "bytes": spec["path"].stat().st_size,
                    "lane": lane,
                    "local_path": str(spec["path"].resolve()),
                    "sha256": sha256_file(spec["path"]),
                    "source_family": spec["family"],
                }
                for lane, spec in lane_specs.items()
            },
            "status": "PINNED_CANDIDATE_SOURCES_NOT_ADMITTED",
            "text_span_audit": {
                "independent_reconstruction": "PASS_INDEPENDENT_RECONSTRUCTION",
                "row_ledger_bytes": text_ledger.stat().st_size,
                "row_ledger_path": str(text_ledger.resolve()),
                "row_ledger_rows": len(ledger_rows),
                "row_ledger_sha256": sha256_file(text_ledger),
            },
        },
    )

    lane_paths: dict[str, Path] = {}
    for lane, rows in candidate_rows.items():
        path = candidate_root / f"{lane}.candidate.jsonl"
        _write_jsonl(path, rows)
        lane_paths[lane] = path
    authority_path = candidate_root / "SOURCE_AUTHORITIES.candidate.json"
    _write_json(
        authority_path,
        {
            "authorities": candidate_authorities,
            "claim_boundary": "fixture candidate only",
            "review_status": DRAFT_REVIEW_STATUS,
            "schema": CANDIDATE_AUTHORITY_SCHEMA,
            "training_authorized": False,
        },
    )
    manifest = candidate_root / "CANDIDATE_MANIFEST.json"
    descriptors = {lane: _descriptor(path, len(candidate_rows[lane])) for lane, path in lane_paths.items()}
    authority_descriptor = _descriptor(authority_path, len(candidate_authorities))
    _write_json(
        manifest,
        {
            "accepted_by_campaign_loader": False,
            "files": descriptors,
            "material_evidence_authorized": False,
            "review_status": DRAFT_REVIEW_STATUS,
            "schema": CANDIDATE_MANIFEST_SCHEMA,
            "source_authorities": authority_descriptor,
            "training_authorized": False,
        },
    )
    build = candidate_root / "BUILD_RECEIPT.json"
    _write_json(
        build,
        {
            "authority": {
                "dataset_admission": "NONE",
                "launch": "NONE",
                "partial_unfreeze": "NONE",
                "promotion": "NONE",
                "tool_dispatch": "DISABLED",
            },
            "inputs": {
                "source_audit_receipt_sha256": sha256_file(source_audit),
                "text_audit_ledger_sha256": sha256_file(text_ledger),
            },
            "outputs": {**descriptors, "source_authorities": authority_descriptor},
            "schema": CANDIDATE_BUILD_SCHEMA,
            "status": "COMPLETE_NOT_ADMITTED",
        },
    )
    return {
        "authority": authority_path,
        "candidate_root": candidate_root,
        "ordinary_artifact": ordinary_source,
        "ordinary_candidate": lane_paths["ordinary"],
        "output": tmp_path / "draft-output",
        "source_audit": source_audit,
        "text_ledger": text_ledger,
    }


def _refresh_candidate_descriptors(paths: dict[str, Path]) -> None:
    root = paths["candidate_root"]
    manifest_path = root / "CANDIDATE_MANIFEST.json"
    build_path = root / "BUILD_RECEIPT.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    build = json.loads(build_path.read_text(encoding="utf-8"))
    for lane in ("ordinary", "retention"):
        path = root / f"{lane}.candidate.jsonl"
        records = len([line for line in path.read_text(encoding="utf-8").splitlines() if line])
        descriptor = _descriptor(path, records)
        manifest["files"][lane] = descriptor
        build["outputs"][lane] = descriptor
    authority_document = json.loads(paths["authority"].read_text(encoding="utf-8"))
    descriptor = _descriptor(paths["authority"], len(authority_document["authorities"]))
    manifest["source_authorities"] = descriptor
    build["outputs"]["source_authorities"] = descriptor
    _write_json(manifest_path, manifest)
    _write_json(build_path, build)


def _build(paths: dict[str, Path]) -> dict[str, object]:
    return build_packet_free_authority_drafts(
        candidate_root=paths["candidate_root"],
        source_audit_receipt_path=paths["source_audit"],
        output_dir=paths["output"],
    )


def test_builds_exact_nonadmitted_drafts_and_review_packet(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)

    receipt = _build(paths)

    assert receipt["schema"] == DRAFT_BUILD_SCHEMA
    assert receipt["status"] == DRAFT_STATUS
    assert receipt["counts"] == {"ordinary": 1, "retention": 1, "total": 2}
    assert receipt["draft_runtime_rejection_verified"] is True
    assert receipt["training_authorized"] is False
    output = paths["output"]
    ordinary_authority = json.loads((output / "ordinary.authority.draft.json").read_text(encoding="utf-8"))
    ordinary_rows = [
        json.loads(line) for line in (output / "ordinary.source.draft.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert ordinary_authority["review_status"] == DRAFT_REVIEW_STATUS
    assert ordinary_authority["authority"]["training_intake"] == "NOT_AUTHORIZED"
    assert ordinary_authority["sources"][0]["records"][0]["byte_start"] == 0
    assert ordinary_authority["sources"][0]["records"][0]["text_transform"] == LINE_STRIP_JOIN_TRANSFORM
    with pytest.raises(ValueError, match="not admitted"):
        validate_packet_free_rows(
            ordinary_rows,
            authority_path=output / "ordinary.authority.draft.json",
            lane="ordinary",
        )
    review_rows = [
        json.loads(line) for line in (output / "REVIEW_PACKET.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(review_rows) == 2
    assert {row["decision"] for row in review_rows} == {"PENDING"}
    assert {row["training_authorized"] for row in review_rows} == {False}


def test_rejects_artifact_drift_and_candidate_text_tampering(tmp_path: Path) -> None:
    drift = _fixture(tmp_path / "drift")
    drift["ordinary_artifact"].write_text("changed", encoding="utf-8")
    with pytest.raises(RuntimeError, match="artifact hash differs"):
        _build(drift)

    tamper = _fixture(tmp_path / "tamper")
    rows = [json.loads(line) for line in tamper["ordinary_candidate"].read_text(encoding="utf-8").splitlines()]
    rows[0]["input"] = "rewritten candidate prompt"
    _write_jsonl(tamper["ordinary_candidate"], rows)
    _refresh_candidate_descriptors(tamper)
    with pytest.raises(RuntimeError, match="transformed prompt differs"):
        _build(tamper)


def test_rejects_authority_receipt_tampering_and_missing_coverage(
    tmp_path: Path,
) -> None:
    tamper = _fixture(tmp_path / "receipt")
    authority = json.loads(tamper["authority"].read_text(encoding="utf-8"))
    authority["authorities"][0]["locator"] = "fixture://tampered"
    _write_json(tamper["authority"], authority)
    _refresh_candidate_descriptors(tamper)
    with pytest.raises(RuntimeError, match="authority receipt differs"):
        _build(tamper)

    missing = _fixture(tmp_path / "missing")
    authority = json.loads(missing["authority"].read_text(encoding="utf-8"))
    authority["authorities"] = [row for row in authority["authorities"] if row["lane"] != "retention"]
    _write_json(missing["authority"], authority)
    _refresh_candidate_descriptors(missing)
    with pytest.raises(ValueError, match="lacks source coverage"):
        _build(missing)


def test_rejects_invalid_line_span_and_cross_lane_content_overlap(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="out of bounds"):
        _line_span_to_bytes(
            b"one\ntwo\n",
            {"start": 0, "end": 3, "unit": "line"},
            label="fixture span",
        )

    overlap = _fixture(tmp_path / "overlap", overlapping_prompts=True)
    with pytest.raises(ValueError, match="reuse transformed content"):
        _build(overlap)


def test_refuses_to_overwrite_existing_output(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    _build(paths)

    with pytest.raises(FileExistsError, match="already exists"):
        _build(paths)


def test_direct_cli_launches_outside_repo_root(tmp_path: Path) -> None:
    paths = _fixture(tmp_path / "fixture")
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "tokenizer" / "build_packet_free_authority_drafts.py"

    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-B",
            str(script),
            "--candidate-root",
            str(paths["candidate_root"]),
            "--source-audit-receipt",
            str(paths["source_audit"]),
            "--output",
            str(paths["output"]),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["schema"] == DRAFT_BUILD_SCHEMA
    assert receipt["status"] == DRAFT_STATUS
    assert receipt["draft_runtime_rejection_verified"] is True
    assert receipt["training_authorized"] is False
