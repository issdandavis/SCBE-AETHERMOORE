---
name: scbe-experimental-research-safe-integration
description: Design and execute advanced experimental research with fail-closed safety integration for SCBE systems. Use when users ask to test novel kernels/manifolds, map proposals into the 21D/M4 state layout, add semantic mesh overlays (including 230-bit envelopes), or move experimental results toward production safely.
---

# SCBE Experimental Research + Safe Integration

## Operating Contract

1. Preserve canonical SCBE terms and spelling.
2. Preserve canonical wall formula `H(d*,R) = R · pi^(phi · d*)` unless explicitly overridden.
3. Treat new formulas and kernels as untrusted until dimensional and behavior checks pass.
4. Default to fail-closed decisions (`DENY` or `QUARANTINE`) when evidence is incomplete.
5. Keep experiment and production paths separate until all gates pass.
6. Emit both `StateVector` and `DecisionRecord` for every meaningful step.

## Workflow

1. Frame the experiment:
   - Write hypothesis, expected gain, and explicit failure modes.
   - Define measurable metrics and pass/fail thresholds before running.
2. Establish baseline:
   - Capture current production-equivalent metrics and artifact hashes.
   - Require reproducible replay seeds.
3. Map the proposal into 21D:
   - `1-3` SCBE context/trust
   - `4-6` Dual-Lattice perpendicular space
   - `7-9` PHDM cognitive position
   - `10-12` Sacred Tongues phase encoding
   - `13-15` M4 model manifold position (`model_x`, `model_y`, `model_z`)
   - `16-18` Swarm composite state
   - `19-21` HYDRA ordering/meta
4. Add tri/quaternary kernel overlays:
   - Use K-ary simplex state `p_t ∈ Δ^(K-1)` with `K=3` or `K=4`.
   - Track multi-timescale channels: `T_micro`, `T_task`, `T_stage`, `T_life`.
   - Track causal inputs: `I` (intent), `P` (pressure), `D` (depth), `q=Time/Intent`.
5. Apply 230-bit semantic mesh overlay exoskeleton:
   - Treat this as governance metadata packing, not standalone confidentiality.
   - Pack 230 bits with deterministic schema:
     - `84 bits`: 21D signed quantized state (`21 x 4 bits`)
     - `18 bits`: Sacred Tongues semantic phase block
     - `24 bits`: time channels (`T_micro/T_task/T_stage/T_life`)
     - `24 bits`: intent kernel block (`I/P/D/q`)
     - `24 bits`: M4 model block (`x/y/z`)
     - `16 bits`: gate flags and rollout state
     - `32 bits`: integrity digest prefix
     - `8 bits`: epoch/nonce shard
   - If confidentiality/integrity is required, wrap this overlay in approved crypto (for example SCBE/PQC + AEAD).
6. Run safe integration gates:
   - `G0` Spec gate: dimensions, invariants, and thresholds defined.
   - `G1` Unit gate: deterministic tests green.
   - `G2` Adversarial gate: red-team pass rate meets threshold.
   - `G3` Staged rollout gate: pilot SLOs hold.
   - `G4` Promotion gate: rollback verified and audit complete.
7. Promote or block:
   - Promote only when all gates pass.
   - Otherwise output `QUARANTINE` or `DENY` with explicit blockers.

## Required Output Contract

Every substantial run must return:

- `files_changed`: exact paths
- `state_vector`: 21D + kernel overlays
- `decision_record`: action, reason, confidence, timestamp, signature
- `gate_report`: per-gate pass/fail with evidence
- `rollback_plan`: checkpoint reference and reversal steps

Also finish with tri-fold YAML:

```yaml
action_summary:
  build:
    status: completed|partial|blocked
    artifacts: []
  document:
    status: completed|partial|blocked
    artifacts: []
  route:
    status: completed|partial|blocked
    next_hop: ""
```

## Resources

- Read `references/research-notes.md` for the external research baseline.
- Read `references/safe-integration-gates.yaml` for gate defaults.
- Use `scripts/evaluate_experiment_gate.py` for deterministic gate scoring.
