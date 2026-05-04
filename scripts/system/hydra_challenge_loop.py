#!/usr/bin/env python3
"""Self-healing HYDRA challenge loop for repo-native agentic evals.

The loop uses the compound matrix council to pick a challenge style, runs a
bounded local verifier, and records recovery decisions when an attempt fails.
It is meant to prove the workflow locally before using Kaggle, Hugging Face, or
other remote workers.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.system.agent_context_vault import append_event, digest_agent  # noqa: E402
from scripts.system.hydra_challenge_eval import write_eval  # noqa: E402
from scripts.system.hydra_challenge_reloop import build_reloop_plan  # noqa: E402
from scripts.system.multi_model_compound_matrix import build_council_packet  # noqa: E402

SCHEMA_VERSION = "scbe_hydra_challenge_loop_v1"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "agent_context_vault" / "challenge_loop"


@dataclass(frozen=True)
class Challenge:
    challenge_id: str
    title: str
    command: list[str]
    max_attempts: int
    success_metric: str
    recovery_command: list[str] | None = None


CHALLENGES = {
    "repo_ladder_validate": Challenge(
        challenge_id="repo_ladder_validate",
        title="Validate repo-native agentic benchmark task manifests",
        command=[sys.executable, "scripts/benchmark/agentic_benchmark_ladder.py", "validate"],
        max_attempts=2,
        success_metric="manifest_validation_ok",
        recovery_command=[sys.executable, "scripts/benchmark/agentic_benchmark_ladder.py", "list"],
    ),
    "repo_ladder_level1": Challenge(
        challenge_id="repo_ladder_level1",
        title="Run repo-native agentic benchmark ladder through level 1",
        command=[sys.executable, "scripts/benchmark/agentic_benchmark_ladder.py", "run", "--max-level", "1"],
        max_attempts=2,
        success_metric="ladder_ok_true",
        recovery_command=[sys.executable, "scripts/benchmark/agentic_benchmark_ladder.py", "validate"],
    ),
    "external_eval_validate": Challenge(
        challenge_id="external_eval_validate",
        title="Validate external agentic eval adapter manifest",
        command=[
            sys.executable,
            "scripts/benchmark/external_agentic_eval_driver.py",
            "--manifest",
            "config/eval/external_agentic_eval_tasks.sample.json",
            "--validate-only",
        ],
        max_attempts=2,
        success_metric="external_manifest_ok",
        recovery_command=[
            sys.executable,
            "scripts/benchmark/external_agentic_eval_driver.py",
            "--manifest",
            "config/eval/external_agentic_eval_tasks.sample.json",
        ],
    ),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_command(command: list[str], timeout: int) -> dict[str, Any]:
    started = time.perf_counter()
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    elapsed = time.perf_counter() - started
    return {
        "command": command,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "elapsed_sec": round(elapsed, 3),
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
    }


def _classify_failure(result: dict[str, Any]) -> dict[str, Any]:
    text = f"{result.get('stdout_tail', '')}\n{result.get('stderr_tail', '')}".lower()
    if result.get("ok"):
        return {"class": "none", "recovery": "not_needed"}
    if "timeout" in text:
        return {"class": "timeout", "recovery": "shrink_scope_and_preserve_logs"}
    if "missing" in text or "not found" in text or "no such file" in text:
        return {"class": "missing_artifact", "recovery": "run_inventory_then_retry"}
    if "json" in text or "manifest" in text:
        return {"class": "manifest_or_schema", "recovery": "validate_manifest_then_retry"}
    if "secret" in text or "token" in text:
        return {"class": "security_leak_guard", "recovery": "stop_and_scrub_before_retry"}
    return {"class": "unknown", "recovery": "run_recovery_command_then_retry_once"}


def _parse_json_tail(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def run_challenge_loop(
    *,
    challenge_id: str = "repo_ladder_validate",
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    timeout: int = 600,
    max_attempts: int | None = None,
    rounds: int = 1,
    attempts_per_round: int | None = None,
    continue_after_pass: bool = False,
) -> dict[str, Any]:
    if challenge_id not in CHALLENGES:
        raise ValueError(f"unknown challenge_id: {challenge_id}")
    challenge = CHALLENGES[challenge_id]
    council = build_council_packet()
    attempts: list[dict[str, Any]] = []
    round_summaries: list[dict[str, Any]] = []
    recovery_events: list[dict[str, Any]] = []
    rounds = max(1, rounds)
    limit = max(1, attempts_per_round or max_attempts or challenge.max_attempts)
    channel_id = f"challenge-{challenge.challenge_id}"

    append_event(
        agent_id="agent.codex",
        channel_id=channel_id,
        task_id=challenge.challenge_id,
        intent="challenge_start",
        summary=f"Starting HYDRA challenge loop: {challenge.title}",
        proof=["scripts/system/hydra_challenge_loop.py"],
        next_action="Run verifier and record attempt.",
    )

    global_attempt = 0
    for round_index in range(1, rounds + 1):
        round_start_state = digest_agent(agent_id="agent.codex")
        round_attempts: list[dict[str, Any]] = []
        append_event(
            agent_id="agent.codex",
            channel_id=channel_id,
            task_id=challenge.challenge_id,
            intent="challenge_round_start",
            summary=f"Round {round_index} starts without resetting the context ledger.",
            proof=[f"round:{round_index}", f"start_state_hash:{round_start_state['state_hash']}"],
            next_action=f"Spend up to {limit} time packets on the verifier.",
        )
        for attempt_in_round in range(1, limit + 1):
            global_attempt += 1
            result = _run_command(challenge.command, timeout=timeout)
            classification = _classify_failure(result)
            parsed_stdout = _parse_json_tail(result.get("stdout_tail", ""))
            attempt = {
                "attempt": global_attempt,
                "round": round_index,
                "attempt_in_round": attempt_in_round,
                "phase": "execute",
                "result": result,
                "classification": classification,
                "parsed_stdout": parsed_stdout,
            }
            attempts.append(attempt)
            round_attempts.append(attempt)
            append_event(
                agent_id="agent.codex",
                channel_id=channel_id,
                task_id=challenge.challenge_id,
                intent="challenge_attempt",
                status="done" if result["ok"] else "blocked",
                summary=(
                    f"Round {round_index} attempt {attempt_in_round} returned "
                    f"{result['returncode']} for {challenge.challenge_id}."
                ),
                proof=[
                    f"metric:{challenge.success_metric}",
                    f"returncode:{result['returncode']}",
                    f"round:{round_index}",
                ],
                next_action="Continue ledger run." if result["ok"] and continue_after_pass else classification["recovery"],
                risk="low" if result["ok"] else "medium",
            )
            if result["ok"] and not continue_after_pass:
                break
            if not result["ok"] and attempt_in_round < limit and challenge.recovery_command:
                recovery_result = _run_command(challenge.recovery_command, timeout=timeout)
                recovery_events.append(
                    {
                        "after_attempt": global_attempt,
                        "round": round_index,
                        "command": challenge.recovery_command,
                        "result": recovery_result,
                        "reason": classification["recovery"],
                    }
                )
        round_end_state = digest_agent(agent_id="agent.codex")
        round_summaries.append(
            {
                "round": round_index,
                "attempt_count": len(round_attempts),
                "pass_count": sum(1 for item in round_attempts if item["result"]["ok"]),
                "fail_count": sum(1 for item in round_attempts if not item["result"]["ok"]),
                "start_state_hash": round_start_state["state_hash"],
                "end_state_hash": round_end_state["state_hash"],
                "ledger_continued": round_index == 1 or round_summaries[-1]["end_state_hash"] != "",
            }
        )

    quorum = _build_improvement_quorum(round_summaries, attempts, council)
    append_event(
        agent_id="agent.codex",
        channel_id=channel_id,
        task_id=challenge.challenge_id,
        intent="challenge_quorum_improvement",
        status="done" if quorum["decision"] == "PROMOTE" else "blocked",
        summary=quorum["summary"],
        proof=quorum["proof"],
        next_action=quorum["next_action"],
        risk="low" if quorum["decision"] == "PROMOTE" else "medium",
    )

    ok = bool(attempts and attempts[-1]["result"]["ok"])
    state = digest_agent(agent_id="agent.codex")
    report = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "challenge": {
            "challenge_id": challenge.challenge_id,
            "title": challenge.title,
            "success_metric": challenge.success_metric,
            "command": challenge.command,
        },
        "ok": ok,
        "attempt_count": len(attempts),
        "round_count": rounds,
        "time_packets_per_round": limit,
        "continue_after_pass": continue_after_pass,
        "round_summaries": round_summaries,
        "attempts": attempts,
        "recovery_events": recovery_events,
        "improvement_quorum": quorum,
        "council_primary_operation": council["council_conclusion"]["primary_use"],
        "council_top_operations": [
            {"id": op["id"], "score": op["score"], "formation": op["selected_formation"]}
            for op in council["candidate_operations"][:5]
        ],
        "self_healing_policy": {
            "on_timeout": "shrink_scope_and_preserve_logs",
            "on_missing_artifact": "run_inventory_then_retry",
            "on_manifest_or_schema": "validate_manifest_then_retry",
            "on_security_leak_guard": "stop_and_scrub_before_retry",
            "successful_trace_policy": "convert to training row only after held-out gates pass",
        },
        "context_state_hash": state["state_hash"],
    }
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / f"{challenge.challenge_id}_latest.json"
    md_path = output_root / f"{challenge.challenge_id}_latest.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    eval_payload = write_eval(json_path, output_root / "eval")
    reloop_payload = build_reloop_plan(
        eval_path=Path(str(eval_payload["artifact_path"])),
        output_root=output_root / "loops",
        execute_next=False,
    )
    report["pipeline"] = {
        "eval_artifact": eval_payload["artifact_path"],
        "eval_hash": eval_payload["eval_hash"],
        "completion_factor": eval_payload["completion_factor"],
        "residual": eval_payload["residual"],
        "reloop_plan_hash": reloop_payload["plan"]["plan_hash"],
        "reloop_temp_dir": reloop_payload["plan"]["temp_dir"],
        "next_challenge": reloop_payload["plan"]["next_challenge"],
    }
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    return {**report, "artifact_paths": {"json": str(json_path), "markdown": str(md_path)}}


def _build_improvement_quorum(
    round_summaries: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    council: dict[str, Any],
) -> dict[str, Any]:
    pass_count = sum(1 for item in attempts if item["result"]["ok"])
    fail_count = sum(1 for item in attempts if not item["result"]["ok"])
    leader_vote = pass_count > 0
    desk_pair_vote = fail_count == 0
    secretary_vote = len(round_summaries) >= 2 and all(row["end_state_hash"] for row in round_summaries)
    decision = "PROMOTE" if leader_vote else "HOLD"
    return {
        "schema_version": "scbe_hydra_improvement_quorum_v1",
        "decision": decision,
        "leader_vote_is_decisive": True,
        "votes": {
            "leader_context_vote": leader_vote,
            "desk_pair_clean_run_vote": desk_pair_vote,
            "context_secretary_continuity_vote": secretary_vote,
        },
        "summary": (
            f"Two-run ledger review saw {pass_count} passes and {fail_count} failures. "
            "Leader vote follows context continuity and verifier outcome before process preference."
        ),
        "agreed_test_additions": [
            "continuous rounds must preserve one task channel and write round_summaries",
            "third-pass quorum must record leader_context_vote as the decisive vote",
            "report must expose time_packets_per_round and continue_after_pass",
        ],
        "system_improvements": [
            "Keep successful attempts in the ledger instead of stopping context collection immediately.",
            "Use context secretary compression after each round to preserve residue without raw log bloat.",
            f"Prefer council primary operation {council['council_conclusion']['primary_use']} until a later gate beats it.",
        ],
        "proof": [
            f"pass_count:{pass_count}",
            f"fail_count:{fail_count}",
            f"rounds:{len(round_summaries)}",
        ],
        "next_action": "Promote continuous two-round challenge loops into the local benchmark gate."
        if decision == "PROMOTE"
        else "Hold and inspect failing attempts before promotion.",
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# HYDRA Challenge Loop Report",
        "",
        f"- challenge: `{report['challenge']['challenge_id']}`",
        f"- ok: `{report['ok']}`",
        f"- attempts: `{report['attempt_count']}`",
        f"- rounds: `{report.get('round_count', 1)}`",
        f"- time packets per round: `{report.get('time_packets_per_round', '')}`",
        f"- council primary operation: `{report['council_primary_operation']}`",
        f"- context state hash: `{report['context_state_hash']}`",
        f"- completion factor: `{(report.get('pipeline') or {}).get('completion_factor', '')}`",
        f"- next challenge: `{(report.get('pipeline') or {}).get('next_challenge', '')}`",
        "",
        "## Round Summaries",
        "",
    ]
    for summary in report.get("round_summaries", []):
        lines.append(
            f"- round `{summary['round']}` attempts `{summary['attempt_count']}` "
            f"passes `{summary['pass_count']}` fails `{summary['fail_count']}` "
            f"end `{summary['end_state_hash']}`"
        )
    lines.extend(
        [
            "",
            "## Improvement Quorum",
            "",
        ]
    )
    quorum = report.get("improvement_quorum") or {}
    if quorum:
        lines.extend(
            [
                f"- decision: `{quorum['decision']}`",
                f"- leader vote decisive: `{quorum['leader_vote_is_decisive']}`",
                f"- votes: `{json.dumps(quorum['votes'], sort_keys=True)}`",
                f"- summary: {quorum['summary']}",
                "",
            ]
        )
    lines.extend(
        [
        "## Attempts",
        "",
        ]
    )
    for attempt in report["attempts"]:
        result = attempt["result"]
        classification = attempt["classification"]
        lines.append(
            f"- attempt `{attempt['attempt']}` returncode `{result['returncode']}` ok `{result['ok']}` "
            f"class `{classification['class']}` recovery `{classification['recovery']}`"
        )
    lines.extend(["", "## Top Council Operations", ""])
    for op in report["council_top_operations"]:
        lines.append(f"- `{op['id']}` score `{op['score']}` formation `{op['formation']}`")
    lines.extend(["", "## Self-Healing Policy", ""])
    for key, value in report["self_healing_policy"].items():
        lines.append(f"- `{key}`: {value}")
    pipeline = report.get("pipeline") or {}
    if pipeline:
        lines.extend(
            [
                "",
                "## Eval And Reloop",
                "",
                f"- eval artifact: `{pipeline['eval_artifact']}`",
                f"- eval hash: `{pipeline['eval_hash']}`",
                f"- residual: `{pipeline['residual']}`",
                f"- reloop plan hash: `{pipeline['reloop_plan_hash']}`",
                f"- temp run directory: `{pipeline['reloop_temp_dir']}`",
                f"- next challenge: `{pipeline['next_challenge']}`",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--challenge", choices=sorted(CHALLENGES), default="repo_ladder_validate")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--max-attempts", type=int, default=None)
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--attempts-per-round", type=int, default=None)
    parser.add_argument("--continue-after-pass", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_challenge_loop(
        challenge_id=args.challenge,
        output_root=args.output_root,
        timeout=args.timeout,
        max_attempts=args.max_attempts,
        rounds=args.rounds,
        attempts_per_round=args.attempts_per_round,
        continue_after_pass=args.continue_after_pass,
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
