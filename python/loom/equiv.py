"""Cross-language equivalence, behavioral equivalence, and the mirror check.

- ``cross_check``  — run the reference interpreter and the emitted Python (and
  Node/C if those toolchains are present) on the same inputs and confirm every
  backend produces the same output. The coherence the emitters guarantee, tested.
- ``behaviorally_equivalent`` — do two *different* programs produce the same
  output on a battery of inputs? (A "collision" in behavior-space — useful for an
  agent that generates many candidate solutions and wants to dedupe them.)
- ``mirror_check`` — round-trip a program through unparse→parse and report whether
  it comes back EXACTLY (a true mirror) or only behaviorally (a *near* mirror).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional

from . import emit as E
from . import machine as M


def run_reference(prog: M.Program, init: Optional[Dict[str, int]] = None, max_steps: int = 100_000) -> List[int]:
    return M.run(prog, init=init, max_steps=max_steps).output


def run_python_emit(prog: M.Program, init: Optional[Dict[str, int]] = None) -> List[int]:
    namespace: Dict[str, object] = {}
    exec(E.emit_python(prog, init=init, func_name="run"), namespace)  # our own generated code
    return list(namespace["run"]())


def _run_capture(cmd: List[str], cwd: Optional[str] = None) -> Optional[str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    return proc.stdout if proc.returncode == 0 else None


def _parse_int_line(text: Optional[str]) -> Optional[List[int]]:
    if text is None:
        return None
    text = text.strip()
    return [int(tok) for tok in text.split()] if text else []


def run_node(prog: M.Program, init: Optional[Dict[str, int]] = None) -> Optional[List[int]]:
    """Run the emitted JavaScript via node, if available. Returns None if node is absent."""
    if not shutil.which("node"):
        return None
    src = E.emit_js(prog, init=init) + "\nconsole.log(run().join(' '));\n"
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "loom.js")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(src)
        return _parse_int_line(_run_capture(["node", path]))


def run_c(prog: M.Program, init: Optional[Dict[str, int]] = None) -> Optional[List[int]]:
    """Compile + run the emitted C via gcc/cc, if available. Returns None if no compiler."""
    cc = shutil.which("gcc") or shutil.which("cc")
    if not cc:
        return None
    with tempfile.TemporaryDirectory() as d:
        src_path = os.path.join(d, "loom.c")
        exe_path = os.path.join(d, "loom.exe")
        with open(src_path, "w", encoding="utf-8") as fh:
            fh.write(E.emit_c(prog, init=init))
        if _run_capture([cc, src_path, "-O2", "-o", exe_path]) is None:
            return None
        return _parse_int_line(_run_capture([exe_path]))


def cross_check(prog: M.Program, inits: List[Dict[str, int]]) -> Dict[str, object]:
    """Confirm reference, Python-emit (and Node/C if present) agree on every input."""
    rows = []
    all_agree = True
    backends_used = {"reference", "python"}
    for init in inits:
        ref = run_reference(prog, init)
        results: Dict[str, Optional[List[int]]] = {"reference": ref, "python": run_python_emit(prog, init)}
        node = run_node(prog, init)
        if node is not None:
            results["node"] = node
            backends_used.add("node")
        c = run_c(prog, init)
        if c is not None:
            results["c"] = c
            backends_used.add("c")
        present = [v for v in results.values() if v is not None]
        agree = all(v == present[0] for v in present)
        all_agree = all_agree and agree
        rows.append({"init": init, "results": results, "agree": agree})
    return {"all_agree": all_agree, "backends": sorted(backends_used), "rows": rows}


def behaviorally_equivalent(src_a: str, src_b: str, inits: List[Dict[str, int]]) -> bool:
    """Two programs are behaviorally equivalent on a battery iff they agree on every input."""
    pa, pb = M.parse(src_a), M.parse(src_b)
    return all(M.run(pa, init).output == M.run(pb, init).output for init in inits)


def mirror_check(source: str, inits: Optional[List[Dict[str, int]]] = None) -> Dict[str, bool]:
    """Round-trip a program (unparse->parse) and classify the symmetry.

    exact_mirror     : structurally identical after the round-trip.
    near_mirror      : behaviorally identical but NOT structurally (e.g. jump-to-end
                       materialized as an explicit halt) — symmetric in effect, not in form.
    broken           : behavior changed under the round-trip (should never happen).
    """
    inits = (
        inits
        if inits is not None
        else [{}, {r: 1 for r in M.parse(source).registers}, {r: 3 for r in M.parse(source).registers}]
    )
    p1 = M.parse(source)
    p2 = M.parse(M.unparse(p1))
    exact = p1.signature() == p2.signature()
    behavioral = all(M.run(p1, init).output == M.run(p2, init).output for init in inits)
    return {
        "exact_mirror": exact and behavioral,
        "near_mirror": behavioral and not exact,
        "broken": not behavioral,
    }
