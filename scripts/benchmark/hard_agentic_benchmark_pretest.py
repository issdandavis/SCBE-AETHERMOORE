#!/usr/bin/env python3
"""Run a local pretest matrix for hard public agentic benchmarks.

This is not a leaderboard runner. It separates three things:

1. What SCBE can execute locally right now.
2. What public benchmark setup is missing.
3. Why the benchmark blocks agents, and what non-leaky assistance an agent
   harness may provide without handing over the answer.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "artifacts" / "benchmarks" / "hard_agentic_pretest"


@dataclass(frozen=True)
class BenchmarkTarget:
    benchmark_id: str
    display_name: str
    domain: str
    official_url: str
    public_context: str
    why_hard: str
    defender_view: str
    non_leaky_assist: tuple[str, ...]
    pretest_command: tuple[str, ...] | None = None
    cwd: str = "."
    expected_blockers: tuple[str, ...] = ()
    setup_checks: tuple[tuple[str, ...], ...] = ()
    source_refs: tuple[str, ...] = ()


@dataclass
class PretestResult:
    benchmark_id: str
    display_name: str
    domain: str
    status: str
    score: float | None
    command: list[str] | None
    returncode: int | None
    duration_ms: int
    stdout_tail: str = ""
    stderr_tail: str = ""
    blockers: list[str] = field(default_factory=list)
    why_hard: str = ""
    defender_view: str = ""
    missing_link: list[str] = field(default_factory=list)
    public_context: str = ""
    official_url: str = ""
    source_refs: list[str] = field(default_factory=list)


TARGETS: tuple[BenchmarkTarget, ...] = (
    BenchmarkTarget(
        benchmark_id="scbe_swe_local_control",
        display_name="SCBE Local SWE-Style Control",
        domain="code repair/control",
        official_url="docs/benchmarks/SWE_LOCAL_BENCHMARK.md",
        public_context="Repo-local control benchmark; not official SWE-bench.",
        why_hard="Checks whether the agent control layer preserves task contracts instead of merely writing plausible code prose.",
        defender_view="The task withholds easy credit unless the exact executable contract is satisfied.",
        non_leaky_assist=(
            "Expose the required output contract before execution.",
            "Provide test command shape and artifact location.",
            "Reject answer-only responses when an executable patch is required.",
        ),
        pretest_command=("python", "scripts/benchmark/swe_local_benchmark.py"),
        source_refs=("docs/benchmarks/SWE_LOCAL_BENCHMARK.md",),
    ),
    BenchmarkTarget(
        benchmark_id="scbe_real_patch_fixtures",
        display_name="SCBE Real-Patch Fixtures",
        domain="code repair/execution",
        official_url="docs/benchmarks/SWE_LOCAL_BENCHMARK.md",
        public_context="Local broken mini-repos with pytest, patch receipts, and edit-scope checks.",
        why_hard="The lane requires a real source edit and passing tests; narrative answers score zero.",
        defender_view="The fixture defends against plan-only agents by checking filesystem diffs and pytest results.",
        non_leaky_assist=(
            "Show the failing test names and allowed edit files.",
            "Provide patch-scope receipts after each attempt.",
            "Permit retries driven by test failure text, not by hidden solution text.",
        ),
        pretest_command=("python", "scripts/benchmark/real_patch_task_benchmark.py"),
        source_refs=("docs/benchmarks/SWE_LOCAL_BENCHMARK.md",),
    ),
    BenchmarkTarget(
        benchmark_id="scbe_pathfinding_suite",
        display_name="SCBE Pathfinding Suite",
        domain="partial-observation planning",
        official_url="packages/agent-bus/scripts/bench_pathfinding_suite.cjs",
        public_context="Repo-local roll-stack, worm adapter, projection board, and vector-field navigation evidence suite.",
        why_hard="Shortest path is not always visible or optimal under fog, security state, importance depth, pressure, and local sensor radius.",
        defender_view="The maze defends itself by hiding global structure and rewarding robust penetration rather than perfect omniscience.",
        non_leaky_assist=(
            "Expose local sensor readings and uncertainty bands.",
            "Provide frontier/visited/pressure heat maps without revealing the hidden goal path.",
            "Allow ensemble route candidates and score them against safety and progress.",
        ),
        pretest_command=("node", "scripts/bench_pathfinding_suite.cjs"),
        cwd="packages/agent-bus",
        source_refs=("packages/agent-bus/scripts/bench_pathfinding_suite.cjs",),
    ),
    BenchmarkTarget(
        benchmark_id="public_harness_setup",
        display_name="Public Harness Setup",
        domain="benchmark readiness",
        official_url="docs/benchmarks/PUBLIC_AGENTIC_CLI_BENCHMARK_PLAN.md",
        public_context="Local readiness checks for Terminal-Bench, SWE-bench, Aider Polyglot, and Vexp SWE-bench.",
        why_hard="Public harnesses require Docker, exact agent adapters, and repeatable artifact packets.",
        defender_view="The benchmark defends against inflated claims by refusing to score unless the public harness actually runs.",
        non_leaky_assist=(
            "Install/readiness checks before attempting full scoring.",
            "Emit exact missing prerequisites.",
            "Run small setup-only jobs before cost-heavy model runs.",
        ),
        pretest_command=("python", "scripts/benchmark/setup_public_agentic_benchmarks.py", "--dry-run"),
        source_refs=("docs/benchmarks/PUBLIC_AGENTIC_CLI_BENCHMARK_PLAN.md",),
    ),
    BenchmarkTarget(
        benchmark_id="swe_bench_verified_readiness",
        display_name="SWE-bench Verified Readiness",
        domain="public code repair",
        official_url="https://www.swebench.com/",
        public_context=(
            "SWE-bench Verified remains useful but OpenAI has reported it is no longer a clean frontier-only measure."
        ),
        why_hard="Requires reproducing real repository bugs inside Docker and producing patches that pass hidden/task tests.",
        defender_view="The task blocks shallow agents with environment setup, repo scale, issue ambiguity, and test-only acceptance.",
        non_leaky_assist=(
            "Provide repository map and failing test commands.",
            "Expose allowed patch files and dependency setup.",
            "Give test failure deltas after each attempt, never the gold patch.",
        ),
        pretest_command=("python", "scripts/benchmark/swe_verified_readiness.py"),
        expected_blockers=("docker", "swebench_harness"),
        source_refs=("https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/",),
    ),
    BenchmarkTarget(
        benchmark_id="terminal_bench",
        display_name="Terminal-Bench",
        domain="terminal execution",
        official_url="https://terminalbench.lol/",
        public_context="Versioned terminal task benchmark with sandbox execution, verifier scripts, and public leaderboard.",
        why_hard="Agents must operate in a shell, inspect files, run commands, fix state, and satisfy verifier scripts.",
        defender_view="The benchmark prevents answer-only success by validating final filesystem/process state.",
        non_leaky_assist=(
            "Expose safe command affordances and current working directory.",
            "Provide verifier failure text and command receipts.",
            "Keep a bounded scratchpad of observed filesystem facts.",
        ),
        setup_checks=(("tb", "--help"), ("docker", "--version")),
        expected_blockers=("tb", "docker"),
        source_refs=("https://terminalbench.lol/",),
    ),
    BenchmarkTarget(
        benchmark_id="arc_agi_2",
        display_name="ARC-AGI-2",
        domain="abstract reasoning",
        official_url="https://arcprize.org/arc-agi/2",
        public_context="ARC-AGI-2 is calibrated for human solvability while remaining difficult for current AI systems.",
        why_hard="Tasks require discovering new visual rules from tiny examples rather than retrieving known facts.",
        defender_view="The task defends itself with novelty: no instruction text, few examples, and no reusable single algorithm.",
        non_leaky_assist=(
            "Provide reversible grid transforms and hypothesis slots.",
            "Run candidate programs against public train examples.",
            "Expose contradiction traces when a hypothesis fails, without revealing test output.",
        ),
        setup_checks=(("python", "-c", "from pathlib import Path; raise SystemExit(0 if Path('artifacts/arc-data').exists() else 1)"),),
        expected_blockers=("arc_agi_2_dataset_or_checkout",),
        source_refs=("https://arcprize.org/arc-agi/2", "https://arxiv.org/abs/2505.11831"),
    ),
    BenchmarkTarget(
        benchmark_id="mle_bench",
        display_name="MLE-bench",
        domain="ML engineering/Kaggle",
        official_url="https://openai.com/index/mle-bench/",
        public_context="OpenAI reports o1-preview with AIDE reached at least Kaggle bronze level in 16.9% of competitions.",
        why_hard="Requires data loading, experiment design, training, validation, submission formatting, and iteration under time/compute limits.",
        defender_view="The benchmark blocks agents that cannot execute experiments or learn from metric feedback.",
        non_leaky_assist=(
            "Expose dataset schema, scoring metric, and submission format.",
            "Provide experiment ledger and validation curves.",
            "Suggest next experiment families without leaking leaderboard labels.",
        ),
        setup_checks=(("kaggle", "--version"), ("python", "-c", "import pandas, sklearn; print('ml stack ok')")),
        expected_blockers=("kaggle_cli_or_credentials", "ml_stack"),
        source_refs=("https://openai.com/index/mle-bench/",),
    ),
    BenchmarkTarget(
        benchmark_id="browsecomp",
        display_name="BrowseComp",
        domain="deep web research",
        official_url="https://openai.com/index/browsecomp/",
        public_context="OpenAI reports GPT-4o with browsing at 1.9%, o1 at 9.9%, and Deep Research at 51.5%.",
        why_hard="Answers are short and easy to verify but require persistent multi-hop search across obscure sources.",
        defender_view="The benchmark hides the answer behind search strategy rather than computation alone.",
        non_leaky_assist=(
            "Maintain a search-branch ledger.",
            "Force source-backed candidate answers.",
            "Use best-of-N verification over independent search paths.",
        ),
        setup_checks=(("python", "-c", "import requests; print('requests ok')"), ("git", "--version")),
        source_refs=("https://openai.com/index/browsecomp/", "https://github.com/openai/simple-evals"),
    ),
    BenchmarkTarget(
        benchmark_id="gaia",
        display_name="GAIA",
        domain="general assistant/tool use",
        official_url="https://huggingface.co/learn/agents-course/unit4/what-is-gaia",
        public_context="Hugging Face describes GAIA as 466 tasks; humans about 92%, GPT-4 with plugins about 15%, Deep Research 67.36% validation.",
        why_hard="Requires planning across web, files, multimodal evidence, and precise answer formatting.",
        defender_view="The task blocks single-shot chat by requiring grounded multi-tool execution and concise final answers.",
        non_leaky_assist=(
            "Provide a typed tool menu and evidence packet.",
            "Require each answer to cite retrieval or file evidence.",
            "Track unresolved subgoals and formatting constraints.",
        ),
        setup_checks=(("python", "-c", "import datasets; print('datasets ok')"),),
        expected_blockers=("huggingface_datasets_or_gaia_access",),
        source_refs=("https://huggingface.co/learn/agents-course/unit4/what-is-gaia",),
    ),
    BenchmarkTarget(
        benchmark_id="webarena_visualwebarena",
        display_name="WebArena / VisualWebArena",
        domain="browser operation",
        official_url="https://webarena.dev/",
        public_context="WebArena paper reports best GPT-4-based agent at 14.41% task success versus 78.24% human performance.",
        why_hard="Agents must operate long-horizon web tasks in stateful sites with DOM, visual grounding, and hidden success conditions.",
        defender_view="The site defends itself with state, navigation depth, ambiguous UI labels, and irreversible actions.",
        non_leaky_assist=(
            "Provide DOM snapshots, screenshots, and action receipts.",
            "Keep reversible navigation history and form-state diffs.",
            "Expose success-check hints as rubric categories, not target values.",
        ),
        setup_checks=(("docker", "--version"), ("python", "-c", "import playwright; print('playwright ok')")),
        expected_blockers=("docker", "browser_benchmark_checkout"),
        source_refs=("https://arxiv.org/abs/2307.13854", "https://arxiv.org/abs/2401.13649"),
    ),
    BenchmarkTarget(
        benchmark_id="osworld",
        display_name="OSWorld",
        domain="desktop/computer use",
        official_url="https://os-world.github.io/",
        public_context="OSWorld evaluates real computer tasks across desktop applications and web interfaces.",
        why_hard="The agent must use GUI state, applications, files, and multi-step procedures rather than plain text.",
        defender_view="The OS blocks agents through visual state, app-specific workflows, timing, and hidden verifier state.",
        non_leaky_assist=(
            "Provide perception snapshots and active-window metadata.",
            "Record UI action receipts and reversible checkpoints.",
            "Expose task progress predicates without giving coordinates for every click.",
        ),
        setup_checks=(("python", "-c", "import pyautogui; print('gui stack ok')"),),
        expected_blockers=("desktop_eval_stack",),
        source_refs=("https://os-world.github.io/",),
    ),
    BenchmarkTarget(
        benchmark_id="vending_bench",
        display_name="Vending-Bench",
        domain="long-horizon coherence",
        official_url="https://arxiv.org/abs/2502.15840",
        public_context="Long-term autonomous vending-machine business simulation for coherence and capital acquisition behavior.",
        why_hard="Requires stable goals, inventory, pricing, memory, finance, and adaptation over long simulated horizons.",
        defender_view="The environment punishes state drift, short-term greed, forgotten constraints, and inconsistent business policy.",
        non_leaky_assist=(
            "Provide durable business ledger state.",
            "Summarize invariant policies before each decision.",
            "Score long-term stability separately from immediate profit.",
        ),
        setup_checks=(("python", "-c", "import inspect_ai; print('inspect ok')"),),
        expected_blockers=("inspect_ai_or_vending_bench_env",),
        source_refs=("https://arxiv.org/abs/2502.15840",),
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_command(command: tuple[str, ...], cwd: Path, timeout: int) -> tuple[int, str, str, int]:
    started = datetime.now()
    try:
        proc = subprocess.run(
            list(command),
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        elapsed = int((datetime.now() - started).total_seconds() * 1000)
        return proc.returncode, proc.stdout, proc.stderr, elapsed
    except FileNotFoundError as exc:
        elapsed = int((datetime.now() - started).total_seconds() * 1000)
        return 127, "", str(exc), elapsed
    except subprocess.TimeoutExpired as exc:
        elapsed = int((datetime.now() - started).total_seconds() * 1000)
        return 124, exc.stdout or "", exc.stderr or "timeout", elapsed


def tail(value: str, limit: int = 2200) -> str:
    return value[-limit:] if len(value) > limit else value


def extract_score(target: BenchmarkTarget, returncode: int, stdout: str) -> float | None:
    if target.benchmark_id == "scbe_swe_local_control":
        try:
            payload = json.loads(stdout)
            return float(payload["mechanical_ensemble"]["pass_rate"])
        except Exception:
            return None
    if target.benchmark_id == "scbe_real_patch_fixtures":
        match = re.search(r"baseline=(\d+)/(\d+)\s+scbe=(\d+)/(\d+)", stdout)
        if match:
            return int(match.group(3)) / max(1, int(match.group(4)))
    if target.benchmark_id == "scbe_pathfinding_suite":
        try:
            payload = json.loads(stdout)
            return float(payload["summary"]["avg_primary_score"])
        except Exception:
            return None
    if target.benchmark_id == "public_harness_setup":
        try:
            payload = json.loads(stdout)
            return 1.0 if payload.get("ok") else 0.0
        except Exception:
            return None
    if target.benchmark_id == "swe_bench_verified_readiness":
        try:
            payload = json.loads(stdout)
            return 1.0 if payload.get("official_swe_bench_verified_local_ready") else 0.0
        except Exception:
            return None
    return 1.0 if returncode == 0 else 0.0


def check_setup(target: BenchmarkTarget, timeout: int) -> tuple[str, list[str], list[dict[str, Any]], int]:
    blockers: list[str] = []
    checks: list[dict[str, Any]] = []
    elapsed_total = 0
    for command in target.setup_checks:
        if shutil.which(command[0]) is None and command[0] not in {"python"}:
            checks.append(
                {
                    "command": list(command),
                    "ok": False,
                    "returncode": 127,
                    "stdout_tail": "",
                    "stderr_tail": f"{command[0]} not found on PATH",
                }
            )
            blockers.append(command[0])
            continue
        returncode, stdout, stderr, elapsed = run_command(command, REPO_ROOT, timeout)
        elapsed_total += elapsed
        ok = returncode == 0
        checks.append(
            {
                "command": list(command),
                "ok": ok,
                "returncode": returncode,
                "stdout_tail": tail(stdout, 800),
                "stderr_tail": tail(stderr, 800),
            }
        )
        if not ok:
            blockers.append(command[0] if command[0] != "python" else target.expected_blockers[0] if target.expected_blockers else "python_check")
    status = "READY_PRETEST" if not blockers else "BLOCKED_SETUP"
    return status, sorted(set(blockers)), checks, elapsed_total


def run_target(target: BenchmarkTarget, timeout: int) -> PretestResult:
    if target.pretest_command:
        cwd = REPO_ROOT / target.cwd
        returncode, stdout, stderr, elapsed = run_command(target.pretest_command, cwd, timeout)
        score = extract_score(target, returncode, stdout)
        blockers: list[str] = []
        if returncode != 0:
            if target.expected_blockers:
                blockers.extend(target.expected_blockers)
            else:
                blockers.append("pretest_command_failed")
        status = "EXECUTED_PASS" if returncode == 0 else "BLOCKED_OR_FAILED"
        return PretestResult(
            benchmark_id=target.benchmark_id,
            display_name=target.display_name,
            domain=target.domain,
            status=status,
            score=score,
            command=list(target.pretest_command),
            returncode=returncode,
            duration_ms=elapsed,
            stdout_tail=tail(stdout),
            stderr_tail=tail(stderr),
            blockers=blockers,
            why_hard=target.why_hard,
            defender_view=target.defender_view,
            missing_link=list(target.non_leaky_assist),
            public_context=target.public_context,
            official_url=target.official_url,
            source_refs=list(target.source_refs),
        )
    status, blockers, checks, elapsed = check_setup(target, timeout)
    return PretestResult(
        benchmark_id=target.benchmark_id,
        display_name=target.display_name,
        domain=target.domain,
        status=status,
        score=1.0 if status == "READY_PRETEST" else 0.0,
        command=None,
        returncode=None,
        duration_ms=elapsed,
        stdout_tail=json.dumps(checks, indent=2),
        blockers=blockers,
        why_hard=target.why_hard,
        defender_view=target.defender_view,
        missing_link=list(target.non_leaky_assist),
        public_context=target.public_context,
        official_url=target.official_url,
        source_refs=list(target.source_refs),
    )


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Hard Agentic Benchmark Pretest",
        "",
        f"Generated: `{payload['generated_at_utc']}`",
        f"Executed targets: `{payload['summary']['executed']} / {payload['summary']['target_count']}`",
        f"Ready/setup-pass targets: `{payload['summary']['ready_or_pass']} / {payload['summary']['target_count']}`",
        "",
        "## Scorecard",
        "",
        "| Benchmark | Domain | Status | Score | Blockers |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in payload["results"]:
        score = "" if row["score"] is None else f"{row['score']:.4f}"
        blockers = ", ".join(row["blockers"]) if row["blockers"] else "none"
        lines.append(
            f"| {row['display_name']} | {row['domain']} | `{row['status']}` | `{score}` | {blockers} |"
        )
    lines.extend(["", "## Task Defender Analysis", ""])
    for row in payload["results"]:
        lines.extend(
            [
                f"### {row['display_name']}",
                "",
                f"- Public context: {row['public_context']}",
                f"- Why agents fail: {row['why_hard']}",
                f"- Defender view: {row['defender_view']}",
                "- Missing-link assistance that does not leak the answer:",
                *[f"  - {item}" for item in row["missing_link"]],
                "",
            ]
        )
    lines.extend(["## Sources", ""])
    seen = set()
    for row in payload["results"]:
        for ref in row["source_refs"] or [row["official_url"]]:
            if ref in seen:
                continue
            seen.add(ref)
            lines.append(f"- {ref}")
    return "\n".join(lines) + "\n"


def build_report(out_dir: Path, timeout: int, filter_ids: set[str] | None = None) -> dict[str, Any]:
    selected = [target for target in TARGETS if not filter_ids or target.benchmark_id in filter_ids]
    results = [run_target(target, timeout) for target in selected]
    payload = {
        "schema_version": "scbe_hard_agentic_benchmark_pretest_v1",
        "generated_at_utc": utc_now(),
        "claim_boundary": "pretest_matrix_not_public_leaderboard_score",
        "summary": {
            "target_count": len(results),
            "executed": sum(1 for result in results if result.command is not None),
            "ready_or_pass": sum(result.status in {"EXECUTED_PASS", "READY_PRETEST"} for result in results),
            "blocked_or_failed": sum(result.status in {"BLOCKED_OR_FAILED", "BLOCKED_SETUP"} for result in results),
        },
        "results": [result.__dict__ for result in results],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "latest_report.json"
    md_path = out_dir / "LATEST.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {"payload": payload, "json": str(json_path), "markdown": str(md_path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--filter", action="append", default=[], help="Run only a benchmark_id; repeatable.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.out_dir, args.timeout, set(args.filter) if args.filter else None)
    if args.json:
        print(json.dumps(report["payload"], indent=2, sort_keys=True))
    else:
        summary = report["payload"]["summary"]
        print(
            "hard benchmark pretest: "
            f"ready_or_pass={summary['ready_or_pass']}/{summary['target_count']} "
            f"blocked_or_failed={summary['blocked_or_failed']}/{summary['target_count']}"
        )
        print(f"report={report['json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
