#!/usr/bin/env python3
"""Build a before-completion checklist from benchmark workflow artifacts.

This does not judge the model by consensus. It inspects executable evidence:
stats, per-case result JSON, and chat/test logs. Any miss becomes a known-fail
record plus a concrete retry/help plan before the workflow can claim completion.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "scbe_workflow_completion_checklist_v1"
FAILURE_PATTERNS = (
    "FAIL",
    "FAILED",
    "AssertionError",
    "TypeError",
    "ReferenceError",
    "SyntaxError",
    "IndentationError",
    "Expected:",
    "Received:",
    "Traceback",
    "Error:",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_text(path: Path, limit: int = 120_000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(text) <= limit:
        return text
    return text[-limit:]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _find_latest_stats(artifact_root: Path) -> Path | None:
    stats = sorted(artifact_root.rglob("latest_stats.yml"), key=lambda item: item.stat().st_mtime, reverse=True)
    return stats[0] if stats else None


def _extract_stats(stats_text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for key in (
        "test_cases",
        "model",
        "edit_format",
        "pass_rate_1",
        "pass_rate_2",
        "pass_num_1",
        "pass_num_2",
        "percent_cases_well_formed",
        "error_outputs",
        "num_malformed_responses",
        "num_with_malformed_responses",
        "user_asks",
        "lazy_comments",
        "syntax_errors",
        "indentation_errors",
        "exhausted_context_windows",
        "prompt_tokens",
        "completion_tokens",
        "test_timeouts",
        "total_tests",
        "seconds_per_case",
        "total_cost",
    ):
        match = re.search(rf"^\s*{re.escape(key)}:\s*(.+?)\s*$", stats_text, flags=re.MULTILINE)
        if not match:
            continue
        raw = match.group(1).strip()
        if raw in {"null", "None"}:
            fields[key] = None
            continue
        try:
            fields[key] = int(raw)
            continue
        except ValueError:
            # Not an integer; try float parsing before preserving raw text.
            pass
        try:
            fields[key] = float(raw)
            continue
        except ValueError:
            fields[key] = raw.strip("'\"")
    return fields


def _diagnostic_stem(path: Path) -> str:
    name = path.name
    for suffix in (".results.json", ".chat.history.md"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def _language_from_stem(stem: str) -> str:
    return stem.split("_", 1)[0] if "_" in stem else "unknown"


def _task_from_stem(stem: str) -> str:
    parts = stem.split("_")
    if "practice" in parts:
        index = parts.index("practice")
        if index + 1 < len(parts):
            return "_".join(parts[index + 1 :])
    return parts[-1] if parts else stem


def _extract_failure_lines(chat_text: str, max_lines: int = 30) -> list[str]:
    lines = []
    for line in chat_text.splitlines():
        compact = line.strip()
        if not compact:
            continue
        if any(pattern in compact for pattern in FAILURE_PATTERNS):
            lines.append(compact[:500])
        if len(lines) >= max_lines:
            break
    return lines


def _classify_failure(result: dict[str, Any], chat_text: str) -> list[str]:
    classes: list[str] = []
    outcomes = result.get("tests_outcomes")
    if isinstance(outcomes, list) and any(item is False for item in outcomes):
        classes.append("tests_failed")
        if len(outcomes) >= 2 and outcomes[0] is False and outcomes[-1] is False:
            classes.append("retry_did_not_recover")
        elif len(outcomes) >= 2 and outcomes[0] is False and outcomes[-1] is True:
            classes.append("retry_recovered")
    if result.get("syntax_errors"):
        classes.append("syntax_error")
    if result.get("indentation_errors"):
        classes.append("indentation_error")
    if result.get("num_malformed_responses"):
        classes.append("malformed_response")
    if result.get("num_user_asks"):
        classes.append("asked_user_instead_of_solving")
    if result.get("num_exhausted_context_windows"):
        classes.append("context_exhausted")
    if result.get("test_timeouts"):
        classes.append("timeout")
    if "length is not a function" in chat_text:
        classes.append("language_api_confusion")
    if re.search(r"Expected:\s*\d+.*Received:\s*\d+", chat_text, flags=re.DOTALL):
        classes.append("edge_case_over_or_under_count")
    if "Expected:" in chat_text and "Received:" in chat_text:
        classes.append("assertion_delta_available")
    return classes or ["unknown_miss"]


def _help_plan(language: str, task: str, classes: list[str], failure_lines: list[str]) -> dict[str, Any]:
    query_base = f"{language} {task.replace('_', ' ')} coding kata edge cases"
    queries = [
        query_base,
        f"Exercism {language} {task.replace('_', ' ')} tests solution approach",
    ]
    if "language_api_confusion" in classes:
        queries.append(f"{language} string length property versus method")
    if "edge_case_over_or_under_count" in classes:
        queries.append(f"{task.replace('_', ' ')} rectangle counting corner edge cases")
    if failure_lines:
        queries.append(f"{query_base} {failure_lines[0][:120]}")

    return {
        "call_for_help_when": [
            "same class fails after two attempts",
            "new attempt loses tests that previously passed",
            "failure lines include an API/runtime error that is not part of the algorithm",
            "edge-case counts disagree but syntax and basic tests pass",
        ],
        "allowed_help_sources": [
            "official language documentation",
            "benchmark/exercise README and tests",
            "public issue/discussion pages for the same error class",
            "web search snippets used only to form a repair hypothesis, not copied blindly",
        ],
        "web_search_queries": queries,
        "retry_prompt": (
            "Do not rewrite from scratch unless the current approach is structurally wrong. "
            "First preserve all passing tests, then explain the failing assertion, identify the invariant it violates, "
            "apply the smallest patch, and rerun the exact test command."
        ),
    }


def _retry_cycle(language: str, task: str, classes: list[str]) -> dict[str, Any]:
    task_label = f"{language}/{task}"
    return {
        "schema_version": "scbe_known_fail_retry_cycle_v1",
        "principle": (
            "A failure is a captured learning packet, not a final verdict. Consensus is advisory; "
            "working executable evidence is the gate."
        ),
        "stages": [
            {
                "id": "problem",
                "owner": "runner",
                "goal": "Freeze the exact failing task, model, attempt history, test output, and current code.",
                "done_when": "result JSON, chat history, failure classes, and 5W summary are present.",
            },
            {
                "id": "retry_with_knowledge",
                "owner": "coding_agent",
                "goal": (
                    "Retry from the captured miss, preserving tests that already passed and repairing only the "
                    "failing invariant."
                ),
                "done_when": "the exact benchmark task test command has been rerun after the smallest plausible patch.",
            },
            {
                "id": "multi_agent_research",
                "owner": "research_lanes",
                "goal": (
                    "Ask independent cheap/free helpers for source-backed clues: official docs, exercise tests, "
                    "language API rules, and common edge cases."
                ),
                "done_when": "at least two independent hypotheses are captured with source/search terms.",
            },
            {
                "id": "bigger_agent_confirmation",
                "owner": "confirmation_agent",
                "goal": (
                    "Use a stronger or slower model only after the cheap lanes produce a candidate repair. "
                    "The stronger model confirms invariants and regressions; it does not replace the test gate."
                ),
                "done_when": "candidate patch is checked against failure classes and prior passing tests.",
            },
            {
                "id": "workingness_gate",
                "owner": "harness",
                "goal": "Judge by executable workingness, not model agreement.",
                "done_when": "all task tests pass or the miss is recaptured as a new known-fail packet.",
            },
        ],
        "free_first_model_rotation": [
            "local small model: classify failure and extract exact failing invariant",
            "HF/free router model: propose minimal patch",
            "second cheap model: review for regression risk",
            "bigger model: confirm only after cheap lanes converge on a runnable candidate",
        ],
        "anti_consensus_rule": (
            f"For {task_label}, do not add more consensus variables. Require overlap on the main invariant, "
            "then let tests decide."
        ),
        "next_retry_prompt": (
            f"Known fail packet for {task_label}: classes={', '.join(classes)}. "
            "Use the tests and failure lines as the source of truth. Keep the passing behavior, patch the failing "
            "invariant, rerun the exact task tests, and return only: patch summary, test command, pass/fail, "
            "remaining known fails."
        ),
    }


def _completion_items(known_failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base = [
        {
            "id": "all_executable_tests_green",
            "question": "Did every executable benchmark/test command pass after the final edit?",
            "required_for_done": True,
        },
        {
            "id": "no_new_regressions",
            "question": "Did the retry preserve tests that were already passing?",
            "required_for_done": True,
        },
        {
            "id": "known_fails_captured",
            "question": "If anything failed, is each miss captured with task, model, failure class, and next retry?",
            "required_for_done": True,
        },
        {
            "id": "help_plan_attached",
            "question": "For hard misses, is there a help/search plan before the next retry?",
            "required_for_done": False,
        },
        {
            "id": "claim_scope_correct",
            "question": "Does the final claim distinguish harness success from coding benchmark success?",
            "required_for_done": True,
        },
    ]
    for item in base:
        if item["id"] in {"known_fails_captured", "help_plan_attached"}:
            item["status"] = "pass" if known_failures else "not_needed"
        elif item["id"] == "claim_scope_correct":
            item["status"] = "pass"
        else:
            item["status"] = "fail" if known_failures else "pass"
    return base


def _result_paths(artifact_root: Path) -> list[Path]:
    diagnostics_dir = artifact_root / "diagnostics"
    diagnostics_results = sorted(diagnostics_dir.glob("*.results.json")) if diagnostics_dir.exists() else []
    if diagnostics_results:
        return diagnostics_results
    return [
        path
        for path in sorted(artifact_root.rglob("*.results.json"))
        if path.name != ".aider.results.json" and "known_fail_retry_prompts" not in path.parts
    ]


def _recovered_after_retry(outcomes: Any, classes: list[str]) -> bool:
    return (
        isinstance(outcomes, list)
        and bool(outcomes)
        and any(item is False for item in outcomes)
        and outcomes[-1] is True
        and "retry_recovered" in classes
    )


def build_checklist(artifact_root: Path, output_root: Path) -> dict[str, Any]:
    latest_stats = _find_latest_stats(artifact_root)
    stats_text = _read_text(latest_stats) if latest_stats else ""
    stats = _extract_stats(stats_text)

    known_failures = []
    recovered_misses = []
    for result_path in _result_paths(artifact_root):
        result = _load_json(result_path)
        if not result:
            continue
        outcomes = result.get("tests_outcomes")
        failed = bool(isinstance(outcomes, list) and any(item is False for item in outcomes))
        failed = failed or any(
            result.get(key) for key in ("syntax_errors", "indentation_errors", "num_malformed_responses")
        )
        if not failed:
            continue
        stem = _diagnostic_stem(result_path)
        chat_path = result_path.with_name(stem + ".chat.history.md")
        chat_text = _read_text(chat_path)
        language = _language_from_stem(stem)
        task = _task_from_stem(stem)
        classes = _classify_failure(result, chat_text)
        failure_lines = _extract_failure_lines(chat_text)
        miss = {
            "id": stem,
            "task": task,
            "language": language,
            "model": result.get("model") or stats.get("model"),
            "edit_format": result.get("edit_format") or stats.get("edit_format"),
            "tests_outcomes": outcomes,
            "failure_classes": classes,
            "recovered": _recovered_after_retry(outcomes, classes),
            "evidence": {
                "result_json": str(result_path),
                "chat_history": str(chat_path) if chat_path.exists() else None,
                "failure_lines": failure_lines,
            },
            "five_w": {
                "what": f"{language}/{task} did not pass the executable benchmark tests.",
                "where": str(result.get("testdir") or result_path.parent),
                "when": stats.get("date") or _utc_now(),
                "who": result.get("model") or stats.get("model") or "unknown model",
                "why": ", ".join(classes),
                "how_to_retry": "preserve passing tests, repair only the failing invariant, rerun the exact task tests",
            },
            "help_plan": _help_plan(language, task, classes, failure_lines),
            "retry_cycle": _retry_cycle(language, task, classes),
        }
        if miss["recovered"]:
            recovered_misses.append(miss)
        else:
            known_failures.append(miss)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "artifact_root": str(artifact_root),
        "latest_stats": str(latest_stats) if latest_stats else None,
        "stats": stats,
        "known_failure_count": len(known_failures),
        "known_failures": known_failures,
        "recovered_miss_count": len(recovered_misses),
        "recovered_misses": recovered_misses,
        "completion_status": "blocked_known_fails" if known_failures else "ready_to_claim_done",
        "completion_checklist": _completion_items(known_failures),
        "claim_guidance": (
            "Claim harness execution when the workflow completed. Claim benchmark task success only when "
            "known_failure_count is zero and all required checklist items pass. Recovered misses are learning "
            "packets, not blockers."
        ),
        "workingness_policy": {
            "consensus_role": "advisory_only",
            "success_gate": "executable_tests_and_artifact_evidence",
            "failure_role": "learning_packet_for_retry",
            "retry_shape": "problem + retry_with_knowledge + multi_agent_research + bigger_agent_confirmation",
        },
    }

    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "latest_completion_checklist.json"
    md_path = output_root / "latest_completion_checklist.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {"payload": payload, "json": str(json_path), "markdown": str(md_path)}


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Workflow Completion Checklist",
        "",
        f"Generated: `{payload['created_at']}`",
        f"Status: `{payload['completion_status']}`",
        f"Known failures: `{payload['known_failure_count']}`",
        f"Recovered misses: `{payload.get('recovered_miss_count', 0)}`",
        "",
        "## Required Checks",
        "",
    ]
    for item in payload["completion_checklist"]:
        lines.append(f"- `{item['status']}` {item['id']}: {item['question']}")
    lines.extend(["", "## Known Fails", ""])
    if not payload["known_failures"]:
        lines.append("- None")
    for failure in payload["known_failures"]:
        lines.extend(
            [
                f"### {failure['id']}",
                "",
                f"- task: `{failure['language']}/{failure['task']}`",
                f"- model: `{failure['model']}`",
                f"- classes: `{', '.join(failure['failure_classes'])}`",
                f"- outcomes: `{failure['tests_outcomes']}`",
                f"- result: `{failure['evidence']['result_json']}`",
                f"- chat: `{failure['evidence']['chat_history']}`",
                "",
                "5W:",
            ]
        )
        for key, value in failure["five_w"].items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "Evidence lines:"])
        if failure["evidence"]["failure_lines"]:
            lines.extend(f"- {line}" for line in failure["evidence"]["failure_lines"][:8])
        else:
            lines.append("- No focused failure lines captured; inspect result/chat artifacts.")
        lines.extend(["", "Help/search plan:"])
        lines.extend(f"- {item}" for item in failure["help_plan"]["call_for_help_when"])
        lines.append("")
        lines.append("Suggested web searches:")
        lines.extend(f"- `{query}`" for query in failure["help_plan"]["web_search_queries"])
        lines.append("")
        lines.append(f"Retry prompt: {failure['help_plan']['retry_prompt']}")
        lines.extend(["", "Retry cycle:"])
        for stage in failure["retry_cycle"]["stages"]:
            lines.append(f"- `{stage['id']}` ({stage['owner']}): {stage['goal']} Done when: {stage['done_when']}")
        lines.extend(["", "Free-first model rotation:"])
        lines.extend(f"- {item}" for item in failure["retry_cycle"]["free_first_model_rotation"])
        lines.append("")
        lines.append(f"Anti-consensus rule: {failure['retry_cycle']['anti_consensus_rule']}")
        lines.append("")
        lines.append(f"Next retry prompt: {failure['retry_cycle']['next_retry_prompt']}")
        lines.append("")
    lines.extend(["## Recovered Misses", ""])
    if not payload.get("recovered_misses"):
        lines.append("- None")
    for failure in payload.get("recovered_misses", []):
        lines.extend(
            [
                f"### {failure['id']}",
                "",
                f"- task: `{failure['language']}/{failure['task']}`",
                f"- model: `{failure['model']}`",
                f"- classes: `{', '.join(failure['failure_classes'])}`",
                f"- outcomes: `{failure['tests_outcomes']}`",
                f"- result: `{failure['evidence']['result_json']}`",
                "",
                "This miss recovered inside the run. Keep it as training signal and avoid blocking completion.",
                "",
            ]
        )
    lines.extend(["## Claim Guidance", "", payload["claim_guidance"], ""])
    lines.extend(
        [
            "## Workingness Policy",
            "",
            f"- consensus role: `{payload['workingness_policy']['consensus_role']}`",
            f"- success gate: `{payload['workingness_policy']['success_gate']}`",
            f"- failure role: `{payload['workingness_policy']['failure_role']}`",
            f"- retry shape: `{payload['workingness_policy']['retry_shape']}`",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--fail-on-known-fails",
        action="store_true",
        help="Exit non-zero when known failures are captured. Keep off in CI artifact lanes.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_checklist(args.artifact_root, args.output_root)
    payload = report["payload"]
    print(
        json.dumps(
            {
                "completion_status": payload["completion_status"],
                "known_failure_count": payload["known_failure_count"],
                "json": report["json"],
                "markdown": report["markdown"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    if args.fail_on_known_fails and payload["known_failure_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
