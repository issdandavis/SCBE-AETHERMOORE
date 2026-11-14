"""Audit query-session/target-family components for prime-token evaluation.

This module creates evaluator metadata only.  It never emits query text, opens
model weights, scores an arm, admits training data, or grants promotion.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from python.scbe.prime_token_query_harvest import review_queue_sha256

SCHEMA = "scbe.prime-token-query-session-family-components.v1"
REVIEW_QUEUE_SCHEMA = "scbe.prime-token-independent-review-queue.v1"
REVIEW_LABEL_SCHEMA = "scbe.prime-token-independent-review-labels.v1"
SOURCE_INVENTORY_SCHEMA = "clay.prime-token-catalog-source-suffixes.v1"
SOURCE_FAMILY_AUDIT_SCHEMA = "scbe.prime-token-source-family-audit.v1"
STATUS_VERIFIED = "VERIFIED_QUERY_SESSION_FAMILY_COMPONENT_SPLIT"
STATUS_UNDERPOWERED = "QUERY_SESSION_FAMILY_SPLIT_UNDERPOWERED"
STATUS_INVALID = "INVALID_QUERY_SESSION_FAMILY_SPLIT"
HEX64 = re.compile(r"[0-9a-f]{64}")
LINE_FRAGMENT = re.compile(r"^(?P<path>.+)#L[1-9][0-9]*$")
AUTHORITY = {
    "scoring": "NOT_AUTHORIZED",
    "training_intake": "NOT_AUTHORIZED",
    "execution": "NONE",
    "merge": "NOT_AUTHORIZED",
    "promotion": "NOT_AUTHORIZED",
    "partial_unfreeze": "NONE",
}


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
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


def _session_hash(session_id: str) -> str:
    return hashlib.sha256(f"query-session\0{session_id}".encode("utf-8")).hexdigest()


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, value: str) -> None:
        self.parent.setdefault(value, value)

    def find(self, value: str) -> str:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        self.add(left)
        self.add(right)
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        low, high = sorted((left_root, right_root))
        self.parent[high] = low


def _validate_thresholds(
    *,
    minimum_accepted_queries: int,
    minimum_sessions: int,
    minimum_families: int,
    maximum_component_share: float,
    fold_names: Sequence[str],
) -> tuple[str, ...]:
    if min(minimum_accepted_queries, minimum_sessions, minimum_families) < 1:
        raise ValueError("minimum thresholds must be positive")
    if not 0.0 < maximum_component_share <= 1.0:
        raise ValueError("maximum_component_share must be in (0, 1]")
    names = tuple(str(value).strip() for value in fold_names)
    if len(names) < 2 or not all(names) or len(set(names)) != len(names):
        raise ValueError("at least two unique non-empty fold names are required")
    return names


def _component_records(entries: Sequence[Mapping[str, str]]) -> list[dict[str, Any]]:
    union = _UnionFind()
    for row in entries:
        union.union(f"session:{row['session_hash']}", f"family:{row['family_id']}")

    by_root: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in entries:
        root = union.find(f"session:{row['session_hash']}")
        by_root[root].append(row)

    components = []
    for rows in by_root.values():
        sessions = sorted({row["session_hash"] for row in rows})
        families = sorted({row["family_id"] for row in rows})
        query_hashes = sorted(row["query_sha256"] for row in rows)
        strata = Counter(row["review_stratum"] for row in rows)
        identity = {"session_hashes": sessions, "family_ids": families}
        components.append(
            {
                "component_id": canonical_sha256(identity),
                "query_count": len(rows),
                "query_sha256": query_hashes,
                "query_digest_sha256": canonical_sha256(query_hashes),
                "session_count": len(sessions),
                "session_hashes": sessions,
                "family_count": len(families),
                "family_ids": families,
                "review_strata_counts": dict(sorted(strata.items())),
            }
        )
    return sorted(
        components, key=lambda row: (-row["query_count"], row["component_id"])
    )


def _assign_folds(
    components: Sequence[Mapping[str, Any]], fold_names: Sequence[str]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    loads = {
        name: {
            "query_count": 0,
            "component_count": 0,
            "component_ids": [],
            "query_sha256": [],
            "session_hashes": set(),
            "family_ids": set(),
            "review_strata_counts": Counter(),
        }
        for name in fold_names
    }
    assigned = []
    for original in components:
        fold = min(
            fold_names,
            key=lambda name: (
                loads[name]["query_count"],
                loads[name]["component_count"],
                name,
            ),
        )
        row = {**original, "fold": fold}
        assigned.append(row)
        load = loads[fold]
        load["query_count"] += int(row["query_count"])
        load["component_count"] += 1
        load["component_ids"].append(row["component_id"])
        load["query_sha256"].extend(row["query_sha256"])
        load["session_hashes"].update(row["session_hashes"])
        load["family_ids"].update(row["family_ids"])
        load["review_strata_counts"].update(row["review_strata_counts"])

    sealed_loads: dict[str, dict[str, Any]] = {}
    for name in fold_names:
        load = loads[name]
        sealed_loads[name] = {
            "query_count": load["query_count"],
            "component_count": load["component_count"],
            "component_ids": sorted(load["component_ids"]),
            "query_sha256": sorted(load["query_sha256"]),
            "query_digest_sha256": canonical_sha256(sorted(load["query_sha256"])),
            "session_count": len(load["session_hashes"]),
            "session_hashes": sorted(load["session_hashes"]),
            "family_count": len(load["family_ids"]),
            "family_ids": sorted(load["family_ids"]),
            "review_strata_counts": dict(sorted(load["review_strata_counts"].items())),
        }
    return sorted(assigned, key=lambda row: row["component_id"]), sealed_loads


def _overlap_counts(folds: Mapping[str, Mapping[str, Any]]) -> tuple[int, int]:
    sessions: dict[str, set[str]] = defaultdict(set)
    families: dict[str, set[str]] = defaultdict(set)
    for fold, row in folds.items():
        for session_hash in row["session_hashes"]:
            sessions[session_hash].add(fold)
        for family_id in row["family_ids"]:
            families[family_id].add(fold)
    return (
        sum(len(names) > 1 for names in sessions.values()),
        sum(len(names) > 1 for names in families.values()),
    )


def audit_query_session_family_components(
    *,
    review_queue: str | Path,
    review_labels: str | Path,
    source_inventory: str | Path,
    source_family_audit: str | Path,
    fold_names: Sequence[str] = ("fold-0", "fold-1", "fold-2"),
    minimum_accepted_queries: int = 30,
    minimum_sessions: int = 3,
    minimum_families: int = 2,
    maximum_component_share: float = 0.8,
) -> dict[str, Any]:
    """Build and audit indivisible query-session/target-family components."""

    folds_requested = _validate_thresholds(
        minimum_accepted_queries=minimum_accepted_queries,
        minimum_sessions=minimum_sessions,
        minimum_families=minimum_families,
        maximum_component_share=maximum_component_share,
        fold_names=fold_names,
    )
    queue_path = Path(review_queue).resolve(strict=True)
    labels_path = Path(review_labels).resolve(strict=True)
    inventory_path = Path(source_inventory).resolve(strict=True)
    family_path = Path(source_family_audit).resolve(strict=True)
    queue = _object(queue_path, "review queue")
    labels = _object(labels_path, "review labels")
    inventory = _object(inventory_path, "source inventory")
    family_audit = _object(family_path, "source-family audit")
    errors: list[str] = []

    queue_hash = ""
    if queue.get("schema") != REVIEW_QUEUE_SCHEMA:
        errors.append("review queue schema mismatch")
    else:
        try:
            queue_hash = review_queue_sha256(queue)
            if str(queue.get("queue_sha256") or "").casefold() != queue_hash:
                errors.append("review queue content hash mismatch")
        except (KeyError, TypeError, ValueError) as error:
            errors.append(f"review queue hash cannot be replayed: {error}")
    if labels.get("schema") != REVIEW_LABEL_SCHEMA:
        errors.append("review label schema mismatch")
    if queue_hash and str(labels.get("queue_sha256") or "").casefold() != queue_hash:
        errors.append("review labels target a different queue")
    if inventory.get("schema") != SOURCE_INVENTORY_SCHEMA:
        errors.append("source inventory schema mismatch")
    if (
        family_audit.get("schema") != SOURCE_FAMILY_AUDIT_SCHEMA
        or int(family_audit.get("error_count", -1)) != 0
    ):
        errors.append("source-family audit is not verified")
    family_catalog = (
        family_audit.get("catalog")
        if isinstance(family_audit.get("catalog"), Mapping)
        else {}
    )
    if (
        str(inventory.get("catalog_sha256") or "").casefold()
        != str(family_catalog.get("database_sha256") or "").casefold()
    ):
        errors.append("source inventory targets a different catalog")

    candidates_raw = queue.get("candidates")
    if not isinstance(candidates_raw, list) or int(
        queue.get("candidate_count", -1)
    ) != len(candidates_raw or []):
        errors.append("review queue candidate count mismatch")
        candidates_raw = []
    candidate_by_hash: dict[str, dict[str, Any]] = {}
    candidate_ids: set[str] = set()
    candidate_sessions: set[str] = set()
    for index, row in enumerate(candidates_raw):
        if not isinstance(row, Mapping):
            errors.append(f"review candidate {index} is not an object")
            continue
        candidate_id = str(row.get("candidate_id") or "").strip()
        query_hash = str(row.get("query_sha256") or "").strip().casefold()
        query = row.get("query")
        session_id = str(row.get("session_id") or "").strip()
        if not candidate_id or candidate_id in candidate_ids:
            errors.append(f"review candidate {index} has missing or duplicate identity")
            continue
        if not HEX64.fullmatch(query_hash) or query_hash in candidate_by_hash:
            errors.append(
                f"review candidate {index} has missing or duplicate query hash"
            )
            continue
        if (
            not isinstance(query, str)
            or hashlib.sha256(query.encode("utf-8")).hexdigest() != query_hash
        ):
            errors.append(f"review candidate {index} query hash mismatch")
            continue
        if not session_id:
            errors.append(f"review candidate {index} has no source session")
            continue
        candidate_ids.add(candidate_id)
        candidate_sessions.add(session_id)
        candidate_by_hash[query_hash] = dict(row)
    declared_sessions = queue.get("session_ids")
    if (
        not isinstance(declared_sessions, list)
        or {str(value) for value in declared_sessions} != candidate_sessions
    ):
        errors.append("review queue session index does not match candidates")

    canonical_rows = family_audit.get("canonical_sources")
    canonical_by_path: dict[str, dict[str, Any]] = {}
    if not isinstance(canonical_rows, list):
        errors.append("source-family audit lacks canonical source mappings")
        canonical_rows = []
    for index, row in enumerate(canonical_rows):
        if (
            not isinstance(row, Mapping)
            or not row.get("path")
            or not row.get("family_id")
        ):
            errors.append(f"canonical source row {index} is incomplete")
            continue
        key = _canonical_path(str(row["path"]))
        if key in canonical_by_path:
            errors.append(f"canonical source path is duplicated: {row['path']}")
        canonical_by_path[key] = dict(row)

    source_rows = inventory.get("sources")
    inventory_by_suffix: dict[str, dict[str, str]] = {}
    if not isinstance(source_rows, list) or int(
        inventory.get("source_count", -1)
    ) != len(source_rows or []):
        errors.append("source inventory count mismatch")
        source_rows = []
    for index, row in enumerate(source_rows):
        if not isinstance(row, Mapping):
            errors.append(f"source inventory row {index} is not an object")
            continue
        suffix = str(row.get("unique_suffix") or "").strip()
        uri = str(row.get("source_uri") or "").strip()
        if not suffix or not uri or suffix in inventory_by_suffix:
            errors.append(
                f"source inventory row {index} has missing or duplicate identity"
            )
            continue
        canonical = canonical_by_path.get(_canonical_path(uri))
        if canonical is None:
            errors.append(
                f"source inventory row is not bound to a canonical source: {uri}"
            )
            continue
        inventory_by_suffix[suffix] = {
            "family_id": str(canonical["family_id"]),
            "canonical_source_sha256": hashlib.sha256(
                str(canonical["path"]).encode("utf-8")
            ).hexdigest(),
        }

    labels_raw = labels.get("labels")
    if not isinstance(labels_raw, list):
        errors.append("review labels are missing")
        labels_raw = []
    decisions: dict[str, dict[str, Any]] = {}
    accepted_entries: list[dict[str, str]] = []
    for index, row in enumerate(labels_raw):
        if not isinstance(row, Mapping):
            errors.append(f"review label {index} is not an object")
            continue
        query_hash = str(row.get("query_sha256") or "").strip().casefold()
        decision = str(row.get("decision") or "").strip().casefold()
        if query_hash not in candidate_by_hash or query_hash in decisions:
            errors.append(
                f"review label {index} has unknown or duplicate query identity"
            )
            continue
        if decision not in {"accept", "reject"}:
            errors.append(f"review label {index} has invalid decision")
            continue
        decisions[query_hash] = dict(row)
        if decision == "reject":
            continue
        suffix = str(row.get("relevant_source_suffix") or "").strip()
        binding = inventory_by_suffix.get(suffix)
        if binding is None:
            errors.append(f"accepted review label {index} has unknown source suffix")
            continue
        stratum = str(row.get("review_stratum") or "").strip()
        if not stratum:
            errors.append(f"accepted review label {index} has no review stratum")
            continue
        candidate = candidate_by_hash[query_hash]
        session_id = str(candidate["session_id"])
        accepted_entries.append(
            {
                "query_sha256": query_hash,
                "session_hash": _session_hash(session_id),
                "family_id": binding["family_id"],
                "canonical_source_sha256": binding["canonical_source_sha256"],
                "review_stratum": stratum,
            }
        )
    if set(decisions) != set(candidate_by_hash):
        errors.append("every review candidate requires exactly one decision")

    components = _component_records(accepted_entries)
    assigned, folds = _assign_folds(components, folds_requested)
    session_overlap, family_overlap = _overlap_counts(folds)
    accepted_count = len(accepted_entries)
    session_count = len({row["session_hash"] for row in accepted_entries})
    family_count = len({row["family_id"] for row in accepted_entries})
    component_count = len(components)
    maximum_observed_share = (
        max((row["query_count"] for row in components), default=0) / accepted_count
        if accepted_count
        else 0.0
    )
    gates = {
        "minimum_accepted_queries": accepted_count >= minimum_accepted_queries,
        "minimum_query_sessions": session_count >= minimum_sessions,
        "minimum_manifest_bound_families": family_count >= minimum_families,
        "minimum_indivisible_components": component_count >= len(folds_requested),
        "all_folds_nonempty": all(
            folds[name]["query_count"] > 0 for name in folds_requested
        ),
        "maximum_component_share": maximum_observed_share <= maximum_component_share,
        "zero_query_session_overlap": session_overlap == 0,
        "zero_target_family_overlap": family_overlap == 0,
    }
    status = STATUS_VERIFIED if all(gates.values()) else STATUS_UNDERPOWERED
    if errors:
        status = STATUS_INVALID

    split_payload = {
        "fold_names": list(folds_requested),
        "components": assigned,
        "folds": folds,
    }
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "error_count": len(errors),
        "errors": errors,
        "inputs": {
            "review_queue": str(queue_path),
            "review_queue_sha256": sha256_file(queue_path),
            "review_queue_content_sha256": queue_hash or None,
            "review_labels": str(labels_path),
            "review_labels_sha256": sha256_file(labels_path),
            "source_inventory": str(inventory_path),
            "source_inventory_sha256": sha256_file(inventory_path),
            "source_family_audit": str(family_path),
            "source_family_audit_sha256": sha256_file(family_path),
        },
        "thresholds": {
            "minimum_accepted_queries": minimum_accepted_queries,
            "minimum_query_sessions": minimum_sessions,
            "minimum_manifest_bound_families": minimum_families,
            "minimum_indivisible_components": len(folds_requested),
            "maximum_component_share": maximum_component_share,
        },
        "observed": {
            "review_candidate_count": len(candidate_by_hash),
            "review_decision_count": len(decisions),
            "accepted_query_count": accepted_count,
            "rejected_query_count": len(decisions) - accepted_count,
            "query_session_count": session_count,
            "target_family_count": family_count,
            "indivisible_component_count": component_count,
            "maximum_component_share": maximum_observed_share,
            "query_session_overlap_count": session_overlap,
            "target_family_overlap_count": family_overlap,
        },
        **split_payload,
        "component_split_sha256": canonical_sha256(split_payload),
        "gates": gates,
        "authority": AUTHORITY,
        "claim_boundary": (
            "This is evaluator metadata only. Components keep query sessions and target families "
            "indivisible; target labels never enter a model query packet. A passing receipt does "
            "not authorize scoring, training, execution, merging, promotion, or partial unfreeze."
        ),
    }
    report["report_sha256"] = canonical_sha256(report)
    return report


def write_json_exclusive(path: str | Path, payload: Mapping[str, Any]) -> None:
    output = Path(path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        handle.write("\n")
