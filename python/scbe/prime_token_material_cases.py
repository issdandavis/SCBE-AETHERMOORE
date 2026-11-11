"""Plan and write target-invariant, dual-source-disjoint material cases.

The in-memory planner never writes or authorizes training.  The bundle builder
writes one new, hash-bound directory and refuses overwrite.  In both paths the
input packet depends only on query text and pre-outcome query provenance; the
reviewed catalog source, class token, and split remain supervision metadata.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from itertools import combinations
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from .function_lexicon import FunctionLexicon
from .prime_token_catalog import VIEW_NAMES, _query_features
from .prime_token_input_access import PrimeTokenRecord
from .prime_token_query_harvest import (
    EXPLICIT_ROUTE_SCOPE_COUNTS,
    REVIEW_QUEUE_SCHEMA,
    review_queue_sha256,
)
from .prime_token_training import canonical_sha256, sha256_file

PLAN_SCHEMA = "scbe.prime-token-material-case-plan.v1"
BUILD_RECEIPT_SCHEMA = "scbe.prime-token-material-case-build.v1"
SOURCE_MANIFEST_SCHEMA = "scbe.prime-token-material-source-manifest.v1"
SPLIT_MANIFEST_SCHEMA = "scbe.prime-token-dual-source-split.v1"
EVALUATOR_RECEIPT_SCHEMA = "scbe.prime-token-evaluator-receipt.v1"
CASE_MANIFEST_SCHEMA = "scbe.prime-token-material-cases.v1"
BENCHMARK_SCHEMA = "scbe.prime-token-benchmark.v1"
SOURCE_FAMILY_AUDIT_SCHEMA = "scbe.prime-token-source-family-audit.v1"
CLOSED_SOURCE_SNAPSHOT_SCHEMA = "clay.closed-codex-source-snapshot.v1"
DEFAULT_OUTPUT_TOKEN_START = 224
DEFAULT_MAX_QUERY_BYTES = 510
LANES = ("train", "validation", "final_test")
FIXED_FUNCTION_CLASSES = tuple(EXPLICIT_ROUTE_SCOPE_COUNTS)


def _sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _required_text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def _required_sha256(value: object, *, label: str) -> str:
    digest = _required_text(value, label=label).casefold()
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError(f"{label} must be lowercase SHA-256")
    return digest


def query_session_id(query_source_uri: object) -> str:
    """Extract one closed source-session identity from a private-session URI."""

    uri = _required_text(query_source_uri, label="query_source_uri")
    parsed = urlsplit(uri)
    if parsed.scheme != "private-session" or not parsed.netloc:
        raise ValueError("query source URI must use private-session://<session>/...")
    return parsed.netloc


def _record_json(record: PrimeTokenRecord) -> dict[str, object]:
    return {
        "canonical_id": record.canonical_id,
        "section_id": record.section_id,
        "source_family": record.source_family,
        "views": {name: dict(record.views[name]) for name in VIEW_NAMES},
    }


def build_query_input(
    query: object,
    query_source_uri: object,
    *,
    max_query_bytes: int = DEFAULT_MAX_QUERY_BYTES,
) -> dict[str, object]:
    """Build one packet/input identity without accepting any target metadata."""

    text = _required_text(query, label="query")
    if max_query_bytes < 1 or max_query_bytes > 65_533:
        raise ValueError("max_query_bytes must be in [1, 65533]")
    session_id = query_session_id(query_source_uri)
    query_sha256 = _sha256_text(text)
    session_sha256 = _sha256_text(session_id)
    features, analysis = _query_features(text, FunctionLexicon())
    views: dict[str, dict[str, object]] = {
        name: {"features": sorted(features[name])[:128]} for name in VIEW_NAMES
    }
    views["lexical"].update(
        {
            "query_sha256": query_sha256,
            "utf8_bytes": len(text.encode("utf-8")),
            "word_count": len(analysis["words"]),
        }
    )
    views["five_w"].update(
        {
            "primary": analysis["five_w"]["primary"],
            "color": analysis["five_w"]["color"],
        }
    )
    views["source"] = {
        "source_kind": "private-session",
        "session_sha256": session_sha256,
        "query_sha256": query_sha256,
        "query_source_uri_sha256": _sha256_text(str(query_source_uri).strip()),
    }
    query_source_family = f"query-session:{session_sha256}"
    record = PrimeTokenRecord(
        canonical_id=f"query:{query_sha256}",
        section_id=f"query-session:{session_sha256}:query:{query_sha256[:16]}",
        source_family=query_source_family,
        views=views,
    )
    record.validate()
    encoded = text.encode("utf-8")[:max_query_bytes]
    token_ids = [0, *encoded, 0]
    owner_positions = [0]
    output_positions = [len(token_ids) - 1]
    packet_identity = {
        "query_sha256": query_sha256,
        "query_session_sha256": session_sha256,
        "query_source_family": query_source_family,
        "token_ids": token_ids,
        "owner_positions": owner_positions,
        "output_positions": output_positions,
        "record_receipts": [record.receipt()],
    }
    return {
        **packet_identity,
        "packet_input_sha256": canonical_sha256(packet_identity),
        "records": [_record_json(record)],
    }


def frozen_output_vocabulary(
    source_family_audit: Mapping[str, Any],
    *,
    start_token_id: int = DEFAULT_OUTPUT_TOKEN_START,
) -> dict[str, object]:
    """Freeze the relation/function Cartesian vocabulary before reading labels."""

    if source_family_audit.get("schema") != SOURCE_FAMILY_AUDIT_SCHEMA:
        raise ValueError("source-family audit schema changed")
    if not str(source_family_audit.get("status") or "").startswith(
        "VERIFIED_SOURCE_FAMILY_BOUNDARY"
    ):
        raise ValueError("source-family audit is not verified")
    if int(source_family_audit.get("error_count", -1)) != 0:
        raise ValueError("source-family audit contains errors")
    families = source_family_audit.get("families")
    if not isinstance(families, list) or len(families) < 3:
        raise ValueError("at least three manifest-bound source families are required")
    family_ids = sorted(
        _required_text(
            row.get("family_id") if isinstance(row, dict) else None, label="family_id"
        )
        for row in families
    )
    if len(set(family_ids)) != len(family_ids):
        raise ValueError("source-family audit repeats a family identity")
    size = len(family_ids) * len(FIXED_FUNCTION_CLASSES)
    if start_token_id < 0 or start_token_id + size > 256:
        raise ValueError("bounded output vocabulary does not fit the byte model")
    rows = []
    for family_id in family_ids:
        for function_class in FIXED_FUNCTION_CLASSES:
            rows.append(
                {
                    "token_id": start_token_id + len(rows),
                    "relationship_class": family_id,
                    "function_class": function_class,
                }
            )
    return {
        "start_token_id": start_token_id,
        "family_ids": family_ids,
        "function_classes": list(FIXED_FUNCTION_CLASSES),
        "rows": rows,
        "vocabulary_sha256": canonical_sha256(rows),
    }


def _canonical_sources(source_family_audit: Mapping[str, Any]) -> list[dict[str, str]]:
    raw = source_family_audit.get("canonical_sources")
    if not isinstance(raw, list) or not raw:
        raise ValueError("source-family audit omitted canonical sources")
    rows = []
    for value in raw:
        if not isinstance(value, dict):
            raise TypeError("canonical source must be an object")
        rows.append(
            {
                "path": _required_text(
                    value.get("path"), label="canonical source path"
                ),
                "family_id": _required_text(
                    value.get("family_id"), label="canonical source family"
                ),
                "content_sha256": _required_text(
                    value.get("content_sha256"), label="canonical source hash"
                ),
            }
        )
        rows[-1]["content_sha256"] = _required_sha256(
            rows[-1]["content_sha256"], label="canonical source hash"
        )
    return rows


def resolve_relevant_source(
    relevant_source_suffix: object,
    source_family_audit: Mapping[str, Any],
) -> dict[str, str]:
    """Resolve a reviewed suffix to exactly one canonical source authority."""

    suffix = _required_text(relevant_source_suffix, label="relevant_source_suffix")
    normalized = suffix.replace("\\", "/").casefold().lstrip("/")
    matches = [
        row
        for row in _canonical_sources(source_family_audit)
        if row["path"].replace("\\", "/").casefold().endswith(normalized)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"reviewed source suffix resolves to {len(matches)} canonical sources"
        )
    return matches[0]


def _review_stratum(query: Mapping[str, Any]) -> str:
    review = query.get("review")
    if not isinstance(review, dict):
        raise ValueError("reviewed query omitted its review receipt")
    explicit = review.get("review_stratum")
    if isinstance(explicit, str) and explicit in FIXED_FUNCTION_CLASSES:
        return explicit
    groups = review.get("topic_groups")
    if not isinstance(groups, list):
        raise ValueError("review receipt omitted topic groups")
    matched = [str(group) for group in groups if str(group) in FIXED_FUNCTION_CLASSES]
    if len(matched) != 1:
        raise ValueError(
            "reviewed query must resolve to exactly one fixed function stratum"
        )
    return matched[0]


class _DisjointSet:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, value: str) -> str:
        self.parent.setdefault(value, value)
        if self.parent[value] != value:
            self.parent[value] = self.find(self.parent[value])
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[max(left_root, right_root)] = min(left_root, right_root)


def _component_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, object]]:
    graph = _DisjointSet()
    for row in rows:
        graph.union(
            f"family:{row['source_family']}", f"session:{row['query_source_family']}"
        )
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        root = graph.find(f"family:{row['source_family']}")
        grouped[root].append(index)
    components = []
    for indices in grouped.values():
        families = sorted({str(rows[index]["source_family"]) for index in indices})
        sessions = sorted(
            {str(rows[index]["query_source_family"]) for index in indices}
        )
        identity = {"families": families, "query_sources": sessions}
        components.append(
            {
                "component_sha256": canonical_sha256(identity),
                "indices": indices,
                "families": families,
                "query_sources": sessions,
                "count": len(indices),
            }
        )
    return sorted(components, key=lambda row: str(row["component_sha256"]))


def _assign_components(
    rows: Sequence[Mapping[str, Any]],
    *,
    minimum_final_test: int,
) -> tuple[dict[int, str], list[dict[str, object]]]:
    components = _component_rows(rows)
    if len(components) < 3:
        raise ValueError(
            "catalog-family/query-session graph has fewer than three components"
        )
    if len(components) > 16:
        raise ValueError("component assignment exceeds the bounded exhaustive planner")
    final_options = []
    for width in range(1, len(components) - 1):
        for selected in combinations(range(len(components)), width):
            count = sum(int(components[index]["count"]) for index in selected)
            if count >= minimum_final_test:
                fingerprint = tuple(
                    str(components[index]["component_sha256"]) for index in selected
                )
                final_options.append((count, fingerprint, selected))
    if not final_options:
        raise ValueError(
            "no source-disjoint final-test component set reaches the minimum"
        )
    _, _, final_indices = min(final_options)
    remaining = [
        index for index in range(len(components)) if index not in final_indices
    ]
    if len(remaining) < 2:
        raise ValueError("component assignment leaves no train/validation separation")
    validation_index = min(
        remaining,
        key=lambda index: (
            int(components[index]["count"]),
            str(components[index]["component_sha256"]),
        ),
    )
    assignment: dict[int, str] = {}
    for component_index, component in enumerate(components):
        lane = (
            "final_test"
            if component_index in final_indices
            else "validation" if component_index == validation_index else "train"
        )
        for row_index in component["indices"]:
            assignment[int(row_index)] = lane
        component["lane"] = lane
    if set(assignment.values()) != set(LANES):
        raise ValueError("component assignment did not populate every required lane")
    return assignment, components


def _concentration_gate(
    rows: Sequence[Mapping[str, Any]],
    *,
    maximum_source_fraction: float,
    maximum_family_fraction: float,
) -> dict[str, object]:
    if not rows:
        raise ValueError("material case plan has no accepted queries")
    source_counts = Counter(str(row["target_source_path"]) for row in rows)
    family_counts = Counter(str(row["source_family"]) for row in rows)
    total = len(rows)
    source_fraction = max(source_counts.values()) / total
    family_fraction = max(family_counts.values()) / total
    if source_fraction > maximum_source_fraction:
        raise ValueError("largest canonical source exceeds its accepted-query bound")
    if family_fraction > maximum_family_fraction:
        raise ValueError("largest catalog family exceeds its accepted-query bound")
    return {
        "total": total,
        "source_counts": dict(sorted(source_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "largest_source_fraction": source_fraction,
        "largest_family_fraction": family_fraction,
    }


def plan_material_cases(
    benchmark: Mapping[str, Any],
    source_family_audit: Mapping[str, Any],
    *,
    closed_query_sessions: Sequence[str],
    minimum_final_test: int = 30,
    maximum_source_fraction: float = 0.40,
    maximum_family_fraction: float = 0.60,
    max_query_bytes: int = DEFAULT_MAX_QUERY_BYTES,
    start_token_id: int = DEFAULT_OUTPUT_TOKEN_START,
) -> dict[str, object]:
    """Return a deterministic in-memory plan; never write or launch training."""

    if benchmark.get("schema") != BENCHMARK_SCHEMA:
        raise ValueError("reviewed benchmark schema changed")
    if benchmark.get("private_runtime_only") is not True:
        raise ValueError("material benchmark is not restricted to private runtime")
    if source_family_audit.get("schema") != SOURCE_FAMILY_AUDIT_SCHEMA:
        raise ValueError("source-family audit schema changed")
    if minimum_final_test < 1:
        raise ValueError("minimum final-test count must be positive")
    if (
        not 0.0 < maximum_source_fraction <= 1.0
        or not 0.0 < maximum_family_fraction <= 1.0
    ):
        raise ValueError("concentration bounds must lie in (0,1]")
    vocabulary = frozen_output_vocabulary(
        source_family_audit, start_token_id=start_token_id
    )
    closed_sessions = {
        _required_text(value, label="closed query session")
        for value in closed_query_sessions
    }
    if len(closed_sessions) < 3:
        raise ValueError("at least three closed query source sessions are required")
    token_by_classes = {
        (str(row["relationship_class"]), str(row["function_class"])): int(
            row["token_id"]
        )
        for row in vocabulary["rows"]
    }
    queries = benchmark.get("queries")
    if not isinstance(queries, list) or not queries:
        raise ValueError("reviewed benchmark has no queries")
    rows: list[dict[str, object]] = []
    seen_queries: set[str] = set()
    seen_record_ids: set[str] = set()
    for index, query in enumerate(queries):
        if not isinstance(query, dict):
            raise TypeError("reviewed query must be an object")
        material_input = build_query_input(
            query.get("query"),
            query.get("query_source_uri"),
            max_query_bytes=max_query_bytes,
        )
        query_hash = str(material_input["query_sha256"])
        if query_hash in seen_queries:
            raise ValueError("material benchmark repeats a query hash")
        seen_queries.add(query_hash)
        session_id = query_session_id(query.get("query_source_uri"))
        if session_id not in closed_sessions:
            raise ValueError("material benchmark contains an open query source session")
        record_id = _required_text(query.get("id"), label=f"query {index} id")
        if record_id in seen_record_ids:
            raise ValueError("material benchmark repeats a record identity")
        seen_record_ids.add(record_id)
        target_source = resolve_relevant_source(
            query.get("relevant_source_suffix"), source_family_audit
        )
        function_class = _review_stratum(query)
        target_token = token_by_classes[(target_source["family_id"], function_class)]
        targets = list(material_input["token_ids"])
        targets[int(material_input["output_positions"][0])] = target_token
        rows.append(
            {
                "record_id": record_id,
                "query": str(query["query"]).strip(),
                "query_source_uri": str(query["query_source_uri"]).strip(),
                **material_input,
                "source_family": target_source["family_id"],
                "target_source_path": target_source["path"],
                "target_source_sha256": target_source["content_sha256"],
                "function_class": function_class,
                "target_token_id": target_token,
                "targets": targets,
            }
        )
    concentration = _concentration_gate(
        rows,
        maximum_source_fraction=maximum_source_fraction,
        maximum_family_fraction=maximum_family_fraction,
    )
    assignments, components = _assign_components(
        rows, minimum_final_test=minimum_final_test
    )
    lanes: dict[str, list[dict[str, object]]] = {lane: [] for lane in LANES}
    for index, row in enumerate(rows):
        lane = assignments[index]
        case = dict(row)
        case["split"] = lane
        lanes[lane].append(case)
    lane_families = {
        lane: sorted({str(row["source_family"]) for row in values})
        for lane, values in lanes.items()
    }
    lane_sessions = {
        lane: sorted({str(row["query_source_family"]) for row in values})
        for lane, values in lanes.items()
    }
    for left_index, left in enumerate(LANES):
        for right in LANES[left_index + 1 :]:
            if set(lane_families[left]) & set(lane_families[right]):
                raise RuntimeError("planned lanes overlap catalog source families")
            if set(lane_sessions[left]) & set(lane_sessions[right]):
                raise RuntimeError("planned lanes overlap query source sessions")
    if len(lanes["final_test"]) < minimum_final_test:
        raise RuntimeError("planned final-test lane is below its minimum")
    split_manifest = {
        "schema": "scbe.prime-token-dual-source-split.v1",
        "source_disjoint": True,
        "query_session_disjoint": True,
        "component_policy": "catalog-family/query-session connected components",
        "components": components,
        "lane_counts": {lane: len(lanes[lane]) for lane in LANES},
        "lane_source_families": lane_families,
        "lane_query_source_families": lane_sessions,
        "minimum_final_test": minimum_final_test,
    }
    return {
        "schema": PLAN_SCHEMA,
        "status": "PLANNED_NO_WRITE_NO_TRAINING_AUTHORITY",
        "vocabulary": vocabulary,
        "concentration": concentration,
        "split_manifest": split_manifest,
        "lanes": lanes,
        "query_count": len(rows),
        "closed_query_session_count": len(closed_sessions),
        "max_query_bytes": max_query_bytes,
        "packet_inputs_exclude_targets": True,
        "training_authorized": False,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
        "tool_dispatch": False,
    }


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"JSON authority must contain one object: {path}")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise TypeError(f"{path}:{line_number} must contain one object")
            rows.append(value)
    return rows


def _queue_sessions_and_queries(
    queue: Mapping[str, Any],
) -> tuple[list[str], dict[str, Mapping[str, Any]]]:
    if queue.get("schema") != REVIEW_QUEUE_SCHEMA:
        raise ValueError("source review queue schema changed")
    if queue.get("queue_sha256") != review_queue_sha256(queue):
        raise ValueError("source review queue content hash differs")
    sessions = queue.get("session_ids")
    candidates = queue.get("candidates")
    if not isinstance(sessions, list) or not isinstance(candidates, list):
        raise ValueError("source review queue omitted sessions or candidates")
    closed_sessions = sorted(
        {_required_text(value, label="queue session identity") for value in sessions}
    )
    by_hash: dict[str, Mapping[str, Any]] = {}
    for value in candidates:
        if not isinstance(value, dict):
            raise TypeError("source review candidate must be an object")
        query = _required_text(value.get("query"), label="source review query")
        query_hash = _sha256_text(query)
        if query_hash != value.get("query_sha256") or query_hash in by_hash:
            raise ValueError("source review candidate hash is invalid or duplicated")
        by_hash[query_hash] = value
    return closed_sessions, by_hash


def _closed_source_sessions(
    snapshot: Mapping[str, Any],
    queue: Mapping[str, Any],
    *,
    queue_sessions: Sequence[str],
) -> list[str]:
    """Bind queue sessions to the watcher's immutable closed-source snapshot."""

    if snapshot.get("schema") != CLOSED_SOURCE_SNAPSHOT_SCHEMA:
        raise ValueError("closed-source snapshot schema changed")
    boundary = queue.get("prospective_boundary")
    if not isinstance(boundary, dict):
        raise ValueError("source review queue omitted its prospective boundary")
    if snapshot.get("catalog_generated_at_utc") != boundary.get(
        "catalog_generated_at_utc"
    ):
        raise ValueError("closed-source snapshot catalog boundary differs")
    root_text = _required_text(
        snapshot.get("sessions_root"), label="closed-source sessions root"
    )
    root = Path(root_text)
    if not root.is_absolute():
        raise ValueError("closed-source sessions root must be absolute")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)
    sources = snapshot.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("closed-source snapshot has no sources")
    snapshot_sessions: set[str] = set()
    source_paths: set[Path] = set()
    for index, value in enumerate(sources):
        if not isinstance(value, dict):
            raise TypeError(f"closed-source snapshot row {index} must be an object")
        source_text = _required_text(
            value.get("path"), label=f"closed-source snapshot row {index} path"
        )
        source = Path(source_text)
        if not source.is_absolute():
            raise ValueError("closed-source snapshot path must be absolute")
        source = source.resolve(strict=True)
        if not source.is_relative_to(root):
            raise ValueError("closed-source snapshot path escapes its sessions root")
        if source in source_paths:
            raise ValueError("closed-source snapshot repeats a source path")
        source_paths.add(source)
        stat = source.stat()
        if stat.st_size != value.get("bytes") or stat.st_mtime_ns != value.get(
            "mtime_ns"
        ):
            raise RuntimeError("closed-source snapshot source stat differs")
        session = _required_text(
            value.get("source_session"),
            label=f"closed-source snapshot row {index} session",
        )
        if session in snapshot_sessions:
            raise ValueError("closed-source snapshot repeats a session identity")
        snapshot_sessions.add(session)
    queue_set = set(queue_sessions)
    if not queue_set <= snapshot_sessions:
        raise ValueError(
            "source review queue contains a session absent from the closed snapshot"
        )
    return sorted(queue_set)


def _validate_benchmark_queue_binding(
    benchmark: Mapping[str, Any], queue_by_hash: Mapping[str, Mapping[str, Any]]
) -> None:
    queries = benchmark.get("queries")
    if not isinstance(queries, list) or not queries:
        raise ValueError("reviewed benchmark has no queries")
    for value in queries:
        if not isinstance(value, dict):
            raise TypeError("reviewed benchmark query must be an object")
        query = _required_text(value.get("query"), label="reviewed benchmark query")
        query_hash = _sha256_text(query)
        source = queue_by_hash.get(query_hash)
        if source is None:
            raise ValueError("reviewed benchmark query is absent from the source queue")
        if value.get("id") != source.get("candidate_id"):
            raise ValueError(
                "reviewed benchmark query identity differs from the source queue"
            )
        if query_session_id(value.get("query_source_uri")) != _required_text(
            source.get("session_id"), label="source review session"
        ):
            raise ValueError(
                "reviewed benchmark query session differs from the source queue"
            )


def _packet_free_rows(
    path: Path, *, lane: str, max_bytes: int = 512
) -> list[dict[str, object]]:
    if max_bytes < 1 or max_bytes > 512:
        raise ValueError("packet-free byte bound must be in [1,512]")
    rows = []
    identities: set[str] = set()
    for value in _load_jsonl(path):
        identity = _required_text(value.get("id"), label=f"{lane} identity")
        if identity in identities:
            raise ValueError(f"{lane} repeats an identity")
        identities.add(identity)
        text = _required_text(value.get("text"), label=f"{lane} text")
        source_family = _required_text(
            value.get("source_family"), label=f"{lane} source family"
        )
        source_locator = _required_text(
            value.get("source_locator"), label=f"{lane} source locator"
        )
        content_sha256 = _required_text(
            value.get("content_sha256"), label=f"{lane} content hash"
        ).casefold()
        if len(content_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in content_sha256
        ):
            raise ValueError(f"{lane} content hash must be lowercase SHA-256")
        token_ids = list(text.encode("utf-8")[:max_bytes])
        if not token_ids:
            raise ValueError(f"{lane} text produced no byte tokens")
        rows.append(
            {
                "id": identity,
                "split": lane,
                "source_family": source_family,
                "source_locator": source_locator,
                "content_sha256": content_sha256,
                "token_ids": token_ids,
            }
        )
    if not rows:
        raise ValueError(f"{lane} source lane is empty")
    return rows


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def build_material_case_bundle(
    *,
    benchmark_path: str | Path,
    source_family_audit_path: str | Path,
    source_queue_path: str | Path,
    closed_source_snapshot_path: str | Path,
    ordinary_source_path: str | Path,
    retention_source_path: str | Path,
    output_dir: str | Path,
    minimum_final_test: int = 30,
    maximum_source_fraction: float = 0.40,
    maximum_family_fraction: float = 0.60,
    max_query_bytes: int = DEFAULT_MAX_QUERY_BYTES,
    start_token_id: int = DEFAULT_OUTPUT_TOKEN_START,
) -> dict[str, object]:
    """Write one immutable case bundle after all source authorities exist."""

    benchmark_file = Path(benchmark_path).resolve(strict=True)
    audit_file = Path(source_family_audit_path).resolve(strict=True)
    queue_file = Path(source_queue_path).resolve(strict=True)
    snapshot_file = Path(closed_source_snapshot_path).resolve(strict=True)
    ordinary_file = Path(ordinary_source_path).resolve(strict=True)
    retention_file = Path(retention_source_path).resolve(strict=True)
    benchmark = _load_json(benchmark_file)
    source_family_audit = _load_json(audit_file)
    queue = _load_json(queue_file)
    queue_sessions, queue_by_hash = _queue_sessions_and_queries(queue)
    snapshot = _load_json(snapshot_file)
    closed_sessions = _closed_source_sessions(
        snapshot, queue, queue_sessions=queue_sessions
    )
    _validate_benchmark_queue_binding(benchmark, queue_by_hash)
    plan = plan_material_cases(
        benchmark,
        source_family_audit,
        closed_query_sessions=closed_sessions,
        minimum_final_test=minimum_final_test,
        maximum_source_fraction=maximum_source_fraction,
        maximum_family_fraction=maximum_family_fraction,
        max_query_bytes=max_query_bytes,
        start_token_id=start_token_id,
    )
    ordinary = _packet_free_rows(ordinary_file, lane="ordinary")
    retention = _packet_free_rows(retention_file, lane="retention")
    material_families = {
        str(row["source_family"]) for lane in LANES for row in plan["lanes"][lane]
    } | {
        str(row["query_source_family"]) for lane in LANES for row in plan["lanes"][lane]
    }
    ordinary_families = {str(row["source_family"]) for row in ordinary}
    retention_families = {str(row["source_family"]) for row in retention}
    if material_families & (ordinary_families | retention_families):
        raise ValueError("packet-free lanes overlap material source families")
    if ordinary_families & retention_families:
        raise ValueError("ordinary and retention source families overlap")

    output = Path(output_dir).resolve()
    pending = output.with_name(f"{output.name}.pending")
    if output.exists() or pending.exists():
        raise FileExistsError(
            "material case output or pending directory already exists"
        )
    pending.mkdir(parents=True)
    try:
        lane_rows = {
            "train": plan["lanes"]["train"],
            "validation": plan["lanes"]["validation"],
            "final_test": plan["lanes"]["final_test"],
            "ordinary": ordinary,
            "retention": retention,
        }
        descriptors = {}
        for lane, rows in lane_rows.items():
            path = pending / f"{lane}.jsonl"
            _write_jsonl(path, rows)
            descriptors[lane] = {
                "path": path.name,
                "sha256": sha256_file(path),
                "count": len(rows),
            }
        vocabulary_rows = plan["vocabulary"]["rows"]
        allowed = [int(row["token_id"]) for row in vocabulary_rows]
        relationship_classes = {
            str(row["token_id"]): str(row["relationship_class"])
            for row in vocabulary_rows
        }
        function_classes = {
            str(row["token_id"]): str(row["function_class"]) for row in vocabulary_rows
        }
        evaluator = {
            "schema": EVALUATOR_RECEIPT_SCHEMA,
            "allowed_output_token_ids": allowed,
            "relationship_class_by_token_id": relationship_classes,
            "function_class_by_token_id": function_classes,
            "scoring": "full-vocabulary-argmax_then_exact_and_class_equivalence",
        }
        evaluator_path = pending / "EVALUATOR_RECEIPT.json"
        _write_json(evaluator_path, evaluator)
        split_path = pending / "SPLIT_MANIFEST.json"
        _write_json(split_path, plan["split_manifest"])
        source_manifest = {
            "schema": SOURCE_MANIFEST_SCHEMA,
            "benchmark": str(benchmark_file),
            "benchmark_sha256": sha256_file(benchmark_file),
            "source_family_audit": str(audit_file),
            "source_family_audit_sha256": sha256_file(audit_file),
            "source_queue": str(queue_file),
            "source_queue_sha256": sha256_file(queue_file),
            "closed_source_snapshot": str(snapshot_file),
            "closed_source_snapshot_sha256": sha256_file(snapshot_file),
            "ordinary_source": str(ordinary_file),
            "ordinary_source_sha256": sha256_file(ordinary_file),
            "retention_source": str(retention_file),
            "retention_source_sha256": sha256_file(retention_file),
            "closed_query_sessions": closed_sessions,
            "private_runtime_only": True,
        }
        source_manifest_path = pending / "SOURCE_MANIFEST.json"
        _write_json(source_manifest_path, source_manifest)
        cases_manifest = {
            "schema": CASE_MANIFEST_SCHEMA,
            "source_disjoint": True,
            "query_session_disjoint": True,
            "max_query_bytes": max_query_bytes,
            "exact_evaluator_receipt_sha256": sha256_file(evaluator_path),
            "exact_source_manifest_sha256": sha256_file(source_manifest_path),
            "exact_split_manifest_sha256": sha256_file(split_path),
            "allowed_output_token_ids": allowed,
            "relationship_class_by_token_id": relationship_classes,
            "function_class_by_token_id": function_classes,
            "vocabulary_sha256": plan["vocabulary"]["vocabulary_sha256"],
            "files": descriptors,
        }
        cases_manifest_path = pending / "CASES_MANIFEST.json"
        _write_json(cases_manifest_path, cases_manifest)
        receipt = {
            "schema": BUILD_RECEIPT_SCHEMA,
            "status": "BUILT_NO_TRAINING_AUTHORITY",
            "query_count": plan["query_count"],
            "lane_counts": {lane: len(rows) for lane, rows in lane_rows.items()},
            "source_manifest": source_manifest_path.name,
            "source_manifest_sha256": sha256_file(source_manifest_path),
            "split_manifest": split_path.name,
            "split_manifest_sha256": sha256_file(split_path),
            "cases_manifest": cases_manifest_path.name,
            "cases_manifest_sha256": sha256_file(cases_manifest_path),
            "evaluator_receipt": evaluator_path.name,
            "evaluator_receipt_sha256": sha256_file(evaluator_path),
            "training_authorized": False,
            "promotion_authorized": False,
            "partial_unfreeze_authorized": False,
            "tool_dispatch": False,
        }
        receipt_path = pending / "BUILD_RECEIPT.json"
        _write_json(receipt_path, receipt)
        os.replace(pending, output)
    except BaseException:
        # Preserve the pending directory for forensic inspection; never delete it.
        raise
    return {
        **receipt,
        "output_dir": str(output),
        "build_receipt": str(output / "BUILD_RECEIPT.json"),
        "build_receipt_sha256": sha256_file(output / "BUILD_RECEIPT.json"),
    }


__all__ = [
    "BENCHMARK_SCHEMA",
    "BUILD_RECEIPT_SCHEMA",
    "CASE_MANIFEST_SCHEMA",
    "CLOSED_SOURCE_SNAPSHOT_SCHEMA",
    "DEFAULT_MAX_QUERY_BYTES",
    "DEFAULT_OUTPUT_TOKEN_START",
    "EVALUATOR_RECEIPT_SCHEMA",
    "FIXED_FUNCTION_CLASSES",
    "LANES",
    "PLAN_SCHEMA",
    "SOURCE_MANIFEST_SCHEMA",
    "SOURCE_FAMILY_AUDIT_SCHEMA",
    "SPLIT_MANIFEST_SCHEMA",
    "build_material_case_bundle",
    "build_query_input",
    "frozen_output_vocabulary",
    "plan_material_cases",
    "query_session_id",
    "resolve_relevant_source",
]
