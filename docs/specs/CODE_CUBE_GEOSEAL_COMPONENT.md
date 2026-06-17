# CodeCube GeoSeal Component

## Purpose

CodeCube is the functional software core for a future physical coding cube.

The physical object is deferred. The current product component proves the semantics:

- one center project representation
- six functional faces
- twist operations that mutate or project the center
- target language faces
- command preflight before execution
- receipt output

## CLI

```bash
geoseal code-cube "build a todo app with auth and tests" --language rust --twist tests.backend --json
```

Alias:

```bash
geoseal codecube "payment page with checkout receipt"
```

Manifold target:

```bash
geoseal code-cube "station safe-mode controller" --target manifold --dimensions 8 --moduli 7,11,13 --twist security.deploy --json
```

AI control surface:

```bash
geoseal code-cube "safe-mode controller" --target manifold --pitch 15 --yaw -20 --roll 5 --speed 0.7 --json
```

## Center

The center is a canonical app IR:

- entities
- actions
- constraints
- invariants

The center is the source of truth. Faces are projections, not separate apps.

## Faces

Structural faces:

- `frontend` - routes, components, state, responsive checks
- `backend` - handlers, validation, services, receipts
- `data` - entities, relations, indexes, seed records
- `tests` - unit tests, route tests, safety tests, smoke tests
- `security` - preflight checks, secret boundaries, deny rules
- `deploy` - env vars, build command, healthcheck, rollback note

Language faces:

- `python`
- `javascript`
- `typescript`
- `rust`
- `go`
- `sql`
- `markdown`

## Twists

Twists are operations, not visual effects:

- `frontend.backend` binds UI actions to API routes.
- `backend.data` binds handlers to schema.
- `tests.backend` generates tests from backend actions.
- `security.deploy` runs command preflight and deploy gate.
- `language.rotate` emits the selected language face from the center IR.

## Safety

The component does not execute shell commands. It emits suggested commands with GeoSeal preflight decisions.

Current safety contract:

- `executes_shell: false`
- destructive commands are described and preflighted only
- physical hardware claim is explicitly excluded

## Manifold Target

`--target manifold` adds a second output face to the same CodeCube packet.

It emits:

- balanced ternary shuttle states per named face
- physical tongue/valve class mapping
- coprime residue bank addresses
- GeoSeal pressure tier
- twist schedule
- N-dimensional rotation basis
- center attitude controls: pitch, yaw, roll, speed

This is a software schedule only. It is not a fabrication plan and does not claim measured hardware performance.

### Center Attitude Control

The center can act like an AI steering frame.

The default instruction is a simple forward vector. Pitch, yaw, roll, and speed distribute that vector across additional dimensions before it becomes a twist schedule.

This lets an AI control work direction instead of only producing text:

- `pitch` biases vertical/depth movement through the task space.
- `yaw` biases lateral face selection.
- `roll` biases rotation/spin through alternate faces.
- `speed` scales how aggressively the rotation schedule fires.

The output is a `geoseal_center_attitude_v1` packet. It is a navigation/control abstraction for AI work, not aircraft dynamics.

### Rotation Model

The target uses three compatible rotation ideas:

- **Plane rotations:** each twist chooses an `(i, j)` state plane and emits an `SO(n)` generator such as `R_1_4`.
- **Hyperbolic rotations:** gated/security transitions emit a boost-like rapidity packet, modeled as an `SO(n-1,1)` pressure/privilege gate.
- **Rubix generators:** named twists such as `tests.backend` and `security.deploy` are discrete moves in the allowed operation graph.

The point is not visual rotation. The point is a reversible, auditable operation schedule over the center IR.

## Existing System Inputs

CodeCube should progressively integrate these existing SCBE systems:

- `python/scbe/cube_token.py` - bijective token faces
- `python/scbe/cube_faces.py` - core, chemistry, code, governance, Wolfram faces
- `python/scbe/polyglot.py` - one opcode core to multiple language faces
- `python/scbe/blocks.py` - interlocking blocks and destructive-operation gates
- `docs/benchmarks/RUBIX_BROWSER_HYPERCUBE_BENCHMARK.md` - permission face routing

## Next Build

1. Add `--emit` to write a project packet into an output directory.
2. Add `--from-repo` to build the center IR from a local repo scan.
3. Add a web product page for `/code-cube`.
4. Add a visible twist stage to the terminal UI.
5. Add manifold packet export to research artifacts.
6. Later: map IMU/BLE physical cube events to the same twist IDs.
