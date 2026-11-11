"""Independently verify the live E92 collection/preparation chain.

This audit never opens session bodies, labels candidates, or runs retrieval. It
checks that the pinned collector, harvester, preparer, frozen catalog, and live
status receipts still form a collection-only path with no scoring artifacts.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Mapping


WATCHER_PIN_SCHEMA = "clay.codex-prospective-watcher-pin.v2"
WATCHER_PIN_SCHEMA_V3 = "clay.codex-prospective-watcher-pin.v3"
WATCHER_PIN_SCHEMAS = (WATCHER_PIN_SCHEMA, WATCHER_PIN_SCHEMA_V3)
WATCHER_STATUS_SCHEMA = "clay.codex-prospective-watcher.v1"
SOURCE_SNAPSHOT_SCHEMA = "clay.closed-codex-source-snapshot.v1"
PREPARER_PIN_SCHEMA = "clay.prime-token-preparer-watcher-pin.v1"
PREPARER_STATUS_SCHEMA = "clay.prime-token-preparer-watcher.v1"
AUDIT_SCHEMA = "scbe.prime-token-watch-chain-audit.v1"
WATCHER_AUTHORITY = "COLLECTION_ONLY_NO_SCORING_NO_TRAINING_NO_PROMOTION"
PREPARER_AUTHORITY = "PREPARE_UNREVIEWED_PACKET_ONLY_NO_LABELS_NO_SCORING_NO_TRAINING_NO_PROMOTION"
FORBIDDEN_PACKET_FILES = ("BENCHMARK.json", "RESULT.json", "RUN_RECEIPT.json")
PACKET_FILES = (
    "PREPARATION_RECEIPT.json",
    "REVIEW_LABEL_TEMPLATE.json",
    "CATALOG_SOURCE_SUFFIXES.json",
    "REVIEW_WORKSHEET.html",
)


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_object(path: Path, *, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def _check_pinned_file(
    errors: list[str],
    pin: Mapping[str, Any],
    *,
    path_field: str,
    hash_field: str,
) -> None:
    raw_path = str(pin.get(path_field) or "")
    expected = str(pin.get(hash_field) or "").casefold()
    path = Path(raw_path)
    if not raw_path or not path.is_file():
        errors.append(f"{path_field} file is missing")
    elif sha256_file(path) != expected:
        errors.append(f"{path_field} hash mismatch")


def _check_no_authority(errors: list[str], status: Mapping[str, Any], *, label: str) -> None:
    if status.get("scoring") != "NOT_AUTHORIZED":
        errors.append(f"{label} unexpectedly authorizes scoring")
    for field in ("training_intake", "promotion"):
        if status.get(field) != "NOT_AUTHORIZED":
            errors.append(f"{label} unexpectedly authorizes {field}")
    for field in ("serving", "merge"):
        if field in status and status.get(field) != "NOT_AUTHORIZED":
            errors.append(f"{label} unexpectedly authorizes {field}")


def _check_v3_closed_snapshot(
    errors: list[str],
    *,
    watcher_pin: Mapping[str, Any],
    watcher_status: Mapping[str, Any],
    watcher_status_file: Path,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "required": True,
        "verified": False,
        "source_count": 0,
        "snapshot_file_sha256": None,
        "snapshot_fingerprint_sha256": None,
    }
    if watcher_pin.get("closed_source_snapshot_gate") is not True:
        errors.append("watcher v3 closed-source snapshot gate is disabled")
    if watcher_pin.get("open_sources_deferred") is not True:
        errors.append("watcher v3 does not defer open sources")
    open_count = int(watcher_status.get("open_post_freeze_source_count", 0))
    if open_count and watcher_status.get("deferred_open_source_session_disjoint") is not True:
        errors.append("watcher v3 open-source deferral is not source-session disjoint")
    closed_count = int(watcher_status.get("closed_post_freeze_source_count", 0))
    evidence["source_count"] = closed_count
    if closed_count == 0:
        evidence["verified"] = True
        return evidence

    raw_scan = str(watcher_status.get("last_scan") or "")
    if not raw_scan:
        errors.append("watcher v3 closed sources have no last_scan authority")
        return evidence
    snapshot_path = watcher_status_file.parent / f"{Path(raw_scan).name}-SOURCE_SNAPSHOT.json"
    if not snapshot_path.is_file():
        errors.append("watcher v3 closed-source snapshot file is missing")
        return evidence
    snapshot = _load_object(snapshot_path, label="closed-source snapshot")
    evidence["snapshot_file_sha256"] = sha256_file(snapshot_path)
    if snapshot.get("schema") != SOURCE_SNAPSHOT_SCHEMA:
        errors.append("watcher v3 closed-source snapshot schema mismatch")
    sources = snapshot.get("sources")
    if not isinstance(sources, list):
        errors.append("watcher v3 closed-source snapshot lacks sources")
        return evidence
    fingerprint = canonical_sha256(sources)
    evidence["snapshot_fingerprint_sha256"] = fingerprint
    if fingerprint != watcher_status.get("closed_source_snapshot_sha256"):
        errors.append("watcher v3 closed-source snapshot fingerprint mismatch")
    if len(sources) != closed_count:
        errors.append("watcher v3 closed-source snapshot count mismatch")
    sessions: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, Mapping):
            errors.append(f"watcher v3 snapshot source {index} is invalid")
            continue
        raw_path = str(source.get("path") or "")
        session = str(source.get("source_session") or "")
        path = Path(raw_path)
        if not raw_path or not path.is_absolute() or not path.is_file():
            errors.append(f"watcher v3 snapshot source {index} is missing")
            continue
        stat = path.stat()
        if int(source.get("bytes", -1)) != stat.st_size:
            errors.append(f"watcher v3 snapshot source {index} size drifted")
        if int(source.get("mtime_ns", -1)) != stat.st_mtime_ns:
            errors.append(f"watcher v3 snapshot source {index} mtime drifted")
        if not session or session in sessions:
            errors.append(f"watcher v3 snapshot source {index} session is invalid")
        sessions.add(session)

    report_path = Path(raw_scan) / "COLLECTION_REPORT.json"
    if not report_path.is_file():
        errors.append("watcher v3 collection report is missing")
    else:
        report = _load_object(report_path, label="collection report")
        selection = report.get("selection")
        authority = selection.get("source_snapshot") if isinstance(selection, Mapping) else None
        if not isinstance(authority, Mapping):
            errors.append("watcher v3 collection report lacks snapshot authority")
        else:
            if Path(str(authority.get("path") or "")).resolve() != snapshot_path.resolve():
                errors.append("watcher v3 collection report snapshot path mismatch")
            if authority.get("sha256") != evidence["snapshot_file_sha256"]:
                errors.append("watcher v3 collection report snapshot hash mismatch")
            if int(authority.get("source_count", -1)) != closed_count:
                errors.append("watcher v3 collection report snapshot count mismatch")
    evidence["verified"] = not any("watcher v3" in error for error in errors)
    return evidence


def verify_watch_chain(
    *,
    watcher_pin_path: str | Path,
    watcher_status_path: str | Path,
    preparer_pin_path: str | Path,
    preparer_status_path: str | Path,
    catalog_database: str | Path,
    packet_output_dir: str | Path,
) -> dict[str, Any]:
    watcher_pin_file = Path(watcher_pin_path).resolve(strict=True)
    watcher_status_file = Path(watcher_status_path).resolve(strict=True)
    preparer_pin_file = Path(preparer_pin_path).resolve(strict=True)
    preparer_status_file = Path(preparer_status_path).resolve(strict=True)
    catalog_file = Path(catalog_database).resolve(strict=True)
    packet_dir = Path(packet_output_dir).resolve()
    watcher_pin = _load_object(watcher_pin_file, label="watcher pin")
    watcher_status = _load_object(watcher_status_file, label="watcher status")
    preparer_pin = _load_object(preparer_pin_file, label="preparer pin")
    preparer_status = _load_object(preparer_status_file, label="preparer status")
    errors: list[str] = []

    watcher_pin_schema = watcher_pin.get("schema")
    if watcher_pin_schema not in WATCHER_PIN_SCHEMAS:
        errors.append("watcher pin schema mismatch")
    if watcher_pin.get("authority") != WATCHER_AUTHORITY:
        errors.append("watcher authority mismatch")
    if watcher_pin.get("source_session_disjoint_gate") is not True:
        errors.append("watcher source-session-disjoint gate is disabled")
    if watcher_status.get("schema") != WATCHER_STATUS_SCHEMA:
        errors.append("watcher status schema mismatch")
    if watcher_status.get("source_session_disjoint") is not True:
        errors.append("watcher status does not prove source-session disjointness")
    _check_no_authority(errors, watcher_status, label="watcher")
    closed_snapshot = {
        "required": False,
        "verified": None,
        "source_count": 0,
        "snapshot_file_sha256": None,
        "snapshot_fingerprint_sha256": None,
    }
    if watcher_pin_schema == WATCHER_PIN_SCHEMA_V3:
        closed_snapshot = _check_v3_closed_snapshot(
            errors,
            watcher_pin=watcher_pin,
            watcher_status=watcher_status,
            watcher_status_file=watcher_status_file,
        )

    if preparer_pin.get("schema") != PREPARER_PIN_SCHEMA:
        errors.append("preparer pin schema mismatch")
    if preparer_pin.get("authority") != PREPARER_AUTHORITY:
        errors.append("preparer authority mismatch")
    if preparer_status.get("schema") != PREPARER_STATUS_SCHEMA:
        errors.append("preparer status schema mismatch")
    _check_no_authority(errors, preparer_status, label="preparer")

    for path_field, hash_field in (
        ("catalog_manifest", "catalog_manifest_sha256"),
        ("collector", "collector_sha256"),
        ("watcher", "watcher_sha256"),
        ("scbe_harvester", "scbe_harvester_sha256"),
    ):
        _check_pinned_file(
            errors,
            watcher_pin,
            path_field=path_field,
            hash_field=hash_field,
        )
    _check_pinned_file(
        errors,
        preparer_pin,
        path_field="preparer",
        hash_field="preparer_sha256",
    )
    _check_pinned_file(
        errors,
        preparer_pin,
        path_field="watcher",
        hash_field="watcher_sha256",
    )

    catalog_hash = sha256_file(catalog_file)
    expected_catalog = str(watcher_pin.get("catalog_sha256") or "").casefold()
    if catalog_hash != expected_catalog:
        errors.append("frozen catalog hash mismatch")
    if str(preparer_pin.get("catalog_sha256") or "").casefold() != expected_catalog:
        errors.append("preparer pin targets another catalog")
    boundary = watcher_status.get("catalog_boundary")
    if not isinstance(boundary, Mapping) or str(boundary.get("catalog_sha256") or "").casefold() != expected_catalog:
        errors.append("watcher status targets another catalog")
    expected_minimum = int(watcher_pin.get("minimum_candidates", -1))
    if expected_minimum < 30:
        errors.append("watcher candidate floor is below 30")
    if int(preparer_pin.get("minimum_candidates", -2)) != expected_minimum:
        errors.append("preparer candidate floor differs from watcher")
    if int(watcher_status.get("minimum_candidates", -3)) != expected_minimum:
        errors.append("watcher status candidate floor drifted")
    if int(preparer_status.get("minimum_candidates", -4)) != expected_minimum:
        errors.append("preparer status candidate floor drifted")

    packet_presence = {name: (packet_dir / name).is_file() for name in PACKET_FILES}
    if any(packet_presence.values()) and not all(packet_presence.values()):
        errors.append("prospective review packet is partially written")
    forbidden_presence = {name: (packet_dir / name).exists() for name in FORBIDDEN_PACKET_FILES}
    if any(forbidden_presence.values()):
        errors.append("collection/preparation directory contains a scoring artifact")

    packet_ready = all(packet_presence.values())
    terminal = (
        "VERIFIED_PACKET_READY_NO_SCORING"
        if packet_ready and not errors
        else ("VERIFIED_WAITING_NO_SCORING" if not errors else "INVALID_WATCH_CHAIN")
    )
    core = {
        "schema": AUDIT_SCHEMA,
        "status": terminal,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "watcher_status": watcher_status.get("status"),
        "watcher_pin_schema": watcher_pin_schema,
        "closed_source_snapshot": closed_snapshot,
        "preparer_status": preparer_status.get("status"),
        "catalog_sha256": catalog_hash,
        "minimum_candidates": expected_minimum,
        "candidate_count": int(watcher_status.get("candidate_count", 0)),
        "open_post_freeze_source_count": int(watcher_status.get("open_post_freeze_source_count", 0)),
        "closed_post_freeze_source_count": int(watcher_status.get("closed_post_freeze_source_count", 0)),
        "packet_files": packet_presence,
        "forbidden_scoring_files": forbidden_presence,
        "watcher_pin_file_sha256": sha256_file(watcher_pin_file),
        "watcher_status_file_sha256": sha256_file(watcher_status_file),
        "preparer_pin_file_sha256": sha256_file(preparer_pin_file),
        "preparer_status_file_sha256": sha256_file(preparer_status_file),
        "error_count": len(errors),
        "errors": errors,
        "scoring": "NOT_AUTHORIZED",
        "training_intake": "NOT_AUTHORIZED",
        "serving": "NOT_AUTHORIZED",
        "merge": "NOT_AUTHORIZED",
        "promotion": "NOT_AUTHORIZED",
    }
    return {**core, "audit_sha256": canonical_sha256(core)}


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(pending, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watcher-pin", required=True, type=Path)
    parser.add_argument("--watcher-status", required=True, type=Path)
    parser.add_argument("--preparer-pin", required=True, type=Path)
    parser.add_argument("--preparer-status", required=True, type=Path)
    parser.add_argument("--catalog-database", required=True, type=Path)
    parser.add_argument("--packet-output-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify_watch_chain(
        watcher_pin_path=args.watcher_pin,
        watcher_status_path=args.watcher_status,
        preparer_pin_path=args.preparer_pin,
        preparer_status_path=args.preparer_status,
        catalog_database=args.catalog_database,
        packet_output_dir=args.packet_output_dir,
    )
    if args.output:
        atomic_json(args.output, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "error_count": result["error_count"],
                "audit_sha256": result["audit_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
