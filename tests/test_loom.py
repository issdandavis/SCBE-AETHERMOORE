"""Tests for Loom — the tiny universal loop machine + multi-language weaver."""

import shutil

import pytest

from python.loom import emit as E
from python.loom import equiv, machine as M

# r2 += r1, then output r2 (a classic Minsky addition)
ADD = """
loop: dec r1 done
      inc r2
      jmp loop
done: out r2
      halt
"""

SPIN = "spin: jmp spin"  # a pure infinite loop
GROW = "g: inc r1\n    jmp g"  # pc cycles but r1 grows forever -> never repeats state


def test_parse_resolves_labels_and_registers():
    prog = M.parse(ADD)
    assert prog.registers == ("r1", "r2")
    assert [i.op for i in prog.instrs] == ["dec", "inc", "jmp", "out", "halt"]
    # 'loop' labels instr 0, 'done' labels instr 3
    assert prog.labels["loop"] == 0 and prog.labels["done"] == 3
    assert prog.instrs[0].target == 3  # dec r1 -> done
    assert prog.instrs[2].target == 0  # jmp -> loop


@pytest.mark.parametrize("a,b", [(0, 0), (3, 4), (5, 0), (9, 2)])
def test_addition_runs_correctly(a, b):
    res = M.run(M.parse(ADD), {"r1": a, "r2": b})
    assert res.halted is True
    assert res.output == [a + b]


def test_loop_detection_spots_self_intersection():
    res = M.run(M.parse(SPIN))
    assert res.status == "loop"
    assert res.loops is True
    assert res.loop_state is not None  # the (pc, regs) point that repeated


def test_growing_state_is_undetermined_not_a_false_loop():
    # halting is undecidable: pc cycles but r1 grows, so no exact state repeats
    res = M.run(M.parse(GROW), max_steps=500)
    assert res.status == "budget"
    assert res.loops is False and res.halted is False


def test_python_emit_matches_reference():
    prog = M.parse(ADD)
    for init in ({"r1": 0, "r2": 0}, {"r1": 3, "r2": 4}, {"r1": 7, "r2": 2}):
        assert equiv.run_python_emit(prog, init) == equiv.run_reference(prog, init)


def test_emitters_produce_wellformed_source():
    prog = M.parse(ADD)
    py = E.emit_python(prog, {"r1": 3, "r2": 4})
    js = E.emit_js(prog, {"r1": 3, "r2": 4})
    c = E.emit_c(prog, {"r1": 3, "r2": 4})
    assert "def run():" in py and "while 0 <= pc <" in py
    assert "function run()" in js and "return trace;" in js
    assert "#include <stdio.h>" in c and "int main(void)" in c


def test_cross_check_all_backends_agree():
    prog = M.parse(ADD)
    report = equiv.cross_check(prog, [{"r1": 3, "r2": 4}, {"r1": 6, "r2": 1}])
    assert report["all_agree"] is True
    assert "reference" in report["backends"] and "python" in report["backends"]


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_node_emit_matches_reference():
    prog = M.parse(ADD)
    assert equiv.run_node(prog, {"r1": 3, "r2": 4}) == [7]


@pytest.mark.skipif(not (shutil.which("gcc") or shutil.which("cc")), reason="no C compiler")
def test_c_emit_matches_reference():
    prog = M.parse(ADD)
    assert equiv.run_c(prog, {"r1": 5, "r2": 2}) == [7]


def test_mirror_check_exact_for_normal_program():
    # ADD's jump targets are all real instructions -> exact mirror
    m = equiv.mirror_check(ADD, inits=[{"r1": 0}, {"r1": 4, "r2": 1}])
    assert m["exact_mirror"] is True
    assert m["near_mirror"] is False and m["broken"] is False


def test_mirror_check_near_for_jump_to_end():
    # 'fin' is a label at the very end -> dec jumps PAST the last instr (= halt);
    # unparse materializes that as an explicit trailing halt: behaviorally identical,
    # structurally one instruction longer -> a NEAR mirror, not an exact one.
    src = "dec r1 fin\n    inc r2\n    out r2\nfin:"
    m = equiv.mirror_check(src, inits=[{"r1": 0}, {"r1": 3}])
    assert m["near_mirror"] is True
    assert m["exact_mirror"] is False and m["broken"] is False


def test_behavioral_equivalence():
    a = "out r1\nhalt"
    b = "inc r1\n    dec r1 k\nk: out r1\nhalt"  # inc then dec-back nets zero -> same output
    c = "inc r1\n    out r1\nhalt"  # off by one -> different
    inits = [{"r1": 0}, {"r1": 5}, {"r1": 9}]
    assert equiv.behaviorally_equivalent(a, b, inits) is True
    assert equiv.behaviorally_equivalent(a, c, inits) is False


def test_syntax_errors_are_reported():
    with pytest.raises(M.LoomSyntaxError):
        M.parse("inc")  # missing register
    with pytest.raises(M.LoomSyntaxError):
        M.parse("jmp nowhere")  # unknown label
    with pytest.raises(M.LoomSyntaxError):
        M.parse("bogus r1")  # unknown op
