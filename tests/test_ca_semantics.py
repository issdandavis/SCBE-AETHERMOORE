"""Reference semantic-template choices for all 64 CA ops."""

import pytest

from python.scbe import ca_semantics as S
from python.scbe.ca_opcode_table import OP_TABLE


def test_every_ca_opcode_has_a_template_choice():
    report = S.coverage_report()

    assert report["covered"] == 64
    assert report["missing"] == []
    assert {"aggregate", "arithmetic", "bitwise", "predicate", "ternary"}.issubset(report["families"])
    for entry in OP_TABLE.values():
        choices = S.template_choices(entry.name)
        assert choices
        assert S.default_choice(entry.name) == choices[0]


@pytest.mark.parametrize(
    ("op", "expected"),
    [
        ("xor", "bitwise_i64"),
        ("bitset", "bit_index_i64"),
        ("popcount", "unary_bitcount_i64"),
        ("variance", "aggregate_scalar"),
        ("reduce", "pair_fold"),
        ("within", "ternary_float"),
    ],
)
def test_exotic_ops_name_their_template_family(op, expected):
    assert S.default_choice(op).name == expected


def test_bitwise_template_semantics():
    assert S.apply_opcode("xor", 5, 3) == 6.0
    assert S.apply_opcode("bitset", 8, 1) == 10.0
    assert S.apply_opcode("bitclear", 10, 1) == 8.0
    assert S.apply_opcode("popcount", 0b101101) == 4.0
    assert S.apply_opcode("ctz", 0b1000) == 3.0


def test_ternary_and_predicate_template_semantics():
    assert S.apply_opcode("clamp", 12, 0, 10) == 10.0
    assert S.apply_opcode("clamp", -4, 0, 10) == 0.0
    assert S.apply_opcode("within", 5, 0, 10) == 1.0
    assert S.apply_opcode("within", 12, 0, 10) == 0.0
    assert S.apply_opcode("cmp", 2, 9) == -1.0


def test_aggregate_scalar_template_semantics():
    assert S.apply_opcode("sum", 7) == 7.0
    assert S.apply_opcode("product", 7) == 7.0
    assert S.apply_opcode("mean", 7) == 7.0
    assert S.apply_opcode("variance", 7) == 0.0
    assert S.apply_opcode("count", 7) == 1.0
    assert S.apply_opcode("reduce", 2, 5) == 7.0
    assert S.apply_opcode("filter", 9, 0) == 0.0
    assert S.apply_opcode("filter", 9, 1) == 9.0


def test_reference_stack_machine_runs_exotic_programs():
    assert S.run_program(["pow"], [2, 5]) == 32.0
    assert S.run_program(["xor"], [5, 3]) == 6.0
    assert S.run_program(["clamp"], [12, 0, 10]) == 10.0
    assert S.run_program(["add", "popcount"], [2, 3]) == 2.0


def test_template_choice_validation():
    with pytest.raises(ValueError, match="not valid"):
        S.apply_opcode("xor", 5, 3, choice="aggregate_scalar")
    with pytest.raises(ValueError, match="expects 3 args"):
        S.apply_opcode("clamp", 1, 2)
