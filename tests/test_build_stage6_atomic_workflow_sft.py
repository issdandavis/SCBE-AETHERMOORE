from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_stage6_atomic_workflow_sft.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_stage6_atomic_workflow_sft", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stage6_builder_emits_gated_chat_sft_rows(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    sft_root = tmp_path / "training-data" / "sft"
    semantic_path = tmp_path / "semantic_chemistry_workflows.jsonl"
    resource_path = tmp_path / "mars_drone_resource_decay_demo.json"
    train_out = sft_root / "atomic_workflow_stage6_train.sft.jsonl"
    eval_out = sft_root / "atomic_workflow_stage6_holdout.sft.jsonl"
    manifest_out = sft_root / "atomic_workflow_stage6_manifest.json"

    semantic_row = {
        "schema_version": "semantic_chemistry_workflow_v1",
        "concept": "mirror_check",
        "primary": "KO",
        "source_sha256": "abc123",
        "workflow_chain": "mirror_check[6D.69|N-La]",
        "lanes": {
            "chemistry_actual": {
                "mapping": "byte -> binary_interpretation_matrix.hex -> periodic_element",
                "feature": {
                    "bit_density": 0.5,
                    "byte_count_log": 2.0,
                    "element_N": 0.6,
                    "high_nibble_6": 1.0,
                    "low_nibble_D": 1.0,
                },
            },
            "semantic_overlay": {
                "mapping": "source token -> current atomic tokenizer semantic state",
                "feature": {"token_count": 1, "class_ENTITY": 1.0, "tau_KO": 1.0},
            },
            "flow_reinforcement": {
                "mapping": "source text -> operational control and syntax shape",
                "feature": {"kw_return": 1.0, "line_count_log": 1.0, "avg_token_len": 6.0},
            },
        },
    }
    semantic_path.write_text(json.dumps(semantic_row) + "\n", encoding="utf-8")
    resource_path.write_text(
        json.dumps(
            {
                "version": "atomic_workflow_composition_demo_v1",
                "decision": "steady_state_fallback",
                "budget": {"power": 1.0},
                "spent": {"power": 0.8},
                "degradation_events": [
                    {
                        "index": 0,
                        "token": "sample",
                        "blocked_resources": ["power"],
                        "available": {"power": 0.2},
                        "spent_before": {"power": 0.8},
                        "cost": {"power": 0.5},
                        "fallback": "hold",
                        "momentum_before": 1.0,
                        "momentum_after": 0.35,
                    }
                ],
                "readvance_attempts": [{"index": 0, "token": "sample", "result": "accepted"}],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "SEMANTIC_WORKFLOWS", semantic_path)
    monkeypatch.setattr(module, "RESOURCE_DECAY_DEMO", resource_path)
    monkeypatch.setattr(module, "TRAIN_OUT", train_out)
    monkeypatch.setattr(module, "EVAL_OUT", eval_out)
    monkeypatch.setattr(module, "MANIFEST_OUT", manifest_out)

    manifest = module.build()

    assert manifest["counts"] == {"semantic_workflow": 1, "resource_decay": 2, "train": 2, "eval": 1, "total": 3}
    assert "Stage 6 only" in manifest["training_rule"]
    all_rows = [
        json.loads(line)
        for path in (train_out, eval_out)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert all("messages" in row for row in all_rows)
    assistant_payloads = [json.loads(row["messages"][-1]["content"]) for row in all_rows]
    serialized = json.dumps(assistant_payloads)
    assert "token_hex_element_chain" in serialized
    assert "steady-state fallback" in serialized or "steady_state_fallback" in serialized
    assert "Do not claim material chemistry" in serialized
