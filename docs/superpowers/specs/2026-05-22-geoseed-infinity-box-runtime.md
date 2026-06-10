# GeoSeed Infinity Box Runtime

Status: draft integration spec  
Date: 2026-05-22  
Owner: Issac Davis  
Scope: SCBE sphere-grid nodes, PHDM shapes, STISA token chemistry, GeoSeal receipts, and governed tool calls

## 1. Purpose

This spec names the runtime shape behind the user's "infinity box" concept.

It is not true mathematical infinity. It is bounded practical recursion: a finite seed can keep expanding into child nodes while budget, depth, policy, usefulness, and receipt trace remain valid.

The box is therefore a recursive execution container:

```text
finite seed
  -> shape assignment
  -> bins
  -> governed tool calls
  -> receipts
  -> optional child boxes
```

The value is that every child container inherits geometry, policy, and provenance instead of becoming an unbounded agent loop.

## 2. Current Repo Anchors

The design composes existing surfaces rather than inventing a parallel subsystem.

| Layer | Current anchor | Role |
|---|---|---|
| M6 / GeoSeed direction | `docs/M6_SEED_MULTI_NODAL_NETWORK_SPEC.md` | Six-seed topology plus the current `src/geoseed/` orbital / prime-abacus implementation subset |
| Sphere-grid behavior | `notes/sphere-grid/Agentic Sphere Grid.md` | Tongue domains, tiers, learning through need pressure |
| Sacred flow geometry | `notes/sphere-grid/geometry/sacred-flows.md` | Tongue-to-shape mapping and vertical/horizontal/diagonal flow |
| Phi spacing | `notes/sphere-grid/geometry/phi-spiral.md` | Tongue weights and tier spacing |
| Runtime implementation substrate | `src/kernel/agentic_sphere_grid.py` | Skill nodes, activation tiers, need pressure, governance verdicts |
| Context substrate | `src/kernel/context_grid.py` | Documents projected into 6D/3D geometry and indexed with provenance |
| PHDM shape integrity | `src/harmonic/phdm.ts` | 16-polyhedra Hamiltonian path, topology checks, HMAC chain |
| STISA token chemistry | `notes/theory/atomic-tokenizer-chemistry-unified.md` and `tests/tokenizer/test_stisa_chemical_composition.py` | Token composition and cross-language action invariance |
| GeoSeal / legitimacy | GeoSeal CLI and legitimacy-trial surfaces | Time/location/system-state legitimacy receipts |
| Coding gate | `coding-trial` CLI path | Mechanical compiler/probe verdicts before mutation |

Note: the old Notion-exported GeoSeed note overstates implementation status. In this checkout, `src/geoseed/` does exist and contains a real subset: orbital model, shell duality / theory-fit work, bit dressing, semantic abacus, prime atlas, prime seed init, transfer recorder, and visualization surfaces. What does **not** exist here is the full Notion-claimed 14-layer network stack (`sphere_grid.py`, `dressing_geometric.py`, `composition_geometric.py`, `model.py`). Treat the Notion note as design/canon input and this spec as the current repo-truth: GeoSeed is partially implemented, with orbital / prime-abacus code live and the larger network architecture still future work.

## 3. Core Invariant

The box may recurse only while all five limits hold:

1. `budget_remaining > 0`
2. `depth <= max_depth`
3. `policy_verdict in {ALLOW, PROBE}`
4. `usefulness_score >= threshold`
5. `receipt_chain verifies`

If any condition fails, the node must stop expanding and return a receipt-backed terminal state.

This is the practical-infinity invariant:

```text
recursion is permitted, infinity is not claimed
```

## 4. Shape Palette

The sphere-grid gives the operational shape for each tongue. PHDM gives the higher-order containment and path-integrity shapes.

Shape use is operational, not mystical. A shape is allowed to mean:

- routing domain
- capacity limit
- traversal order
- audit path
- visual/debug affordance

A shape is not allowed to prove security, physics, or correctness by itself. Every shape claim must reduce to a typed field, validator, traversal rule, or receipt hash.

### 4.1 Tongue Runtime Shapes

| Tongue | Domain | Runtime shape | Use |
|---|---|---|---|
| KO | Command | Hexagonal | Dispatch, task decomposition, routing command |
| AV | Transport | Spiral | Research navigation, web/video traversal, widening search |
| RU | Entropy | Fractal | Adversarial branching, anomaly exploration, ambiguity pressure |
| CA | Compute | Cubic | Compile checks, tests, transforms, structured tool execution |
| UM | Redaction/Privacy | Icosahedral | Policy gates, threat faces, denial surfaces |
| DR | Authentication/Integrity | Dodecahedral | Auth tags, documentation, contracts, stable interfaces |

### 4.2 PHDM Containment Shapes

PHDM supplies a canonical polyhedral path for integrity and flux posture.

| Flux state | Shape family | Runtime meaning |
|---|---|---|
| DEMI | Platonic only | Minimal stable check; early prototype or low-risk lane |
| QUASI | Platonic + Archimedean | Normal governed workflow; enough shape variety for routing |
| POLLY | All 16 PHDM shapes | Full audit/high-risk lane with maximal path diversity |

Every high-risk Infinity Box should carry a PHDM path hash:

```text
K_{i+1} = HMAC-SHA256(K_i, Serialize(P_i))
```

That makes the shape traversal tamper-evident without claiming the shape itself is magic.

### 4.3 Notion Export Shape Intake

Old Notion pages can mention shapes before they identify a build surface. Import them through this rule:

```text
shape phrase -> operational role -> repo anchor -> first executable slice
```

Examples:

| Notion phrase | Safe operational reading | Unsafe reading to fence |
|---|---|---|
| `PHDM 16-polyhedra paths` | ordered audit/traversal families with path hashes | polyhedra create security by themselves |
| `sphere grid` | bounded routing/embedding topology | infinite agent space |
| `tesseract` | 3D state plus build-time or phase axis | real fourth spatial dimension |
| `Rubik shifts` | surface permutation / task reordering while core state is locked | magic self-reconfiguration |
| `spin voxel` | vector-field coherence/disorder metric | physical magnetics or Grover resistance |

If the safe operational reading cannot be named, the page stays `research-only`.

## 5. GeoSeed Dressing

The Notion GeoSeed document defines Geometric Bit Dressing:

```text
raw bit/token/action
  -> 14-layer traversal
  -> tongue assignment
  -> manifold signature
  -> governance stamp
```

For the runtime, dressing applies at three levels:

| Tier | Name | Runtime target |
|---|---|---|
| F1 | Binary substrate | Raw bits, token rows, compiler atoms |
| F2 | Public interface | SS1 bytes, BPE/WordPiece tokens, API packets |
| F3 | Identity genesis | Sacred Eggs, GeoSeal identity, agent/tool birth certificates |

The Infinity Box does not need full bit-level dressing before it is useful. The first build can dress operation packets and code-trial records, then later push downward toward bit-level dressing.

## 6. Node Schema

```json
{
  "schema_version": "scbe-geoseed-box-v0.1",
  "node_id": "box:root:ca-compile-001",
  "parent_id": null,
  "tongue": "CA",
  "shape": "cubic",
  "phdm_flux": "QUASI",
  "tier": 2,
  "activation": "PARTIAL",
  "depth": 0,
  "budget": {
    "max_steps": 12,
    "max_child_nodes": 4,
    "max_seconds": 120,
    "max_cost_cents": 0
  },
  "allowed_ops": [
    "coding-trial",
    "legitimacy-trial",
    "research-nav",
    "fs.read"
  ],
  "forbidden_ops": [
    "terminal.shell.raw",
    "fs.delete.unscoped",
    "network.post.unreviewed"
  ],
  "bins": [],
  "state_hash": "sha256:...",
  "phdm_path_hash": "hmac-sha256:...",
  "receipt_refs": [],
  "exit_condition": "budget_or_policy_or_success"
}
```

## 7. Bin Schema

Bins are bounded sub-containers inside a node. They are how the box avoids becoming a pile of untyped context.

```json
{
  "bin_id": "bin:compile-probes",
  "kind": "probe_results",
  "capacity": {
    "max_items": 16,
    "max_bytes": 65536
  },
  "spawn_rule": "spawn_child_on_repeated_failure",
  "contents": [],
  "provenance": [
    "coding-trial:2026-05-22T..."
  ],
  "validator": "compile_result_schema_v1"
}
```

Recommended first bin kinds:

| Bin kind | Contents | Validator |
|---|---|---|
| `intent_packet` | User/request goal and constraints | request schema |
| `evidence` | Search/video/source snippets and citations | source schema |
| `probe_results` | dry-run/test/compile output | probe schema |
| `patch_candidates` | proposed diffs or command plans | diff schema |
| `receipts` | GeoSeal/audit/state hashes | receipt schema |
| `memory_context` | selected prior notes/context bins | context schema |

## 8. Tool Tiering

The runtime should treat tool calls as tiered actions.

| Tier | Tool/action class | Default decision |
|---|---|---|
| T0 | inert data read, local metadata | ALLOW |
| T1 | analysis, summarization, local search | ALLOW |
| T2 | probe/dry-run/test/compile without mutation | PROBE |
| T3 | local file mutation inside workspace | ALLOW after probe |
| T4 | external action: post, email, deploy, upload | ESCALATE unless policy pre-authorizes |
| T5 | destructive/high-risk action, secrets, money, live actuators | DENY or explicit human approval |

Mapping current tools:

| Tool surface | Tongue shape | Tier |
|---|---|---|
| `research-nav` / `youtube-nav` | AV spiral | T1-T2 |
| `coding-trial` | CA cubic + UM icosahedral | T2 |
| `legitimacy-trial` | UM icosahedral | T2-T3 gate |
| agent-bus dispatch | KO hexagonal | T1-T4 depending op |
| GeoSeal receipt | UM/DR icosahedral-dodecahedral | receipt layer |
| PHDM path hash | DR/PHDM | integrity layer |

## 9. State Transition Flow

```text
1. propose
   A user, agent, workflow, or CLI proposes an action.

2. classify
   The action is assigned tongue, shape, tier, and risk.

3. allocate
   The action enters a node and a typed bin.

4. legitimize
   GeoSeal/legitimacy-trial checks time, location, workspace, origin, command shape,
   and known system state.

5. probe
   coding-trial or another dry-run mechanism tests the action without mutation.

6. gate
   Governance emits ALLOW, PROBE, QUARANTINE, ESCALATE, or DENY.

7. execute or stop
   Only allowed actions execute. Denied actions become receipts, not side effects.

8. receipt
   The node appends state hash, PHDM path hash, tool output summary, and decision.

9. spawn
   If useful and bounded, child nodes are created for unresolved subgoals.
```

## 10. Coding Example

```text
User goal:
  "Make the coding harness prove a proposed patch is mechanically stable."

KO command node:
  decomposes into read -> probe -> patch -> test -> receipt.

CA compute node:
  runs coding-trial, py_compile, pytest collect, TypeScript strict, Rust compile,
  or other available compiler checks.

UM security bin:
  verifies workspace scope, forbidden command shape, secret paths, and destructive
  intent before any mutation.

DR structure node:
  writes or updates the schema/spec after tests prove the behavior.

Receipt:
  GeoSeal + PHDM path hash + coding-trial JSON + git diff hash.
```

This turns coding into a board/state problem: the model proposes moves, the runtime decides whether they are legal, and compilers provide mechanical evidence.

## 11. Research/Navigation Example

```text
User goal:
  "Find credible sources for runtime assured autonomy."

AV spiral node:
  starts broad, collects candidate source trails, and prevents source loops.

RU fractal bin:
  stores contradictory or adversarial findings.

UM security node:
  rejects low-trust or unsafe sources.

DR structure node:
  emits the final source packet with citations and provenance.
```

This is the same box, but its dominant shape is AV spiral instead of CA cubic.

## 12. Relationship To STISA

STISA/atomic-tokenizer work provides the compositional rule beneath the boxes:

```text
same action class, many surface languages
```

For example, `+`, `add`, and language-specific addition functions should resolve to one action class while retaining distinct lexical hashes. That matters because an Infinity Box should route by semantic operation and verify by concrete implementation.

Practical rule:

```text
transport hash != semantic action class
```

The box must store both:

- lexical/transport identity for exact reproducibility
- semantic/action identity for cross-language equivalence

## 13. What To Build First

Do not start with bit-level dressing. Start with the operation-packet runtime.

Minimum vertical slice:

1. Define the JSON schemas above under `docs/schemas/` or `src/.../schemas`.
2. Add a small `box-trial` CLI that accepts an operation packet.
3. Route one safe coding command through:
   `classify -> legitimacy-trial -> coding-trial -> receipt`.
4. Route one unsafe command and prove it stops before probe/execution.
5. Store one receipt with:
   node id, shape, tongue, tier, decision, state hash, and output summary.

Acceptance bar:

```text
safe compile/test probe produces an ALLOW/PROBE receipt
unsafe/destructive command produces a DENY receipt
no side effect occurs before legitimacy and probe gates
all receipts are deterministic JSON
```

## 14. Open Decisions

1. Whether `src/geoseed/` should be created now or reserved until the schemas settle.
2. Whether `box-trial` belongs under GeoSeal CLI, coding-board CLI, or a new runtime CLI.
3. Whether PHDM path hashing should be required for every node or only T3+ actions.
4. Whether bit-level dressing is implemented as a training pipeline first or a runtime verifier first.

## 15. Clean One-Line Framing

GeoSeed Infinity Box is a bounded recursive execution container: sphere-grid shapes route work, PHDM shapes seal the path, STISA maps equivalent operations across languages, and GeoSeal receipts prove every child box stayed inside policy.
