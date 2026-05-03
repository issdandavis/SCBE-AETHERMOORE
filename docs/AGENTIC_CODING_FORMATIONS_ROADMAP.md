# Agentic Coding Formations Roadmap

Generated: 2026-05-02

Purpose: define the coding side of the layer-runner system. Layer runners handle the 14-layer system path; coding formations handle multi-agent implementation work.

## Core Decision

Use **bijective task packets** to send coding agents into formations.

A formation is not a chat room. It is a preplanned work pattern with roles, file ownership, handoff signals, receipts, and tests.

```text
user goal
  -> intent packet
  -> bijective task packet
  -> formation plan
  -> role packets
  -> code/test/doc receipts
  -> integration gate
  -> deploy test
```

## Existing Source Anchors

This roadmap should reuse the existing formation and squad material, not replace it.

| Source | What it contributes |
|---|---|
| `docs/specs/MASTER_ARCHITECTURE_CONTRACT_21D_M4_SQUAD.md` | Canonical deployment contract for 21D state, M4 position, swarm composite node state, HYDRA ordering, and promotion gates. |
| `docs/specs/TOKENIZER_EXECUTION_LATTICE_ROLE_v1.md` | Boundary rule: tokenizer makes operations routeable/reversible; governance, crypto, capability controls, execution policy, and verification decide safety and trust. |
| `notes/sphere-grid/KO-Command/T2-Formation-Swap/` | Formation Swap skill sphere: checkpoint-swap-restore, role reassignment, zero-downtime rotation, and training pairs. |
| `scripts/generate_kids_group_physics_sft.py` | Existing SFT generator for formation concepts: hexagonal formation, concentric rings, phase coherence, task handoff, Byzantine detection, formation swap, pair bonding, adaptive scatter, and center-of-mass stability. |
| `docs/chatbot-corpus.json` | Clone-trooper lesson: fixed canon/allegiance and squad roles as alignment drills. |
| `C:\Users\issda\OneDrive\SCBE-Archives\training_artifacts_2026-04\notion_export_unpacked\Export-d3f8086e-07e0-444f-9291-10b7fe375b22\🌊 Swarm Deployment Formations 476ba4d2332048a58843ba25b53d0d07.md` | Notion source for six-agent swarm deployment formations: hexagonal ring, tetrahedral, concentric rings, and adaptive scatter. |
| `C:\Users\issda\OneDrive\SCBE-Archives\training_artifacts_2026-04\notion_export_unpacked\Export-d3f8086e-07e0-444f-9291-10b7fe375b22\Define AI employee roles and responsibilities d82480b2c9f54900afdd871161e88769.md` | Notion source for AI employee roles. Cloud-only at last inspection, so fetch before relying on content. |

## Formation Geometry Reuse

The coding formations should inherit these existing patterns:

| Existing formation | Coding use |
|---|---|
| Hexagonal ring | Default six-role formation when all roles need equal visibility. Good for review and consensus. |
| Tetrahedral / 3D | Higher fault-tolerance formation when one role can fail without stopping the whole task. |
| Concentric rings | Inner ring handles authority/gates; outer ring handles research, file management, and support. |
| Adaptive scatter | Used when a large repo search needs independent scouts with low collision risk. |
| Formation swap | Used when a role is stuck, failing, or exhausted; checkpoint, swap, restore, continue. |

For coding work, the best default is **concentric rings**:

```text
inner ring: planner, verifier, integrator
outer ring: researcher, scout, coder, firefighter, file_manager, context_roller
```

The inner ring protects task authority and promotion. The outer ring performs work and gathers evidence.

## Formation Roles

| Role | Purpose | Write access | Output |
|---|---|---|---|
| `researcher` | Finds source docs, repo entrypoints, existing tests, and external references when needed. | No writes by default. | Research packet with exact file/source pointers and reject list. |
| `scout` | Reads local code and maps the smallest implementation path. | No writes. | File ownership plan and test plan. |
| `coder` | Implements bounded changes in assigned paths only. | Owned files only. | Patch receipt plus changed paths. |
| `firefighter` | Handles bugs, failing tests, crashes, and broken gates. | Narrow fix paths only. | Root cause, fix patch, regression test. |
| `file_manager` | Sorts generated outputs, manifests, research captures, artifacts, and release cleanliness. | Generated/artifact/docs paths only unless explicitly assigned. | Cleanup receipt and path movement manifest. |
| `context_roller` | Maintains rolling task state behind the scenes so work survives compaction and long sessions. | Handoff/context files only. | Rolling context packet and compaction summary. |
| `verifier` | Runs tests, checks schemas, compares receipts, and blocks bad promotion. | No writes except reports. | Verification report. |
| `integrator` | Merges role outputs, resolves conflicts, updates docs, and emits final receipt. | Shared integration files only. | Integrated patch and final receipt. |

## Context Roller

The `context_roller` is a first-class role.

Its job is to prevent context cliffs by creating small rolling packets while other agents work.

It should capture:

- current goal
- active formation
- role assignments
- files read
- files changed
- tests run
- failing commands
- accepted decisions
- rejected paths
- next action

It should not summarize everything. It should preserve only what is needed to resume.

Recommended packet:

```json
{
  "schema_version": "scbe_rolling_context_packet_v1",
  "task_id": "layer-runner-cli",
  "formation_id": "scout-coder-firefighter-verifier",
  "phase": "implementation",
  "current_owner": "coder",
  "files_read": [],
  "files_changed": [],
  "commands_run": [],
  "decisions": [],
  "blocked_on": [],
  "next_action": "run focused tests",
  "packet_sha256": "<computed>"
}
```

## Initial Formations

### 1. Scout Coder Verifier

Use for small clean features.

```text
scout -> coder -> verifier -> integrator
```

Good target:

- Add one GeoSeal CLI command.
- Add one focused test file.
- Update one doc.

### 2. Researcher Scout Coder Verifier

Use when outside research or old notes must be turned into code.

```text
researcher -> scout -> coder -> verifier -> integrator
```

Good target:

- Convert `*-research.json` into one testable feature lane.

### 3. Firefighter Loop

Use when tests are failing.

```text
verifier -> firefighter -> verifier -> integrator
```

Rules:

- Firefighter gets the failing command, stack trace, and touched files only.
- Firefighter must add or update a regression test when practical.
- Firefighter cannot broaden scope without a new packet.

### 4. File Manager Cleanup

Use before release.

```text
file_manager -> verifier -> integrator
```

Rules:

- Preserve source, canonical corpora, and local model stores.
- Move generated/raw research artifacts out of root.
- Do not delete without a manifest and verification.

### 5. Long Session Formation

Use for multi-hour work.

```text
context_roller runs beside every phase
researcher/scout/coder/firefighter/verifier/integrator proceed normally
```

Rules:

- Context roller writes small rolling packets every phase change.
- It updates before compaction-sensitive steps.
- It emits a final handoff even if implementation is incomplete.

## Bijective Task Packet

Every formation starts from a reversible task packet:

```json
{
  "schema_version": "scbe_bijective_coding_task_v1",
  "task_id": "geoseal-layer-registry-cli",
  "goal": "Add a GeoSeal command that prints the layer runner registry.",
  "formation": "scout-coder-verifier",
  "owned_paths": [
    "src/geoseal_cli.py",
    "tests/terminal/test_geoseal_layer_runner_cli.py"
  ],
  "blocked_paths": [
    "training-data/",
    "artifacts/"
  ],
  "required_signal": "formation-hop:scout->coder:bounded-edit",
  "success_gate": "python -m pytest tests/terminal/test_geoseal_layer_runner_cli.py -q",
  "receipt_required": true
}
```

## Formation Receipts

Each role emits:

```json
{
  "schema_version": "scbe_formation_role_receipt_v1",
  "task_id": "geoseal-layer-registry-cli",
  "formation_id": "scout-coder-verifier",
  "role": "coder",
  "input_packet_sha256": "<hash>",
  "output_packet_sha256": "<hash>",
  "files_changed": [],
  "commands_run": [],
  "tests_passed": [],
  "tests_failed": [],
  "handoff_signal": "formation-hop:coder->verifier:test",
  "verdict": "pass"
}
```

## First Implementation Target

Do this after the layer-runner registry exists:

1. Add `config/formations/coding_formations.json`.
2. Add `geoseal formation-plan --task task.json --json`.
3. Add dry-run receipts only.
4. Add tests for:
   - valid formation plan
   - duplicate role failure
   - missing owner failure
   - invalid handoff signal failure
   - context roller packet round trip

Do not run real parallel agents until dry-run formation planning is deterministic.

## Training Target

Train models to choose formation and role chain:

```text
goal -> task packet -> formation -> role sequence -> gate
```

Good SFT row:

```json
{
  "prompt": "User asks to add a GeoSeal CLI command and tests.",
  "completion": {
    "formation": "scout-coder-verifier",
    "roles": ["scout", "coder", "verifier", "integrator"],
    "required_receipts": true,
    "first_gate": "focused pytest"
  }
}
```

Keep the training compact. Do not train on whole conversations when packet traces are enough.

## Coding Pazaak Simulation

Use a turn-based table simulation as the long-form training game.

The point is not the card-game theme. The useful property is hidden-hand, visible-board coordination with non-greedy cooperative scoring:

- each role has private context or capability cards,
- the system does not need to inspect the private hand,
- each role plays one legal move to the shared board,
- the board records only visible plays, totals, lanes, and receipts,
- success is measured by legal progression toward the task target,
- roles are rewarded for useful shared progress and low-cost handoffs, not isolated point hoarding.

This is a good repeatable simulator for coding formations because it teaches:

- turn order,
- handoff discipline,
- role specialization,
- legal move constraints,
- hidden local context with shared public state,
- cooperative non-greedy action selection,
- verifier/integrator gates at the table level.

Prototype:

```powershell
python scripts/system/simulate_coding_formation.py --json
```

Focused test:

```powershell
python -m pytest tests/system/test_simulate_coding_formation.py -q
```

Current prototype behavior:

```text
task packet -> formation choice -> role turns -> table-game board plays + coding deck draws -> receipts -> final verdict
```

The simulation is intentionally pure math and local JSON. It should become the first source for compact SFT traces before real agents are allowed to run formation work.

The current simulator draws public coding substrate cards from `config/coding_decks/coding_deck_manifest.v1.json` while keeping each role's private hand hidden. This ties formation practice to the 899-card grounded deck:

| Role kind | Deck group |
|---|---|
| `researcher`, `scout`, `planner` | pairing cards |
| `coder`, `firefighter` | language-view cards |
| `file_manager`, `verifier` | STIB structure cards |
| `context_roller` | binary byte cards |
| `integrator` | operation cards |
