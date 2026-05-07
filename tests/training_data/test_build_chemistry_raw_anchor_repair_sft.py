from __future__ import annotations

import json

from scripts.training_data import build_chemistry_raw_anchor_repair_sft as builder


def test_raw_anchor_repair_records_include_observed_corrections() -> None:
    train, eval_rows = builder.build_records(repeats=2)

    assert len(train) == 30
    assert len(eval_rows) == 2
    answers = "\n".join(row["messages"][-1]["content"] for row in train)

    for good in ("carboxylic acid", "NaCl", "queue_drain_guard", "SCBE fusion", "not a molecule"):
        assert good in answers
    for bad in (
        "carboxyllic acid -> carboxylic acid",
        "NA_clathrine -> NaCl",
        "queue_drill_guard -> queue_drain_guard",
    ):
        assert bad in answers


def test_raw_anchor_manifest_records_source_job_and_pass_rates(tmp_path) -> None:
    result = builder.write_outputs(tmp_path, repeats=1)

    assert result["train_records"] == 15
    manifest = json.loads((tmp_path / builder.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "chemistry_raw_anchor_repair_manifest_v1"
    assert manifest["source_hf_job"] == "69fc98b3317220dbbd1a5d52"
    assert manifest["source_raw_pass_rate"] == 0.0
    assert manifest["source_scaffolded_pass_rate"] == 1.0
    assert any(pair["good"] == "queue_drain_guard" for pair in manifest["repair_pairs"])
