from __future__ import annotations

import json
from pathlib import Path

from scripts.training_data.build_coding_raw_failure_repair_sft import build_rows, write_outputs


def _gate_report() -> dict:
    return {
        "contract_id": "coding_verification_unseen_eval_v1",
        "adapter": "issdandavis/scbe-coding-primary-7b-qlora-v6f",
        "pass_rate": 1.0,
        "raw_pass_rate": 0.08333333333333333,
        "results": [
            {
                "id": "code_eval_inventory_unique_python",
                "raw_ok": True,
                "raw_missing_required": [],
                "raw_triggered_forbidden": [],
            },
            {
                "id": "code_eval_count_vowels_translate",
                "raw_ok": False,
                "raw_missing_required": ["umbroth", "haskell", "sig", "init", "loop_open", "loop_body", "ret"],
                "raw_triggered_forbidden": [],
                "raw_response": "def count_vowels(s): return 0",
            },
            {
                "id": "code_eval_lane_boundary_no_chem",
                "raw_ok": False,
                "raw_missing_required": ["queue_drain_guard", "code identifier", "definition", "unit test"],
                "raw_triggered_forbidden": ["chemistry"],
                "raw_response": "This is not chemistry.",
            },
        ],
    }


def _message_text(row: dict) -> str:
    return "\n".join(message["content"] for message in row["messages"])


def test_build_rows_extracts_raw_failures_without_exact_eval_prompt_text() -> None:
    train, eval_rows, manifest = build_rows(_gate_report())
    rows = train + eval_rows

    assert manifest["raw_failures"] == 2
    assert manifest["raw_pass_rate"] == 0.08333333333333333
    assert manifest["frozen_eval_boundary"]["copies_prompt_text"] is False
    assert manifest["frozen_eval_boundary"]["uses_analog_neighbor_tasks"] is True
    assert {row["metadata"]["failure_kind"] for row in rows} == {
        "cross_tongue_slot_translation",
        "code_chemistry_boundary",
    }

    text = "\n".join(_message_text(row) for row in rows)
    assert "count the number of vowels in a string" not in text
    assert "queue_drain_guard" not in text
    assert "count_digits" in text
    assert "cache_flush_guard" in text


def test_write_outputs_creates_repair_shard_and_manifest(tmp_path: Path) -> None:
    result = write_outputs(_gate_report(), tmp_path)

    assert result["ok"] is True
    assert result["raw_failures"] == 2
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "coding_raw_failure_repair_manifest_v1"
    assert manifest["train_records"] == result["train_records"]
    assert manifest["source_prompt_ids"] == [
        "code_eval_count_vowels_translate",
        "code_eval_lane_boundary_no_chem",
    ]
    train_rows = [
        json.loads(line)
        for line in Path(result["train_path"]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert train_rows
    assert train_rows[0]["messages"][0]["content"].startswith(
        "You are an SCBE-AETHERMOORE coding repair tutor"
    )
    assert train_rows[0]["metadata"]["frozen_eval_boundary"] == "no held-out prompt text copied into messages"
