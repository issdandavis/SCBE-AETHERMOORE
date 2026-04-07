# Governance Gate Prediction Benchmark

This is the first local benchmark lane for `AetherMoore` governance work. It does not replace the live Omega lock. It creates a safe, reproducible proxy task around the existing `/governance-check` contract so we can benchmark surrogate models before pushing anything public.

## Goal

Predict:

- `decision ∈ {ALLOW, QUARANTINE, DENY}`
- `risk_prime`

from the same deterministic inputs and intermediate traces already used by the live governance-check path.

## Source of truth

The benchmark mirrors the current implementation in:

- [src/api/main.py](C:\Users\issda\SCBE-AETHERMOORE\src\api\main.py)
- [src/scbe_14layer_reference.py](C:\Users\issda\SCBE-AETHERMOORE\src\scbe_14layer_reference.py)

It reuses:

- synthetic 6D position from `sha256(agent:topic)`
- context-aware weight tables for `internal`, `external`, and `untrusted`
- `scbe_14layer_pipeline(...)` outputs for labels and traces

## Local artifact shape

Each JSONL row contains:

- `id`, `split`, `group_id`, `source`
- `inputs.context`
- `inputs.agent_hash`, `inputs.topic_hash`
- `inputs.position`
- `inputs.harmonic_factor`, `inputs.d_star`, `inputs.d_tri_norm`
- `inputs.coherence_metrics`
- `inputs.geometry`
- `labels.decision`
- `labels.risk_score`
- `labels.risk_prime`

Explicitly excluded:

- plaintext
- sealed blobs
- retrieval payloads

## Split policy

Splits are grouped by `group_id = sha256(agent|topic)[:16]`.

That means all context variants for one agent/topic pair stay in the same split, which prevents leakage between train and eval.

## First baseline

The local runner ships a trivial `context_prior` baseline:

- learns decision distribution per context from train split
- learns mean `risk_prime` per context from train split
- predicts by context only

This is intentionally weak. It gives us a stable floor before adding real surrogate models.

## Local command

```powershell
python scripts/research/build_governance_gate_prediction_benchmark.py
```

Artifacts land in:

- `artifacts/benchmark/governance_gate_prediction/dataset/`
- `artifacts/benchmark/governance_gate_prediction/baseline_context_prior/`
- `artifacts/benchmark/governance_gate_prediction/benchmark_summary.json`

## Why this lane comes first

This is the cheapest and safest public-benchmark candidate because:

- labels are self-generated from the live governance logic
- no plaintext or sealed state has to be released
- it tests governance support, not governance replacement
