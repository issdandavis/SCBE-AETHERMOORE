#!/usr/bin/env python3
"""Plan remote-only, non-quantized adapter routing and merge candidates.

This script is intentionally conservative. It does not load models, does not
merge weights, and does not dispatch jobs. It reads the current evaluation
matrix plus LoRA drift report and tells the operator what is safe to do next.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GATE = REPO_ROOT / "config" / "model_training" / "remote_non_quantized_merge_gate_v1.json"
DEFAULT_MATRIX = REPO_ROOT / "artifacts" / "training_evaluation_matrix" / "latest.json"
DEFAULT_DRIFT = REPO_ROOT / "artifacts" / "adapter_registry" / "drift" / "latest" / "drift_report.json"
DEFAULT_OUT = REPO_ROOT / "artifacts" / "remote_merge_plans"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def gate_status(row: dict[str, Any], gate_name: str) -> str:
    for gate in row.get("gates") or []:
        if gate.get("name") == gate_name:
            return str(gate.get("status") or "unknown")
    return "missing"


def gate_value(row: dict[str, Any], gate_name: str) -> str:
    for gate in row.get("gates") or []:
        if gate.get("name") == gate_name:
            return str(gate.get("value") or "-")
    return "-"


def latest_drift_decisions(drift: dict[str, Any]) -> dict[str, Any]:
    pairs = drift.get("pairs") if isinstance(drift.get("pairs"), list) else []
    return {
        "n_pairs": len(pairs),
        "route_only_conflict_high": sum(1 for row in pairs if row.get("decision") == "route_only_conflict_high"),
        "linear_candidate": sum(1 for row in pairs if row.get("decision") == "linear_candidate"),
        "ties_candidate": sum(1 for row in pairs if row.get("decision") == "ties_candidate"),
        "dare_ties_candidate": sum(1 for row in pairs if row.get("decision") == "dare_ties_candidate"),
    }


def classify_row(row: dict[str, Any], quarantine_decisions: set[str]) -> dict[str, Any]:
    decision = str(row.get("decision") or "EVAL_REQUIRED")
    frozen = gate_status(row, "frozen_perplexity")
    dsl = gate_status(row, "dsl_executable")
    stage6 = gate_status(row, "stage6_regression")
    functional = gate_status(row, "functional_benchmark")

    route_ready = frozen == "pass" and functional == "pass" and decision not in quarantine_decisions
    merge_ready = route_ready and dsl == "pass" and stage6 == "pass"

    if decision in quarantine_decisions:
        status = "quarantine"
        reason = f"decision={decision}"
    elif merge_ready:
        status = "merge_candidate"
        reason = "all hard gates passed"
    elif route_ready:
        status = "route_candidate"
        reason = "route gates passed; merge gates still pending"
    else:
        status = "eval_required"
        missing = [
            name
            for name, value in (
                ("frozen_perplexity", frozen),
                ("dsl_executable", dsl),
                ("stage6_regression", stage6),
                ("functional_benchmark", functional),
            )
            if value in {"missing", "unknown"}
        ]
        reason = "missing=" + ",".join(missing) if missing else "hard gate not passed"

    return {
        "name": row.get("name"),
        "lane": row.get("lane"),
        "adapter": row.get("adapter"),
        "matrix_decision": decision,
        "status": status,
        "reason": reason,
        "gates": {
            "frozen_perplexity": f"{frozen} {gate_value(row, 'frozen_perplexity')}",
            "dsl_executable": f"{dsl} {gate_value(row, 'dsl_executable')}",
            "stage6_regression": f"{stage6} {gate_value(row, 'stage6_regression')}",
            "functional_benchmark": f"{functional} {gate_value(row, 'functional_benchmark')}",
        },
    }


def build_plan(gate: dict[str, Any], matrix: dict[str, Any], drift: dict[str, Any]) -> dict[str, Any]:
    quarantine_decisions = set((gate.get("promotion_gates") or {}).get("quarantine_decisions") or [])
    rows = [classify_row(row, quarantine_decisions) for row in matrix.get("rows", [])]
    drift_summary = latest_drift_decisions(drift)
    merge_candidates = [row for row in rows if row["status"] == "merge_candidate"]
    route_candidates = [row for row in rows if row["status"] == "route_candidate"]
    eval_required = [row for row in rows if row["status"] == "eval_required"]
    quarantined = [row for row in rows if row["status"] == "quarantine"]

    if not merge_candidates:
        next_action = "BLOCK_MERGE_BUILD_REPAIR_DATA"
        rationale = "No adapter has passed route + executable + Stage 6 + functional gates."
    elif drift_summary["route_only_conflict_high"]:
        next_action = "REMOTE_DARE_TIES_CANDIDATE_ONLY"
        rationale = "Some adapter pairs show high conflict; do not linear-merge."
    else:
        next_action = "REMOTE_TIES_OR_CAT_CANDIDATE"
        rationale = "Merge candidates exist and drift does not force route-only."

    return {
        "schema_version": "scbe_remote_non_quantized_merge_plan_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "gate_policy": gate.get("policy_id"),
        "local_heavy_work_allowed": False,
        "quantization_allowed": False,
        "next_action": next_action,
        "rationale": rationale,
        "foundation_goal": {
            "target": "one coding model/router that can express actions across English, Python/code, Sacred Tongues, binary, and hexadecimal forms",
            "current_best_architecture": "multi-adapter router with verifier-gated self-training; single merged artifact only after hard gates",
            "why_not_single_merge_yet": "current adapters either fail executable behavior or lack full gate evidence, and measured LoRA drift shows high sign conflict",
        },
        "drift_summary": drift_summary,
        "candidate_counts": {
            "merge_candidates": len(merge_candidates),
            "route_candidates": len(route_candidates),
            "eval_required": len(eval_required),
            "quarantined": len(quarantined),
        },
        "merge_ladder": [
            {
                "step": "router_only",
                "status": "available_after_route_gates",
                "method": "load base plus lane adapters and select adapter per prompt/task",
                "reason": "preserves learned capabilities and keeps failures reversible",
            },
            {
                "step": "cat_adapter_candidate",
                "status": "future_candidate",
                "method": "PEFT add_weighted_adapter(combination_type='cat') on gate-passing LoRAs",
                "reason": "keeps adapter subspaces separated; useful before destructive folding when ranks differ",
            },
            {
                "step": "ties_or_dare_ties_candidate",
                "status": "future_candidate",
                "method": "remote add_weighted_adapter(combination_type='ties' or 'dare_ties') with density sweep",
                "reason": "handles redundant deltas and sign conflicts better than linear averaging",
            },
            {
                "step": "full_merge_and_unload",
                "status": "blocked",
                "method": "merge into base weights only after candidate beats route baseline",
                "reason": "destructive merge would erase evidence and make regression harder to reverse",
            },
        ],
        "repair_priorities": [
            "Fix contract selector grammar: well_select(...) and tongue_shift(...) must be first-class targets.",
            "Keep bijective action examples synchronized across English, Python/code, Sacred Tongues, binary, and hexadecimal fields.",
            "Mine every unparseable_output, wrong_well, runtime_error, and Stage 6 failure into labeled repair records.",
            "Cap overrepresented translate_one examples and require floors for identify, align, governance_tag, edit_slot, multiline_edit, and dialogue.",
            "Run frozen perplexity, DSL executable, Stage 6 regression, and functional coding benchmark before route or merge promotion.",
        ],
        "rows": rows,
        "remote_dispatch_hint": {
            "status": "blocked" if next_action.startswith("BLOCK") else "candidate",
            "preferred_target": "huggingface_jobs_l4x1",
            "preferred_merge_method": "dare_ties" if drift_summary["route_only_conflict_high"] else "ties",
            "density": ((gate.get("merge_policy") or {}).get("dare_ties_default") or {}).get("density"),
            "non_quantized": True,
            "local_heavy_work": False,
        },
    }


def write_plan(plan: dict[str, Any], out_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = out_root / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    lines = [
        "# Remote Non-Quantized Merge Plan",
        "",
        f"- Generated: `{plan['generated_at_utc']}`",
        f"- Next action: `{plan['next_action']}`",
        f"- Rationale: {plan['rationale']}",
        f"- Quantization allowed: `{plan['quantization_allowed']}`",
        f"- Local heavy work allowed: `{plan['local_heavy_work_allowed']}`",
        "",
        "## Adapter Board",
        "",
        "| Run | Lane | Status | Matrix Decision | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in plan["rows"]:
        lines.append(
            f"| `{row['name']}` | `{row['lane']}` | `{row['status']}` | "
            f"`{row['matrix_decision']}` | {row['reason']} |"
        )
    lines.extend(
        [
            "",
            "## Foundation Goal",
            "",
            f"- Target: {plan['foundation_goal']['target']}",
            f"- Current best architecture: {plan['foundation_goal']['current_best_architecture']}",
            f"- Why not one merged artifact yet: {plan['foundation_goal']['why_not_single_merge_yet']}",
            "",
            "## Candidate Counts",
            "",
            "```json",
            json.dumps(plan["candidate_counts"], indent=2),
            "```",
            "",
            "## Merge Ladder",
            "",
            "| Step | Status | Method | Reason |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in plan["merge_ladder"]:
        lines.append(f"| `{row['step']}` | `{row['status']}` | {row['method']} | {row['reason']} |")
    lines.extend(
        [
            "",
            "## Repair Priorities",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in plan["repair_priorities"])
    lines.extend(
        [
            "",
            "## Drift Summary",
            "",
            "```json",
            json.dumps(plan["drift_summary"], indent=2),
            "```",
            "",
            "## Dispatch Hint",
            "",
            "```json",
            json.dumps(plan["remote_dispatch_hint"], indent=2),
            "```",
        ]
    )
    (out_dir / "plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    latest = out_root / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    (latest / "plan.json").write_text((out_dir / "plan.json").read_text(encoding="utf-8"), encoding="utf-8")
    (latest / "plan.md").write_text((out_dir / "plan.md").read_text(encoding="utf-8"), encoding="utf-8")
    return out_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--drift", type=Path, default=DEFAULT_DRIFT)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--strict-exit", action="store_true", help="Return nonzero when the merge plan is blocked.")
    args = parser.parse_args()

    gate = load_json(args.gate)
    matrix = load_json(args.matrix)
    drift = load_json(args.drift) if args.drift.exists() else {"pairs": []}
    plan = build_plan(gate, matrix, drift)
    out_dir = write_plan(plan, args.out_root)
    print(f"Plan JSON: {out_dir / 'plan.json'}")
    print(f"Plan MD:   {out_dir / 'plan.md'}")
    print(f"Next:      {plan['next_action']}")
    if args.strict_exit and plan["next_action"].startswith("BLOCK"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
