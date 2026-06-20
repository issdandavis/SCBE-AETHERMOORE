# MASTER ARCHITECTURE CONTRACT (21D + M4 + Squad)

Status: canonical deployment contract for runtime promotion.

This contract freezes the deploy-critical backbone and defines what can evolve
only in shadow mode.

## 1) Canonical Core (frozen for deployment)

### 21D canonical state layout

- `1-3`: SCBE context and crypto control
- `4-6`: dual-lattice navigation
- `7-9`: PHDM cognitive position
- `10-12`: sacred tongue phase encoding
- `13-15`: M4 model manifold position
- `16-18`: swarm composite node state
- `19-21`: HYDRA ordering/meta control

### Governance micro-alphabet

Allowed control states:

- `+1`: constructive/amplify
- `-1`: destructive/contract
- `+0`: neutral-pass/abstain-continue
- `-0`: neutral-hold/abstain-quarantine

### Canonical cost family

All deploy surfaces must route through the canonical harmonic family from:

- `docs/specs/CANONICAL_FORMULA_REGISTRY.md`

Legacy alternatives are allowed only as:

- compatibility mode,
- bounded scorer mode,
- or explicit experiment mode.

## 2) Deployment Runtime Surfaces

Deployment claims apply only to these runtime surfaces:

- `api/main.py` (governance/control API)
- `src/api/main.py` (product API)
- `scripts/scbe-system-cli.py` (operator entrypoint)

Everything else is supporting, experimental, or archival unless explicitly
promoted through gates in Section 4.

## 3) Extension Points (allowed to evolve in shadow mode)

These can iterate without changing canonical state semantics:

- MAZE expert routing/fusion
- hypersphere retrieval channels
- spin-voxel reranker channels
- octree/quasi-octree retrieval channels

Rule: extension channels can influence ranking and policy recommendations, but
cannot become write-path authorities until promotion gates pass.

## 4) Promotion Gates (required before production integration)

An experimental module can be promoted only if all gates pass:

1. **Correctness gate**
   - dedicated unit tests with deterministic pass in CI.
2. **Benchmark gate**
   - quality >= baseline on scoped benchmark.
   - p95 latency regression must be bounded and documented.
3. **Governance gate**
   - fail-closed behavior on missing/invalid signals.
   - no bypass of quarantine/deny paths.
4. **Rollback gate**
   - feature flag or route switch to disable module quickly.
5. **Docs gate**
   - spec + operator runbook + benchmark artifact references.

## 5) Deployment Checklist (minimum)

- Canonical docs present and current:
  - `docs/specs/CANONICAL_SYSTEM_STATE.md`
  - `docs/specs/CANONICAL_FORMULA_REGISTRY.md`
  - `docs/specs/MASTER_ARCHITECTURE_CONTRACT_21D_M4_SQUAD.md`
- Runtime entrypoints present:
  - `api/main.py`
  - `src/api/main.py`
  - `scripts/scbe-system-cli.py`
- Packaging profile present:
  - `config/offline_bundle_profiles.json` with deploy profile.
- Smoke tests pass for deployment lane.

## 6) Deployment Language Rules

Use the following wording unless a narrower scope is provided:

- Operational: yes
- Pilot-ready: yes
- Enterprise-regulated-ready: no (unless separately validated)

Never use blanket "production ready" without naming the exact runtime surface.
