# Machine Crystal - Geometric Turing Object

Date: 2026-06-27
Status: Implemented as `python/scbe/machine_crystal.py`

## Core object

The Machine Crystal is a regular octahedron.

Reason: a regular octahedron has eight faces. The SCBE bit spine already uses
the eight Brainfuck-class tape operations:

```text
> < + - . , [ ]
```

That eight-operation tape alphabet is Turing complete with unbounded tape and
time. Therefore, any language that can lower into that alphabet can route
through this geometric object.

## Geometric control surfaces

### Rotation surface

Turn the crystal until a face is active. The active face selects one tape
operation.

### Interior light projection surface

Project a ray from the center of the crystal. The ray exits one of eight
octants, and the octant selects one face.

This means the same machine can be driven either by discrete rotations or by
continuous-looking projection angles.

## Face addressing

An octahedron's eight face normals point toward the eight cube corners:

```text
(-,-,-) (-,-,+) (-,+,-) (-,+,+)
(+,-,-) (+,-,+) (+,+,-) (+,+,+)
```

The sign pattern is a 3-bit address. Each address maps to one bit-spine op.

## Honest completeness claim

The crystal is Turing complete by reduction to the eight-op tape machine. The
local runtime is finite-limited for safety, so the code is a bounded executor.

Use this wording:

```text
The Machine Crystal is a geometric surface for a Turing-complete tape-machine
alphabet, with local finite execution limits.
```

Do not say:

```text
The finite Python runtime itself is infinite or physically Turing complete.
```

## Language routing

There are two levels:

1. Semantic lowering: a source language compiles to the eight tape ops. This is
   executable.
2. Geometric addressing: a symbol or opcode is assigned to a face. This is
   provenance/routing metadata and is not automatically semantic execution.

`machine_crystal.py` supports both, but keeps them separate.

## SCBE integration points

- `python/scbe/bit_spine.py`: source of the eight tape ops.
- `python/scbe/tongue_isa.py`: CA opcode names can be addressed onto faces.
- `python/scbe/tongue_code_lanes.py`: language lanes can route through the
  crystal once they lower to tape-machine ops.

## Minimal example

```python
from scbe.machine_crystal import MachineCrystalProgram, run_crystal

program = MachineCrystalProgram.from_brainfuck("+++.")
receipt = run_crystal(program)
assert receipt["output_hex"] == "03"
```

## Product use

This gives SCBE a single geometric compiler target:

```text
conlang / Python / Rust / C / Forth / binary
    -> compiler/lowering lane
    -> eight crystal faces
    -> bounded receipt runtime
```

The object can be shown visually in AetherDesk as a rotating crystal. Each turn
or projected light ray is not just UI; it is an addressable machine operation.

## Shape expressions

Shapes can be used as expressions by lowering each named shape to one crystal face.

Initial vocabulary:

| Shape | Crystal op | Meaning |
| --- | --- | --- |
| `east` / `right` | `>` | move tape pointer right |
| `west` / `left` | `<` | move tape pointer left |
| `sun` / `spark` | `+` | increase current cell |
| `moon` / `shade` | `-` | decrease current cell |
| `eye` / `emit` | `.` | emit current cell |
| `mouth` / `read` | `,` | read one input byte |
| `ring` / `open` | `[` | start loop gate |
| `seal` / `close` | `]` | close loop gate |

Example:

```text
sun*3 eye
```

lowers to:

```text
+++.
```

That emits byte `0x03` and returns a receipt through the same crystal runtime.

This is the first working form of:

```text
shape expression -> crystal faces -> tape runtime -> result receipt
```

The vocabulary is deliberately small. We can add higher-level shapes later:

- `triangle add`
- `cube memory`
- `spiral loop`
- `lens project`
- `prism split`

Those should lower through the same receipt path instead of becoming separate unverified metaphors.
