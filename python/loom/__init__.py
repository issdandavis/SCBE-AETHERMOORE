"""Loom — a tiny universal loop machine that weaves one program into many languages.

A minimal Turing-complete register (Minsky) machine for agentic code generation:
an agent writes one small program; Loom (1) emits it as runnable Python / JavaScript
/ C that are equal by construction, (2) reads the topology of its run to detect
infinite loops (a revisited state closes a loop — sound but, like all halting
analysis, incomplete), and (3) checks "near mirror symmetry" — whether a program
round-trips through unparse/parse exactly, or only behaviorally.

Quick start:

    from python.loom import parse, run, emit_python, cross_check, mirror_check

    prog = parse('''
        loop: dec r1 done   ; r2 += r1
              inc r2
              jmp loop
        done: out r2
              halt
    ''')
    run(prog, {"r1": 3, "r2": 4}).output      # -> [7]
    cross_check(prog, [{"r1": 3, "r2": 4}])    # all backends agree
"""

from .emit import emit_c, emit_js, emit_python
from .equiv import behaviorally_equivalent, cross_check, mirror_check, run_reference
from .machine import Instr, LoomSyntaxError, Program, RunResult, parse, run, unparse

__all__ = [
    "parse",
    "run",
    "unparse",
    "Program",
    "Instr",
    "RunResult",
    "LoomSyntaxError",
    "emit_python",
    "emit_js",
    "emit_c",
    "run_reference",
    "cross_check",
    "behaviorally_equivalent",
    "mirror_check",
]
