from __future__ import annotations

import json

from scripts.training_data import build_chemistry_gate_repair_sft as builder


def test_gate_repair_records_include_exact_promotion_markers() -> None:
    train, eval_rows = builder.build_records(repeats=2)

    assert len(train) == 30
    assert len(eval_rows) == 2
    answers = "\n".join(row["messages"][-1]["content"] for row in train)
    for marker in ("PASS", "DENY", "RDKit", "SCBE fusion", "valence", "not a molecule", "real atoms"):
        assert marker in answers
    assert all(row["messages"][-1]["content"].startswith("REQUIRED_MARKERS=") for row in train)


def test_gate_repair_manifest_counts_repeats(tmp_path) -> None:
    result = builder.write_outputs(tmp_path, repeats=3)

    assert result["train_records"] == 45
    assert result["eval_records"] == 2
    manifest = json.loads((tmp_path / builder.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "chemistry_gate_repair_manifest_v1"
    assert manifest["repeats"] == 3
    assert manifest["train_records"] == 45
    assert "lane_boundary" in manifest["case_ids"]
