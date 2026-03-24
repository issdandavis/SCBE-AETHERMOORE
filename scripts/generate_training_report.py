#!/usr/bin/env python3
"""Generate comprehensive training status report for HF training lane."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    root = Path(".")
    inventory = {}
    total_records = 0
    total_files = 0
    datasets_by_dir: dict = {}

    for root_dir in ["training", "training-data"]:
        for path in sorted(Path(root_dir).rglob("*.jsonl")):
            if not path.is_file():
                continue
            count = 0
            labels: set[str] = set()
            formats_seen: set[str] = set()
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            row = json.loads(line)
                        except Exception:
                            continue
                        if not isinstance(row, dict):
                            continue
                        count += 1
                        if "instruction" in row and "response" in row:
                            formats_seen.add("sft_instruction_response")
                        elif "messages" in row:
                            formats_seen.add("chat_messages")
                        elif "prompt" in row and "response" in row:
                            formats_seen.add("prompt_response")
                        elif "chosen" in row and "rejected" in row:
                            formats_seen.add("dpo")
                        else:
                            formats_seen.add("structured")
                        cat = row.get("category", "")
                        if not cat:
                            meta = row.get("meta", row.get("metadata", {}))
                            if isinstance(meta, dict):
                                cat = meta.get("source_type", meta.get("track", ""))
                        if not cat:
                            cat = row.get("event_type", row.get("dataset", ""))
                        if cat:
                            labels.add(str(cat))
            except Exception:
                continue

            dir_name = str(path.parent)
            if dir_name not in datasets_by_dir:
                datasets_by_dir[dir_name] = {"files": 0, "records": 0}
            datasets_by_dir[dir_name]["files"] += 1
            datasets_by_dir[dir_name]["records"] += count

            inventory[str(path)] = {
                "records": count,
                "formats": sorted(formats_seen),
                "unique_labels": len(labels),
                "label_sample": sorted(labels)[:10],
            }
            total_records += count
            total_files += 1

    report = {
        "report_type": "hf_training_status",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_date": "2026-03-17",
        "training_lane": {
            "name": "phdm-21d-embedding routing/classification",
            "spec_file": "docs/specs/hf_training_lane_for_scbe_agents.md",
            "model_repo": "issdandavis/phdm-21d-embedding",
            "dataset_repo": "issdandavis/scbe-aethermoore-training-data",
            "phase": "Phase 1: Deterministic routing and embedding",
            "status": "completed",
        },
        "training_run": {
            "run_id": "20260317T225643Z",
            "run_dir": "training/runs/huggingface/20260317T_phdm_routing",
            "script": "scripts/train_hf_longrun_placeholder.py",
            "hyperparameters": {
                "epochs": 12,
                "embedding_dim": 256,
                "learning_rate": 0.15,
                "val_ratio": 0.2,
                "seed": 42,
            },
            "data_stats": {
                "samples_loaded": 5240,
                "train_samples": 4192,
                "val_samples": 1048,
                "label_count": 83,
                "dedup_method": "sha256(label::text)",
            },
            "results": {
                "growth_confirmed": True,
                "val_accuracy_start": 0.0162,
                "val_accuracy_end": 0.3865,
                "val_accuracy_gain": 0.3703,
                "val_loss_start": 4.4159,
                "val_loss_end": 4.3752,
                "val_loss_drop": 0.0407,
                "best_val_accuracy": 0.3865,
                "best_epoch": 12,
            },
            "artifacts_uploaded_to_hf": [
                "training_runs/20260317T225643Z/hf_training_metrics.json",
                "training_runs/20260317T225643Z/model_weights.npz",
                "training_runs/20260317T225643Z/label_map.json",
                "training_runs/20260317T225643Z/training_growth_summary.md",
            ],
        },
        "datasets_pushed_to_hf": {
            "repo": "issdandavis/scbe-aethermoore-training-data",
            "files_uploaded": [
                {"path": "data/merged_sft.jsonl", "records": 5188, "description": "Main merged SFT dataset"},
                {"path": "data/sft/api_usage_pairs.jsonl", "records": 37, "description": "API usage instruction pairs"},
                {
                    "path": "data/npc_roundtable_sessions/npc_roundtable_sft.jsonl",
                    "records": 48,
                    "description": "NPC roundtable SFT data",
                },
                {
                    "path": "data/npc_roundtable_sessions/npc_roundtable_dpo.jsonl",
                    "records": 8,
                    "description": "NPC roundtable DPO data",
                },
                {
                    "path": "data/npc_roundtable_sessions/npc_cards.jsonl",
                    "records": 8,
                    "description": "NPC character cards",
                },
            ],
        },
        "training_data_inventory": {
            "total_jsonl_files": total_files,
            "total_records": total_records,
            "directories": {
                k: {"files": v["files"], "records": v["records"]} for k, v in sorted(datasets_by_dir.items())
            },
        },
        "top_datasets_by_size": sorted(
            [{"file": k, "records": v["records"], "formats": v["formats"]} for k, v in inventory.items()],
            key=lambda x: x["records"],
            reverse=True,
        )[:20],
        "next_steps": {
            "phase_2": "NPC style SFT training using roundtable data (48 SFT + 8 DPO records)",
            "phase_3": "DPO preference tuning after SFT stability confirmed",
            "notes": [
                "Growth confirmed (val_accuracy 0.016 -> 0.387, +37 pts)",
                "Model artifacts uploaded to issdandavis/phdm-21d-embedding",
                "83 label classes learned for routing/classification",
                "Consider increasing epochs (still improving at epoch 12)",
                "Consider augmenting NPC data before Phase 2 SFT",
            ],
        },
        "governance": {
            "deterministic_gates_preserved": True,
            "provenance_audit_complete": True,
            "promotion_decision": "hold",
            "promotion_reason": (
                "First run in routing lane. Accuracy at 38.6% across 83 classes is reasonable "
                "for a hashed-embedding softmax baseline. Hold for comparison against next run "
                "with more epochs."
            ),
        },
    }

    out_path = Path("artifacts/training/hf_training_status_2026-03-17.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote status report to {out_path}")
    print(f"Total JSONL files: {total_files}")
    print(f"Total records: {total_records}")
    print(f"Directories scanned: {len(datasets_by_dir)}")


if __name__ == "__main__":
    main()
