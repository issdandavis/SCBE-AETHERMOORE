from __future__ import annotations

from scripts.build_ca_opcode_final_dpo import build_rows


def test_ca_opcode_final_dpo_rows_keep_exact_sequence_in_chosen() -> None:
    rows = build_rows()
    assert len(rows) == 160
    assert all("0x09, 0x09, 0x00" in row["chosen"] for row in rows)
    assert all("add" in row["chosen"].lower() for row in rows)


def test_ca_opcode_final_dpo_rejected_rows_include_observed_failure_shapes() -> None:
    rows = build_rows()
    rejected = "\n".join(row["rejected"] for row in rows)
    assert "CA: 0x09\nOPCODES: abs(a), abs(b), add" in rejected
    assert "0x09, 0x09, 0x09" in rejected
    assert "0x09, 0x09\nops" in rejected
