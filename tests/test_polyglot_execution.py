"""Cross-language identity PROOF: emit each face, compile+run it, and assert it
computes the SAME number as the Python reference.

The old test only checked that ``emit()`` does not raise — so a face could emit
code that does not compile or computes the wrong value and still pass (this is how
the PHP face shipped emitting bare ``a``/``b`` instead of ``$a``/``$b``). This test
actually executes the emitted source. Faces whose compiler/runtime is not installed
on the current machine are SKIPPED, not failed, so the suite is green locally with
only python/node/rustc and gets stronger as CI adds toolchains.
"""

import math
import os
import shutil
import subprocess
import tempfile
import time

import pytest

from python.scbe import polyglot as P

INPUTS = (2.0, 3.0, 4.0)


class _NoTool(Exception):
    """Raised by a runner when its toolchain is absent -> the case is skipped."""


def _which(*names: str):
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


# Transient OS-level failures (NOT compiler errors): a freshly-written face.exe is
# briefly locked by an AV/indexer scan, the temp dir is contended, or the run times
# out under a heavy parallel batch. These are environmental and self-clear on retry.
# A REAL emitter bug surfaces as a compiler diagnostic (error[E0xxx], SyntaxError,
# Traceback, parse error) which never matches this signature -> still fails hard.
_TRANSIENT = (
    "access is denied",
    "being used by another process",
    "permission denied",
    "os error 5",
    "resource temporarily unavailable",
    "text file busy",
    "cannot create",
    "couldn't write output",
)


def _is_transient(text: str) -> bool:
    low = (text or "").lower()
    return any(sig in low for sig in _TRANSIENT)


def _run(cmd, **kw):
    last = None
    for attempt in range(3):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180, **kw)
        except subprocess.TimeoutExpired as exc:  # batch contention, not a code bug
            last = exc
            time.sleep(0.5 * (attempt + 1))
            continue
        if r.returncode and _is_transient((r.stderr or "") + (r.stdout or "")) and attempt < 2:
            time.sleep(0.5 * (attempt + 1))  # let the AV/indexer release the lock
            continue
        return r
    raise RuntimeError(f"transient toolchain failure after retries: {last}")


def _last_number(stdout: str) -> float:
    return float(stdout.strip().splitlines()[-1])


def _write(td: str, name: str, src: str) -> str:
    path = os.path.join(td, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src)
    return path


# --- per-language compile+run -------------------------------------------------
def _interp(tool_names, fname):
    def run(src, td):
        exe = _which(*tool_names)
        if not exe:
            raise _NoTool(tool_names[0])
        path = _write(td, fname, src)
        r = _run([exe, path])
        if r.returncode:
            raise RuntimeError(f"{tool_names[0]} failed:\n{r.stderr or r.stdout}")
        return _last_number(r.stdout)

    return run


def _compiled(tool_names, fname, compile_argv, run_argv):
    def run(src, td):
        cc = _which(*tool_names)
        if not cc:
            raise _NoTool(tool_names[0])
        src_path = _write(td, fname, src)
        exe = os.path.join(td, "face.exe")
        rc = _run([cc] + compile_argv(src_path, exe, td))
        if rc.returncode:
            raise RuntimeError(f"{tool_names[0]} compile failed:\n{rc.stderr or rc.stdout}")
        rr = _run(run_argv(exe, td))
        if rr.returncode:
            raise RuntimeError(f"run failed:\n{rr.stderr or rr.stdout}")
        return _last_number(rr.stdout)

    return run


def _java(src, td):
    if not (_which("javac") and _which("java")):
        raise _NoTool("javac")
    _write(td, "Main.java", src)  # public class Main -> filename must match
    rc = _run([_which("javac"), os.path.join(td, "Main.java")])
    if rc.returncode:
        raise RuntimeError(f"javac failed:\n{rc.stderr}")
    rr = _run([_which("java"), "-cp", td, "Main"])
    if rr.returncode:
        raise RuntimeError(f"java run failed:\n{rr.stderr}")
    return _last_number(rr.stdout)


def _kotlin(src, td):
    if not (_which("kotlinc") and _which("java")):
        raise _NoTool("kotlinc")
    kt = _write(td, "face.kt", src)
    jar = os.path.join(td, "face.jar")
    rc = _run([_which("kotlinc"), kt, "-include-runtime", "-d", jar])
    if rc.returncode:
        raise RuntimeError(f"kotlinc failed:\n{rc.stderr}")
    rr = _run([_which("java"), "-jar", jar])
    if rr.returncode:
        raise RuntimeError(f"kotlin run failed:\n{rr.stderr}")
    return _last_number(rr.stdout)


RUNNERS = {
    "javascript": _interp(["node"], "face.js"),
    "typescript": _interp(["deno"], "face.ts"),  # deno runs .ts directly
    "ruby": _interp(["ruby"], "face.rb"),
    "php": _interp(["php"], "face.php"),
    "lua": _interp(["lua", "lua5.4", "lua5.3", "luajit"], "face.lua"),
    "julia": _interp(["julia"], "face.jl"),
    "haskell": _interp(["runghc", "runhaskell"], "face.hs"),
    "swift": _interp(["swift"], "face.swift"),
    "rust": _compiled(
        ["rustc"],
        "face.rs",
        lambda s, e, td: ["-O", "-o", e, s],
        lambda e, td: [e],
    ),
    "c": _compiled(
        ["gcc", "clang", "cc"],
        "face.c",
        lambda s, e, td: [s, "-O2", "-lm", "-o", e],
        lambda e, td: [e],
    ),
    "cpp": _compiled(
        ["g++", "clang++"],
        "face.cpp",
        lambda s, e, td: [s, "-O2", "-o", e],
        lambda e, td: [e],
    ),
    "go": _compiled(
        ["go"],
        "face.go",
        lambda s, e, td: ["build", "-o", e, s],
        lambda e, td: [e],
    ),
    "zig": _interp(["zig"], "face.zig"),  # handled specially below via 'run'
    "java": _java,
    "kotlin": _kotlin,
}


def _zig(src, td):
    exe = _which("zig")
    if not exe:
        raise _NoTool("zig")
    path = _write(td, "face.zig", src)
    r = _run([exe, "run", path])
    if r.returncode:
        raise RuntimeError(f"zig failed:\n{r.stderr or r.stdout}")
    # The Zig face uses std.debug.print, which writes to stderr.
    return _last_number(r.stdout or r.stderr)


RUNNERS["zig"] = _zig

# Languages we can actually execute on THIS machine (others -> not collected).
_AVAILABLE = sorted(
    lang
    for lang in RUNNERS
    if _which(
        *{
            "javascript": ("node",),
            "typescript": ("deno",),
            "ruby": ("ruby",),
            "php": ("php",),
            "lua": ("lua", "lua5.4", "lua5.3", "luajit"),
            "julia": ("julia",),
            "haskell": ("runghc", "runhaskell"),
            "swift": ("swift",),
            "rust": ("rustc",),
            "c": ("gcc", "clang", "cc"),
            "cpp": ("g++", "clang++"),
            "go": ("go",),
            "zig": ("zig",),
            "java": ("javac",),
            "kotlin": ("kotlinc",),
        }[lang]
    )
)


def _programs():
    """Every scalar op exercised at least once, plus chains that actually TAKE the
    div-by-zero and sqrt-of-negative roundabout branches."""
    progs = [(op, [op]) for op in sorted(P.SCALAR_OPS)]
    progs += [
        ("chain_mix", ["add", "mul", "sqrt", "inc"]),
        ("chain_unary", ["neg", "abs", "dec"]),
        ("chain_cmp", ["lt", "add"]),
        ("roundabout_div0", ["eq", "div"]),  # 3==4 -> 0.0 ; 2 / 0.0 -> 0.0
        ("roundabout_sqrtneg", ["sub", "sqrt"]),  # 3-4 -> -1 ; sqrt(-1) -> 0.0
    ]
    return progs


def _ref(prog) -> float:
    src = P.emit(P.program_bytes(*prog), "python", safe=True)
    ns: dict = {}
    exec(compile(src, "ref.py", "exec"), ns)  # noqa: S102 - test oracle
    return ns["tongue_fn"](*INPUTS)


PROGRAMS = _programs()


def test_at_least_python_runs():
    """Sanity floor: the oracle itself must produce the known value."""
    assert math.isclose(_ref(["add", "mul", "sqrt", "inc"]), 4.741657386773941, rel_tol=1e-12)


@pytest.mark.parametrize("lang", _AVAILABLE)
@pytest.mark.parametrize("prog_id,prog", PROGRAMS, ids=[p[0] for p in PROGRAMS])
def test_face_executes_identically(lang, prog_id, prog):
    """Each installed face must compute the same number as the Python reference."""
    ref = _ref(prog)
    src = P.emit(P.program_bytes(*prog), lang, runnable=True, safe=True)
    td = tempfile.mkdtemp(prefix=f"face_{lang}_")
    try:
        try:
            val = RUNNERS[lang](src, td)
        except _NoTool as exc:  # pragma: no cover - filtered by _AVAILABLE
            pytest.skip(f"{lang}: toolchain {exc} not installed")
        # Faces now print full round-trip precision, so require near-exact agreement
        # (1e-9), not a loose display tolerance — this is the real identity proof.
        assert math.isclose(
            val, ref, rel_tol=1e-9, abs_tol=1e-12
        ), f"{lang} face of {prog} produced {val}, reference is {ref}\n--- emitted ---\n{src}"
    finally:
        shutil.rmtree(td, ignore_errors=True)


def test_emit_var_binding_invariant():
    """Static guard for the PHP-class bug: the temp-var names the push expression
    uses MUST be the names pop2/pop1 bind. Catches a broken face even with no
    toolchain present."""
    for lang in P.languages():
        d = P.REGISTRY[lang]
        assert d.var_a in d.pop2 and d.var_b in d.pop2, f"{lang}: pop2 does not bind {d.var_a!r}/{d.var_b!r}"
        assert d.var_a in d.pop1, f"{lang}: pop1 does not bind {d.var_a!r}"
