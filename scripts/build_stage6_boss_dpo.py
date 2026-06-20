#!/usr/bin/env python3
"""Build Stage 6 boss-retry DPO preference data from a failed gate plan."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = REPO_ROOT / "artifacts" / "model_training" / "stage6-v12-boss-retry-plan.json"
DEFAULT_CONTRACT = REPO_ROOT / "config" / "model_training" / "stage6_atomic_workflow_eval_contract.json"
DEFAULT_OUT = REPO_ROOT / "training-data" / "dpo" / "stage6_boss_retry_v1_train.jsonl"
DEFAULT_MANIFEST = REPO_ROOT / "training-data" / "dpo" / "stage6_boss_retry_v1_manifest.json"

SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE GeoSeal coding agent. Keep byte/hex substrate, semantic workflow, "
    "resource budgets, and training-boundary governance in separate lanes. Use required-token checklists "
    "before prose when a gate asks for exact route evidence."
)

ANALOGS: dict[str, list[dict[str, Any]]] = {
    "byte_hex_compute_trace": [
        {"token": "parity_patch", "role": "checksum repair action", "budget": "compute=0.09", "decision": "hold"},
        {"token": "drift_crc", "role": "telemetry error-repair action", "budget": "compute=0.11", "decision": "hold"},
        {
            "token": "cache_mend",
            "role": "route-table error-repair action",
            "budget": "compute=0.07",
            "decision": "hold",
        },
        {
            "token": "delta_repair",
            "role": "state-diff error-repair action",
            "budget": "compute=0.12",
            "decision": "hold",
        },
    ],
    "multi_budget_cost_propagation": [
        {"actions": ["image_crater", "filter_static", "uplink_digest"]},
        {"actions": ["probe_shadow", "compress_noise", "send_summary"]},
        {"actions": ["scan_lava_tube", "stabilize_map", "relay_packet"]},
        {"actions": ["sample_regolith", "reduce_jitter", "send_digest"]},
    ],
    "heldout_boundary_pollution_control": [
        {"stage": "Stage 6", "prior": "command-harmony-v5", "topic": "route-cost repair rows"},
        {"stage": "Stage 6", "prior": "command-harmony-v5", "topic": "atomic workflow preference rows"},
        {"stage": "Stage 6", "prior": "command-harmony-v5", "topic": "byte/hex scaffold rows"},
        {"stage": "Stage 6", "prior": "command-harmony-v5", "topic": "GeoSeal boss retry rows"},
    ],
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _jsonl_write(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=True) for row in rows) + "\n", encoding="utf-8")


def _contains_contract_prompt(row: dict[str, Any], frozen_prompts: list[str]) -> bool:
    blob = json.dumps(row, ensure_ascii=False)
    return any(prompt and prompt in blob for prompt in frozen_prompts)


def _hex_for(token: str) -> str:
    return ".".join(f"{byte:02X}" for byte in token.encode("utf-8"))


def _row(
    *,
    target: dict[str, Any],
    prompt: str,
    chosen: str,
    rejected: str,
    variant: int,
    analog: dict[str, Any],
) -> dict[str, Any]:
    return {
        "prompt": prompt,
        "chosen": chosen,
        "rejected": rejected,
        "system": SYSTEM_PROMPT,
        "meta": {
            "schema": "stage6_boss_retry_dpo_v1",
            "source_plan": "geoseal_stage6_boss_retry_plan_v1",
            "target_id": target["id"],
            "failure_kind": target["kind"],
            "missing_required": target.get("missing_required", []),
            "must_pass": bool(target.get("must_pass")),
            "variant": variant,
            "analog": analog,
        },
    }


def _hex_trace_rows(target: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, analog in enumerate(ANALOGS["byte_hex_compute_trace"]):
        token = analog["token"]
        prompt = (
            f"Trace the token {token} through Stage 6. Include byte/hex substrate, its role as "
            f"an error-repair workflow action, and the route decision when {analog['budget']} is insufficient."
        )
        chosen = (
            f"required-tokens: `{token}` | byte | hex | error-repair | compute | hold | re-advance ::\n"
            f"`{token}` is first kept in the byte lane and hex lane as `{_hex_for(token)}`. "
            f"The semantic lane treats it as an {analog['role']}. Because {analog['budget']} is insufficient, "
            f"GeoSeal should {analog['decision']} the action, preserve the partial route state, and only "
            "re-advance from a cheaper compute footing."
        )
        rejected = (
            f"`{token}` is an error-repair workflow action with byte and hex evidence `{_hex_for(token)}`. "
            "The system can continue normally and re-advance later."
        )
        rows.append(_row(target=target, prompt=prompt, chosen=chosen, rejected=rejected, variant=idx, analog=analog))
    return rows


def _cost_rows(target: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, analog in enumerate(ANALOGS["multi_budget_cost_propagation"]):
        actions = analog["actions"]
        prompt = (
            f"Given action units {actions[0]}, {actions[1]}, and {actions[2]}, explain how Stage 6 "
            "propagates power, compute, time, comms, and wear costs before final launch."
        )
        chosen = (
            f"required-tokens: `{actions[0]}` | `{actions[1]}` | `{actions[2]}` | power | compute | time | comms | wear ::\n"
            f"Stage 6 evaluates `{actions[0]}`, `{actions[1]}`, and `{actions[2]}` as separate action units. "
            "Each unit contributes power, compute, time, comms, and wear cost before final launch. "
            "If any propagated lane overruns, the route holds or falls back instead of always launching."
        )
        rejected = (
            "Stage 6 reviews the workflow at a high level and then launches if the semantic goal is useful. "
            "Budget details can be handled after execution."
        )
        rows.append(_row(target=target, prompt=prompt, chosen=chosen, rejected=rejected, variant=idx, analog=analog))
    return rows


def _boundary_rows(target: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, analog in enumerate(ANALOGS["heldout_boundary_pollution_control"]):
        stage = analog["stage"]
        prior = analog["prior"]
        prompt = f"Explain why {stage} {analog['topic']} must stay gated after {prior} and not be mixed into earlier profiles."
        chosen = (
            f"required-tokens: {stage} | gated | {prior} | held-out | pollution ::\n"
            f"{stage} rows stay gated after {prior} because the held-out gate must measure real transfer. "
            "Mixing these rows into earlier profiles causes pollution, weakens promotion evidence, and hides "
            "whether the agent can use the GeoSeal route under the same frozen contract."
        )
        rejected = (
            f"{stage} data should be merged into every profile so all models see the same examples. "
            "That makes training easier and avoids needing a separate eval."
        )
        rows.append(_row(target=target, prompt=prompt, chosen=chosen, rejected=rejected, variant=idx, analog=analog))
    return rows


def build_rows(plan: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    frozen_prompts = [str(item.get("prompt", "")) for item in contract.get("prompts", []) if isinstance(item, dict)]
    rows: list[dict[str, Any]] = []
    for target in plan.get("repair_targets", []):
        if not isinstance(target, dict):
            continue
        kind = str(target.get("kind") or "")
        if kind == "byte_hex_compute_trace":
            base_rows = _hex_trace_rows(target)
        elif kind == "multi_budget_cost_propagation":
            base_rows = _cost_rows(target)
        elif kind == "heldout_boundary_pollution_control":
            base_rows = _boundary_rows(target)
        else:
            continue
        recommended = int(target.get("recommended_rows") or len(base_rows))
        if recommended <= 0:
            continue
        repeats = (recommended + len(base_rows) - 1) // len(base_rows)
        expanded = (base_rows * repeats)[:recommended]
        rows.extend(expanded)
    leaked = [idx for idx, row in enumerate(rows) if _contains_contract_prompt(row, frozen_prompts)]
    if leaked:
        raise ValueError(f"refusing to write rows that copy frozen eval prompt text: {leaked[:5]}")
    return rows


def build_manifest(rows: list[dict[str, Any]], plan: dict[str, Any], out_path: Path) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    for row in rows:
        kind = str((row.get("meta") or {}).get("failure_kind") or "")
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return {
        "schema_version": "stage6_boss_retry_dpo_manifest_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_plan": plan.get("source", ""),
        "source_profile_id": plan.get("profile_id", ""),
        "output_path": str(out_path),
        "row_count": len(rows),
        "rows_by_failure_kind": by_kind,
        "training_boundary": {
            "rule": "Analog repair rows only; frozen eval prompt text is not copied into DPO data.",
            "frozen_contract": str(DEFAULT_CONTRACT),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", default=str(DEFAULT_PLAN))
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    contract_path = Path(args.contract)
    out_path = Path(args.output)
    manifest_path = Path(args.manifest)
    plan = _load_json(plan_path)
    contract = _load_json(contract_path)
    rows = build_rows(plan, contract)
    _jsonl_write(out_path, rows)
    manifest = build_manifest(rows, plan, out_path)
    manifest["plan_path"] = str(plan_path)
    manifest["contract_path"] = str(contract_path)
    _write_json(manifest_path, manifest)
    if args.json:
        print(json.dumps(manifest, indent=2, ensure_ascii=True))
    else:
        print(f"wrote {len(rows)} DPO rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
