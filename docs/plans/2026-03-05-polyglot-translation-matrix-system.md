# SCBE-AETHERMOORE Polyglot Translation Matrix (Whole System)

Date: 2026-03-05  
Scope: Entire system portability rubric (Python, TypeScript/Node, browser/UI, MCP, pipelines)

## 1. Goal

Provide a deterministic rubric for porting SCBE-AETHERMOORE subsystems across languages without changing behavior, governance outcomes, or auditability.

This matrix is the contract for:
- cross-language parity,
- replay-safe serialization,
- test vector reuse,
- staged migration (component-by-component, not big bang).

## 2. Language Targets

- L1: Python 3.11+ (reference for math-heavy modules and data ops)
- L2: TypeScript/Node 20+ (reference for MCP servers, app services, orchestration)
- L3: Browser TypeScript (MCP App UI, visualization, operator controls)
- L4: Rust (optional high-assurance backend for crypto/math hot paths)
- L5: Go (optional service runtime for high-throughput gateways)

## 3. Portability Rubric

Score each subsystem before and after port:

- `P0` Interface parity: Same input/output schema and field names.
- `P1` Determinism parity: Same output for shared test vectors.
- `P2` Numeric parity: Error bounds documented for float-heavy logic.
- `P3` Security parity: Same boundary checks, fail-closed behavior, and signature validation.
- `P4` Operational parity: Same CLI/MCP commands and telemetry fields.

A subsystem is "portable-ready" only when all `P0-P4` are green.

## 4. Translation Matrix

| Subsystem | Canonical Impl | Required Invariants | TS/Node Port Rule | Python Port Rule | Notes |
|---|---|---|---|---|---|
| Sacred Tongues tokenizer | TS (`src/tokenizer/ss1`) | Exact token roundtrip, tongue detection parity | Preserve token grammar and prefix rules exactly | Mirror decode/encode bytes-first, not string-first | Keep canonical token vectors in shared fixtures |
| Hyperbolic geometry core | TS+Python | Poincare metric invariance, triangle inequality constraints | Use same `acosh` formula + bounded domain guards | Same formula; reject out-of-ball points | No silent clamping except documented |
| Governance decision engine | TS (`ai_brain`) + MCP | Same ALLOW/DEFER/QUARANTINE/DENY outcomes for vectors | Port threshold tables as data, not code constants | Same threshold data loaded from shared schema | Decision proof fields must be identical |
| Cymatic voxel 6D+t | Python (`hydra/voxel_storage.py`) + TS app model | Dimensions, Chladni addressing, authority+intent fields, temporal slice semantics | Normalize snake_case and ms/sec at boundary only | Emit canonical field aliases when needed | Keep one canonical schema and adapters |
| HYDRA CLI + orchestration | Python (`hydra/*.py`) | Command semantics and output JSON fields | Use wrappers for CLI in Node side, avoid behavior forks | CLI remains canonical for shell workflows | Prefer machine-readable JSON modes |
| MCP SCBE server | Node (`mcp/scbe-server/server.mjs`) | Tool names, schemas, error contract, fail-closed default | Keep request validation + adapter layers | Python tools called via controlled subprocesses | Never pass raw unvalidated args to shell |
| Research/ingest pipelines | Python (`src/knowledge/*`) | Deterministic dedup + source attribution | Node side consumes exported artifacts only | Python remains source of ingest truth | Artifact schema versioned |
| Browser/agent surfaces | TS/browser + Playwright | Same workflow state transitions and result packet keys | Keep UI state model versioned | Python can consume packet JSON only | No implicit field assumptions |
| Crypto envelopes/seals | Mixed | Hash/signature reproducibility and key scope | Use canonical serialization before hashing | Same canonical serializer order | Never hash language-native map ordering |
| Test harness + vectors | Mixed (`tests/*`) | Shared golden vectors for every critical path | TS tests must load same fixtures as Python | Python tests must load same fixtures as TS | Add parity tests before feature tests |

## 5. Canonical Shared Contracts

These artifacts must be language-neutral and versioned:

- `schemas/*.json` for IO contracts.
- `tests/interop/test_vectors.json` for deterministic parity.
- `docs/specs/*` for math and governance invariants.
- MCP tool schemas (single source surfaced by server).

## 6. Anti-Drift Rules

- No new field names without schema update + adapter update.
- No timestamp unit ambiguity:
  - internal canonical: Unix milliseconds in interchange.
  - adapters may accept seconds but must normalize at boundary.
- No implicit enum expansion (must update schema + tests first).
- Any new algorithm requires:
  1. reference vectors,
  2. parity tests in both languages,
  3. migration note.

## 7. Porting Workflow (Per Subsystem)

1. Freeze canonical schema and vectors.  
2. Implement target-language adapter layer first.  
3. Implement core logic.  
4. Run parity suite (`P0-P4`).  
5. Enable in shadow mode.  
6. Promote to primary only after parity burn-in window.

## 8. Immediate Priority Queue

1. Voxel 6D+t cross-language parity (Python CLI <-> MCP server <-> TS app).  
2. Governance decision parity vectors (TS brain <-> Python consumers).  
3. Sacred Tongue tokenizer parity vectors (TS canonical <-> Python decoder wrappers).  
4. Unified schema registry and version gates in CI.

## 9. Definition of Done (Whole System)

Whole-system polyglot readiness is complete when:

- all core subsystems satisfy `P0-P4`,
- CI enforces schema/vector parity,
- MCP tools expose normalized canonical outputs,
- operator docs map every command/tool to canonical contracts.
