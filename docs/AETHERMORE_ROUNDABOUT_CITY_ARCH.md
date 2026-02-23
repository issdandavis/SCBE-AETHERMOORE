# AetherMore Roundabout City Architecture

## Intent
Build SCBE-AETHERMOORE as a non-linear, autonomous routing city instead of a single linear pipeline.

## City Map (System -> Utility)
- `Water` -> Data streams (events, logs, datasets)
- `Electric` -> Compute scheduling (CPU/GPU budgets)
- `Gas` -> Burst acceleration lanes (batch training/inference)
- `Roads` -> Task routing between services/agents
- `Rail` -> High-throughput batch movement (nightly backfills)
- `Emergency` -> Quarantine/deny/kill-switch paths

## Districts
1. `Ingress District` (capture + normalize)
- Inputs: agent events, browser traces, telemetry, human prompts.
- Output contract: `StateVector` only.

2. `Identity District` (attestation + binding)
- Sacred Tongues binding, envelope parse, signer checks.
- Output contract: `DecisionRecord` pre-check.

3. `Governance District` (SCBE 14-layer gates)
- L1-4 context embedding -> L5 metric -> L6-11 coherence -> L12 harmonic scaling -> L13 decision -> L14 audio axis.
- Output contract: `ALLOW|QUARANTINE|DENY` + reason.

4. `Execution District` (agent actions)
- Browser/API/terminal actions execute only from governed tickets.
- Writes immutable audit edges for every action.

5. `Learning District` (training flywheel)
- Curate logs -> redact -> label -> publish dataset snapshots -> train -> evaluate -> promote.
- No direct write-back to production policy without a consensus gate.

## Roundabouts (Non-Linear Hubs)
Each roundabout is a decision hub with multiple exits, not a fixed chain.

- `R0 Intake Roundabout`
  exits: normalize, drop, quarantine.
- `R1 Trust Roundabout`
  exits: allow lane, shadow lane, human-review lane.
- `R2 Risk Roundabout`
  exits: execute, simulate-first, deny+noise.
- `R3 Learning Roundabout`
  exits: dataset candidate, retrain queue, discard.

## Core Control Rules
- Every inter-district handoff must include:
  - `StateVector`
  - `DecisionRecord`
- All high-risk exits require consensus (`3f+1` architecture target for Byzantine tolerance).
- Quarantine lanes are first-class paths, not error states.
- Human-in-the-loop is a lane, not a blocker.

## Data Plan for Hugging Face
Use org-managed repos by lane:
- `datasets/raw-events` (append-only)
- `datasets/curated-training` (redacted/labeled)
- `datasets/redteam-cases` (attacks/failures)
- `models/phdm-21d-embedding` (embedding model + eval cards)
- `models/spiralverse-ai-federated-v1` (policy/coordination model)
- `spaces/aethermore-observatory` (light dashboard)

## 7-Day Bring-Up
1. Create org + roles.
2. Bootstrap repos by lane.
3. Wire upload jobs from `scbe-interaction-logs` to `raw-events`.
4. Add redaction + schema checks before `curated-training`.
5. Add nightly eval and promotion gate.
6. Add rollback lane (last known good model/dataset tag).
7. Add weekly drift review using decimal drift + temporal coherence metrics.

## First Success Criteria
- One end-to-end loop runs without manual edits:
  `logs -> curated dataset -> train -> eval -> gated promote`.
- Failed actions route to quarantine lanes with full audit context.
- Human review lane can approve/reject without stopping the rest of the city.
