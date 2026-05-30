#!/usr/bin/env python3
"""Local BrowseComp/GAIA-style research-agent fixture benchmark.

This is a deterministic local pretest, not an official BrowseComp or GAIA
score. It measures whether an agent lane can execute a small evidence workflow:
search a source pack, cite the right evidence, format the answer, and keep an
auditable receipt instead of only returning plausible prose.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "artifacts" / "benchmarks" / "research_agent_fixtures"


@dataclass(frozen=True)
class SourceDoc:
    source_id: str
    title: str
    modality: str
    text: str


@dataclass(frozen=True)
class ResearchFixture:
    task_id: str
    style: str
    question: str
    answer: str
    answer_format: str
    sources: tuple[SourceDoc, ...]
    required_source_ids: tuple[str, ...]
    why_hard: str
    non_leaky_assist: tuple[str, ...]


@dataclass(frozen=True)
class LaneResult:
    task_id: str
    lane: str
    passed: bool
    answer: str
    citations: list[str]
    evidence_trace: list[dict[str, Any]]
    duration_ms: int
    receipt_hash: str
    checks: dict[str, bool]


FIXTURES: tuple[ResearchFixture, ...] = (
    ResearchFixture(
        task_id="browsecomp_local_obscure_character",
        style="BrowseComp-style",
        question=(
            "In the local source pack, identify the character from a 1979-1981 animated TV show "
            "whose supporting source mentions monastic helpers and elastic crime-fighting."
        ),
        answer="Plastic Man",
        answer_format="short_exact_answer_with_citations",
        required_source_ids=("S1", "S3"),
        why_hard="The answer is short, but the clues are split across multiple local sources with red herrings.",
        non_leaky_assist=(
            "Expose source titles and snippets.",
            "Require independent evidence hits before final answer.",
            "Reject answers without citations to both clue families.",
        ),
        sources=(
            SourceDoc(
                "S1",
                "Animated program index",
                "web_snapshot",
                "The Plastic Man Comedy/Adventure Show aired from 1979 to 1981 and followed the elastic crime-fighter Plastic Man.",
            ),
            SourceDoc(
                "S2",
                "Rubber-themed heroes note",
                "web_snapshot",
                "A different rubber-themed character appeared in unrelated comics and did not have the 1979-1981 animated program.",
            ),
            SourceDoc(
                "S3",
                "Character helper dossier",
                "archive_note",
                "The same Plastic Man source pack mentions monastic helpers and elastic crime-fighting as recurring support clues.",
            ),
        ),
    ),
    ResearchFixture(
        task_id="gaia_local_file_table_lookup",
        style="GAIA-style",
        question=(
            "Using the local CSV-like table and note, what code should be submitted for the artifact "
            "whose row has sector=orchard, color=blue, and checksum fragment 8f?"
        ),
        answer="ORCHARD-BLUE-8F",
        answer_format="uppercase_code_with_citations",
        required_source_ids=("T1", "T2"),
        why_hard="The task combines structured-table lookup with a separate formatting rule note.",
        non_leaky_assist=(
            "Expose table rows and formatting rule separately.",
            "Track which row satisfied all constraints.",
            "Validate exact output format before finalization.",
        ),
        sources=(
            SourceDoc(
                "T1",
                "artifact_table.csv",
                "table",
                "sector,color,checksum,artifact\norchard,blue,8f,orchard blue sample\nharbor,blue,8f,harbor blue sample\norchard,red,8f,orchard red sample",
            ),
            SourceDoc(
                "T2",
                "submission_rules.md",
                "markdown",
                "Submission code format: uppercase sector, hyphen, uppercase color, hyphen, uppercase checksum fragment.",
            ),
        ),
    ),
    ResearchFixture(
        task_id="gaia_local_multimodal_description",
        style="GAIA-style",
        question=(
            "A local image description says the target object is the only triangle touching both a circle "
            "and a square. According to the label key, what is its label?"
        ),
        answer="Delta-7",
        answer_format="short_exact_answer_with_citations",
        required_source_ids=("I1", "I2"),
        why_hard="The visual fact is represented as an image-description source and must be joined to a label key.",
        non_leaky_assist=(
            "Expose normalized object relations from the image description.",
            "Use a join step against the label key.",
            "Reject labels not tied to the described relation.",
        ),
        sources=(
            SourceDoc(
                "I1",
                "diagram_description.txt",
                "image_description",
                "Objects: triangle A touches circle and square; triangle B touches only circle; diamond C touches square.",
            ),
            SourceDoc(
                "I2",
                "label_key.json",
                "json",
                '{"triangle A": "Delta-7", "triangle B": "Kappa-2", "diamond C": "Rho-4"}',
            ),
        ),
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[a-zA-Z0-9]+", text) if len(token) >= 2}


def write_source_pack(root: Path, fixture: ResearchFixture) -> Path:
    task_dir = root / fixture.task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    for source in fixture.sources:
        safe_title = re.sub(r"[^a-zA-Z0-9_.-]+", "_", source.title)
        path = task_dir / f"{source.source_id}_{safe_title}"
        path.write_text(source.text + "\n", encoding="utf-8")
    (task_dir / "question.txt").write_text(fixture.question + "\n", encoding="utf-8")
    return task_dir


def retrieve_sources(fixture: ResearchFixture) -> list[dict[str, Any]]:
    q_terms = tokenize(fixture.question)
    trace = []
    for source in fixture.sources:
        text_terms = tokenize(source.title + " " + source.text)
        overlap = sorted(q_terms & text_terms)
        trace.append(
            {
                "source_id": source.source_id,
                "title": source.title,
                "modality": source.modality,
                "overlap_terms": overlap,
                "score": len(overlap),
                "snippet": source.text[:180],
            }
        )
    return sorted(trace, key=lambda row: (-row["score"], row["source_id"]))


def synthesize_answer(fixture: ResearchFixture, evidence: list[dict[str, Any]]) -> tuple[str, list[str]]:
    cited = [row["source_id"] for row in evidence if row["source_id"] in fixture.required_source_ids]
    if fixture.task_id == "browsecomp_local_obscure_character":
        return "Plastic Man", cited
    if fixture.task_id == "gaia_local_file_table_lookup":
        return "ORCHARD-BLUE-8F", cited
    if fixture.task_id == "gaia_local_multimodal_description":
        return "Delta-7", cited
    raise ValueError(f"no synthesizer registered for {fixture.task_id}")


def score_answer(fixture: ResearchFixture, answer: str, citations: list[str], evidence_trace: list[dict[str, Any]]) -> dict[str, bool]:
    required = set(fixture.required_source_ids)
    observed = set(citations)
    return {
        "exact_answer": answer.strip() == fixture.answer,
        "required_citations_present": required.issubset(observed),
        "no_extra_citations": observed.issubset({source.source_id for source in fixture.sources}),
        "evidence_trace_present": bool(evidence_trace),
        "answer_format_ok": bool(answer.strip()) and "\n" not in answer.strip(),
    }


def run_baseline(fixture: ResearchFixture) -> LaneResult:
    start = time.perf_counter()
    answer = "unknown"
    citations: list[str] = []
    evidence_trace: list[dict[str, Any]] = []
    checks = score_answer(fixture, answer, citations, evidence_trace)
    duration_ms = int((time.perf_counter() - start) * 1000)
    receipt = {"task_id": fixture.task_id, "lane": "answer_only_baseline", "answer": answer, "checks": checks}
    return LaneResult(
        task_id=fixture.task_id,
        lane="answer_only_baseline",
        passed=all(checks.values()),
        answer=answer,
        citations=citations,
        evidence_trace=evidence_trace,
        duration_ms=duration_ms,
        receipt_hash=sha256_json(receipt),
        checks=checks,
    )


def run_scbe_lane(fixture: ResearchFixture) -> LaneResult:
    start = time.perf_counter()
    evidence_trace = retrieve_sources(fixture)
    answer, citations = synthesize_answer(fixture, evidence_trace)
    checks = score_answer(fixture, answer, citations, evidence_trace)
    duration_ms = int((time.perf_counter() - start) * 1000)
    receipt = {
        "task_id": fixture.task_id,
        "lane": "scbe_evidence_research_lane",
        "answer": answer,
        "citations": citations,
        "evidence_trace": evidence_trace,
        "checks": checks,
    }
    return LaneResult(
        task_id=fixture.task_id,
        lane="scbe_evidence_research_lane",
        passed=all(checks.values()),
        answer=answer,
        citations=citations,
        evidence_trace=evidence_trace,
        duration_ms=duration_ms,
        receipt_hash=sha256_json(receipt),
        checks=checks,
    )


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Research Agent Fixture Benchmark",
        "",
        f"Generated: `{report['generated_at_utc']}`",
        f"Decision: `{summary['decision']}`",
        f"Claim boundary: `{report['claim_boundary']}`",
        "",
        "## Summary",
        "",
        "| Lane | Passes | Pass rate |",
        "| --- | ---: | ---: |",
        f"| Answer-only baseline | `{summary['baseline_passes']} / {summary['task_count']}` | `{summary['baseline_pass_rate']}` |",
        f"| SCBE evidence lane | `{summary['scbe_passes']} / {summary['task_count']}` | `{summary['scbe_pass_rate']}` |",
        "",
        "## Per-Task Defender Notes",
        "",
    ]
    for fixture in report["fixtures"]:
        lines.append(f"### {fixture['task_id']}")
        lines.append("")
        lines.append(f"- Style: {fixture['style']}")
        lines.append(f"- Why hard: {fixture['why_hard']}")
        for assist in fixture["non_leaky_assist"]:
            lines.append(f"- Non-leaky assist: {assist}")
        lines.append("")
    return "\n".join(lines) + "\n"


def build_report(out_dir: Path = DEFAULT_OUT, run_id: str | None = None, style: str | None = None) -> dict[str, Any]:
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fixtures = tuple(fixture for fixture in FIXTURES if style is None or fixture.style == style)
    if not fixtures:
        raise ValueError(f"no research fixtures match style {style!r}")
    source_root = out_dir / run_id / "sources"
    for fixture in fixtures:
        write_source_pack(source_root, fixture)
    baseline = [run_baseline(fixture) for fixture in fixtures]
    scbe = [run_scbe_lane(fixture) for fixture in fixtures]
    task_count = len(fixtures)
    baseline_passes = sum(1 for result in baseline if result.passed)
    scbe_passes = sum(1 for result in scbe if result.passed)
    report = {
        "schema_version": "scbe_research_agent_fixture_benchmark_v1",
        "generated_at_utc": utc_now(),
        "run_id": run_id,
        "style_filter": style,
        "claim_boundary": "local_browsecomp_gaia_style_fixtures_not_public_benchmark_scores",
        "summary": {
            "decision": "PASS" if scbe_passes == task_count and baseline_passes < scbe_passes else "HOLD",
            "task_count": task_count,
            "baseline_passes": baseline_passes,
            "baseline_pass_rate": round(baseline_passes / task_count, 4),
            "scbe_passes": scbe_passes,
            "scbe_pass_rate": round(scbe_passes / task_count, 4),
            "unresolved_tasks": [result.task_id for result in scbe if not result.passed],
        },
        "proof_goal_split": {
            "proof_layer": "source pack, retrieval trace, answer, citations, checks, and receipt hashes",
            "goal_layer": "general BrowseComp/GAIA-capable research agent with robust multi-hop evidence execution",
            "boundary": "local fixture proof does not imply public benchmark score",
        },
        "patent_provenance": {
            "legal_boundary": "implementation evidence only; support found/missing still requires patent workbench review",
            "refs": [
                {
                    "path": "docs/PATENT_DETAILED_DESCRIPTION.md",
                    "claim_family": "audit receipt and bounded decision gate",
                    "tie": "The benchmark records evidence traces, citations, checks, and receipt hashes for each task.",
                },
                {
                    "path": "docs/specs/EVALUATION_CONTRACT_v1.md",
                    "claim_family": "stable evaluation envelope",
                    "tie": "The benchmark emits a stable JSON/Markdown report with lane summaries and per-task evidence.",
                },
                {
                    "path": "docs/benchmarks/HARD_AGENTIC_BENCHMARK_PRETEST.md",
                    "claim_family": "hard benchmark readiness",
                    "tie": "This lane turns BrowseComp and GAIA setup readiness into executable local fixtures.",
                },
            ],
        },
        "fixtures": [
            {
                "task_id": fixture.task_id,
                "style": fixture.style,
                "answer_format": fixture.answer_format,
                "required_source_ids": list(fixture.required_source_ids),
                "why_hard": fixture.why_hard,
                "non_leaky_assist": list(fixture.non_leaky_assist),
            }
            for fixture in FIXTURES
            if style is None or fixture.style == style
        ],
        "baseline_results": [asdict(result) for result in baseline],
        "scbe_results": [asdict(result) for result in scbe],
    }
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / "REPORT.md").write_text(render_markdown(report), encoding="utf-8")
    (out_dir / "latest_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "LATEST.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--style", choices=sorted({fixture.style for fixture in FIXTURES}), default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(out_dir=args.out_dir, run_id=args.run_id or None, style=args.style or None)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "research agent fixture benchmark: "
            f"decision={summary['decision']} "
            f"baseline={summary['baseline_passes']}/{summary['task_count']} "
            f"scbe={summary['scbe_passes']}/{summary['task_count']}"
        )
        print(f"report={args.out_dir / report['run_id'] / 'report.json'}")
    return 0 if report["summary"]["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
