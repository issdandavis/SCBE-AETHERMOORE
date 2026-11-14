"""Build exact candidate spans for ordinary and retention source lanes.

The output is an evidence-preparation receipt only.  Every row remains
``NOT_REVIEWED`` and ineligible for training until a separate material dataset
manifest and source-authority ledger are reviewed and explicitly authorized.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable

SCHEMA = "clay.frozen-action-text-source-span-audit.v1"
ACTION_TERMS = (
    "action",
    "call",
    "continue",
    "execute",
    "jump",
    "move",
    "pass",
    "pull",
    "push",
    "return",
    "rotate",
    "run",
    "stop",
)
ACTION_TERM_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(term) for term in ACTION_TERMS) + r")\w*\b",
    re.IGNORECASE,
)
WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z'-]*")
FORBIDDEN_ACTION_MARKERS = ("<ACTION>", "<ACTION_PACKET>", " :: ")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _line_blocks(text: str) -> Iterable[tuple[int, int, str]]:
    """Yield zero-based, half-open nonblank line blocks and exact source text."""

    lines = text.splitlines(keepends=True)
    start: int | None = None
    for index, line in enumerate(lines):
        if line.strip():
            if start is None:
                start = index
            continue
        if start is not None:
            yield start, index, "".join(lines[start:index])
            start = None
    if start is not None:
        yield start, len(lines), "".join(lines[start:])


def _prompt_from_excerpt(excerpt: str) -> str:
    return " ".join(part.strip() for part in excerpt.splitlines() if part.strip())


def _candidate_reason(
    prompt: str,
    *,
    lane: str,
    min_prompt_bytes: int,
    max_prompt_bytes: int,
) -> str | None:
    encoded = prompt.encode("utf-8")
    if len(encoded) < min_prompt_bytes:
        return "too_short"
    if len(encoded) > max_prompt_bytes:
        return "too_long"
    if any(marker in prompt for marker in FORBIDDEN_ACTION_MARKERS):
        return "action_envelope_marker"
    if len(WORD_PATTERN.findall(prompt)) < 12:
        return "too_few_words"
    alpha = sum(character.isalpha() for character in prompt)
    if alpha / max(len(prompt), 1) < 0.5:
        return "low_language_ratio"
    if lane == "ordinary" and ACTION_TERM_PATTERN.search(prompt) is None:
        return "no_action_term"
    return None


def _scan_source(
    path: Path,
    *,
    source: str,
    source_family: str,
    lane: str,
    limit: int,
    min_prompt_bytes: int,
    max_prompt_bytes: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    rows: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()
    block_count = 0
    for start, end, excerpt in _line_blocks(text):
        block_count += 1
        prompt = _prompt_from_excerpt(excerpt)
        reason = _candidate_reason(
            prompt,
            lane=lane,
            min_prompt_bytes=min_prompt_bytes,
            max_prompt_bytes=max_prompt_bytes,
        )
        if reason is not None:
            rejected[reason] += 1
            continue
        action_terms = sorted({match.group(0).lower() for match in ACTION_TERM_PATTERN.finditer(prompt)})
        ordinal = len(rows)
        rows.append(
            {
                "action_terms": action_terms,
                "artifact_sha256": _sha256_file(path),
                "excerpt_sha256": _sha256_bytes(excerpt.encode("utf-8")),
                "lane": lane,
                "prompt": prompt,
                "prompt_bytes": len(prompt.encode("utf-8")),
                "prompt_sha256": _sha256_bytes(prompt.encode("utf-8")),
                "review_status": "NOT_REVIEWED",
                "source": source,
                "source_family": source_family,
                "source_id": f"{source}:{lane}:{ordinal:04d}",
                "span": {"end": end, "start": start, "unit": "line"},
                "training_eligible": False,
            }
        )
        if len(rows) >= limit:
            break
    summary = {
        "accepted_candidates": len(rows),
        "artifact_bytes": path.stat().st_size,
        "artifact_sha256": _sha256_file(path),
        "blocks_scanned": block_count,
        "lane": lane,
        "path": str(path),
        "rejection_counts": dict(sorted(rejected.items())),
        "source_family": source_family,
    }
    return rows, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ordinary", required=True, type=Path)
    parser.add_argument("--retention", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ledger-output", type=Path)
    parser.add_argument("--limit-per-source", type=int, default=64)
    parser.add_argument("--min-prompt-bytes", type=int, default=80)
    parser.add_argument("--max-prompt-bytes", type=int, default=512)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit_per_source <= 0:
        raise ValueError("--limit-per-source must be positive")
    if args.min_prompt_bytes <= 0 or args.max_prompt_bytes < args.min_prompt_bytes:
        raise ValueError("prompt byte bounds are invalid")

    ordinary = args.ordinary.resolve(strict=True)
    retention = args.retention.resolve(strict=True)
    ordinary_rows, ordinary_summary = _scan_source(
        ordinary,
        source="python-cpython-controlflow",
        source_family="python-cpython-documentation",
        lane="ordinary",
        limit=args.limit_per_source,
        min_prompt_bytes=args.min_prompt_bytes,
        max_prompt_bytes=args.max_prompt_bytes,
    )
    retention_rows, retention_summary = _scan_source(
        retention,
        source="rust-lang-book-control-flow",
        source_family="rust-lang-book",
        lane="retention",
        limit=args.limit_per_source,
        min_prompt_bytes=args.min_prompt_bytes,
        max_prompt_bytes=args.max_prompt_bytes,
    )
    if not ordinary_rows or not retention_rows:
        raise RuntimeError("both text lanes must produce at least one candidate")

    rows = ordinary_rows + retention_rows
    ledger_output = (args.ledger_output or args.output.with_suffix(".rows.jsonl")).resolve()
    ledger_text = "".join(_canonical_json(row) + "\n" for row in rows)
    _atomic_text(ledger_output, ledger_text)
    report = {
        "schema": SCHEMA,
        "status": "COMPLETE_NO_ADMISSION",
        "authority": {
            "dataset_admission": "NONE",
            "launch": "NONE",
            "partial_unfreeze": "NONE",
            "promotion": "NONE",
            "tool_dispatch": "DISABLED",
        },
        "filters": {
            "forbidden_action_markers": list(FORBIDDEN_ACTION_MARKERS),
            "limit_per_source": args.limit_per_source,
            "max_prompt_bytes": args.max_prompt_bytes,
            "min_prompt_bytes": args.min_prompt_bytes,
            "ordinary_requires_action_term": True,
        },
        "ledger": {
            "bytes": len(ledger_text.encode("utf-8")),
            "path": str(ledger_output),
            "rows": len(rows),
            "sha256": _sha256_bytes(ledger_text.encode("utf-8")),
        },
        "sources": {
            "python-cpython-controlflow": ordinary_summary,
            "rust-lang-book-control-flow": retention_summary,
        },
        "claim_boundary": (
            "These exact text spans are unreviewed ordinary/retention candidates only. "
            "They are not a material dataset, source-authority ledger, training "
            "authorization, or evidence of model retention or specificity."
        ),
    }
    output = args.output.resolve()
    _atomic_text(output, json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        _canonical_json(
            {
                "ledger_sha256": report["ledger"]["sha256"],
                "ordinary_candidates": len(ordinary_rows),
                "output": str(output),
                "retention_candidates": len(retention_rows),
                "status": report["status"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
