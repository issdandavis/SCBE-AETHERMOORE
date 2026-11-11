from __future__ import annotations

import json
from pathlib import Path

from python.scbe.prime_token_watch_audit import (
    PREPARER_AUTHORITY,
    PREPARER_PIN_SCHEMA,
    PREPARER_STATUS_SCHEMA,
    WATCHER_AUTHORITY,
    WATCHER_PIN_SCHEMA,
    WATCHER_PIN_SCHEMA_V3,
    WATCHER_STATUS_SCHEMA,
    canonical_sha256,
    sha256_file,
    verify_watch_chain,
)


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _fixture(tmp_path: Path) -> dict[str, Path]:
    files = {}
    for name in ("manifest", "collector", "watcher", "harvester", "preparer", "prep_watcher"):
        path = tmp_path / f"{name}.txt"
        path.write_text(name, encoding="utf-8")
        files[name] = path
    catalog = tmp_path / "catalog.sqlite3"
    catalog.write_bytes(b"sealed-catalog")
    catalog_hash = sha256_file(catalog)
    watcher_pin = {
        "schema": WATCHER_PIN_SCHEMA,
        "authority": WATCHER_AUTHORITY,
        "source_session_disjoint_gate": True,
        "catalog_manifest": str(files["manifest"]),
        "catalog_manifest_sha256": sha256_file(files["manifest"]),
        "catalog_sha256": catalog_hash,
        "collector": str(files["collector"]),
        "collector_sha256": sha256_file(files["collector"]),
        "watcher": str(files["watcher"]),
        "watcher_sha256": sha256_file(files["watcher"]),
        "scbe_harvester": str(files["harvester"]),
        "scbe_harvester_sha256": sha256_file(files["harvester"]),
        "minimum_candidates": 30,
    }
    watcher_status = {
        "schema": WATCHER_STATUS_SCHEMA,
        "status": "WAITING_FOR_SESSION_CLOSE",
        "source_session_disjoint": True,
        "catalog_boundary": {"catalog_sha256": catalog_hash},
        "minimum_candidates": 30,
        "candidate_count": 0,
        "open_post_freeze_source_count": 1,
        "closed_post_freeze_source_count": 0,
        "scoring": "NOT_AUTHORIZED",
        "training_intake": "NOT_AUTHORIZED",
        "promotion": "NOT_AUTHORIZED",
    }
    preparer_pin = {
        "schema": PREPARER_PIN_SCHEMA,
        "authority": PREPARER_AUTHORITY,
        "watcher": str(files["prep_watcher"]),
        "watcher_sha256": sha256_file(files["prep_watcher"]),
        "preparer": str(files["preparer"]),
        "preparer_sha256": sha256_file(files["preparer"]),
        "catalog_sha256": catalog_hash,
        "minimum_candidates": 30,
    }
    preparer_status = {
        "schema": PREPARER_STATUS_SCHEMA,
        "status": "WAITING_FOR_PROSPECTIVE_QUEUE",
        "minimum_candidates": 30,
        "candidate_count": 0,
        "scoring": "NOT_AUTHORIZED",
        "training_intake": "NOT_AUTHORIZED",
        "serving": "NOT_AUTHORIZED",
        "merge": "NOT_AUTHORIZED",
        "promotion": "NOT_AUTHORIZED",
    }
    return {
        "watcher_pin": _write(tmp_path / "WATCHER_PIN.json", watcher_pin),
        "watcher_status": _write(tmp_path / "WATCHER_STATUS.json", watcher_status),
        "preparer_pin": _write(tmp_path / "PREPARER_PIN.json", preparer_pin),
        "preparer_status": _write(tmp_path / "PREPARER_STATUS.json", preparer_status),
        "catalog": catalog,
        "packet": tmp_path / "packet",
        "collector": files["collector"],
    }


def _verify(paths: dict[str, Path]) -> dict:
    return verify_watch_chain(
        watcher_pin_path=paths["watcher_pin"],
        watcher_status_path=paths["watcher_status"],
        preparer_pin_path=paths["preparer_pin"],
        preparer_status_path=paths["preparer_status"],
        catalog_database=paths["catalog"],
        packet_output_dir=paths["packet"],
    )


def test_watch_chain_verifies_waiting_collection_only_path(tmp_path: Path) -> None:
    result = _verify(_fixture(tmp_path))
    assert result["status"] == "VERIFIED_WAITING_NO_SCORING"
    assert result["error_count"] == 0
    assert result["candidate_count"] == 0
    assert result["open_post_freeze_source_count"] == 1
    assert result["promotion"] == "NOT_AUTHORIZED"


def test_watch_chain_rejects_pinned_source_drift(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    paths["collector"].write_text("mutated", encoding="utf-8")
    result = _verify(paths)
    assert result["status"] == "INVALID_WATCH_CHAIN"
    assert "collector hash mismatch" in result["errors"]


def test_watch_chain_rejects_scoring_artifact_or_authority_drift(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    paths["packet"].mkdir()
    (paths["packet"] / "RESULT.json").write_text("{}", encoding="utf-8")
    status = json.loads(paths["preparer_status"].read_text(encoding="utf-8"))
    status["training_intake"] = "AUTHORIZED"
    _write(paths["preparer_status"], status)
    result = _verify(paths)
    assert result["status"] == "INVALID_WATCH_CHAIN"
    assert "collection/preparation directory contains a scoring artifact" in result["errors"]
    assert "preparer unexpectedly authorizes training_intake" in result["errors"]


def test_watch_chain_rejects_serving_or_merge_authority_drift(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    status = json.loads(paths["preparer_status"].read_text(encoding="utf-8"))
    status["serving"] = "AUTHORIZED"
    status["merge"] = "AUTHORIZED"
    _write(paths["preparer_status"], status)
    result = _verify(paths)
    assert result["status"] == "INVALID_WATCH_CHAIN"
    assert "preparer unexpectedly authorizes serving" in result["errors"]
    assert "preparer unexpectedly authorizes merge" in result["errors"]


def test_watch_chain_reports_complete_unreviewed_packet(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    paths["packet"].mkdir()
    for name in (
        "PREPARATION_RECEIPT.json",
        "REVIEW_LABEL_TEMPLATE.json",
        "CATALOG_SOURCE_SUFFIXES.json",
        "REVIEW_WORKSHEET.html",
    ):
        (paths["packet"] / name).write_text("{}", encoding="utf-8")
    result = _verify(paths)
    assert result["status"] == "VERIFIED_PACKET_READY_NO_SCORING"
    assert result["error_count"] == 0


def _upgrade_fixture_to_v3(paths: dict[str, Path]) -> None:
    pin = json.loads(paths["watcher_pin"].read_text(encoding="utf-8"))
    pin.update(
        {
            "schema": WATCHER_PIN_SCHEMA_V3,
            "closed_source_snapshot_gate": True,
            "open_sources_deferred": True,
        }
    )
    _write(paths["watcher_pin"], pin)
    source = paths["watcher_status"].parent / "closed-rollout.jsonl"
    source.write_text("sealed\n", encoding="utf-8")
    stat = source.stat()
    sources = [
        {
            "path": str(source.resolve()),
            "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "source_session": "session-a",
        }
    ]
    scan = paths["watcher_status"].parent / "scan-004"
    scan.mkdir()
    snapshot = paths["watcher_status"].parent / "scan-004-SOURCE_SNAPSHOT.json"
    _write(
        snapshot,
        {
            "schema": "clay.closed-codex-source-snapshot.v1",
            "sources": sources,
        },
    )
    _write(
        scan / "COLLECTION_REPORT.json",
        {
            "selection": {
                "source_snapshot": {
                    "path": str(snapshot.resolve()),
                    "sha256": sha256_file(snapshot),
                    "source_count": 1,
                }
            }
        },
    )
    status = json.loads(paths["watcher_status"].read_text(encoding="utf-8"))
    status.update(
        {
            "closed_post_freeze_source_count": 1,
            "closed_source_snapshot_sha256": canonical_sha256(sources),
            "deferred_open_source_session_disjoint": True,
            "last_scan": str(scan.resolve()),
        }
    )
    _write(paths["watcher_status"], status)


def test_watch_chain_verifies_v3_closed_source_snapshot(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    _upgrade_fixture_to_v3(paths)
    result = _verify(paths)
    assert result["status"] == "VERIFIED_WAITING_NO_SCORING"
    assert result["error_count"] == 0
    assert result["watcher_pin_schema"] == WATCHER_PIN_SCHEMA_V3
    assert result["closed_source_snapshot"]["verified"] is True
    assert result["closed_source_snapshot"]["source_count"] == 1


def test_watch_chain_rejects_v3_snapshot_fingerprint_drift(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    _upgrade_fixture_to_v3(paths)
    status = json.loads(paths["watcher_status"].read_text(encoding="utf-8"))
    status["closed_source_snapshot_sha256"] = "0" * 64
    _write(paths["watcher_status"], status)
    result = _verify(paths)
    assert result["status"] == "INVALID_WATCH_CHAIN"
    assert "watcher v3 closed-source snapshot fingerprint mismatch" in result["errors"]
