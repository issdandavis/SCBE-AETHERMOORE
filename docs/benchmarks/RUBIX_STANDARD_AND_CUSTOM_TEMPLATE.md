# Rubix Standard And Custom Template

This note splits the cube work into two compatible lanes.

## Lane A: Standard Rubik Solver

Use a normal 3x3 cube when we need a public, externally understood control
surface.

- State format: 54 facelets in `URFDLB` order.
- Move alphabet: `U U' U2 R R' R2 F F' F2 D D' D2 L L' L2 B B' B2`.
- Solver: plug in a proven two-phase/Kociemba implementation rather than
  hand-rolling cube group search.
- Benchmark role: measure whether an agent can read a scrambled state, choose
  legal moves, and verify solved state through an external solver/checker.

The standard cube is useful because other people already understand it. It is
not the whole SCBE substrate; it is the shared ruler.

## Lane B: Custom Contract Cube

Use a custom Rubix cube when we want benchmark tasks to become a forced
action-gate surface.

Each custom cube maps benchmark work to rotations:

- Faces are task dimensions: contract, state, branch, syntax, safety, evidence.
- Layers are task stages: observe, extract, propose, execute, verify, seal.
- Moves are legal micro-actions: extract return shape, bind state field, build
  branch table, run check, apply deterministic joint, shadow-audit hidden.
- Denied faces block unsafe or irrelevant shortcuts.
- Receipts prove every rotation and final sealed state.

The model should not freeform solve the benchmark. It should choose the next
legal rotation from a small move menu. The backend can route that rotation to
tests, deterministic joints, property probes, or repair loops.

## Public/Hidden Rule

For known-answer tasks, public examples may guide the route, but hidden checks
decide verification.

A custom cube run should report:

- public_pass
- hidden_pass
- overfit_caught
- illegal_rotations
- denied_faces
- receipt_hash
- final_cube_state

## Next Build Target

Build `scripts/benchmark/rubix_contract_cube_benchmark.py` from the template in
`config/eval/rubix_contract_cube_template.v1.json`.

The first version should replay the top-30 functional benchmark:

1. Load public-only checks.
2. Convert each task to a custom cube state.
3. Let the model choose from legal rotations.
4. Force shadow contract audit when public-pass occurs.
5. Score hidden checks.
6. Emit receipts and a public/hidden overfit report.
