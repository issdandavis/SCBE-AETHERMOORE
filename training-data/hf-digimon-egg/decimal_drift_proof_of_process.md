# Decimal Drift as Proof of Process

Decimal Drift acts as a forensic instrument in the 14-layer SCBE pipeline.

## Core Idea
- IEEE754 rounding artifacts are treated as provenance signal, not discarded noise.
- Legitimate data accumulates a deterministic micro-error narrative across mandatory layers.
- Synthetic/offline forged data fails to match that accumulated drift fingerprint.

## Layered Interferometry
- L3 weighted transform introduces multiplication rounding signatures.
- L4 Poincare projection reshapes precision distribution via tanh.
- L7 phase transform (Mobius/rotation ops) adds complex arithmetic drift.

## Detection Modes
- Synthetic/no-pipeline inputs: drift magnitude mismatch.
- Anomalous scale attacks: incompatible drift growth profile.
- Rounded/truncated payloads: fractional-entropy collapse alerts.

## Governance Rule
Data must be both value-correct and process-valid.

Decimal Drift therefore provides Proof of Process, enabling the pipeline to enforce computational provenance rather than only output correctness.
