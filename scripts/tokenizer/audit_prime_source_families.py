#!/usr/bin/env python3
"""Audit canonical source and source-family boundaries in a prime-token catalog."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any

AUDIT_SCHEMA = "scbe.prime-token-source-family-audit.v1"
CATALOG_SCHEMA = "scbe.prime-token-catalog.v1"
SOURCE_MANIFEST_SCHEMA = "scbe.prime-token-source-manifest.v1"
WATCHER_SCHEMA = "clay.codex-prospective-watcher.v1"
LINE_FRAGMENT = re.compile(r"^(?P<path>.+)#L(?P<line>[1-9][0-9]*)$")
NOT_AUTHORIZED = "NOT_AUTHORIZED"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def catalog_source_id(source_hint: str, content_sha256: str) -> str:
    """Reproduce prime_token_catalog.stable_id("source", hint, content hash)."""
    payload = "\x1f".join(("source", source_hint, content_sha256))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _resolve_path(raw: Any, *, relative_to: Path, label: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{label} path is missing")
    path = Path(raw.strip())
    if not path.is_absolute():
        path = relative_to / path
    return path.resolve(strict=True)


def _path_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve(strict=True)))


def _uri_binding(uri: str) -> tuple[Path, int | None]:
    match = LINE_FRAGMENT.fullmatch(uri)
    if match:
        return Path(match.group("path")).resolve(strict=True), int(match.group("line"))
    if "#" in uri:
        raise ValueError(f"unsupported source URI fragment: {uri}")
    return Path(uri).resolve(strict=True), None


def _catalog_database_binding(manifest: dict[str, Any], manifest_path: Path) -> tuple[Path, str]:
    outputs = manifest.get("outputs")
    if not isinstance(outputs, list):
        raise ValueError("catalog outputs are missing")
    matches: list[tuple[Path, str]] = []
    for index, row in enumerate(outputs):
        if not isinstance(row, dict):
            continue
        raw_path = row.get("path")
        if not isinstance(raw_path, str) or Path(raw_path).name != "catalog.sqlite3":
            continue
        path = _resolve_path(raw_path, relative_to=manifest_path.parent, label=f"output {index}")
        digest = str(row.get("sha256") or "").casefold()
        if len(digest) != 64:
            raise ValueError("catalog database binding lacks SHA-256")
        matches.append((path, digest))
    if len(matches) != 1:
        raise ValueError("catalog must bind exactly one catalog.sqlite3")
    return matches[0]


def _conversation_lines(path: Path) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"conversation line {line_number} is not an object")
            text = value.get("text")
            session = value.get("source_session")
            if not isinstance(text, str) or not isinstance(session, str) or not session.strip():
                raise ValueError(f"conversation line {line_number} lacks text/source_session")
            rows[line_number] = value
    return rows


def audit_source_families(
    *,
    catalog_manifest: Path,
    catalog_database: Path,
    watcher_status: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    catalog_manifest = catalog_manifest.resolve(strict=True)
    catalog_database = catalog_database.resolve(strict=True)
    manifest = _load_object(catalog_manifest, "catalog manifest")
    if manifest.get("schema") != CATALOG_SCHEMA:
        errors.append("unexpected catalog manifest schema")

    bound_database: Path | None = None
    bound_database_sha256 = ""
    try:
        bound_database, bound_database_sha256 = _catalog_database_binding(manifest, catalog_manifest)
        if _path_key(bound_database) != _path_key(catalog_database):
            errors.append("catalog database path differs from manifest binding")
        actual_database_sha256 = sha256_file(catalog_database)
        if actual_database_sha256 != bound_database_sha256:
            errors.append("catalog database hash mismatch")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        actual_database_sha256 = sha256_file(catalog_database)
        errors.append(str(exc))

    declarations: dict[str, dict[str, Any]] = {}
    family_rows: list[dict[str, Any]] = []
    family_by_path: dict[str, str] = {}
    conversation_by_path: dict[str, dict[int, dict[str, Any]]] = {}
    bindings = manifest.get("source_manifests")
    if not isinstance(bindings, list):
        bindings = []
        errors.append("catalog source-manifest bindings are missing")
    for binding_index, binding in enumerate(bindings):
        if not isinstance(binding, dict):
            errors.append(f"source-manifest binding {binding_index} is invalid")
            continue
        try:
            source_manifest_path = _resolve_path(
                binding.get("path"),
                relative_to=catalog_manifest.parent,
                label=f"source-manifest binding {binding_index}",
            )
            expected_manifest_sha256 = str(binding.get("sha256") or "").casefold()
            actual_manifest_sha256 = sha256_file(source_manifest_path)
            if actual_manifest_sha256 != expected_manifest_sha256:
                errors.append(f"source manifest {binding_index} hash mismatch")
            source_manifest = _load_object(source_manifest_path, f"source manifest {binding_index}")
            if source_manifest.get("schema") != SOURCE_MANIFEST_SCHEMA:
                errors.append(f"source manifest {binding_index} schema mismatch")
            sources = source_manifest.get("sources")
            if not isinstance(sources, list):
                errors.append(f"source manifest {binding_index} has no sources")
                sources = []
            declared_count = binding.get("declared_sources")
            if int(declared_count) != len(sources):
                errors.append(f"source manifest {binding_index} declared-source count mismatch")
            family_id = hashlib.sha256(f"{source_manifest_path}|{actual_manifest_sha256}".encode("utf-8")).hexdigest()
            family = {
                "family_id": family_id,
                "manifest": str(source_manifest_path),
                "manifest_sha256": actual_manifest_sha256,
                "declared_canonical_sources": len(sources),
                "catalog_source_rows": 0,
                "source_kinds": {},
            }
            family_rows.append(family)
            for source_index, source in enumerate(sources):
                if not isinstance(source, dict):
                    errors.append(f"source manifest {binding_index} source {source_index} is invalid")
                    continue
                source_path = _resolve_path(
                    source.get("path"),
                    relative_to=source_manifest_path.parent,
                    label=f"source manifest {binding_index} source {source_index}",
                )
                key = _path_key(source_path)
                if key in declarations:
                    errors.append(f"canonical source is declared by multiple manifests: {source_path}")
                    continue
                expected_sha256 = str(source.get("sha256") or "").casefold()
                actual_sha256 = sha256_file(source_path)
                if actual_sha256 != expected_sha256:
                    errors.append(f"declared canonical source hash mismatch: {source_path}")
                source_kind = str(source.get("source_kind") or "")
                license_name = str(source.get("license") or "")
                declarations[key] = {
                    "path": source_path,
                    "family_id": family_id,
                    "source_kind": source_kind,
                    "license_name": license_name,
                    "sha256": actual_sha256,
                }
                family_by_path[key] = family_id
                if source_kind.casefold() == "conversation":
                    conversation_by_path[key] = _conversation_lines(source_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))

    seen_canonical_sources: set[str] = set()
    seen_conversation_lines: dict[str, set[int]] = defaultdict(set)
    source_kind_counts: Counter[str] = Counter()
    family_source_rows: Counter[str] = Counter()
    family_kind_rows: dict[str, Counter[str]] = defaultdict(Counter)
    conversation_sessions: set[str] = set()
    database_rows = 0
    try:
        connection = sqlite3.connect(f"file:{catalog_database.as_posix()}?mode=ro", uri=True)
        try:
            rows = connection.execute(
                "SELECT source_id, source_uri, source_kind, license_name, content_sha256, byte_count "
                "FROM sources ORDER BY source_uri"
            )
            for source_id, source_uri, source_kind, license_name, content_sha256, byte_count in rows:
                database_rows += 1
                try:
                    source_path, line_number = _uri_binding(str(source_uri))
                except (OSError, ValueError) as exc:
                    errors.append(str(exc))
                    continue
                key = _path_key(source_path)
                declaration = declarations.get(key)
                if declaration is None:
                    errors.append(f"catalog source is not declared by a bound manifest: {source_uri}")
                    continue
                seen_canonical_sources.add(key)
                family_id = family_by_path[key]
                source_kind_counts[str(source_kind)] += 1
                family_source_rows[family_id] += 1
                family_kind_rows[family_id][str(source_kind)] += 1
                if str(source_kind) != declaration["source_kind"]:
                    errors.append(f"source kind mismatch: {source_uri}")
                if str(license_name) != declaration["license_name"]:
                    errors.append(f"source license mismatch: {source_uri}")
                if line_number is None:
                    if str(content_sha256) != declaration["sha256"]:
                        errors.append(f"source content hash mismatch: {source_uri}")
                    if int(byte_count) != source_path.stat().st_size:
                        errors.append(f"source byte count mismatch: {source_uri}")
                    expected_source_id = catalog_source_id(str(source_uri), str(content_sha256))
                    if str(source_id) != expected_source_id:
                        errors.append(f"source identity mismatch: {source_uri}")
                    continue
                lines = conversation_by_path.get(key)
                if lines is None:
                    errors.append(f"line fragment is not bound to a conversation source: {source_uri}")
                    continue
                row = lines.get(line_number)
                if row is None:
                    errors.append(f"conversation fragment line is missing: {source_uri}")
                    continue
                if line_number in seen_conversation_lines[key]:
                    errors.append(f"conversation fragment line is duplicated: {source_uri}")
                seen_conversation_lines[key].add(line_number)
                text = row["text"]
                expected_text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
                if str(content_sha256) != expected_text_sha256:
                    errors.append(f"conversation text hash mismatch: {source_uri}")
                if int(byte_count) != len(text.encode("utf-8")):
                    errors.append(f"conversation text byte count mismatch: {source_uri}")
                conversation_sessions.add(str(row["source_session"]))
                expected_source_id = catalog_source_id(str(source_uri), str(content_sha256))
                if str(source_id) != expected_source_id:
                    errors.append(f"conversation source identity mismatch: {source_uri}")
        finally:
            connection.close()
    except sqlite3.Error as exc:
        errors.append(f"catalog database read failed: {exc}")

    missing_sources = sorted(set(declarations) - seen_canonical_sources)
    if missing_sources:
        errors.append(f"{len(missing_sources)} declared canonical sources are absent from the catalog")
    for key, lines in conversation_by_path.items():
        if set(lines) != seen_conversation_lines.get(key, set()):
            errors.append(f"conversation source does not map one-to-one onto catalog rows: {declarations[key]['path']}")

    family_index = {row["family_id"]: row for row in family_rows}
    for family_id, count in family_source_rows.items():
        family_index[family_id]["catalog_source_rows"] = count
        family_index[family_id]["source_kinds"] = dict(sorted(family_kind_rows[family_id].items()))

    if int(manifest.get("source_count", -1)) != database_rows:
        errors.append("catalog manifest source_count differs from database rows")

    prospective: dict[str, Any] | None = None
    if watcher_status is not None:
        watcher_status = watcher_status.resolve(strict=True)
        watcher = _load_object(watcher_status, "watcher status")
        if watcher.get("schema") != WATCHER_SCHEMA:
            errors.append("unexpected prospective watcher schema")
        boundary = watcher.get("catalog_boundary")
        if not isinstance(boundary, dict):
            errors.append("prospective watcher catalog boundary is missing")
            boundary = {}
        if str(boundary.get("catalog_sha256") or "") != actual_database_sha256:
            errors.append("prospective watcher catalog hash mismatch")
        if str(boundary.get("manifest_sha256") or "") != sha256_file(catalog_manifest):
            errors.append("prospective watcher manifest hash mismatch")
        conversation_boundary = watcher.get("catalog_conversation_boundary")
        if not isinstance(conversation_boundary, dict):
            errors.append("prospective watcher conversation boundary is missing")
            conversation_boundary = {}
        expected_conversation_rows = source_kind_counts.get("conversation", 0)
        expected_conversation_sources = len(conversation_by_path)
        expected_source_manifests = len(family_rows)
        expected_conversation_sessions = len(conversation_sessions)
        expected_counts = {
            "conversation_rows": expected_conversation_rows,
            "conversation_sources": expected_conversation_sources,
            "source_manifests": expected_source_manifests,
            "conversation_sessions": expected_conversation_sessions,
        }
        for key, expected in expected_counts.items():
            if int(conversation_boundary.get(key, -1)) != expected:
                errors.append(f"prospective watcher {key} mismatch")
        if watcher.get("source_session_disjoint") is not True:
            errors.append("prospective closed-source session boundary is not disjoint")
        if watcher.get("deferred_open_source_session_disjoint") is not True:
            errors.append("prospective open-source session boundary is not disjoint")
        for authority in ("scoring", "training_intake", "promotion"):
            if watcher.get(authority) != NOT_AUTHORIZED:
                errors.append(f"prospective watcher unexpectedly authorizes {authority}")
        prospective = {
            "status": watcher.get("status"),
            "closed_post_freeze_source_count": int(watcher.get("closed_post_freeze_source_count", 0)),
            "open_post_freeze_source_count": int(watcher.get("open_post_freeze_source_count", 0)),
            "source_session_disjoint": watcher.get("source_session_disjoint") is True,
            "deferred_open_source_session_disjoint": watcher.get("deferred_open_source_session_disjoint") is True,
            "evaluation_ready": int(watcher.get("closed_post_freeze_source_count", 0)) > 0,
            "scoring": watcher.get("scoring"),
            "training_intake": watcher.get("training_intake"),
            "promotion": watcher.get("promotion"),
            "watcher_status_path": str(watcher_status),
            "watcher_status_sha256": sha256_file(watcher_status),
        }

    status = "VERIFIED_SOURCE_FAMILY_BOUNDARY"
    if prospective and not prospective["evaluation_ready"]:
        status = "VERIFIED_SOURCE_FAMILY_BOUNDARY_WAITING"
    if errors:
        status = "INVALID_SOURCE_FAMILY_BOUNDARY"
    report: dict[str, Any] = {
        "schema": AUDIT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "error_count": len(errors),
        "errors": errors,
        "catalog": {
            "manifest": str(catalog_manifest),
            "manifest_sha256": sha256_file(catalog_manifest),
            "database": str(catalog_database),
            "database_sha256": actual_database_sha256,
        },
        "counts": {
            "catalog_source_rows": database_rows,
            "canonical_sources": len(seen_canonical_sources),
            "manifest_bound_source_families": len(family_rows),
            "conversation_source_rows": source_kind_counts.get("conversation", 0),
            "conversation_canonical_sources": len(conversation_by_path),
            "conversation_source_sessions": len(conversation_sessions),
            "source_kinds": dict(sorted(source_kind_counts.items())),
        },
        "families": sorted(family_rows, key=lambda row: row["manifest"]),
        "prospective": prospective,
        "authority": {
            "scoring": NOT_AUTHORIZED,
            "training_intake": NOT_AUTHORIZED,
            "merge": NOT_AUTHORIZED,
            "promotion": NOT_AUTHORIZED,
        },
        "claim_boundary": (
            "Manifest bindings are conservative source-family units for split accounting. "
            "They do not prove independent authorship. Deterministic token views and line "
            "fragments remain correlated representations of one canonical source."
        ),
    }
    report["audit_sha256"] = canonical_sha256(report)
    return report


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(pending, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-manifest", required=True, type=Path)
    parser.add_argument("--catalog-database", required=True, type=Path)
    parser.add_argument("--watcher-status", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = audit_source_families(
        catalog_manifest=args.catalog_manifest,
        catalog_database=args.catalog_database,
        watcher_status=args.watcher_status,
    )
    atomic_json(args.output, report)
    print(json.dumps({key: report[key] for key in ("status", "error_count", "audit_sha256")}, sort_keys=True))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
