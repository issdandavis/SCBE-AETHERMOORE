"""Regression tests for CA opcode runtime plumbing."""

import pytest

from python.scbe.tongue_isa import (
    SUPPORTED_TARGETS,
    compile_ca_tokens,
    disassemble,
    emit_compiled_program_source,
)


def test_emit_compiled_program_source_attaches_runtime_for_fallback_ops():
    program = compile_ca_tokens([0x29], target="python", fn_name="clamp_demo", arg_names=["a", "b", "c"])

    source = emit_compiled_program_source(program)

    assert "def ca_apply3" in source
    assert "def clamp_demo(a, b, c)" in source

    namespace = {}
    exec(compile(source, "<clamp_demo>", "exec"), namespace)  # noqa: S102 - test executes generated code
    assert namespace["clamp_demo"](12, 0, 10) == 10


@pytest.mark.parametrize("target", SUPPORTED_TARGETS)
def test_official_source_emitter_preserves_opcode_trace_for_every_target(target):
    program = compile_ca_tokens([0x00], target=target, fn_name="add_demo", arg_names=["a", "b"])

    source = emit_compiled_program_source(program, include_runtime=False)

    assert disassemble(source) == [(0x00, "add")]
