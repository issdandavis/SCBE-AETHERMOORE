from __future__ import annotations

from scripts.aetherpp.parse import parse_program


def test_parse_program_core_statements() -> None:
    program = (
        "create spacaita system with 3 manifolds. "
        "set goal to safe addition route. "
        "apply discrete fold 0.8 to manifold 0 with goal signal 0.9 in tongue KO. "
        "cross propagate from manifold 0 to manifold 1 with ratio 0.5,0.3,0.2. "
        'encode "def add(a, b): return a + b" in tongue AV. '
        "run route."
    )
    nodes = parse_program(program)
    assert [node.kind for node in nodes] == [
        "create_system",
        "set_goal",
        "apply_fold",
        "cross_propagate",
        "encode",
        "run_route",
    ]
    assert nodes[2].data["tongue"] == "KO"
    assert nodes[4].data["tongue"] == "AV"


def test_parse_rejects_unknown_statement() -> None:
    bad = "summon dragons now."
    try:
        parse_program(bad)
        assert False, "Expected ValueError for invalid statement"
    except ValueError as exc:
        assert "Unrecognized Aether++ statement" in str(exc)
