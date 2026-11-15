"""Exact token masks compiled through the existing semantic opcode VM."""

from __future__ import annotations

from copy import deepcopy

import pytest

from python.scbe.eot_token_lattice import (
    TokenProbability,
    TokenTableDistribution,
    build_interwoven_eot_lattice,
)
from python.scbe.token_action_lithography import (
    ActionTokenBinding,
    TokenActionLithographyError,
    compile_token_action_mask,
    verify_token_action_mask,
)


def _fixture() -> tuple[dict, tuple[ActionTokenBinding, ...]]:
    rows = (
        (0, b"load-a", "LOAD", ("A", "7")),
        (1, b"load-b", "LOAD", ("B", "7")),
        (2, b"compare", "COMPARE", ("A", "B")),
        (3, b"verify", "VERIFY", ()),
        (4, b"halt", "HALT", ()),
    )
    table = TokenTableDistribution(
        "action-table",
        tuple(TokenProbability(token_id, raw.hex(), 0.2, semantic_token) for token_id, raw, semantic_token, _ in rows),
    )
    bindings = tuple(
        ActionTokenBinding(
            table_id=table.table_id,
            token_id=token_id,
            byte_hex=raw.hex(),
            semantic_token=semantic_token,
            operands=operands,
        )
        for token_id, raw, semantic_token, operands in rows
    )
    return build_interwoven_eot_lattice((table,)), bindings


def test_explicit_token_mask_round_trips_and_executes_existing_vm() -> None:
    lattice, bindings = _fixture()
    receipt = compile_token_action_mask(
        lattice,
        bindings,
        execute=True,
        projection_receipt_sha256="a" * 64,
    )
    assert receipt["program"]["disassembly_roundtrip_exact"] is True
    assert receipt["program"]["isa_profile"] == "semantic-vm-v1"
    assert receipt["program"]["instruction_count"] == 5
    assert [row["opcode"] for row in receipt["mask"]] == [1, 1, 32, 130, 255]
    assert receipt["execution"]["status"] == "PASS"
    assert receipt["execution"]["verified"] is True
    assert receipt["authority"]["arbitrary_token_bytes_are_executable"] is False
    assert receipt["authority"]["external_os_or_shell_authority"] is False
    assert verify_token_action_mask(lattice, bindings, receipt) is True


def test_token_bytes_do_not_gain_implicit_execution_authority() -> None:
    with pytest.raises(ValueError, match="exact VM contract"):
        ActionTokenBinding("action-table", 0, b"load-a".hex(), "load", ("A", "7"))

    lattice, bindings = _fixture()
    wrong = (
        ActionTokenBinding("action-table", 0, b"not-the-token".hex(), "LOAD", ("A", "7")),
        *bindings[1:],
    )
    with pytest.raises(TokenActionLithographyError, match="exactly one lattice path"):
        compile_token_action_mask(lattice, wrong)


def test_token_mask_verifier_fails_closed_on_changed_program() -> None:
    lattice, bindings = _fixture()
    receipt = compile_token_action_mask(lattice, bindings)
    changed = deepcopy(receipt)
    changed["program"]["program_hex"] = "00"
    assert verify_token_action_mask(lattice, bindings, changed) is False
