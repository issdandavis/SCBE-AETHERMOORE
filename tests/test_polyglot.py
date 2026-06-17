"""Polyglot all-code compiler — emit + roundabout (defined undefined-zone) parity."""
import pytest

from python.scbe import polyglot as P


def _run_python(prog, safe):
    src = P.emit(prog, "python", safe=safe)
    ns = {}
    exec(compile(src, "p.py", "exec"), ns)  # noqa: S102 - test self-exec
    return ns["tongue_fn"](2.0, 3.0, 4.0)


def test_emit_all_18_languages():
    prog = P.program_bytes("add", "mul")
    langs = P.languages()
    assert len(langs) == 18
    for lang in langs:
        src = P.emit(prog, lang, runnable=True)
        assert "tongue_fn" in src and src.endswith("\n")


def test_roundabout_divide_by_zero():
    # eq: 3==4 -> 0.0 ; div: 2 / 0.0
    prog = P.program_bytes("eq", "div")
    with pytest.raises(ZeroDivisionError):
        _run_python(prog, safe=False)          # raw: python raises
    assert _run_python(prog, safe=True) == 0.0  # roundabout: defined as 0.0


def test_roundabout_sqrt_of_negative():
    prog = P.program_bytes("sub", "sqrt")       # 3-4=-1 ; sqrt(-1)
    with pytest.raises(ValueError):
        _run_python(prog, safe=False)           # raw: math domain error
    assert _run_python(prog, safe=True) == 0.0  # roundabout: defined as 0.0


def test_safe_matches_raw_on_well_defined():
    # roundabouts must NOT change results where the math is already defined
    prog = P.program_bytes("add", "mul", "sqrt", "inc")
    assert _run_python(prog, safe=False) == _run_python(prog, safe=True)


def test_safe_emits_for_every_language():
    prog = P.program_bytes("add", "div", "sqrt", "mod")  # all roundabout ops
    for lang in P.languages():
        assert P.emit(prog, lang, runnable=True, safe=True)
