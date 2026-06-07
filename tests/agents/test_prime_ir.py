from __future__ import annotations

import json

from python.scbe.prime_ir import (
    audit_language_prime_equivalence,
    decode_primes_to_opcodes,
    encode_opcodes_to_primes,
    op_name_for_prime,
    prime_for_op_name,
    prime_plan_from_ops,
)


def test_prime_opcode_tape_round_trips_abs_abs_add() -> None:
    opcodes = [0x09, 0x09, 0x00]
    primes = encode_opcodes_to_primes(opcodes)

    assert primes == [29, 29, 2]
    assert decode_primes_to_opcodes(primes) == opcodes
    assert op_name_for_prime(29) == "abs"
    assert prime_for_op_name("add") == 2


def test_prime_plan_is_order_preserving() -> None:
    plan = prime_plan_from_ops(["abs", "abs", "add"])

    assert plan["schema"] == "scbe_prime_code_ir_v1"
    assert plan["encoding"] == "ordered_prime_tape"
    assert plan["order_preserving"] is True
    assert plan["prime_sequence"] == [29, 29, 2]
    assert plan["hex_sequence"] == ["0x09", "0x09", "0x00"]


def test_multilingual_lexicon_rows_share_prime_identity() -> None:
    audit = audit_language_prime_equivalence()

    assert audit["ok"] is True, audit["problems"]
    assert audit["row_count"] == 64
    assert audit["sample_rows"][0]["op_name"] == "add"
    assert audit["sample_rows"][0]["prime"] == 2


def test_scbe_code_prime_plan_cli(gate=None) -> None:
    from tests.agents.test_scbe_code import _run_cli

    rc, stdout, _ = _run_cli(["prime-plan", "--expr", "abs(a)+abs(b)", "--json"])

    assert rc == 0
    payload = json.loads(stdout)
    assert payload["prime_sequence"] == [29, 29, 2]
    assert (
        payload["compile_prime_hint"] == 'compile-prime --primes "29 29 2" --args a,b'
    )


def test_scbe_code_compile_prime_cli_json() -> None:
    from tests.agents.test_scbe_code import _run_cli

    rc, stdout, _ = _run_cli(
        [
            "compile-prime",
            "--primes",
            "29 29 2",
            "--target",
            "python",
            "--fn",
            "abs_add",
            "--args",
            "a,b",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(stdout)
    assert payload["prime_sequence"] == [29, 29, 2]
    assert payload["opcodes"] == [9, 9, 0]
    assert payload["round_trip_ok"] is True
    assert "# abs (0x09)" in payload["source"]
    assert "# add (0x00)" in payload["source"]
