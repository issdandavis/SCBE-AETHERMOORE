# Motion Assembly Schema

Status: draft v1
Last updated: 2026-05-04

## Purpose

Specify the `motion_assembly` payload that lets the existing 12-lane SCBE
code-packet describe rows in the mechanical-motion domain (drones, arms,
humanoids, modular-combinable platforms) without forking the spine.

## Non-goals

- Replace any existing lane (`binary`, `tokenizer`, `transport`, `labels`,
  `language_views`, `braille_lane`, `stisa`, `structural_parse`,
  `scip_symbol_index`, `semantic_token_bridge`, `route_ir`,
  `execution_lane`, `native_tokenization`, `atomic_states`,
  `ternary_semantics`, `semantic_expression`).
- Introduce a new top-level packet family parallel to the code packet.
- Inflate the 899-card grounded floor. Motion ops fold into existing
  `phase_operation` slots.

## Three locked rules

1. **`motion_assembly` is a nested payload under `semantic_expression`.**
   Not a sibling of `semantic_expression`. Not a top-level packet field.
   Motion is a semantic descriptor of the row, so it lives inside the
   field that already carries semantic descriptors.
2. **ASCII-only field names.** Use `omega_x`, `omega_y`, `omega_z`, never
   `ωx`/`ωy`/`ωz`. Greek and other non-ASCII glyphs are forbidden in
   keys, values, and emitted JSON. Windows toolchains, JSONL pipelines,
   and tokenizer round-trips stay boring.
3. **Mechanical motion is a domain overlay, not a new tokenizer spine.**
   The byte-level SS1 tokenizer, braille cell lane, STIB envelope, and
   ternary semantics are reused unchanged. Motion only adds an overlay
   that the same model decoder can read alongside code or chemistry.

## Required shape

A row is a normal SCBE code-weight packet (`scbe-code-weight-packet-v1`)
with two additions:

```
{
  "version": "scbe-code-weight-packet-v1",
  ... (all existing 12+ lanes unchanged) ...
  "labels": {
    "conlang": "...",
    "anchor_runtime": "...",   # executable language
    "anchor_spirit": "..."     # conlang / dense-bundle metaphor
  },
  "semantic_expression": {
    "label": "...",
    "gloss": "...",
    "quarks": [...],
    "motion_assembly": { ... }   # nested motion overlay
  }
}
```

### `motion_assembly` payload

```
motion_assembly:
  schema_version: "scbe-motion-assembly-v1"
  platform_id: <str>                        # unique per platform
  swarm_id: <str | null>                    # null for solo
  role: <enum>                              # see Role vocab below
  morphology_state: <enum>                  # see Morphology vocab below
  combine_topology: <str | null>            # which sub-frame when combined
  pilot_layers: [PilotLayer, ...]           # >= 1 entry
  comm_graph:
    edges: [CommEdge, ...]                  # may be empty
    global_clock_t: <float>
    local_clock_t: <float>
  embodiment_passport:
    urdf_uri: <str | null>
    mjcf_uri: <str | null>
    dof_schema: [DoFEntry, ...]
    thrust_to_weight: <float | null>
    motor_count: <int | null>
  invariants:
    joint_limits_ok: <bool>
    motor_saturation_ok: <bool>
    attitude_bounds_ok: <bool>
    energy_budget_ok: <bool>
    collision_free: <bool>
    morphology_transition_safe: <bool>
```

### Sub-records

```
PilotLayer:
  layer: <enum>                              # closed vocab below
  model_id: <str>
  confidence: <float in [0.0, 1.0]>
  action_token: <str | null>                 # SS1-tokenized command
  action_vector: [<float>, ...] | null       # raw continuous, e.g. CTBR len 4
  action_chunk_fast: [<int>, ...] | null     # FAST/FAST+ DCT-BPE token IDs
  horizon_H: <int | null>                    # action chunk horizon
  control_hz: <float | null>                 # control loop rate

CommEdge:
  src: <str>
  dst: <str>
  attn_weight: <float>
  msg_token_ids: [<int>, ...]

DoFEntry:
  name: <str>                                # ASCII-only joint/axis name
  min: <float>
  max: <float>
  vel_limit: <float>
  torque_limit: <float | null>
```

## Closed vocabularies

`role`: `lead | dynamics | perception | comms | sensor | auth | free`

`morphology_state`: `separated | combining | combined | transitioning`

`pilot_layers[].layer`: `strategic | tactical | trajectory | attitude_rate | perception | operator`

## Anchor values for motion (clarification of existing convention)

`anchor_runtime` and `anchor_spirit` follow the tongue's existing language
map. They are NOT motion-specific.

- `anchor_runtime`: tongue's runtime language (KO=python, AV=typescript,
  RU=rust, CA=c, UM=julia, DR=haskell; extended GO=go, ZIG=zig).
- `anchor_spirit`: tongue's spirit language (AV=javascript,
  CA=mathematica, UM=haskell, DR=markdown). For tongues without a spirit
  override, `anchor_spirit` equals `anchor_runtime`.

Motion-specific format references (URDF/MJCF/USD/etc.) live inside
`motion_assembly.embodiment_passport`, not in the row's anchors. This
keeps the cross-domain anchor convention consistent across code,
chemistry, and motion rows.

Both fields are required on every row. Do not flatten to one.

## CTBR convention (drones)

When `action_vector` carries collective-thrust + body-rate commands for a
quadrotor, length is exactly 4: `[thrust_norm, omega_x, omega_y, omega_z]`.

- `thrust_norm`: `float` in `[0.0, 1.0]` (collective thrust normalized to T_max)
- `omega_x`, `omega_y`, `omega_z`: `float`, body-frame angular rate setpoints
  in radians/second

Vehicle physical limits (`thrust_max_n`, `omega_max_rad_s`) belong in
`embodiment_passport`, not in the action vector itself.

## Forbidden vocabulary

Schema and emitted rows must not contain any of these substrings in
field names or string values (case-insensitive):

- `megazord`
- `morphin`
- `zord` (as standalone or suffix)
- `power_ranger`
- `power ranger`

This list exists because a vivid analogy was used during design and the
analogy is for mutual understanding, not product vocab. The test in
`tests/coding_spine/test_motion_assembly_schema.py` enforces it.

## Example: drone CTBR row (abbreviated)

```
labels:
  conlang: "Cassisivadan"
  anchor_runtime: "c"
  anchor_spirit: "mathematica"
semantic_expression:
  label: "drone_hover_hold"
  gloss: "hold position with neutral attitude"
  quarks: ["thrust_apply", "rate_hold"]
  motion_assembly:
    schema_version: "scbe-motion-assembly-v1"
    platform_id: "drone_03"
    swarm_id: null
    role: "dynamics"
    morphology_state: "separated"
    combine_topology: null
    pilot_layers:
      - layer: "tactical"
        model_id: "neural_fly_residual_v2"
        confidence: 0.91
        action_token: null
        action_vector: [0.55, 0.0, 0.0, 0.0]
        action_chunk_fast: null
        horizon_H: null
        control_hz: 100.0
    comm_graph:
      edges: []
      global_clock_t: 12.347
      local_clock_t: 12.341
    embodiment_passport:
      urdf_uri: null
      mjcf_uri: "models/quad_5in.xml"
      dof_schema: []
      thrust_to_weight: 4.2
      motor_count: 4
    invariants:
      joint_limits_ok: true
      motor_saturation_ok: true
      attitude_bounds_ok: true
      energy_budget_ok: true
      collision_free: true
      morphology_transition_safe: true
```

## Domain overlay model

The same code-packet emitter produces motion rows. The decoder reads the
packet through the existing 12-lane spine and finds `motion_assembly`
under `semantic_expression`. Code, chemistry, and motion are three
overlays on one substrate; the model only learns one tokenizer.
