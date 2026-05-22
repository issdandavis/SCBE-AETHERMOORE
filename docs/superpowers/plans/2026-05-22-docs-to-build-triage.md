# Docs-To-Build Triage Plan

Status: active triage plan  
Date: 2026-05-22  
Purpose: Convert the user's large SCBE/Notion/Obsidian doc library into buildable implementation queues.

## 1. Problem

The project has more design pages than available agents. That is not a failure; it is an indexing problem.

The wrong move is to ask every agent to reread every page and synthesize from scratch. The right move is to compile each page into a small, typed build card:

```text
source doc -> claims -> repo anchors -> risk class -> next executable slice
```

Once a page has a build card, agents can act on it without carrying the full original context.

## 2. Build Card Schema

Every imported design page should reduce to this shape:

```json
{
  "schema_version": "scbe-doc-build-card-v1",
  "title": "AetherAuth",
  "source_path": "notion-export-or-repo-path",
  "status": "design | partial | implemented | deprecated | research-only",
  "core_claim": "one sentence",
  "repo_anchors": [],
  "missing_artifacts": [],
  "risk_class": "low | medium | high | cryptographic | external-action",
  "first_slice": {
    "goal": "small executable target",
    "files": [],
    "tests": [],
    "acceptance": []
  },
  "do_not_build_yet": [],
  "notes": []
}
```

## 3. Triage Classes

| Class | Meaning | Action |
|---|---|---|
| `implemented` | Code/tests already exist | Link it, add tests only if behavior is unclear |
| `partial` | Some repo anchors exist, glue missing | Build smallest integration slice |
| `design` | Good idea, no code surface | Write spec before implementation |
| `research-only` | Concept depends on unproven math/security claims | Preserve; do not expose as production feature |
| `deprecated` | Superseded or contradicted by current repo truth | Archive/redirect |

## 4. Priority Rules

Build order should be mechanical:

1. Revenue or proposal support first.
2. Existing CLI/API surfaces before new subsystems.
3. Security gates before external actions.
4. Dry-run/probe before mutation.
5. Tests before marketing claims.
6. Research claims stay out of production until reduced to tested mechanisms.

## 4.1 Notion Export Intake Protocol

Use this before assigning any agent to a pasted Notion/Obsidian page.

```text
1. Preserve the page title and source path.
2. Extract exactly one core claim.
3. Separate claims into: implemented, buildable, research-only, cut/fenced.
4. Map every buildable claim to repo anchors.
5. Convert vivid language into operational fields.
6. Carry the fences beside the kept claim.
7. Pick the smallest dry-run or read-only first slice.
```

Do not merge imported pages into canonical SCBE architecture on first pass. Imported pages start as build cards, salvage notes, or R&D notes.

## 4.2 Shape Translation Rule

PHDM and shape language should help agents preserve structure, not inflate claims.

```text
shape phrase -> operational role -> validator -> receipt
```

Allowed roles:

- route work by domain
- choose traversal order
- cap recursion or fan-out
- visualize/debug a task state
- preserve audit path integrity

Disallowed roles:

- prove physics
- prove cryptographic strength
- bypass tests
- imply infinite capability
- imply unbounded autonomy

## 4.3 Research Fence Template

When a page has useful intuition plus unsafe claims, attach this block:

```text
Kept:
- concrete metric/mechanism

Fenced:
- unsupported physics/security/autonomy claim

Promotion condition:
- test, benchmark, proof, or threat model required before production use
```

No agent should receive a research-only page without this block.

## 4.4 Agent Assignment Template

Agents get narrow ownership.

```text
Task:
  Build <first_slice.goal>.

Own:
  - <file/path/one>
  - <file/path/two>

Do not touch:
  - unrelated canonical architecture
  - live credentials or external APIs
  - generated artifacts unless explicitly required

Acceptance:
  - <deterministic check>
  - <negative test>
  - <receipt/log/schema output>
```

## 4.5 Audience Split

The same source page can produce different artifacts. Do not collapse them.

| Audience | Artifact | Tone |
|---|---|---|
| internal R&D | salvage note / research note | keeps fences and dead ends |
| implementation agent | build card | files, tests, acceptance |
| proposal/SBIR | capability statement slice | verified claims only |
| patent counsel | invention disclosure draft | mechanism and boundaries |
| public site | demo/page | conservative proof and CTA |

## 5. Current Top Build Queue

### 5.1 GeoSeed Infinity Box Runtime

```json
{
  "title": "GeoSeed Infinity Box Runtime",
  "status": "design",
  "core_claim": "Bounded recursive execution containers route work through sphere-grid shapes, PHDM path integrity, GeoSeal receipts, and STISA cross-language action classes.",
  "repo_anchors": [
    "docs/superpowers/specs/2026-05-22-geoseed-infinity-box-runtime.md",
    "docs/M6_SEED_MULTI_NODAL_NETWORK_SPEC.md",
    "src/kernel/agentic_sphere_grid.py",
    "src/harmonic/phdm.ts",
    "tests/coding_board/test_coding_board.py"
  ],
  "risk_class": "medium",
  "first_slice": {
    "goal": "box-trial CLI wraps legitimacy-trial plus coding-trial and emits deterministic node receipts",
    "files": [
      "src/geoseal_cli.py",
      "src/coding_board/",
      "tests/coding_board/"
    ],
    "tests": [
      "safe command returns PROBE or ALLOW receipt",
      "unsafe command returns DENY before probe",
      "receipt includes node_id, tongue, shape, tier, state_hash"
    ],
    "acceptance": [
      "no side effect before legitimacy/probe",
      "JSON output is deterministic",
      "existing coding-trial behavior does not regress"
    ]
  }
}
```

### 5.2 AetherAuth / Context-Bound Vault

```json
{
  "title": "AetherAuth Context-Bound Vault",
  "status": "partial",
  "core_claim": "Secrets are only released after a request passes a context/intent legitimacy trial and receives a GeoSeal-style receipt.",
  "repo_anchors": [
    "src/crypto/geoseal_legitimacy.py",
    "src/crypto/geoseal_execution_gate.py",
    "src/geoseal_cli.py",
    "src/api/geoseal_service.py",
    "config/connector_oauth/.env.connector.oauth"
  ],
  "risk_class": "cryptographic",
  "first_slice": {
    "goal": "aether-auth dry-run command evaluates a request context and returns ALLOW/DENY without decrypting or printing secrets",
    "files": [
      "src/crypto/aether_auth.py",
      "src/geoseal_cli.py",
      "tests/crypto/test_aether_auth.py"
    ],
    "tests": [
      "normal workspace context maps to CORE/ALLOW",
      "path/intent mismatch maps to DENY",
      "dry-run never reads or prints secret values"
    ],
    "acceptance": [
      "no live Notion/Perplexity call in first slice",
      "no custom crypto beyond standard library/approved primitives",
      "audit output redacts secret-bearing fields"
    ]
  },
  "do_not_build_yet": [
    "Calabi-Yau mirror duality key swapping as production cryptography",
    "context-vector-derived encryption keys for real secrets without security review",
    "Fail-to-Noise claims that are not backed by tests"
  ],
  "notes": [
    "The useful core is not OAuth replacement marketing; it is a local secret-release gate over GeoSeal legitimacy.",
    "Build dry-run and audit first, then integrate a real vault only after tests prove no leakage."
  ]
}
```

### 5.3 Runtime Assurance Harness

```json
{
  "title": "SCBE Runtime Assurance Harness",
  "status": "partial",
  "core_claim": "AI-generated actions are proposed state transitions, not truth; the harness validates, probes, gates, and audits before side effects.",
  "repo_anchors": [
    "docs/business/SCBE_RUNTIME_ASSURANCE_HARNESS_ONE_PAGER_2026-05-22.md",
    "docs/runtime-assurance-harness.html",
    "tests/coding_board/test_coding_board.py",
    "tests/crypto/test_geoseal_legitimacy.py"
  ],
  "risk_class": "medium",
  "first_slice": {
    "goal": "one public demo packet showing request -> probe -> gate -> receipt",
    "files": [
      "scripts/system/",
      "docs/runtime-assurance-harness.html",
      "artifacts/"
    ],
    "tests": [
      "demo packet schema validates",
      "unsafe sample is denied",
      "safe compile sample produces receipt"
    ],
    "acceptance": [
      "usable in AFWERX/DARPA capability statement",
      "does not require paid API calls",
      "runs locally"
    ]
  }
}
```

### 5.4 Governed Desktop / Kimi Shell Integration

```json
{
  "title": "Aether Desktop Governed OS",
  "status": "design",
  "core_claim": "A clean desktop shell routes every real backend action through /v1/op, governance, and before/after audit.",
  "repo_anchors": [
    "docs/superpowers/specs/2026-05-21-aether-desktop-governed-os-design.md",
    "docs/superpowers/specs/2026-05-21-agentic-control-desktop-integration.md"
  ],
  "risk_class": "external-action",
  "first_slice": {
    "goal": "llm.chat vertical slice through gate and audit, no raw shell",
    "files": [
      "desktop repo",
      "packages/workflow-engine",
      "src/api/geoseal_service.py"
    ],
    "tests": [
      "request writes before audit",
      "handler result completes after audit",
      "denied op does not call handler"
    ],
    "acceptance": [
      "one real app does one real thing through the gate",
      "Phase 2 workflow builder remains deferred"
    ]
  }
}
```

### 5.5 Narrative Combat / Board Kernel Coding Adapter

```json
{
  "title": "Board Kernel Coding Adapter",
  "status": "partial",
  "core_claim": "The go-board kernel can map coding to legal state moves: files/tests/contracts become board state; probes and captures become compiler/test outcomes.",
  "repo_anchors": [
    "src/narrative_combat/go_board/",
    "docs/superpowers/specs/2026-05-21-go-board-narrative-engine-design.md",
    "tests/narrative_combat/go_board/"
  ],
  "risk_class": "medium",
  "first_slice": {
    "goal": "read-only coding adapter converts a pytest/compile result into board events",
    "files": [
      "src/coding_board/",
      "tests/coding_board/"
    ],
    "tests": [
      "failing test maps to atari/capture pressure",
      "passing test maps to territory stabilization",
      "no file mutation in adapter first slice"
    ],
    "acceptance": [
      "adapter is additive; go-board kernel remains generic",
      "coding-trial remains the mechanical truth source"
    ]
  }
}
```

### 5.6 HYDRA Multi-Agent Coordination

```json
{
  "title": "HYDRA Multi-Agent Coordination",
  "status": "partial",
  "core_claim": "HYDRA is the terminal-native multi-agent coordination armor: model heads propose work, browser/tool limbs execute through governed backends, consensus/spectral checks detect drift, and ledgers preserve state.",
  "repo_anchors": [
    "hydra/README.md",
    "hydra/__init__.py",
    "hydra/ledger.py",
    "hydra/octree_sphere_grid.py",
    "hydra/voxel_storage.py",
    "hydra/color_dimension.py",
    "hydra/cli_swarm.py",
    "agents/README.md",
    "agents/swarm_browser.py",
    "src/api/hydra_routes.py",
    "src/browser/hydra_hand.py",
    "src/agent/swarm.ts",
    "src/ai_brain/bft-consensus.ts",
    "src/fleet/governance.ts"
  ],
  "risk_class": "external-action",
  "first_slice": {
    "goal": "HYDRA local capability registry reports which runtime pieces are local, moved to scbe-agents, or compatibility-only",
    "files": [
      "scripts/system/build_hydra_capability_registry.py",
      "artifacts/hydra/hydra_capability_registry.json",
      "tests/system/test_build_hydra_capability_registry.py"
    ],
    "tests": [
      "registry marks hydra/ as mainrepo-compat",
      "registry marks scbe-agents runtime as external/moved",
      "registry detects local spatial modules: octree, voxel, color dimension, ledger",
      "registry does not claim production-ready full spine/head/librarian files in this repo if absent"
    ],
    "acceptance": [
      "agents can route to the correct repo/surface before building",
      "no browser or shell side effects",
      "output is deterministic JSON"
    ]
  },
  "do_not_build_yet": [
    "Full HydraSpine/Head/Librarian recreation in this repo if scbe-agents is the current home",
    "Live browser swarm execution before operation-gate integration",
    "Claims like 226/226 passing or commit fd49eeb unless verified against the relevant repo"
  ],
  "notes": [
    "In this checkout, hydra/ exists as a compatibility/storage-geometry subset; hydra/README.md says the full runtime moved to https://github.com/issdandavis/scbe-agents.",
    "The pasted architecture is useful as canon, but the build target here should first be a registry/adapter layer so agents do not duplicate the moved runtime."
  ]
}
```

### 5.7 Quasi Vector Field Coherence

```json
{
  "title": "Quasi Vector Field Coherence",
  "status": "partial",
  "core_claim": "The keepable part of the old spin-voxel notes is vector-field coherence and angular disorder as read-side routing/drift signals, plus multi-clock T-phase as scheduled context rotation.",
  "repo_anchors": [
    "docs/research/QUASI_VECTOR_FIELD_COHERENCE_SALVAGE_2026-05-22.md",
    "docs/specs/QUASI_VECTOR_SPIN_VOXELS_MAZE_RND.md",
    "src/storage/spin_voxel.py",
    "tests/test_spin_voxel.py",
    "src/harmonic/temporalPhase.ts",
    "tests/L2-unit/temporalPhase.unit.test.ts"
  ],
  "risk_class": "research-only",
  "first_slice": {
    "goal": "Preserve tested coherence/disorder/T-phase metrics while removing production-facing magnetics and Grover overclaims",
    "files": [
      "docs/specs/QUASI_VECTOR_SPIN_VOXELS_MAZE_RND.md",
      "docs/research/QUASI_VECTOR_FIELD_COHERENCE_SALVAGE_2026-05-22.md"
    ],
    "tests": [
      "python -m pytest tests/test_spin_voxel.py -q",
      "targeted temporalPhase Vitest if the TS labels change"
    ],
    "acceptance": [
      "no canonical architecture claim depends on spintronics",
      "Grover discussion stays limited to key-size/PQC reality",
      "field coherence remains read-side only unless promoted by benchmark"
    ]
  },
  "do_not_build_yet": [
    "topological protection claims",
    "magnonic computing claims",
    "Grover-defeat claims",
    "write-path harmonic-wall multiplication by unvalidated field score"
  ]
}
```

### 5.8 Task-Autonomous Fabrication Cell

```json
{
  "title": "Task-Autonomous Fabrication Cell",
  "status": "research-only/design",
  "source_path": "docs/research/TASK_AUTONOMOUS_FABRICATION_CELL_TECH_TREE_2026-05-22.md",
  "not_canonical_scbe": true,
  "core_claim": "A bounded agentic system can dispatch physical fabrication tools as governed operations, close the build-sense-correct loop, and emit auditable receipts while remaining under a human-specified goal-and-constraint envelope.",
  "repo_anchors": [
    "docs/research/TASK_AUTONOMOUS_FABRICATION_CELL_TECH_TREE_2026-05-22.md",
    "docs/specs/AETHERFAB_PUF_NEGATIVE_RESULT.md",
    "docs/research/drone_autonomy_training_patterns_2026-05-02.md",
    "docs/ops/REGENERATIVE_AI_MOBILITY_OPEN_SOURCE_STACK_2026-05-21.md"
  ],
  "risk_class": "physical-action / R&D-adjacent",
  "provenance_rule": "Keep the correction ledger with the claim: vivid idea -> stress test -> fenced overreach -> kept core.",
  "first_slice": {
    "goal": "Simulate a governed build-sense-correct loop for a calibration bracket with no real hardware actuation",
    "files": [
      "scripts/system/fab_cell_sim.py",
      "tests/system/test_fab_cell_sim.py",
      "artifacts/fab_cell/"
    ],
    "tests": [
      "safe print plan emits ALLOW receipt",
      "out-of-bounds tool path emits DENY receipt",
      "measured error triggers adjust/retry decision",
      "no hardware command is emitted in simulation mode"
    ],
    "acceptance": [
      "human target remains root of task tree",
      "task autonomy is pinned as bounded and envelope-governed",
      "self-modeling loop is demonstrated before kiln/foundry claims",
      "all physical action stays simulated"
    ]
  },
  "do_not_build_yet": [
    "live hardware actuation",
    "autonomous goal origination",
    "self-replication claims",
    "kiln/foundry endpoint",
    "canonical SCBE architecture merge"
  ],
  "fences": [
    "not self-fabrication: semiconductor/controller floor remains sourced unless a real process exists",
    "not full autonomy: stacked subtasks do not remove the human-specified root goal",
    "not concealment: dangerous failure modes belong in simulation/closed environments with audit receipts"
  ]
}
```

## 6. AetherAuth Security Correction

The AetherAuth page has one very strong buildable idea and several risky claims.

Buildable:

- context/state capture
- trust ring decision
- secret-release dry-run
- GeoSeal audit receipt
- denial before any external API call

Needs correction before implementation:

- Do not derive real encryption keys directly from unstable context vectors.
- Do not claim OAuth replacement until the system has threat-model tests.
- Do not print, log, or return plaintext API keys in any test path.
- Do not ship Calabi-Yau/mirror-duality as cryptography until reduced to a standard primitive or kept as a research simulation.

The first safe implementation is not "Notion to Perplexity bridge." It is:

```text
given: requested provider + declared intent + workspace + context snapshot
return: ALLOW/DENY + trust ring + redacted audit receipt
```

Only after that should a vault adapter be connected.

## 7. Agent Allocation Rule

Each agent gets one build card, not a whole theory bundle.

Good delegation:

```text
Build AetherAuth dry-run gate. Own only:
- src/crypto/aether_auth.py
- tests/crypto/test_aether_auth.py
- CLI hook in src/geoseal_cli.py
Do not implement live Notion/Perplexity calls.
Do not touch unrelated GeoSeal behavior.
```

Bad delegation:

```text
Read all Notion docs and build the auth system.
```

## 8. Next Compiler Step

Create a script later:

```text
scripts/system/build_doc_build_cards.py
```

Inputs:

- `docs/superpowers/specs/`
- `docs/specs/`
- selected `notes/sphere-grid/`
- selected Notion exports under `notes/System Library/`

Outputs:

- `artifacts/doc_build_cards/doc_build_cards.jsonl`
- `docs/superpowers/plans/DOC_BUILD_QUEUE.md`

For now, this hand-written plan is enough to keep the next agents focused.
