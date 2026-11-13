#!/usr/bin/env python3
"""Count prospective turns in open Codex sessions without harvesting their text."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from types import ModuleType
from typing import Any

SCHEMA_V1 = "scbe.prime-token-open-source-readiness.v1"
SCHEMA_V2 = "scbe.prime-token-query-readiness.v2"
CATALOG_SCHEMA = "scbe.prime-token-catalog.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp is missing")
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(pending, path)


def _catalog_boundary(manifest_path: Path) -> dict[str, str]:
    manifest_file = manifest_path.resolve(strict=True)
    raw = manifest_file.read_bytes()
    manifest = json.loads(raw)
    if not isinstance(manifest, dict) or manifest.get("schema") != CATALOG_SCHEMA:
        raise ValueError("unexpected catalog manifest schema")
    generated = _utc(manifest.get("generated_at_utc"))
    return {
        "catalog_generated_at_utc": generated.isoformat(),
        "manifest": str(manifest_file),
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _load_collector(path: Path, expected_sha256: str) -> ModuleType:
    collector = path.resolve(strict=True)
    expected = expected_sha256.strip().casefold()
    if len(expected) != 64 or sha256_file(collector) != expected:
        raise RuntimeError("collector hash mismatch")
    name = f"prime_token_readiness_collector_{expected[:12]}"
    spec = importlib.util.spec_from_file_location(name, collector)
    if spec is None or spec.loader is None:
        raise RuntimeError("collector module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    collector_parent = str(collector.parent)
    inserted = collector_parent not in sys.path
    if inserted:
        sys.path.insert(0, collector_parent)
    try:
        spec.loader.exec_module(module)
    finally:
        if inserted:
            sys.path.remove(collector_parent)
    required = (
        "INTERNAL_MARKERS",
        "MAX_TRAINING_CHARS",
        "SYSTEM_REMINDER",
        "_source_session",
        "extract_user_text",
        "normalized_hash",
        "scrub",
        "source_is_closed",
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"collector interface is incomplete: {', '.join(missing)}")
    return module


def _load_selector(path: Path, expected_sha256: str) -> ModuleType:
    selector = path.resolve(strict=True)
    expected = expected_sha256.strip().casefold()
    if len(expected) != 64 or sha256_file(selector) != expected:
        raise RuntimeError("selector hash mismatch")
    name = f"prime_token_readiness_selector_{expected[:12]}"
    spec = importlib.util.spec_from_file_location(name, selector)
    if spec is None or spec.loader is None:
        raise RuntimeError("selector module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    repo_root = str(selector.parents[2])
    inserted = repo_root not in sys.path
    if inserted:
        sys.path.insert(0, repo_root)
    try:
        spec.loader.exec_module(module)
    finally:
        if inserted:
            sys.path.remove(repo_root)
    required = (
        "DEFAULT_MAX_REQUEST_CHARS",
        "DEFAULT_MIN_REQUEST_CHARS",
        "classify_review_request",
        "normalize_review_request",
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"selector interface is incomplete: {', '.join(missing)}")
    return module


def _scan_source(
    path: Path,
    *,
    cutoff: datetime,
    collector: ModuleType,
    seen: set[str],
    selector: ModuleType | None = None,
    candidate_seen: set[str] | None = None,
) -> tuple[dict[str, Any], set[str], set[str]]:
    initial = path.stat()
    initially_closed = bool(collector.source_is_closed(path))
    counts: Counter[str] = Counter()
    local_seen: set[str] = set()
    accepted: set[str] = set()
    local_candidates: set[str] = set()
    known_candidates = candidate_seen if candidate_seen is not None else set()
    with path.open("rb") as handle:
        for raw in handle:
            counts["lines"] += 1
            try:
                record = json.loads(raw.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                counts["invalid_json"] += 1
                continue
            extracted = collector.extract_user_text(record)
            if extracted is None:
                continue
            text, authored_at = extracted
            if _utc(authored_at) <= cutoff:
                counts["pre_freeze_user_turns"] += 1
                continue
            counts["post_freeze_user_turns"] += 1
            text = collector.SYSTEM_REMINDER.sub("", text).strip()
            if len(text) < 2:
                counts["empty_or_tiny"] += 1
                continue
            folded = text.casefold()
            if any(marker in folded for marker in collector.INTERNAL_MARKERS):
                counts["internal_context_rejected"] += 1
                continue
            identity = collector.normalized_hash(text)
            if identity in seen or identity in local_seen:
                counts["duplicate"] += 1
                continue
            local_seen.add(identity)
            if len(text) > int(collector.MAX_TRAINING_CHARS):
                counts["oversize_excluded"] += 1
                continue
            accepted.add(identity)
            counts["eligible_unique_turns"] += 1
            if selector is not None:
                scrubbed_text, _ = collector.scrub(text)
                selection = selector.classify_review_request(scrubbed_text)
                reason = str(selection.get("reason") or "invalid")
                if not selection.get("eligible"):
                    counts[f"review_rejected_{reason}"] += 1
                    continue
                candidate_identity = selector.normalize_review_request(scrubbed_text)
                if candidate_identity in known_candidates or candidate_identity in local_candidates:
                    counts["review_duplicate"] += 1
                    continue
                local_candidates.add(candidate_identity)
                counts["review_query_candidates"] += 1
    final = path.stat()
    stable = final.st_size == initial.st_size and final.st_mtime_ns == initial.st_mtime_ns
    closed = bool(collector.source_is_closed(path))
    stable = stable and initially_closed == closed
    if not stable:
        accepted.clear()
        local_candidates.clear()
    return (
        {
            "path_sha256": hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest(),
            "source_session": collector._source_session(path),
            "source_bytes": final.st_size,
            "source_mtime_utc": datetime.fromtimestamp(final.st_mtime, tz=timezone.utc).isoformat(),
            "stable_during_scan": stable,
            "closed": closed,
            "counts": dict(sorted(counts.items())),
        },
        accepted,
        local_candidates,
    )


def measure_readiness(
    *,
    sessions_root: Path,
    catalog_manifest: Path,
    collector_path: Path,
    collector_sha256: str,
    minimum_candidates: int,
    minimum_closed_sessions: int,
    selector_path: Path | None = None,
    selector_sha256: str | None = None,
) -> dict[str, Any]:
    if minimum_candidates < 1 or minimum_closed_sessions < 1:
        raise ValueError("minimums must be positive")
    sessions = sessions_root.resolve(strict=True)
    if not sessions.is_dir():
        raise NotADirectoryError(sessions)
    boundary = _catalog_boundary(catalog_manifest)
    cutoff = _utc(boundary["catalog_generated_at_utc"])
    collector = _load_collector(collector_path, collector_sha256)
    if (selector_path is None) != (selector_sha256 is None):
        raise ValueError("selector path and SHA-256 must be provided together")
    selector = _load_selector(selector_path, str(selector_sha256)) if selector_path is not None else None
    selected = [
        path
        for path in sorted(sessions.rglob("rollout-*.jsonl"))
        if datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc) > cutoff
    ]
    # The pinned collector consumes closed sources only, in lexical path order.
    # Measure those first so an open-source duplicate cannot suppress a closed
    # candidate. Open sources are then a projection of what could be added after
    # closure, not an authority over the current queue.
    selected.sort(key=lambda path: (not collector.source_is_closed(path), str(path)))
    seen: set[str] = set()
    sources: list[dict[str, Any]] = []
    stable_sources = 0
    closed_sources = 0
    open_sources = 0
    eligible = 0
    candidate_seen: set[str] = set()
    closed_review_candidates = 0
    open_review_candidates = 0
    for path in selected:
        row, identities, candidates = _scan_source(
            path,
            cutoff=cutoff,
            collector=collector,
            seen=seen,
            selector=selector,
            candidate_seen=candidate_seen,
        )
        sources.append(row)
        if not row["stable_during_scan"]:
            continue
        stable_sources += 1
        if row["closed"]:
            closed_sources += 1
            closed_review_candidates += len(candidates)
        else:
            open_sources += 1
            open_review_candidates += len(candidates)
        seen.update(identities)
        candidate_seen.update(candidates)
        eligible += len(identities)

    measured_candidates = closed_review_candidates if selector is not None else eligible
    candidate_deficit = max(0, minimum_candidates - measured_candidates)
    closed_session_deficit = max(0, minimum_closed_sessions - closed_sources)
    distinct_session_deficit = max(0, minimum_closed_sessions - stable_sources)
    if any(not row["stable_during_scan"] for row in sources):
        status = "RETRY_UNSTABLE_SOURCE"
    elif selector is not None and candidate_deficit and closed_session_deficit:
        status = "WAITING_FOR_REVIEW_QUERIES_AND_CLOSED_SESSIONS"
    elif selector is not None and candidate_deficit:
        status = "WAITING_FOR_CLOSED_REVIEW_QUERIES"
    elif selector is not None and closed_session_deficit:
        status = "WAITING_FOR_CLOSED_SESSIONS"
    elif candidate_deficit and distinct_session_deficit:
        status = "WAITING_FOR_MORE_AUTHORED_TURNS_AND_DISTINCT_SESSIONS"
    elif candidate_deficit:
        status = "WAITING_FOR_MORE_AUTHORED_TURNS"
    elif distinct_session_deficit:
        status = "WAITING_FOR_MORE_DISTINCT_SESSIONS"
    elif closed_session_deficit:
        status = "WAITING_FOR_SESSION_CLOSE"
    else:
        status = "READY_FOR_PINNED_COLLECTOR"
    result = {
        "schema": SCHEMA_V2 if selector is not None else SCHEMA_V1,
        "status": status,
        "updated_at_utc": utc_now(),
        "sessions_root": str(sessions),
        "catalog_boundary": boundary,
        "collector": {
            "path": str(collector_path.resolve()),
            "sha256": collector_sha256.casefold(),
        },
        "minimums": {
            "eligible_candidates": minimum_candidates,
            "closed_source_sessions": minimum_closed_sessions,
        },
        "observed": {
            "post_freeze_source_files": len(selected),
            "stable_source_sessions": stable_sources,
            "closed_source_sessions": closed_sources,
            "open_source_sessions": open_sources,
            "eligible_unique_turns": eligible,
        },
        "deficits": {
            "eligible_candidates": candidate_deficit,
            "closed_source_sessions": closed_session_deficit,
            "additional_distinct_sessions_even_if_current_sources_close": distinct_session_deficit,
        },
        "sources": sources,
        "authority": {
            "training_intake": "NOT_AUTHORIZED",
            "scoring": "NOT_AUTHORIZED",
            "promotion": "NOT_AUTHORIZED",
            "partial_unfreeze": "NONE",
            "tool_dispatch": "DISABLED",
        },
        "claim_boundary": (
            "Readiness telemetry only. Open source text is counted but never emitted, harvested, queued, "
            "scored, or admitted to training. The pinned closed-session collector remains authoritative."
        ),
    }
    if selector is not None and selector_path is not None:
        result["selector"] = {
            "path": str(selector_path.resolve()),
            "sha256": str(selector_sha256).casefold(),
            "minimum_chars": int(selector.DEFAULT_MIN_REQUEST_CHARS),
            "maximum_chars": int(selector.DEFAULT_MAX_REQUEST_CHARS),
        }
        result["minimums"] = {
            "closed_review_query_candidates": minimum_candidates,
            "closed_source_sessions": minimum_closed_sessions,
        }
        result["observed"].update(
            {
                "collector_eligible_unique_turns": eligible,
                "closed_review_query_candidates": closed_review_candidates,
                "open_review_query_candidates": open_review_candidates,
                "projected_review_query_candidates_if_open_sources_close": (
                    closed_review_candidates + open_review_candidates
                ),
            }
        )
        result["deficits"] = {
            "closed_review_query_candidates": candidate_deficit,
            "closed_source_sessions": closed_session_deficit,
            "additional_distinct_sessions_even_if_current_sources_close": (distinct_session_deficit),
        }
        result["claim_boundary"] = (
            "Readiness telemetry only. The hash-pinned review selector is applied in memory, but open source "
            "text and identities are never emitted, queued, scored, or admitted to training. Only the pinned "
            "closed-session collector may create a review queue."
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions-root", required=True, type=Path)
    parser.add_argument("--catalog-manifest", required=True, type=Path)
    parser.add_argument("--collector", required=True, type=Path)
    parser.add_argument("--collector-sha256", required=True)
    parser.add_argument("--selector-module", type=Path)
    parser.add_argument("--selector-sha256")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--minimum-candidates", type=int, default=30)
    parser.add_argument("--minimum-closed-sessions", type=int, default=3)
    parser.add_argument("--poll-seconds", type=int, default=600)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.poll_seconds < 60:
        parser.error("poll-seconds must be at least 60")
    while True:
        result = measure_readiness(
            sessions_root=args.sessions_root,
            catalog_manifest=args.catalog_manifest,
            collector_path=args.collector,
            collector_sha256=args.collector_sha256,
            minimum_candidates=args.minimum_candidates,
            minimum_closed_sessions=args.minimum_closed_sessions,
            selector_path=args.selector_module,
            selector_sha256=args.selector_sha256,
        )
        atomic_json(args.output.resolve(), result)
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "observed": result["observed"],
                    "deficits": result["deficits"],
                },
                sort_keys=True,
            ),
            flush=True,
        )
        if args.once:
            return 0
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
