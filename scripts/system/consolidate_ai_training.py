#!/usr/bin/env python3
"""Consolidate SCBE training data into specialist model buckets.

This is a local-first control plane. It inventories datasets, regularizes
purpose buckets, and writes a staged specialist-training plus adapter-merge
promotion plan. It does not dispatch GPU jobs by default.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "ai_training_consolidation" / "latest"
DEFAULT_PURPOSES = (
    "coding_model",
    "aligned_foundations",
    "operator_agent_bus",
    "governance_security",
    "research_bridge",
)
CONVERGENCE_GOALS = (
    {
        "goal_id": "bijective_reasoning_and_coding",
        "summary": "Make reversible packet reasoning and coding a first-class behavior across GeoSeal, Sacred Tongues, and coding formation traces.",
        "evidence": [
            "source_sha256/token_sha256 round trips",
            "slot-preserving code packet traces",
            "Stage 5 and Stage 6 frozen contracts",
        ],
    },
    {
        "goal_id": "repo_grounded_agentic_execution",
        "summary": "Train models to turn ambiguous user goals into repo-grounded actions, receipts, tests, and release gates instead of broad prose.",
        "evidence": [
            "intent packets",
            "layer runner receipts",
            "formation role receipts",
            "focused pytest or benchmark command evidence",
        ],
    },
    {
        "goal_id": "multi_representation_alignment",
        "summary": "Keep mathematics, English, full Sacred Tongues names, abbreviations, binary framing, chemistry packets, and coding primaries synchronized.",
        "evidence": [
            "aligned-foundations concept_id threading",
            "chemistry conservation records",
            "coding face and packet compliance checks",
        ],
    },
    {
        "goal_id": "source_grounded_research_rag",
        "summary": "Convert research captures into source-identified, falsifiable records that agents can cite, reject, or route into implementation lanes.",
        "evidence": [
            "source path or URL identity",
            "claim text",
            "reject list",
            "testable implementation target",
        ],
    },
    {
        "goal_id": "local_first_free_model_fleet",
        "summary": "Prefer small local/free model pairs and triads with explicit lane-change signaling; use larger models only as bounded helpers.",
        "evidence": [
            "provider-pair signals",
            "harness-terminal provider matrix",
            "costed pair or triad receipts",
        ],
    },
    {
        "goal_id": "release_cleanliness_and_promotion",
        "summary": "Promote only artifacts that pass packet integrity, route consistency, code tests, benchmark checks, and release-readiness cleanup.",
        "evidence": [
            "promotion gate report",
            "specialist bucket readiness report",
            "release readiness output",
        ],
    },
)
TRAINING_LANES = (
    {
        "lane_id": "aligned_foundations",
        "purpose": "Shared substrate learning across math, English, Sacred Tongues, binary, chemistry, and coding.",
        "primary_profile": "config/model_training/aligned-foundations-qwen-primary.json",
        "canonical_inputs": [
            "training-data/manifests/2026-05-02-aligned-foundations-v2-manifest.json",
            "training-data/sft/drill_langues_full_train.sft.jsonl",
            "training-data/sft/bijective_codeflow_v1_train.sft.jsonl",
        ],
    },
    {
        "lane_id": "stage5_command_harmony",
        "purpose": "Teach current GeoSeal command recall, analog action compression, provider lane signaling, and runtime-vs-structural boundaries.",
        "primary_profile": "config/model_training/coding-agent-qwen-command-harmony-v5-signal-repair-v1.json",
        "canonical_inputs": [
            "config/model_training/stage5_command_harmony_eval_contract.json",
            "training-data/sft/stage5_command_harmony_signal_shape_boost_train.sft.jsonl",
            "training-data/sft/stage5_command_harmony_signal_shape_boost_holdout.sft.jsonl",
        ],
    },
    {
        "lane_id": "stage6_coding_repair",
        "purpose": "Teach executable repair vocabulary and constrained code-output behavior under frozen must-pass gates.",
        "primary_profile": "config/model_training/coding-agent-qwen-stage6-repair-v9.json",
        "canonical_inputs": [
            "training-data/sft/atomic_workflow_stage6_must_pass_boost_manifest.json",
            "training-data/sft/atomic_workflow_stage6_signal_shape_boost_manifest.json",
        ],
    },
    {
        "lane_id": "agentic_packet_traces",
        "purpose": "Teach compact runner-chain and provider-pair behavior from executable packet traces instead of whole conversations.",
        "primary_profile": "config/model_training/operator-agent-bus-qwen-primary.json",
        "canonical_inputs": [
            "training-data/agentic_coding/packet_traces.jsonl",
            "docs/AGENTIC_LAYER_RUNNER_ROADMAP.md",
            "docs/AGENTIC_CODING_FORMATIONS_ROADMAP.md",
        ],
    },
    {
        "lane_id": "source_grounded_research",
        "purpose": "Teach agents to find sources, keep claims falsifiable, and route research into implementation or rejection lanes.",
        "primary_profile": "config/model_training/research-bridge-qwen-primary.json",
        "canonical_inputs": [
            "docs/RESEARCH_ROADMAP_INDEX.md",
            "docs/research/ATOMIC_TOKENIZER_INDUSTRY_REFERENCES_2026-05-03.md",
            "training-data/research_bridge_smoke",
        ],
    },
)
PROMOTION_GATES = (
    {
        "gate_id": "G1_packet_integrity",
        "rule": "Every promoted lane must preserve packet schema, hashes, and bijective round-trip evidence.",
    },
    {
        "gate_id": "G2_route_and_lane_signaling",
        "rule": "Provider, permission, phase, or language lane changes require explicit signals and must fail closed when missing.",
    },
    {
        "gate_id": "G3_executable_coding",
        "rule": "Coding specialists must pass focused repo tests or frozen executable contracts before adapter promotion.",
    },
    {
        "gate_id": "G4_cross_lane_alignment",
        "rule": "Aligned-foundations records must preserve concept identity across math, English, Sacred Tongues, binary, chemistry, and coding faces.",
    },
    {
        "gate_id": "G5_source_and_research_grounding",
        "rule": "Research records must carry source identity, falsifiable claim text, and a routeable implementation or rejection target.",
    },
    {
        "gate_id": "G6_release_readiness",
        "rule": "Merged outputs must pass benchmark/readiness checks and keep generated churn out of release commits.",
    },
)
REGULARIZATION_CONFIG = (
    REPO_ROOT / "config" / "model_training" / "scbe_dataset_regularization_v1.json"
)
MERGE_PROFILE = (
    REPO_ROOT
    / "config"
    / "model_training"
    / "coding-agent-qwen-merged-coding-model.json"
)


SPECIALIST_DEFAULTS: dict[str, dict[str, Any]] = {
    "coding_model": {
        "specialist_id": "coding_primary_specialist",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "method_order": ["SFT", "adapter_eval", "adapter_merge"],
        "profile_candidates": [
            "config/model_training/coding-agent-qwen-full-coding-system-v8.json",
            "config/model_training/coding-agent-qwen-stage6-repair-v7.json",
        ],
        "merge_weight": 0.38,
        "promotion_gate": "GeoSeal command recall, cross-language slot preservation, Stage 6 frozen eval",
    },
    "aligned_foundations": {
        "specialist_id": "aligned_foundations_specialist",
        "base_model": "Qwen/Qwen2.5-7B-Instruct",
        "method_order": ["SFT", "representation_transfer_eval"],
        "profile_candidates": [
            "config/model_training/aligned-foundations-qwen-primary.json",
            "config/model_training/chemistry-qwen-primary.json",
        ],
        "merge_weight": 0.22,
        "promotion_gate": "concept survives math/English/Sacred Tongues/binary/chemistry/coding transfer",
    },
    "operator_agent_bus": {
        "specialist_id": "operator_agent_bus_specialist",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "method_order": ["SFT", "tool_trace_eval", "DPO_optional"],
        "profile_candidates": [
            "config/model_training/operator-agent-bus-qwen-primary.json",
            "config/model_training/coding-agent-qwen-command-harmony-v5-signal-repair-v1.json",
            "config/model_training/coding-agent-qwen-command-harmony-v5.json",
            "config/model_training/ollama-agentic-handler.json",
            "config/model_training/hf-agentic-handler.json",
        ],
        "merge_weight": 0.16,
        "promotion_gate": "exact CLI recall, Stage 5 command harmony, provider-pair signaling, and fail-closed route behavior",
    },
    "governance_security": {
        "specialist_id": "governance_security_specialist",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "method_order": ["SFT", "adversarial_eval", "DPO_optional"],
        "profile_candidates": [
            "config/model_training/governance-security-qwen-primary.json",
        ],
        "merge_weight": 0.14,
        "promotion_gate": "ALLOW/QUARANTINE/ESCALATE/DENY plus invalid-input regression tests",
    },
    "research_bridge": {
        "specialist_id": "source_grounded_research_specialist",
        "base_model": "Qwen/Qwen2.5-7B-Instruct",
        "method_order": ["SFT", "citation_eval", "GRPO_optional_verifiable_claims"],
        "profile_candidates": [
            "config/model_training/research-bridge-qwen-primary.json",
        ],
        "merge_weight": 0.10,
        "promotion_gate": "source identity, falsifiable claim text, and citation-backed synthesis",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _repo_rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def build_inventory(
    output_dir: Path, *, include_kaggle: bool, include_hf: bool, include_cloud: bool
) -> dict[str, Any]:
    inventory_module = _load_module(
        REPO_ROOT / "scripts" / "training_dataset_inventory.py",
        "training_dataset_inventory",
    )
    options = inventory_module.InventoryOptions(
        output_dir=output_dir / "inventory",
        include_kaggle=include_kaggle,
        include_hf=include_hf,
        include_cloud=include_cloud,
        max_cloud_files=250,
    )
    return inventory_module.build_inventory(options)


def regularize_purposes(
    inventory_path: Path, purposes: tuple[str, ...], output_dir: Path
) -> dict[str, Any]:
    regularize_module = _load_module(
        REPO_ROOT / "scripts" / "regularize_training_bucket.py",
        "regularize_training_bucket",
    )
    manifests: dict[str, Any] = {}
    for purpose in purposes:
        manifests[purpose] = regularize_module.build_bucket(
            inventory_path, purpose, output_dir / "regularized"
        )
    return manifests


def build_specialist_plan(
    inventory: dict[str, Any],
    regularized: dict[str, Any],
    purposes: tuple[str, ...],
) -> dict[str, Any]:
    regularization_policy = _load_json(REGULARIZATION_CONFIG)
    merge_profile = _load_json(MERGE_PROFILE) if MERGE_PROFILE.exists() else {}
    summary = inventory["summary"]
    specialists = []
    for purpose in purposes:
        defaults = SPECIALIST_DEFAULTS[purpose]
        bucket = regularized[purpose]
        policy = (regularization_policy.get("model_sets") or {}).get(purpose, {})
        specialists.append(
            {
                "purpose": purpose,
                "specialist_id": defaults["specialist_id"],
                "base_model": defaults["base_model"],
                "training_methods": defaults["method_order"],
                "profile_candidates": defaults["profile_candidates"],
                "regularized_train": bucket["outputs"]["train"],
                "regularized_eval": bucket["outputs"]["eval"],
                "train_records": bucket["train_records"],
                "eval_records": bucket["eval_records"],
                "duplicates_removed": bucket["duplicates_removed"],
                "skipped_records": bucket["skipped_records"],
                "merge_weight": defaults["merge_weight"],
                "eval_gate": policy.get("eval_gate", defaults["promotion_gate"]),
                "promotion_gate": defaults["promotion_gate"],
                "status": (
                    "ready_for_training"
                    if bucket["train_records"] > 0
                    else "blocked_no_train_records"
                ),
            }
        )

    merge_weight_total = sum(float(item["merge_weight"]) for item in specialists)
    if merge_weight_total <= 0:
        raise ValueError("Specialist merge weights must sum to a positive value")
    for item in specialists:
        item["normalized_merge_weight"] = (
            float(item["merge_weight"]) / merge_weight_total
        )

    return {
        "schema_version": "scbe_ai_training_consolidation_plan_v1",
        "generated_at_utc": _utc_now(),
        "core_rule": "Train specialist adapters first, test each bucket independently, then merge only promoted adapters into a rounded model.",
        "convergence_goals": list(CONVERGENCE_GOALS),
        "training_lanes": list(TRAINING_LANES),
        "local_inventory_summary": summary,
        "open_weight_strategy": {
            "low_cost_coding": "Qwen/Qwen2.5-Coder-0.5B-Instruct for Kaggle/HF smoke and LoRA iteration",
            "larger_foundation_lane": "Qwen/Qwen2.5-7B-Instruct for aligned-foundations transfer when GPU budget allows",
            "deployment": "merge promoted LoRA adapters, then optionally convert to GGUF for local Ollama/llama.cpp testing",
        },
        "training_method_ladder": [
            "SFT for specialist behavior acquisition",
            "frozen eval and smoke tests for each specialist",
            "DPO only for preference pairs with chosen/rejected evidence",
            "GRPO only for verifiable coding/governance tasks with mechanical rewards",
            "weighted adapter merge only after specialist gates pass",
            "final smoke, benchmark, and regression eval before local GGUF export",
        ],
        "specialists": specialists,
        "final_merge": {
            "merge_profile": _repo_rel(MERGE_PROFILE),
            "merge_id": merge_profile.get("merge_id", "unconfigured"),
            "base_model": merge_profile.get(
                "base_model", "Qwen/Qwen2.5-Coder-0.5B-Instruct"
            ),
            "output_model_repo": merge_profile.get("output_model_repo", ""),
            "rule": "Do not merge a specialist adapter until its eval gate passes and its held-out set stays frozen.",
        },
        "promotion_checks": [
            *(gate["rule"] for gate in PROMOTION_GATES),
            "all selected specialist buckets have train_records > 0",
            "each specialist has an eval or explicit frozen external contract",
            "no story_lore or commerce_product records enter coding_model unless explicitly code-paired",
            "semantic gate blocks analogy/experimental lanes from acting as fact channels",
            "final model beats base on coding smoke while not regressing governance/route tests",
        ],
    }


def render_report(plan: dict[str, Any]) -> str:
    lines = [
        "# SCBE AI Training Consolidation Plan",
        "",
        f"Generated: {plan['generated_at_utc']}",
        "",
        "## Rule",
        "",
        plan["core_rule"],
        "",
        "## Inventory",
        "",
    ]
    summary = plan["local_inventory_summary"]
    lines.extend(
        [
            f"- Local files: {summary.get('local_file_count', 0)}",
            f"- Local JSONL files: {summary.get('local_jsonl_file_count', 0)}",
            f"- Known local JSONL records: {summary.get('local_known_jsonl_records', 0)}",
        ]
    )
    lines.extend(["", "## Convergence Goals", ""])
    for goal in plan.get("convergence_goals", []):
        lines.append(f"- {goal['goal_id']}: {goal['summary']}")
    lines.extend(["", "## Training Lanes", ""])
    for lane in plan.get("training_lanes", []):
        lines.append(f"- {lane['lane_id']}: {lane['purpose']}")
    lines.extend(["", "## Specialist Buckets", ""])
    for specialist in plan["specialists"]:
        lines.append(
            "- "
            f"{specialist['specialist_id']}: {specialist['train_records']} train, "
            f"{specialist['eval_records']} eval, base {specialist['base_model']}, "
            f"weight {specialist['normalized_merge_weight']:.3f}, status {specialist['status']}"
        )
    lines.extend(["", "## Training Method Ladder", ""])
    for step in plan["training_method_ladder"]:
        lines.append(f"- {step}")
    lines.extend(["", "## Promotion Checks", ""])
    for check in plan["promotion_checks"]:
        lines.append(f"- {check}")
    lines.append("")
    return "\n".join(lines)


def run(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    purposes: tuple[str, ...] = DEFAULT_PURPOSES,
    *,
    include_kaggle: bool = False,
    include_hf: bool = False,
    include_cloud: bool = False,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory = build_inventory(
        output_dir,
        include_kaggle=include_kaggle,
        include_hf=include_hf,
        include_cloud=include_cloud,
    )
    inventory_path = output_dir / "inventory" / "inventory.json"
    regularized = regularize_purposes(inventory_path, purposes, output_dir)
    plan = build_specialist_plan(inventory, regularized, purposes)
    _write_json(output_dir / "consolidation_plan.json", plan)
    (output_dir / "REPORT.md").write_text(render_report(plan), encoding="utf-8")
    return {
        "schema_version": "scbe_ai_training_consolidation_result_v1",
        "output_dir": str(output_dir),
        "inventory_path": str(inventory_path),
        "plan_path": str(output_dir / "consolidation_plan.json"),
        "report_path": str(output_dir / "REPORT.md"),
        "specialist_count": len(plan["specialists"]),
        "specialists": [
            {
                "purpose": item["purpose"],
                "specialist_id": item["specialist_id"],
                "train_records": item["train_records"],
                "eval_records": item["eval_records"],
                "status": item["status"],
            }
            for item in plan["specialists"]
        ],
    }


def _parse_purposes(value: str) -> tuple[str, ...]:
    if not value.strip():
        return DEFAULT_PURPOSES
    purposes = tuple(item.strip() for item in value.split(",") if item.strip())
    unknown = [purpose for purpose in purposes if purpose not in SPECIALIST_DEFAULTS]
    if unknown:
        raise ValueError(f"Unknown specialist purpose(s): {', '.join(unknown)}")
    return purposes


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolidate SCBE AI training buckets")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--purposes", default=",".join(DEFAULT_PURPOSES))
    parser.add_argument("--include-kaggle", action="store_true")
    parser.add_argument("--include-hf", action="store_true")
    parser.add_argument("--include-cloud", action="store_true")
    args = parser.parse_args()

    result = run(
        output_dir=Path(args.output_dir),
        purposes=_parse_purposes(args.purposes),
        include_kaggle=bool(args.include_kaggle),
        include_hf=bool(args.include_hf),
        include_cloud=bool(args.include_cloud),
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
