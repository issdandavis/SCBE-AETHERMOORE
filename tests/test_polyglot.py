"""Polyglot all-code compiler — emit + roundabout (defined undefined-zone) parity."""

import os
import shutil
import subprocess
from collections.abc import Callable

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
        _run_python(prog, safe=False)  # raw: python raises
    assert _run_python(prog, safe=True) == 0.0  # roundabout: defined as 0.0


def test_roundabout_sqrt_of_negative():
    prog = P.program_bytes("sub", "sqrt")  # 3-4=-1 ; sqrt(-1)
    with pytest.raises(ValueError):
        _run_python(prog, safe=False)  # raw: math domain error
    assert _run_python(prog, safe=True) == 0.0  # roundabout: defined as 0.0


def test_safe_matches_raw_on_well_defined():
    # roundabouts must NOT change results where the math is already defined
    prog = P.program_bytes("add", "mul", "sqrt", "inc")
    assert _run_python(prog, safe=False) == _run_python(prog, safe=True)


def test_safe_emits_for_every_language():
    prog = P.program_bytes("add", "div", "sqrt", "mod")  # all roundabout ops
    for lang in P.languages():
        assert P.emit(prog, lang, runnable=True, safe=True)


def _run_emitted_toolchain(tmp_path, lang: str, command: Callable) -> float:
    path = _write_emitted_source(tmp_path, lang)
    proc = subprocess.run(command(path), cwd=tmp_path, text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stderr
    return float(proc.stdout.strip())


def _write_emitted_source(tmp_path, lang: str):
    prog = P.program_bytes("add", "mul", "sqrt", "inc")
    src = P.emit(prog, lang, runnable=True, safe=True)
    path = tmp_path / f"tongue_fn.{P.REGISTRY[lang].ext}"
    path.write_text(src, encoding="utf-8")
    return path


def test_available_emitted_faces_run_with_python_parity(tmp_path):
    expected = _run_python(P.program_bytes("add", "mul", "sqrt", "inc"), safe=True)
    assert expected == pytest.approx(4.741657386773941)

    if shutil.which("node"):
        got = _run_emitted_toolchain(tmp_path, "javascript", lambda path: ["node", str(path)])
        assert got == pytest.approx(expected)

    if shutil.which("rustc"):
        path = _write_emitted_source(tmp_path, "rust")
        exe = tmp_path / ("tongue_fn" + (".exe" if os.name == "nt" else ""))
        compile_proc = subprocess.run(["rustc", str(path), "-o", str(exe)], text=True, capture_output=True, check=False)
        assert compile_proc.returncode == 0, compile_proc.stderr
        run_proc = subprocess.run([str(exe)], text=True, capture_output=True, check=False)
        assert run_proc.returncode == 0, run_proc.stderr
        got = float(run_proc.stdout.strip())
        assert got == pytest.approx(expected)


def test_php_face_uses_php_variable_sigil():
    src = P.emit(P.program_bytes("add", "mul", "sqrt", "inc"), "php", runnable=True, safe=True)
    assert "$s[] = $a + $b;" in src
    assert "$s[] = $a * $b;" in src
    assert "sqrt($a)" in src
    assert "$s[] = a + b;" not in src
    assert "$s[] = a * b;" not in src
    assert "sqrt(a)" not in src
