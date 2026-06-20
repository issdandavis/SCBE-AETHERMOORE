#!/usr/bin/env python3
"""Benchmark the geometry-aware SCBE swarm router.

This benchmark measures the harness behavior, not coding intelligence in the
abstract. It checks whether agent profiles resolve, whether local/free lanes
produce promotable work, and whether the router escalates when the free lanes
fail quality gates.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SWARM = REPO_ROOT / "scripts" / "system" / "scbe_swarm_router.py"
FUNCTIONAL_CODING_BENCH = REPO_ROOT / "scripts" / "eval" / "functional_coding_agent_benchmark.py"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "benchmarks" / "scbe_swarm_router"
SELF_CLI_TASK_FILE = REPO_ROOT / "config" / "eval" / "scbe_productivity_eval_tasks.v1.json"
DEFAULT_SELF_CLI_MODELS = ("openclaw:latest", "qwen2.5-coder:1.5b", "qwen3-coder:480b-cloud")

PUBLIC_BENCHMARK_TARGETS = (
    {
        "name": "SWE-bench Verified",
        "url": "https://www.swebench.com/verified.html",
        "what_it_tests": "Real GitHub issue resolution on a human-validated 500-task subset.",
        "scbe_gap": "Needs a safe_apply loop that produces and verifies real patches against held-out issues.",
    },
    {
        "name": "Terminal-Bench",
        "url": "https://terminalbench.lol/",
        "what_it_tests": "End-to-end terminal work in sandboxed environments with observable command/file outcomes.",
        "scbe_gap": (
            "Needs a terminal task adapter that runs the router inside a sandbox and grades final files/results."
        ),
    },
    {
        "name": "Vexp SWE-bench harness",
        "url": "https://github.com/Vexp-ai/vexp-swe-bench",
        "what_it_tests": "Agent comparison on a curated SWE-bench Verified subset with cost and speed tracking.",
        "scbe_gap": "Needs per-run cost/latency accounting and a standard adapter for external coding agents.",
    },
)

FIXED_DECLARATION_KEYS = (
    "task_id",
    "task_intent",
    "persona",
    "output_contract",
    "constraint_mode",
    "allowed_paths",
    "focus_paths",
    "agent_set",
    "cloud_policy",
    "runtime",
    "gate_state",
    "interpretation",
)

HEXAGONAL_CONSENSUS_FACES = (
    "task_intent",
    "output_contract",
    "path_scope",
    "model_lane",
    "gate_state",
    "evidence_trace",
)

QUALITY_FLAG_REPAIR_RULES = {
    "decision_missing_or_ambiguous": {
        "weakness": "ambiguous_lane_decision",
        "why_we_lose": (
            "Agent benchmarks need machine-graded final states; ambiguous decisions cannot be routed safely."
        ),
        "patch_direction": (
            "Tighten output contracts or post-parse decisions so every lane resolves to one exact decision."
        ),
    },
    "path_not_found": {
        "weakness": "nonexistent_file_reference",
        "why_we_lose": (
            "Applicable patches require real files; public coding benchmarks reject changes aimed at missing paths."
        ),
        "patch_direction": (
            "Filter file mentions against repo inventory and force needs-human/defer when a target file is absent."
        ),
    },
    "placeholder_diff_index": {
        "weakness": "placeholder_patch_metadata",
        "why_we_lose": "Patch applicators need real unified diffs, not illustrative examples.",
        "patch_direction": "Reject placeholder diff metadata before builder promotion and request a narrower patch.",
    },
    "placeholder_implementation": {
        "weakness": "placeholder_implementation_body",
        "why_we_lose": "Benchmarks grade completed behavior; placeholders are indistinguishable from incomplete work.",
        "patch_direction": "Require complete diff hunks or downgrade the lane to evidence/defer.",
    },
    "verification_mutates_git_state": {
        "weakness": "unsafe_verification_command",
        "why_we_lose": (
            "Benchmark verification must be reproducible and non-mutating unless the harness explicitly applies a "
            "patch."
        ),
        "patch_direction": "Whitelist test/read-only verification verbs and reject git add/commit/push in lane output.",
    },
    "lane_failed": {
        "weakness": "model_lane_runtime_failure",
        "why_we_lose": (
            "A multi-agent benchmark cannot depend on a lane that fails silently; public harnesses need every lane "
            "failure to become an isolated, reproducible repair target."
        ),
        "patch_direction": (
            "Record the failed lane, model, surface, and task; rerun the failed adapter alone with narrower context "
            "or a stronger guard model."
        ),
    },
    "blacklisted_path": {
        "weakness": "blacklisted_path_reference",
        "why_we_lose": (
            "A safe coding harness must block proposals that reach into forbidden or operator-only paths before they "
            "can become patches."
        ),
        "patch_direction": (
            "Keep blacklisted paths blocked, but route the lane to an evidence/defer contract with the nearest "
            "allowed implementation path."
        ),
    },
}

QUALITY_FLAG_FACE_MAP = {
    "evidence_symbol_not_found": "evidence_trace",
    "symbol_not_found": "evidence_trace",
    "path_outside_lane": "path_scope",
    "path_not_found": "path_scope",
    "decision_missing_or_ambiguous": "gate_state",
    "placeholder_diff_index": "gate_state",
    "placeholder_implementation": "gate_state",
    "verification_mutates_git_state": "gate_state",
    "non_git_unified_diff_context": "gate_state",
    "lane_failed": "model_lane",
    "blacklisted_path": "path_scope",
}

KAGGLE_WINNER_STAGE_ORDER = (
    "baseline",
    "feature_packet",
    "ensemble_consensus",
    "postprocess_repair",
)

KAGGLE_WINNER_STAGES = {
    "baseline": {
        "name": "Baseline run",
        "goal": "Run the smallest comparable router lane before adding helpers.",
        "case_ids": {"dry_full_catalog", "single_local_openclaw", "local_openclaw_hermes"},
    },
    "feature_packet": {
        "name": "Feature and evidence packet",
        "goal": "Improve inputs before asking models to generate: focus paths, declarations, and task variables.",
        "case_ids": {"semantic_inner_task_tracking", "operator_user", "public_free_user", "admin_operator"},
    },
    "ensemble_consensus": {
        "name": "Ensemble consensus",
        "goal": "Compare independent lanes and promote only near-fixed declarations with traceable evidence.",
        "case_ids": {"free_triage", "cloud_opencode_codex", "internal_ai_lane"},
    },
    "postprocess_repair": {
        "name": "Postprocess and repair",
        "goal": "Apply deterministic validators, safe patch probes, and weakness-to-repair loops.",
        "case_ids": {"safe_apply_sandbox_patch_probe"},
    },
}

QUALITY_DIMENSION_REPAIR_TASKS = {
    "actionability": "Tighten next_action mapping so every pass names exactly one executable follow-up.",
    "efficiency": "Reduce context and lane count before escalating model size.",
    "evidence_integrity": "Add deterministic symbol/file lookup before model evidence synthesis.",
    "gate_contract": "Repair parser/schema issues before testing larger model swarms.",
    "patch_readiness": "Route builder lanes through safe_apply-ready unified diff contracts.",
    "traceability": "Require run_dir, routing.json, assurance_packet, and lane artifacts before promotion.",
}


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    task: str
    agents: str
    timeout: int
    max_workers: int
    persona: str = "operator"
    allowed_paths: str = ""
    output_contract: str = "patch-proposal"
    constraint_mode: str = "strict"
    dry_run: bool = False
    allow_ollama_cloud: bool = False
    prefer_ollama_cloud: bool = False
    focus_paths: str = ""


QUICK_CASES = (
    BenchmarkCase(
        case_id="dry_full_catalog",
        task="Map all free Ollama launch agents into geometry roles. Proposal only, no edits.",
        agents="claude,openclaw,hermes,opencode,codex,copilot,droid,pi",
        timeout=20,
        max_workers=1,
        dry_run=True,
    ),
    BenchmarkCase(
        case_id="single_local_openclaw",
        task="Find one safe next improvement for the SCBE swarm router. Proposal only, no edits.",
        agents="openclaw",
        timeout=45,
        max_workers=1,
    ),
    BenchmarkCase(
        case_id="free_triage",
        task="Check the free-first geometry router. Proposal only, no edits.",
        agents="openclaw,hermes,pi",
        timeout=45,
        max_workers=1,
    ),
)

FULL_CASES = QUICK_CASES + (
    BenchmarkCase(
        case_id="code_pair",
        task="Find one testable improvement for AetherDesk routing. Proposal only, no edits.",
        agents="opencode,codex",
        timeout=60,
        max_workers=1,
    ),
    BenchmarkCase(
        case_id="full_catalog_throttled",
        task="Find one safe next improvement for AetherDesk. Proposal only, no edits.",
        agents="claude,openclaw,hermes,opencode,codex,copilot,droid,pi",
        timeout=60,
        max_workers=2,
    ),
)

SHORT_TASK = "Find one safe improvement for the SCBE swarm router. Proposal only, no edits."
MEDIUM_TASK = (
    "Find one safe improvement for the SCBE swarm router that improves free-first routing, "
    "artifact clarity, or AetherDesk operator visibility. Proposal only, no edits. Prefer existing files."
)
LONG_TASK = (
    "Evaluate the SCBE swarm router as a multi-agent engineering system. Find one safe improvement that helps "
    "many free/local agent surfaces work on one project without conflicts. The improvement should preserve the "
    "free-first policy, keep paid models as escalation-only critics or final integrators, produce useful notes, "
    "citations, and changelog surfaces, avoid direct repo mutation, and make the next safe_apply step clearer. "
    "Proposal only, no edits."
)

CONCURRENCY_CASES = tuple(
    BenchmarkCase(
        case_id=f"{length}_{mode}_workers{workers}",
        task=task,
        agents="openclaw,hermes,pi",
        timeout=45,
        max_workers=workers,
        constraint_mode=mode,
    )
    for length, task in (("short", SHORT_TASK), ("medium", MEDIUM_TASK), ("long", LONG_TASK))
    for mode in ("strict", "relaxed")
    for workers in (1, 3)
)

OLLAMA_CLOUD_CASES = (
    BenchmarkCase(
        case_id="local_openclaw_hermes",
        task="Find one safe improvement for the SCBE swarm router. Proposal only, no edits.",
        agents="openclaw,hermes",
        timeout=45,
        max_workers=1,
        constraint_mode="relaxed",
        focus_paths=(
            "scripts/system/scbe_swarm_router.py,scripts/system/openclaw_swarm.py,tests/test_openclaw_swarm.py,"
            "scripts/benchmark/openclaw_swarm_benchmark.py"
        ),
    ),
    BenchmarkCase(
        case_id="cloud_opencode_codex",
        task="Find one safe improvement for the SCBE swarm router. Proposal only, no edits.",
        agents="opencode,codex",
        timeout=90,
        max_workers=1,
        constraint_mode="relaxed",
        allow_ollama_cloud=True,
        prefer_ollama_cloud=True,
        focus_paths=(
            "scripts/system/scbe_swarm_router.py,scripts/system/openclaw_swarm.py,tests/test_openclaw_swarm.py,"
            "scripts/benchmark/openclaw_swarm_benchmark.py"
        ),
    ),
)

ROLE_CASES = (
    BenchmarkCase(
        case_id="public_free_user",
        persona="public_free_user",
        task=(
            "Public free user role: explain what this SCBE bus can do without paid models or repo mutation. "
            "Return a safe capability answer and one next action. No code, no patch, no file mutation."
        ),
        agents="openclaw",
        timeout=45,
        max_workers=1,
        allowed_paths="docs/,aetherdesk/",
        output_contract="answer",
        constraint_mode="relaxed",
        focus_paths="aetherdesk/README.md,docs/research/SCBE_SWARM_ROUTER_COMPARISON_2026-05-10.md",
    ),
    BenchmarkCase(
        case_id="operator_user",
        persona="operator_user",
        task=(
            "Operator user role: find one safe improvement to the headless SCBE swarm router using existing files. "
            "Proposal only, no edits."
        ),
        agents="openclaw,hermes",
        timeout=60,
        max_workers=1,
        allowed_paths="scripts/,tests/,docs/",
        constraint_mode="strict",
        focus_paths="scripts/system/openclaw_swarm.py,scripts/system/scbe_swarm_router.py,tests/test_openclaw_swarm.py",
    ),
    BenchmarkCase(
        case_id="admin_operator",
        persona="admin_operator",
        task=(
            "Admin role: inspect whether package, deploy, or workflow surfaces need a guarded change. "
            "If touching greylisted files, explain approval need instead of patching. Proposal only, no edits."
        ),
        agents="openclaw,pi",
        timeout=60,
        max_workers=1,
        allowed_paths="scripts/,tests/,docs/,package.json,vercel.json,.github/workflows/",
        constraint_mode="strict",
        focus_paths="package.json,vercel.json,scripts/benchmark/openclaw_swarm_benchmark.py",
    ),
    BenchmarkCase(
        case_id="internal_ai_lane",
        persona="internal_ai_lane",
        task=(
            "Internal AI lane role: behave as a helper/guard inside the system. Gather file evidence for the next "
            "builder cycle and avoid proposing code unless declarations exist. Evidence only, no patch, no edits."
        ),
        agents="codex,opencode",
        timeout=90,
        max_workers=1,
        allowed_paths="scripts/,tests/,docs/",
        output_contract="evidence",
        constraint_mode="strict",
        allow_ollama_cloud=True,
        prefer_ollama_cloud=True,
        focus_paths=(
            "scripts/system/openclaw_swarm.py,scripts/system/scbe_swarm_router.py,tests/test_openclaw_swarm.py,"
            "docs/research/DARPA_AGENTIC_SYSTEM_ALIGNMENT_2026-05-10.md"
        ),
    ),
)

SEMANTIC_CASES = (
    BenchmarkCase(
        case_id="semantic_inner_task_tracking",
        persona="internal_ai_lane",
        task=(
            "Semantic benchmark role: track the inner task variables for improving the SCBE swarm router. "
            "Gather evidence about task intent, output contract, allowed paths, quality gates, and next cycle. "
            "Evidence only, no patch, no edits."
        ),
        agents="openclaw,hermes",
        timeout=90,
        max_workers=1,
        allowed_paths="scripts/,tests/,docs/",
        output_contract="evidence",
        constraint_mode="strict",
        focus_paths=(
            "scripts/system/openclaw_swarm.py,"
            "scripts/system/scbe_swarm_router.py,"
            "scripts/benchmark/openclaw_swarm_benchmark.py,"
            "tests/test_openclaw_swarm.py,"
            "docs/research/SCBE_BUS_TASK_KNOWLEDGE_GRAPH_2026-05-10.json"
        ),
    ),
)

KAGGLE_LOOP_CASES = (
    QUICK_CASES[0],
    QUICK_CASES[1],
    SEMANTIC_CASES[0],
    ROLE_CASES[1],
    ROLE_CASES[3],
    OLLAMA_CLOUD_CASES[1],
)

PUBLIC_PARALLEL_CASES = (
    BenchmarkCase(
        case_id="public_swebench_verified_adapter",
        persona="public_benchmark_adapter",
        task=(
            "Public benchmark adapter role: inspect what is needed to run SCBE swarm router against SWE-bench "
            "Verified without claiming a score. Evidence only: adapter requirements, missing commands, grading "
            "surface, and one next implementation step."
        ),
        agents="openclaw",
        timeout=75,
        max_workers=1,
        allowed_paths="scripts/,tests/,docs/",
        output_contract="evidence",
        constraint_mode="strict",
        focus_paths=(
            "scripts/benchmark/openclaw_swarm_benchmark.py,"
            "scripts/system/scbe_swarm_router.py,"
            "docs/research/SCBE_SWARM_ROUTER_COMPARISON_2026-05-10.md"
        ),
    ),
    BenchmarkCase(
        case_id="public_terminal_bench_adapter",
        persona="public_benchmark_adapter",
        task=(
            "Public benchmark adapter role: inspect what is needed to run SCBE swarm router against "
            "Terminal-Bench. Evidence only: sandbox command requirements, observable terminal/file outcomes, "
            "grading surface, and one next implementation step."
        ),
        agents="hermes",
        timeout=75,
        max_workers=1,
        allowed_paths="scripts/,tests/,docs/",
        output_contract="evidence",
        constraint_mode="strict",
        focus_paths=(
            "scripts/benchmark/openclaw_swarm_benchmark.py,"
            "scripts/system/scbe_swarm_router.py,"
            "docs/research/SCBE_SWARM_ROUTER_COMPARISON_2026-05-10.md"
        ),
    ),
    BenchmarkCase(
        case_id="public_vexp_swebench_adapter",
        persona="public_benchmark_adapter",
        task=(
            "Public benchmark adapter role: inspect what is needed to compare SCBE swarm router using the Vexp "
            "SWE-bench harness. Evidence only: cost/speed fields, external-agent adapter shape, grading surface, "
            "and one next implementation step."
        ),
        agents="pi",
        timeout=75,
        max_workers=1,
        allowed_paths="scripts/,tests/,docs/",
        output_contract="evidence",
        constraint_mode="strict",
        focus_paths=(
            "scripts/benchmark/openclaw_swarm_benchmark.py,"
            "scripts/system/scbe_swarm_router.py,"
            "docs/research/SCBE_SWARM_ROUTER_COMPARISON_2026-05-10.md"
        ),
    ),
)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def allocate_output_dir(output_root: Path, run_id: str) -> Path:
    """Create a unique benchmark artifact directory even for same-second launches."""
    output_root.mkdir(parents=True, exist_ok=True)
    for index in range(1000):
        suffix = "" if index == 0 else f"-{index:03d}"
        candidate = output_root / f"{run_id}{suffix}"
        try:
            candidate.mkdir(parents=False, exist_ok=False)
            return candidate
        except FileExistsError:
            continue
    raise RuntimeError(f"could not allocate benchmark output dir under {output_root}")


def run_case(case: BenchmarkCase) -> dict[str, Any]:
    command = [
        sys.executable,
        str(SWARM),
        "--task",
        case.task,
        "--agents",
        case.agents,
        "--timeout",
        str(case.timeout),
        "--max-workers",
        str(case.max_workers),
        "--constraint-mode",
        case.constraint_mode,
    ]
    if case.allowed_paths:
        command.extend(["--allowed-paths", case.allowed_paths])
    if case.output_contract:
        command.extend(["--output-contract", case.output_contract])
    if case.focus_paths:
        command.extend(["--focus-paths", case.focus_paths])
    if case.dry_run:
        command.append("--dry-run")
    if case.allow_ollama_cloud:
        command.append("--allow-ollama-cloud")
    if case.prefer_ollama_cloud:
        command.append("--prefer-ollama-cloud")

    started = time.time()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=max(30, case.timeout * max(1, len(case.agents.split(","))) + 60),
        check=False,
    )
    wall_seconds = round(time.time() - started, 3)

    parsed: dict[str, Any] | None = None
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        parsed = None

    routing: dict[str, Any] = {}
    if parsed and parsed.get("run_dir"):
        routing_path = Path(parsed["run_dir"]) / "routing.json"
        if routing_path.exists():
            routing = json.loads(routing_path.read_text(encoding="utf-8"))

    return {
        "case": asdict(case),
        "exit_code": completed.returncode,
        "wall_seconds": wall_seconds,
        "ok": bool(parsed and parsed.get("ok") and completed.returncode == 0),
        "stdout_json": parsed,
        "stderr_tail": completed.stderr[-2000:],
        "routing": routing,
        "score": score_case(parsed, routing, completed.returncode),
    }


def score_case(parsed: dict[str, Any] | None, routing: dict[str, Any], exit_code: int) -> dict[str, Any]:
    if not parsed or exit_code != 0:
        return {"points": 0, "max_points": 100, "grade": "fail", "reason": "command failed or emitted non-json"}

    points = 0
    points += 20 if parsed.get("ok") else 0
    points += 15 if parsed.get("agents") else 0
    points += 15 if parsed.get("models") else 0
    points += 15 if "promotable_lanes" in parsed and "blocked_lanes" in parsed else 0
    points += 20 if routing.get("schema") in {"scbe_swarm_routing_v1", "openclaw_swarm_routing_v1"} else 0
    points += (
        10
        if routing.get("next_action")
        in {
            "extract_one_promotable_diff_then_safe_apply",
            "escalate_to_paid_or_narrow_task",
            "run_helper_guard_cycle_before_escalation",
            "deliver_answer_to_user",
            "handoff_evidence_to_builder",
            "review_promotable_lane",
            "safe_apply_verified",
        }
        else 0
    )
    points += 5 if "correction_guide" in routing and "quality_flag_counts" in routing else 0
    if routing.get("assurance_packet"):
        points = min(100, points + 0)
    quality_flags = routing.get("quality_flag_counts") or parsed.get("quality_flag_counts") or {}
    if parsed.get("failed_lanes", 0):
        points = min(points, 65)
    elif quality_flags:
        points = min(points, 85)

    if points >= 90:
        grade = "pass"
    elif points >= 70:
        grade = "partial"
    else:
        grade = "weak"
    return {"points": points, "max_points": 100, "grade": grade, "reason": "harness artifact contract score"}


def _score_efficiency(seconds: float) -> float:
    if seconds <= 2.0:
        return 100.0
    if seconds <= 10.0:
        return 90.0
    if seconds <= 30.0:
        return 75.0
    if seconds <= 60.0:
        return 60.0
    return 40.0


def _score_actionability(next_action: str) -> float:
    action_scores = {
        "safe_apply_verified": 100.0,
        "extract_one_promotable_diff_then_safe_apply": 95.0,
        "review_promotable_lane": 90.0,
        "handoff_evidence_to_builder": 85.0,
        "run_helper_guard_cycle_before_escalation": 75.0,
        "deliver_answer_to_user": 70.0,
        "escalate_to_paid_or_narrow_task": 60.0,
    }
    return action_scores.get(next_action, 40.0)


def build_quality_vector(item: dict[str, Any]) -> dict[str, Any]:
    """Measure how well a case passed, beyond binary pass/fail."""
    parsed = item.get("stdout_json") or {}
    routing = item.get("routing") or {}
    assurance = routing.get("assurance_packet") or {}
    quality_flags = routing.get("quality_flag_counts") or parsed.get("quality_flag_counts") or {}
    flag_total = sum(int(count) for count in quality_flags.values())
    mean_applicability = float(
        assurance.get("mean_applicability_score", parsed.get("mean_applicability_score", 0)) or 0
    )
    next_action = str(routing.get("next_action") or parsed.get("next_action") or "")
    trace_parts = [
        bool(parsed.get("run_dir")),
        routing.get("schema") in {"scbe_swarm_routing_v1", "openclaw_swarm_routing_v1"},
        bool(next_action),
        bool(routing.get("assurance_packet")),
        "promotable_lanes" in parsed and "blocked_lanes" in parsed,
    ]
    traceability = round(100.0 * sum(1 for value in trace_parts if value) / len(trace_parts), 2)
    evidence_integrity = max(0.0, 100.0 - (flag_total * 15.0))
    dimensions = {
        "gate_contract": float((item.get("score") or {}).get("points", 0)),
        "evidence_integrity": round(evidence_integrity, 2),
        "traceability": traceability,
        "actionability": _score_actionability(next_action),
        "patch_readiness": max(0.0, min(100.0, mean_applicability)),
        "efficiency": _score_efficiency(float(item.get("wall_seconds") or 0.0)),
    }
    weights = {
        "gate_contract": 0.10,
        "evidence_integrity": 0.20,
        "traceability": 0.20,
        "actionability": 0.20,
        "patch_readiness": 0.20,
        "efficiency": 0.10,
    }
    score = round(sum(dimensions[key] * weights[key] for key in weights), 2)
    if score >= 95.0:
        depth = "exceptional_pass"
    elif score >= 85.0:
        depth = "solid_pass"
    elif score >= 70.0:
        depth = "thin_pass"
    else:
        depth = "weak_or_failed"
    return {
        "schema": "scbe_swarm_case_quality_vector_v1",
        "quality_score": score,
        "pass_depth": depth,
        "dimensions": dimensions,
        "weights": weights,
        "quality_flag_total": flag_total,
        "note": (
            "Measures how well the case passed: evidence quality, traceability, actionability, patch readiness, "
            "efficiency, and gate shape."
        ),
    }


def attach_quality_vectors(results: list[dict[str, Any]]) -> None:
    for item in results:
        item["quality_vector"] = build_quality_vector(item)


def summarize_quality_vectors(results: list[dict[str, Any]]) -> dict[str, Any]:
    vectors = [item.get("quality_vector") or build_quality_vector(item) for item in results]
    if not vectors:
        return {
            "schema": "scbe_swarm_quality_summary_v1",
            "average_quality_score": 0.0,
            "pass_depth_counts": {},
            "dimension_averages": {},
        }
    depth_counts: dict[str, int] = {}
    dimension_totals: dict[str, float] = {}
    for vector in vectors:
        depth = str(vector.get("pass_depth") or "unknown")
        depth_counts[depth] = depth_counts.get(depth, 0) + 1
        for key, value in (vector.get("dimensions") or {}).items():
            dimension_totals[key] = dimension_totals.get(key, 0.0) + float(value)
    return {
        "schema": "scbe_swarm_quality_summary_v1",
        "average_quality_score": round(sum(float(vector["quality_score"]) for vector in vectors) / len(vectors), 2),
        "pass_depth_counts": depth_counts,
        "dimension_averages": {key: round(value / len(vectors), 2) for key, value in sorted(dimension_totals.items())},
        "interpretation": (
            "Use this to compare successful runs by quality, not just pass/fail. A green run with low traceability or "
            "patch_readiness is a thin pass."
        ),
    }


def build_summary(
    results: list[dict[str, Any]],
    *,
    completed_cases: int | None = None,
    planned_cases: int | None = None,
    case_workers: int | None = None,
) -> dict[str, Any]:
    attach_quality_vectors(results)
    scores = [item["score"]["points"] for item in results]
    parsed_rows = [item.get("stdout_json") or {} for item in results]
    summary: dict[str, Any] = {
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "average_quality_score": summarize_quality_vectors(results)["average_quality_score"],
        "promotable_total": sum(int(row.get("promotable_lanes") or 0) for row in parsed_rows),
        "blocked_total": sum(int(row.get("blocked_lanes") or 0) for row in parsed_rows),
        "failed_total": sum(int(row.get("failed_lanes") or 0) for row in parsed_rows),
        "quality_summary": summarize_quality_vectors(results),
    }
    if completed_cases is not None:
        summary["completed_cases"] = completed_cases
    if planned_cases is not None:
        summary["planned_cases"] = planned_cases
    if case_workers is not None:
        summary["case_workers"] = case_workers
    return summary


def _case_stage(case_id: str) -> str:
    for stage, spec in KAGGLE_WINNER_STAGES.items():
        if case_id in spec["case_ids"]:
            return stage
    return "unmapped"


def _average_dimension_vectors(items: list[dict[str, Any]]) -> dict[str, float]:
    if not items:
        return {}
    totals: dict[str, float] = {}
    for item in items:
        vector = item.get("quality_vector") or build_quality_vector(item)
        for key, value in (vector.get("dimensions") or {}).items():
            totals[key] = totals.get(key, 0.0) + float(value)
    return {key: round(value / len(items), 2) for key, value in sorted(totals.items())}


def build_kaggle_winner_loop(report: dict[str, Any]) -> dict[str, Any]:
    """Summarize the benchmark like a Kaggle-style iterative improvement loop."""
    cases = report.get("cases") or []
    stage_rows: dict[str, list[dict[str, Any]]] = {stage: [] for stage in KAGGLE_WINNER_STAGE_ORDER}
    stage_rows["unmapped"] = []
    for item in cases:
        case = item.get("case") or {}
        stage_rows.setdefault(_case_stage(str(case.get("case_id") or "")), []).append(item)

    stages: list[dict[str, Any]] = []
    previous_score: float | None = None
    for stage in KAGGLE_WINNER_STAGE_ORDER:
        items = stage_rows.get(stage, [])
        spec = KAGGLE_WINNER_STAGES[stage]
        quality_scores = [
            float((item.get("quality_vector") or build_quality_vector(item)).get("quality_score") or 0.0)
            for item in items
        ]
        dimensions = _average_dimension_vectors(items)
        weakest_dimension = min(dimensions, key=dimensions.get) if dimensions else "not_run"
        average_quality = round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else 0.0
        delta = None if previous_score is None or not items else round(average_quality - previous_score, 2)
        if items:
            previous_score = average_quality
        stages.append(
            {
                "stage": stage,
                "name": spec["name"],
                "goal": spec["goal"],
                "case_count": len(items),
                "case_ids": [str((item.get("case") or {}).get("case_id")) for item in items],
                "average_quality_score": average_quality,
                "delta_from_previous_run_stage": delta,
                "dimension_averages": dimensions,
                "weakest_dimension": weakest_dimension,
                "next_repair_task": QUALITY_DIMENSION_REPAIR_TASKS.get(
                    weakest_dimension,
                    "Run the stage before assigning a repair task.",
                ),
            }
        )

    cloud_cases = [
        item
        for item in cases
        if (item.get("case") or {}).get("allow_ollama_cloud") or (item.get("case") or {}).get("prefer_ollama_cloud")
    ]
    cloud_models: list[str] = []
    for item in cloud_cases:
        parsed = item.get("stdout_json") or {}
        cloud_models.extend(str(model) for model in parsed.get("models", []) if "cloud" in str(model).lower())
    weaknesses = (report.get("weakness_loop") or {}).get("weaknesses") or []
    first_weakness = weaknesses[0] if weaknesses else {}
    weakest_stage = min(
        (stage for stage in stages if stage["case_count"]),
        key=lambda stage: stage["average_quality_score"],
        default=None,
    )
    return {
        "schema": "scbe_kaggle_winner_improvement_loop_v1",
        "claim_boundary": "Internal improvement-loop evidence only; public benchmarks require their official graders.",
        "method": [
            "baseline",
            "feature/evidence packet",
            "ensemble consensus",
            "postprocess/repair",
            "rerun same cases before claiming lift",
        ],
        "stages": stages,
        "weakest_stage": weakest_stage["stage"] if weakest_stage else "not_run",
        "next_best_patch": first_weakness.get("patch_direction")
        or (weakest_stage or {}).get("next_repair_task")
        or "Run the benchmark before selecting a patch.",
        "next_rerun": first_weakness.get("rerun")
        or "python scripts/benchmark/openclaw_swarm_benchmark.py --mode kaggle-loop",
        "ollama_cloud": {
            "enabled_case_count": len(cloud_cases),
            "prefer_cloud_case_count": sum(
                1 for item in cloud_cases if (item.get("case") or {}).get("prefer_ollama_cloud")
            ),
            "models_seen": sorted(set(cloud_models)),
            "note": "Cloud models are used only by opted-in cases; local/free lanes remain the default first pass.",
        },
        "web_search": {
            "status": "not_embedded",
            "note": (
                "Use repo-captured research/context files as inputs for now; direct web search is intentionally "
                "outside this harness loop."
            ),
        },
    }


def build_safe_apply_patch(rel_path: str) -> str:
    return (
        f"diff --git a/{rel_path} b/{rel_path}\n"
        "new file mode 100644\n"
        "index 0000000..e69de29\n"
        "--- /dev/null\n"
        f"+++ b/{rel_path}\n"
        "@@ -0,0 +1 @@\n"
        "+scbe safe-apply benchmark probe\n"
    )


def run_safe_apply_case(output_dir: Path) -> dict[str, Any]:
    """Run the deterministic safe_apply rung without mutating the main tree."""
    rel_path = f"tests/_safe_apply_benchmark_probe_{output_dir.name}_DELETE_ME.txt"
    patch_path = output_dir / "safe_apply_probe.diff"
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_text(build_safe_apply_patch(rel_path), encoding="utf-8")
    smoke = (
        'python -c "from pathlib import Path; '
        f"assert Path({rel_path!r}).exists(); "
        "print('sandbox patch visible')\""
    )
    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "agents" / "safe_apply.py"),
        "--patch-file",
        str(patch_path),
        "--smoke",
        smoke,
        "--smoke-timeout",
        "30",
        "--dry-run",
    ]
    started = time.time()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    wall_seconds = round(time.time() - started, 3)
    parsed: dict[str, Any] | None = None
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        parsed = None
    main_target_exists = (REPO_ROOT / rel_path).exists()
    ok = bool(
        completed.returncode == 0
        and parsed
        and parsed.get("ok") is True
        and parsed.get("applied") is False
        and parsed.get("smoke_returncode") == 0
        and not main_target_exists
    )
    quality_flags: dict[str, int] = {}
    if completed.returncode != 0:
        quality_flags["safe_apply_cli_failed"] = 1
    if not parsed:
        quality_flags["safe_apply_non_json"] = 1
    elif parsed.get("applied") is not False:
        quality_flags["safe_apply_mutated_main"] = 1
    if main_target_exists:
        quality_flags["safe_apply_probe_left_main_file"] = 1
    routing = {
        "schema": "scbe_swarm_routing_v1",
        "policy": "deterministic_safe_apply_sandbox_rung",
        "quality_flag_counts": quality_flags,
        "correction_guide": [],
        "next_action": "safe_apply_verified" if ok else "repair_safe_apply_rung",
        "assurance_packet": {
            "schema": "scbe_darpa_style_assurance_packet_v1",
            "mean_applicability_score": 100.0 if ok else 0.0,
            "min_applicability_score": 100 if ok else 0,
            "requirements": {
                "patch_functionality": "patch is checked and smoked in sandbox before any main-tree apply",
                "predictability": "dry-run must leave the main tree untouched",
            },
        },
    }
    stdout_json = {
        "ok": ok,
        "run_dir": str(output_dir),
        "agents": ["safe_apply"],
        "models": ["deterministic_patch"],
        "promotable_lanes": 1 if ok else 0,
        "blocked_lanes": 0 if ok else 1,
        "failed_lanes": 0 if ok else 1,
        "safe_apply": parsed,
        "main_target_exists": main_target_exists,
    }
    case = BenchmarkCase(
        case_id="safe_apply_sandbox_patch_probe",
        persona="safe_apply_gate",
        task="Apply a deterministic patch in a sandbox, run smoke, and prove dry-run does not mutate the main tree.",
        agents="safe_apply",
        timeout=90,
        max_workers=1,
        allowed_paths="tests/",
        output_contract="patch-proposal",
        constraint_mode="strict",
        focus_paths=rel_path,
    )
    return {
        "case": asdict(case),
        "exit_code": completed.returncode,
        "wall_seconds": wall_seconds,
        "ok": ok,
        "stdout_json": stdout_json,
        "stderr_tail": completed.stderr[-2000:],
        "routing": routing,
        "score": score_case(stdout_json, routing, completed.returncode),
        "command": command,
    }


def build_self_cli_functional_command(
    output_dir: Path,
    models: tuple[str, ...],
    *,
    task_limit: int,
    repair_model: str = "",
    repair_attempts: int = 0,
) -> list[str]:
    command = [
        sys.executable,
        str(FUNCTIONAL_CODING_BENCH),
        "--ollama-models",
        *models,
        "--task-file",
        str(SELF_CLI_TASK_FILE),
        "--replace-default-tasks",
        "--task-limit",
        str(task_limit),
        "--max-new-tokens",
        "260",
        "--min-pass-rate",
        "0",
        "--output-root",
        str(output_dir / "functional"),
    ]
    if repair_model and repair_attempts > 0:
        command.extend(["--repair-ollama-model", repair_model, "--repair-attempts", str(repair_attempts)])
    return command


def _functional_score_from_report(payload: dict[str, Any]) -> dict[str, Any]:
    results = payload.get("results") or []
    if not results:
        return {"points": 0, "max_points": 100, "grade": "fail", "reason": "no functional results"}
    pass_rates = [float((row.get("summary") or {}).get("pass_rate") or 0.0) for row in results]
    points = round((sum(pass_rates) / len(pass_rates)) * 100.0, 2)
    if points >= 90:
        grade = "pass"
    elif points >= 60:
        grade = "partial"
    elif points > 0:
        grade = "weak"
    else:
        grade = "fail"
    return {
        "points": points,
        "max_points": 100,
        "grade": grade,
        "reason": "executable TypeScript productivity task pass rate",
    }


def _find_functional_report_path(stdout: str, output_dir: Path) -> Path | None:
    for line in stdout.splitlines():
        if line.startswith("Report JSON:"):
            candidate = Path(line.split(":", 1)[1].strip())
            if candidate.exists():
                return candidate
    latest = output_dir / "functional" / "latest" / "report.json"
    return latest if latest.exists() else None


def run_self_cli_functional_case(
    output_dir: Path,
    models: tuple[str, ...],
    *,
    task_limit: int,
    repair_model: str = "",
    repair_attempts: int = 0,
) -> dict[str, Any]:
    """Run hard CLI compiler/productivity tasks through our Ollama-backed evaluator."""
    command = build_self_cli_functional_command(
        output_dir,
        models,
        task_limit=task_limit,
        repair_model=repair_model,
        repair_attempts=repair_attempts,
    )
    started = time.time()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=max(120, 180 * max(1, len(models)) * max(1, task_limit)),
        check=False,
    )
    wall_seconds = round(time.time() - started, 3)
    report_path = _find_functional_report_path(completed.stdout, output_dir)
    functional_report: dict[str, Any] = {}
    if report_path:
        functional_report = json.loads(report_path.read_text(encoding="utf-8"))
    score = _functional_score_from_report(functional_report)
    results = functional_report.get("results") or []
    summaries = [row.get("summary") or {} for row in results]
    tasks_total = sum(int(summary.get("tasks") or 0) for summary in summaries)
    passed_total = sum(int(summary.get("passed") or 0) for summary in summaries)
    failed_total = max(0, tasks_total - passed_total)
    quality_flags: dict[str, int] = {}
    if completed.returncode != 0:
        quality_flags["self_cli_functional_runner_failed"] = 1
    if not functional_report:
        quality_flags["self_cli_functional_report_missing"] = 1
    if failed_total:
        quality_flags["self_cli_functional_task_failed"] = failed_total
    routing = {
        "schema": "scbe_swarm_routing_v1",
        "policy": "self_cli_functional_coding_gauntlet",
        "quality_flag_counts": quality_flags,
        "correction_guide": [],
        "next_action": (
            "safe_apply_verified"
            if failed_total == 0 and functional_report
            else "run_helper_guard_cycle_before_escalation"
        ),
        "next_cycle": "inspect_failed_functional_tasks_then_repair_prompt_or_task_packet",
        "assurance_packet": {
            "schema": "scbe_darpa_style_assurance_packet_v1",
            "mean_applicability_score": score["points"],
            "requirements": {
                "execution": "generated TypeScript must pass scripts/run_typescript_debug_scenario.cjs",
                "compiler_trace": (
                    "each generated artifact should carry semantic packet, target-language hash, tongue route, and "
                    "GeoSeal trace"
                ),
                "system_boundary": "only SCBE task pack, SCBE evaluator, Ollama models, and local harness are used",
            },
        },
    }
    stdout_json = {
        "ok": bool(functional_report and completed.returncode == 0),
        "run_dir": str(output_dir),
        "agents": ["self_cli_functional_gauntlet"],
        "models": list(models),
        "successful_lanes": passed_total,
        "promotable_lanes": passed_total,
        "blocked_lanes": failed_total,
        "failed_lanes": 0 if completed.returncode == 0 else 1,
        "tasks_total": tasks_total,
        "passed_total": passed_total,
        "functional_report": str(report_path) if report_path else "",
    }
    case = BenchmarkCase(
        case_id="self_cli_functional_productivity_gauntlet",
        persona="self_cli_coding_agent",
        task=(
            "Compile SCBE productivity tasks from natural language into TypeScript artifacts with GeoSeal trace "
            "metadata, then verify executable behavior through the local CLI evaluator using Ollama-routed models."
        ),
        agents="self_cli_functional_gauntlet",
        timeout=180,
        max_workers=1,
        allowed_paths="scripts/,config/eval/,artifacts/",
        output_contract="cross-lingual-compiler-artifact",
        constraint_mode="strict",
        focus_paths=(
            "config/eval/scbe_productivity_eval_tasks.v1.json,scripts/eval/functional_coding_agent_benchmark.py,"
            "scripts/run_typescript_debug_scenario.cjs"
        ),
    )
    return {
        "case": asdict(case),
        "exit_code": completed.returncode,
        "wall_seconds": wall_seconds,
        "ok": bool(functional_report and completed.returncode == 0),
        "stdout_json": stdout_json,
        "stderr_tail": completed.stderr[-2000:],
        "routing": routing,
        "score": score,
        "command": command,
        "functional_report_summary": {
            "report": str(report_path) if report_path else "",
            "models": [
                {
                    "adapter": row.get("adapter"),
                    "tasks": (row.get("summary") or {}).get("tasks"),
                    "passed": (row.get("summary") or {}).get("passed"),
                    "pass_rate": (row.get("summary") or {}).get("pass_rate"),
                    "avg_generation_s": (row.get("summary") or {}).get("avg_generation_s"),
                }
                for row in results
            ],
        },
    }


def build_single_case_report(run_id: str, mode: str, output_dir: Path, item: dict[str, Any]) -> dict[str, Any]:
    results = [item]
    summary = build_summary(results)
    report = {
        "schema": "openclaw_swarm_benchmark_v1",
        "run_id": run_id,
        "mode": mode,
        "summary": summary,
        "cases": results,
        "semantic_task_variables": [build_semantic_task_variables(row) for row in results],
    }
    report["weakness_loop"] = build_weakness_loop(report)
    report["kaggle_winner_loop"] = build_kaggle_winner_loop(report)
    report["geometric_consensus"] = build_geometric_consensus(report)
    report["trust_ladder_report"] = build_trust_ladder_report(report)
    _write_json(output_dir / "report.json", report)
    (output_dir / "report.md").write_text(build_markdown(report), encoding="utf-8")
    latest = output_dir.parent / "latest"
    _write_json(latest / "report.json", report)
    (latest / "report.md").write_text(build_markdown(report), encoding="utf-8")
    return report


def build_trust_ladder_report(report: dict[str, Any]) -> dict[str, Any]:
    """Compute a small Fibonacci-style trust ladder over benchmark rows."""
    rows = report.get("semantic_task_variables") or []
    values = [1.0, 1.0]
    phi = (1.0 + 5.0**0.5) / 2.0
    betrayal_count = 0
    events = []
    for row in rows:
        gate = row.get("gate_state") or {}
        completion = str(gate.get("completion_state") or "unknown")
        quality_flags = gate.get("quality_flags") or {}
        betrayal_delta = 1.0 if completion == "runtime_failed" else 0.0
        if quality_flags and completion != "blocked_correctly":
            betrayal_delta = max(betrayal_delta, 0.5)
        prev1 = values[-1]
        prev2 = values[-2] if len(values) >= 2 else prev1
        if betrayal_delta > 0.0:
            new_value = prev1 - phi * abs(betrayal_delta)
            betrayal_count += 1
        else:
            new_value = prev1 + phi * prev2
        values.append(float(new_value))
        values = values[-12:]
        events.append(
            {
                "task_id": row.get("task_id"),
                "completion_state": completion,
                "betrayal_delta": betrayal_delta,
                "trust_level": round(new_value, 4),
                "trust_factor": round(max(0.3, min(1.8, new_value / 8.0)), 4),
            }
        )
    current = float(values[-1])
    factor = float(max(0.3, min(1.8, current / 8.0)))
    if betrayal_count == 0 and rows:
        state = "trust_accruing"
    elif betrayal_count:
        state = "trust_repair_needed"
    elif factor <= 0.5:
        state = "trust_low_retry_or_escalate"
    else:
        state = "trust_uninitialized"
    return {
        "schema": "scbe_fibonacci_trust_ladder_report_v1",
        "source_note": "notes/theory/fibonacci-trust-ladder.md",
        "rows": len(rows),
        "trust_values": [round(value, 4) for value in values],
        "trust_level": round(current, 4),
        "trust_factor": round(factor, 4),
        "betrayal_count": betrayal_count,
        "state": state,
        "events": events,
        "note": (
            "This is benchmark-route trust, not human trust. Runtime failure and unhandled flags decay the ladder; "
            "clean promotable or correctly-blocked rows accrue it."
        ),
    }


def build_semantic_task_variables(item: dict[str, Any]) -> dict[str, Any]:
    """Summarize one benchmark case as stable variables for inner task tracking."""
    case = item.get("case") or {}
    parsed = item.get("stdout_json") or {}
    routing = item.get("routing") or {}
    quality_flags = routing.get("quality_flag_counts") or parsed.get("quality_flag_counts") or {}
    assurance = routing.get("assurance_packet") or {}
    mean_applicability = assurance.get("mean_applicability_score", parsed.get("mean_applicability_score", 0))
    if parsed.get("failed_lanes", 0):
        completion_state = "runtime_failed"
    elif parsed.get("promotable_lanes", 0):
        completion_state = "promotable_signal"
    elif parsed.get("blocked_lanes", 0):
        completion_state = "blocked_correctly"
    else:
        completion_state = "no_signal"
    return {
        "task_id": case.get("case_id"),
        "task_intent": case.get("task"),
        "persona": case.get("persona"),
        "output_contract": case.get("output_contract"),
        "constraint_mode": case.get("constraint_mode"),
        "allowed_paths": case.get("allowed_paths"),
        "focus_paths": case.get("focus_paths"),
        "agent_set": case.get("agents"),
        "cloud_policy": {
            "allow_ollama_cloud": bool(case.get("allow_ollama_cloud")),
            "prefer_ollama_cloud": bool(case.get("prefer_ollama_cloud")),
        },
        "runtime": {
            "exit_code": item.get("exit_code"),
            "wall_seconds": item.get("wall_seconds"),
            "run_dir": parsed.get("run_dir"),
            "lanes": parsed.get("lanes", []),
            "models": parsed.get("models", []),
        },
        "gate_state": {
            "successful_lanes": parsed.get("successful_lanes", 0),
            "promotable_lanes": parsed.get("promotable_lanes", 0),
            "blocked_lanes": parsed.get("blocked_lanes", 0),
            "failed_lanes": parsed.get("failed_lanes", 0),
            "quality_flags": quality_flags,
            "mean_applicability_score": mean_applicability,
            "next_action": routing.get("next_action", parsed.get("next_action")),
            "next_cycle": routing.get("next_cycle", parsed.get("next_cycle")),
            "completion_state": completion_state,
        },
        "interpretation": {
            "public_benchmark_claim": "not_public_benchmark",
            "internal_claim": "orchestration_contract_and_task_tracking_only",
            "promotion_rule": (
                "Only patch-proposal lanes with no quality flags and later safe_apply verification "
                "may become code changes."
            ),
        },
    }


def build_weakness_loop(report: dict[str, Any]) -> dict[str, Any]:
    """Turn benchmark output into the next benchmark-patch-rerun cycle."""
    flag_counts: dict[str, int] = {}
    for item in report.get("cases", []):
        routing = item.get("routing") or {}
        parsed = item.get("stdout_json") or {}
        counts = routing.get("quality_flag_counts") or parsed.get("quality_flag_counts") or {}
        for flag, count in counts.items():
            flag_counts[flag] = flag_counts.get(flag, 0) + int(count)
    weaknesses: list[dict[str, str]] = []
    if flag_counts.get("evidence_symbol_not_found"):
        weaknesses.append(
            {
                "weakness": "model_invented_evidence_symbols",
                "observed": f"{flag_counts['evidence_symbol_not_found']} evidence symbol misses",
                "why_we_lose": (
                    "External coding agents win by grounding generation in repo retrieval and execution; our weak "
                    "local lanes still infer declarations from prompt text."
                ),
                "patch_direction": "Add deterministic local symbol inventory to helper evidence before model routing.",
                "rerun": "python scripts/benchmark/openclaw_swarm_benchmark.py --mode semantic",
            }
        )
    if flag_counts.get("symbol_not_found"):
        weaknesses.append(
            {
                "weakness": "patch_targets_fake_or_stale_symbols",
                "observed": f"{flag_counts['symbol_not_found']} patch symbol misses",
                "why_we_lose": "Public coding benchmarks reward applicable patches, not plausible diffs.",
                "patch_direction": (
                    "Require symbol inventory and context extraction before any builder lane can be promotable."
                ),
                "rerun": "python scripts/benchmark/openclaw_swarm_benchmark.py --mode roles",
            }
        )
    if flag_counts.get("path_outside_lane"):
        weaknesses.append(
            {
                "weakness": "lane_scope_leakage",
                "observed": f"{flag_counts['path_outside_lane']} out-of-lane path mentions",
                "why_we_lose": (
                    "Terminal agents fail when they touch broad or unrelated surfaces instead of the task sandbox."
                ),
                "patch_direction": "Tighten file hints and role prompts around explicit focus paths and allowed roots.",
                "rerun": "python scripts/benchmark/openclaw_swarm_benchmark.py --mode roles",
            }
        )
    mapped_prefixes = {
        "evidence_symbol_not_found",
        "symbol_not_found",
        "path_outside_lane",
    }
    for flag, count in sorted(flag_counts.items()):
        if flag in mapped_prefixes:
            continue
        rule = QUALITY_FLAG_REPAIR_RULES.get(flag)
        if rule:
            weaknesses.append(
                {
                    "weakness": rule["weakness"],
                    "observed": f"{count} occurrences",
                    "why_we_lose": rule["why_we_lose"],
                    "patch_direction": rule["patch_direction"],
                    "rerun": "python scripts/benchmark/openclaw_swarm_benchmark.py --mode roles",
                }
            )
            continue
        weaknesses.append(
            {
                "weakness": f"unmapped_quality_flag:{flag}",
                "observed": f"{count} occurrences",
                "why_we_lose": "A benchmark loop is only useful when every blocker maps to a repair action.",
                "patch_direction": (
                    "Add a specific correction rule or suppress the flag only if the validator is too strict."
                ),
                "rerun": "python scripts/benchmark/openclaw_swarm_benchmark.py --mode semantic",
            }
        )
    if not weaknesses:
        weaknesses.append(
            {
                "weakness": "no_internal_blocker_detected",
                "observed": "No quality flags in this run.",
                "why_we_lose": (
                    "Internal cleanliness is not public benchmark success; we still need patch-apply and "
                    "task-completion scores."
                ),
                "patch_direction": "Run a real safe_apply benchmark on held-out repo tasks and record pass/fail.",
                "rerun": "python scripts/benchmark/openclaw_swarm_benchmark.py --mode full",
            }
        )
    return {
        "schema": "scbe_benchmark_patch_rerun_loop_v1",
        "claim_boundary": (
            "Internal harness score only. Do not present as SWE-bench, Terminal-Bench, or public leaderboard "
            "performance."
        ),
        "public_benchmark_targets": list(PUBLIC_BENCHMARK_TARGETS),
        "quality_flag_counts": flag_counts,
        "weaknesses": weaknesses,
        "next_loop": [
            "Run internal semantic/role benchmark.",
            "Patch the highest-count weakness.",
            "Rerun the same benchmark to isolate attribution.",
            "Run docs review to ensure report caveats match actual behavior.",
            "Only then compare to external public benchmark adapters.",
        ],
    }


def build_geometric_consensus(report: dict[str, Any]) -> dict[str, Any]:
    """Keep consensus as advisory context, never as the production gate."""
    rows = report.get("semantic_task_variables") or []
    if not rows:
        return {
            "schema": "scbe_geometric_consensus_v1",
            "rows": 0,
            "fixed_declaration_keys": list(FIXED_DECLARATION_KEYS),
            "declaration_coverage": 0.0,
            "role_states": {},
            "note": (
                "Consensus is advisory only. Production scoring is based on artifacts, patch readiness, traceability, "
                "and verification."
            ),
        }
    total_keys = len(rows) * len(FIXED_DECLARATION_KEYS)
    present_keys = sum(1 for row in rows for key in FIXED_DECLARATION_KEYS if key in row)
    coverage = round(present_keys / total_keys, 4) if total_keys else 0.0
    role_states: dict[str, dict[str, int]] = {}
    completion_counts: dict[str, int] = {}
    contract_counts: dict[str, int] = {}
    hex_faces = {face: {"present": 0, "total": len(rows)} for face in HEXAGONAL_CONSENSUS_FACES}
    rays: list[dict[str, Any]] = []
    code_5w_rows: list[dict[str, Any]] = []
    for row in rows:
        persona = str(row.get("persona") or "unknown")
        gate = row.get("gate_state") or {}
        runtime = row.get("runtime") or {}
        completion = str(gate.get("completion_state") or "unknown")
        contract = str(row.get("output_contract") or "unknown")
        role_states.setdefault(persona, {})
        role_states[persona][completion] = role_states[persona].get(completion, 0) + 1
        completion_counts[completion] = completion_counts.get(completion, 0) + 1
        contract_counts[contract] = contract_counts.get(contract, 0) + 1
        hex_faces["task_intent"]["present"] += int(bool(row.get("task_intent")))
        hex_faces["output_contract"]["present"] += int(contract != "unknown")
        hex_faces["path_scope"]["present"] += int(bool(row.get("allowed_paths")) and bool(row.get("focus_paths")))
        hex_faces["model_lane"]["present"] += int(bool(row.get("agent_set")) and bool(runtime.get("lanes")))
        hex_faces["gate_state"]["present"] += int(completion != "unknown" and "quality_flags" in gate)
        hex_faces["evidence_trace"]["present"] += int(bool(runtime.get("run_dir")) and bool(gate.get("next_cycle")))
        for flag, count in (gate.get("quality_flags") or {}).items():
            source_face = QUALITY_FLAG_FACE_MAP.get(flag, "gate_state")
            rays.append(
                {
                    "ray_type": "informational_drift",
                    "task_id": row.get("task_id"),
                    "source_face": source_face,
                    "target_focus": completion,
                    "signal": flag,
                    "count": int(count),
                    "path": [source_face, "result_focus", completion],
                }
            )
        code_5w_rows.append(
            {
                "task_id": row.get("task_id"),
                "who": {
                    "persona": persona,
                    "agents": row.get("agent_set"),
                    "models": runtime.get("models", []),
                },
                "what": {
                    "task_intent": row.get("task_intent"),
                    "output_contract": contract,
                    "completion_state": completion,
                },
                "where": {
                    "allowed_paths": row.get("allowed_paths"),
                    "focus_paths": row.get("focus_paths"),
                    "run_dir": runtime.get("run_dir"),
                },
                "when": {
                    "wall_seconds": runtime.get("wall_seconds"),
                    "exit_code": runtime.get("exit_code"),
                },
                "why": {
                    "quality_flags": gate.get("quality_flags", {}),
                    "next_action": gate.get("next_action"),
                    "next_cycle": gate.get("next_cycle"),
                },
            }
        )
    face_coverage = {
        face: {
            "coverage": round(value["present"] / value["total"], 4) if value["total"] else 0.0,
            "present": value["present"],
            "total": value["total"],
        }
        for face, value in hex_faces.items()
    }
    return {
        "schema": "scbe_geometric_consensus_v1",
        "geometry": "hexagonal_half-dodecahedral_consensus_graph",
        "rows": len(rows),
        "fixed_declaration_keys": list(FIXED_DECLARATION_KEYS),
        "hexagonal_faces": face_coverage,
        "result_focus": {
            "completion_counts": completion_counts,
            "dominant_completion": (
                max(completion_counts, key=completion_counts.get) if completion_counts else "unknown"
            ),
            "note": "Dominant completion is a routing clue, not a consensus score.",
        },
        "information_ray_trace": {
            "ray_model": "non_light_information_object_paths",
            "rays": rays,
            "ray_count": len(rays),
        },
        "code_5w": code_5w_rows,
        "declaration_coverage": coverage,
        "role_states": role_states,
        "contract_counts": contract_counts,
        "note": (
            "Consensus is advisory only. It must not block production by itself; code is judged by produced "
            "artifacts, patch readiness, traceability, and safe_apply/smoke verification."
        ),
    }


def build_markdown(report: dict[str, Any]) -> str:
    grouped: dict[str, dict[str, float]] = {}
    for item in report["cases"]:
        case = item["case"]
        for key in (
            f"constraint={case['constraint_mode']}",
            f"workers={case['max_workers']}",
        ):
            bucket = grouped.setdefault(key, {"cases": 0, "promotable": 0, "blocked": 0, "failed": 0, "seconds": 0.0})
            parsed = item.get("stdout_json") or {}
            bucket["cases"] += 1
            bucket["promotable"] += int(parsed.get("promotable_lanes") or 0)
            bucket["blocked"] += int(parsed.get("blocked_lanes") or 0)
            bucket["failed"] += int(parsed.get("failed_lanes") or 0)
            bucket["seconds"] += float(item["wall_seconds"])
    lines = [
        "# SCBE Swarm Router Benchmark",
        "",
        f"- run_id: `{report['run_id']}`",
        f"- mode: `{report['mode']}`",
        f"- cases: `{len(report['cases'])}`",
        f"- average_score: `{report['summary']['average_score']}`",
        f"- average_quality_score: `{report['summary'].get('average_quality_score', 0)}`",
        f"- promotable_total: `{report['summary']['promotable_total']}`",
        f"- blocked_total: `{report['summary']['blocked_total']}`",
        f"- failed_total: `{report['summary']['failed_total']}`",
        "",
        "## Cases",
        "",
        "| Case | Persona | Exit | Seconds | Score | Quality | Depth | Promotable | Blocked "
        "| Failed | Mean Applicability | Next Action |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|",
    ]
    for item in report["cases"]:
        parsed = item.get("stdout_json") or {}
        routing = item.get("routing") or {}
        assurance = routing.get("assurance_packet") or {}
        quality = item.get("quality_vector") or build_quality_vector(item)
        lines.append(
            "| {case} | `{persona}` | {exit_code} | {seconds} | {score}/100 | {quality}/100 "
            "| `{depth}` | {promotable} | {blocked} | {failed} | {mean_app} | `{next_action}` |".format(
                case=item["case"]["case_id"],
                persona=item["case"].get("persona", ""),
                exit_code=item["exit_code"],
                seconds=item["wall_seconds"],
                score=item["score"]["points"],
                quality=quality["quality_score"],
                depth=quality["pass_depth"],
                promotable=parsed.get("promotable_lanes", ""),
                blocked=parsed.get("blocked_lanes", ""),
                failed=parsed.get("failed_lanes", ""),
                mean_app=assurance.get("mean_applicability_score", ""),
                next_action=routing.get("next_action", ""),
            )
        )
    quality_summary = report["summary"].get("quality_summary")
    if quality_summary:
        lines.extend(
            [
                "",
                "## Pass Quality",
                "",
                f"- schema: `{quality_summary['schema']}`",
                f"- average_quality_score: `{quality_summary['average_quality_score']}`",
                f"- pass_depth_counts: `{json.dumps(quality_summary['pass_depth_counts'], sort_keys=True)}`",
                f"- interpretation: {quality_summary['interpretation']}",
                "",
                "| Dimension | Average |",
                "|---|---:|",
            ]
        )
        for key, value in quality_summary["dimension_averages"].items():
            lines.append(f"| `{key}` | {value} |")
    if report.get("semantic_task_variables"):
        lines.extend(
            [
                "",
                "## Semantic Task Variables",
                "",
                "| Task | Persona | Contract | State | Mean Applicability | Next Action | Public Claim |",
                "|---|---|---|---|---:|---|---|",
            ]
        )
        for row in report["semantic_task_variables"]:
            gate = row["gate_state"]
            interp = row["interpretation"]
            lines.append(
                "| {task} | `{persona}` | `{contract}` | `{state}` | {mean_app} | `{next_action}` | `{claim}` |".format(
                    task=row["task_id"],
                    persona=row["persona"],
                    contract=row["output_contract"],
                    state=gate["completion_state"],
                    mean_app=gate["mean_applicability_score"],
                    next_action=gate["next_action"],
                    claim=interp["public_benchmark_claim"],
                )
            )
    if report.get("geometric_consensus"):
        consensus = report["geometric_consensus"]
        lines.extend(
            [
                "",
                "## Geometric Consensus Advisory",
                "",
                f"- schema: `{consensus['schema']}`",
                f"- geometry: `{consensus['geometry']}`",
                f"- rows: `{consensus['rows']}`",
                f"- declaration_coverage: `{consensus['declaration_coverage']}`",
                f"- note: {consensus['note']}",
                "",
                "### Hexagonal Faces",
                "",
                "| Face | Coverage | Present | Total |",
                "|---|---:|---:|---:|",
            ]
        )
        for face, values in consensus["hexagonal_faces"].items():
            lines.append(f"| `{face}` | {values['coverage']} | {values['present']} | {values['total']} |")
        trace = consensus.get("information_ray_trace") or {}
        lines.extend(
            [
                "",
                "### Information Ray Trace",
                "",
                f"- ray_model: `{trace.get('ray_model', '')}`",
                f"- ray_count: `{trace.get('ray_count', 0)}`",
            ]
        )
        if consensus.get("code_5w"):
            lines.extend(
                [
                    "",
                    "### Code 5Ws",
                    "",
                    "| Task | Who | What | Where | When | Why |",
                    "|---|---|---|---|---|---|",
                ]
            )
            for row in consensus["code_5w"]:
                who = row.get("who") or {}
                what = row.get("what") or {}
                where = row.get("where") or {}
                when = row.get("when") or {}
                why = row.get("why") or {}
                lines.append(
                    "| {task} | `{persona}` / `{agents}` | `{contract}` -> `{state}` | `{focus}` "
                    "| `{seconds}s`, exit `{exit_code}` | flags `{flags}`, next `{next_action}` |".format(
                        task=row.get("task_id"),
                        persona=who.get("persona"),
                        agents=who.get("agents"),
                        contract=what.get("output_contract"),
                        state=what.get("completion_state"),
                        focus=where.get("focus_paths"),
                        seconds=when.get("wall_seconds"),
                        exit_code=when.get("exit_code"),
                        flags=json.dumps(why.get("quality_flags") or {}, sort_keys=True),
                        next_action=why.get("next_action"),
                    )
                )
    if report.get("trust_ladder_report"):
        trust = report["trust_ladder_report"]
        lines.extend(
            [
                "",
                "## Trust Ladder",
                "",
                f"- schema: `{trust['schema']}`",
                f"- source_note: `{trust['source_note']}`",
                f"- rows: `{trust['rows']}`",
                f"- trust_level: `{trust['trust_level']}`",
                f"- trust_factor: `{trust['trust_factor']}`",
                f"- betrayal_count: `{trust['betrayal_count']}`",
                f"- state: `{trust['state']}`",
                f"- note: {trust['note']}",
            ]
        )
    if grouped:
        lines.extend(
            [
                "",
                "## Grouped Totals",
                "",
                "| Group | Cases | Seconds | Promotable | Blocked | Failed |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for key in sorted(grouped):
            bucket = grouped[key]
            lines.append(
                f"| `{key}` | {int(bucket['cases'])} | {round(bucket['seconds'], 3)} | "
                f"{int(bucket['promotable'])} | {int(bucket['blocked'])} | {int(bucket['failed'])} |"
            )
    if report.get("weakness_loop"):
        loop = report["weakness_loop"]
        lines.extend(
            [
                "",
                "## Benchmark Patch Rerun Loop",
                "",
                f"- claim_boundary: {loop['claim_boundary']}",
                "",
                "### Public Benchmark Targets",
                "",
                "| Target | What It Tests | SCBE Gap |",
                "|---|---|---|",
            ]
        )
        for target in loop["public_benchmark_targets"]:
            lines.append(f"| [{target['name']}]({target['url']}) | {target['what_it_tests']} | {target['scbe_gap']} |")
        lines.extend(
            [
                "",
                "### Current Weaknesses",
                "",
                "| Weakness | Observed | Why We Lose | Patch Direction | Rerun |",
                "|---|---|---|---|---|",
            ]
        )
        for weakness in loop["weaknesses"]:
            lines.append(
                "| {weakness} | {observed} | {why_we_lose} | {patch_direction} | `{rerun}` |".format(**weakness)
            )
    if report.get("kaggle_winner_loop"):
        loop = report["kaggle_winner_loop"]
        lines.extend(
            [
                "",
                "## Kaggle-Style Improvement Loop",
                "",
                f"- schema: `{loop['schema']}`",
                f"- claim_boundary: {loop['claim_boundary']}",
                f"- weakest_stage: `{loop['weakest_stage']}`",
                f"- next_best_patch: {loop['next_best_patch']}",
                f"- next_rerun: `{loop['next_rerun']}`",
                "",
                "| Stage | Cases | Avg Quality | Delta | Weakest Dimension | Next Repair |",
                "|---|---:|---:|---:|---|---|",
            ]
        )
        for stage in loop["stages"]:
            lines.append(
                "| {stage} | {case_count} | {quality} | {delta} | `{weakest}` | {repair} |".format(
                    stage=stage["stage"],
                    case_count=stage["case_count"],
                    quality=stage["average_quality_score"],
                    delta=(
                        "" if stage["delta_from_previous_run_stage"] is None else stage["delta_from_previous_run_stage"]
                    ),
                    weakest=stage["weakest_dimension"],
                    repair=stage["next_repair_task"],
                )
            )
        cloud = loop["ollama_cloud"]
        lines.extend(
            [
                "",
                "### Ollama Cloud",
                "",
                f"- enabled_case_count: `{cloud['enabled_case_count']}`",
                f"- prefer_cloud_case_count: `{cloud['prefer_cloud_case_count']}`",
                f"- models_seen: `{json.dumps(cloud['models_seen'])}`",
                f"- note: {cloud['note']}",
            ]
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This benchmark scores the orchestration contract: agent catalog resolution, local/cloud "
            "model routing, promotion/blocked counts, and routing recommendations. It does not claim "
            "the generated code is correct unless a lane is promotable and then passes "
            "`scripts/agents/safe_apply.py` with a smoke command.",
            "",
            "A run with zero promotable lanes can still be a useful pass when the router correctly "
            "blocks confident but non-applicable proposals before patch application.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OpenClaw swarm benchmark cases.")
    parser.add_argument(
        "--mode",
        choices=(
            "quick",
            "full",
            "concurrency",
            "ollama-cloud",
            "roles",
            "semantic",
            "loop",
            "public-parallel",
            "safe-apply",
            "kaggle-loop",
            "self-cli-functional",
        ),
        default="quick",
    )
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--limit", type=int, default=0, help="Run only the first N cases.")
    parser.add_argument("--case-workers", type=int, default=0, help="Run benchmark cases in parallel when >1.")
    parser.add_argument(
        "--self-cli-models",
        nargs="+",
        default=list(DEFAULT_SELF_CLI_MODELS),
        help="Ollama model names for --mode self-cli-functional.",
    )
    parser.add_argument("--self-cli-task-limit", type=int, default=3)
    parser.add_argument("--self-cli-repair-model", default="")
    parser.add_argument("--self-cli-repair-attempts", type=int, default=0)
    args = parser.parse_args()
    run_id = _utc_stamp()
    output_dir = allocate_output_dir(Path(args.output_root), run_id)
    run_id = output_dir.name

    if args.mode == "safe-apply":
        item = run_safe_apply_case(output_dir)
        report = build_single_case_report(run_id, args.mode, output_dir, item)
        print(
            json.dumps({"ok": True, "report": str(output_dir / "report.json"), "summary": report["summary"]}, indent=2)
        )
        return 0
    if args.mode == "self-cli-functional":
        item = run_self_cli_functional_case(
            output_dir,
            tuple(args.self_cli_models),
            task_limit=max(1, int(args.self_cli_task_limit)),
            repair_model=args.self_cli_repair_model,
            repair_attempts=max(0, int(args.self_cli_repair_attempts)),
        )
        report = build_single_case_report(run_id, args.mode, output_dir, item)
        print(
            json.dumps({"ok": True, "report": str(output_dir / "report.json"), "summary": report["summary"]}, indent=2)
        )
        return 0

    if args.mode == "quick":
        cases = QUICK_CASES
    elif args.mode == "full":
        cases = FULL_CASES
    elif args.mode == "ollama-cloud":
        cases = OLLAMA_CLOUD_CASES
    elif args.mode == "roles":
        cases = ROLE_CASES
    elif args.mode == "semantic":
        cases = SEMANTIC_CASES
    elif args.mode == "loop":
        cases = ROLE_CASES + SEMANTIC_CASES
    elif args.mode == "public-parallel":
        cases = PUBLIC_PARALLEL_CASES
    elif args.mode == "kaggle-loop":
        cases = KAGGLE_LOOP_CASES
    else:
        cases = CONCURRENCY_CASES
    if args.limit > 0:
        cases = cases[: args.limit]
    case_workers = args.case_workers
    if case_workers <= 0 and args.mode == "public-parallel":
        case_workers = min(3, len(cases))
    results = []
    if case_workers > 1:
        with ThreadPoolExecutor(max_workers=case_workers) as executor:
            future_map = {executor.submit(run_case, case): case for case in cases}
            for future in as_completed(future_map):
                results.append(future.result())
                results.sort(key=lambda item: item["case"]["case_id"])
                partial_summary = build_summary(
                    results,
                    completed_cases=len(results),
                    planned_cases=len(cases),
                    case_workers=case_workers,
                )
                partial_report = {
                    "schema": "openclaw_swarm_benchmark_v1",
                    "run_id": run_id,
                    "mode": args.mode,
                    "summary": partial_summary,
                    "cases": results,
                    "semantic_task_variables": [build_semantic_task_variables(item) for item in results],
                }
                partial_report["weakness_loop"] = build_weakness_loop(partial_report)
                partial_report["kaggle_winner_loop"] = build_kaggle_winner_loop(partial_report)
                partial_report["geometric_consensus"] = build_geometric_consensus(partial_report)
                partial_report["trust_ladder_report"] = build_trust_ladder_report(partial_report)
                _write_json(output_dir / "partial_report.json", partial_report)
                (output_dir / "partial_report.md").write_text(build_markdown(partial_report), encoding="utf-8")
    else:
        for case in cases:
            results.append(run_case(case))
            partial_summary = build_summary(
                results,
                completed_cases=len(results),
                planned_cases=len(cases),
                case_workers=case_workers or 1,
            )
            partial_report = {
                "schema": "openclaw_swarm_benchmark_v1",
                "run_id": run_id,
                "mode": args.mode,
                "summary": partial_summary,
                "cases": results,
                "semantic_task_variables": [build_semantic_task_variables(item) for item in results],
            }
            partial_report["weakness_loop"] = build_weakness_loop(partial_report)
            partial_report["kaggle_winner_loop"] = build_kaggle_winner_loop(partial_report)
            partial_report["geometric_consensus"] = build_geometric_consensus(partial_report)
            partial_report["trust_ladder_report"] = build_trust_ladder_report(partial_report)
            _write_json(output_dir / "partial_report.json", partial_report)
            (output_dir / "partial_report.md").write_text(build_markdown(partial_report), encoding="utf-8")
    summary = build_summary(results)
    report = {
        "schema": "openclaw_swarm_benchmark_v1",
        "run_id": run_id,
        "mode": args.mode,
        "summary": summary,
        "cases": results,
        "semantic_task_variables": [build_semantic_task_variables(item) for item in results],
    }
    report["weakness_loop"] = build_weakness_loop(report)
    report["kaggle_winner_loop"] = build_kaggle_winner_loop(report)
    report["geometric_consensus"] = build_geometric_consensus(report)
    report["trust_ladder_report"] = build_trust_ladder_report(report)
    _write_json(output_dir / "report.json", report)
    (output_dir / "report.md").write_text(build_markdown(report), encoding="utf-8")
    latest = Path(args.output_root) / "latest"
    _write_json(latest / "report.json", report)
    (latest / "report.md").write_text(build_markdown(report), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(output_dir / "report.json"), "summary": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
