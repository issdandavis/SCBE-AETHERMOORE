# SCBE Monorepo Restructuring Plan (Kernel-First)

This plan turns SCBE-AETHERMOORE into a single monorepo with internal workspaces, while preserving one publishable npm package surface.

## Target Package Layout

1. **`packages/kernel`**
   - Pure math/types seed.
   - Zero runtime dependencies.
   - Includes core geometry/scaling/types (`GovernanceTier`, `DimensionalState`) and invariant math.

2. **`packages/crypto`**
   - Cryptographic envelopes, KDF/HMAC, nonce/replay guards.
   - Depends on `kernel` only.

3. **`packages/brain`**
   - 21D brain mapping and higher-order embedding logic.
   - Depends on `kernel` and `crypto` where needed.

4. **`packages/fleet`**
   - Agent orchestration, governance tiers, roundtables, runtime coordination.
   - Depends on `kernel` + `brain`.

5. **`packages/api`**
   - Gateway/Lambda/REST adapters.
   - Depends on `fleet` + `crypto`.

6. **`packages/app`**
   - Catch-all integration layer for demos/UI/legacy adapters.

> Tests remain rooted in `/tests` and are not relocated during migration.

## Why Kernel Extraction Comes First

Training and deployment provenance requires a deterministic answer to: **"which files ARE the model?"**

To support that now, this repo includes a canonical kernel manifest used by CI/training:
- `training/kernel_manifest.yaml`
- `training/kernel_manifest.py`

The Vertex workflow validates this manifest before training and injects a manifest SHA into training job args/labels for traceability.

## Seven Migration Phases (One Commit Per Phase)

1. **Kernel carve-out (lowest risk / highest leverage)**
   - Move pure math/types into `packages/kernel`.
   - Keep old imports via compatibility re-exports.

2. **Crypto separation**
   - Move crypto primitives to `packages/crypto`.
   - Prohibit app-layer imports into crypto.

3. **Brain modularization**
   - Move brain/embedding modules to `packages/brain`.

4. **Fleet extraction**
   - Move governance/orchestration to `packages/fleet`.

5. **API package formation**
   - Isolate API transport/runtime concerns in `packages/api`.

6. **App catch-all stabilization**
   - Move demos/UI/integration glue into `packages/app`.

7. **Workspace hardening + release path**
   - Enforce dependency graph, lint boundaries, CI matrix.
   - Keep one public npm package; internal packages remain workspace-private.

## Non-Negotiables

- Root tests continue to run during every phase.
- No "big bang" move.
- Every phase must preserve runtime behavior and pass targeted tests.
