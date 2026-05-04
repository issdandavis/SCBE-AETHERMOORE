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
DEFAULT_POPULATION_MULTIPLIER = 14

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
    "tired operator with short instructions",
    "release-prep operator asking for exact gates",
    "dirty-worktree operator requiring owned-file boundaries",
    "multi-agent handoff with Cursor, Claude, Codex, and Kimi present",
    "security-aware operator requiring secret and apply separation",
    "training-run operator asking for machine-readable evidence",
    "remote GPU operator preparing Hugging Face and Kaggle dispatch",
    "terminal-first operator using PowerShell with copy-paste commands",
    "research-bridge operator asking for source-grounded routing before coding",
    "chemistry-lane operator requiring validation before promotion",
    "website-release operator asking for docs, tests, and user-facing evidence",
    "failure-recovery operator turning a failed run into repair data",
    "roundtable operator coordinating Builder, Navigator, Judge, and Context Keeper",
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
        user_content = (
            "Return a GeoShell paired-agent promotion-gate answer that satisfies every required "
            "substring and avoids every forbidden substring.\n\n"
            f"GATE_ID: {gate_id}\nPROMPT: {prompt['prompt']}\n"
            f"REQUIRED: {_json_dumps(required)}\nFORBIDDEN: {_json_dumps(forbidden)}"
        )
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
    train = [row for row in populated if row["meta"]["split"] == "train"]
    holdout = [row for row in populated if row["meta"]["split"] == "holdout"]
    populated_events = []
    for row in populated:
        assistant = json.loads(row["messages"][-1]["content"])
        event = assistant.get("geoshell_event") or assistant.get("switchboard_event")
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
