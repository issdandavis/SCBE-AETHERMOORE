"""Programmatic synthesis of Loom programs for simple arithmetic.

Generate a Loom program from a spec, without an LLM — the deterministic stand-in
for a 'build' executor in a crank workflow. Each program is plain Loom assembly
(see ``machine``), so it inherits loom's cross-language emit and loop/mirror checks.

    add:      out = a + b   (destroys a, b)
    multiply: out = a * b   (destroys a; uses scratch; preserves b)
"""

from __future__ import annotations

SUPPORTED = ("add", "multiply")


def arith_program(op: str, a: str = "r1", b: str = "r2", out: str = "r3", scratch: str = "r4") -> str:
    """Return Loom assembly computing `op` of registers a and b into out."""
    if op == "add":
        return "\n".join(
            [
                f"a0: dec {a} a1",  # while a > 0: out += 1
                f"    inc {out}",
                "    jmp a0",
                f"a1: dec {b} a2",  # while b > 0: out += 1
                f"    inc {out}",
                "    jmp a1",
                f"a2: out {out}",
                "    halt",
            ]
        )
    if op == "multiply":
        return "\n".join(
            [
                f"m0: dec {a} m3",  # for each unit of a:
                f"m1: dec {b} m2",  # add b into out, stashing b into scratch
                f"    inc {out}",
                f"    inc {scratch}",
                "    jmp m1",
                f"m2: dec {scratch} m0",  # restore b from scratch
                f"    inc {b}",
                "    jmp m2",
                f"m3: out {out}",
                "    halt",
            ]
        )
    raise ValueError(f"unsupported op {op!r}; choose from {SUPPORTED}")
