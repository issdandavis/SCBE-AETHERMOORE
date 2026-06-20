#!/usr/bin/env python3
"""Compile known-fail checklist packets into bounded retry prompts.

The completion checklist decides whether a workflow can claim done. This script
turns any captured miss into a concrete next-attempt prompt that can be handed
to a cheap local/cloud model, a stronger confirmation model, or a human.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "scbe_known_fail_retry_prompt_bundle_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    return slug[:120] or "known-fail"


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_lines(values: list[Any], *, prefix: str = "- ") -> list[str]:
    lines = []
    for value in values:
        if isinstance(value, str) and value.strip():
            lines.append(f"{prefix}{value.strip()}")
    return lines


def _stage_summary(retry_cycle: dict[str, Any]) -> list[str]:
    lines = []
    for stage in _as_list(retry_cycle.get("stages")):
        if not isinstance(stage, dict):
            continue
        stage_id = str(stage.get("id") or "stage")
        goal = str(stage.get("goal") or "").strip()
        done_when = str(stage.get("done_when") or "").strip()
        line = f"- {stage_id}: {goal}"
        if done_when:
            line += f" Done when: {done_when}"
        lines.append(line)
    return lines


def _build_prompt(failure: dict[str, Any], policy: dict[str, Any]) -> str:
    failure_id = str(failure.get("id") or failure.get("task") or "known-fail")
    language = str(failure.get("language") or "unknown")
    task = str(failure.get("task") or "unknown")
    model = str(failure.get("model") or "unknown")
    edit_format = str(failure.get("edit_format") or "unknown")
    classes = [str(item) for item in _as_list(failure.get("failure_classes"))]
    evidence = failure.get("evidence") if isinstance(failure.get("evidence"), dict) else {}
    five_w = failure.get("five_w") if isinstance(failure.get("five_w"), dict) else {}
    help_plan = failure.get("help_plan") if isinstance(failure.get("help_plan"), dict) else {}
    retry_cycle = failure.get("retry_cycle") if isinstance(failure.get("retry_cycle"), dict) else {}
    retry_shape_default = "problem + retry_with_knowledge + multi_agent_research + bigger_agent_confirmation"

    lines = [
        "# SCBE Known-Fail Retry Prompt",
        "",
        "You are repairing one captured benchmark miss. Failure is a learning packet, not a final verdict.",
        "Do not chase model consensus. Multiple agents may disagree; preserve the overlapping "
        "working core and let executable tests decide.",
        "",
        "## Workingness Policy",
        f"- consensus role: {policy.get('consensus_role', 'advisory_only')}",
        f"- success gate: {policy.get('success_gate', 'executable_tests_and_artifact_evidence')}",
        f"- failure role: {policy.get('failure_role', 'learning_packet_for_retry')}",
        f"- retry shape: {policy.get('retry_shape', retry_shape_default)}",
        "",
        "## Frozen Problem",
        f"- id: {failure_id}",
        f"- task: {language}/{task}",
        f"- previous model: {model}",
        f"- edit format: {edit_format}",
        f"- failure classes: {', '.join(classes) if classes else 'unknown_miss'}",
        "",
        "## 5W Summary",
    ]
    for key in ("what", "where", "when", "who", "why", "how_to_retry"):
        value = five_w.get(key)
        if value:
            lines.append(f"- {key}: {value}")

    failure_lines = _as_list(evidence.get("failure_lines"))
    if failure_lines:
        lines.extend(["", "## Failure Evidence"])
        lines.extend(_string_lines([str(item)[:500] for item in failure_lines[:12]]))

    queries = _as_list(help_plan.get("web_search_queries"))
    if queries:
        lines.extend(["", "## Allowed Research Queries"])
        lines.extend(_string_lines([str(item) for item in queries[:8]]))

    allowed_sources = _as_list(help_plan.get("allowed_help_sources"))
    if allowed_sources:
        lines.extend(["", "## Allowed Help Sources"])
        lines.extend(_string_lines([str(item) for item in allowed_sources]))

    stage_lines = _stage_summary(retry_cycle)
    if stage_lines:
        lines.extend(["", "## Retry Cycle"])
        lines.extend(stage_lines)

    rotation = _as_list(retry_cycle.get("free_first_model_rotation"))
    if rotation:
        lines.extend(["", "## Free-First Model Rotation"])
        lines.extend(_string_lines([str(item) for item in rotation]))

    next_prompt = str(retry_cycle.get("next_retry_prompt") or help_plan.get("retry_prompt") or "").strip()
    if next_prompt:
        lines.extend(["", "## Required Repair Behavior", next_prompt])

    lines.extend(
        [
            "",
            "## Output Contract",
            "Return only:",
            "1. failure_invariant: the exact invariant the previous attempt violated.",
            "2. preserve_list: tests/behaviors that were already working and must not regress.",
            "3. minimal_patch_plan: the smallest patch that should fix the invariant.",
            "4. verification_command: the exact command or benchmark rerun needed.",
            "5. confidence_note: what still might be wrong after the patch.",
            "",
            "Stop if you cannot identify a runnable verification path. Ask for a local evidence "
            "lane instead of inventing facts.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def build_retry_prompt_bundle(checklist_path: Path, output_root: Path) -> dict[str, Any]:
    checklist = _load_json(checklist_path)
    payload = checklist.get("payload") if isinstance(checklist.get("payload"), dict) else checklist
    known_failures = [item for item in _as_list(payload.get("known_failures")) if isinstance(item, dict)]
    policy = payload.get("workingness_policy") if isinstance(payload.get("workingness_policy"), dict) else {}

    prompts_dir = output_root / "known_fail_retry_prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    prompt_records = []
    for index, failure in enumerate(known_failures, start=1):
        failure_id = str(failure.get("id") or failure.get("task") or f"known_fail_{index}")
        path = prompts_dir / f"{index:02d}-{_safe_slug(failure_id)}.md"
        prompt = _build_prompt(failure, policy)
        path.write_text(prompt, encoding="utf-8")
        prompt_records.append(
            {
                "id": failure_id,
                "task": failure.get("task"),
                "language": failure.get("language"),
                "failure_classes": failure.get("failure_classes", []),
                "prompt_path": str(path),
            }
        )

    bundle = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_checklist": str(checklist_path),
        "known_failure_count": len(known_failures),
        "prompt_count": len(prompt_records),
        "status": "prompts_ready" if prompt_records else "no_known_fails",
        "workingness_policy": policy,
        "prompts": prompt_records,
    }
    bundle_path = output_root / "latest_known_fail_retry_prompts.json"
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md_path = output_root / "latest_known_fail_retry_prompts.md"
    lines = [
        "# Known-Fail Retry Prompts",
        "",
        f"Generated: `{bundle['generated_at']}`",
        f"Status: `{bundle['status']}`",
        f"Known failures: `{bundle['known_failure_count']}`",
        "",
    ]
    if not prompt_records:
        lines.append("No known failures were present, so no retry prompts were generated.")
    else:
        lines.append("## Prompt Files")
        for record in prompt_records:
            classes = ", ".join(str(item) for item in _as_list(record.get("failure_classes"))) or "unknown_miss"
            lines.append(
                f"- `{record['id']}` ({record.get('language')}/{record.get('task')}): `{record['prompt_path']}`"
            )
            lines.append(f"  - failure classes: `{classes}`")
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    bundle["bundle_path"] = str(bundle_path)
    bundle["markdown_path"] = str(md_path)
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checklist",
        type=Path,
        required=True,
        help="Path to latest_completion_checklist.json.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="Directory where prompt bundle artifacts should be written.",
    )
    args = parser.parse_args()

    bundle = build_retry_prompt_bundle(checklist_path=args.checklist, output_root=args.output_root)
    print(
        json.dumps(
            {
                "status": bundle["status"],
                "known_failure_count": bundle["known_failure_count"],
                "prompt_count": bundle["prompt_count"],
                "bundle_path": bundle["bundle_path"],
                "markdown_path": bundle["markdown_path"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
