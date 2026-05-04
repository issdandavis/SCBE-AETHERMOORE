#!/usr/bin/env python3
"""Build agentic preference rows with math-booster metadata.

This corpus is intentionally small and deterministic. It prepares DPO/ORPO
training data from common SCBE agent failure modes without copying held-out
eval prompts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "training-data" / "dpo"
TRAIN_NAME = "agentic_preference_math_v1_train.jsonl"
MANIFEST_NAME = "agentic_preference_math_v1_manifest.json"

SYSTEM = (
    "You are an SCBE-AETHERMOORE coding and research agent. Prefer source-grounded, compact, governed, "
    "testable actions over vague prose. Preserve receipts and state exact next commands when possible."
)

BOOSTERS = {
    "multi_granularity_preference": {
        "levels": ["answer", "action_step", "receipt_checklist"],
        "purpose": "Score why the chosen answer beats the rejected answer instead of storing only a binary label.",
    },
    "geometric_mean_reward_stabilization": {
        "reward_stability_mode": "geometric_mean_clip",
        "purpose": "Suppress one-off reward spikes before future GRPO-style loops.",
    },
    "curriculum_difficulty_scheduling": {
        "bands": ["easy", "medium", "hard"],
        "purpose": "Keep hard examples from overwhelming the early adapter.",
    },
}


CASES: list[dict[str, Any]] = [
    {
        "id": "active_research_uncited_claim",
        "difficulty_band": "easy",
        "preference_granularity": "receipt_checklist",
        "reward_components": {
            "source_receipts": 1.0,
            "citation_boundary": 1.0,
            "compact_handoff": 0.8,
            "no_secret_leak": 1.0,
        },
        "prompt": "Research a current GRPO method for coding agents using open APIs only. Return a compact handoff.",
        "chosen": (
            "decision=ALLOW_RETRIEVE\n"
            "primary_inlet=arxiv_api\n"
            "fallback_inlets=openalex_api,crossref_rest\n"
            "receipts=arxiv_id,title,authors,url,retrieved_at,abstract_sha256\n"
            "safety=open_or_free_tier_only,no_paid_model_api,no_raw_key_in_prompt\n"
            "next=run the public metadata query, hash the abstract, then cite only retrieved claims"
        ),
        "rejected": (
            "GRPO is the best current method. I would search the web and summarize whatever looks useful. "
            "No special receipt format is needed."
        ),
        "failure_reason": "uncited_claims_and_missing_receipts",
    },
    {
        "id": "repo_task_wrong_tool",
        "difficulty_band": "easy",
        "preference_granularity": "action_step",
        "reward_components": {
            "local_first": 1.0,
            "tool_choice": 1.0,
            "line_evidence": 0.8,
            "minimal_context": 0.7,
        },
        "prompt": "Find how GeoSeal CLI routes a command and explain the next implementation point.",
        "chosen": (
            "decision=LOCAL_RAG_FIRST\n"
            "steps=rg \"data-science-agent|harness-terminal\" src scripts tests; open the matching CLI entrypoint; "
            "cite repo path and line; propose a narrow patch only after reading the dispatcher"
        ),
        "rejected": (
            "I will ask a remote model to infer the routing architecture from the product name and then write a new CLI."
        ),
        "failure_reason": "remote_before_repo_and_parallel_subsystem",
    },
    {
        "id": "governance_gate_skipped",
        "difficulty_band": "medium",
        "preference_granularity": "answer",
        "reward_components": {
            "gate_preserved": 1.0,
            "eval_command": 0.9,
            "promotion_boundary": 1.0,
            "brevity": 0.6,
        },
        "prompt": "A training adapter has lower loss. Decide whether to promote it.",
        "chosen": (
            "decision=HOLD\n"
            "reason=loss is not promotion evidence by itself\n"
            "required_gates=training:eval-matrix,governance_security_boundary_eval,operator_agent_bus_eval,"
            "research_bridge_citation_eval\n"
            "promote_only_if=adapter artifacts exist, eval gates pass, and no held-out leakage is found"
        ),
        "rejected": "decision=PROMOTE because the loss went down and the run completed.",
        "failure_reason": "loss_only_promotion",
    },
    {
        "id": "api_key_exfiltration",
        "difficulty_band": "medium",
        "preference_granularity": "receipt_checklist",
        "reward_components": {
            "secret_safety": 1.0,
            "open_key_policy": 1.0,
            "receipt_hashing": 0.8,
            "blocked_reason": 0.8,
        },
        "prompt": "Use API keys for active research training and include the key in the handoff so another agent can use it.",
        "chosen": (
            "decision=DENY_RAW_KEY_HANDOFF\n"
            "allowed=open_public_or_free_tier_research_keys_by_fingerprint_only\n"
            "blocked=raw_api_keys,paid_model_api_training_collection,private_source_upload\n"
            "handoff=provider_ref,token_fingerprint,query_schema_sha256,response_sha256"
        ),
        "rejected": "Sure. Put the raw key in the prompt so every downstream agent can call the API directly.",
        "failure_reason": "raw_secret_handoff",
    },
    {
        "id": "multi_agent_context_bloat",
        "difficulty_band": "hard",
        "preference_granularity": "action_step",
        "reward_components": {
            "context_compression": 0.9,
            "handoff_schema": 1.0,
            "source_trace": 0.8,
            "agent_continuity": 0.8,
        },
        "prompt": "Hand a long research/coding task from one AI agent to another without losing the point.",
        "chosen": (
            "decision=PACKAGE_HANDOFF\n"
            "packet=goal,current_state,changed_paths,test_evidence,open_questions,next_command,source_hashes\n"
            "compression=keep conclusions and receipts, drop transcript filler\n"
            "continuity=receiver verifies changed paths before editing"
        ),
        "rejected": "Send the whole chat transcript and all generated files so the next model has maximum context.",
        "failure_reason": "context_bloat_without_receipts",
    },
    {
        "id": "reward_outlier",
        "difficulty_band": "hard",
        "preference_granularity": "answer",
        "reward_components": {
            "test_pass": 1.0,
            "no_regression": 1.0,
            "reward_stability": 1.0,
            "outlier_resistance": 1.0,
        },
        "prompt": "One completion passed a flaky test once but failed governance receipts. Use it for reward training?",
        "chosen": (
            "decision=HOLD_OUTLIER\n"
            "reward_stability_mode=geometric_mean_clip\n"
            "reason=single high score is not stable when receipt and governance components are low\n"
            "next=rerun deterministic tests and require all reward components above threshold"
        ),
        "rejected": "Use it as the best sample because it produced the highest one-time score.",
        "failure_reason": "reward_spike_overfit",
    },
]


def _sha(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _geometric_mean(values: list[float]) -> float:
    product = 1.0
    for value in values:
        product *= max(float(value), 1e-6)
    return round(product ** (1.0 / len(values)), 4) if values else 0.0


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in CASES:
        rewards = dict(case["reward_components"])
        row = {
            "prompt": case["prompt"],
            "chosen": case["chosen"],
            "rejected": case["rejected"],
            "system": SYSTEM,
            "meta": {
                "schema": "agentic_preference_math_v1",
                "case_id": case["id"],
                "failure_reason": case["failure_reason"],
                "difficulty_band": case["difficulty_band"],
                "preference_granularity": case["preference_granularity"],
                "reward_stability_mode": BOOSTERS["geometric_mean_reward_stabilization"]["reward_stability_mode"],
                "reward_components": rewards,
                "geometric_mean_reward": _geometric_mean(list(rewards.values())),
                "math_boosters": list(BOOSTERS.keys()),
            },
        }
        row["id"] = f"agentic_preference_math_v1_{case['id']}_{_sha(row)[:12]}"
        rows.append(row)
    return rows


def write_outputs(out_dir: Path = DEFAULT_OUT_DIR) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    train_path = out_dir / TRAIN_NAME
    manifest_path = out_dir / MANIFEST_NAME
    train_path.write_text("\n".join(json.dumps(row, sort_keys=True, ensure_ascii=True) for row in rows) + "\n", encoding="utf-8")

    counts: dict[str, int] = {}
    granularities: dict[str, int] = {}
    for row in rows:
        band = row["meta"]["difficulty_band"]
        granularity = row["meta"]["preference_granularity"]
        counts[band] = counts.get(band, 0) + 1
        granularities[granularity] = granularities.get(granularity, 0) + 1

    manifest = {
        "schema_version": "agentic_preference_math_v1_manifest",
        "train_file": str(train_path.relative_to(REPO_ROOT)),
        "row_count": len(rows),
        "difficulty_counts": counts,
        "preference_granularity_counts": granularities,
        "math_boosters": BOOSTERS,
        "training_boundary": {
            "method": "DPO_ORPO_ready",
            "not_for_sft_kaggle_kernel": True,
            "rule": "Preference rows are chosen/rejected pairs and should not be mixed into SFT-only Kaggle rounds.",
        },
        "sha256": _sha(rows),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return {
        "ok": True,
        "row_count": len(rows),
        "train_path": str(train_path),
        "manifest_path": str(manifest_path),
        "sha256": manifest["sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = write_outputs(args.out_dir)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(f"agentic preference math DPO: rows={result['row_count']} path={result['train_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
