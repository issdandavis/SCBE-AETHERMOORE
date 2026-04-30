"""
Agent Bus event schema versioning + validation.

Every event written to events.jsonl carries a `_schema_version` field. This
module defines the current version, the migration table, and a validator
that the reader (or a verify CLI) can use to reject events from
unsupported future versions.

Versioning rule (semver-ish):
  - MAJOR bump = breaking change to event shape. Old readers MUST refuse.
  - MINOR bump = additive field. Old readers warn but proceed.
  - PATCH bump = doc-only. No validation impact.

Today's events are all `1.0.0`. As we add fields (e.g., `cost_usd`, signed
trace_id, etc.) we'll bump MINOR. If we ever rename or remove a required
field we'll bump MAJOR and ship a migration.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("scbe.agent_bus.schema")

CURRENT_SCHEMA_VERSION = "1.0.0"

# Required top-level fields for v1 events. The signing/audit fields are added
# by the signer at log time — they're checked separately.
V1_REQUIRED_FIELDS = ("task_type", "query", "timestamp", "success")

# Migration registry. Maps "from_version" -> callable(record) -> migrated record.
# Empty for now. When v1.1.0 lands we register an entry here so v1.0.0 events
# round-trip cleanly into the new shape.
MIGRATIONS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}


@dataclass
class ValidationResult:
    """Outcome of validating a single event."""

    ok: bool
    version: str
    reason: Optional[str] = None
    migrated: bool = False


@dataclass
class LogValidationReport:
    """Summary of validating an entire events.jsonl file."""

    total: int
    accepted: int
    rejected: int
    warnings: int
    rejections: List[Tuple[int, str]]  # [(line_no, reason), ...]
    version_counts: Dict[str, int]


def parse_version(v: str) -> Tuple[int, int, int]:
    """Parse a 'MAJOR.MINOR.PATCH' string into a 3-int tuple. Raises ValueError on garbage."""
    parts = v.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"version must be MAJOR.MINOR.PATCH, got {v!r}")
    return tuple(int(p) for p in parts)  # type: ignore[return-value]


def validate_event(record: Dict[str, Any]) -> ValidationResult:
    """Validate a single event. Returns ValidationResult, never raises."""
    raw_version = record.get("_schema_version")
    if raw_version is None:
        # Pre-versioning events from before this module landed. Treat as 1.0.0.
        raw_version = CURRENT_SCHEMA_VERSION

    try:
        major, minor, patch = parse_version(raw_version)
    except ValueError as exc:
        return ValidationResult(ok=False, version=raw_version, reason=f"unparseable version: {exc}")

    cur_major, cur_minor, _ = parse_version(CURRENT_SCHEMA_VERSION)

    # MAJOR mismatch above current = refuse (forward-incompatible)
    if major > cur_major:
        return ValidationResult(
            ok=False,
            version=raw_version,
            reason=f"event from future major version ({raw_version}); current reader is {CURRENT_SCHEMA_VERSION}",
        )

    # MAJOR mismatch below: try migration
    if major < cur_major:
        migration = MIGRATIONS.get(raw_version)
        if migration is None:
            return ValidationResult(
                ok=False,
                version=raw_version,
                reason=f"no migration registered for {raw_version} → {CURRENT_SCHEMA_VERSION}",
            )
        try:
            migration(record)
            return ValidationResult(ok=True, version=raw_version, migrated=True)
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(ok=False, version=raw_version, reason=f"migration failed: {exc}")

    # Same major. Newer minor = warn, accept.
    if minor > cur_minor:
        return ValidationResult(
            ok=True,
            version=raw_version,
            reason=f"event from newer minor version ({raw_version}); unknown fields ignored",
        )

    # Required fields check (v1)
    if major == 1:
        missing = [f for f in V1_REQUIRED_FIELDS if f not in record]
        if missing:
            return ValidationResult(ok=False, version=raw_version, reason=f"missing required v1 fields: {missing}")

    return ValidationResult(ok=True, version=raw_version)


def validate_log(path: Path) -> LogValidationReport:
    """Validate every event in a JSONL log. Reports per-line and totals."""
    rejections: List[Tuple[int, str]] = []
    accepted = 0
    rejected = 0
    warnings = 0
    versions: Dict[str, int] = {}

    if not path.exists():
        return LogValidationReport(0, 0, 0, 0, [], {})

    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                rejected += 1
                rejections.append((i, f"invalid JSON: {exc}"))
                continue

            result = validate_event(record)
            versions[result.version] = versions.get(result.version, 0) + 1
            if result.ok:
                accepted += 1
                if result.reason:
                    warnings += 1
            else:
                rejected += 1
                rejections.append((i, result.reason or "unknown"))

    total = accepted + rejected
    return LogValidationReport(
        total=total,
        accepted=accepted,
        rejected=rejected,
        warnings=warnings,
        rejections=rejections,
        version_counts=versions,
    )
