from python.loom import parse
from python.loom.typewriter import encode_typewriter, typewriter_receipt, validate_typewriter_table

SCHEDULE = """
tick: dec budget done
      out budget
      jmp tick
done: halt
"""


def test_typewriter_table_covers_the_loom_core() -> None:
    ok, errors = validate_typewriter_table()
    assert ok is True
    assert errors == []


def test_typewriter_uses_honest_opcode_namespaces() -> None:
    keys = encode_typewriter(parse(SCHEDULE))
    assert [key.loom_op for key in keys] == ["dec", "out", "jmp", "halt"]
    assert keys[0].opcode_hex == "0x0C"
    assert keys[0].ca_name == "dec"
    assert keys[0].namespace == "ca-opcode"
    assert keys[1].flow_op == "print"
    assert keys[1].namespace == "loom-control-overlay"
    assert keys[1].ca_aligned is False


def test_typewriter_receipt_is_stable_and_run_bound() -> None:
    first = typewriter_receipt(SCHEDULE, {"budget": 3})
    second = typewriter_receipt(SCHEDULE, {"budget": 3})
    assert first["status"] == "halted"
    assert first["output"] == [2, 1, 0]
    assert first["route_sha256"] == second["route_sha256"]
    assert len(first["route_sha256"]) == 64
    assert first["mirror"]["broken"] is False
