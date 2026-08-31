# SYSTEM_MAP — load order from core to extension

**Updated:** 2026-08-31  
**Scope:** live tree at `main` after Dependabot #2807 (`60fd157`).  
**Diagram:** [SYSTEM_FLOW.mmd](SYSTEM_FLOW.mmd)

This file is the root orientation map. It does **not** move source trees. Physical
moves of `src/`, `api/`, `scripts/`, or workflow files would break package
exports, tests, and CI. Structure here means *read and load order*, not a
mass rename.

When documents conflict, use the authority order in
[docs/CANONICAL_SYSTEM_STATE.md](docs/CANONICAL_SYSTEM_STATE.md).

## How to enter the repo

1. This file.
2. [SYSTEM_FLOW.mmd](SYSTEM_FLOW.mmd)
3. [START_HERE.md](START_HERE.md)
4. [README.md](README.md)
5. [docs/REPO_SURFACE_MAP.md](docs/REPO_SURFACE_MAP.md)
6. Named runtime code for the profile you are changing.

```bash
npm install
npm run product:release-gate
```

## Load order

| Order | Layer | What loads | Live paths |
|---:|---|---|---|
| 0 | Authority | Specs, formulas, claim bounds | `docs/specs/`, `docs/CANONICAL_SYSTEM_STATE.md` |
| 1 | Core | 14-layer math, PQC, harmonic/spectral primitives | `packages/kernel`, `src/scbe_14layer_reference.py`, `src/crypto`, `src/pqc`, `src/harmonic`, `rust/scbe_core` |
| 2 | Board | Model proposes; board decides | `src/governance`, `src/tongues`, `src/tokenizer`, `src/spiralverse` |
| 3 | Packages | Public scan / CLI / library exports | `src/index.ts`, `python/scbe`, `src/scbe_aethermoore`, `bin/`, `packages/cli` |
| 4 | Control planes | HTTP and edge adapters | `api/`, `src/api/`, `src/gateway`, `netlify/functions`, `vercel.json` |
| 5 | Product | AetherBrowser + AetherDesk | `src/aetherbrowser`, `src/extension`, `aetherdesk`, `scripts/system/product_surface_release_gate.py` |
| 6 | Extensions | Fleet, MCP, Hydra, visual/desktop apps | `src/fleet`, `src/agentic`, `mcp/`, `hydra/`, `scbe-visual-system`, `conference-app` |
| 7 | Non-primary | Research, training, generated, archive | `research/`, `training/`, `training-data/`, `notebooks/`, `notes/`, `archive/`, `artifacts/` |

Stay in layers 1–5 unless the task names layer 6 or 7.

## Runtime profiles

Name the profile. The four pipelines are aligned in role, not byte-identical.

| Profile | Source |
|---|---|
| `TS_PIPELINE14` | `packages/kernel/src/pipeline14.ts` |
| `PY_REFERENCE14` | `src/scbe_14layer_reference.py` |
| `PY_FULL14` | `src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py` |
| `PUBLIC_SCAN` | `src/index.ts`, `src/scbe_aethermoore/__init__.py` |

Layer 11 aggregation and Layer 13 decisions can differ across profiles.

## Request flow

```
input text or proposed tool call
        ↓
L1–2 context / realification
        ↓
L3–4 weighted transform / Poincaré embed
        ↓
L5–7 hyperbolic distance / breathing / Möbius phase
        ↓
L8–10 realms / spectral / spin
        ↓
L11 temporal distance
        ↓
L12 bounded harmonic score
        ↓
L13 ALLOW | QUARANTINE | ESCALATE | DENY
        ↓
L14 telemetry + receipt
        ↓
product surface (scan CLI, API, AetherDesk action, Netlify function)
```

Canonical equations live in `docs/specs/CANONICAL_FORMULA_REGISTRY.md`, not in
this map.

## What was reviewed for this map

Reviewed against the live root listing and `src/` listing on `60fd157`:

- Root is a hybrid monorepo: product, platform, research, and archive coexist.
- `src/` holds both the TypeScript package surface and many Python modules.
- Duplicate architecture docs exist (`docs/ARCHITECTURE.md` vs
  `docs/specs/ARCHITECTURE.md`). Prefer `docs/specs/` and this map.
- `docs/SYSTEM_OVERVIEW.mermaid.md` is the older package-centric diagram.
  This root mermaid is the load-order diagram.
- Draft PR #2784 still wants to delete live workflows. Leave it draft until
  rebase + CI. Do not treat workflow deletion as part of this map.

## In-order vs out-of-order root noise

Treat these as support, not the boot path:

- generated: `artifacts/`, `dist/`, `_kaggle_pull/`
- research overflow: `notes/`, `notebooks/`, `paper/`, `references/`, `articles/`
- training accumulation: `training/`, `training-data/`
- product-adjacent but not first-run: `game/`, `desktop/`, `shopify/`, `spaces/`
- infra copies: multiple `Dockerfile*` and `docker-compose*.yml` — use
  `docker-compose.unified.yml` or the npm `docker:*` scripts when you need a stack

## Commands by layer

```bash
# Layer 5 — product proof
npm run product:release-gate

# Layer 3 — package
npm run build && npm test && npm run test:python

# Layer 4 — APIs
python -m uvicorn src.api.main:app --reload --port 8000
python -m uvicorn api.main:app --reload --port 8080

# Layer 1 — rust core
npm run test:rust
```

## Merge confidence after this map

| Claim | Confidence |
|---|---|
| #2807 is on `main` and does not require a follow-up code change for types-only `@netlify/functions` | 92% |
| Electron 44 is safe for current 64-bit builder targets | 88% |
| This map matches the live tree and existing canonical docs | 90% |
| Physically reshuffling directories now would be safe | 15% — do not do it |
| Draft #2784 can merge without rebase | 35% |
