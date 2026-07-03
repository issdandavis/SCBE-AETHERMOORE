"""Regression tests for CA opcode runtime plumbing."""

from python.scbe.tongue_isa import compile_ca_tokens, emit_compiled_program_source


def test_emit_compiled_program_source_attaches_runtime_for_fallback_ops():
    program = compile_ca_tokens([0x29], target="python", fn_name="clamp_demo", arg_names=["a", "b", "c"])

    source = emit_compiled_program_source(program)

    assert "def ca_apply3" in source
    assert "def clamp_demo(a, b, c)" in source

    namespace = {}
    exec(compile(source, "<clamp_demo>", "exec"), namespace)  # noqa: S102 - test executes generated code
    assert namespace["clamp_demo"](12, 0, 10) == 10
