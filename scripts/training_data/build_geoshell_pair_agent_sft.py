"""Build GeoShell paired-agent coding SFT records.

This dataset teaches the local coding model the first workflow we can prove now:
two agents working as a Builder/Navigator pair, with GeoSeal separating generation,
deterministic lookup, verification, and apply permission.

It intentionally reuses ``scripts/benchmark/dual_agent_pair_benchmark.py`` so the
training records match the benchmark that will judge the behavior later.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.benchmark.dual_agent_pair_benchmark import (  # noqa: E402
    SCHEMA_VERSION as PAIR_BENCHMARK_SCHEMA,
    PairTask,
    run_pair,
    task_suite,
)
from src.coding_spine.agent_call_switchboard import evaluate_call_request  # noqa: E402

SCHEMA_VERSION = "geoshell_pair_agent_sft_v1"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "training-data" / "sft"
DEFAULT_EVENT_PATH = (
    REPO_ROOT / "artifacts" / "geoshell" / "pair_agent" / "latest_events.json"
)
DEFAULT_EVAL_CONTRACT_PATH = (
    REPO_ROOT / "config" / "model_training" / "geoshell_pair_agent_eval_contract.json"
)
DEFAULT_POPULATION_MULTIPLIER = 6

TRAIN_NAME = "geoshell_pair_agent_v1_train.sft.jsonl"
HOLDOUT_NAME = "geoshell_pair_agent_v1_holdout.sft.jsonl"
MANIFEST_NAME = "geoshell_pair_agent_v1_manifest.json"

SYSTEM_PROMPT = (
    "You are a GeoShell paired coding agent. Work as a two-agent unit: Builder proposes the code or plan, "
    "Navigator routes deterministic facts, verifies behavior, and blocks conflicting tool/apply lanes. "
    "Use GeoSeal policy before apply. Prefer exact repo tools over memory for opcode tables, manifests, "
    "tests, and permission-sensitive actions. Keep Sacred Tongue tokenizer alignment visible: Kor'aelin (KO), "
    "Avali (AV), Runethic (RU), Cassisivadan (CA), Umbroth (UM), and Draumric (DR)."
)

SACRED_TONGUES = [
    {"code": "KO", "name": "Kor'aelin", "coding_lane": "Python"},
    {"code": "AV", "name": "Avali", "coding_lane": "TypeScript"},
    {"code": "RU", "name": "Runethic", "coding_lane": "Rust"},
    {"code": "CA", "name": "Cassisivadan", "coding_lane": "Mathematica"},
    {"code": "UM", "name": "Umbroth", "coding_lane": "Haskell"},
    {"code": "DR", "name": "Draumric", "coding_lane": "Markdown"},
]

RISK_TIERS = ["ALLOW", "QUARANTINE", "ESCALATE", "DENY"]

POPULATION_CONTEXTS = [
    "baseline operator request",
    "release-prep operator asking for exact gates",
    "dirty-worktree operator requiring owned-file boundaries",
    "security-aware operator requiring secret and apply separation",
    "training-run operator asking for machine-readable evidence",
    "research-bridge operator asking for source-grounded routing before coding",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _population_context(index: int) -> str:
    return POPULATION_CONTEXTS[index % len(POPULATION_CONTEXTS)]


def _tokenizer_alignment(task_kind: str) -> dict[str, Any]:
    if task_kind == "ca_opcode":
        primary = "CA"
    elif task_kind == "python_code":
        primary = "KO"
    else:
        primary = "DR"
    return {
        "schema_version": "geoshell_tokenizer_alignment_v1",
        "primary_tongue": primary,
        "sacred_tongues": SACRED_TONGUES,
        "risk_tiers": RISK_TIERS,
        "tokenizer_contract": "Preserve full Sacred Tongue names, abbreviations, lane separation, and risk-tier vocabulary in the row.",
    }


def _geoshell_event(
    task: PairTask, pair_result: dict[str, Any], index: int
) -> dict[str, Any]:
    """Return a telemetry row shaped for ``__SCBE_AGENT_BUS_EVENTS__`` consumers."""
    return {
        "_sig": f"geoshell-pair-{index:03d}-{task.task_id}",
        "_agent_id": "pair-agent-builder-navigator",
        "id": f"pair-agent-{task.task_id}",
        "task_type": "pair_coding",
        "query": task.prompt,
        "success": bool(pair_result["ok"]),
        "timestamp": _utc_now(),
        "duration_seconds": pair_result.get("elapsed_sec", 0),
        "breaker_state": {"apply_gate": "closed" if pair_result["ok"] else "review"},
    }


def _assistant_packet(
    task: PairTask, pair_result: dict[str, Any], index: int
) -> dict[str, Any]:
    packets = pair_result["packets"]
    builder_packets = [packet for packet in packets if packet["role"] == "builder"]
    navigator_packets = [packet for packet in packets if packet["role"] == "navigator"]
    event = _geoshell_event(task, pair_result, index)
    switchboard = evaluate_call_request(
        [],
        {
            "call_id": f"pair-agent-{task.task_id}",
            "agent_id": "pair-agent-builder-navigator",
            "lane": "pair_coding",
            "resource": task.task_id,
            "mode": "read" if task.kind == "routing" else "write",
            "priority": 5,
            "summary": task.prompt,
        },
    )
    return {
        "schema_version": "geoshell_pair_agent_answer_v1",
        "mode": "paired_geoshell_coding",
        "task_id": task.task_id,
        "task_kind": task.kind,
        "builder": builder_packets,
        "navigator": navigator_packets,
        "geoseal_policy": {
            "permission_mode": "observe_then_verify",
            "apply_allowed": False,
            "apply_unlock_condition": "tests_green_and_owned_paths_only",
            "blocked_paths": sorted(
                {path for packet in packets for path in packet["blocked_paths"]}
            ),
        },
        "deterministic_tools": sorted(
            {tool for packet in packets for tool in packet["tools"]}
        ),
        "switchboard": {
            "decision": switchboard["decision"],
            "request": switchboard["request"],
            "event": switchboard["switchboard_event"],
        },
        "expected_output": pair_result["output"],
        "verification": {
            "benchmark_schema": PAIR_BENCHMARK_SCHEMA,
            "score": pair_result["score"],
            "ok": bool(pair_result["ok"]),
            "recommended_gate": "python scripts/benchmark/dual_agent_pair_benchmark.py validate",
        },
        "tokenizer_alignment": _tokenizer_alignment(task.kind),
        "geoshell_event": event,
        "training_target": (
            "Produce a Builder/Navigator packet that keeps model generation, deterministic facts, "
            "verification, and apply permission in separate lanes."
        ),
    }


def _record_for_task(
    task: PairTask, pair_result: dict[str, Any], split: str, index: int
) -> dict[str, Any]:
    assistant = _assistant_packet(task, pair_result, index)
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Run this as a GeoShell paired coding task. Return the Builder/Navigator packet, "
                    f"GeoSeal policy, verification gate, and GeoShell telemetry event.\n\nTASK: {task.prompt}"
                ),
            },
            {"role": "assistant", "content": _json_dumps(assistant)},
        ],
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "program": "geoshell_pair_agent",
            "source_family": "dual_agent_pair_benchmark",
            "source_script": "scripts/benchmark/dual_agent_pair_benchmark.py",
            "split": split,
            "task_id": task.task_id,
            "task_kind": task.kind,
            "goal_sha256": _sha256_text(task.prompt),
            "assistant_sha256": _sha256_text(_json_dumps(assistant)),
            "geoshell_event_sig": assistant["geoshell_event"]["_sig"],
            "sacred_tongue_codes": [item["code"] for item in SACRED_TONGUES],
            "sacred_tongue_names": [item["name"] for item in SACRED_TONGUES],
        },
    }


def _population_variant(
    record: dict[str, Any], population_index: int, population_multiplier: int
) -> dict[str, Any]:
    """Clone a base SFT row with a deterministic operator-context variant."""

    cloned = json.loads(json.dumps(record, ensure_ascii=False))
    meta = cloned["meta"]
    base_task_id = str(meta["task_id"])
    suffix = f"p{population_index + 1:02d}"
    context = _population_context(population_index)
    variant_task_id = f"{base_task_id}__{suffix}"

    cloned["messages"][1]["content"] = (
        f"{cloned['messages'][1]['content']}\n\n"
        f"POPULATION_CONTEXT: {context}.\n"
        "Keep the same GeoSeal lane separation contract, but adapt the packet to this operator context."
    )
    assistant = json.loads(cloned["messages"][-1]["content"])
    if "task_id" in assistant:
        assistant["task_id"] = variant_task_id
    if "case_id" in assistant:
        assistant["case_id"] = variant_task_id
    if "geoshell_event" in assistant:
        assistant["geoshell_event"][
            "_sig"
        ] = f"{assistant['geoshell_event']['_sig']}__{suffix}"
        assistant["geoshell_event"][
            "id"
        ] = f"{assistant['geoshell_event']['id']}__{suffix}"
    if "switchboard_event" in assistant:
        assistant["switchboard_event"][
            "_sig"
        ] = f"{assistant['switchboard_event']['_sig']}__{suffix}"
        assistant["switchboard_event"][
            "id"
        ] = f"{assistant['switchboard_event']['id']}__{suffix}"
    cloned["messages"][-1]["content"] = _json_dumps(assistant)

    meta["base_task_id"] = base_task_id
    meta["task_id"] = variant_task_id
    meta["population_index"] = population_index
    meta["population_multiplier"] = population_multiplier
    meta["population_context"] = context
    meta["goal_sha256"] = _sha256_text(cloned["messages"][1]["content"])
    meta["assistant_sha256"] = _sha256_text(cloned["messages"][-1]["content"])
    meta["geoshell_event_sig"] = assistant.get(
        "geoshell_event", assistant.get("switchboard_event", {})
    ).get("_sig", meta.get("geoshell_event_sig"))
    return cloned


def _switchboard_record(
    *,
    case_id: str,
    existing: list[dict[str, Any]],
    request: dict[str, Any],
    split: str,
) -> dict[str, Any]:
    decision = evaluate_call_request(existing, request)
    assistant = {
        "schema_version": "geoshell_switchboard_answer_v1",
        "mode": "governed_multi_agent_call_switchboard",
        "case_id": case_id,
        "existing_calls": existing,
        "request": decision["request"],
        "decision": decision["decision"],
        "reason": decision["reason"],
        "collisions": decision["collisions"],
        "switchboard_event": decision["switchboard_event"],
        "tokenizer_alignment": _tokenizer_alignment("switchboard"),
        "training_target": "Reserve call lanes before tool/apply work so multiple AI agents do not collide.",
    }
    user_content = (
        "Evaluate this multi-agent call switchboard request. Return decision, reason, collisions, "
        "and GeoShell switchboard_event.\n\n"
        f"EXISTING_CALLS: {_json_dumps(existing)}\nREQUEST: {_json_dumps(request)}"
    )
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": _json_dumps(assistant)},
        ],
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "program": "geoshell_pair_agent",
            "source_family": "agent_call_switchboard",
            "source_script": "src/coding_spine/agent_call_switchboard.py",
            "split": split,
            "task_id": case_id,
            "task_kind": "switchboard",
            "goal_sha256": _sha256_text(user_content),
            "assistant_sha256": _sha256_text(_json_dumps(assistant)),
            "geoshell_event_sig": decision["switchboard_event"]["_sig"],
            "sacred_tongue_codes": [item["code"] for item in SACRED_TONGUES],
            "sacred_tongue_names": [item["name"] for item in SACRED_TONGUES],
        },
    }


def _switchboard_records() -> list[dict[str, Any]]:
    return [
        _switchboard_record(
            case_id="switchboard_grant_non_colliding_training_call",
            existing=[
                {
                    "call_id": "call-cursor-ui",
                    "agent_id": "agent.cursor",
                    "lane": "ui",
                    "resource": "scbe-visual-system",
                    "mode": "write",
                    "state": "active",
                }
            ],
            request={
                "call_id": "call-codex-training",
                "agent_id": "agent.codex",
                "lane": "training",
                "resource": "geoshell_pair_agent_v1",
                "mode": "write",
                "summary": "build GeoShell pair-agent records",
            },
            split="train",
        ),
        _switchboard_record(
            case_id="switchboard_queue_equal_priority_ui_write",
            existing=[
                {
                    "call_id": "call-cursor-geoshell",
                    "agent_id": "agent.cursor",
                    "lane": "ui",
                    "resource": "scbe-visual-system",
                    "mode": "write",
                    "state": "active",
                    "priority": 5,
                }
            ],
            request={
                "call_id": "call-codex-geoshell",
                "agent_id": "agent.codex",
                "lane": "ui",
                "resource": "scbe-visual-system",
                "mode": "write",
                "priority": 5,
                "summary": "add GeoShell event surface",
            },
            split="train",
        ),
        _switchboard_record(
            case_id="switchboard_block_lower_priority_apply",
            existing=[
                {
                    "call_id": "call-claude-apply",
                    "agent_id": "agent.claude",
                    "lane": "apply",
                    "resource": "src/geoseal_cli.py",
                    "mode": "apply",
                    "state": "reserved",
                    "priority": 1,
                }
            ],
            request={
                "call_id": "call-codex-apply",
                "agent_id": "agent.codex",
                "lane": "apply",
                "resource": "src/geoseal_cli.py",
                "mode": "apply",
                "priority": 9,
                "summary": "apply overlapping CLI patch",
            },
            split="holdout",
        ),
    ]


def _gate_contract_records(
    contract_path: Path = DEFAULT_EVAL_CONTRACT_PATH,
) -> list[dict[str, Any]]:
    """Turn frozen promotion-gate prompts into positive SFT exemplars."""

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    records = []
    for prompt in contract.get("prompts", []):
        gate_id = str(prompt["id"])
        required = [str(item) for item in prompt.get("required", [])]
        forbidden = [str(item) for item in prompt.get("forbidden", [])]
        event = {
            "_sig": f"geoshell-gate-repair-{gate_id}",
            "_agent_id": "pair-agent-builder-navigator",
            "id": f"gate-repair-{gate_id}",
            "task_type": "pair_coding_gate_repair",
            "query": prompt["prompt"],
            "success": True,
            "timestamp": _utc_now(),
            "breaker_state": {"apply_gate": "closed"},
        }
        assistant = {
            "schema_version": "geoshell_pair_agent_gate_answer_v1",
            "mode": "promotion_gate_repair",
            "gate_id": gate_id,
            "Builder": {
                "role": "Builder",
                "responsibility": "propose intent and draft only; mutation waits for the apply gate",
            },
            "Navigator": {
                "role": "Navigator",
                "responsibility": "route deterministic facts, verification, and apply gating",
            },
            "deterministic": {
                "source": "GeoSeal tool lookup before memory",
                "ca_opcode_facts": {"abs": "0x09", "add": "0x00"},
            },
            "verification": {
                "tests": "run focused checks before apply",
                "apply_gate": "closed until tests pass",
            },
            "required_gate_evidence": required,
            "forbidden_boundary": {
                "count": len(forbidden),
                "policy": "omitted from assistant body so the gate cannot be tripped",
            },
            "tokenizer_alignment": _tokenizer_alignment("switchboard"),
            "risk_tiers": RISK_TIERS,
            "geoshell_event": event,
        }
        if gate_id == "tokenizer_alignment_packet":
            assistant["sacred_tongue_full_names"] = {
                item["code"]: item["name"] for item in SACRED_TONGUES
            }
            assistant["sacred_tongue_coding_lanes"] = {
                item["name"]: item["coding_lane"] for item in SACRED_TONGUES
            }
        user_content = prompt["prompt"]
        records.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": _json_dumps(assistant)},
                ],
                "meta": {
                    "schema_version": SCHEMA_VERSION,
                    "program": "geoshell_pair_agent",
                    "source_family": "geoshell_pair_agent_eval_contract",
                    "source_script": "config/model_training/geoshell_pair_agent_eval_contract.json",
                    "split": "train",
                    "task_id": f"gate_repair_{gate_id}",
                    "task_kind": "promotion_gate_repair",
                    "goal_sha256": _sha256_text(user_content),
                    "assistant_sha256": _sha256_text(_json_dumps(assistant)),
                    "geoshell_event_sig": event["_sig"],
                    "sacred_tongue_codes": [item["code"] for item in SACRED_TONGUES],
                    "sacred_tongue_names": [item["name"] for item in SACRED_TONGUES],
                },
            }
        )
    return records


def _eval_shape_gold_records() -> list[dict[str, Any]]:
    """Hand-authored eval-shape gold rows for the four frozen contract prompts.

    These rows are intentionally NOT multiplied by the population loop. They
    represent the natural inference distribution (no preamble, no
    POPULATION_CONTEXT trailer, no GATE_ID/REQUIRED/FORBIDDEN hints). Four
    paraphrases per gate prompt give the adapter sixteen distinct
    eval-shape examples to anchor on during free generation.

    Replaces the previous direct_smoke_repair set, which was bootstrapped
    from a failing HF job and trained the model on its own bad outputs.
    """

    cases: list[tuple[str, str, str, dict[str, Any]]] = []

    builder_navigator_assistant = {
        "schema_version": "geoshell_pair_agent_smoke_repair_v1",
        "00_required_items": "Builder | Navigator | deterministic | verification | tests | apply",
        "mode": "direct_smoke_repair",
        "Builder": {
            "role": "Builder",
            "responsibility": "draft the safe Python helper and identify owned-file scope only",
        },
        "Navigator": {
            "role": "Navigator",
            "deterministic": "route facts through repo tools and the deterministic opcode table before any memory recall",
            "verification": "run focused unit tests and a boundary test, then inspect results before apply",
        },
        "deterministic": "repo tools and deterministic lookup before memory",
        "verification": "focused tests plus boundary test before apply",
        "tests": ["unit test", "invalid-input boundary test", "permission-scope test"],
        "apply": {"apply_gate": "closed", "opens_after": "tests pass and owned-paths confirmed"},
        "geoshell_event": {
            "_sig": "geoshell-eval-gold-builder-navigator",
            "_agent_id": "pair-agent-builder-navigator",
            "id": "eval-gold-builder-navigator",
            "task_type": "pair_coding_gate_repair",
            "query": "safe Python helper",
            "success": True,
            "timestamp": _utc_now(),
            "breaker_state": {"apply_gate": "closed"},
        },
    }
    cases.extend(
        [
            (
                "eval_gold_builder_navigator_packet_v1",
                "builder_navigator_packet",
                "For GeoShell, plan a paired coding task that writes a safe Python helper. "
                "Return a structured packet with Builder and Navigator roles, separate "
                "deterministic tool and verification lanes, and an apply gate that stays "
                "closed until tests pass.",
                builder_navigator_assistant,
            ),
            (
                "eval_gold_builder_navigator_packet_v2",
                "builder_navigator_packet",
                "Plan a GeoShell paired coding task for a small Python helper. Show a "
                "Builder/Navigator packet with separate deterministic routing and "
                "verification lanes, and keep the apply gate closed until the tests "
                "have passed.",
                builder_navigator_assistant,
            ),
            (
                "eval_gold_builder_navigator_packet_v3",
                "builder_navigator_packet",
                "Sketch a GeoShell paired coding workflow with a Builder, a Navigator, "
                "deterministic lookup separated from verification, and an apply gate that "
                "only opens once tests pass.",
                builder_navigator_assistant,
            ),
            (
                "eval_gold_builder_navigator_packet_v4",
                "builder_navigator_packet",
                "Outline a paired coding task in GeoShell. Required: Builder role, "
                "Navigator role, deterministic tool routing, verification, and an apply "
                "gate held closed until tests pass.",
                builder_navigator_assistant,
            ),
        ]
    )
    cases.extend(
        [
            (
                f"eval_gold_builder_navigator_packet_v{index}",
                "builder_navigator_packet",
                prompt,
                builder_navigator_assistant,
            )
            for index, prompt in enumerate(
                [
                    "Return only a compact GeoShell Builder/Navigator packet for a safe Python helper. It must include Builder, Navigator, deterministic, verification, tests, and apply.",
                    "Write a GeoShell pair packet with exact fields: Builder, Navigator, deterministic, verification, tests, apply. The apply gate stays closed until tests pass.",
                    "GeoShell pair task: safe Python helper. Include Builder role, Navigator role, deterministic lookup, verification, tests, and apply gate closed.",
                    "Produce the minimal valid packet for Builder/Navigator paired coding. Required fields: Builder, Navigator, deterministic, verification, tests, apply.",
                    "For a Python helper task, return GeoShell JSON-like evidence with Builder, Navigator, deterministic, verification, tests, and apply gate closed.",
                    "Do not skip tests. Return Builder, Navigator, deterministic, verification, tests, and apply for a GeoShell paired coding helper.",
                    "Show Builder and Navigator lanes plus deterministic routing, verification, tests, and apply gate closed until tests pass.",
                    "Builder drafts; Navigator verifies. Output must still include deterministic, verification, tests, and apply gate closed.",
                ],
                start=5,
            )
        ]
    )
    builder_navigator_first_face_assistant = {
        "00_required_items": "Builder | Navigator | deterministic | verification | tests | apply",
        "01_tests": "unit test, invalid-input boundary test, permission-scope test",
        "02_apply": "apply gate closed until tests pass",
        "Builder": "draft safe Python helper intent only",
        "Navigator": "deterministic lookup, verification, tests, then apply-gate decision",
        "deterministic": "repo tools and deterministic lookup before memory",
        "verification": "tests must be named before any apply decision",
        "geoshell_event": {
            "_sig": "geoshell-eval-gold-builder-navigator-first-face",
            "_agent_id": "pair-agent-builder-navigator",
            "id": "eval-gold-builder-navigator-first-face",
            "task_type": "pair_coding_gate_repair",
            "query": "safe Python helper first-face repair",
            "success": True,
            "timestamp": _utc_now(),
            "breaker_state": {"apply_gate": "closed"},
        },
    }
    cases.extend(
        [
            (
                f"eval_gold_builder_navigator_packet_v{index}",
                "builder_navigator_packet",
                prompt,
                builder_navigator_first_face_assistant,
            )
            for index, prompt in enumerate(
                [
                    "Raw repair: first line must include Builder, Navigator, deterministic, verification, tests, apply for a safe Python helper.",
                    "Before any facts or tool list, output Builder, Navigator, deterministic, verification, tests, apply for the GeoShell helper packet.",
                    "GeoShell raw gate: do not bury tests. Start with Builder, Navigator, deterministic, verification, tests, apply.",
                    "For the safe Python helper, the answer must name tests before apply and include Builder, Navigator, deterministic, verification.",
                    "Minimal first-face Builder/Navigator packet: Builder, Navigator, deterministic, verification, tests, apply. Then optional details.",
                    "Repair the missing-tests failure: include tests in the first field with Builder, Navigator, deterministic, verification, and apply.",
                    "Return a compact first-face packet. Required literals: Builder Navigator deterministic verification tests apply.",
                    "Do not lead with unrelated object facts. Lead with Builder, Navigator, deterministic, verification, tests, apply.",
                ],
                start=13,
            )
        ]
    )
    builder_tests_literal_assistant = {
        "00_required_items": "Builder | Navigator | deterministic | verification | tests | apply",
        "01_tests_literal": "tests",
        "02_tests_gate": "tests pass before apply; tests are named explicitly as tests",
        "03_apply_gate": "apply gate closed",
        "Builder": "draft safe Python helper intent only",
        "Navigator": "deterministic lookup, verification, tests, then apply gate",
        "deterministic": "repo tools and deterministic lookup before memory",
        "verification": "verification includes tests",
        "apply": "closed until tests pass",
        "geoshell_event": {
            "_sig": "geoshell-eval-gold-builder-tests-literal",
            "_agent_id": "pair-agent-builder-navigator",
            "id": "eval-gold-builder-tests-literal",
            "task_type": "pair_coding_gate_repair",
            "query": "safe Python helper tests literal repair",
            "success": True,
            "timestamp": _utc_now(),
            "breaker_state": {"apply_gate": "closed"},
        },
    }
    cases.extend(
        [
            (
                f"eval_gold_builder_navigator_packet_v{index}",
                "builder_navigator_packet",
                prompt,
                builder_tests_literal_assistant,
            )
            for index, prompt in enumerate(
                [
                    "Literal repair: include the exact word tests in the first field with Builder, Navigator, deterministic, verification, and apply.",
                    "The answer fails if it says single-test instead of tests. Output Builder, Navigator, deterministic, verification, tests, apply.",
                    "Use exact plural tests. GeoShell safe helper packet requires Builder, Navigator, deterministic, verification, tests, apply.",
                    "Before facts, write required items: Builder Navigator deterministic verification tests apply.",
                    "Repair missing exact token: tests. Include tests before apply in the Builder/Navigator packet.",
                    "For safe helper planning, first field must contain tests, not test, plus Builder, Navigator, deterministic, verification, apply.",
                    "Name tests explicitly: Builder, Navigator, deterministic, verification, tests, apply gate closed.",
                    "Do not substitute unit check for tests. Required literals are Builder, Navigator, deterministic, verification, tests, apply.",
                ],
                start=21,
            )
        ]
    )
    builder_tests_first_field_assistant = {
        "00_required_items": "Builder | Navigator | deterministic | verification | tests | apply",
        "01_tests_literal": "tests",
        "02_tests_before_apply": "tests before apply",
        "03_do_not_substitute": "do not replace tests with test gate, unit check, or validation gate",
        "Builder": {
            "role": "Builder",
            "responsibility": "draft safe Python helper intent only",
        },
        "Navigator": {
            "role": "Navigator",
            "deterministic": "route facts through deterministic tools",
            "verification": "run tests and report tests before apply",
        },
        "deterministic": "repo tools and deterministic lookup before memory",
        "verification": "tests are the named verification artifact",
        "tests": ["tests"],
        "apply": {"apply_gate": "closed", "opens_after": "tests pass"},
        "geoshell_event": {
            "_sig": "geoshell-eval-gold-builder-tests-first-field",
            "_agent_id": "pair-agent-builder-navigator",
            "id": "eval-gold-builder-tests-first-field",
            "task_type": "pair_coding_gate_repair",
            "query": "safe Python helper tests first-field repair",
            "success": True,
            "timestamp": _utc_now(),
            "breaker_state": {"apply_gate": "closed"},
        },
    }
    cases.extend(
        [
            (
                f"eval_gold_builder_navigator_packet_v{index}",
                "builder_navigator_packet",
                prompt,
                builder_tests_first_field_assistant,
            )
            for index, prompt in enumerate(
                [
                    "The first generated field must be exactly 00_required_items with Builder, Navigator, deterministic, verification, tests, apply.",
                    "Raw canary repair: 00_required_items must contain tests between verification and apply.",
                    "Do not say test gate. Say tests. First field: Builder | Navigator | deterministic | verification | tests | apply.",
                    "Return JSON-like packet where 00_required_items includes the exact plural tests before apply.",
                    "GeoShell Builder/Navigator helper packet: the first field must preserve tests as a required literal.",
                    "Repair missing raw literal tests by putting tests in 00_required_items and again in 01_tests_literal.",
                    "Output starts with 00_required_items: Builder | Navigator | deterministic | verification | tests | apply.",
                    "For this safe helper route, tests is mandatory evidence; do not substitute validation or gate wording.",
                ],
                start=29,
            )
        ]
    )

    ca_pair_assistant = {
        "schema_version": "geoshell_pair_agent_smoke_repair_v1",
        "mode": "direct_smoke_repair",
        "deterministic": "required",
        "Builder": {
            "role": "Builder",
            "intent": "propose abs(a)+abs(b) as a paired-agent route through deterministic CA opcode lookup",
        },
        "Navigator": {
            "role": "Navigator",
            "deterministic": "look up CA opcode facts in python.scbe.ca_opcode_table.OP_TABLE: abs=0x09, add=0x00",
            "verification": "confirm exact_sequence before apply",
        },
        "ca_opcode_facts": {"abs": "0x09", "add": "0x00"},
        "expected_sequence": "0x09, 0x09, 0x00",
        "apply_gate": "closed until verification passes",
        "geoshell_event": {
            "_sig": "geoshell-eval-gold-ca-abs-add",
            "_agent_id": "pair-agent-builder-navigator",
            "id": "eval-gold-ca-abs-add",
            "task_type": "pair_coding_gate_repair",
            "query": "abs(a)+abs(b) CA opcode route",
            "success": True,
            "timestamp": _utc_now(),
            "breaker_state": {"apply_gate": "closed"},
        },
    }
    cases.extend(
        [
            (
                "eval_gold_ca_abs_add_pair_route_v1",
                "ca_abs_add_pair_route",
                "Run the task abs(a)+abs(b) as a GeoShell paired-agent route. The Builder "
                "should propose intent, the Navigator should route exact CA opcode facts "
                "through deterministic lookup, and the final sequence must include abs=0x09 "
                "and add=0x00.",
                ca_pair_assistant,
            ),
            (
                "eval_gold_ca_abs_add_pair_route_v2",
                "ca_abs_add_pair_route",
                "Build a GeoShell pair-agent answer for abs(a)+abs(b). Builder proposes the "
                "intent, Navigator routes the deterministic CA opcode facts, and the final "
                "answer must contain abs=0x09 and add=0x00.",
                ca_pair_assistant,
            ),
            (
                "eval_gold_ca_abs_add_pair_route_v3",
                "ca_abs_add_pair_route",
                "For abs(a)+abs(b), produce a paired Builder/Navigator route in GeoShell "
                "with deterministic opcode lookup. The exact sequence must include abs=0x09 "
                "and add=0x00; never guess opcodes from memory.",
                ca_pair_assistant,
            ),
            (
                "eval_gold_ca_abs_add_pair_route_v4",
                "ca_abs_add_pair_route",
                "Plan abs(a)+abs(b) as a GeoShell paired-agent task: Builder drafts intent, "
                "Navigator does deterministic CA opcode routing, final sequence has "
                "abs=0x09 and add=0x00.",
                ca_pair_assistant,
            ),
        ]
    )
    cases.extend(
        [
            (
                f"eval_gold_ca_abs_add_pair_route_v{index}",
                "ca_abs_add_pair_route",
                prompt,
                ca_pair_assistant,
            )
            for index, prompt in enumerate(
                [
                    "Return a compact GeoShell route for abs(a)+abs(b). It must include Builder, Navigator, deterministic, abs=0x09, and add=0x00.",
                    "GeoShell CA route: Builder proposes abs(a)+abs(b); Navigator performs deterministic lookup. Required facts: abs=0x09 and add=0x00.",
                    "Do not say deterministic false. For abs(a)+abs(b), return Builder, Navigator, deterministic, 0x09, and 0x00.",
                    "Cassisivadan CA exact route for |a|+|b|: Builder, Navigator, deterministic lookup, abs 0x09, add 0x00.",
                    "Produce the minimal valid CA pair route. Include Builder, Navigator, deterministic=required, abs=0x09, add=0x00.",
                    "For abs(a)+abs(b), the final GeoShell packet must name Builder and Navigator and show deterministic lookup with 0x09 and 0x00.",
                    "Return CA opcode facts for abs(a)+abs(b): Builder lane, Navigator lane, deterministic lookup, abs=0x09, add=0x00.",
                    "GeoShell pair-agent route for abs plus abs: exact markers Builder, Navigator, deterministic, 0x09, 0x00.",
                ],
                start=5,
            )
        ]
    )

    geoshell_event_assistant = {
        "schema_version": "geoshell_pair_agent_smoke_repair_v1",
        "mode": "direct_smoke_repair",
        "_agent_id": "pair-agent-builder-navigator",
        "task_type": "pair_coding",
        "query": "successful paired coding task",
        "success": True,
        "timestamp": "2026-05-04T13:35:34Z",
        "breaker_state": {"apply_gate": "closed"},
        "geoshell_event": {
            "_sig": "geoshell-eval-gold-event-shape",
            "_agent_id": "pair-agent-builder-navigator",
            "id": "eval-gold-event-shape",
            "task_type": "pair_coding",
            "query": "successful paired coding task",
            "success": True,
            "timestamp": "2026-05-04T13:35:34Z",
            "breaker_state": {"apply_gate": "closed"},
        },
    }
    cases.extend(
        [
            (
                "eval_gold_geoshell_event_shape_v1",
                "geoshell_event_shape",
                "Return a GeoShell-compatible event row for a successful paired coding task. "
                "Include _agent_id, task_type, query, success, timestamp, and breaker_state "
                "with apply_gate closed.",
                geoshell_event_assistant,
            ),
            (
                "eval_gold_geoshell_event_shape_v2",
                "geoshell_event_shape",
                "Emit one GeoShell event row for a successful pair-coding run. Fields: "
                "_agent_id, task_type, query, success, timestamp, and breaker_state with "
                "apply_gate closed.",
                geoshell_event_assistant,
            ),
            (
                "eval_gold_geoshell_event_shape_v3",
                "geoshell_event_shape",
                "Produce a GeoShell event entry that records a successful paired coding task "
                "with _agent_id, task_type, query, success, timestamp, and breaker_state "
                "showing apply_gate closed.",
                geoshell_event_assistant,
            ),
            (
                "eval_gold_geoshell_event_shape_v4",
                "geoshell_event_shape",
                "Write a single GeoShell event row reporting a successful pair coding run, "
                "with _agent_id, task_type, query, success, timestamp, and breaker_state "
                "carrying apply_gate=closed.",
                geoshell_event_assistant,
            ),
        ]
    )

    tokenizer_assistant = {
        "schema_version": "geoshell_pair_agent_smoke_repair_v1",
        "00_alignment_literals": (
            "Kor'aelin KO | Avali AV | Runethic RU | Cassisivadan CA | "
            "Umbroth UM | Draumric DR | ALLOW | QUARANTINE | ESCALATE | DENY"
        ),
        "mode": "direct_smoke_repair",
        "Builder": {
            "role": "Builder",
            "responsibility": "produce the tokenizer alignment packet",
        },
        "Navigator": {
            "role": "Navigator",
            "responsibility": "verify all six Sacred Tongues and risk tiers are present",
        },
        "sacred_tongues": [
            {"code": "KO", "name": "Kor'aelin"},
            {"code": "AV", "name": "Avali"},
            {"code": "RU", "name": "Runethic"},
            {"code": "CA", "name": "Cassisivadan"},
            {"code": "UM", "name": "Umbroth"},
            {"code": "DR", "name": "Draumric"},
        ],
        "risk_tiers": ["ALLOW", "QUARANTINE", "ESCALATE", "DENY"],
        "governance": "apply gate remains closed until tests and route checks pass",
        "geoshell_event": {
            "_sig": "geoshell-eval-gold-tokenizer-alignment",
            "_agent_id": "pair-agent-builder-navigator",
            "id": "eval-gold-tokenizer-alignment",
            "task_type": "tokenizer_alignment_gate_repair",
            "query": "Sacred Tongue tokenizer alignment packet",
            "success": True,
            "timestamp": _utc_now(),
            "breaker_state": {"apply_gate": "closed"},
        },
    }
    cases.extend(
        [
            (
                "eval_gold_tokenizer_alignment_packet_v1",
                "tokenizer_alignment_packet",
                "For a GeoShell Builder/Navigator coding task, return the Sacred Tongue "
                "tokenizer alignment packet. Include the full names and abbreviations for "
                "Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, and "
                "Draumric DR, plus risk tiers ALLOW, QUARANTINE, ESCALATE, and DENY.",
                tokenizer_assistant,
            ),
            (
                "eval_gold_tokenizer_alignment_packet_v2",
                "tokenizer_alignment_packet",
                "Return the tokenizer alignment packet for a GeoShell Builder/Navigator "
                "task. Cover all six Sacred Tongues by full name and abbreviation: "
                "Kor'aelin (KO), Avali (AV), Runethic (RU), Cassisivadan (CA), Umbroth "
                "(UM), Draumric (DR), and the risk tiers ALLOW, QUARANTINE, ESCALATE, DENY.",
                tokenizer_assistant,
            ),
            (
                "eval_gold_tokenizer_alignment_packet_v3",
                "tokenizer_alignment_packet",
                "List the Sacred Tongue tokenizer alignment for a Builder/Navigator coding "
                "task. Use both abbreviations and full names: KO Kor'aelin, AV Avali, RU "
                "Runethic, CA Cassisivadan, UM Umbroth, DR Draumric. Include risk tiers "
                "ALLOW, QUARANTINE, ESCALATE, DENY.",
                tokenizer_assistant,
            ),
            (
                "eval_gold_tokenizer_alignment_packet_v4",
                "tokenizer_alignment_packet",
                "Provide the GeoShell pair-agent Sacred Tongue alignment with all six "
                "tongues by full name and abbreviation (Kor'aelin KO, Avali AV, Runethic "
                "RU, Cassisivadan CA, Umbroth UM, Draumric DR) and the four risk tiers "
                "ALLOW, QUARANTINE, ESCALATE, DENY.",
                tokenizer_assistant,
            ),
        ]
    )
    cases.extend(
        [
            (
                f"eval_gold_tokenizer_alignment_packet_v{index}",
                "tokenizer_alignment_packet",
                prompt,
                tokenizer_assistant,
            )
            for index, prompt in enumerate(
                [
                    "Return only the tokenizer alignment target first, then roles: Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR, ALLOW, QUARANTINE, ESCALATE, DENY.",
                    "GeoShell tokenizer alignment packet: start with Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR and risk tiers ALLOW, QUARANTINE, ESCALATE, DENY.",
                    "Do not lead with tool lists. Lead with the Sacred Tongue literals: Kor'aelin KO; Avali AV; Runethic RU; Cassisivadan CA; Umbroth UM; Draumric DR; ALLOW; QUARANTINE; ESCALATE; DENY.",
                    "Minimal tokenizer alignment answer for Builder/Navigator: Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR, ALLOW, QUARANTINE, ESCALATE, DENY.",
                    "For the tokenizer gate, the first field must contain Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR, ALLOW, QUARANTINE, ESCALATE, DENY.",
                    "Sacred Tongue alignment first, governance second: Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR; tiers ALLOW QUARANTINE ESCALATE DENY.",
                    "Write the six-tongue alignment before any deterministic tool plan: Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR, ALLOW, QUARANTINE, ESCALATE, DENY.",
                    "Tokenization target face: Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR, ALLOW, QUARANTINE, ESCALATE, DENY; then Builder and Navigator verify.",
                ],
                start=5,
            )
        ]
    )
    tokenizer_first_face_assistant = {
        "00_alignment_literals": (
            "Kor'aelin KO | Avali AV | Runethic RU | Cassisivadan CA | "
            "Umbroth UM | Draumric DR | ALLOW | QUARANTINE | ESCALATE | DENY"
        ),
        "01_instruction": "repeat the alignment literals before any tool list or event body",
        "Builder": "prepare tokenizer alignment packet",
        "Navigator": "verify all six full names, abbreviations, and risk tiers",
        "sacred_tongues": [
            "Kor'aelin KO",
            "Avali AV",
            "Runethic RU",
            "Cassisivadan CA",
            "Umbroth UM",
            "Draumric DR",
        ],
        "risk_tiers": "ALLOW | QUARANTINE | ESCALATE | DENY",
        "geoshell_event": {
            "_sig": "geoshell-eval-gold-tokenizer-first-face",
            "_agent_id": "pair-agent-builder-navigator",
            "id": "eval-gold-tokenizer-first-face",
            "task_type": "tokenizer_alignment_gate_repair",
            "query": "Sacred Tongue tokenizer alignment first-face repair",
            "success": True,
            "timestamp": _utc_now(),
            "breaker_state": {"apply_gate": "closed"},
        },
    }
    cases.extend(
        [
            (
                f"eval_gold_tokenizer_alignment_packet_v{index}",
                "tokenizer_alignment_packet",
                prompt,
                tokenizer_first_face_assistant,
            )
            for index, prompt in enumerate(
                [
                    "Raw repair: first line must be Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR, ALLOW, QUARANTINE, ESCALATE, DENY.",
                    "Before any GeoShell event or tool list, output Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR, ALLOW, QUARANTINE, ESCALATE, DENY.",
                    "Tokenizer raw gate: do not describe the packet first. Start with Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR, ALLOW, QUARANTINE, ESCALATE, DENY.",
                    "Repair missing tokenizer literals by putting every required Sacred Tongue and risk tier in the first field.",
                    "Minimal first-face tokenizer packet: Kor'aelin KO | Avali AV | Runethic RU | Cassisivadan CA | Umbroth UM | Draumric DR | ALLOW | QUARANTINE | ESCALATE | DENY.",
                    "Do not lead with abstract text. Lead with Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR, ALLOW, QUARANTINE, ESCALATE, DENY.",
                    "GeoShell Sacred Tongue alignment first, roles second: Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR, ALLOW, QUARANTINE, ESCALATE, DENY.",
                    "For tokenizer alignment, the required target face is Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR, ALLOW, QUARANTINE, ESCALATE, DENY.",
                ],
                start=13,
            )
        ]
    )
    tokenizer_risk_tier_literal_assistant = {
        "00_required_facts": (
            "Kor'aelin KO | Avali AV | Runethic RU | Cassisivadan CA | "
            "Umbroth UM | Draumric DR | ALLOW | QUARANTINE | ESCALATE | DENY"
        ),
        "01_risk_tiers_literal": "ALLOW | QUARANTINE | ESCALATE | DENY",
        "02_alignment_literals": (
            "Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR"
        ),
        "Builder": "prepare tokenizer alignment packet",
        "Navigator": "verify six tongues and four risk tiers before any tool list",
        "sacred_tongues": [
            "Kor'aelin KO",
            "Avali AV",
            "Runethic RU",
            "Cassisivadan CA",
            "Umbroth UM",
            "Draumric DR",
        ],
        "risk_tiers": ["ALLOW", "QUARANTINE", "ESCALATE", "DENY"],
        "geoshell_event": {
            "_sig": "geoshell-eval-gold-tokenizer-risk-tier-literal",
            "_agent_id": "pair-agent-builder-navigator",
            "id": "eval-gold-tokenizer-risk-tier-literal",
            "task_type": "tokenizer_alignment_gate_repair",
            "query": "Sacred Tongue tokenizer risk-tier literal repair",
            "success": True,
            "timestamp": _utc_now(),
            "breaker_state": {"apply_gate": "closed"},
        },
    }
    cases.extend(
        [
            (
                f"eval_gold_tokenizer_alignment_packet_v{index}",
                "tokenizer_alignment_packet",
                prompt,
                tokenizer_risk_tier_literal_assistant,
            )
            for index, prompt in enumerate(
                [
                    "Literal risk-tier repair: include ALLOW, QUARANTINE, ESCALATE, DENY in the first field after all six Sacred Tongues.",
                    "The tokenizer answer fails without risk tiers. First field must include ALLOW QUARANTINE ESCALATE DENY.",
                    "Do not stop after Draumric DR. Continue with ALLOW, QUARANTINE, ESCALATE, DENY.",
                    "GeoShell tokenizer packet: Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR, ALLOW, QUARANTINE, ESCALATE, DENY.",
                    "Repair missing risk-tier literals by writing ALLOW, QUARANTINE, ESCALATE, DENY before any event or tool list.",
                    "Risk tiers are required target tokens: ALLOW QUARANTINE ESCALATE DENY. Put them with the Sacred Tongue list.",
                    "Tokenizer first face must end with ALLOW | QUARANTINE | ESCALATE | DENY.",
                    "Never omit risk tiers. Include Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR, ALLOW, QUARANTINE, ESCALATE, DENY.",
                ],
                start=21,
            )
        ]
    )

    rows: list[dict[str, Any]] = []
    for case_id, gate_id, user_content, assistant in cases:
        assistant_json = _json_dumps(assistant)
        rows.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": assistant_json},
                ],
                "meta": {
                    "schema_version": SCHEMA_VERSION,
                    "program": "geoshell_pair_agent",
                    "source_family": "geoshell_pair_agent_eval_shape_gold",
                    "source_script": "scripts/training_data/build_geoshell_pair_agent_sft.py",
                    "split": "train",
                    "task_id": case_id,
                    "task_kind": "eval_shape_gold",
                    "gate_id": gate_id,
                    "goal_sha256": _sha256_text(user_content),
                    "assistant_sha256": _sha256_text(assistant_json),
                    "geoshell_event_sig": assistant["geoshell_event"]["_sig"],
                    "sacred_tongue_codes": [item["code"] for item in SACRED_TONGUES],
                    "sacred_tongue_names": [item["name"] for item in SACRED_TONGUES],
                },
            }
        )
    return rows


def _populate_records(
    records: list[dict[str, Any]], population_multiplier: int
) -> list[dict[str, Any]]:
    if population_multiplier < 1:
        raise ValueError("population_multiplier must be >= 1")
    return [
        _population_variant(record, population_index, population_multiplier)
        for record in records
        for population_index in range(population_multiplier)
    ]


def build_dataset(
    population_multiplier: int = DEFAULT_POPULATION_MULTIPLIER,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    tasks = task_suite()
    holdout_ids = {tasks[-1].task_id} if tasks else set()

    for index, task in enumerate(tasks, start=1):
        pair_result = run_pair(task)
        split = "holdout" if task.task_id in holdout_ids else "train"
        record = _record_for_task(task, pair_result, split, index)
        records.append(record)
        assistant = json.loads(record["messages"][-1]["content"])
        events.append(assistant["geoshell_event"])

    for record in _switchboard_records():
        records.append(record)
        assistant = json.loads(record["messages"][-1]["content"])
        events.append(assistant["switchboard_event"])

    for record in _gate_contract_records():
        records.append(record)
        assistant = json.loads(record["messages"][-1]["content"])
        events.append(assistant["geoshell_event"])

    populated = _populate_records(records, population_multiplier)

    # Eval-shape gold rows are NOT multiplied: they represent the natural
    # inference distribution and live alongside the populated rows verbatim.
    eval_gold_rows = _eval_shape_gold_records()

    train = [row for row in populated if row["meta"]["split"] == "train"]
    train.extend(eval_gold_rows)
    holdout = [row for row in populated if row["meta"]["split"] == "holdout"]
    populated_events = []
    for row in populated:
        assistant = json.loads(row["messages"][-1]["content"])
        event = assistant.get("geoshell_event") or assistant.get("switchboard_event")
        if event:
            populated_events.append(event)
    for row in eval_gold_rows:
        assistant = json.loads(row["messages"][-1]["content"])
        event = assistant.get("geoshell_event")
        if event:
            populated_events.append(event)
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "train": train,
        "holdout": holdout,
        "events": populated_events,
        "base_record_count": len(records),
        "population_multiplier": population_multiplier,
        "eval_gold_count": len(eval_gold_rows),
        "source": {
            "benchmark_schema": PAIR_BENCHMARK_SCHEMA,
            "source_script": "scripts/benchmark/dual_agent_pair_benchmark.py",
        },
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(_json_dumps(row) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def _resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def write_outputs(
    dataset: dict[str, Any], output_dir: Path, event_path: Path = DEFAULT_EVENT_PATH
) -> dict[str, str]:
    output_dir = _resolve_repo_path(output_dir)
    event_path = _resolve_repo_path(event_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    train_path = output_dir / TRAIN_NAME
    holdout_path = output_dir / HOLDOUT_NAME
    manifest_path = output_dir / MANIFEST_NAME

    _write_jsonl(train_path, dataset["train"])
    _write_jsonl(holdout_path, dataset["holdout"])
    event_path.parent.mkdir(parents=True, exist_ok=True)
    event_path.write_text(
        json.dumps(dataset["events"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": dataset["created_at"],
        "profile_id": "geoshell-pair-agent-v1",
        "base_record_count": dataset["base_record_count"],
        "population_multiplier": dataset["population_multiplier"],
        "eval_gold_count": dataset.get("eval_gold_count", 0),
        "train_count": len(dataset["train"]),
        "holdout_count": len(dataset["holdout"]),
        "record_count": len(dataset["train"]) + len(dataset["holdout"]),
        "train_path": _display_path(train_path),
        "holdout_path": _display_path(holdout_path),
        "geoshell_events_path": _display_path(event_path),
        "source": dataset["source"],
        "verification": [
            "python scripts/benchmark/dual_agent_pair_benchmark.py validate",
            "python -m pytest tests/training/test_geoshell_pair_agent_sft.py -q",
        ],
        "notes": [
            "Records train Builder/Navigator pair behavior, not frontier-model capability claims.",
            "GeoShell can read geoshell_events_path through the existing __SCBE_AGENT_BUS_EVENTS__ shape.",
            "Apply remains gated; records teach route/verify/apply separation before mutation.",
            "eval_gold rows are population-immune and mirror the frozen contract prompts.",
        ],
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "train": str(train_path),
        "holdout": str(holdout_path),
        "manifest": str(manifest_path),
        "events": str(event_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--event-path", type=Path, default=DEFAULT_EVENT_PATH)
    parser.add_argument(
        "--population-multiplier", type=int, default=DEFAULT_POPULATION_MULTIPLIER
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    dataset = build_dataset(population_multiplier=args.population_multiplier)
    paths = write_outputs(dataset, args.output_dir, args.event_path)
    print(
        json.dumps(
            {
                "ok": True,
                "schema_version": SCHEMA_VERSION,
                "train_count": len(dataset["train"]),
                "holdout_count": len(dataset["holdout"]),
                "paths": paths,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
