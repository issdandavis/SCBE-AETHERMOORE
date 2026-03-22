# SCBE Concepts (Working Summary)

Use this as an orientation aid. Treat the repo code and the repo docs as source of truth for exact formulas/thresholds in the current version.

## Core Idea

SCBE-AETHERMOORE is an AI safety and governance framework built around a 14-layer pipeline. High-risk or adversarial behavior is intended to become increasingly expensive as it drifts from safe operation (hyperbolic geometry + a risk amplification "wall").

## 14-Layer Pipeline (Mnemonic)

- L1-4: Context processing and embedding into a hyperbolic space (Poincare ball model)
- L5: Hyperbolic distance is treated as an invariant signal
- L6-7: "Breathing" (radial scaling/containment) and phase transforms (Mobius addition)
- L8: Multi-well / realm separation (domains)
- L9-10: Spectral + spin coherence checks (stability/alignment)
- L11: Triadic temporal distance (immediate/memory/governance)
- L12: Harmonic scaling ("armor"/wall) risk amplification
- L13: Decision gate (ALLOW vs QUARANTINE/ESCALATE/DENY depending on repo version)
- L14: Optional audio axis / FFT telemetry features

To locate implementations, start with:
- `SCBE-AETHERMOORE-working/src/harmonic/pipeline14.ts`
- `SCBE-AETHERMOORE-working/src/harmonic/hyperbolic.ts`
- `SCBE-AETHERMOORE-working/src/harmonic/harmonicScaling.ts`

## Six Sacred Tongues (Langues Metric)

Six dimensions commonly referenced across docs/code:
- KO: Control & Intent
- AV: I/O & Messaging
- RU: Policy & Constraints
- CA: Logic & Computation
- UM: Security & Secrets
- DR: Types & Schema

## Polly Pads (Trust States)

Common trust states used to describe containment/workspace "breathing":
- POLLY: expanded/trusted
- QUASI: neutral/default
- DEMI: contracted/quarantined

## Dual Implementation Rule of Thumb

- TypeScript is canonical (production).
- Python is reference (research/validation).
- Prefer updating TypeScript first, then bring Python along and keep parity tests passing.
