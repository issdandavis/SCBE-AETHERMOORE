"""Machine Crystal: geometric routing object for Turing-complete language lanes.

The crystal is a regular octahedron with eight faces. Each face is one of the
eight Brainfuck-class tape operations already used by ``bit_spine``:

    > < + - . , [ ]

That alphabet is Turing complete with unbounded tape and time. This module keeps
finite safety limits for local execution, so the implementation is a safe
runtime surface, not an infinite machine.

Two equivalent geometric control surfaces are provided:

* rotation: turn the octahedron until a face is active.
* interior light projection: project a ray from the center; the octant of the
  ray selects the face it exits through.

Language lanes can route into this object by lowering to the eight tape ops. If
they only provide opcode metadata, this module can assign a geometric address,
but that is provenance, not a semantic compiler.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable, Sequence

from .bit_spine import BF_TO_OP, OP_TO_BF, BitSpineError, SpineOp

Vector3 = tuple[float, float, float]


class MachineCrystalError(ValueError):
    """Invalid crystal geometry, program, or runtime transition."""


def _normal_for_index(index: int) -> Vector3:
    """Map a 3-bit face index to a cube-corner face normal.

    A regular octahedron's eight face normals point at the eight cube corners.
    The sign bits are therefore a direct geometric address.
    """

    if not 0 <= int(index) <= 7:
        raise MachineCrystalError(f"face index out of range: {index!r}")
    return (
        1.0 if index & 0b100 else -1.0,
        1.0 if index & 0b010 else -1.0,
        1.0 if index & 0b001 else -1.0,
    )


def _face_index_from_light(direction: Vector3) -> int:
    x, y, z = direction
    if x == 0 or y == 0 or z == 0:
        raise MachineCrystalError(
            "light direction must not lie exactly on a face boundary"
        )
    return (
        (0b100 if x > 0 else 0)
        | (0b010 if y > 0 else 0)
        | (0b001 if z > 0 else 0)
    )


@dataclass(frozen=True, slots=True)
class CrystalFace:
    """One octahedral face and its tape-machine operation."""

    index: int
    normal: Vector3
    op: SpineOp
    symbol: str

    def packet(self) -> dict:
        return {
            "face": self.index,
            "normal": list(self.normal),
            "op": self.op.name,
            "op_id": int(self.op),
            "symbol": self.symbol,
        }


FACES: tuple[CrystalFace, ...] = tuple(
    CrystalFace(
        index=int(op),
        normal=_normal_for_index(int(op)),
        op=op,
        symbol=OP_TO_BF[op],
    )
    for op in SpineOp
)


FACE_BY_SYMBOL: dict[str, CrystalFace] = {face.symbol: face for face in FACES}
FACE_BY_OP: dict[SpineOp, CrystalFace] = {face.op: face for face in FACES}


@dataclass(frozen=True, slots=True)
class CrystalStep:
    """One geometric move through the Machine Crystal."""

    face: CrystalFace
    source: str = "unknown"

    def packet(self) -> dict:
        out = self.face.packet()
        out["source"] = self.source
        return out


@dataclass(frozen=True, slots=True)
class MachineCrystalProgram:
    """A sequence of crystal faces, equivalent to a tape-machine program."""

    steps: tuple[CrystalStep, ...]

    @classmethod
    def from_brainfuck(cls, source: str, *, source_label: str = "bf") -> "MachineCrystalProgram":
        steps: list[CrystalStep] = []
        for char in source:
            if char in FACE_BY_SYMBOL:
                steps.append(CrystalStep(FACE_BY_SYMBOL[char], source=source_label))
        return cls(tuple(steps))

    @classmethod
    def from_light(
        cls,
        directions: Iterable[Vector3],
        *,
        source_label: str = "light",
    ) -> "MachineCrystalProgram":
        steps = []
        for direction in directions:
            face_index = _face_index_from_light(direction)
            steps.append(CrystalStep(FACES[face_index], source=source_label))
        return cls(tuple(steps))

    @classmethod
    def from_ops(
        cls,
        ops: Iterable[SpineOp],
        *,
        source_label: str = "spine_op",
    ) -> "MachineCrystalProgram":
        return cls(tuple(CrystalStep(FACE_BY_OP[op], source=source_label) for op in ops))

    def symbols(self) -> str:
        return "".join(step.face.symbol for step in self.steps)

    def digest(self) -> str:
        return hashlib.sha256(self.symbols().encode("ascii")).hexdigest()

    def packet(self) -> dict:
        return {
            "schema": "scbe_machine_crystal_program_v1",
            "object": "regular_octahedron",
            "turing_complete_by": "reduction_to_8_op_tape_machine",
            "finite_runtime_limits": True,
            "symbol_count": len(self.steps),
            "symbols": self.symbols(),
            "sha256": self.digest(),
            "steps": [step.packet() for step in self.steps],
        }


SHAPE_SYMBOLS: dict[str, str] = {
    # Movement: slide on the crystal surface.
    "east": ">",
    "right": ">",
    "west": "<",
    "left": "<",
    # Value: grow or shrink the current lit cell.
    "sun": "+",
    "spark": "+",
    "moon": "-",
    "shade": "-",
    # IO: emit or absorb light.
    "eye": ".",
    "emit": ".",
    "mouth": ",",
    "read": ",",
    # Control: an open/closed ring is a loop gate.
    "ring": "[",
    "open": "[",
    "seal": "]",
    "close": "]",
}


@dataclass(frozen=True, slots=True)
class ShapeExpr:
    """One shape expression before lowering to crystal faces."""

    shape: str
    count: int = 1

    def symbol(self) -> str:
        key = self.shape.strip().lower()
        if key not in SHAPE_SYMBOLS:
            raise MachineCrystalError(f"unknown shape expression: {self.shape!r}")
        return SHAPE_SYMBOLS[key]

    def symbols(self) -> str:
        if self.count < 0:
            raise MachineCrystalError("shape expression count must be non-negative")
        return self.symbol() * self.count

    def packet(self) -> dict:
        return {
            "shape": self.shape,
            "count": self.count,
            "symbol": self.symbol(),
            "symbols": self.symbols(),
        }


def parse_shape_expression(text: str) -> tuple[ShapeExpr, ...]:
    """Parse a compact shape-expression line.

    Grammar:

    ```text
    expr    := term*
    term    := name [ "*" integer ]
    name    := ascii letters, "_", or "-"
    ```

    Example:

    ```text
    sun*3 eye
    ```

    lowers to:

    ```text
    +++.
    ```
    """

    exprs: list[ShapeExpr] = []
    for raw in text.replace(",", " ").split():
        if "*" in raw:
            name, count_text = raw.split("*", 1)
            if not count_text.isdigit():
                raise MachineCrystalError(f"invalid shape repeat count: {raw!r}")
            count = int(count_text)
        else:
            name, count = raw, 1
        if not name:
            raise MachineCrystalError(f"invalid empty shape expression: {raw!r}")
        exprs.append(ShapeExpr(name, count))
    return tuple(exprs)


def program_from_shapes(
    shapes: Sequence[ShapeExpr],
    *,
    source_label: str = "shape_expr",
) -> MachineCrystalProgram:
    """Lower shape expressions to a MachineCrystalProgram."""

    symbols = "".join(shape.symbols() for shape in shapes)
    return MachineCrystalProgram.from_brainfuck(symbols, source_label=source_label)


def run_shape_expression(
    text: str,
    *,
    input_bytes: bytes = b"",
    max_steps: int = 100_000,
) -> dict:
    """Parse, lower, and run a shape-expression program."""

    shapes = parse_shape_expression(text)
    program = program_from_shapes(shapes)
    receipt = run_crystal(program, input_bytes=input_bytes, max_steps=max_steps)
    return {
        "schema": "scbe_shape_expression_receipt_v1",
        "source": text,
        "shape_expressions": [shape.packet() for shape in shapes],
        "program": program.packet(),
        "receipt": receipt,
    }


@dataclass(frozen=True, slots=True)
class CrystalAddress:
    """Geometric address for an external language/opcode.

    This is routing metadata. It does not claim that the external opcode has
    been semantically lowered to the tape-machine program.
    """

    language: str
    symbol: str
    face: CrystalFace
    note: str

    def packet(self) -> dict:
        out = self.face.packet()
        out.update(
            {
                "language": self.language,
                "symbol": self.symbol,
                "note": self.note,
            }
        )
        return out


def address_symbol(language: str, symbol: str, *, opcode_id: int | None = None) -> CrystalAddress:
    """Assign a stable geometric address to a language symbol.

    If an opcode id is known, the low three bits choose the face. Otherwise the
    SHA-256 digest of ``language:symbol`` chooses a deterministic face.
    """

    if opcode_id is None:
        payload = f"{language}:{symbol}".encode("utf-8")
        face_index = hashlib.sha256(payload).digest()[0] & 0b111
    else:
        face_index = int(opcode_id) & 0b111
    return CrystalAddress(
        language=language,
        symbol=symbol,
        face=FACES[face_index],
        note="geometric_address_only_not_semantic_lowering",
    )


def address_ca_opcode(op_byte: int) -> CrystalAddress:
    """Address a Cassisivadan opcode byte on the crystal.

    This uses ``tongue_isa.lookup_ca`` for real CA opcode names. The result is a
    face address, not a complete semantic lowering.
    """

    from .tongue_isa import lookup_ca

    op_id, name = lookup_ca(int(op_byte))
    return address_symbol("CA", f"{name}:0x{op_id:02X}", opcode_id=op_id)


def _jump_table(symbols: str) -> dict[int, int]:
    stack: list[int] = []
    jumps: dict[int, int] = {}
    for index, char in enumerate(symbols):
        if char == "[":
            stack.append(index)
        elif char == "]":
            if not stack:
                raise MachineCrystalError("unmatched loop end face")
            start = stack.pop()
            jumps[start] = index
            jumps[index] = start
    if stack:
        raise MachineCrystalError("unmatched loop start face")
    return jumps


def run_crystal(
    program: MachineCrystalProgram,
    *,
    input_bytes: bytes = b"",
    max_steps: int = 100_000,
    max_cells: int = 65_536,
) -> dict:
    """Execute the crystal program as a finite-safety tape runtime."""

    symbols = program.symbols()
    jumps = _jump_table(symbols)
    tape: dict[int, int] = {}
    pointer = 0
    pc = 0
    steps = 0
    input_index = 0
    output = bytearray()

    while pc < len(symbols):
        steps += 1
        if steps > max_steps:
            raise MachineCrystalError("crystal runtime exceeded max_steps")
        if len(tape) > max_cells:
            raise MachineCrystalError("crystal runtime exceeded max_cells")

        symbol = symbols[pc]
        if symbol == ">":
            pointer += 1
        elif symbol == "<":
            pointer -= 1
        elif symbol == "+":
            tape[pointer] = (tape.get(pointer, 0) + 1) & 0xFF
        elif symbol == "-":
            tape[pointer] = (tape.get(pointer, 0) - 1) & 0xFF
        elif symbol == ".":
            output.append(tape.get(pointer, 0))
        elif symbol == ",":
            if input_index < len(input_bytes):
                tape[pointer] = input_bytes[input_index]
                input_index += 1
            else:
                tape[pointer] = 0
        elif symbol == "[":
            if tape.get(pointer, 0) == 0:
                pc = jumps[pc]
        elif symbol == "]":
            if tape.get(pointer, 0) != 0:
                pc = jumps[pc]
        else:
            raise MachineCrystalError(f"invalid crystal symbol: {symbol!r}")

        pc += 1

    occupied = sorted(pos for pos, value in tape.items() if value)
    window: dict[int, int] = {}
    for pos in occupied[:32]:
        window[pos] = tape[pos]

    return {
        "schema": "scbe_machine_crystal_receipt_v1",
        "program_sha256": program.digest(),
        "symbols": symbols,
        "steps": steps,
        "pointer": pointer,
        "input_len": len(input_bytes),
        "output_hex": bytes(output).hex(),
        "output_text": bytes(output).decode("utf-8", errors="replace"),
        "nonzero_cells": len(occupied),
        "tape_window": window,
    }


def demo_receipt() -> dict:
    """Small receipt: turn four faces (+++.) and emit byte 0x03."""

    program = MachineCrystalProgram.from_brainfuck("+++.", source_label="demo")
    address = address_symbol("python", "increment_and_emit", opcode_id=2)
    shape = run_shape_expression("sun*3 eye")
    return {
        "program": program.packet(),
        "receipt": run_crystal(program),
        "shape_receipt": shape,
        "sample_address": address.packet(),
    }


def main() -> int:
    print(json.dumps(demo_receipt(), indent=2, sort_keys=True))
    return 0


__all__ = [
    "CrystalAddress",
    "CrystalFace",
    "CrystalStep",
    "FACES",
    "MachineCrystalError",
    "MachineCrystalProgram",
    "SHAPE_SYMBOLS",
    "ShapeExpr",
    "address_ca_opcode",
    "address_symbol",
    "demo_receipt",
    "parse_shape_expression",
    "program_from_shapes",
    "run_crystal",
    "run_shape_expression",
]


if __name__ == "__main__":
    raise SystemExit(main())
