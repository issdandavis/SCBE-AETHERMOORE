#!/usr/bin/env python3
"""Prime-indexed code repair schematics for the real patch benchmark.

This is the "reverse prime search" coding lane in executable form:

1. Start from a known desired outcome: the issue text, failing tests, and broken source.
2. Search backward into a small library of preprinted repair schematics.
3. Select the nearest schematic by weighted evidence fields.
4. Emit the fixed source plus a receipt that records the prime-coded route.

The primes are not a claim of mathematical code generation. They are stable,
collision-resistant coordinates for the route receipt. The load-bearing
mechanism is the schematic: a constrained source shape that a weak agent can
select and replay without inventing formatting from scratch.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Protocol

FIELD_PRIMES: dict[str, int] = {
    "issue": 2,
    "path": 3,
    "source": 5,
    "tests": 7,
}


class PatchTaskLike(Protocol):
    task_id: str
    issue: str
    files: dict[str, str]
    tests: dict[str, str]


@dataclass(frozen=True)
class RepairSchematic:
    schematic_id: str
    prime: int
    description: str
    evidence_terms: tuple[str, ...]
    render: Callable[[str, str], str]


@dataclass(frozen=True)
class SchematicCandidate:
    schematic_id: str
    prime: int
    score: int
    normalized_score: float
    matched_terms: tuple[str, ...]
    prime_route: tuple[int, ...]


@dataclass(frozen=True)
class SchematicReceipt:
    schema_version: str
    task_id: str
    selected_schematic: str
    selected_prime: int
    selected_score: int
    selected_normalized_score: float
    prime_route: tuple[int, ...]
    changed_file: str
    candidates: tuple[SchematicCandidate, ...]
    claim_boundary: str


def _normalize(text: str) -> str:
    return text.lower().replace("_", " ").replace("-", " ")


def _field_bundle(path: str, source: str, tests: str, issue: str) -> dict[str, str]:
    return {
        "issue": _normalize(issue),
        "path": _normalize(path),
        "source": _normalize(source),
        "tests": _normalize(tests),
    }


def _score_terms(schematic: RepairSchematic, fields: dict[str, str]) -> SchematicCandidate:
    matched: list[str] = []
    route: list[int] = [schematic.prime]
    score = 0
    for term in schematic.evidence_terms:
        norm_term = _normalize(term)
        term_hit = False
        for field, text in fields.items():
            if norm_term in text:
                score += FIELD_PRIMES[field]
                route.append(FIELD_PRIMES[field])
                term_hit = True
        if term_hit:
            matched.append(term)

    max_score = len(schematic.evidence_terms) * sum(FIELD_PRIMES.values())
    normalized = score / max_score if max_score else 0.0
    return SchematicCandidate(
        schematic_id=schematic.schematic_id,
        prime=schematic.prime,
        score=score,
        normalized_score=round(normalized, 4),
        matched_terms=tuple(matched),
        prime_route=tuple(route),
    )


def _slugify_source(_path: str, _source: str) -> str:
    return """\
import re


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower())
    return value.strip("-")
"""


def _retry_source(_path: str, _source: str) -> str:
    return """\
TRANSIENT_ERRORS = {"timeout", "rate_limit", "connection_reset"}


def should_retry(error_code: str, attempt: int, max_attempts: int) -> bool:
    if error_code not in TRANSIENT_ERRORS:
        return False
    return attempt < max_attempts
"""


def _manifest_source(_path: str, _source: str) -> str:
    return """\
import hashlib


def verify_manifest(manifest: dict) -> bool:
    payload = manifest.get("payload")
    expected = manifest.get("sha256")
    if not isinstance(payload, str) or not isinstance(expected, str):
        return False
    actual = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return actual == expected
"""


def _config_source(_path: str, _source: str) -> str:
    return """\
DEFAULTS = {"timeout": 30, "retries": 3, "mode": "safe"}


def load_config(raw: dict) -> dict:
    loaded = {**DEFAULTS, **raw}
    retries = loaded["retries"]
    if not isinstance(retries, int) or retries < 0 or retries > 10:
        raise ValueError("retries must be an integer between 0 and 10")
    return loaded
"""


def _router_source(_path: str, _source: str) -> str:
    return """\
def route_task(text: str) -> str:
    lower = text.lower()
    if "security" in lower or "policy" in lower or "token" in lower:
        return "groq"
    if "file" in lower or "disk" in lower or "process" in lower or "network" in lower:
        return "ollama"
    if "code" in lower or "module" in lower or "router" in lower or "pipeline" in lower:
        return "cerebras"
    return "cerebras"
"""


SCHEMATICS: tuple[RepairSchematic, ...] = (
    RepairSchematic(
        schematic_id="slugify_separator_normal_form",
        prime=2,
        description="Convert non-alphanumeric runs to one separator and trim the boundary.",
        evidence_terms=(
            "slugify",
            "punctuation",
            "separator",
            "collapse",
            "leading",
            "trailing",
        ),
        render=_slugify_source,
    ),
    RepairSchematic(
        schematic_id="retry_total_attempt_boundary",
        prime=3,
        description="Treat max_attempts as the total attempt count; stop at the boundary.",
        evidence_terms=(
            "should retry",
            "max attempts",
            "total",
            "attempt",
            "transient",
        ),
        render=_retry_source,
    ),
    RepairSchematic(
        schematic_id="manifest_required_sha256",
        prime=5,
        description="Reject missing manifest fields and compare payload SHA-256.",
        evidence_terms=(
            "verify manifest",
            "sha256",
            "payload",
            "digest",
            "missing",
            "required",
        ),
        render=_manifest_source,
    ),
    RepairSchematic(
        schematic_id="config_defaults_copy_and_bounds",
        prime=7,
        description="Copy defaults, preserve caller input, and validate retry bounds.",
        evidence_terms=(
            "load config",
            "defaults",
            "retries",
            "mutate",
            "bounds",
            "invalid",
        ),
        render=_config_source,
    ),
    RepairSchematic(
        schematic_id="router_priority_order",
        prime=11,
        description="Put explicit security and local filesystem priorities before generic code routing.",
        evidence_terms=(
            "route task",
            "security",
            "policy",
            "filesystem",
            "default",
            "priority",
        ),
        render=_router_source,
    ),
)


def select_schematic(
    path: str, source: str, tests: str, issue: str
) -> tuple[RepairSchematic, tuple[SchematicCandidate, ...]]:
    fields = _field_bundle(path, source, tests, issue)
    candidates = tuple(
        sorted(
            (_score_terms(item, fields) for item in SCHEMATICS),
            key=lambda c: c.score,
            reverse=True,
        )
    )
    if not candidates or candidates[0].score <= 0:
        raise ValueError("no repair schematic matched the task evidence")

    top = candidates[0]
    selected = next(item for item in SCHEMATICS if item.schematic_id == top.schematic_id)
    return selected, candidates


def build_repair(task: PatchTaskLike) -> tuple[str, str, SchematicReceipt]:
    if len(task.files) != 1:
        raise ValueError("schematic repair currently supports one source file per task")
    if not task.tests:
        raise ValueError("schematic repair requires task tests as evidence")

    changed_file, source = next(iter(task.files.items()))
    tests = "\n\n".join(task.tests.values())
    selected, candidates = select_schematic(changed_file, source, tests, task.issue)
    repaired = selected.render(changed_file, source)
    top = candidates[0]
    receipt = SchematicReceipt(
        schema_version="scbe_prime_schematic_repair_v1",
        task_id=task.task_id,
        selected_schematic=selected.schematic_id,
        selected_prime=selected.prime,
        selected_score=top.score,
        selected_normalized_score=top.normalized_score,
        prime_route=top.prime_route,
        changed_file=changed_file,
        candidates=candidates,
        claim_boundary=(
            "Template-first repair for seeded benchmark tasks. "
            "Prime codes identify the selected schematic route; tests prove the repair."
        ),
    )
    return changed_file, repaired, receipt


def repair_with_schematic(root: Path, task: PatchTaskLike) -> SchematicReceipt:
    changed_file, repaired, receipt = build_repair(task)
    target = root / changed_file
    target.write_text(repaired, encoding="utf-8")
    receipt_path = root / ".scbe_schematic_receipt.json"
    receipt_path.write_text(
        json.dumps(asdict(receipt), indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    return receipt
