# Mixed Expression Coding Lane - 2026-06-27

Status: batter. This is a staging spec, not a compiled product yet.

## Goal

Let the SCBE conlang/code systems talk to each other in one program packet.
Each segment can use the brush that fits the job:

- AV / Python: readable state and human-debuggable glue.
- CA / Haskell target view: pure transforms and fold/reduce semantics.
- UM / C-family or assembly view: fast edge kernels and low-level control.
- CA / STIB binary: tiny exact gaps, the speckles that normal syntax does not capture cleanly.
- KO, RU, DR lanes: alternate program shapes, stack/thread/build views, and teaching forms.

The point is not to make syntax stranger. The point is to give the agent enough
verified brushes that it can build without inventing unsafe tools mid-task.

## Existing local anchors

The current SCBE codebase already has useful pieces:

- `python/scbe/tongue_code_lanes.py` maps tongues to code-lane families.
- `python/scbe/tongue_isa.py` lowers CA opcode programs to targets including Python, C, Haskell, Rust, Zig, Julia, Go, and TypeScript.
- `python/scbe/tongue_isa_binary.py` defines the STIB binary route for canonical tongue programs.
- `src/coding_spine/shared_ir.py` and `src/coding_spine/command_compiler.py` are the bridge toward real executable plans.

## Packet rule

A mixed expression packet records:

- `tongue`: which SCBE language/lens owns the segment.
- `language`: host syntax or target view.
- `role`: what this segment is responsible for.
- `weight`: how much authority it has in the combined expression.
- `text`: the human-readable or host-language form.
- `opcodes`: symbolic low-level operations when known.
- `binary_hex`: exact micro-marker for STIB/binary gaps.
- `constraints`: what must stay true when lowering.
- `oven`: what must compile/run before release.

Weights do not mean truth. Weights mean routing authority. The oven still wins.

## Example mixed expression

```text
AV:python        raw_value = request.get('value'); value = normalize(raw_value)
CA:haskell       score xs = foldl caAdd 0 xs
UM:cpp_style     double clamp_corner(double v) { ... }
CA:stib_hex      STIB-like staging bytes for the tiny rounding/corner speckle
```

This is allowed as batter. It is not allowed as a product claim until the lane
lowers it, compiles it, runs it, and emits a receipt.

## Why the binary speckle matters

Normal languages are broad brushes. They are good for structure, but they can be
awkward at tiny exact boundaries: rounding corners, opcode flags, byte layouts,
policy bits, or reversible-state details. The STIB/binary segment is the small
white-paint speckle: not the whole painting, but the exact dot that makes the
picture honest.

## Compile-is-the-oven rule

This lane follows the SCBE oven doctrine:

1. Batter: mixed-expression packet exists.
2. Lowered: packet maps to shared IR / tongue ISA / STIB.
3. Baked: generated target compiles.
4. Served: generated target runs in front of the user and emits a receipt.
5. Burnt: any mismatch, crash, or unsupported target blocks release.

## Current prototype

Prototype script:

```powershell
python C:\Users\issda\SCBE-AETHERMOORE\scripts\system\mixed_expression_lane.py --brief
python C:\Users\issda\SCBE-AETHERMOORE\scripts\system\mixed_expression_lane.py --out mixed_packet.json
```

I did not run it in this pass. It is intentionally staged as code batter until
we explicitly bake it.

## Next build steps

1. Connect `ca_binary_speckle` to the official `tongue_isa_binary.py` encoder.
2. Connect CA symbolic opcodes to the real `tongue_isa.py` opcode table.
3. Add a lowering pass from mixed packet to `shared_ir.RouteIR`.
4. Add a tiny oven command that compiles/runs one emitted target and writes a receipt.
5. Add one training pair where a small model learns to produce the packet, not raw unverified code.
