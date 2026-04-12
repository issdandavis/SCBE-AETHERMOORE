---
name: "scbe-dry-run-rubix"
description: "Dry-run cross-language verification for SCBE changes using narrow-region checks, Sacred Tongues lenses, and cube-style parity gates."
---

# SCBE Dry-Run Rubix

Use this skill before non-trivial changes land in the SCBE-AETHERMOORE codebase.

## Use when

- a change touches more than one language or runtime surface
- a bug involves Windows paths, subprocess dispatch, crypto fallbacks, or dual-package drift
- a gateway tool, workflow lane, or 14-layer math surface changed
- you need a preflight hold/ship judgement before merge

## What this skill does

1. Read the changed scope and classify affected languages, modules, and invariants.
2. Run dry-run style verification first. Prefer compile, collect-only, or no-run checks over live execution.
3. Check narrow-region regressions explicitly:
   - cross-drive Windows paths
   - subprocess stderr propagation
   - zero-distance and degenerate math inputs
   - liboqs/PQC fallback behavior
   - Unicode normalization and tokenizer round-trip edges
4. Compare parity across the touched surfaces when there is more than one implementation.
5. Emit a concise verdict: `SHIP`, `HOLD`, or `BLOCK`.

## Default commands

TypeScript:

```powershell
npm run typecheck
npm test -- --runInBand
```

Python:

```powershell
python -m pytest --collect-only -q tests
python -m pytest tests -q
```

Rust (if touched):

```powershell
cargo check --manifest-path rust/scbe_core/Cargo.toml
cargo test --no-run --manifest-path rust/scbe_core/Cargo.toml
```

## Reporting format

- one-line verdict with why
- failing surfaces first
- concrete remediation lines with file references

## Guardrails

- do not treat a partial probe as a clean pass
- do not skip narrow-region checks on Windows-sensitive changes
- do not rely on semantic summaries when deterministic regressions are possible
- do not ship cross-language math changes without parity evidence
