from __future__ import annotations

import pytest

from python.scbe.semantic_opcode_vm import (
    SemanticOpcodeError,
    assemble,
    disassemble_text,
    opcode_table,
    run_program,
)


def test_opcode_table_has_family_partition_and_contracts() -> None:
    table = opcode_table()
    by_token = {row["token"]: row for row in table}

    assert by_token["LOAD"]["opcode"] == 0x01
    assert by_token["VERIFY"]["opcode"] == 0x82
    assert by_token["MERGE"]["opcode"] == 0xC1
    assert by_token["HALT"]["opcode"] == 0xFF
    assert by_token["MERGE"]["verification_rule"] == "dst equals packed nibbles"


def test_assembler_disassembler_round_trips_token_program() -> None:
    program = "LOAD A 0x41; LOAD B 0x41; COMPARE A B; VERIFY; HALT"
    blob = assemble(program)

    assert blob.hex().startswith("01020141")
    assert disassemble_text(blob) == [
        "LOAD A 0x41",
        "LOAD B 0x41",
        "COMPARE A B",
        "VERIFY",
        "HALT",
    ]


def test_semantic_opcode_vm_executes_minimum_verified_program() -> None:
    receipt = run_program("LOAD A 7; LOAD B 7; COMPARE A B; VERIFY; HALT")

    assert receipt["schema"] == "scbe_semantic_opcode_vm_receipt_v1"
    assert receipt["status"] == "PASS"
    assert receipt["verified"] is True
    assert receipt["registers"]["A"] == 7
    assert receipt["program_tokens"] == ["LOAD", "LOAD", "COMPARE", "VERIFY", "HALT"]
    assert receipt["cost"]["cost_accounting"] == "direct"
    assert receipt["cost"]["total_evaluations"] == 5


def test_semantic_opcode_vm_failed_verify_is_cost_honest() -> None:
    receipt = run_program("LOAD A 7; LOAD B 8; COMPARE A B; VERIFY; HALT")

    assert receipt["status"] == "FAIL"
    assert receipt["verified"] is False
    assert receipt["trace"][3]["verified"] is False
    assert receipt["cost"]["total_evaluations"] == receipt["cost"]["evaluations"]


def test_semantic_opcode_vm_rejects_blurry_unknown_tokens() -> None:
    with pytest.raises(SemanticOpcodeError, match="unknown semantic token"):
        assemble("MERGE_AND_APPROVE A B")


def test_semantic_merge_and_split_have_sharp_byte_behavior() -> None:
    receipt = run_program("LOAD A 0xAB; SPLIT A B C; MERGE D B C; COMPARE A D; VERIFY; HALT")

    assert receipt["verified"] is True
    assert receipt["registers"]["B"] == 0x0A
    assert receipt["registers"]["C"] == 0x0B
    assert receipt["registers"]["D"] == 0xAB
