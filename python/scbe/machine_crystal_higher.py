"""Higher-level Machine Crystal shapes.

This layer makes shape expressions useful without weakening the primitive
octahedral runtime in ``machine_crystal.py``.

Implemented ideas:

* discrete path curvature:
  each crystal face has a normal vector; a program has a sequence of face
  turn angles; first differences provide a path roughness signal.

* quasicrystal light path:
  deterministic golden-angle rays project through the octahedron and select
  faces. This is cut-and-project inspired, not a full crystallographic model.

* path-state injection:
  higher-level shapes lower into crystal programs only through a PHDM path-state
  gate. ALLOW executes, ESCALATE compiles but does not execute, DENY refuses.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Iterable, Sequence

from .machine_crystal import (
    CrystalFace,
    MachineCrystalError,
    MachineCrystalProgram,
    ShapeExpr,
    parse_shape_expression,
    program_from_shapes,
    run_crystal,
)
from .phdm_chapter6 import evaluate_path

PHI = (1.0 + 5.0**0.5) / 2.0
GOLDEN_ANGLE = 2.0 * math.pi * (1.0 - 1.0 / PHI)


HIGHER_SHAPE_MACROS: dict[str, str] = {
    # Base aliases, kept here so higher expressions can mix with primitive ones.
    "star": "+",
    "sun": "+",
    "shadow": "-",
    "moon": "-",
    "cube": ">",
    "step": ">",
    "root": "<",
    "back": "<",
    "lens": ".",
    "eye": ".",
    "mouth": ",",
    # Real tape-machine macros.
    # Move current cell into the right neighbor and clear current.
    "triangle": "[->+<]",
    "triangle_add": "[->+<]",
    # Copy current cell into the right neighbor while preserving current.
    "prism": "[->+>+<<]>>[-<<+>>]<<",
    "prism_split": "[->+>+<<]>>[-<<+>>]<<",
    # Clear current cell.
    "spiral": "[-]",
    "spiral_zero": "[-]",
}


@dataclass(frozen=True, slots=True)
class HigherShapeExpr:
    """One higher-level shape expression before macro lowering."""

    shape: str
    count: int = 1

    def macro(self) -> str:
        key = self.shape.strip().lower()
        if key in HIGHER_SHAPE_MACROS:
            return HIGHER_SHAPE_MACROS[key]
        # Fall back to primitive shape vocabulary from machine_crystal.py.
        primitive = ShapeExpr(key, 1)
        return primitive.symbols()

    def symbols(self) -> str:
        if self.count < 0:
            raise MachineCrystalError("higher shape repeat count must be non-negative")
        return self.macro() * self.count

    def packet(self) -> dict:
        return {
            "shape": self.shape,
            "count": self.count,
            "macro": self.macro(),
            "symbols": self.symbols(),
        }


def parse_higher_shape_expression(text: str) -> tuple[HigherShapeExpr, ...]:
    """Parse higher shape terms with optional ``*count`` repeats."""

    exprs: list[HigherShapeExpr] = []
    for raw in text.replace(",", " ").split():
        if "*" in raw:
            name, count_text = raw.split("*", 1)
            if not count_text.isdigit():
                raise MachineCrystalError(f"invalid higher shape repeat count: {raw!r}")
            count = int(count_text)
        else:
            name, count = raw, 1
        if not name:
            raise MachineCrystalError(f"invalid empty higher shape expression: {raw!r}")
        exprs.append(HigherShapeExpr(name, count))
    return tuple(exprs)


def program_from_higher_shapes(
    shapes: Sequence[HigherShapeExpr],
    *,
    source_label: str = "higher_shape",
) -> MachineCrystalProgram:
    symbols = "".join(shape.symbols() for shape in shapes)
    return MachineCrystalProgram.from_brainfuck(symbols, source_label=source_label)


def face_turn_angle(left: CrystalFace, right: CrystalFace) -> float:
    """Angle in radians between two crystal face normals."""

    ax, ay, az = left.normal
    bx, by, bz = right.normal
    dot = ax * bx + ay * by + az * bz
    na = math.sqrt(ax * ax + ay * ay + az * az)
    nb = math.sqrt(bx * bx + by * by + bz * bz)
    value = max(-1.0, min(1.0, dot / (na * nb)))
    return math.acos(value)


def discrete_path_curvature(program: MachineCrystalProgram) -> dict:
    """Discrete curvature/roughness profile for a face path.

    This is not the Julia-Caratheodory angular derivative. It is a local
    path metric: face-normal turn angles plus first differences along the
    crystal program.
    """

    faces = [step.face for step in program.steps]
    angles = [face_turn_angle(a, b) for a, b in zip(faces, faces[1:])]
    dtheta = [b - a for a, b in zip(angles, angles[1:])]
    return {
        "schema": "scbe_machine_crystal_discrete_path_curvature_v1",
        "angle_count": len(angles),
        "turn_angles_rad": [round(v, 10) for v in angles],
        "turn_delta_rad": [round(v, 10) for v in dtheta],
        "total_turn_rad": round(sum(abs(v) for v in angles), 10),
        "curvature_energy": round(sum(abs(v) for v in dtheta), 10),
        "max_turn_rad": round(max(angles) if angles else 0.0, 10),
    }


def angular_relation(left: CrystalFace, right: CrystalFace) -> float:
    """Deprecated compatibility alias for ``face_turn_angle``."""

    return face_turn_angle(left, right)


def angular_derivative(program: MachineCrystalProgram) -> dict:
    """Deprecated compatibility alias for ``discrete_path_curvature``."""

    return discrete_path_curvature(program)


def quasicrystal_light_program(
    count: int,
    *,
    phase: float = 0.0,
    source_label: str = "quasicrystal_light",
) -> MachineCrystalProgram:
    """Generate a deterministic quasiperiodic light-projection face path."""

    if count < 0:
        raise MachineCrystalError("quasicrystal light count must be non-negative")
    directions = []
    for i in range(count):
        a = phase + (i + 1) * GOLDEN_ANGLE
        b = phase / PHI + (i + 1) * GOLDEN_ANGLE / PHI
        c = phase * PHI + (i + 1) * GOLDEN_ANGLE * PHI
        x = math.cos(a)
        y = math.sin(b)
        z = math.cos(c)
        # Avoid exact boundaries, keeping the projection deterministic.
        if abs(x) < 1e-12:
            x = 1e-12
        if abs(y) < 1e-12:
            y = -1e-12
        if abs(z) < 1e-12:
            z = 1e-12
        directions.append((x, y, z))
    return MachineCrystalProgram.from_light(directions, source_label=source_label)


def path_state_inject(
    shape_text: str,
    phdm_path: str | Iterable[str | int],
    *,
    input_bytes: bytes = b"",
    budget: float = 100.0,
    max_steps: int = 100_000,
) -> dict:
    """Gate a higher-shape program through a PHDM path state."""

    phdm = evaluate_path(phdm_path, budget=budget)
    shapes = parse_higher_shape_expression(shape_text)
    program = program_from_higher_shapes(shapes)
    curvature = discrete_path_curvature(program)
    decision = phdm["geoseal"]["decision"]
    core = {
        "schema": "scbe_machine_crystal_path_state_injection_v1",
        "source": shape_text,
        "shape_expressions": [shape.packet() for shape in shapes],
        "program": program.packet(),
        "path_curvature": curvature,
        "phdm": phdm,
    }

    if decision == "DENY":
        core["injection"] = {
            "decision": "REFUSED",
            "reason": "phdm_path_state_denied",
        }
        return core
    if decision == "ESCALATE":
        core["injection"] = {
            "decision": "COMPILED_NOT_EXECUTED",
            "reason": "phdm_path_state_escalated",
        }
        return core

    receipt = run_crystal(program, input_bytes=input_bytes, max_steps=max_steps)
    core["injection"] = {
        "decision": "EXECUTED",
        "receipt": receipt,
    }
    return core


def benchmark_cases() -> dict:
    """Run correctness and path-state benchmarks for higher shapes."""

    cases = []
    failures = []
    safe_path = "Tetrahedron,Cube,Octahedron,Dodecahedron,Icosahedron"
    risk_path = "Tetrahedron,Great Stellated Dodecahedron,Cube"
    for value in range(65):
        expr = f"star*{value} prism cube lens"
        result = path_state_inject(expr, safe_path, max_steps=200_000)
        out_hex = result["injection"]["receipt"]["output_hex"]
        expected = bytes([value & 0xFF]).hex()
        ok = out_hex == expected
        cases.append({"expr": expr, "expected": expected, "actual": out_hex, "ok": ok})
        if not ok:
            failures.append(cases[-1])

    quasi_metrics = []
    for idx in range(128):
        program = quasicrystal_light_program(64, phase=idx / PHI)
        metric = discrete_path_curvature(program)
        quasi_metrics.append(
            {
                "idx": idx,
                "sha256": program.digest(),
                "symbols_sha256": hashlib.sha256(program.symbols().encode("ascii")).hexdigest(),
                "curvature_energy": metric["curvature_energy"],
                "total_turn_rad": metric["total_turn_rad"],
            }
        )

    safe_exec = path_state_inject("star*5 prism cube lens", safe_path)
    risk_block = path_state_inject("star*5 prism cube lens", risk_path)

    return {
        "schema": "scbe_machine_crystal_higher_benchmark_v1",
        "copy_emit_cases": len(cases),
        "copy_emit_failures": failures,
        "copy_emit_passed": len(failures) == 0,
        "quasicrystal_programs": len(quasi_metrics),
        "quasicrystal_unique_hashes": len({m["sha256"] for m in quasi_metrics}),
        "quasicrystal_curvature_min": min(m["curvature_energy"] for m in quasi_metrics),
        "quasicrystal_curvature_max": max(m["curvature_energy"] for m in quasi_metrics),
        "safe_path_decision": safe_exec["injection"]["decision"],
        "safe_path_output_hex": safe_exec["injection"]["receipt"]["output_hex"],
        "risk_path_decision": risk_block["injection"]["decision"],
        "risk_path_reason": risk_block["injection"]["reason"],
    }


def main() -> int:
    print(json.dumps(benchmark_cases(), indent=2, sort_keys=True))
    return 0


__all__ = [
    "HIGHER_SHAPE_MACROS",
    "HigherShapeExpr",
    "discrete_path_curvature",
    "face_turn_angle",
    "angular_derivative",
    "angular_relation",
    "benchmark_cases",
    "parse_higher_shape_expression",
    "path_state_inject",
    "program_from_higher_shapes",
    "quasicrystal_light_program",
]


if __name__ == "__main__":
    raise SystemExit(main())
