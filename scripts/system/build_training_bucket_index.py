#!/usr/bin/env python3
"""Build a routeable index of SCBE training buckets.

This does not move or duplicate training files. It classifies existing local
surfaces into useful lanes so SFT, eval, upload, and archive steps can operate
from one manifest.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "training_buckets" / "latest"


@dataclass(frozen=True)
class BucketRule:
    bucket_id: str
    title: str
    purpose: str
    include: tuple[str, ...]
    exclude: tuple[str, ...] = ()
    gate: str = "manual review before training"


BUCKET_RULES: tuple[BucketRule, ...] = (
    BucketRule(
        bucket_id="coding_transport",
        title="Coding, Transport, and Bijective Token Work",
        purpose="Code primaries, binary/hexa transport, bijective mappings, Stage 6 repair, GeoSeal command recall.",
        include=(
            "training-data/sft/*code*",
            "training-data/sft/*coding*",
            "training-data/sft/*dsl*",
            "training-data/sft/*binary*",
            "training-data/sft/*atomic_workflow*",
            "training-data/sft/*geoseal_command*",
            "training-data/sft/*t_operator*",
            "training-data/sft/*typescript*",
            "src/tokenizer/**",
            "src/crypto/sacred_tongues.py",
            "tests/test_geoseal_cli_tokenizer_atomic.py",
        ),
        exclude=("**/__pycache__/**",),
        gate="coding smoke, slot preservation, deterministic round trip",
    ),
    BucketRule(
        bucket_id="aligned_foundations_chemistry",
        title="Aligned Foundations and Chemistry",
        purpose="Multi-representation math, English, Sacred Tongues, binary packet, chemistry, and coding substrate alignment.",
        include=(
            "training-data/sft/aligned_foundations*",
            "training-data/sft/chemistry_primary*",
            "training-data/sft/*foundation*",
            "training-data/sft/*tongue_name*",
            "training-data/sft/*layer_index*",
            "training-data/sft/*cross_tongue*",
            "training-data/sft/*multirep*",
            "notes/theory/atomic-tokenizer-chemistry-unified.md",
        ),
        gate="cross-lane concept preservation and packet compliance",
    ),
    BucketRule(
        bucket_id="agent_ops_harness",
        title="Agent Operations and Harness",
        purpose="Runnable CLI/operator behavior, command recall, browser traces, Apollo collection, HYDRA and agent-bus routing.",
        include=(
            "training-data/sft/operator_agent_bus*",
            "training-data/sft/command_lattice*",
            "training-data/sft/aetherbrowser*",
            "scripts/apollo/**",
            "scripts/system/*hydra*",
            "scripts/system/*agent*",
            "docs/architecture/AGENT_HARNESS_RESEARCH_AND_UPGRADE.md",
            "hydra/README.md",
        ),
        exclude=("**/__pycache__/**",),
        gate="exact command recall and fail-closed route behavior",
    ),
    BucketRule(
        bucket_id="governance_safety",
        title="Governance, Safety, and Boundary Decisions",
        purpose="ALLOW/QUARANTINE/ESCALATE/DENY behavior, null-space confidence, code governance, social contract guardrails.",
        include=(
            "training-data/sft/*governance*",
            "training-data/sft/*security*",
            "training-data/sft/*boundary*",
            "training-data/sft/*null_space*",
            "training-data/sft/l13*",
            "src/governance/**",
            "src/harmonic/state21_product_metric.py",
            "schemas/decision*.json",
            "docs/architecture/SOCIAL_CONSTRUCT_FRAMING_PILLARS_2026-04-28.md",
        ),
        exclude=("**/__pycache__/**",),
        gate="invalid-input regression and auditable decision record",
    ),
    BucketRule(
        bucket_id="interop_social_civic",
        title="Interop, Social Frames, and Civic Formations",
        purpose="View-dependent token overlays, cross-platform interpretation, HYDRA formations, civic/social framing devices.",
        include=(
            "src/interop/**",
            "tests/interop/test_view_token_envelope.py",
            "scripts/experiments/evaluate_view_token_overlay.py",
            "artifacts/interop/view_token_overlay_eval.json",
            "docs/architecture/VIEW_DEPENDENT_TOKENIZER_INTEROP_RESEARCH_2026-04-28.md",
            "docs/architecture/SOCIAL_CONSTRUCT_FRAMING_PILLARS_2026-04-28.md",
            "skills/codex-mirror/scbe-github-sweep-sorter/references/formations.md",
            "src/ai_brain/swarm-formation.ts",
        ),
        exclude=("**/__pycache__/**",),
        gate="dual-frame payload identity, formation route, and social appeal path",
    ),
    BucketRule(
        bucket_id="source_grounded_research",
        title="Source-Grounded Research Bridge",
        purpose="Citation-backed synthesis, paper/video/source extraction, external research grounding, and claim verification.",
        include=(
            "training-data/sft/research_bridge*",
            "docs/architecture/*RESEARCH*",
            "benchmarks/results/review_*",
            "content/articles/*research*",
        ),
        gate="source identity, falsifiable claim, and citation verification",
    ),
    BucketRule(
        bucket_id="story_manhwa_social",
        title="Story, Manhwa, Webtoon, and Social-State Signals",
        purpose="Narrative social-state interpretation, visible hierarchy, pacing, repair, character/canon continuity.",
        include=(
            "notes/manhwa-project/**",
            "artifacts/webtoon/**/*.md",
            "artifacts/webtoon/**/*.json",
            "content/book/**",
            "training-data/sft/*lore*",
            "training-data/sft/*story*",
        ),
        gate="canon/style eval, no coding merge unless explicitly paired",
    ),
    BucketRule(
        bucket_id="commerce_product_sidecar",
        title="Commerce and Product Sidecar",
        purpose="Offers, checkout, fulfillment, taxes, outreach, and product workflows kept outside the core coding/governance model.",
        include=(
            "training-data/sft/*tax*",
            "content/marketing/**",
            "products/**",
            "deliverables/SCBE_Production_Pack/**",
            "docs/benchmark-kit.html",
        ),
        gate="secret sweep, live/test separation, and fulfillment smoke",
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def unique_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    output: list[Path] = []
    for path in paths:
        key = str(path.resolve()).lower()
        if key in seen or not path.exists() or not path.is_file():
            continue
        seen.add(key)
        output.append(path)
    return sorted(output, key=lambda item: repo_rel(item).lower())


def matches_any(path: Path, patterns: tuple[str, ...]) -> bool:
    rel = repo_rel(path)
    return any(path.match(pattern) or Path(rel).match(pattern) for pattern in patterns)


def iter_rule_paths(rule: BucketRule) -> list[Path]:
    candidates: list[Path] = []
    for pattern in rule.include:
        candidates.extend(REPO_ROOT.glob(pattern))
    paths = unique_paths(candidates)
    if rule.exclude:
        paths = [path for path in paths if not matches_any(path, rule.exclude)]
    return paths


def count_jsonl_records(path: Path, max_bytes: int = 50_000_000) -> int | None:
    if path.suffix.lower() != ".jsonl" or path.stat().st_size > max_bytes:
        return None
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return sum(1 for line in handle if line.strip())
    except OSError:
        return None


def classify_file(path: Path) -> dict[str, Any]:
    stat = path.stat()
    record_count = count_jsonl_records(path)
    return {
        "path": repo_rel(path),
        "bytes": stat.st_size,
        "suffix": path.suffix.lower(),
        "records": record_count,
    }


def build_bucket_index() -> dict[str, Any]:
    buckets: list[dict[str, Any]] = []
    assigned: set[str] = set()
    for rule in BUCKET_RULES:
        files = [classify_file(path) for path in iter_rule_paths(rule)]
        for item in files:
            assigned.add(item["path"])
        total_records = sum(int(item["records"] or 0) for item in files)
        total_bytes = sum(int(item["bytes"]) for item in files)
        buckets.append(
            {
                "bucket_id": rule.bucket_id,
                "title": rule.title,
                "purpose": rule.purpose,
                "gate": rule.gate,
                "file_count": len(files),
                "known_jsonl_records": total_records,
                "total_bytes": total_bytes,
                "files": files,
            }
        )

    unassigned_sft = []
    for path in sorted((REPO_ROOT / "training-data" / "sft").glob("*"), key=lambda p: p.name.lower()):
        if not path.is_file():
            continue
        rel = repo_rel(path)
        if rel not in assigned:
            unassigned_sft.append(classify_file(path))

    return {
        "schema_version": "scbe_training_bucket_index_v1",
        "generated_at_utc": utc_now(),
        "core_rule": "Keep source files in place; train from bucket manifests; do not flat-merge across bucket gates.",
        "buckets": buckets,
        "unassigned_sft": unassigned_sft,
        "summary": {
            "bucket_count": len(buckets),
            "bucketed_file_count": sum(bucket["file_count"] for bucket in buckets),
            "bucketed_known_jsonl_records": sum(bucket["known_jsonl_records"] for bucket in buckets),
            "unassigned_sft_file_count": len(unassigned_sft),
            "unassigned_sft_known_jsonl_records": sum(int(item["records"] or 0) for item in unassigned_sft),
        },
    }


def render_markdown(index: dict[str, Any]) -> str:
    lines = [
        "# SCBE Training Bucket Index",
        "",
        f"Generated: {index['generated_at_utc']}",
        "",
        "## Rule",
        "",
        index["core_rule"],
        "",
        "## Buckets",
        "",
        "| Bucket | Files | Known JSONL Records | Bytes | Gate |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for bucket in index["buckets"]:
        lines.append(
            f"| `{bucket['bucket_id']}` | {bucket['file_count']} | {bucket['known_jsonl_records']} | {bucket['total_bytes']} | {bucket['gate']} |"
        )
    lines.extend(["", "## Bucket Details", ""])
    for bucket in index["buckets"]:
        lines.extend(
            [
                f"### {bucket['title']}",
                "",
                bucket["purpose"],
                "",
                f"Gate: {bucket['gate']}",
                "",
            ]
        )
        for item in bucket["files"][:40]:
            record_text = "" if item["records"] is None else f", records={item['records']}"
            lines.append(f"- `{item['path']}` ({item['bytes']} bytes{record_text})")
        if len(bucket["files"]) > 40:
            lines.append(f"- ... {len(bucket['files']) - 40} more files in JSON index")
        lines.append("")
    lines.extend(
        [
            "## Unassigned SFT",
            "",
            "These are not deleted or ignored. They need classification before joining a bucket.",
            "",
        ]
    )
    for item in index["unassigned_sft"][:80]:
        record_text = "" if item["records"] is None else f", records={item['records']}"
        lines.append(f"- `{item['path']}` ({item['bytes']} bytes{record_text})")
    if len(index["unassigned_sft"]) > 80:
        lines.append(f"- ... {len(index['unassigned_sft']) - 80} more files in JSON index")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SCBE training bucket index")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    index = build_bucket_index()
    json_path = output_dir / "training_bucket_index.json"
    md_path = output_dir / "TRAINING_BUCKET_INDEX.md"
    json_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(index), encoding="utf-8")
    print(
        json.dumps(
            {
                "bucket_count": index["summary"]["bucket_count"],
                "bucketed_file_count": index["summary"]["bucketed_file_count"],
                "unassigned_sft_file_count": index["summary"]["unassigned_sft_file_count"],
                "json": str(json_path),
                "markdown": str(md_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

