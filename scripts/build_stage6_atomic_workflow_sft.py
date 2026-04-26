"""Build Stage 6 SFT records for atomic workflow/resource-decay training.

Stage 6 is intentionally downstream of command harmony. It converts verified
artifact records into normal chat SFT rows while preserving the shared
token -> hex/binary -> lane flow used by the coding-agent profiles.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SFT_ROOT = REPO_ROOT / "training-data" / "sft"
SEMANTIC_WORKFLOWS = (
    REPO_ROOT
    / "artifacts"
    / "mathbac"
    / "atomic_tokenizer_rename_benchmark"
    / "semantic_chemistry_workflows.jsonl"
)
RESOURCE_DECAY_DEMO = (
    REPO_ROOT
    / "artifacts"
    / "mathbac"
    / "atomic_workflow_composition"
    / "mars_drone_resource_decay_demo.json"
)
TRAIN_OUT = SFT_ROOT / "atomic_workflow_stage6_train.sft.jsonl"
EVAL_OUT = SFT_ROOT / "atomic_workflow_stage6_holdout.sft.jsonl"
MANIFEST_OUT = SFT_ROOT / "atomic_workflow_stage6_manifest.json"

SYSTEM_PROMPT = (
    "You are an SCBE GeoSeal coding-agent tutor. Preserve the same token to binary/hex flow across code, "
    "semantic overlay, structural chemistry frame, and resource-aware workflow composition. Keep material "
    "chemistry separate from structural chemistry templates."
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _top_features(feature: dict[str, Any], prefix: str, limit: int = 6) -> list[tuple[str, float]]:
    pairs = [
        (key, float(value))
        for key, value in feature.items()
        if key.startswith(prefix) and isinstance(value, (int, float)) and float(value) > 0
    ]
    return sorted(pairs, key=lambda item: (-item[1], item[0]))[:limit]


def _semantic_workflow_to_sft(row: dict[str, Any]) -> dict[str, Any]:
    chemistry = row["lanes"]["chemistry_actual"]["feature"]
    semantic = row["lanes"]["semantic_overlay"]["feature"]
    flow = row["lanes"]["flow_reinforcement"]["feature"]
    prompt = (
        f"Map this {row['primary']} code sample for concept `{row['concept']}` through the shared Stage 6 flow. "
        "Return the token-to-hex chain, lane summaries, and training-safe interpretation."
    )
    response = {
        "concept": row["concept"],
        "primary": row["primary"],
        "source_sha256": row["source_sha256"],
        "token_hex_element_chain": row["workflow_chain"],
        "chemistry_actual_summary": {
            "mapping": row["lanes"]["chemistry_actual"]["mapping"],
            "bit_density": chemistry.get("bit_density"),
            "byte_count_log": chemistry.get("byte_count_log"),
            "top_elements": _top_features(chemistry, "element_"),
            "top_high_nibbles": _top_features(chemistry, "high_nibble_"),
            "top_low_nibbles": _top_features(chemistry, "low_nibble_"),
        },
        "semantic_overlay_summary": {
            "mapping": row["lanes"]["semantic_overlay"]["mapping"],
            "token_count": semantic.get("token_count"),
            "dominant_classes": _top_features(semantic, "class_"),
            "tau": {
                key.removeprefix("tau_"): value
                for key, value in semantic.items()
                if key.startswith("tau_")
            },
        },
        "flow_reinforcement_summary": {
            "mapping": row["lanes"]["flow_reinforcement"]["mapping"],
            "dominant_keywords": _top_features(flow, "kw_"),
            "line_count_log": flow.get("line_count_log"),
            "avg_token_len": flow.get("avg_token_len"),
        },
        "interpretation": (
            "Use the structural byte/hex lane and semantic overlay as separate evidence lanes. "
            "Do not claim material chemistry unless direct chemical symbols or reactions are present."
        ),
    }
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": json.dumps(response, ensure_ascii=False, sort_keys=True)},
        ],
        "meta": {
            "stage": "stage6_atomic_workflow",
            "source_schema": row.get("schema_version"),
            "kind": "semantic_chemistry_workflow",
            "concept": row["concept"],
            "primary": row["primary"],
        },
    }


def _resource_decay_to_sft(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    summary = {
        "version": report["version"],
        "decision": report["decision"],
        "budget": report["budget"],
        "spent": report["spent"],
        "degradation_count": len(report.get("degradation_events", [])),
        "readvance_count": len(report.get("readvance_attempts", [])),
        "rule": (
            "Predict budget overrun before commit, cancel into steady-state fallback, damp momentum, "
            "then attempt re-advance from a cheaper footing."
        ),
    }
    rows.append(
        {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "Summarize the Stage 6 Mars-drone resource-decay workflow and its fallback rule.",
                },
                {"role": "assistant", "content": json.dumps(summary, ensure_ascii=False, sort_keys=True)},
            ],
            "meta": {"stage": "stage6_atomic_workflow", "kind": "resource_decay_summary"},
        }
    )
    for event in report.get("degradation_events", []):
        matching = [
            item
            for item in report.get("readvance_attempts", [])
            if item.get("index") == event.get("index")
        ]
        payload = {
            "token": event["token"],
            "index": event["index"],
            "blocked_resources": event["blocked_resources"],
            "available": event["available"],
            "spent_before": event["spent_before"],
            "attempted_cost": event["cost"],
            "fallback": event["fallback"],
            "momentum_before": event.get("momentum_before"),
            "momentum_after": event.get("momentum_after"),
            "readvance_attempts": matching,
            "decision": "cancel_commit_damp_and_readvance" if matching else "cancel_commit_and_hold",
        }
        rows.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Explain the steady-state fallback decision for blocked token `{event['token']}`.",
                    },
                    {"role": "assistant", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
                ],
                "meta": {
                    "stage": "stage6_atomic_workflow",
                    "kind": "resource_decay_event",
                    "token": event["token"],
                },
            }
        )
    return rows


def build() -> dict[str, Any]:
    semantic_rows = [_semantic_workflow_to_sft(row) for row in _read_jsonl(SEMANTIC_WORKFLOWS)]
    resource_report = (
        json.loads(RESOURCE_DECAY_DEMO.read_text(encoding="utf-8"))
        if RESOURCE_DECAY_DEMO.exists()
        else {}
    )
    resource_rows = _resource_decay_to_sft(resource_report) if resource_report else []
    all_rows = semantic_rows + resource_rows
    train_rows = [row for index, row in enumerate(all_rows) if index % 7 != 0]
    eval_rows = [row for index, row in enumerate(all_rows) if index % 7 == 0]
    _write_jsonl(TRAIN_OUT, train_rows)
    _write_jsonl(EVAL_OUT, eval_rows)
    manifest = {
        "schema_version": "atomic_workflow_stage6_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "semantic_workflows": str(SEMANTIC_WORKFLOWS),
            "resource_decay_demo": str(RESOURCE_DECAY_DEMO),
        },
        "outputs": {"train": str(TRAIN_OUT), "eval": str(EVAL_OUT)},
        "counts": {
            "semantic_workflow": len(semantic_rows),
            "resource_decay": len(resource_rows),
            "train": len(train_rows),
            "eval": len(eval_rows),
            "total": len(all_rows),
        },
        "training_rule": "Stage 6 only; do not mix into earlier coding-agent profiles before promotion.",
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, ensure_ascii=True))

