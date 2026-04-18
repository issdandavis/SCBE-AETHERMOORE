# SCBE-AETHERMOORE Monorepo Restructuring Plan

## Context

The project has grown to ~200+ files across 38 directories, all in a flat `src/` folder with no internal organization. The core math engine (the "kernel") is mixed in with application code (fleet orchestration, APIs, browser integrations, video processing, etc.). This makes it impossible to:

1. Know which files define the actual embedding model (needed for Vertex AI training)
2. Develop application features without risking kernel breakage
3. Onboard new contributors (or AI assistants) without confusion

The user wants **one monorepo, subdivided into clear packages**. PRs #127/#128 just added Vertex AI training infrastructure, making kernel identification even more urgent.

---

## Package Structure

```
SCBE-AETHERMOORE/
├── packages/
│   ├── kernel/          ← THE SEED (pure math, zero npm deps)
│   ├── crypto/          ← Post-quantum crypto (Node crypto only)
│   ├── brain/           ← 21D AI Brain Mapping
│   ├── fleet/           ← Multi-agent orchestration
│   ├── api/             ← REST API + Lambda + Gateway
│   └── app/             ← Everything else (symphonic, spiralverse, browser, video, etc.)
├── training/            ← Vertex AI (already merged via PR #127/#128)
├── tests/               ← Stays at root (no test file moves)
├── package.json         ← Root: adds workspaces, remaps exports
├── tsconfig.json        ← Root: project references only
└── tsconfig.base.json   ← Shared compiler options (unchanged)
```

### Dependency Tree (strictly acyclic)

```
kernel (0 deps) → crypto, brain, fleet → app, api
```

- **kernel** depends on NOTHING
- **crypto** depends on kernel (types only)
- **brain** depends on kernel
- **fleet** depends on kernel
- **app** depends on kernel, crypto, fleet
- **api** depends on kernel, crypto, fleet, app

---

## Package 1: `packages/kernel/` — THE SEED

**~30 files, ~5,000 lines, zero npm dependencies, zero Node.js APIs.**

### Files to move from `src/harmonic/`:

**Foundation:**
- `constants.ts` — Vector6D, Vector3D, Tensor types, CONSTANTS
- `assertions.ts` — assertFinite, assertIntGE, log2

**Core Geometry (L5-L8):**
- `hyperbolic.ts` — Poincaré ball: distance, Möbius add, exp/log maps (472 lines, most-imported file)
- `adaptiveNavigator.ts` — Adaptive hyperbolic geometry
- `hamiltonianCFI.ts` — Control flow integrity

**Sacred Tongues:**
- `sacredTongues.ts` — 6×256 tokenizer (494 lines)
- `languesMetric.ts` — 6D governance cost function
- `spiralSeal.ts` — SS1 spell-text encoding (imports sacredTongues only)

**14-Layer Pipeline:**
- `pipeline14.ts` — L1-L14 complete (739 lines)
- `harmonicScaling.ts` — H(d,R) harmonic wall (L12)
- `halAttention.ts` — Harmonic Attention Layer
- `audioAxis.ts` — FFT telemetry (L14)
- `vacuumAcoustics.ts` — Cymatic simulation (L14)

**Temporal System:**
- `temporalIntent.ts` — H_eff(d,R,x), IntentState, SecurityGate
- `temporalPhase.ts` — Multi-clock T-phase (FAST/MEMORY/GOVERNANCE/CIRCADIAN/SET)

**Voxel & CHSFN:**
- `scbe_voxel_types.ts` — Voxel Record types
- `chsfn.ts` — Cymatic-hyperbolic state-field network
- `quasiSphereOverlap.ts` — Squad overlap, consensus gradient
- `securityInvariants.ts` — 6 formal security invariants
- `triDirectionalPlanner.ts` — Tri-directional path planner
- `hyperbolicRAG.ts` — Hyperbolic retrieval scoring
- `entropicLayer.ts` — Escape detection, adaptive k
- `quasiSphereSlice.ts` — 2D slice simulator

**Detection & Identity:**
- `spectral-identity.ts` — Rainbow chromatic fingerprinting
- `triMechanismDetector.ts` — 3-mechanism adversarial detection
- `pqc.ts` — Pure-math PQC (NOT the Node crypto one — this is the harmonic one)
- `qcLattice.ts` — Quasicrystal lattice verification

**Geometry Extensions:**
- `sacredEggs.ts` — Ciphertext containers (imports hyperbolic only)
- `trustCone.ts` — Geometric access control (imports hyperbolic only)
- `fluxState.ts` — Dimensional flux tracking (imports adaptiveNavigator only)

**New file to create:**
- `governance-types.ts` — Extract `GovernanceTier` and `DimensionalState` from `fleet/types.ts` (pure type aliases, no deps)

---

## Package 2: `packages/crypto/`

**10 files from `src/crypto/`. Depends on: kernel (types only), Node.js crypto.**

Files: `envelope.ts`, `hkdf.ts`, `jcs.ts`, `kms.ts`, `nonceManager.ts`, `replayGuard.ts`, `replayStore.ts`, `bloom.ts`, `pqc.ts` (Node crypto PQC), `index.ts`

---

## Package 3: `packages/brain/`

**7 files from `src/ai_brain/`. Depends on: kernel.**

Files: `types.ts`, `unified-state.ts`, `detection.ts`, `bft-consensus.ts`, `quasi-space.ts`, `audit.ts`, `index.ts`

**Fix needed:** `types.ts` line 20 imports `GovernanceTier, DimensionalState` from `../fleet/types.js` → change to import from `@scbe/kernel/governance-types`

---

## Package 4: `packages/fleet/`

**~15 files from `src/fleet/`. Depends on: kernel.**

Files: `types.ts`, `agent-registry.ts`, `fleet-manager.ts`, `governance.ts`, `swarm.ts`, `task-dispatcher.ts`, `polly-pad.ts`, `polly-pad-runtime.ts`, `redis-orchestrator.ts`, `polly-pads/` subdir, `index.ts`

**Fix needed:** `types.ts` exports `GovernanceTier` and `DimensionalState` → re-export from `@scbe/kernel/governance-types` for backward compat

---

## Package 5: `packages/api/`

**~10 files. Depends on: kernel, crypto, fleet, app.**

Moves: `src/api/`, `src/gateway/`, `src/lambda/`

---

## Package 6: `packages/app/` — catchall

**Everything else (~100+ files). Depends on: kernel, crypto, fleet.**

Includes: `symphonic/`, `spiralverse/`, `spectral/`, `tokenizer/`, `agent/`, `agentic/`, `ai_orchestration/`, `browser/`, `video/`, `network/`, `spaceTor/`, `selfHealing/`, `security/`, `skills/`, `metrics/`, `rollout/`, `utils/`, `core/`, `constants/`, `errors/`, `integrations/`, `physics_sim/`, `cloud/`, `minimal/`, `science_packs/`

Also moves 3 harmonic files that use Node crypto: `voxelRecord.ts`, `phdm.ts`, `encryptedTransport.ts`

---

## Migration Phases (7 steps, each a separate commit)

### Phase 0: Baseline
- Run `npm test`, record passing count (479 L2-unit, 127+ total)
- Run `npm run typecheck`, confirm clean
- Create git tag `pre-monorepo`

### Phase 1: Extract kernel (highest value)
- Create `packages/kernel/src/`, move 30 pure-math files
- Create `packages/kernel/tsconfig.json` (extends `../../tsconfig.base.json`, composite: true)
- Create `packages/kernel/package.json` (`"name": "@scbe/kernel", "private": true`)
- Create `packages/kernel/src/index.ts` barrel export
- Create `packages/kernel/src/governance-types.ts` (extract from fleet/types.ts)
- Update root `tsconfig.json` to project references
- Run tests

### Phase 2: Extract crypto
- Create `packages/crypto/`, move `src/crypto/*.ts`
- Add tsconfig reference to kernel
- Run tests

### Phase 3: Extract fleet
- Create `packages/fleet/`, move `src/fleet/`
- Update `fleet/types.ts` to re-export GovernanceTier from kernel
- Run tests

### Phase 4: Extract brain
- Create `packages/brain/`, move `src/ai_brain/`
- Fix `types.ts` import to `@scbe/kernel/governance-types`
- Run tests

### Phase 5: Extract api
- Create `packages/api/`, move `src/api/`, `src/gateway/`, `src/lambda/`
- Run tests

### Phase 6: Consolidate app
- Move everything remaining in `src/` into `packages/app/src/`
- Update `package.json` exports map to point to `dist/packages/` paths
- Run full test suite, verify parity with Phase 0 baseline

### Phase 7: Polish
- Add `vitest.config.ts` path aliases for `@scbe/*`
- Create `training/KERNEL_MANIFEST.md` listing all kernel files
- Update `CLAUDE.md` with new structure
- Migrate test imports incrementally to `@scbe/` prefixed paths

---

## Config Changes

### Root `package.json` additions:
```json
{
  "workspaces": ["packages/*"],
  "scripts": {
    "build": "tsc --build",
    "build:kernel": "tsc --build packages/kernel"
  }
}
```

### Root `tsconfig.json` (becomes references-only):
```json
{
  "files": [],
  "references": [
    { "path": "packages/kernel" },
    { "path": "packages/crypto" },
    { "path": "packages/brain" },
    { "path": "packages/fleet" },
    { "path": "packages/api" },
    { "path": "packages/app" }
  ]
}
```

### Each package `tsconfig.json` pattern:
```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "rootDir": "src",
    "outDir": "../../dist/packages/<name>",
    "composite": true
  },
  "include": ["src/**/*"],
  "references": [{ "path": "../kernel" }]
}
```

---

## Tests Strategy

**Tests stay at root in `tests/`.** No test files move.

- `vitest.config.ts` gets path aliases so `@scbe/kernel` resolves to `packages/kernel/src/`
- Existing imports like `../../src/harmonic/hyperbolic.js` continue to work during migration via symlinks or aliases
- Test imports are updated incrementally (one file at a time) in Phase 7

---

## Training Pipeline Connection

`training/KERNEL_MANIFEST.md` will list every kernel file with annotations:
- Which files define embedding dimensions (constants.ts → Vector6D)
- Which files implement the Poincaré embedding (hyperbolic.ts)
- Which files define the CHSFN state space (chsfn.ts)
- Which files run the 14-layer pipeline (pipeline14.ts)

The `vertex-training.yml` workflow can reference `packages/kernel/` as the model source.

---

## What we do NOT do:
1. Do NOT publish separate npm packages — stays as one published package, internal workspaces only
2. Do NOT move Python files — only TypeScript restructures
3. Do NOT move test files — tests stay at root
4. Do NOT rename exported symbols — all public API names unchanged
5. Do NOT do it all at once — each phase is a separate commit

---

## Verification

After each phase:
1. `npm run typecheck` — no new errors
2. `npx vitest run tests/L2-unit/` — all 479 tests pass
3. `npx vitest run` — full suite passes
4. `git diff --stat` — only expected files changed
