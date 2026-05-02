#!/usr/bin/env python3
"""Generate ambiguity-to-action SFT records for SCBE coding agents.

The target behavior is practical: convert messy user commands into repo-grounded
actions, ask for clarity only at defined gates, and delegate small tasks through
compact handoff packets. The scenarios intentionally include realistic user
behaviors such as vague commands, context bloat, mid-task corrections, and
mini-skill composition.

Output: training-data/agentic_coding/ambiguity_action_traces.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent_comms import AgentPacketV1, Budget, ContextRef, Route, hash_state  # noqa: E402
from src.agent_comms.secure_handoff import seal_handoff, semantic_shadow  # noqa: E402


DEFAULT_OUTPUT = PROJECT_ROOT / "training-data" / "agentic_coding" / "ambiguity_action_traces.jsonl"
GENERATOR_NAME = "generate_ambiguity_action_sft.py"
GENERATOR_VERSION = "1"
TRAINING_SECRET = "training-only-shared-secret"
PINNED_CREATED_AT = 0.0
PINNED_NONCE = b"ambiguity-trace!"  # 16 bytes


@dataclass(frozen=True)
class MiniSkill:
    skill_id: str
    trigger: str
    action: str
    improves: list[str]
    load_cost: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    user_command: str
    simulated_repo: dict[str, Any]
    ambiguity: list[str]
    clarity_gate: dict[str, Any]
    inferred_purpose: str
    grounded_actions: list[str]
    subagent_tasks: list[dict[str, Any]]
    mini_skills: list[MiniSkill]
    stressors: list[str]
    expected_behavior: str


def _mini_skills() -> dict[str, MiniSkill]:
    skills = [
        MiniSkill(
            skill_id="ask-once-at-risk-boundary",
            trigger="missing destructive scope, credentials, publish target, or irreversible action",
            action="ask one concise blocking question before acting",
            improves=["clarity_gate", "release_readiness", "safety_boundary"],
            load_cost=1,
        ),
        MiniSkill(
            skill_id="repo-first-grounding",
            trigger="user says vague command like fix it, improve it, ship it, make it work",
            action="search repo entrypoints and tests before proposing new surfaces",
            improves=["actionability", "token_savings", "anti_cargo_cult"],
            load_cost=1,
        ),
        MiniSkill(
            skill_id="context-bloat-triage",
            trigger="user dumps large files, logs, or old chat history mid-task",
            action="extract newest actionable request, summarize heavy context, preserve open gates",
            improves=["compaction_resilience", "task_continuity"],
            load_cost=1,
        ),
        MiniSkill(
            skill_id="small-packet-delegation",
            trigger="subtask can run independently with paths, command, success gate, and no broad repo context",
            action="emit sealed handoff shadow plus AgentPacketV1 task core",
            improves=["ai_to_ai_handoff", "token_savings", "auditability"],
            load_cost=1,
        ),
        MiniSkill(
            skill_id="release-board-cleaning",
            trigger="repo is dirty and user asks to ship",
            action="separate release files, generated artifacts, unrelated dirt, and tests evidence",
            improves=["release_readiness", "cleanup_skill"],
            load_cost=1,
        ),
        MiniSkill(
            skill_id="residual-temp-skill-propagation",
            trigger="a task needs a short-lived helper note, scratch schema, or focused adapter during execution",
            action="create temp artifact, use it, delete it, and retain only a residue manifest with trigger/action/hash/evidence",
            improves=["context_savings", "skill_evolution", "retrieval_hints", "workspace_hygiene"],
            load_cost=1,
        ),
    ]
    return {skill.skill_id: skill for skill in skills}


def _scenarios() -> list[Scenario]:
    skills = _mini_skills()
    return [
        Scenario(
            scenario_id="ambiguous_harness_upgrade",
            user_command="make the harness better than theirs and use the good parts",
            simulated_repo={
                "paths": [
                    "scripts/terminal/geoseal_harness_terminal.py",
                    "scripts/benchmark/harness_research_matrix.py",
                    "tests/terminal/test_geoseal_harness_terminal.py",
                ],
                "test_command": "python -m pytest tests/terminal/test_geoseal_harness_terminal.py tests/benchmark/test_harness_research_matrix.py -q",
            },
            ambiguity=["theirs", "better", "good parts"],
            clarity_gate={
                "ask_user": False,
                "reason": "repo has existing harness and benchmark matrix entrypoints; implement local readiness lanes first",
                "ask_if": ["publish target requested", "paid API spend required", "destructive cleanup requested"],
            },
            inferred_purpose="Improve GeoSeal harness using runnable benchmark/readiness lanes without copying external tool cargo-cult features.",
            grounded_actions=[
                "Inspect existing terminal harness and benchmark matrix.",
                "Add one local readiness lane per reusable benchmark lesson.",
                "Expose command through geoseal CLI.",
                "Run focused tests and report parity limits.",
            ],
            subagent_tasks=[
                {
                    "agent": "benchmark-reviewer",
                    "task": "Compare harness lanes to local test evidence and flag non-runnable claims.",
                    "paths": ["scripts/benchmark/harness_research_matrix.py"],
                    "success_gate": "all lanes include local_command and parity_claim",
                }
            ],
            mini_skills=[
                skills["repo-first-grounding"],
                skills["small-packet-delegation"],
            ],
            stressors=["ambiguous_comparison_target", "cargo_cult_risk"],
            expected_behavior="Act locally, add runnable gates, avoid fake leaderboard claims.",
        ),
        Scenario(
            scenario_id="context_bloat_after_working_state",
            user_command="here is the whole session log and old files, keep going from the newest part and dont lose the tests",
            simulated_repo={
                "paths": [
                    "training-data/agentic_coding/packet_traces.jsonl",
                    "tests/training/test_generate_packet_traces_sft.py",
                    "notes/sessions/2026-05-02-session.md",
                ],
                "test_command": "python -m pytest tests/training/test_generate_packet_traces_sft.py -q",
            },
            ambiguity=["newest part", "whole session log", "dont lose"],
            clarity_gate={
                "ask_user": False,
                "reason": "newest actionable request is explicit enough; summarize context and preserve current gates",
                "ask_if": ["multiple conflicting newest requests", "missing target file", "unrecoverable compaction gap"],
            },
            inferred_purpose="Recover task continuity after context bloat by extracting the newest actionable request and preserving validation evidence.",
            grounded_actions=[
                "Identify latest explicit request and affected files.",
                "Compress old context into a short handoff note.",
                "Continue from durable artifacts rather than replaying full chat.",
                "Rerun the focused test that proves the lane.",
            ],
            subagent_tasks=[
                {
                    "agent": "continuity-checker",
                    "task": "Read session note and changed training generator, then report newest actionable gate.",
                    "paths": ["notes/sessions/2026-05-02-session.md", "scripts/training/generate_packet_traces_sft.py"],
                    "success_gate": "returns one current task and one test command",
                }
            ],
            mini_skills=[
                skills["context-bloat-triage"],
                skills["small-packet-delegation"],
            ],
            stressors=["context_bloat", "bad_compaction_timing"],
            expected_behavior="Do not restart; compress context, preserve gates, and continue from disk.",
        ),
        Scenario(
            scenario_id="release_dirty_tree",
            user_command="ship the packages this weekend but clean the board between meat orders",
            simulated_repo={
                "paths": ["package.json", "bin/geoseal.cjs", "src/geoseal_cli.py", "training-data/manifests"],
                "test_command": "node ./bin/geoseal.cjs doctor --json",
            },
            ambiguity=["packages", "clean the board", "this weekend"],
            clarity_gate={
                "ask_user": True,
                "reason": "publishing packages is irreversible and may require tokens or account targets",
                "question": "Which package target should be published first: npm, PyPI, or both after review?",
                "ask_if": ["publish account/token missing", "version bump unclear", "dirty tree includes unrelated edits"],
            },
            inferred_purpose="Prepare release readiness by separating publishable code, generated artifacts, and unrelated dirty-tree work before package publication.",
            grounded_actions=[
                "Inventory package surfaces and dirty tree.",
                "Run package-local doctor/test gates.",
                "Create release candidate manifest.",
                "Ask before publishing to npm or PyPI.",
            ],
            subagent_tasks=[
                {
                    "agent": "release-auditor",
                    "task": "Classify dirty files into release, generated, unrelated, and blocked buckets.",
                    "paths": ["package.json", "pyproject.toml", "bin/geoseal.cjs"],
                    "success_gate": "produces release bucket table with tests",
                }
            ],
            mini_skills=[
                skills["ask-once-at-risk-boundary"],
                skills["release-board-cleaning"],
            ],
            stressors=["irreversible_publish", "dirty_tree", "time_pressure"],
            expected_behavior="Ask one blocking release-target question, then prepare without publishing blindly.",
        ),
        Scenario(
            scenario_id="mini_skill_compounds",
            user_command="make tiny skills that update other skills when the system shape changes",
            simulated_repo={
                "paths": [
                    ".codex/skills",
                    ".agents/skills",
                    "scripts/emit_codex_skill_sphere_index.py",
                    "scripts/system/refresh_universal_skill_synthesis.py",
                ],
                "test_command": "python scripts/emit_codex_skill_sphere_index.py --help",
            },
            ambiguity=["tiny skills", "system shape", "update other skills"],
            clarity_gate={
                "ask_user": False,
                "reason": "can build a training record and spec before mutating live skill folders",
                "ask_if": ["actual skill install path requested", "auto-update live skills requested"],
            },
            inferred_purpose="Train agents to propose small composable skill deltas that improve adjacent skills without loading or rewriting the entire skill graph.",
            grounded_actions=[
                "Represent each mini skill as trigger/action/improves/load_cost.",
                "Apply only when the trigger matches the current task.",
                "Prefer references or scripts over large SKILL.md growth.",
                "Validate with focused skill tests before updating live skills.",
            ],
            subagent_tasks=[
                {
                    "agent": "skill-delta-reviewer",
                    "task": "Check whether proposed mini skill overlaps existing skills or should remain a small patch.",
                    "paths": [".codex/skills", ".agents/skills"],
                    "success_gate": "returns merge, split, or reject with one reason",
                }
            ],
            mini_skills=[
                skills["repo-first-grounding"],
                skills["context-bloat-triage"],
                skills["release-board-cleaning"],
            ],
            stressors=["skill_sprawl", "context_budget_pressure"],
            expected_behavior="Keep skills small, relational, triggerable, and testable.",
        ),
        Scenario(
            scenario_id="residual_deletion_skill_trace",
            user_command=(
                "make a temp helper for this weird workflow, use it, attach the useful part to the right skill, "
                "then clean it up but leave a little residue so the system remembers the shape"
            ),
            simulated_repo={
                "paths": [
                    "artifacts/tmp/skill_residue/",
                    ".agents/skills",
                    "scripts/training/generate_ambiguity_action_sft.py",
                    "training-data/agentic_coding/ambiguity_action_traces.jsonl",
                ],
                "test_command": "python -m pytest tests/training/test_generate_ambiguity_action_sft.py -q",
            },
            ambiguity=["temp helper", "attach useful part", "little residue", "remembers"],
            clarity_gate={
                "ask_user": False,
                "reason": "safe if residue is a manifest only and live skill files are not auto-mutated",
                "ask_if": ["requested live skill edit", "residue contains secrets", "temp artifact cannot be safely deleted"],
            },
            inferred_purpose=(
                "Use short-lived task artifacts to discover useful behavior, then delete bulky scratch files while "
                "retaining a compact residue record for retrieval, evaluation, and later training."
            ),
            grounded_actions=[
                "Create a temp artifact under a generated/tmp path.",
                "Use it for the immediate task only.",
                "Extract trigger/action/evidence/hash into a residue manifest.",
                "Delete the bulky temp artifact.",
                "Do not claim model weights changed until residue is indexed or trained.",
            ],
            subagent_tasks=[
                {
                    "agent": "residue-auditor",
                    "task": "Validate that temp artifacts can be deleted and the residue manifest preserves only safe retrieval hints.",
                    "paths": ["artifacts/tmp/skill_residue/", "training-data/agentic_coding/ambiguity_action_traces.jsonl"],
                    "success_gate": "residue has no secrets, has source hash, and points to one improvement target",
                }
            ],
            mini_skills=[
                skills["residual-temp-skill-propagation"],
                skills["context-bloat-triage"],
                skills["release-board-cleaning"],
            ],
            stressors=["temp_file_sprawl", "false_weight_update_claim", "skill_auto_mutation_risk"],
            expected_behavior="Leave a compact residue manifest, not durable scratch junk or unreviewed live skill edits.",
        ),
    ]


def _packet_for_task(scenario: Scenario, task: dict[str, Any], index: int) -> AgentPacketV1:
    refs = [ContextRef(kind="path", value=path, bytes=4096) for path in task.get("paths", [])]
    return AgentPacketV1(
        task_id=f"{scenario.scenario_id}-subtask-{index}",
        phase="plan",
        route=Route(tongue="KO", domain="agentic-training", permission="read"),
        context_refs=refs,
        state_hash=hash_state(scenario.scenario_id, task["agent"], task["task"]),
        budget=Budget(max_input_tokens=1024, max_output_tokens=256),
        request=task["task"],
        expected_output="verdict",
        created_at=PINNED_CREATED_AT,
    )


def _delegation_records(scenario: Scenario) -> list[dict[str, Any]]:
    records = []
    for index, task in enumerate(scenario.subagent_tasks):
        packet = _packet_for_task(scenario, task, index)
        sealed = seal_handoff(
            packet,
            sender_id="main-agent",
            recipient_id=task["agent"],
            shared_secret=TRAINING_SECRET,
            nonce=PINNED_NONCE,
            created_at=PINNED_CREATED_AT,
        )
        records.append(
            {
                "agent": task["agent"],
                "success_gate": task["success_gate"],
                "packet_shadow": semantic_shadow(packet),
                "decode_agreement": sealed["decode_agreement"],
                "sealed_handoff_commitment": sealed["shadow"]["body_commitment"],
                "compactness": sealed["compactness"],
            }
        )
    return records


def _residual_lifecycle(scenario: Scenario) -> dict[str, Any]:
    """Describe temp-file use/deletion residue without mutating the workspace."""

    residue_id = f"residue-{scenario.scenario_id}"
    scratch_path = f"artifacts/tmp/skill_residue/{scenario.scenario_id}.scratch.md"
    residue_path = f"artifacts/tmp/skill_residue/{scenario.scenario_id}.residue.json"
    residue_source = {
        "scenario_id": scenario.scenario_id,
        "user_command": scenario.user_command,
        "stressors": scenario.stressors,
        "mini_skill_ids": [skill.skill_id for skill in scenario.mini_skills],
        "target_paths": scenario.simulated_repo["paths"],
    }
    return {
        "schema_version": "residual_temp_skill_lifecycle_v1",
        "residue_id": residue_id,
        "temp_artifact": {
            "path": scratch_path,
            "status": "delete_after_use",
            "allowed_contents": ["task-local notes", "scratch schema", "adapter sketch"],
            "forbidden_contents": ["secrets", "raw .env", "large copied source", "unreviewed model output"],
        },
        "residue_manifest": {
            "path": residue_path,
            "status": "retain_if_safe",
            "retained_fraction_goal": 0.03,
            "source_commitment": f"sha256:{hash_state(json.dumps(residue_source, sort_keys=True))}",
            "fields": [
                "trigger",
                "action",
                "improves",
                "evidence",
                "source_hash",
                "target_skill_hint",
            ],
        },
        "weight_space_note": (
            "Deleting the temp file does not update model weights. The residue can influence future behavior only "
            "through retrieval/indexing, eval feedback, or a later training pass."
        ),
    }


def _response_for_scenario(scenario: Scenario) -> dict[str, Any]:
    return {
        "schema_version": "ambiguity_action_trace_v1",
        "scenario_id": scenario.scenario_id,
        "simulation_only": True,
        "inferred_purpose": scenario.inferred_purpose,
        "repo_grounding": scenario.simulated_repo,
        "ambiguity_detected": scenario.ambiguity,
        "clarity_gate": scenario.clarity_gate,
        "main_agent_role": {
            "does": ["interpret", "plan", "issue compact task packets", "record gates"],
            "does_not": ["dump full context to every subagent", "invent repo surfaces", "ask clarification for every ambiguity"],
        },
        "grounded_actions": scenario.grounded_actions,
        "delegation": _delegation_records(scenario),
        "mini_skills": [skill.to_dict() for skill in scenario.mini_skills],
        "residual_lifecycle": _residual_lifecycle(scenario),
        "stressors": scenario.stressors,
        "expected_behavior": scenario.expected_behavior,
    }


def _instruction_for_scenario(scenario: Scenario) -> str:
    return (
        "Convert the ambiguous user command into a repo-grounded action trace. "
        "Ask for clarity only if the clarity gate requires it. Emit JSON only.\n\n"
        f"User command: {scenario.user_command}\n"
        f"Simulated repo: {json.dumps(scenario.simulated_repo, sort_keys=True)}"
    )


def generate_pairs() -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for scenario in _scenarios():
        response = _response_for_scenario(scenario)
        pairs.append(
            {
                "id": f"ambiguity-action-{scenario.scenario_id}",
                "category": "ambiguity-to-action-trace",
                "instruction": _instruction_for_scenario(scenario),
                "response": json.dumps(response, indent=2, sort_keys=True),
                "metadata": {
                    "source": "scbe_ambiguity_action_simulator_v1",
                    "generator": GENERATOR_NAME,
                    "version": GENERATOR_VERSION,
                    "scenario_id": scenario.scenario_id,
                    "stressors": scenario.stressors,
                    "mini_skill_ids": [skill.skill_id for skill in scenario.mini_skills],
                    "asks_clarity": bool(scenario.clarity_gate.get("ask_user")),
                },
            }
        )
    return pairs


def write_jsonl(pairs: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as f:
        for pair in pairs:
            f.write(json.dumps(pair, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json", action="store_true", help="Print summary as JSON")
    args = parser.parse_args(argv)
    pairs = generate_pairs()
    write_jsonl(pairs, args.output)
    summary = {
        "ok": True,
        "schema_version": "ambiguity_action_generator_summary_v1",
        "pairs": len(pairs),
        "output": str(args.output),
        "categories": sorted({pair["category"] for pair in pairs}),
        "clarity_ask_records": sum(1 for pair in pairs if pair["metadata"]["asks_clarity"]),
    }
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"Wrote {summary['pairs']} ambiguity-action pairs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
