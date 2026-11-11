#!/usr/bin/env python3
"""Fail-closed source-family diversity gate for E92 prospective labels."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

SCHEMA = "clay.e92-source-family-gate.v1"
SOURCE_AUDIT_SCHEMA = "scbe.prime-token-source-family-audit.v1"
INVENTORY_SCHEMA = "clay.prime-token-catalog-source-suffixes.v1"
LABEL_SCHEMA = "scbe.prime-token-independent-review-labels.v1"
LINE_FRAGMENT = re.compile(r"^(?P<path>.+)#L[1-9][0-9]*$")
NOT_AUTHORIZED = "NOT_AUTHORIZED"


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _canonical_path(source_uri: str) -> str:
    match = LINE_FRAGMENT.fullmatch(source_uri)
    raw = match.group("path") if match else source_uri
    return os.path.normcase(str(Path(raw).resolve(strict=False)))


def audit_family_gate(
    *,
    source_family_audit: Path,
    source_inventory: Path,
    labels: Path,
    minimum_accepted_queries: int = 30,
    minimum_canonical_sources: int = 6,
    minimum_families: int = 2,
    maximum_canonical_source_share: float = 0.4,
    maximum_family_share: float = 0.8,
) -> dict[str, Any]:
    audit_path = source_family_audit.resolve(strict=True)
    inventory_path = source_inventory.resolve(strict=True)
    labels_path = labels.resolve(strict=True)
    audit = _object(audit_path, "source-family audit")
    inventory = _object(inventory_path, "source inventory")
    label_set = _object(labels_path, "review labels")
    errors: list[str] = []

    if audit.get("schema") != SOURCE_AUDIT_SCHEMA or int(audit.get("error_count", -1)) != 0:
        errors.append("source-family audit is not verified")
    if inventory.get("schema") != INVENTORY_SCHEMA:
        errors.append("source inventory schema mismatch")
    if label_set.get("schema") != LABEL_SCHEMA:
        errors.append("review label schema mismatch")
    audit_catalog = audit.get("catalog") if isinstance(audit.get("catalog"), dict) else {}
    if (
        str(inventory.get("catalog_sha256") or "").casefold()
        != str(audit_catalog.get("database_sha256") or "").casefold()
    ):
        errors.append("source inventory targets a different catalog")

    canonical_rows = audit.get("canonical_sources")
    canonical_by_path: dict[str, dict[str, Any]] = {}
    if not isinstance(canonical_rows, list):
        errors.append("source-family audit lacks canonical source mappings")
        canonical_rows = []
    for index, row in enumerate(canonical_rows):
        if not isinstance(row, dict) or not row.get("path") or not row.get("family_id"):
            errors.append(f"canonical source row {index} is incomplete")
            continue
        key = _canonical_path(str(row["path"]))
        if key in canonical_by_path:
            errors.append(f"canonical source path is duplicated: {row['path']}")
        canonical_by_path[key] = row

    source_rows = inventory.get("sources")
    inventory_by_suffix: dict[str, dict[str, Any]] = {}
    if not isinstance(source_rows, list) or int(inventory.get("source_count", -1)) != len(source_rows or []):
        errors.append("source inventory count mismatch")
        source_rows = []
    for index, row in enumerate(source_rows):
        if not isinstance(row, dict):
            errors.append(f"source inventory row {index} is not an object")
            continue
        suffix = str(row.get("unique_suffix") or "").strip()
        uri = str(row.get("source_uri") or "").strip()
        if not suffix or not uri or suffix in inventory_by_suffix:
            errors.append(f"source inventory row {index} has missing or duplicate identity")
            continue
        canonical = canonical_by_path.get(_canonical_path(uri))
        if canonical is None:
            errors.append(f"source inventory row is not bound to a canonical source: {uri}")
            continue
        inventory_by_suffix[suffix] = {"source_uri": uri, "canonical": canonical}

    raw_labels = label_set.get("labels")
    if not isinstance(raw_labels, list):
        errors.append("review labels are missing")
        raw_labels = []
    accepted: list[dict[str, Any]] = []
    seen_queries: set[str] = set()
    for index, row in enumerate(raw_labels):
        if not isinstance(row, dict):
            errors.append(f"review label {index} is not an object")
            continue
        query_hash = str(row.get("query_sha256") or "").casefold()
        decision = str(row.get("decision") or "").casefold()
        if len(query_hash) != 64 or query_hash in seen_queries:
            errors.append(f"review label {index} has missing or duplicate query identity")
            continue
        seen_queries.add(query_hash)
        if decision not in {"accept", "reject"}:
            errors.append(f"review label {index} has invalid decision")
            continue
        if decision == "reject":
            continue
        suffix = str(row.get("relevant_source_suffix") or "").strip()
        binding = inventory_by_suffix.get(suffix)
        if binding is None:
            errors.append(f"accepted review label {index} has unknown source suffix")
            continue
        accepted.append(binding)

    canonical_counts = Counter(str(row["canonical"]["path"]) for row in accepted)
    family_counts = Counter(str(row["canonical"]["family_id"]) for row in accepted)
    accepted_count = len(accepted)
    canonical_share = max(canonical_counts.values(), default=0) / max(accepted_count, 1)
    family_share = max(family_counts.values(), default=0) / max(accepted_count, 1)
    gates = {
        "minimum_accepted_queries": accepted_count >= minimum_accepted_queries,
        "minimum_canonical_sources": len(canonical_counts) >= minimum_canonical_sources,
        "minimum_manifest_bound_families": len(family_counts) >= minimum_families,
        "maximum_canonical_source_share": canonical_share <= maximum_canonical_source_share,
        "maximum_family_share": family_share <= maximum_family_share,
    }
    status = "VERIFIED_SOURCE_FAMILY_DIVERSITY"
    if not all(gates.values()):
        status = "SOURCE_FAMILY_DIVERSITY_UNDERPOWERED"
    if errors:
        status = "INVALID_SOURCE_FAMILY_GATE"

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "error_count": len(errors),
        "errors": errors,
        "inputs": {
            "source_family_audit": str(audit_path),
            "source_family_audit_sha256": sha256_file(audit_path),
            "source_inventory": str(inventory_path),
            "source_inventory_sha256": sha256_file(inventory_path),
            "labels": str(labels_path),
            "labels_sha256": sha256_file(labels_path),
        },
        "thresholds": {
            "minimum_accepted_queries": minimum_accepted_queries,
            "minimum_canonical_sources": minimum_canonical_sources,
            "minimum_manifest_bound_families": minimum_families,
            "maximum_canonical_source_share": maximum_canonical_source_share,
            "maximum_family_share": maximum_family_share,
        },
        "observed": {
            "review_label_count": len(raw_labels),
            "accepted_query_count": accepted_count,
            "catalog_row_source_count": len({row["source_uri"] for row in accepted}),
            "canonical_source_count": len(canonical_counts),
            "manifest_bound_family_count": len(family_counts),
            "maximum_canonical_source_share": canonical_share,
            "maximum_family_share": family_share,
            "canonical_source_query_counts": dict(sorted(canonical_counts.items())),
            "family_query_counts": dict(sorted(family_counts.items())),
        },
        "gates": gates,
        "authority": {
            "scoring": NOT_AUTHORIZED,
            "training_intake": NOT_AUTHORIZED,
            "merge": NOT_AUTHORIZED,
            "promotion": NOT_AUTHORIZED,
        },
        "claim_boundary": (
            "Distinct row suffixes and deterministic token views do not establish independent sources. "
            "This gate collapses line fragments to canonical files and then to conservative manifest-bound "
            "families. Passing is evidence of label diversity only and grants no downstream authority."
        ),
    }
    report["report_sha256"] = canonical_sha256(report)
    return report


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(pending, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-family-audit", required=True, type=Path)
    parser.add_argument("--source-inventory", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = audit_family_gate(
        source_family_audit=args.source_family_audit,
        source_inventory=args.source_inventory,
        labels=args.labels,
    )
    atomic_json(args.output, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "error_count": report["error_count"],
                "report_sha256": report["report_sha256"],
            },
            sort_keys=True,
        )
    )
    if report["status"] == "VERIFIED_SOURCE_FAMILY_DIVERSITY":
        return 0
    return 1 if report["error_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
