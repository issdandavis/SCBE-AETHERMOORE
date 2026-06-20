"""Differential conformance harness for the polyglot multi-backend compiler.

The polyglot emitter is a compiler with many backends over one core opcode IR. This
harness measures the only thing that actually matters about that: do the backends compute
the SAME numbers? It is HONEST by construction:

  * It compiles+runs a backend ONLY where a local toolchain exists (this box: python in
    process, javascript via `node`, rust via `rustc`). Everything else is reported as
    emitted-but-unverified -- never as agreement.
  * It never marks a backend AGREE unless it actually ran and matched the Python reference.
  * It SURFACES real divergences instead of hiding them. "Same value class" (Church-Turing)
    is not "same program with the same numeric behaviour": e.g. round(2.5) is 2.0 in Python
    (half-to-even) but 3.0 in JS/Rust (half-up / half-away). The harness reports that as a
    DISAGREE, because it is one -- that asymmetry is the whole point of the calibration.

    python -m python.scbe.polyglot_conformance "mul gt" --args 2,3,4 --args 10,3,2
    python -m python.scbe.polyglot_conformance --demo
"""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import polyglot as P

TOL = 1e-9  # absolute+relative tolerance for "agree"

# Backends we know HOW to run locally. A backend not listed here is emitted but has no
# runner, so it can only ever be reported as unverified -- not as agreement.
_RUNNER_TOOL = {
    "python": None,
    "javascript": "node",
    "rust": "rustc",
    "c": "cc",
    "go": "go",
    "ruby": "ruby",
    "php": "php",
    "lua": "lua",
}


def _toolchain_ok(lang: str) -> bool:
    tool = _RUNNER_TOOL.get(lang, "<none>")
    if tool is None:
        return True  # python runs in-process
    if tool == "<none>":
        return False  # no runner implemented for this backend
    return shutil.which(tool) is not None


def _close(x: Optional[float], r: Optional[float]) -> bool:
    if x is None or r is None:
        return x is r
    if math.isnan(x) or math.isnan(r):
        return math.isnan(x) and math.isnan(r)
    if math.isinf(x) or math.isinf(r):
        return x == r  # require SAME signed infinity; the tolerance form below mis-handles inf
        # (abs(inf-inf)==nan -> false DISAGREE on equal infinities; abs(inf-(-inf))==inf<=inf -> false AGREE)
    return abs(x - r) <= TOL + TOL * abs(r)


# per-language literals for the special IEEE values, so nan/inf can actually be fed to each backend
# (repr(float('nan')) == 'nan' is a valid literal in NONE of js/rust/c -- this is what lets the harness
# verify the predicate ops isnan/isinf/isfinite on the inputs that actually exercise them).
_SPECIAL = {
    "javascript": ("NaN", "Infinity"),
    "rust": ("f64::NAN", "f64::INFINITY"),
    "c": ("NAN", "INFINITY"),
    "go": ("math.NaN()", "math.Inf(1)"),
}


def _fmt(a: float, lang: str) -> str:
    a = float(a)
    nan, inf = _SPECIAL.get(lang, ("nan", "inf"))
    if math.isnan(a):
        return nan
    if math.isinf(a):
        return ("-" + inf) if a < 0 else inf
    return repr(a)


def _arglist(args: Sequence[float], lang: str = "python") -> str:
    return ", ".join(_fmt(a, lang) for a in args)


def run_python(prog: Sequence[int], args: Sequence[float]) -> Optional[float]:
    ns: Dict[str, object] = {}
    exec(compile(P.emit(prog, "python"), "<conf>", "exec"), ns)  # noqa: S102 - our own emitter output
    out = ns["tongue_fn"](*[float(a) for a in args])  # type: ignore[operator]
    return None if out is None else float(out)


def _run_subprocess_float(cmd: Sequence[str], cwd: Optional[Path] = None, timeout: int = 60) -> Optional[float]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "nonzero exit").strip().splitlines()[-1][:200])
    line = proc.stdout.strip().splitlines()[-1].strip()
    if line.lower() in ("nan", "-nan"):
        return float("nan")
    return float(line)


def run_node(prog: Sequence[int], args: Sequence[float]) -> Optional[float]:
    src = P.emit(prog, "javascript") + "\nprocess.stdout.write(String(tongue_fn(%s)));\n" % _arglist(args, "javascript")
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "prog.js"
        f.write_text(src, encoding="utf-8")
        return _run_subprocess_float(["node", str(f)])


def run_rust(prog: Sequence[int], args: Sequence[float]) -> Optional[float]:
    src = P.emit(prog, "rust") + '\nfn main() { println!("{:.17}", tongue_fn(%s)); }\n' % _arglist(args, "rust")
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "prog.rs"
        f.write_text(src, encoding="utf-8")
        exe = Path(td) / ("prog.exe" if shutil.which("cmd") else "prog")
        subprocess.run(["rustc", "-O", str(f), "-o", str(exe)], capture_output=True, text=True, timeout=120, check=True)
        return _run_subprocess_float([str(exe)])


def run_c(prog: Sequence[int], args: Sequence[float]) -> Optional[float]:
    src = P.emit(prog, "c") + '\nint main(void) { printf("%%.17g\\n", tongue_fn(%s)); return 0; }\n' % _arglist(
        args, "c"
    )
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "prog.c"
        f.write_text(src, encoding="utf-8")
        exe = Path(td) / ("prog.exe" if shutil.which("cmd") else "prog")
        subprocess.run(["cc", str(f), "-lm", "-o", str(exe)], capture_output=True, text=True, timeout=120, check=True)
        return _run_subprocess_float([str(exe)])


def run_go(prog: Sequence[int], args: Sequence[float]) -> Optional[float]:
    src = P.emit(prog, "go") + "\nfunc main() { fmt.Println(tongue_fn(%s)) }\n" % _arglist(args, "go")
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "prog.go"
        f.write_text(src, encoding="utf-8")
        return _run_subprocess_float(["go", "run", str(f)], timeout=120)


def run_ruby(prog: Sequence[int], args: Sequence[float]) -> Optional[float]:
    src = P.emit(prog, "ruby") + "\nputs tongue_fn(%s)\n" % _arglist(args)
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "prog.rb"
        f.write_text(src, encoding="utf-8")
        return _run_subprocess_float(["ruby", str(f)])


def run_php(prog: Sequence[int], args: Sequence[float]) -> Optional[float]:
    src = P.emit(prog, "php") + "\necho tongue_fn(%s);\n" % _arglist(args)
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "prog.php"
        f.write_text(src, encoding="utf-8")
        return _run_subprocess_float(["php", str(f)])


def run_lua(prog: Sequence[int], args: Sequence[float]) -> Optional[float]:
    src = P.emit(prog, "lua") + "\nprint(tongue_fn(%s))\n" % _arglist(args)
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "prog.lua"
        f.write_text(src, encoding="utf-8")
        return _run_subprocess_float(["lua", str(f)])


_RUNNERS = {
    "python": run_python,
    "javascript": run_node,
    "rust": run_rust,
    "c": run_c,
    "go": run_go,
    "ruby": run_ruby,
    "php": run_php,
    "lua": run_lua,
}


@dataclass
class BackendResult:
    lang: str
    status: str  # REFERENCE | AGREE | DISAGREE | NO_TOOLCHAIN | NO_RUNNER | ERROR
    values: List[Optional[float]] = field(default_factory=list)
    note: str = ""


def conformance(prog: Sequence[int], cases: Sequence[Sequence[float]]) -> dict:
    """Run prog across every registered backend over the given input cases; compare each
    runnable backend to the Python reference and report honest, per-backend status."""
    ref = [run_python(prog, c) for c in cases]
    results: List[BackendResult] = [BackendResult("python", "REFERENCE", ref, "in-process reference")]

    for lang in P.languages():
        if lang == "python":
            continue
        if lang not in _RUNNERS:
            results.append(BackendResult(lang, "NO_RUNNER", note="emitted; no runner implemented"))
            continue
        if not _toolchain_ok(lang):
            results.append(BackendResult(lang, "NO_TOOLCHAIN", note="emitted; %s not on PATH" % _RUNNER_TOOL[lang]))
            continue
        try:
            vals = [_RUNNERS[lang](prog, c) for c in cases]
        except Exception as e:  # compile/run failure is reported, never silently 'agree'
            results.append(BackendResult(lang, "ERROR", note="%s: %s" % (type(e).__name__, e)))
            continue
        agree = all(_close(v, r) for v, r in zip(vals, ref))
        results.append(BackendResult(lang, "AGREE" if agree else "DISAGREE", vals))

    ran = [r for r in results if r.status in ("REFERENCE", "AGREE", "DISAGREE")]
    verified = [r for r in results if r.status == "AGREE"]
    disagreed = [r for r in results if r.status == "DISAGREE"]
    return {
        "program": [P.BYTE_TO_NAME[b] for b in prog],
        "cases": [list(c) for c in cases],
        "reference": ref,
        "results": results,
        "summary": {
            "runnable_backends": len(ran),  # includes the python reference
            "verified_agree": len(verified),
            "disagree": [r.lang for r in disagreed],
            "emitted_unverified": len([r for r in results if r.status in ("NO_TOOLCHAIN", "NO_RUNNER", "ERROR")]),
            "total_backends": len(results),
        },
    }


def format_report(rep: dict) -> str:
    lines = ["program: %s   cases: %s" % (" ".join(rep["program"]) or "(empty)", rep["cases"])]
    lines.append("  %-12s %-13s %s" % ("backend", "status", "values"))
    for r in rep["results"]:
        vals = "" if not r.values else str([None if v is None else round(v, 6) for v in r.values])
        tail = vals if vals else ("(%s)" % r.note if r.note else "")
        lines.append("  %-12s %-13s %s" % (r.lang, r.status, tail))
    s = rep["summary"]
    lines.append(
        "  --> %d/%d runnable backends agree across %d case(s); %d emitted-but-unverified%s"
        % (
            s["verified_agree"],
            s["runnable_backends"] - 1,  # exclude the reference itself from the denominator
            len(rep["cases"]),
            s["emitted_unverified"],
            ("; DISAGREE: " + ", ".join(s["disagree"])) if s["disagree"] else "",
        )
    )
    return "\n".join(lines)


def _parse_args(specs: Sequence[str]) -> List[Tuple[float, ...]]:
    cases: List[Tuple[float, ...]] = []
    for spec in specs:
        parts = [float(x) for x in spec.replace(" ", "").split(",") if x != ""]
        while len(parts) < 3:
            parts.append(0.0)
        cases.append(tuple(parts[:3]))
    return cases


def _demo() -> int:
    print("POLYGLOT CONFORMANCE  (honest: runs only what this box can run)\n")
    print(">> a real DECISION (not just arithmetic): mul gt  ==  (a > b*c) ? 1 : 0")
    print(format_report(conformance(P.program_bytes("mul", "gt"), [(2.0, 3.0, 4.0), (10.0, 3.0, 2.0)])))
    print("\n>> a KNOWN divergence the harness must CATCH: round, on a .5 value")
    print("   (Python round-half-to-even 2.0  vs  JS/Rust half-up/away 3.0)")
    print(format_report(conformance(P.program_bytes("round"), [(2.0, 3.0, 2.5)])))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="scbe-conformance", description="differential conformance for polyglot backends")
    ap.add_argument("program", nargs="?", help="op names, e.g. 'mul gt'")
    ap.add_argument("--args", action="append", default=[], metavar="A,B,C", help="an input case (repeatable)")
    ap.add_argument("--demo", action="store_true", help="run the canned demo (agreement + a caught divergence)")
    a = ap.parse_args(list(argv) if argv is not None else None)
    if a.demo or not a.program:
        return _demo()
    cases = _parse_args(a.args) or [(2.0, 3.0, 4.0)]
    print(format_report(conformance(P.program_bytes(*a.program.split()), cases)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
