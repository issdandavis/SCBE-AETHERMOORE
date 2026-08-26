# Start Here

This repository is a large monorepo with real product code, shared platform code, active research, and archived material living together.

Do not start by browsing the root at random.

## Fast Path

Run the active product surface before exploring the monorepo:

```bash
npm install
npm run product:release-gate
```

Then use this order:

1. [Product Quickstart](docs/PRODUCT_QUICKSTART.md)
2. [Aether Workspace Architecture](docs/product/AETHER_WORKSPACE_ARCHITECTURE.md)
3. [Repo Surface Map](docs/REPO_SURFACE_MAP.md)
4. [Canonical System State](CANONICAL_SYSTEM_STATE.md)
5. [Monorepo Consolidation Authority](docs/specs/MONOREPO_CONSOLIDATION_AUTHORITY.md)

The gate is the release proof: it starts AetherBrowser and AetherDesk, verifies
both, executes one bounded action, and emits a consolidated receipt.

## What To Expect

This repo currently has four real zones:

- `product`
- `platform`
- `research`
- `archive`

The current primary product lane is the AetherBrowser + AetherDesk workspace:

- `src/aetherbrowser/` and `scripts/aetherbrowser/` — governed browser/model runtime
- `src/extension/` — shared browser viewport
- `aetherdesk/` — local operator shell, approvals, tasks, and receipts
- `scripts/system/product_surface_release_gate.py` — end-to-end release proof

The shared platform that supports that lane currently lives mainly in:

- `src/tokenizer/`
- `src/tongues/`
- `src/coding_spine/`
- `src/governance/`
- `src/crypto/`
- `python/scbe/`

## If You Want The Product First

Open these first:

1. [README.md](README.md)
2. [docs/PRODUCT_QUICKSTART.md](docs/PRODUCT_QUICKSTART.md)
3. [docs/ops/INVESTOR_AND_OPERATOR_QUICKSTART_2026-05-02.md](docs/ops/INVESTOR_AND_OPERATOR_QUICKSTART_2026-05-02.md)
4. [docs/ops/DISTRIBUTION_PACKAGE_MAP_2026-05-02.md](docs/ops/DISTRIBUTION_PACKAGE_MAP_2026-05-02.md)
5. [docs/REPO_SURFACE_MAP.md](docs/REPO_SURFACE_MAP.md)
6. [docs/specs/MONOREPO_CONSOLIDATION_AUTHORITY.md](docs/specs/MONOREPO_CONSOLIDATION_AUTHORITY.md)

## If You Want Canonical Definitions

Open these first:

1. [CANONICAL_SYSTEM_STATE.md](CANONICAL_SYSTEM_STATE.md)
2. [docs/specs/SCBE_CANONICAL_CONSTANTS.md](docs/specs/SCBE_CANONICAL_CONSTANTS.md)
3. [docs/SPEC.md](docs/SPEC.md)
4. [docs/CONCEPTS.md](docs/CONCEPTS.md)

## If You Want Research Or Training

Assume those surfaces are useful but non-primary unless explicitly marked otherwise.

Start with:

- `training/`
- `training-data/`
- `scripts/train/`
- `scripts/eval/`
- `notebooks/`
- `notes/`

## If You Want Archive Material

Do not treat archived captures or generated evidence as the product surface.

Use archive lanes only when the task is explicitly about historical evidence, imports, screenshots, or old generated outputs.
