# Changelog

## 4.3.0 - 2026-05-13

### Added

- **`scbe abacus run --d-h <v> --pd <v> [--json]`**: deterministic BigInt L12 harmonic wall + L13 tier scoring with bit-identical output across platforms. Bridges to `runGovernanceAbacus` from `scbe-aethermoore/harmonic`. JSON output schema `scbe_governance_abacus_v1` includes exact rational score (`num`/`den`), fixed-precision decimal, four-tier `tier`, and `trit` (+1 ALLOW, 0 uncertain, -1 DENY).
- **`scbe abacus help`** subcommand summarising the formula, tiers, and trit collapse.
- **Typo correction (suggest-only)**: unknown top-level commands within Levenshtein distance ≤ 2 of a known scbe command now print `scbe: '<typo>' is not a scbe command. Did you mean 'scbe <suggestion>'?` and exit 2. Unknown-but-not-close inputs fall through to the geoseal passthrough unchanged. No auto-execute — the user re-types deliberately.

### Changed

- **Bumped peer dependencies**: `scbe-aethermoore ^4.0.8 → ^4.1.0` (required for the `runGovernanceAbacus` export consumed by `scbe abacus`), `scbe-agent-bus ^0.2.1 → ^0.3.0` (required for the hosted-credential gate behind `scbe agent-bus send`).

## 4.2.0

- **`scbe flow plan|packetize|status|run-next|continue|report`** bridge to the operator-loop in `scripts/scbe-system-cli.py`.
- **`scbe agent-bus serve|send|ui|health|upgrade`** passthrough to the locally-installed `scbe-agent-bus` binary, with a clear error message if it's missing.
- **`scbe upgrade`** defers to `scbe-agent-bus upgrade` when present so the hosted-run guidance has a single source of truth.

## 4.1.5

- Earlier history not migrated into this CHANGELOG. See npm release history for prior versions.
