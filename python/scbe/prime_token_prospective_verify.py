"""Independent aggregate verifier for a completed E92 prospective bundle."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
from statistics import mean, stdev
from typing import Any

E92_RUN_SCHEMA = "scbe.e92-prospective-run.v5"
BENCHMARK_SCHEMA = "scbe.prime-token-benchmark.v1"
RESULT_SCHEMA = "scbe.prime-token-cascade-benchmark-result.v1"
REVIEW_QUEUE_SCHEMA = "scbe.prime-token-independent-review-queue.v1"
REVIEW_LABEL_SCHEMA = "scbe.prime-token-independent-review-labels.v1"
PREPARATION_SCHEMA = "clay.prime-token-prospective-review-preparation.v1"
SOURCE_INVENTORY_SCHEMA = "clay.prime-token-catalog-source-suffixes.v1"
CATALOG_INTEGRITY_SCHEMA = "scbe.prime-token-relational-integrity-audit.v1"
SELECTION_AUDIT_SCHEMA = "clay.prime-token-selection-audit.v1"
SELECTION_AUDIT_STATUS = "PASS_EXACT_SELECTION_REPLAY_NO_SCORING"
COMPONENT_REPORT_SCHEMA = "scbe.prime-token-query-session-family-components.v1"
SOURCE_FAMILY_AUDIT_SCHEMA = "scbe.prime-token-source-family-audit.v1"
COMPONENT_REPORT_VERIFIED = "VERIFIED_QUERY_SESSION_FAMILY_COMPONENT_SPLIT"
ALGORITHM_REVISION = "six-view-late-output-fusion-v1"
MIN_CAPABILITY_QUERIES = 30
DEFAULT_CONTROL_SEEDS = (11, 29, 47)
EXPECTED_ARMS = {
    "late_output_fused",
    "route_null",
    "explicit_routed",
    "lexical_only",
    "no_intervention",
    "shuffled_binding",
    "random_rank_fusion",
}
SOURCE_CHAIN_BUNDLE_FILES = {
    "queue": "SOURCE_QUEUE.json",
    "selection_audit": "SOURCE_SELECTION_AUDIT.json",
    "labels": "SOURCE_LABELS.json",
    "preparation_receipt": "SOURCE_PREPARATION_RECEIPT.json",
    "source_inventory": "SOURCE_INVENTORY.json",
    "catalog_integrity": "SOURCE_CATALOG_INTEGRITY.json",
    "component_report": "SOURCE_QUERY_SESSION_FAMILY_COMPONENTS.json",
    "source_family_audit": "SOURCE_FAMILY_AUDIT.json",
}
SOURCE_HASH_FIELDS = {
    "queue": "queue_file_sha256",
    "selection_audit": "selection_audit_file_sha256",
    "labels": "labels_file_sha256",
    "preparation_receipt": "preparation_receipt_file_sha256",
    "source_inventory": "source_inventory_file_sha256",
    "catalog_integrity": "catalog_integrity_file_sha256",
    "component_report": "component_report_file_sha256",
    "source_family_audit": "source_family_audit_file_sha256",
}
COMPONENT_FOLD_NAMES = ("fold-0", "fold-1", "fold-2")
COMPONENT_THRESHOLDS = {
    "minimum_accepted_queries": 30,
    "minimum_query_sessions": 3,
    "minimum_manifest_bound_families": 2,
    "minimum_indivisible_components": 3,
    "maximum_component_share": 0.8,
}
COMPONENT_AUTHORITY = {
    "scoring": "NOT_AUTHORIZED",
    "training_intake": "NOT_AUTHORIZED",
    "execution": "NONE",
    "merge": "NOT_AUTHORIZED",
    "promotion": "NOT_AUTHORIZED",
    "partial_unfreeze": "NONE",
}
LINE_FRAGMENT = re.compile(r"^(?P<path>.+)#L[1-9][0-9]*$")


def _canonical_sha256(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _review_queue_sha256(queue: Mapping[str, Any]) -> str:
    payload = dict(queue)
    payload.pop("queue_sha256", None)
    return _canonical_sha256(payload)


def _component_sha256(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    ).hexdigest()


def _component_forbidden_keys(value: Any, *, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{path}.{key}"
            if str(key) in {"query", "session_id"}:
                found.append(child)
            found.extend(_component_forbidden_keys(item, path=child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_component_forbidden_keys(item, path=f"{path}[{index}]"))
    return found


def _component_source_path(source_uri: str) -> str:
    match = LINE_FRAGMENT.fullmatch(source_uri)
    raw = match.group("path") if match else source_uri
    return os.path.normcase(str(Path(raw).resolve(strict=False)))


def _component_session_hash(session_id: str) -> str:
    return sha256(f"query-session\0{session_id}".encode("utf-8")).hexdigest()


class _ComponentUnionFind:
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


def _rebuild_component_split(entries: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    union = _ComponentUnionFind()
    for row in entries:
        union.union(f"session:{row['session_hash']}", f"family:{row['family_id']}")

    by_root: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in entries:
        by_root[union.find(f"session:{row['session_hash']}")].append(row)

    components = []
    for rows in by_root.values():
        sessions = sorted({row["session_hash"] for row in rows})
        families = sorted({row["family_id"] for row in rows})
        query_hashes = sorted(row["query_sha256"] for row in rows)
        strata = Counter(row["review_stratum"] for row in rows)
        components.append(
            {
                "component_id": _component_sha256(
                    {"session_hashes": sessions, "family_ids": families}
                ),
                "query_count": len(rows),
                "query_sha256": query_hashes,
                "query_digest_sha256": _component_sha256(query_hashes),
                "session_count": len(sessions),
                "session_hashes": sessions,
                "family_count": len(families),
                "family_ids": families,
                "review_strata_counts": dict(sorted(strata.items())),
            }
        )
    components.sort(key=lambda row: (-row["query_count"], row["component_id"]))

    loads: dict[str, dict[str, Any]] = {
        name: {
            "query_count": 0,
            "component_count": 0,
            "component_ids": [],
            "query_sha256": [],
            "session_hashes": set(),
            "family_ids": set(),
            "review_strata_counts": Counter(),
        }
        for name in COMPONENT_FOLD_NAMES
    }
    assigned = []
    for original in components:
        fold = min(
            COMPONENT_FOLD_NAMES,
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

    folds = {}
    for name in COMPONENT_FOLD_NAMES:
        load = loads[name]
        queries = sorted(load["query_sha256"])
        folds[name] = {
            "query_count": load["query_count"],
            "component_count": load["component_count"],
            "component_ids": sorted(load["component_ids"]),
            "query_sha256": queries,
            "query_digest_sha256": _component_sha256(queries),
            "session_count": len(load["session_hashes"]),
            "session_hashes": sorted(load["session_hashes"]),
            "family_count": len(load["family_ids"]),
            "family_ids": sorted(load["family_ids"]),
            "review_strata_counts": dict(sorted(load["review_strata_counts"].items())),
        }
    return {
        "fold_names": list(COMPONENT_FOLD_NAMES),
        "components": sorted(assigned, key=lambda row: row["component_id"]),
        "folds": folds,
    }


def _load_source_chain(
    root: Path,
    receipt: Mapping[str, Any],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    declaration = receipt.get("source_chain_bundle")
    if not isinstance(declaration, Mapping) or set(declaration) != set(
        SOURCE_CHAIN_BUNDLE_FILES
    ):
        errors.append("source-chain bundle declaration mismatch")
        return {}
    loaded: dict[str, dict[str, Any]] = {}
    for role, expected_name in SOURCE_CHAIN_BUNDLE_FILES.items():
        item = declaration.get(role)
        if not isinstance(item, Mapping) or set(item) != {
            "file",
            "sha256",
            "source_file_sha256",
        }:
            errors.append(f"source-chain {role} declaration mismatch")
            continue
        if item.get("file") != expected_name:
            errors.append(f"source-chain {role} filename mismatch")
            continue
        path = root / expected_name
        if not path.is_file():
            errors.append(f"source-chain {role} file missing")
            continue
        if _sha256_file(path) != item.get("sha256"):
            errors.append(f"source-chain {role} bundled file hash mismatch")
            continue
        if item.get("source_file_sha256") != receipt.get(SOURCE_HASH_FIELDS[role]):
            errors.append(f"source-chain {role} source file hash mismatch")
        try:
            loaded[role] = _load(path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"source-chain {role} JSON invalid: {exc}")
    return loaded


def _verify_component_chain(
    *,
    queue: Mapping[str, Any],
    labels: Mapping[str, Any],
    source_inventory: Mapping[str, Any],
    source_family_audit: Mapping[str, Any],
    report: Mapping[str, Any],
    receipt: Mapping[str, Any],
    errors: list[str],
) -> None:
    if report.get("schema") != COMPONENT_REPORT_SCHEMA:
        errors.append("component report schema mismatch")
    if report.get("status") != COMPONENT_REPORT_VERIFIED:
        errors.append("component report status is not verified")
    if int(report.get("error_count", -1)) != 0 or report.get("errors") != []:
        errors.append("component report did not close without errors")
    if report.get("authority") != COMPONENT_AUTHORITY:
        errors.append("component report authority mismatch")
    if report.get("thresholds") != COMPONENT_THRESHOLDS:
        errors.append("component report thresholds mismatch")
    if tuple(report.get("fold_names") or ()) != COMPONENT_FOLD_NAMES:
        errors.append("component report fold names mismatch")
    forbidden = _component_forbidden_keys(report)
    if forbidden:
        errors.append("component report contains raw query or session fields")

    report_core = dict(report)
    claimed_report_hash = str(report_core.pop("report_sha256", "")).casefold()
    if claimed_report_hash != _component_sha256(report_core):
        errors.append("component report digest mismatch")
    split_payload = {
        "fold_names": report.get("fold_names"),
        "components": report.get("components"),
        "folds": report.get("folds"),
    }
    split_hash = _component_sha256(split_payload)
    if report.get("component_split_sha256") != split_hash:
        errors.append("component split digest mismatch")
    if receipt.get("component_split_sha256") != split_hash:
        errors.append("run receipt component split binding mismatch")

    inputs = report.get("inputs")
    if not isinstance(inputs, Mapping):
        errors.append("component report inputs missing")
        inputs = {}
    expected_input_hashes = {
        "review_queue_sha256": receipt.get("queue_file_sha256"),
        "review_labels_sha256": receipt.get("labels_file_sha256"),
        "source_inventory_sha256": receipt.get("source_inventory_file_sha256"),
        "source_family_audit_sha256": receipt.get("source_family_audit_file_sha256"),
    }
    for field, expected in expected_input_hashes.items():
        if inputs.get(field) != expected:
            errors.append(f"component report input hash mismatch: {field}")
    queue_hash = _review_queue_sha256(queue)
    if inputs.get("review_queue_content_sha256") != queue_hash:
        errors.append("component report queue content binding mismatch")

    if source_family_audit.get("schema") != SOURCE_FAMILY_AUDIT_SCHEMA:
        errors.append("source-family audit schema mismatch")
    if int(source_family_audit.get("error_count", -1)) != 0:
        errors.append("source-family audit contains errors")
    family_catalog = source_family_audit.get("catalog")
    if not isinstance(family_catalog, Mapping) or family_catalog.get(
        "database_sha256"
    ) != receipt.get("catalog_sha256"):
        errors.append("source-family audit catalog binding mismatch")

    canonical_by_path: dict[str, str] = {}
    canonical_rows = source_family_audit.get("canonical_sources")
    if not isinstance(canonical_rows, list):
        errors.append("source-family audit canonical sources missing")
        canonical_rows = []
    for index, row in enumerate(canonical_rows):
        if (
            not isinstance(row, Mapping)
            or not row.get("path")
            or not row.get("family_id")
        ):
            errors.append(f"source-family audit row {index} is incomplete")
            continue
        key = _component_source_path(str(row["path"]))
        if key in canonical_by_path:
            errors.append(f"source-family audit row {index} duplicates a path")
        canonical_by_path[key] = str(row["family_id"])

    suffix_to_family: dict[str, str] = {}
    source_rows = source_inventory.get("sources")
    if not isinstance(source_rows, list):
        errors.append("component source inventory rows missing")
        source_rows = []
    for index, row in enumerate(source_rows):
        if not isinstance(row, Mapping):
            errors.append(f"component source inventory row {index} is invalid")
            continue
        suffix = str(row.get("unique_suffix") or "")
        source_uri = str(row.get("source_uri") or "")
        family = canonical_by_path.get(_component_source_path(source_uri))
        if not suffix or suffix in suffix_to_family or not family:
            errors.append(f"component source inventory row {index} is not family-bound")
            continue
        suffix_to_family[suffix] = family

    candidate_by_hash: dict[str, Mapping[str, Any]] = {}
    candidates = queue.get("candidates")
    if not isinstance(candidates, list):
        candidates = []
    for row in candidates:
        if not isinstance(row, Mapping):
            continue
        query_hash = str(row.get("query_sha256") or "")
        if query_hash:
            candidate_by_hash[query_hash] = row

    accepted_entries: list[dict[str, str]] = []
    decisions: set[str] = set()
    raw_labels = labels.get("labels")
    if not isinstance(raw_labels, list):
        raw_labels = []
    for index, row in enumerate(raw_labels):
        if not isinstance(row, Mapping):
            continue
        query_hash = str(row.get("query_sha256") or "")
        if query_hash in decisions:
            errors.append(f"component label {index} duplicates a query")
            continue
        decisions.add(query_hash)
        if row.get("decision") != "accept":
            continue
        candidate = candidate_by_hash.get(query_hash)
        family = suffix_to_family.get(str(row.get("relevant_source_suffix") or ""))
        stratum = str(row.get("review_stratum") or "")
        session_id = str(candidate.get("session_id") or "") if candidate else ""
        if candidate is None or not family or not stratum or not session_id:
            errors.append(f"component label {index} cannot be reconstructed")
            continue
        accepted_entries.append(
            {
                "query_sha256": query_hash,
                "session_hash": _component_session_hash(session_id),
                "family_id": family,
                "review_stratum": stratum,
            }
        )

    rebuilt = _rebuild_component_split(accepted_entries)
    accepted_count = len(accepted_entries)
    session_count = len({row["session_hash"] for row in accepted_entries})
    family_count = len({row["family_id"] for row in accepted_entries})
    component_count = len(rebuilt["components"])
    maximum_share = (
        max((row["query_count"] for row in rebuilt["components"]), default=0)
        / accepted_count
        if accepted_count
        else 0.0
    )
    expected_observed = {
        "review_candidate_count": len(candidate_by_hash),
        "review_decision_count": len(decisions),
        "accepted_query_count": accepted_count,
        "rejected_query_count": len(decisions) - accepted_count,
        "query_session_count": session_count,
        "target_family_count": family_count,
        "indivisible_component_count": component_count,
        "maximum_component_share": maximum_share,
        "query_session_overlap_count": 0,
        "target_family_overlap_count": 0,
    }
    expected_gates = {
        "minimum_accepted_queries": accepted_count >= 30,
        "minimum_query_sessions": session_count >= 3,
        "minimum_manifest_bound_families": family_count >= 2,
        "minimum_indivisible_components": component_count >= 3,
        "all_folds_nonempty": all(
            rebuilt["folds"][name]["query_count"] > 0 for name in COMPONENT_FOLD_NAMES
        ),
        "maximum_component_share": maximum_share <= 0.8,
        "zero_query_session_overlap": True,
        "zero_target_family_overlap": True,
    }
    if report.get("observed") != expected_observed:
        errors.append("component report observed summary mismatch")
    if report.get("gates") != expected_gates or not all(expected_gates.values()):
        errors.append("component report gate replay mismatch")
    if report.get("components") != rebuilt["components"]:
        errors.append("component report components do not reconstruct")
    if report.get("folds") != rebuilt["folds"]:
        errors.append("component report folds do not reconstruct")
    if split_hash != _component_sha256(rebuilt):
        errors.append("component report split differs from independent reconstruction")


def _verify_source_chain(
    source_chain: Mapping[str, Mapping[str, Any]],
    *,
    benchmark: Mapping[str, Any],
    receipt: Mapping[str, Any],
    errors: list[str],
) -> None:
    if set(source_chain) != set(SOURCE_CHAIN_BUNDLE_FILES):
        return
    queue = source_chain["queue"]
    selection_audit = source_chain["selection_audit"]
    labels = source_chain["labels"]
    preparation = source_chain["preparation_receipt"]
    source_inventory = source_chain["source_inventory"]
    catalog_integrity = source_chain["catalog_integrity"]
    component_report = source_chain["component_report"]
    source_family_audit = source_chain["source_family_audit"]

    if queue.get("schema") != REVIEW_QUEUE_SCHEMA:
        errors.append("source queue schema mismatch")
    queue_hash = _review_queue_sha256(queue)
    if queue.get("queue_sha256") != queue_hash:
        errors.append("source queue content hash mismatch")
    if receipt.get("queue_content_sha256") != queue_hash:
        errors.append("run receipt source queue binding mismatch")
    candidates = queue.get("candidates")
    if not isinstance(candidates, list):
        errors.append("source queue candidates missing")
        candidates = []
    if queue.get("candidate_count") != len(candidates):
        errors.append("source queue candidate count mismatch")
    candidate_by_hash: dict[str, Mapping[str, Any]] = {}
    candidate_ids: set[str] = set()
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, Mapping):
            errors.append(f"source queue candidate {index} is not an object")
            continue
        query = str(candidate.get("query") or "")
        query_hash = str(candidate.get("query_sha256") or "")
        candidate_id = str(candidate.get("candidate_id") or "")
        if sha256(query.encode("utf-8")).hexdigest() != query_hash:
            errors.append(f"source queue candidate {index} query hash mismatch")
        if not candidate_id or candidate_id in candidate_ids:
            errors.append(f"source queue candidate {index} identity mismatch")
        if not query_hash or query_hash in candidate_by_hash:
            errors.append(f"source queue candidate {index} query identity mismatch")
        else:
            candidate_by_hash[query_hash] = candidate
        candidate_ids.add(candidate_id)

    if selection_audit.get("schema") != SELECTION_AUDIT_SCHEMA:
        errors.append("selection audit schema mismatch")
    if selection_audit.get("status") != SELECTION_AUDIT_STATUS:
        errors.append("selection audit status is not an exact replay pass")
    selection_core = dict(selection_audit)
    claimed_selection_hash = str(selection_core.pop("audit_sha256", ""))
    if claimed_selection_hash != _canonical_sha256(selection_core):
        errors.append("selection audit content hash mismatch")
    if selection_audit.get("dataset_sha256") != queue.get("dataset_sha256"):
        errors.append("selection audit dataset binding mismatch")
    if selection_audit.get("queue_sha256") != queue_hash:
        errors.append("selection audit queue binding mismatch")
    if selection_audit.get("candidate_count") != len(candidates):
        errors.append("selection audit candidate count mismatch")
    expected_candidate_hashes = [
        str(candidate.get("query_sha256") or "")
        for candidate in candidates
        if isinstance(candidate, Mapping)
    ]
    if selection_audit.get("accepted_query_sha256") != expected_candidate_hashes:
        errors.append("selection audit candidate hash order mismatch")
    reason_counts = selection_audit.get("reason_counts")
    if not isinstance(reason_counts, Mapping) or reason_counts.get("accepted") != len(
        candidates
    ):
        errors.append("selection audit accepted count mismatch")
    input_rows = selection_audit.get("input_rows")
    if (
        isinstance(input_rows, bool)
        or not isinstance(input_rows, int)
        or input_rows < len(candidates)
    ):
        errors.append("selection audit input row count is impossible")
    selection_authority = {
        "exact_candidate_replay": True,
        "private_text_emitted": False,
        "labels_opened": False,
        "scoring_authorized": False,
        "training_authorized": False,
        "promotion_authorized": False,
    }
    for field, expected in selection_authority.items():
        if selection_audit.get(field) is not expected:
            errors.append(f"selection audit authority invariant failed: {field}")

    boundary = queue.get("prospective_boundary")
    if not isinstance(boundary, Mapping) or boundary.get(
        "catalog_sha256"
    ) != receipt.get("catalog_sha256"):
        errors.append("source queue catalog boundary mismatch")
    if benchmark.get("prospective_boundary") != boundary:
        errors.append("benchmark prospective boundary differs from source queue")
    if benchmark.get("review_scope_sha256") != queue_hash:
        errors.append("benchmark review scope differs from source queue")
    if benchmark.get("source_dataset_sha256") != queue.get("dataset_sha256"):
        errors.append("benchmark dataset hash differs from source queue")

    if source_inventory.get("schema") != SOURCE_INVENTORY_SCHEMA:
        errors.append("source inventory schema mismatch")
    if source_inventory.get("catalog_sha256") != receipt.get("catalog_sha256"):
        errors.append("source inventory catalog binding mismatch")
    source_rows = source_inventory.get("sources")
    if not isinstance(source_rows, list):
        errors.append("source inventory rows missing")
        source_rows = []
    if source_inventory.get("source_count") != len(source_rows):
        errors.append("source inventory count mismatch")
    suffixes = {
        str(row.get("unique_suffix") or "")
        for row in source_rows
        if isinstance(row, Mapping) and row.get("unique_suffix")
    }
    if len(suffixes) != len(source_rows):
        errors.append("source inventory suffixes are incomplete or duplicated")

    if catalog_integrity.get("schema") != CATALOG_INTEGRITY_SCHEMA:
        errors.append("catalog integrity receipt schema mismatch")
    if catalog_integrity.get("status") != "RELATIONAL_INTEGRITY_PASS":
        errors.append("catalog integrity receipt status is not a pass")
    for field in (
        "catalog_sha256_before",
        "catalog_sha256_after",
        "expected_catalog_sha256",
    ):
        if catalog_integrity.get(field) != receipt.get("catalog_sha256"):
            errors.append(f"catalog integrity receipt {field} mismatch")
    integrity_checks = catalog_integrity.get("checks")
    if (
        not isinstance(integrity_checks, Mapping)
        or not integrity_checks
        or not all(value is True for value in integrity_checks.values())
    ):
        errors.append(
            "catalog integrity receipt does not contain an all-pass check set"
        )
    if catalog_integrity.get("independent_semantic_observation_count") != 0:
        errors.append("catalog integrity receipt overstates independent observations")

    if labels.get("schema") != REVIEW_LABEL_SCHEMA:
        errors.append("source labels schema mismatch")
    if labels.get("queue_sha256") != queue_hash:
        errors.append("source labels queue binding mismatch")
    raw_labels = labels.get("labels")
    if not isinstance(raw_labels, list):
        errors.append("source labels missing")
        raw_labels = []
    reviewer = str(labels.get("reviewer") or "")
    reviewed_at = str(labels.get("reviewed_at_utc") or "")
    if not reviewer or not reviewed_at:
        errors.append("source label reviewer identity or time missing")
    expected_queries: list[dict[str, Any]] = []
    used_hashes: set[str] = set()
    for index, label in enumerate(raw_labels):
        if not isinstance(label, Mapping):
            errors.append(f"source label {index} is not an object")
            continue
        query_hash = str(label.get("query_sha256") or "")
        if query_hash not in candidate_by_hash or query_hash in used_hashes:
            errors.append(f"source label {index} query identity mismatch")
            continue
        used_hashes.add(query_hash)
        decision = str(label.get("decision") or "")
        if decision == "reject":
            continue
        suffix = str(label.get("relevant_source_suffix") or "")
        if decision != "accept" or suffix not in suffixes:
            errors.append(f"source label {index} decision or suffix mismatch")
            continue
        candidate = candidate_by_hash[query_hash]
        query_source = (
            f"private-session://{candidate.get('session_id')}/"
            f"{candidate.get('chunk_index')}/{candidate.get('turn_ordinal')}/"
            f"{query_hash[:16]}"
        )
        expected_queries.append(
            {
                "id": candidate.get("candidate_id"),
                "query_source_uri": query_source,
                "query_sha256": query_hash,
                "authored_at_utc": candidate.get("authored_at_utc"),
                "query": candidate.get("query"),
                "relevant_source_suffix": suffix,
                "review": {
                    "reviewer": reviewer,
                    "reviewed_at_utc": reviewed_at,
                    "topic_groups": candidate.get("topic_groups"),
                    "review_stratum": (
                        str(label.get("review_stratum") or "").strip()
                        or candidate.get("review_stratum")
                    ),
                    "rationale": str(label.get("rationale") or "").strip(),
                },
            }
        )
    if used_hashes != set(candidate_by_hash):
        errors.append("source labels do not cover every queued candidate")
    if benchmark.get("queries") != expected_queries:
        errors.append("benchmark queries do not reconstruct from the source chain")

    if preparation.get("schema") != PREPARATION_SCHEMA:
        errors.append("source preparation receipt schema mismatch")
    preparation_core = dict(preparation)
    preparation_hash = str(preparation_core.pop("receipt_sha256", ""))
    if preparation_hash != _canonical_sha256(preparation_core):
        errors.append("source preparation receipt content hash mismatch")
    if (
        preparation.get("status")
        != "READY_FOR_INDEPENDENT_HASH_BOUND_REVIEW_NO_SCORING"
    ):
        errors.append("source preparation receipt status mismatch")
    if preparation.get("queue_file_sha256") != receipt.get("queue_file_sha256"):
        errors.append("source preparation queue file binding mismatch")
    if preparation.get("queue_content_sha256") != queue_hash:
        errors.append("source preparation queue content binding mismatch")
    if preparation.get("catalog_sha256") != receipt.get("catalog_sha256"):
        errors.append("source preparation catalog binding mismatch")
    if preparation.get("candidate_count") != len(candidates):
        errors.append("source preparation candidate count mismatch")
    if preparation.get("source_count") != len(source_rows):
        errors.append("source preparation source count mismatch")
    if preparation.get("source_inventory_sha256") != _canonical_sha256(
        source_inventory
    ):
        errors.append("source preparation inventory binding mismatch")
    if preparation.get("scoring") != "NOT_AUTHORIZED_BY_PREPARATION" or any(
        preparation.get(field) != "NOT_AUTHORIZED"
        for field in ("training_intake", "serving", "merge", "promotion")
    ):
        errors.append("source preparation receipt weakens a no-promotion boundary")

    _verify_component_chain(
        queue=queue,
        labels=labels,
        source_inventory=source_inventory,
        source_family_audit=source_family_audit,
        report=component_report,
        receipt=receipt,
        errors=errors,
    )


def _same_number(left: Any, right: Any) -> bool:
    try:
        return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
    except (TypeError, ValueError):
        return False


def _metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, float | int]:
    count = len(rows)
    reciprocal = [
        0.0 if row["rank"] is None else 1.0 / int(row["rank"]) for row in rows
    ]
    return {
        "queries": count,
        "mrr": mean(reciprocal) if reciprocal else 0.0,
        "recall_at_1": sum(row["rank"] == 1 for row in rows) / count if count else 0.0,
        "recall_at_5": (
            sum(row["rank"] is not None and int(row["rank"]) <= 5 for row in rows)
            / count
            if count
            else 0.0
        ),
        "missed_within_limit": sum(row["rank"] is None for row in rows),
    }


def _macro(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row["relevant_source_uri"]), []).append(
            float(row["reciprocal_rank"])
        )
    by_source = {
        source: {"queries": len(values), "mrr": mean(values)}
        for source, values in sorted(grouped.items())
    }
    return {
        "sources": len(by_source),
        "macro_mrr": (
            mean(value["mrr"] for value in by_source.values()) if by_source else 0.0
        ),
        "by_source": by_source,
    }


def _paired_gate(
    candidate: Sequence[float], control: Sequence[float]
) -> dict[str, Any]:
    if len(candidate) != len(control) or not candidate:
        raise ValueError("paired gate requires nonempty equal-length samples")
    differences = [left - right for left, right in zip(candidate, control, strict=True)]
    pooled_sd = math.sqrt(
        (
            (stdev(candidate) ** 2 if len(candidate) > 1 else 0.0)
            + (stdev(control) ** 2 if len(control) > 1 else 0.0)
        )
        / 2.0
    )
    threshold = 2.0 * pooled_sd
    difference_mean = mean(differences)
    epsilon = 1e-15
    wins = sum(value > epsilon for value in differences)
    losses = sum(value < -epsilon for value in differences)
    ties = len(differences) - wins - losses
    non_tie_pairs = wins + losses
    one_sided_sign_p = (
        sum(math.comb(non_tie_pairs, k) for k in range(wins, non_tie_pairs + 1))
        / (2**non_tie_pairs)
        if non_tie_pairs and wins > losses
        else 1.0
    )
    passes_two_pooled_sd = difference_mean > threshold
    passes_finite_sample_uncertainty = one_sided_sign_p <= 0.05
    return {
        "pair_count": len(differences),
        "mean_difference": difference_mean,
        "pooled_sd": pooled_sd,
        "two_pooled_sd": threshold,
        "passes_two_pooled_sd": passes_two_pooled_sd,
        "finite_sample_test": "exact_one_sided_paired_sign",
        "finite_sample_alpha": 0.05,
        "non_tie_pairs": non_tie_pairs,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "exact_one_sided_p_value": one_sided_sign_p,
        "passes_finite_sample_uncertainty": passes_finite_sample_uncertainty,
        "passes_gate": passes_two_pooled_sd and passes_finite_sample_uncertainty,
    }


def _matched_route_control_contract(
    candidate: Sequence[Mapping[str, Any]],
    route_null: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if len(candidate) != len(route_null) or not candidate:
        raise ValueError(
            "route control contract requires nonempty equal-length outcomes"
        )
    rows = []
    for candidate_row, null_row in zip(candidate, route_null, strict=True):
        candidate_id = str(candidate_row["query_id"])
        null_id = str(null_row["query_id"])
        if candidate_id != null_id:
            raise ValueError("route control outcomes are not query aligned")
        candidate_width = len(candidate_row.get("selected_views", []))
        null_width = len(null_row.get("selected_views", []))
        rows.append(
            {
                "query_id": candidate_id,
                "candidate_route_width": candidate_width,
                "route_null_width": null_width,
                "width_matched": candidate_width == null_width,
            }
        )
    all_widths_match = all(row["width_matched"] for row in rows)
    return {
        "control": "route_null",
        "candidate_trainable_parameters": 0,
        "route_null_trainable_parameters": 0,
        "equal_parameter_count": True,
        "all_route_widths_match": all_widths_match,
        "passes": all_widths_match,
        "rows": rows,
    }


def _check_mapping(
    errors: list[str],
    label: str,
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> None:
    if set(actual) != set(expected):
        errors.append(f"{label}: key set mismatch")
        return
    for key, expected_value in expected.items():
        actual_value = actual[key]
        if isinstance(expected_value, (float, int)) and not isinstance(
            expected_value, bool
        ):
            if not _same_number(actual_value, expected_value):
                errors.append(f"{label}.{key}: numeric mismatch")
        elif actual_value != expected_value:
            errors.append(f"{label}.{key}: value mismatch")


def verify_e92_prospective_bundle(
    output_dir: str | Path,
    *,
    expected_control_seeds: Sequence[int] = DEFAULT_CONTROL_SEEDS,
) -> dict[str, Any]:
    root = Path(output_dir).resolve(strict=True)
    benchmark_path = root / "BENCHMARK.json"
    result_path = root / "RESULT.json"
    receipt_path = root / "RUN_RECEIPT.json"
    benchmark = _load(benchmark_path)
    result = _load(result_path)
    receipt = _load(receipt_path)
    errors: list[str] = []
    expected_seeds = list(expected_control_seeds)
    if (
        len(expected_seeds) < 3
        or len(set(expected_seeds)) != len(expected_seeds)
        or any(
            isinstance(seed, bool) or not isinstance(seed, int)
            for seed in expected_seeds
        )
    ):
        raise ValueError(
            "expected_control_seeds must contain at least three distinct integers"
        )

    if benchmark.get("schema") != BENCHMARK_SCHEMA:
        errors.append("benchmark schema mismatch")
    if result.get("schema") != RESULT_SCHEMA:
        errors.append("result schema mismatch")
    if receipt.get("schema") != E92_RUN_SCHEMA:
        errors.append("run receipt schema mismatch")
    receipt_core = dict(receipt)
    claimed_receipt_hash = str(receipt_core.pop("receipt_sha256", ""))
    if claimed_receipt_hash != _canonical_sha256(receipt_core):
        errors.append("run receipt content hash mismatch")
    benchmark_hash = _sha256_file(benchmark_path)
    result_hash = _sha256_file(result_path)
    if receipt.get("benchmark_sha256") != benchmark_hash:
        errors.append("benchmark file hash mismatch")
    if receipt.get("result_sha256") != result_hash:
        errors.append("result file hash mismatch")
    if result.get("benchmark_sha256") != benchmark_hash:
        errors.append("result benchmark binding mismatch")
    if result.get("catalog_sha256") != receipt.get("catalog_sha256"):
        errors.append("catalog binding mismatch")
    catalog = Path(str(receipt.get("catalog") or ""))
    if not catalog.is_file() or _sha256_file(catalog) != receipt.get("catalog_sha256"):
        errors.append("catalog file hash mismatch")
    source_chain = _load_source_chain(root, receipt, errors)
    _verify_source_chain(
        source_chain,
        benchmark=benchmark,
        receipt=receipt,
        errors=errors,
    )
    if result.get("algorithm_revision") != ALGORITHM_REVISION:
        errors.append("algorithm revision mismatch")
    if result.get("candidate_arm") != "late_output_fused":
        errors.append("candidate arm mismatch")
    if any(
        receipt.get(field) != "NOT_AUTHORIZED"
        for field in ("training_intake", "serving", "merge", "promotion")
    ):
        errors.append("run receipt weakens a no-promotion boundary")
    receipt_seeds = receipt.get("control_seeds")
    result_seeds = result.get("control_seeds")
    if receipt_seeds != expected_seeds:
        errors.append(
            "run receipt control seeds do not match the independently expected seeds"
        )
    if result_seeds != expected_seeds:
        errors.append(
            "result control seeds do not match the independently expected seeds"
        )
    if result_seeds != receipt_seeds:
        errors.append("result and run receipt control seed declarations differ")
    if result.get("result_limit") != receipt.get("result_limit"):
        errors.append("result limit differs from the run receipt")
    if result.get("query_provenance") != benchmark.get("query_provenance"):
        errors.append("result query provenance differs from the benchmark")

    module_root = Path(__file__).resolve().parent
    expected_implementation_hashes = {
        name: _sha256_file(module_root / name)
        for name in (
            "prime_token_catalog.py",
            "prime_token_benchmark.py",
            "prime_token_query_harvest.py",
            "prime_token_query_family_components.py",
            "prime_token_prospective.py",
        )
    }
    if receipt.get("implementation_hashes") != expected_implementation_hashes:
        errors.append("implementation source hash mismatch")

    queries = benchmark.get("queries")
    if not isinstance(queries, list):
        errors.append("benchmark query list missing")
        queries = []
    query_ids = [
        str(row.get("id") or "") for row in queries if isinstance(row, Mapping)
    ]
    if (
        len(query_ids) != len(queries)
        or not all(query_ids)
        or len(set(query_ids)) != len(query_ids)
    ):
        errors.append("benchmark query identities are incomplete or duplicated")
    if result.get("query_count") != len(queries):
        errors.append("result query count mismatch")
    arms = result.get("arms")
    if not isinstance(arms, Mapping) or set(arms) != EXPECTED_ARMS:
        errors.append("result arm set mismatch")
        arms = {}
    for arm_name, runs in arms.items():
        if not isinstance(runs, list) or not runs:
            errors.append(f"{arm_name}: run list missing")
            continue
        expected_run_seeds = (
            expected_seeds
            if arm_name in {"shuffled_binding", "random_rank_fusion"}
            else [0]
        )
        if len(runs) != len(expected_run_seeds):
            errors.append(
                f"{arm_name}: expected {len(expected_run_seeds)} runs, found {len(runs)}"
            )
        for run_index, run in enumerate(runs):
            if run_index >= len(expected_run_seeds):
                errors.append(f"{arm_name}[{run_index}]: unexpected extra run")
            elif (
                not isinstance(run, Mapping)
                or run.get("control_seed") != expected_run_seeds[run_index]
            ):
                errors.append(f"{arm_name}[{run_index}]: control seed mismatch")
            outcomes = run.get("outcomes") if isinstance(run, Mapping) else None
            if (
                not isinstance(outcomes, list)
                or [row.get("query_id") for row in outcomes] != query_ids
            ):
                errors.append(f"{arm_name}[{run_index}]: outcome query order mismatch")
                continue
            for outcome_index, outcome in enumerate(outcomes):
                benchmark_query = queries[outcome_index]
                review = benchmark_query.get("review", {})
                if outcome.get("query_source_uri") != benchmark_query.get(
                    "query_source_uri"
                ):
                    errors.append(
                        f"{arm_name}[{run_index}].outcomes[{outcome_index}]: query source mismatch"
                    )
                if not isinstance(review, Mapping) or outcome.get(
                    "review_stratum"
                ) != review.get("review_stratum"):
                    errors.append(
                        f"{arm_name}[{run_index}].outcomes[{outcome_index}]: review stratum mismatch"
                    )
                source_suffix = str(benchmark_query.get("relevant_source_suffix") or "")
                if not source_suffix or not str(
                    outcome.get("relevant_source_uri") or ""
                ).endswith(source_suffix):
                    errors.append(
                        f"{arm_name}[{run_index}].outcomes[{outcome_index}]: relevant source mismatch"
                    )
                rank = outcome.get("rank")
                expected_rr = 0.0 if rank is None else 1.0 / int(rank)
                if not _same_number(outcome.get("reciprocal_rank"), expected_rr):
                    errors.append(
                        f"{arm_name}[{run_index}].outcomes[{outcome_index}]: reciprocal rank mismatch"
                    )
            _check_mapping(
                errors,
                f"{arm_name}[{run_index}].metrics",
                run.get("metrics", {}),
                _metrics(outcomes),
            )
            actual_macro = run.get("macro_source_metrics", {})
            expected_macro = _macro(outcomes)
            if actual_macro.get("sources") != expected_macro[
                "sources"
            ] or not _same_number(
                actual_macro.get("macro_mrr"), expected_macro["macro_mrr"]
            ):
                errors.append(f"{arm_name}[{run_index}]: macro source summary mismatch")
            if actual_macro.get("by_source") != expected_macro["by_source"]:
                errors.append(f"{arm_name}[{run_index}]: per-source metrics mismatch")

    if not errors and arms:
        candidate_outcomes = arms["late_output_fused"][0]["outcomes"]
        candidate_rr = [float(row["reciprocal_rank"]) for row in candidate_outcomes]
        expected_gates: dict[str, Any] = {}
        for control_name in ("lexical_only", "no_intervention", "route_null"):
            expected_gates[control_name] = _paired_gate(
                candidate_rr,
                [
                    float(row["reciprocal_rank"])
                    for row in arms[control_name][0]["outcomes"]
                ],
            )
        for run in arms["shuffled_binding"]:
            seed = int(run["control_seed"])
            expected_gates[f"shuffled_binding_seed_{seed}"] = _paired_gate(
                candidate_rr,
                [float(row["reciprocal_rank"]) for row in run["outcomes"]],
            )
        for run in arms["random_rank_fusion"]:
            seed = int(run["control_seed"])
            expected_gates[f"random_rank_fusion_seed_{seed}"] = _paired_gate(
                candidate_rr,
                [float(row["reciprocal_rank"]) for row in run["outcomes"]],
            )
        actual_gates = result.get("gates", {})
        if set(actual_gates) != set(expected_gates):
            errors.append("paired gate set mismatch")
        else:
            for name, expected in expected_gates.items():
                _check_mapping(errors, f"gates.{name}", actual_gates[name], expected)

        route_control_contract = _matched_route_control_contract(
            candidate_outcomes,
            arms["route_null"][0]["outcomes"],
        )
        _check_mapping(
            errors,
            "route_control_contract",
            result.get("route_control_contract", {}),
            route_control_contract,
        )

        candidate_macro = _macro(candidate_outcomes)
        lexical_outcomes = arms["lexical_only"][0]["outcomes"]
        lexical_macro = _macro(lexical_outcomes)
        macro_gate = {
            "candidate_macro_mrr": candidate_macro["macro_mrr"],
            "lexical_macro_mrr": lexical_macro["macro_mrr"],
            "passes": candidate_macro["macro_mrr"] > lexical_macro["macro_mrr"],
        }
        _check_mapping(
            errors, "macro_source_gate", result.get("macro_source_gate", {}), macro_gate
        )
        source_deltas = {
            source: candidate_macro["by_source"][source]["mrr"]
            - lexical_macro["by_source"][source]["mrr"]
            for source in candidate_macro["by_source"]
        }
        source_gate = {
            "improved_sources": sum(value > 0 for value in source_deltas.values()),
            "harmed_sources": sum(value < 0 for value in source_deltas.values()),
            "worst_source_delta": min(source_deltas.values(), default=0.0),
            "per_source_delta": source_deltas,
        }
        source_gate["passes"] = (
            source_gate["improved_sources"] >= 3
            and source_gate["worst_source_delta"] >= -0.05
        )
        actual_source_gate = result.get("source_change_gate", {})
        if set(actual_source_gate) != set(source_gate):
            errors.append("source change gate key mismatch")
        else:
            for key, value in source_gate.items():
                if key == "per_source_delta":
                    if actual_source_gate[key] != value:
                        errors.append("source change per-source delta mismatch")
                elif isinstance(value, (float, int)) and not isinstance(value, bool):
                    if not _same_number(actual_source_gate[key], value):
                        errors.append(f"source change gate {key} mismatch")
                elif actual_source_gate[key] != value:
                    errors.append(f"source change gate {key} mismatch")

        source_counts = Counter(
            str(row["relevant_source_uri"]) for row in candidate_outcomes
        )
        strata = sorted(
            {
                str(row.get("review_stratum") or "")
                for row in candidate_outcomes
                if row.get("review_stratum")
            }
        )
        max_source_share = max(source_counts.values(), default=0) / len(
            candidate_outcomes
        )
        diversity = {
            "topic_strata": strata,
            "topic_strata_count": len(strata),
            "relevant_source_count": len(source_counts),
            "max_relevant_source_share": max_source_share,
            "relevant_source_query_counts": dict(sorted(source_counts.items())),
        }
        if result.get("diversity") != diversity:
            errors.append("diversity summary mismatch")
        underpowered = []
        if len(queries) < MIN_CAPABILITY_QUERIES:
            underpowered.append(
                f"{len(queries)} queries is below the preregistered {MIN_CAPABILITY_QUERIES}-query capability floor"
            )
        if benchmark.get("query_provenance") != "independent_external":
            underpowered.append(
                "queries are not independently authored external requests"
            )
        if len(strata) < 3:
            underpowered.append("fewer than three reviewed topic strata")
        if len(source_counts) < 6:
            underpowered.append("fewer than six distinct relevant catalog sources")
        if max_source_share > 0.4:
            underpowered.append("one relevant source exceeds the 40-percent cap")
        if result.get("underpowered_reasons") != underpowered:
            errors.append("underpowered reason mismatch")
        all_gates = all(bool(value["passes_gate"]) for value in expected_gates.values())
        expected_status = (
            "UNDERPOWERED"
            if underpowered
            else (
                "CANDIDATE_PASS"
                if (
                    all_gates
                    and route_control_contract["passes"]
                    and macro_gate["passes"]
                    and source_gate["passes"]
                )
                else "NO_GAIN"
            )
        )
        if (
            result.get("status") != expected_status
            or receipt.get("result_status") != expected_status
        ):
            errors.append("terminal status mismatch")

    verification_core = {
        "schema": "scbe.e92-prospective-verification.v1",
        "status": (
            "VERIFIED_E92_PROSPECTIVE_NO_AUTOMATIC_PROMOTION"
            if not errors
            else "INVALID_E92_PROSPECTIVE_BUNDLE"
        ),
        "bundle": str(root),
        "benchmark_sha256": _sha256_file(benchmark_path),
        "result_sha256": _sha256_file(result_path),
        "run_receipt_sha256": _sha256_file(receipt_path),
        "query_count": len(queries),
        "error_count": len(errors),
        "errors": errors,
        "training_intake": "NOT_AUTHORIZED",
        "serving": "NOT_AUTHORIZED",
        "merge": "NOT_AUTHORIZED",
        "promotion": "NOT_AUTHORIZED",
    }
    return {
        **verification_core,
        "verification_sha256": _canonical_sha256(verification_core),
    }
