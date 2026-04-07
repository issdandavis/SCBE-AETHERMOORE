# SCBE-AETHERMOORE System Review and Runtime Spec
**Date**: 2026-04-02  
**Status**: Audit + consolidation spec  
**Purpose**: Record the current live system honestly, identify contract drift, and define the canonical runtime/public/research boundaries for future work.

---

## Scope

This review covered the current public and runtime-facing surfaces that shape how SCBE-AETHERMOORE is understood and used:

- [README.md](C:/Users/issda/SCBE-AETHERMOORE/README.md)
- [package.json](C:/Users/issda/SCBE-AETHERMOORE/package.json)
- [pyproject.toml](C:/Users/issda/SCBE-AETHERMOORE/pyproject.toml)
- [api/main.py](C:/Users/issda/SCBE-AETHERMOORE/api/main.py)
- [api/governance-schema.yaml](C:/Users/issda/SCBE-AETHERMOORE/api/governance-schema.yaml)
- [src/api/index.ts](C:/Users/issda/SCBE-AETHERMOORE/src/api/index.ts)
- [src/api/govern.ts](C:/Users/issda/SCBE-AETHERMOORE/src/api/govern.ts)
- [src/governance/runtime_gate.py](C:/Users/issda/SCBE-AETHERMOORE/src/governance/runtime_gate.py)
- [src/spiralverse/temporal_intent.py](C:/Users/issda/SCBE-AETHERMOORE/src/spiralverse/temporal_intent.py)
- [src/spiralverse/aethermoor_spiral_engine.py](C:/Users/issda/SCBE-AETHERMOORE/src/spiralverse/aethermoor_spiral_engine.py)
- [src/video/dye_injection.py](C:/Users/issda/SCBE-AETHERMOORE/src/video/dye_injection.py)
- [docs/API.md](C:/Users/issda/SCBE-AETHERMOORE/docs/API.md)
- [docs/research/architecture-overview.html](C:/Users/issda/SCBE-AETHERMOORE/docs/research/architecture-overview.html)
- [docs/specs/SYSTEM_BLUEPRINT_v2_CURRENT.md](C:/Users/issda/SCBE-AETHERMOORE/docs/specs/SYSTEM_BLUEPRINT_v2_CURRENT.md)
- [docs/reports/SYSTEM_SURFACE_REVIEW_2026-03-26.md](C:/Users/issda/SCBE-AETHERMOORE/docs/reports/SYSTEM_SURFACE_REVIEW_2026-03-26.md)

---

## Executive Summary

SCBE-AETHERMOORE is not one monolithic, stable public contract yet. It is a coherent family of related systems sharing math, language, and governance concepts across four main surfaces:

1. package/install surface
2. public API/demo surface
3. richer internal runtime/governance surface
4. research and proof surface

The strongest current issue is **contract drift across governance surfaces**. Different entrypoints present different decision alphabets, threshold rules, and layer semantics. The system is real, but the specification is still distributed across multiple overlapping dialects.

The most important corrective action is:

1. define one canonical public decision alphabet
2. define one canonical public threshold story
3. distinguish runtime governance from diagnostic/proof instrumentation
4. treat blueprint/research claims as secondary to executable public contracts

---

## High-Severity Findings

### 1. Decision alphabet drift

The repo currently exposes multiple incompatible governance alphabets:

- TypeScript govern API: `ALLOW | DENY | ESCALATE | QUARANTINE`  
  [src/api/govern.ts](C:/Users/issda/SCBE-AETHERMOORE/src/api/govern.ts:55)
- OpenAPI schema: `ALLOW, DENY, ESCALATE, QUARANTINE`  
  [api/governance-schema.yaml](C:/Users/issda/SCBE-AETHERMOORE/api/governance-schema.yaml:142)  
  [api/governance-schema.yaml](C:/Users/issda/SCBE-AETHERMOORE/api/governance-schema.yaml:233)  
  [api/governance-schema.yaml](C:/Users/issda/SCBE-AETHERMOORE/api/governance-schema.yaml:316)
- TypeScript top-level risk API: `ALLOW | REVIEW | DENY`  
  [src/api/index.ts](C:/Users/issda/SCBE-AETHERMOORE/src/api/index.ts:58)
- Python runtime gate: `ALLOW | DENY | QUARANTINE | REROUTE | REVIEW`  
  [src/governance/runtime_gate.py](C:/Users/issda/SCBE-AETHERMOORE/src/governance/runtime_gate.py:98)  
  [src/governance/runtime_gate.py](C:/Users/issda/SCBE-AETHERMOORE/src/governance/runtime_gate.py:99)
- Spiralverse temporal gate tests and runtime: `ALLOW | QUARANTINE | DENY | EXILE`  
  [tests/test_aethermoor_spiral_engine.py](C:/Users/issda/SCBE-AETHERMOORE/tests/test_aethermoor_spiral_engine.py:42)  
  [src/spiralverse/temporal_intent.py](C:/Users/issda/SCBE-AETHERMOORE/src/spiralverse/temporal_intent.py:556)

This is the single biggest system-spec problem. Without a normalization rule, external consumers cannot know which decision family is canonical.

### 2. Threshold drift between docs and live public API lane

The published API docs and the live FastAPI demo lane do not use the same decision thresholds:

- Docs trust table:
  - `0.8 - 1.0 -> ALLOW`
  - `0.5 - 0.8 -> ALLOW with logging`
  - `0.2 - 0.5 -> QUARANTINE`
  - below that -> `DENY`  
  [docs/API.md](C:/Users/issda/SCBE-AETHERMOORE/docs/API.md:146)  
  [docs/API.md](C:/Users/issda/SCBE-AETHERMOORE/docs/API.md:147)  
  [docs/API.md](C:/Users/issda/SCBE-AETHERMOORE/docs/API.md:148)
- FastAPI demo pipeline:
  - `ALLOW` if `final_score > 0.6`
  - `QUARANTINE` if `final_score > 0.3`
  - else `DENY`  
  [api/main.py](C:/Users/issda/SCBE-AETHERMOORE/api/main.py:392)  
  [api/main.py](C:/Users/issda/SCBE-AETHERMOORE/api/main.py:394)  
  [api/main.py](C:/Users/issda/SCBE-AETHERMOORE/api/main.py:1775)

That makes the docs non-authoritative for actual behavior.

### 3. Canonical layer semantics drift

The public architecture pages and blueprint do not describe the same system with the same certainty level:

- README and architecture overview present the harmonic wall as `H(d,R) = R^(d^2)`  
  [README.md](C:/Users/issda/SCBE-AETHERMOORE/README.md:80)  
  [docs/research/architecture-overview.html](C:/Users/issda/SCBE-AETHERMOORE/docs/research/architecture-overview.html:45)
- Blueprint presents a broader formula `H(d, R, I) = R^((d * gamma_I)^2)` while still separately describing layer 12 as `H(d,R) = R^(d^2)`  
  [docs/specs/SYSTEM_BLUEPRINT_v2_CURRENT.md](C:/Users/issda/SCBE-AETHERMOORE/docs/specs/SYSTEM_BLUEPRINT_v2_CURRENT.md:39)  
  [docs/specs/SYSTEM_BLUEPRINT_v2_CURRENT.md](C:/Users/issda/SCBE-AETHERMOORE/docs/specs/SYSTEM_BLUEPRINT_v2_CURRENT.md:62)
- The live Spiralverse temporal gate uses `R ** (d**alpha * x)` with `alpha = 2.0`, which is yet another operational form  
  [src/spiralverse/temporal_intent.py](C:/Users/issda/SCBE-AETHERMOORE/src/spiralverse/temporal_intent.py:66)  
  [src/spiralverse/temporal_intent.py](C:/Users/issda/SCBE-AETHERMOORE/src/spiralverse/temporal_intent.py:127)

The system needs one canonical statement for public/runtime use and a separate section for experimental variants.

---

## Medium-Severity Findings

### 4. Public API surface is simpler than internal runtime gate

The public FastAPI lane is effectively a simplified demonstration/governance surface, while the Python runtime gate contains richer operational behaviors such as rerouting and review escalation:

- simplified public/demo lane in [api/main.py](C:/Users/issda/SCBE-AETHERMOORE/api/main.py)
- richer runtime lane in [src/governance/runtime_gate.py](C:/Users/issda/SCBE-AETHERMOORE/src/governance/runtime_gate.py:672)

This is acceptable only if documented explicitly. Right now it is easy to mistake the demo lane for the full internal contract.

### 5. 14-layer trace exists in a diagnostic lane, not in the public decision packet

The repo does have a real 14-layer instrumentation path:

- [src/video/dye_injection.py](C:/Users/issda/SCBE-AETHERMOORE/src/video/dye_injection.py)

But the current temporal Omega telemetry packet is a scalar summary packet, not a full layer-wise trace:

- [src/spiralverse/temporal_intent.py](C:/Users/issda/SCBE-AETHERMOORE/src/spiralverse/temporal_intent.py)
- [src/spiralverse/aethermoor_spiral_engine.py](C:/Users/issda/SCBE-AETHERMOORE/src/spiralverse/aethermoor_spiral_engine.py)

This matters for specs and for buyer-facing claims. The system should not imply that every runtime decision currently emits a 14-layer audit ladder when in practice that fuller trace exists in a proof/diagnostic lane.

### 6. Public proof and package surfaces are cleaner than the repo’s internal topology

The package manifests are already acting like bounded release surfaces:

- npm packages compiled `dist/src` only  
  [package.json](C:/Users/issda/SCBE-AETHERMOORE/package.json)
- Python packages only `spiralverse` and `code_prism`  
  [pyproject.toml](C:/Users/issda/SCBE-AETHERMOORE/pyproject.toml)

That is good. The documentation and website language still sometimes over-compress the monorepo into “one system” without telling readers which parts are actually installable or stable.

---

## Canonical Boundary Spec

### A. Canonical public package surface

This is the install/import surface. It should stay narrow.

- npm: [package.json](C:/Users/issda/SCBE-AETHERMOORE/package.json)
- PyPI: [pyproject.toml](C:/Users/issda/SCBE-AETHERMOORE/pyproject.toml)

**Rule**: package consumers should only rely on published package APIs, not repo-wide implementation details, notebooks, demos, or benchmark artifacts.

### B. Canonical public proof surface

This is where external readers should verify claims.

- [README.md](C:/Users/issda/SCBE-AETHERMOORE/README.md)
- [docs/research/architecture-overview.html](C:/Users/issda/SCBE-AETHERMOORE/docs/research/architecture-overview.html)
- [docs/eval/README.md](C:/Users/issda/SCBE-AETHERMOORE/docs/eval/README.md)
- [docs/research/eval-pack.html](C:/Users/issda/SCBE-AETHERMOORE/docs/research/eval-pack.html)
- [docs/reports/SYSTEM_SURFACE_REVIEW_2026-03-26.md](C:/Users/issda/SCBE-AETHERMOORE/docs/reports/SYSTEM_SURFACE_REVIEW_2026-03-26.md)

**Rule**: public claims should be reproduced from this lane first.

### C. Canonical public API contract

The public governance contract should be normalized to one decision alphabet and one threshold story.

**Recommended canonical public decision alphabet**

- `ALLOW`
- `QUARANTINE`
- `DENY`
- `ESCALATE`

**Mapping rule for non-public/internal decisions**

- `REVIEW -> ESCALATE`
- `REROUTE -> ESCALATE` or an auxiliary `redirect` field, not a top-level public decision
- `EXILE -> DENY` plus state metadata in public-facing summaries

This preserves internal richness without fragmenting the public contract.

### D. Internal runtime governance surface

These remain legitimate internal/system surfaces:

- [src/governance/runtime_gate.py](C:/Users/issda/SCBE-AETHERMOORE/src/governance/runtime_gate.py)
- [src/spiralverse/temporal_intent.py](C:/Users/issda/SCBE-AETHERMOORE/src/spiralverse/temporal_intent.py)
- [src/spiralverse/aethermoor_spiral_engine.py](C:/Users/issda/SCBE-AETHERMOORE/src/spiralverse/aethermoor_spiral_engine.py)

**Rule**: these may expose richer decisions and longer state machines, but adapters must normalize them before they are treated as canonical public output.

### E. Diagnostic / visualization surface

- [src/video/dye_injection.py](C:/Users/issda/SCBE-AETHERMOORE/src/video/dye_injection.py)
- browser demos under `docs/demos/`

**Rule**: these are proof and observability surfaces, not the canonical runtime contract.

### F. Research / blueprint surface

- [docs/specs/SYSTEM_BLUEPRINT_v2_CURRENT.md](C:/Users/issda/SCBE-AETHERMOORE/docs/specs/SYSTEM_BLUEPRINT_v2_CURRENT.md)
- benchmark, notebook, and experiment docs under `docs/specs/`, `scripts/research/`, and `notebooks/`

**Rule**: these may describe broader or future-state systems; they are not authoritative over executable package/API behavior.

---

## Recommended Canonical Runtime Story

For public-facing system explanation, use this exact hierarchy:

1. **Runtime thesis**: SCBE is a pre-execution governance layer.
2. **Distance thesis**: requests are projected into a geometric/semantic space and evaluated for drift.
3. **Cost thesis**: unsafe drift becomes more expensive at layer 12.
4. **Decision thesis**: the public contract returns `ALLOW`, `QUARANTINE`, `ESCALATE`, or `DENY`.
5. **Telemetry thesis**: richer runtime and diagnostic lanes may compute more detailed state, but that detail is downstream of the public contract.

---

## Immediate Spec Corrections Recommended

### 1. Unify public decision alphabet

Patch these surfaces to one canonical public decision family:

- [api/main.py](C:/Users/issda/SCBE-AETHERMOORE/api/main.py)
- [api/governance-schema.yaml](C:/Users/issda/SCBE-AETHERMOORE/api/governance-schema.yaml)
- [src/api/index.ts](C:/Users/issda/SCBE-AETHERMOORE/src/api/index.ts)
- [docs/API.md](C:/Users/issda/SCBE-AETHERMOORE/docs/API.md)
- public demos that echo runtime decisions

### 2. Unify public threshold story

Choose one public threshold family and delete the other from public docs.

### 3. Separate formula canon from experiment variants

Keep one canonical public wall formula and move variants such as intent-modulated or temporal variants into an explicit experimental section.

### 4. Document adapter rules from internal runtime to public contract

This is the cleanest way to keep internal richness without external confusion.

---

## Authority Order

For external readers and internal product work, use this order:

1. [README.md](C:/Users/issda/SCBE-AETHERMOORE/README.md)
2. [docs/research/architecture-overview.html](C:/Users/issda/SCBE-AETHERMOORE/docs/research/architecture-overview.html)
3. [docs/eval/README.md](C:/Users/issda/SCBE-AETHERMOORE/docs/eval/README.md)
4. canonical package manifests
5. public API schema
6. internal runtime specs
7. blueprint and research docs

If a lower-ranked surface contradicts a higher-ranked surface, the higher-ranked surface should win or the contradiction should be removed.

---

## Bottom Line

SCBE-AETHERMOORE already has the substance of a governed AI platform. The current weakness is not absence of system design. It is that the public contract, internal runtime, and research story are still overlapping.

The system should now be treated as:

- one bounded package/install surface
- one bounded public governance contract
- one bounded proof/eval surface
- one richer internal runtime surface
- one research/blueprint surface

That is the spec boundary needed before more demos, benchmarks, or product claims are added.
