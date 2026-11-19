---
schema: clay.training-context-packet.v1
campaign_id: "clay-hybrid-input-access-efficacy-20261119"
status: "PREFLIGHT"
updated_at: "2026-11-19T16:02:00Z"
source_sha256: 7a7d1155951359f4fef2cf1795daf5dee2d7ceae72dadbca3b31989aa53d0c74
---

# Training context: clay-hybrid-input-access-efficacy-20261119

Measure a parameter-matched hybrid downstream-plus-raw-input action learner against downstream-only and immutable baselines.

## Workspace

```json
{
  "dirty": true,
  "path": "C:/dev/_wt_clay_stable_ce_audit_20261119",
  "revision": "20e9d8f498c468f327ff38050e13094be674d973"
}
```

## Parent

```json
{
  "path": "C:/dev/_kaggle_stage/clay-input-access-efficacy-20261119-v3/neutral-suffix-runtime-3c12/baseline_run",
  "sha256": "c5261ada862a2851db0b1dd7e53835b5ddef22299660921527a249a866361482",
  "step": 0
}
```

## Data

```json
{
  "manifest": "7460665cbb718097438227c452f1915e88bdc5a10ac643122b17908b505d0041",
  "receipt_sha256": "7f2516af8ae5a122f357565afad60ab412fdf54e76a3018cd8f1ddbfdb702a97",
  "splits": "Pinned multiview train plus source-disjoint 1500-row holdout per seed"
}
```

## Experiment

```json
{
  "arms": [
    "no_intervention_adapter",
    "downstream_only",
    "hybrid_input_access"
  ],
  "preregistration": "docs/research/CLAY_HYBRID_INPUT_ACCESS_PREREGISTRATION_20261119.json",
  "seeds": [
    20261134,
    20261135,
    20261136
  ]
}
```

## Active job

```json
{
  "id": "issacizrealdavis/clay-hybrid-input-access-efficacy-20261119",
  "provider": "Kaggle private offline CPU",
  "status": "NOT_UPLOADED_NOT_RUN_BREAKER_PENDING"
}
```

## Artifacts

```json
[
  {
    "path": "C:/dev/_kaggle_stage/clay-hybrid-input-access-efficacy-20261119-v1/dataset/clay-hybrid-input-access-efficacy.packet",
    "role": "packet",
    "sha256": "69c0da6049c5e79743ffa78a80ed30f913727af748e46b05adee399befd09fc8"
  },
  {
    "path": "experiments/clay_hybrid_input_access_efficacy_20261119/LOCAL_PREFLIGHT_RECEIPT.json",
    "role": "preflight",
    "sha256": "e3961b250d94ebcd9fa4926ed81ffb8d147fd34040bfc96928c8a489bd7d3c21"
  }
]
```

## Invariants

- Both trained arms expose exactly 140820 effective reachable scalars.
- Candidate and matched-control logits are bit-identical at initialization.
- Training scratch launch requires 26 GiB and keeps a hard 25 GiB runtime floor.
- Durable output has an independent 1 GiB copy guard and exact recovery inventory.
- Private, offline, CPU-only; no upload or run before independent breaker pass.
- No weight promotion without both controls, both metrics, finite gates, retention, and replay.

## Decisions

```json
[
  {
    "claim": "Actual packet data yields compact alphabet 269 and exact 140820/140820 reach/change parity for both arms across all seeds.",
    "evidence": "experiments/clay_hybrid_input_access_efficacy_20261119/LOCAL_PREFLIGHT_RECEIPT.json",
    "state": "MEASURED"
  }
]
```

## Next actions

- MainLane independently audits exact packet bytes and mutation surfaces.
- Only after LAUNCH_GATE_PASS may the private dataset/kernel be uploaded and run.
- After completion, download raw output, replay all six models, and evaluate preregistered gates.

## Conditional chapters

- campaign-packet
- experiment-evidence
- overnight-and-post-training

## Packet receipt

- Source schema: `clay.training-context-source.v1`
- Canonical source SHA-256: `7a7d1155951359f4fef2cf1795daf5dee2d7ceae72dadbca3b31989aa53d0c74`
- This packet is an operational index. Linked evidence remains authoritative.
