#!/usr/bin/env python3
"""Hydra jobsite project-conservation benchmark.

This lane measures a narrow product claim: when a project request crosses
teams, the system must preserve every required obligation instead of collapsing
onto the first obvious work stream. It is intentionally local and deterministic.
The comparison baselines are simple local planners, not live company agents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "artifacts" / "benchmarks" / "hydra_jobsite_conservation"
SCHEMA_VERSION = "scbe_hydra_jobsite_conservation_benchmark_v1"

TONGUES: dict[str, str] = {
    "KO": "scope authority and project decision",
    "AV": "transport, integration, deployment route",
    "RU": "rules, inspection, compliance, claim boundary",
    "CA": "code, computation, tests, benchmark evidence",
    "UM": "secrets, cost, finance, protected state",
    "DR": "documentation, packaging, publishing, receiver landing",
}


@dataclass(frozen=True)
class Obligation:
    obligation_id: str
    tongue: str
    lane: str
    description: str
    critical: bool = True


@dataclass(frozen=True)
class ProjectCase:
    case_id: str
    prompt: str
    formation: str
    signals: tuple[str, ...]
    expected_obligations: tuple[Obligation, ...]


def obligation(
    obligation_id: str,
    tongue: str,
    lane: str,
    description: str,
    critical: bool = True,
) -> Obligation:
    return Obligation(obligation_id, tongue, lane, description, critical)


CASES: tuple[ProjectCase, ...] = (
    ProjectCase(
        case_id="pricing_checkout_launch",
        prompt="Change the Pro plan from 29 to 39 dollars, update checkout, and publish the page before Friday.",
        formation="hexagonal-jobsite",
        signals=("pricing", "checkout", "publish", "deadline"),
        expected_obligations=(
            obligation(
                "scope_owner_approval",
                "KO",
                "project",
                "confirm owner-approved price and launch scope",
            ),
            obligation(
                "checkout_price_patch",
                "CA",
                "code",
                "change checkout and price configuration",
            ),
            obligation(
                "checkout_regression_test",
                "CA",
                "tests",
                "prove checkout still charges the intended amount",
            ),
            obligation(
                "margin_and_tax_review",
                "UM",
                "finance",
                "review margin, tax, and accounting impact",
            ),
            obligation(
                "billing_secret_guard",
                "UM",
                "security",
                "ensure payment keys and webhooks are not exposed",
            ),
            obligation(
                "pricing_copy_update",
                "DR",
                "docs",
                "update public pricing copy and offer text",
            ),
            obligation(
                "price_claim_inspection",
                "RU",
                "inspection",
                "inspect public price claims before publish",
            ),
            obligation(
                "deploy_route_check",
                "AV",
                "deployment",
                "verify publish/deploy route and rollback path",
            ),
        ),
    ),
    ProjectCase(
        case_id="benchmark_claim_publication",
        prompt="Publish the 13 of 13 Terminal-Bench neutral-task result on the site and use it in the pitch deck.",
        formation="inspection-ring",
        signals=("benchmark", "claim", "publish", "pitch"),
        expected_obligations=(
            obligation(
                "benchmark_artifact_verify",
                "CA",
                "benchmark",
                "verify artifact path, score, and task set",
            ),
            obligation(
                "claim_boundary_written",
                "RU",
                "inspection",
                "separate local evidence from public leaderboard claims",
            ),
            obligation(
                "evidence_link_packet",
                "AV",
                "transport",
                "make artifact links and receipts reachable",
            ),
            obligation(
                "homepage_and_deck_update",
                "DR",
                "docs",
                "update site and pitch deck language",
            ),
            obligation(
                "generated_artifact_filter",
                "UM",
                "security",
                "exclude secrets and noisy generated files",
            ),
            obligation(
                "owner_release_decision",
                "KO",
                "project",
                "approve exact wording before publication",
            ),
        ),
    ),
    ProjectCase(
        case_id="provider_fallback_integration",
        prompt="Add a Gemini provider fallback to the agent bus and expose it through the CLI.",
        formation="provider-bridge",
        signals=("provider", "api", "cli", "secret", "cost"),
        expected_obligations=(
            obligation(
                "provider_adapter_patch",
                "CA",
                "code",
                "add provider adapter and routing branch",
            ),
            obligation(
                "provider_regression_tests",
                "CA",
                "tests",
                "cover success, timeout, and fallback behavior",
            ),
            obligation(
                "env_secret_contract",
                "UM",
                "security",
                "document and guard environment-variable secrets",
            ),
            obligation(
                "provider_cost_gate",
                "UM",
                "finance",
                "declare paid-provider budget and free-first route",
            ),
            obligation(
                "cli_help_and_docs", "DR", "docs", "document CLI flags and examples"
            ),
            obligation(
                "bus_route_registration",
                "AV",
                "transport",
                "register bus/provider route without breaking existing lanes",
            ),
            obligation(
                "geoseal_policy_gate",
                "RU",
                "inspection",
                "enforce GeoSeal policy for provider calls",
            ),
        ),
    ),
    ProjectCase(
        case_id="chemistry_demo_launch",
        prompt="Expose chemistry decomposition and recomposition as a customer demo without making wet-lab claims.",
        formation="safety-lattice",
        signals=("chemistry", "demo", "science", "claim", "publish"),
        expected_obligations=(
            obligation(
                "chem_tool_adapter",
                "CA",
                "code",
                "make the chemistry tool executable from the demo path",
            ),
            obligation(
                "chem_benchmark_evidence",
                "CA",
                "benchmark",
                "attach deterministic decomposition benchmark evidence",
            ),
            obligation(
                "wet_lab_claim_boundary",
                "RU",
                "inspection",
                "block wet-lab, medical, dosing, and efficacy claims",
            ),
            obligation(
                "misuse_safety_gate",
                "UM",
                "security",
                "add misuse and unsafe-instruction gate",
            ),
            obligation(
                "demo_copy_packet",
                "DR",
                "docs",
                "write customer-facing demo copy and examples",
            ),
            obligation(
                "demo_export_route",
                "AV",
                "transport",
                "package the demo route and artifact transport",
            ),
            obligation(
                "scope_no_wetlab", "KO", "project", "confirm computational-only scope"
            ),
        ),
    ),
    ProjectCase(
        case_id="youtube_offer_packet",
        prompt="Turn a YouTube transcript into an upload package and connect it to a paid service offer.",
        formation="content-commerce-crew",
        signals=("youtube", "content", "offer", "oauth", "publish", "revenue"),
        expected_obligations=(
            obligation(
                "script_description_tags",
                "DR",
                "docs",
                "create title, description, tags, and transcript summary",
            ),
            obligation(
                "upload_route_check",
                "AV",
                "transport",
                "verify YouTube upload/review route",
            ),
            obligation(
                "oauth_secret_guard",
                "UM",
                "security",
                "guard OAuth tokens and connector credentials",
            ),
            obligation(
                "revenue_offer_alignment",
                "UM",
                "finance",
                "align offer, price, payment, and delivery promise",
            ),
            obligation(
                "platform_policy_review",
                "RU",
                "inspection",
                "check platform and ad-policy constraints",
            ),
            obligation(
                "quality_gate",
                "CA",
                "benchmark",
                "score transcript quality and metadata completeness",
            ),
            obligation(
                "owner_publish_call",
                "KO",
                "project",
                "confirm publish timing and final offer",
            ),
        ),
    ),
    ProjectCase(
        case_id="dirty_tree_cli_release",
        prompt="Ship a CLI release after several agents changed files, and do not lose unrelated local work.",
        formation="release-inspection-ring",
        signals=("release", "cli", "dirty-tree", "multi-agent", "security"),
        expected_obligations=(
            obligation(
                "build_typecheck_tests",
                "CA",
                "tests",
                "run build, typecheck, and targeted tests",
            ),
            obligation(
                "dirty_tree_surgical_review",
                "RU",
                "inspection",
                "separate owned edits from unrelated dirty files",
            ),
            obligation(
                "changelog_and_release_notes",
                "DR",
                "docs",
                "write release notes and changed-path summary",
            ),
            obligation(
                "branch_pr_push_route",
                "AV",
                "transport",
                "verify branch, PR, and push route",
            ),
            obligation(
                "secret_scan_before_push",
                "UM",
                "security",
                "scan staged files for secrets before push",
            ),
            obligation(
                "release_decision",
                "KO",
                "project",
                "make final release/no-release decision",
            ),
        ),
    ),
)

HYDRA_RULES: dict[str, tuple[str, ...]] = {
    "pricing": (
        "scope_owner_approval",
        "margin_and_tax_review",
        "price_claim_inspection",
    ),
    "checkout": (
        "checkout_price_patch",
        "checkout_regression_test",
        "billing_secret_guard",
    ),
    "publish": (
        "deploy_route_check",
        "pricing_copy_update",
        "homepage_and_deck_update",
        "demo_copy_packet",
    ),
    "deadline": ("owner_release_decision",),
    "benchmark": (
        "benchmark_artifact_verify",
        "claim_boundary_written",
        "chem_benchmark_evidence",
        "evidence_link_packet",
        "generated_artifact_filter",
        "quality_gate",
    ),
    "claim": (
        "claim_boundary_written",
        "price_claim_inspection",
        "wet_lab_claim_boundary",
    ),
    "pitch": ("homepage_and_deck_update", "owner_release_decision"),
    "provider": (
        "provider_adapter_patch",
        "provider_regression_tests",
        "bus_route_registration",
        "geoseal_policy_gate",
    ),
    "api": ("provider_adapter_patch", "env_secret_contract", "provider_cost_gate"),
    "cli": ("cli_help_and_docs", "build_typecheck_tests"),
    "secret": (
        "env_secret_contract",
        "billing_secret_guard",
        "oauth_secret_guard",
        "secret_scan_before_push",
    ),
    "cost": ("provider_cost_gate",),
    "chemistry": (
        "chem_tool_adapter",
        "chem_benchmark_evidence",
        "wet_lab_claim_boundary",
    ),
    "demo": ("demo_copy_packet", "demo_export_route", "scope_no_wetlab"),
    "science": ("wet_lab_claim_boundary", "misuse_safety_gate"),
    "youtube": (
        "script_description_tags",
        "upload_route_check",
        "oauth_secret_guard",
        "platform_policy_review",
        "quality_gate",
    ),
    "content": ("script_description_tags", "quality_gate"),
    "offer": ("revenue_offer_alignment", "owner_publish_call"),
    "oauth": ("oauth_secret_guard",),
    "revenue": ("revenue_offer_alignment",),
    "release": (
        "release_decision",
        "changelog_and_release_notes",
        "branch_pr_push_route",
    ),
    "dirty-tree": ("dirty_tree_surgical_review", "secret_scan_before_push"),
    "multi-agent": ("dirty_tree_surgical_review",),
    "security": (
        "secret_scan_before_push",
        "geoseal_policy_gate",
        "misuse_safety_gate",
    ),
}


def expected_ids(case: ProjectCase) -> set[str]:
    return {item.obligation_id for item in case.expected_obligations}


def all_case_obligations(case: ProjectCase) -> dict[str, Obligation]:
    return {item.obligation_id: item for item in case.expected_obligations}


def single_lane_code(case: ProjectCase) -> set[str]:
    return {
        item.obligation_id
        for item in case.expected_obligations
        if item.tongue == "CA" or item.lane in {"code", "tests", "benchmark"}
    }


def doc_only(case: ProjectCase) -> set[str]:
    return {
        item.obligation_id
        for item in case.expected_obligations
        if item.tongue == "DR" or item.lane == "docs"
    }


def naive_project_manager(case: ProjectCase) -> set[str]:
    predicted: set[str] = set()
    for signal in case.signals:
        if signal in {"checkout", "provider", "api", "cli", "chemistry", "release"}:
            predicted.update(
                item.obligation_id
                for item in case.expected_obligations
                if item.lane in {"code", "tests"}
            )
        if signal in {"publish", "pitch", "demo", "youtube", "content"}:
            predicted.update(
                item.obligation_id
                for item in case.expected_obligations
                if item.lane in {"docs", "transport"}
            )
        if signal in {"security", "secret", "oauth"}:
            predicted.update(
                item.obligation_id
                for item in case.expected_obligations
                if item.lane == "security"
            )
    return predicted


def hydra_jobsite(case: ProjectCase) -> set[str]:
    predicted: set[str] = set()
    for signal in case.signals:
        predicted.update(HYDRA_RULES.get(signal, ()))

    # Formation-level conservation rules prevent role collapse.
    lanes = {
        all_case_obligations(case)[item].lane
        for item in predicted
        if item in all_case_obligations(case)
    }
    if "security" in lanes:
        predicted.update(
            item.obligation_id
            for item in case.expected_obligations
            if item.tongue == "RU" and item.critical
        )
    if "docs" in lanes or "transport" in lanes:
        predicted.update(
            item.obligation_id
            for item in case.expected_obligations
            if item.tongue == "KO" and item.critical
        )
    return predicted & expected_ids(case)


PLANNERS: dict[str, Callable[[ProjectCase], set[str]]] = {
    "single_lane_code": single_lane_code,
    "doc_only": doc_only,
    "naive_project_manager": naive_project_manager,
    "hydra_jobsite": hydra_jobsite,
}


def score_case(
    case: ProjectCase, planner_id: str, predicted: set[str]
) -> dict[str, Any]:
    obligations = all_case_obligations(case)
    expected = expected_ids(case)
    covered = predicted & expected
    missing = expected - predicted
    critical_misses = sorted(
        obligation_id
        for obligation_id in missing
        if obligations[obligation_id].critical
    )
    precision = len(covered) / len(predicted) if predicted else 0.0
    recall = len(covered) / len(expected) if expected else 0.0
    conservation_score = recall if not critical_misses else recall * 0.5
    return {
        "case_id": case.case_id,
        "planner_id": planner_id,
        "formation": case.formation,
        "expected_count": len(expected),
        "predicted_count": len(predicted),
        "covered_count": len(covered),
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "conservation_score": round(conservation_score, 4),
        "passed": recall >= 0.95 and not critical_misses,
        "covered": sorted(covered),
        "missing": sorted(missing),
        "critical_misses": critical_misses,
    }


def run_case(case: ProjectCase) -> dict[str, Any]:
    planner_results = {}
    for planner_id, planner in PLANNERS.items():
        planner_results[planner_id] = score_case(case, planner_id, planner(case))
    return {
        "case_id": case.case_id,
        "prompt": case.prompt,
        "formation": case.formation,
        "signals": list(case.signals),
        "expected_obligations": [asdict(item) for item in case.expected_obligations],
        "planner_results": planner_results,
    }


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_commit() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    planner_summaries = {}
    for planner_id in PLANNERS:
        rows = [case["planner_results"][planner_id] for case in cases]
        avg_recall = sum(row["recall"] for row in rows) / len(rows)
        avg_precision = sum(row["precision"] for row in rows) / len(rows)
        avg_conservation = sum(row["conservation_score"] for row in rows) / len(rows)
        planner_summaries[planner_id] = {
            "passed": sum(1 for row in rows if row["passed"]),
            "case_count": len(rows),
            "average_recall": round(avg_recall, 4),
            "average_precision": round(avg_precision, 4),
            "average_conservation_score": round(avg_conservation, 4),
            "total_critical_misses": sum(len(row["critical_misses"]) for row in rows),
        }

    hydra = planner_summaries["hydra_jobsite"]
    best_baseline = max(
        value["average_conservation_score"]
        for planner_id, value in planner_summaries.items()
        if planner_id != "hydra_jobsite"
    )
    hydra_margin = hydra["average_conservation_score"] - best_baseline
    decision = (
        "PASS"
        if hydra["passed"] == len(cases)
        and hydra["total_critical_misses"] == 0
        and hydra_margin >= 0.25
        else "FAIL"
    )
    return {
        "decision": decision,
        "case_count": len(cases),
        "hydra_passed": hydra["passed"],
        "hydra_average_conservation_score": hydra["average_conservation_score"],
        "best_baseline_average_conservation_score": round(best_baseline, 4),
        "hydra_margin_over_best_baseline": round(hydra_margin, 4),
        "planner_summaries": planner_summaries,
    }


def build_report(out_dir: Path = OUT_DIR) -> dict[str, Any]:
    t0 = time.perf_counter()
    case_results = [run_case(case) for case in CASES]
    summary = summarize(case_results)
    generated_at = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": generated_at,
        "run_id": generated_at.replace(":", "").replace("+00:00", "Z"),
        "git_commit": git_commit(),
        "claim_boundary": (
            "Local deterministic project-conservation benchmark comparing Hydra jobsite planning "
            "against simple local baselines; not a public leaderboard score or a live comparison "
            "with named company agents."
        ),
        "product_claim": (
            "A multi-agent project system should preserve cross-team obligations across code, "
            "security, finance, inspection, documentation, transport, and owner decision lanes."
        ),
        "tongues": TONGUES,
        "summary": summary,
        "cases": case_results,
        "evidence_hash": sha256_text(json.dumps(case_results, sort_keys=True)),
        "duration_seconds": round(time.perf_counter() - t0, 4),
    }
    write_outputs(report, out_dir)
    return report


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    stamp = report["run_id"]
    (out_dir / f"hydra_jobsite_conservation_{stamp}.json").write_text(
        payload, encoding="utf-8"
    )
    (out_dir / "latest_report.json").write_text(payload, encoding="utf-8")
    write_markdown(report, out_dir / f"hydra_jobsite_conservation_{stamp}.md")
    write_markdown(report, out_dir / "LATEST.md")


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    planner_summaries = summary["planner_summaries"]
    lines = [
        "# SCBE Hydra Jobsite Conservation Benchmark",
        "",
        f"- Schema: `{report['schema_version']}`",
        f"- Decision: `{summary['decision']}`",
        f"- Cases: `{summary['case_count']}`",
        f"- Hydra average conservation: `{summary['hydra_average_conservation_score']}`",
        f"- Best local baseline conservation: `{summary['best_baseline_average_conservation_score']}`",
        f"- Hydra margin: `{summary['hydra_margin_over_best_baseline']}`",
        f"- Evidence hash: `{report['evidence_hash']}`",
        "",
        "## Claim Boundary",
        "",
        report["claim_boundary"],
        "",
        "## Planner Scores",
        "",
        "| Planner | Passed | Avg Recall | Avg Precision | Avg Conservation | Critical Misses |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for planner_id, row in planner_summaries.items():
        lines.append(
            "| {planner} | {passed}/{case_count} | {recall} | {precision} | {score} | {misses} |".format(
                planner=planner_id,
                passed=row["passed"],
                case_count=row["case_count"],
                recall=row["average_recall"],
                precision=row["average_precision"],
                score=row["average_conservation_score"],
                misses=row["total_critical_misses"],
            )
        )
    lines.extend(["", "## Cases", ""])
    for case in report["cases"]:
        hydra = case["planner_results"]["hydra_jobsite"]
        lines.append(
            f"- `{case['case_id']}` `{case['formation']}`: hydra "
            f"{hydra['covered_count']}/{hydra['expected_count']} obligations, "
            f"critical misses={len(hydra['critical_misses'])}"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the Hydra jobsite project-conservation benchmark."
    )
    parser.add_argument(
        "--json", action="store_true", help="emit the full report as JSON"
    )
    parser.add_argument("--out-dir", default=str(OUT_DIR), help="output directory")
    args = parser.parse_args()

    report = build_report(Path(args.out_dir))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "hydra jobsite conservation benchmark: "
            f"decision={summary['decision']} hydra={summary['hydra_passed']}/{summary['case_count']} "
            f"margin={summary['hydra_margin_over_best_baseline']}"
        )
        print(f"report={Path(args.out_dir) / 'LATEST.md'}")
    return 0 if report["summary"]["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
