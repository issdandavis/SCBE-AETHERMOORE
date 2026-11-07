"""Harvest independent private-session requests for reviewed retrieval evaluation.

Raw request text stays in runtime output. Git-tracked labels can use hashes and
source suffixes without embedding the private conversation text. Both scrubbed
session chunks and scrubbed direct-speech rows retain source-session provenance.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from python.scbe.prime_token_benchmark import BENCHMARK_SCHEMA, MIN_CAPABILITY_QUERIES

REVIEW_QUEUE_SCHEMA = "scbe.prime-token-independent-review-queue.v1"
REVIEW_LABEL_SCHEMA = "scbe.prime-token-independent-review-labels.v1"
SESSION_CHUNK_SCHEMA = "clay.session.chunk.v1"
DIRECT_SPEECH_SCHEMA = "clay.direct-speech-turn.v1"
EXPLICIT_ROUTE_SCOPE_REVISION = "prime-token-explicit-route-scope-v1"
EXPLICIT_ROUTE_SCOPE_COUNTS = {
    "five_w": 3,
    "publication": 20,
    "tongue_braid": 17,
    "source_research": 20,
}

# Broad topic selectors were fixed before reviewing individual requests. They
# contain no phrase copied from a target document or the 11-query benchmark.
TOPIC_PATTERNS: dict[str, re.Pattern[str]] = {
    "prime_sieve": re.compile(r"\b(?:prime|sieves?)\b", re.IGNORECASE),
    "five_w": re.compile(
        r"(?:\b5\s*w\b|\bfive\s+w\b|who\s+what\s+when\s+where\s+why)",
        re.IGNORECASE,
    ),
    "tongue_braid": re.compile(r"\b(?:braid|residual|tongues?)\b", re.IGNORECASE),
    "publication": re.compile(
        r"\b(?:pip|pypi|kdp|publish|publishing|manuscript|book|terminal)\b",
        re.IGNORECASE,
    ),
    "source_research": re.compile(
        r"\b(?:rss|arxiv|crossref|research|sources?|feeds?|metadata)\b",
        re.IGNORECASE,
    ),
}

REJECT_MARKERS = (
    "<codex_internal_context",
    "# agents.md instructions",
    "<instructions>",
    "<environment_context",
    "<skills_instructions>",
    "retained user instructions start",
    "retained source order:",
    "tool exec call:",
    "tool exec result:",
    '"sandbox_permissions":',
    '"environment_id":',
)
SYNTHETIC_TURN_PREFIX = re.compile(
    r'^\s*(?:(?:>>>\s+)?retained\b|\[\d+\]\s+(?:assistant|tool)\b|\{\s*"command"\s*:)',
    re.IGNORECASE,
)
TURN_BOUNDARY = re.compile(r"(?m)(?=^(?:Issac|Assistant): |^\[action:|^\[result\])")


def sha256_file(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def review_queue_sha256(queue: Mapping[str, Any]) -> str:
    """Bind labels to the exact harvested queue, policy, provenance, and text."""
    payload = dict(queue)
    payload.pop("queue_sha256", None)
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _normalized_request(text: str) -> str:
    return " ".join(text.split()).casefold()


def _request_turns(text: str) -> Iterable[str]:
    for part in TURN_BOUNDARY.split(text):
        if part.startswith("Issac: "):
            request = part.removeprefix("Issac: ").strip()
            if request:
                yield request


def _topic_groups(text: str) -> list[str]:
    return [name for name, pattern in TOPIC_PATTERNS.items() if pattern.search(text)]


def harvest_review_queue(
    dataset: str | Path,
    *,
    min_chars: int = 20,
    max_chars: int = 1600,
) -> dict[str, Any]:
    """Return a deterministic queue without assigning relevance labels."""
    if min_chars < 1 or max_chars < min_chars:
        raise ValueError("invalid request length bounds")
    dataset_path = Path(dataset).resolve()
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    global_ordinal = 0
    sessions: set[str] = set()
    input_schemas: set[str] = set()
    with dataset_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            row = json.loads(line)
            schema = str(row.get("schema") or SESSION_CHUNK_SCHEMA).strip()
            input_schemas.add(schema)
            if schema == DIRECT_SPEECH_SCHEMA:
                session_id = str(row.get("source_session") or "").strip()
                chunk_index = int(row.get("turn", line_number - 1))
                text = row.get("text")
                requests = (text,) if isinstance(text, str) else ()
            elif schema == SESSION_CHUNK_SCHEMA:
                session_id = str(row.get("session_id") or "").strip()
                chunk_index = int(row.get("chunk_index", line_number - 1))
                text = row.get("text")
                requests = _request_turns(text) if isinstance(text, str) else ()
            else:
                raise ValueError(
                    f"unknown input schema on line {line_number}: {schema}"
                )
            if not session_id or not isinstance(text, str):
                raise ValueError(f"invalid chunk record on line {line_number}")
            sessions.add(session_id)
            for request in requests:
                request = request.strip()
                if not request:
                    continue
                ordinal = global_ordinal
                global_ordinal += 1
                folded = request.casefold()
                if not min_chars <= len(request) <= max_chars:
                    continue
                if any(
                    marker in folded for marker in REJECT_MARKERS
                ) or SYNTHETIC_TURN_PREFIX.search(request):
                    continue
                groups = _topic_groups(request)
                if not groups:
                    continue
                normalized = _normalized_request(request)
                if normalized in seen:
                    continue
                seen.add(normalized)
                request_hash = sha256(request.encode("utf-8")).hexdigest()
                candidates.append(
                    {
                        "candidate_id": f"request-{request_hash[:16]}",
                        "query_sha256": request_hash,
                        "session_id": session_id,
                        "chunk_index": chunk_index,
                        "source_schema": schema,
                        "turn_ordinal": ordinal,
                        "topic_groups": groups,
                        "query": request,
                    }
                )
    queue = {
        "schema": REVIEW_QUEUE_SCHEMA,
        "dataset": str(dataset_path),
        "dataset_sha256": sha256_file(dataset_path),
        "session_ids": sorted(sessions),
        "selection_policy": {
            "accepted_input_schemas": sorted(input_schemas),
            "min_chars": min_chars,
            "max_chars": max_chars,
            "topic_patterns": {
                name: pattern.pattern for name, pattern in TOPIC_PATTERNS.items()
            },
            "rejected_context_markers": list(REJECT_MARKERS),
            "ordering": "source turn ordinal",
            "deduplication": "casefolded whitespace-normalized exact text",
        },
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    queue["queue_sha256"] = review_queue_sha256(queue)
    return queue


def query_hashes_from_benchmark(benchmark: Mapping[str, Any]) -> set[str]:
    """Return exact private-query hashes consumed by one benchmark."""
    if benchmark.get("schema") != BENCHMARK_SCHEMA:
        raise ValueError("unknown benchmark schema")
    queries = benchmark.get("queries")
    if not isinstance(queries, list):
        raise ValueError("benchmark queries must be a list")
    hashes = set()
    for index, row in enumerate(queries):
        if not isinstance(row, Mapping):
            raise ValueError(f"benchmark query {index} must be an object")
        text = row.get("query")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"benchmark query {index} has no text")
        hashes.add(sha256(text.strip().encode("utf-8")).hexdigest())
    return hashes


def build_explicit_route_review_scope(
    queue: Mapping[str, Any],
    *,
    excluded_query_sha256: Iterable[str] = (),
) -> dict[str, Any]:
    """Seal the preregistered balanced multi-source review scope."""
    if queue.get("schema") != REVIEW_QUEUE_SCHEMA:
        raise ValueError("unknown review-queue schema")
    actual_queue_hash = review_queue_sha256(queue)
    if queue.get("queue_sha256") != actual_queue_hash:
        raise ValueError("review queue content hash mismatch")
    excluded = {str(value).strip().casefold() for value in excluded_query_sha256}
    if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in excluded):
        raise ValueError("excluded query hashes must be lowercase SHA-256 values")
    candidates = queue.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("review queue candidates must be a list")
    selected: list[dict[str, Any]] = []
    for stratum, required in EXPLICIT_ROUTE_SCOPE_COUNTS.items():
        eligible = sorted(
            (
                row
                for row in candidates
                if isinstance(row, Mapping)
                and row.get("topic_groups") == [stratum]
                and str(row.get("query_sha256") or "").casefold() not in excluded
            ),
            key=lambda row: str(row["query_sha256"]),
        )
        stratum_rows = []
        used_sessions: set[str] = set()
        for row in eligible:
            session_id = str(row.get("session_id") or "").strip()
            if not session_id or session_id in used_sessions:
                continue
            candidate = dict(row)
            candidate["review_stratum"] = stratum
            stratum_rows.append(candidate)
            used_sessions.add(session_id)
            if len(stratum_rows) == required:
                break
        if len(stratum_rows) != required:
            raise ValueError(
                f"explicit-route scope requires {required} unique-session {stratum} candidates; "
                f"found {len(stratum_rows)}"
            )
        selected.extend(stratum_rows)
    scope = {
        "schema": REVIEW_QUEUE_SCHEMA,
        "dataset": queue["dataset"],
        "dataset_sha256": queue["dataset_sha256"],
        "session_ids": sorted({str(row["session_id"]) for row in selected}),
        "selection_policy": {
            "scope_revision": EXPLICIT_ROUTE_SCOPE_REVISION,
            "source_queue_sha256": actual_queue_hash,
            "excluded_query_sha256": sorted(excluded),
            "exclusive_topic_groups": True,
            "per_stratum_counts": dict(EXPLICIT_ROUTE_SCOPE_COUNTS),
            "ordering": "query_sha256 ascending within stratum",
            "session_cap": "one candidate per source session within each stratum",
            "review_requirement": "every scoped candidate must receive one hash-bound decision",
        },
        "candidate_count": len(selected),
        "candidates": selected,
    }
    scope["queue_sha256"] = review_queue_sha256(scope)
    return scope


def load_labels(path: str | Path) -> dict[str, Any]:
    labels = json.loads(Path(path).read_text(encoding="utf-8"))
    if labels.get("schema") != REVIEW_LABEL_SCHEMA:
        raise ValueError("unknown review-label schema")
    if not isinstance(labels.get("labels"), list):
        raise ValueError("review labels must be a list")
    return labels


def build_reviewed_benchmark(
    queue: Mapping[str, Any],
    labels: Mapping[str, Any],
    *,
    minimum_queries: int = MIN_CAPABILITY_QUERIES,
) -> dict[str, Any]:
    """Join hash-bound reviewer decisions to private text and emit a benchmark."""
    if queue.get("schema") != REVIEW_QUEUE_SCHEMA:
        raise ValueError("unknown review-queue schema")
    actual_queue_hash = review_queue_sha256(queue)
    if queue.get("queue_sha256") != actual_queue_hash:
        raise ValueError("review queue content hash mismatch")
    if labels.get("schema") != REVIEW_LABEL_SCHEMA:
        raise ValueError("unknown review-label schema")
    if labels.get("queue_sha256") != actual_queue_hash:
        raise ValueError("labels do not target this exact review queue")
    reviewer = str(labels.get("reviewer") or "").strip()
    reviewed_at = str(labels.get("reviewed_at_utc") or "").strip()
    if not reviewer or not reviewed_at:
        raise ValueError("reviewer identity and review time are required")
    by_hash = {row["query_sha256"]: row for row in queue["candidates"]}
    used: set[str] = set()
    queries = []
    for index, label in enumerate(labels["labels"]):
        request_hash = str(label.get("query_sha256") or "").strip()
        decision = str(label.get("decision") or "").strip()
        suffix = str(label.get("relevant_source_suffix") or "").strip()
        if request_hash in used:
            raise ValueError(f"duplicate reviewed request hash: {request_hash}")
        if request_hash not in by_hash:
            raise ValueError(
                f"review label does not match a harvested request: {request_hash}"
            )
        used.add(request_hash)
        if decision == "reject":
            continue
        if decision != "accept" or not suffix:
            raise ValueError(f"label {index} requires accept+suffix or reject")
        candidate = by_hash[request_hash]
        query_source = (
            f"private-session://{candidate['session_id']}/"
            f"{candidate['chunk_index']}/{candidate['turn_ordinal']}/{request_hash[:16]}"
        )
        queries.append(
            {
                "id": candidate["candidate_id"],
                "query_source_uri": query_source,
                "query": candidate["query"],
                "relevant_source_suffix": suffix,
                "review": {
                    "reviewer": reviewer,
                    "reviewed_at_utc": reviewed_at,
                    "topic_groups": candidate["topic_groups"],
                    "review_stratum": candidate.get("review_stratum"),
                    "rationale": str(label.get("rationale") or "").strip(),
                },
            }
        )
    scope_revision = str(queue.get("selection_policy", {}).get("scope_revision") or "")
    if scope_revision == EXPLICIT_ROUTE_SCOPE_REVISION and used != set(by_hash):
        missing = len(set(by_hash) - used)
        raise ValueError(
            f"explicit-route scope requires a decision for every candidate; {missing} are missing"
        )
    if len(queries) < minimum_queries:
        raise ValueError(
            f"review accepted {len(queries)} queries; at least {minimum_queries} are required"
        )
    return {
        "schema": BENCHMARK_SCHEMA,
        "title": "Prime token catalog independently authored private-session benchmark",
        "query_provenance": "independent_external",
        "query_provenance_detail": (
            "Private user requests authored before this catalog benchmark; selected by fixed broad topics and "
            "hash-bound to reviewer-assigned source labels."
        ),
        "label_policy": "Reviewer labels are evaluator-only and never enter query features.",
        "private_runtime_only": True,
        "source_dataset_sha256": queue["dataset_sha256"],
        "review_scope_sha256": actual_queue_hash,
        "review_scope_revision": scope_revision or None,
        "queries": queries,
    }


def write_json_exclusive(path: str | Path, payload: Mapping[str, Any]) -> None:
    output = Path(path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
