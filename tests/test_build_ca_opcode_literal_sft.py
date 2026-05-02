from __future__ import annotations

from scripts.build_ca_opcode_literal_sft import build_rows


def test_literal_sft_contains_exact_ca_sequence_and_smoke_preservation() -> None:
    train, holdout = build_rows()
    assert len(train) == 126
    assert len(holdout) == 4
    ca_rows = [row for row in train if row["meta"]["kind"] == "ca_abs_add_exact_literal"]
    assert ca_rows
    assert all("0x09, 0x09, 0x00" in row["messages"][-1]["content"] for row in ca_rows)
    kinds = {row["meta"]["kind"] for row in train}
    assert "python_smoke_preservation" in kinds
