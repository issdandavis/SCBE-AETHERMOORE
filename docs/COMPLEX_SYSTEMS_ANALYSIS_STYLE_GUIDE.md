# Complex Systems Analysis Style Guide

Last updated: February 19, 2026
Scope: SCBE-AETHERMOORE math, governance, and cross-layer claims

## Purpose
This guide defines how to analyze complex SCBE subsystems without drift, hype, or formula mixing.
It is code-first and evidence-first.

## Current Math Comparison

### Formula Families Found in Repo
1. `H_score(d, pd) = 1 / (1 + d + 2*pd)`  
   Source: `packages/kernel/src/harmonicScaling.ts`  
   Behavior: bounded score in `(0,1]`, ranking-preserving in moderate ranges.

2. `H_wall_exp(d) = exp(d^2)`  
   Source: `harmonic_scaling_law.py`  
   Behavior: super-exponential wall with identity `H(0)=1`.

3. `H_wall_R(d, R) = R^(d^2)`  
   Source: `src/symphonic_cipher/core/harmonic_scaling_law.py`  
   Behavior: super-exponential wall with tunable base `R > 1`.

4. `H_patrol(d, R) = R * pi^(phi*d)`  
   Source: prior templates and skill constants  
   Behavior: exponential patrol profile with non-identity baseline `H(0)=R`.

### Sensitivity Comparison (Wall vs Patrol)
For relative sensitivity, use derivatives of `log(H)`:
- `d/d d log(H_wall_R) = 2*d*ln(R)`
- `d/d d log(H_patrol) = phi*ln(pi)` (constant)

Equal-sensitivity crossover:
- `d_cross = phi*ln(pi) / (2*ln(R))`
- If `R=e`: `d_cross ~= 0.9261`
- If `R=1.5`: `d_cross ~= 2.2841`

Interpretation:
- Below `d_cross`, patrol is more sensitive.
- Above `d_cross`, wall is more sensitive.

## Opinion (Technical)
1. The system should not force one universal harmonic formula.
2. The formulas are different tools for different regimes:
   - Wall formulas (`exp(d^2)` or `R^(d^2)`) fit enforcement and hard escalation.
   - Patrol formula (`R*pi^(phi*d)`) fits drift monitoring and early warning.
   - Bounded score formula fits stable ranking and decision plumbing.
3. Claims must always declare which formula family and regime are being used.

## Analysis Protocol (Codex)

1. Read executable surface first.
   - Prefer implementation files over narrative docs.

2. Extract the math spine.
   - Write each formula, domain, codomain, and identity element.

3. Run behavior checks.
   - Identity at origin.
   - Monotonicity.
   - Boundedness.
   - Asymptotic growth class.
   - Relative sensitivity (`d/dx log(H)`).

4. Compare against baselines.
   - Same dataset, same seeds, same harness.
   - Record AUC/F1/latency with confidence intervals.

5. Classify claim scope.
   - `security primitive`, `governance score`, `telemetry feature`, or `narrative`.

6. Publish decision with evidence.
   - Status tag + artifact path + limitation.

## Red Flags
- Formula appears in docs but not code.
- Same symbol `H` used for different formulas without regime tags.
- Universal words (`always`, `impossible`) without proof scope.
- Metrics reported without dataset and seed.
- Layer numbering or canonical definitions changing between docs.

## Required Output Contract for Reviews
Every substantial review should end with:
- `StateVector`: deterministic state summary.
- `DecisionRecord`: action, reason, confidence, timestamp.

And tri-fold YAML:
- `build`
- `document`
- `route`

## Regime Tags (Required in Docs)
- `[WALL_ENFORCEMENT]`
- `[PATROL_MONITORING]`
- `[BOUNDED_SCORING]`
- `[EXPERIMENTAL]`

## Quick Template
Use this block for each major formula claim:

```md
Formula: <expression>
Regime: [WALL_ENFORCEMENT|PATROL_MONITORING|BOUNDED_SCORING|EXPERIMENTAL]
Identity: <value at origin>
Sensitivity: <d/dx log(H)>
Evidence: <artifact path>
Status: [PROVEN|DISPROVEN|CODE_EXISTS_UNTESTED|REPORTED_PENDING_REPRO]
Limitation: <explicit scope boundary>
```
