# Fleet Wafer State Machine

Status: design spec for SCBE software fleets.

Scope: coding-agent orchestration, sandbox coordination, cache namespacing, and promotion gates. This is not a physical drone-control or military-autonomy specification.

## Existing anchors

This spec composes the existing SCBE surfaces rather than replacing them:

- `docs/specs/SCBE_FLEET_GOVERNANCE_GATE.md` defines the fail-closed gate after an agent move packet.
- `docs/specs/CROSS_LANGUAGE_REACTION_STATE_MODEL.md` defines tongue roles, reaction packets, bounded output, and proof.
- `docs/specs/AGENT_BUS_WORKSPACE_FORMATION.md` defines the workspace folders and receipt/export layout.
- `external/codex-skills-live/scbe-github-sweep-sorter/references/formations.md` defines current software-agent formations.
- `src/fleet/types.ts` defines the live fleet agent/task data surface.

## Core rule

Every fleet gets its own software wafer.

The center of that wafer is a blank identity nucleus. It contains the fleet identity and namespace commitment only. It is not an executable cell, not a task, not a secret store, and not an opcode.

The center exists so every route, cache key, receipt, edge, and artifact can be tied back to the fleet that produced it. That prevents cross-fleet cache contamination and gives every fleet a stable quine root without making the root perform work.

## Fleet wafer object

Minimal serializable shape:

```json
{
  "schema_version": "scbe_fleet_wafer_v1",
  "fleet_id": "fleet-uuid-or-deterministic-id",
  "wafer_id": "wafer-uuid-or-content-id",
  "center": {
    "kind": "blank_identity_nucleus",
    "fleet_id": "fleet-uuid-or-deterministic-id",
    "namespace_commitment": "sha256(fleet_id | wafer_id | created_at | policy_version)",
    "executable": false,
    "stores_secret": false
  },
  "formation": "star | pair_lattice | ring | containment_hull | scatter | tetrahedral",
  "mode": "ionian | dorian | phrygian | lydian | mixolydian | aeolian | locrian",
  "phase": "birth | discover | plan | build | review | integrate | resolve | quarantine | rollback",
  "cells": [],
  "edges": [],
  "receipts": []
}
```

## Center invariants

The blank center has strict invariants:

1. It cannot execute an action.
2. It cannot hold credentials, API tokens, payload secrets, or generated code.
3. It binds only identity, namespace, provenance, and policy version.
4. Every wafer-local cache key must derive from its namespace commitment.
5. Cross-fleet access requires an explicit bridge edge and receipt.
6. A missing or mismatched center commitment fails closed before formation work starts.

## Cell model

A wafer cell is a typed unit of fleet work. It may represent an agent role, a code fragment, a task fragment, a receipt, or a quarantined object.

Suggested fields:

```json
{
  "cell_id": "cell-id",
  "wafer_id": "parent-wafer-id",
  "fleet_id": "parent-fleet-id",
  "tongue_role": "KO | AV | RU | CA | UM | DR",
  "agent_id": "optional-agent-id",
  "task_id": "optional-task-id",
  "fragment_id": "optional-code-fragment-id",
  "state": "empty | assigned | running | waiting | verified | promoted | quarantined | rolled_back",
  "capabilities": [],
  "trust_vector": {},
  "cache_key": "derived-from-center-namespace",
  "receipts": []
}
```

Tongue-role mapping for coding fleets:

| Full tongue role | Fleet responsibility |
| --- | --- |
| KO identity/base syntax | Mission root, task identity, local syntax anchor |
| AV observable properties | Context, telemetry, repository observations, transport facts |
| RU operation/imperative | Route selection, command shape, binder handoff |
| CA conservation/valence | Interface contracts, tests, safety constraints, bond legality |
| UM uncertainty/loss | Risk, ambiguity, disagreement, quarantine triggers |
| DR resolved output | Final artifact, export, release memory, receipt closure |

## Edge model

Edges are proposed bonds between cells. They should be explicit because fleet failures usually happen at integration boundaries, not inside isolated fragments.

Allowed edge kinds:

| Edge kind | Meaning |
| --- | --- |
| `semantic_bond` | Two cells preserve the same intent or concept. |
| `interface_bond` | A function, class, schema, endpoint, or artifact boundary matches. |
| `test_bond` | One cell's tests validate another cell's artifact. |
| `receipt_bond` | A receipt proves a cell transition or decision. |
| `handoff_bond` | Work passes from one role/agent to another. |
| `quarantine_edge` | A cell is isolated from promotion. |
| `bridge_edge` | A controlled, receipted link to another fleet wafer. |

Bond scoring should stay simple and deterministic:

```text
bond_score =
    interface_match
  + semantic_fit
  + test_alignment
  + governance_alignment
  - risk_penalty
  - naming_conflict_penalty
  - cross_fleet_penalty
```

A cell cannot be promoted through a bond unless the bond score clears threshold and the fleet governance gate returns `ALLOW`.

## Cat's-cradle projection rule

The wafer admits an operation only when the operation can be coerced into a cat's-cradle array:

```text
operation
  -> local cell movement
  -> edge tension change
  -> bounded lattice response
  -> projected 3D state
  -> receipt-backed stable or quarantined result
```

This makes the wafer a reconfigurable software mechanism instead of a flat list of agent actions. The two-dimensional wafer is the compact plan. The projected three-dimensional lattice is the execution geometry used to test whether the operation preserves boundaries while moving through the fleet.

Required operation fields:

```json
{
  "operation_id": "operation-id",
  "source_cell": "cell-id",
  "target_cells": [],
  "coercion": "local_move | twist | lift | fold | bridge | seal",
  "preserved_boundaries": ["center", "namespace", "receipts"],
  "projection_state": "disk | cylinder | hyperboloid | sphere",
  "degree_of_freedom": 1,
  "expected_neighbor_response": "local | ring | panel | full_lattice",
  "failure_policy": "quarantine | rollback | replan"
}
```

Admission rule:

```text
admit(operation) =
  center_valid
  and operation_has_receipt_target
  and operation_can_project_to_lattice
  and preserved_boundaries_are_declared
  and degree_of_freedom <= allowed_phase_dof
  and governance_gate(operation) != DENY
```

If the operation cannot be projected into the lattice, it does not run through the fleet wafer. It must either be decomposed into smaller lattice-compatible operations or rejected.

## Projection states

The pop-up wire-basket analogy maps cleanly to software fleet states:

| Projection state | Geometry role | Software role |
| --- | --- | --- |
| `disk` | Flat compressed lattice | Planning, cache indexing, route table, no global execution. |
| `cylinder` | Open zero-curvature tube | Ordered transport, context streaming, receipt movement. |
| `hyperboloid` | Negative-curvature waist under opposing twist | Conflict routing, cross-panel negotiation, mismatch localization. |
| `sphere` | Positive-curvature enclosed volume | Integrated stable compound, promoted shared artifact. |

The center remains blank in every projection. It is the identity axis, not a moving payload.

## Kinematic constraints

The fleet wafer should prefer one effective degree of freedom per phase. Internally many agents/cells may move, but the orchestrator exposes one dominant control variable for the phase:

| Phase | Control variable | Expected lattice response |
| --- | --- | --- |
| `discover` | scan radius | Local cells populate observations without modifying state. |
| `plan` | decomposition angle | Task cells fan out from the center namespace. |
| `build` | local twist | Coder/validator pairs move without global reshaping. |
| `review` | ring phase | KO -> AV -> RU -> CA -> UM -> DR review advances in order. |
| `integrate` | lift depth | Stable cells rise into the shared compound. |
| `resolve` | seal threshold | Final output locks and exports. |
| `quarantine` | tension break | Failed cells are isolated from the promoted lattice. |
| `rollback` | inverse phase | Last stable projection is restored. |

This is the software equivalent of the basket having many wires but one effective motion. The fleet may have many agents, but the wafer phase must make the next valid movement deterministic.

## Bistable checkpoints

Stable checkpoints are the software version of the basket snapping into a self-holding shape.

A checkpoint is stable when:

- the center namespace is unchanged;
- all promoted cells have receipts;
- no promoted edge crosses fleets without a bridge receipt;
- intent, structure, and execution axes pass;
- unresolved tension is below threshold.

Crossing a threshold produces one of two stable outcomes:

- promotion into the next phase;
- quarantine/rollback into a safe prior phase.

No unstable midpoint is allowed to become fleet state.

## State machine

The wafer advances by phase. Formation changes only happen at phase boundaries.

| Phase | Default formation | Default mode | Purpose |
| --- | --- | --- | --- |
| `birth` | center only | ionian | Create blank identity nucleus and namespace commitment. |
| `discover` | scatter | mixolydian | Observe files, APIs, tests, docs, constraints. No modification. |
| `plan` | star | lydian | Decompose mission into bounded cells and assign roles. |
| `build` | pair_lattice | ionian | Generate or modify fragments inside local sandboxes. |
| `review` | ring | aeolian | Ordered KO -> AV -> RU -> CA -> UM -> DR review pass. |
| `integrate` | containment_hull | phrygian for high risk, ionian otherwise | Promote stable fragments into shared state. |
| `resolve` | containment_hull | ionian | Export final artifact and close receipts. |
| `quarantine` | tetrahedral or pair_lattice | locrian | Isolate unsafe, incoherent, or unverified cells. |
| `rollback` | star | aeolian | Restore last stable wafer state and preserve failure receipts. |

## Transitions

| From | To | Trigger | Required gate |
| --- | --- | --- | --- |
| `birth` | `discover` | Center commitment is valid. | `ALLOW` for observe/measure only. |
| `discover` | `plan` | Inventory and constraints are recorded. | Receipts exist for opened resources. |
| `plan` | `build` | Task cells have owners, roles, and bounded workspaces. | No unowned high-risk cells. |
| `build` | `review` | Local sandbox checks pass or fail with receipts. | No silent failures. |
| `review` | `integrate` | Intent, structure, and execution axes agree. | Quorum and governance `ALLOW`. |
| `integrate` | `resolve` | Integration tests and policy checks pass. | Release/export gate `ALLOW`. |
| any | `quarantine` | Secret hit, missing receipt, invalid bridge, low trust, failed invariant, or non-bijective required transform. | Fail closed. |
| `quarantine` | `rollback` | Unsafe state cannot be repaired locally. | Preserve evidence before rollback. |
| `quarantine` | `plan` | The failure changes task decomposition. | New plan required. |
| `quarantine` | `build` | The failure is local and repairable. | Repair cell only. |

## Triangulation gate

A cell or bond is promotable only when three axes agree:

1. Intent axis: the artifact still serves the mission root.
2. Structure axis: interfaces, schemas, names, and imports are coherent.
3. Execution axis: tests, type checks, runtime checks, or policy checks pass.

Promotion rule:

```text
promote(cell) =
  center_valid
  and namespace_matches
  and intent_axis_pass
  and structure_axis_pass
  and execution_axis_pass
  and bond_score >= threshold
  and fleet_governance_decision == ALLOW
```

Quarantine rule:

```text
quarantine(cell) =
  secret_or_credential_hit
  or center_mismatch
  or missing_receipt
  or cross_fleet_edge_without_bridge_receipt
  or hard_governance_deny
  or trust_below_floor
  or required_bijection_failed
  or execution_axis_failed_hard
```

## Cache and context namespacing

All cache and context keys must include the center namespace commitment.

Suggested key shape:

```text
scbe:fleet_wafer:v1:
  <namespace_commitment>:
  <phase>:
  <formation>:
  <mode>:
  <cell_id>:
  <route_id>:
  <artifact_hash>
```

Rules:

- Local agents may read wafer-local cache keys in the same namespace.
- A fleet may not read another fleet's cache directly.
- Cross-fleet cache reads require a `bridge_edge`, a receipt, and an explicit governance decision.
- Cache hits are advisory. Promotion still requires triangulation.

## Workspace binding

The wafer should bind to the agent-bus workspace layout:

```text
.aethermoor-bus/workspaces/<workspace-id>/
  00_inbox/
  10_work/
  20_receipts/
  30_exports/
  40_refs/
  90_tmp/
```

Mapping:

| Workspace folder | Wafer role |
| --- | --- |
| `00_inbox` | Mission packet and incoming bridge receipts. |
| `10_work` | Cell-local sandboxes and draft fragments. |
| `20_receipts` | Gate decisions, tests, proofs, handoff records. |
| `30_exports` | Resolved DR artifacts only. |
| `40_refs` | Read-only references used by AV/KO cells. |
| `90_tmp` | Disposable local scratch that cannot be promoted directly. |

## Determinism policy

The fleet may use stochastic model generation inside a bounded cell, but orchestration must be deterministic.

Freeze these values per wafer run:

- `fleet_id`
- `wafer_id`
- center namespace commitment
- formation schedule
- mode schedule
- role assignment
- tie-break order
- gate thresholds
- cache namespace
- promotion/quarantine rules

If any of those change, create a new wafer or a new wafer revision. Do not silently mutate the center.

## Implementation hook

The first code integration should not add a new executor.

Use the existing order:

```text
agent move packet
  -> fleet wafer namespace check
  -> local cell/bond update
  -> SCBE fleet governance gate
  -> receipt
  -> promotion, quarantine, or rollback
```

Initial implementation can ride existing flexible fields:

- `FleetAgent.metadata.wafer_id`
- `FleetAgent.metadata.cell_id`
- `FleetTask.input.wafer`
- `FleetTask.input.phase`
- `FleetTask.input.formation`
- `FleetTask.input.mode`
- `FleetTask.output.receipts`
- `FleetTask.output.bond_score`

Promote to explicit TypeScript interfaces only after the first working harness proves the state machine catches real integration drift.

## Non-goals

- No raw `/execute` endpoint.
- No unrestricted cross-fleet cache.
- No all-to-all agent chatter per token.
- No center-cell secrets.
- No physical drone-control instructions.
- No military/autonomous weapon workflow.

## Test plan

Minimum harness:

1. Create a wafer with a valid blank center.
2. Assign three cells: planner, coder, validator.
3. Generate one code fragment in a local sandbox.
4. Propose an `interface_bond` and `test_bond`.
5. Run intent, structure, and execution checks.
6. Verify `ALLOW` promotes the fragment.
7. Verify a missing receipt sends the cell to quarantine.
8. Verify a cross-fleet cache read without `bridge_edge` fails closed.
9. Verify the center never stores generated code or secrets.

Success means the fleet can assemble code fragments through deterministic bonds while preventing namespace leaks and unstable promotion.
