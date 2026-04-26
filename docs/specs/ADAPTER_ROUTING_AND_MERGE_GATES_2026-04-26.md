# Adapter Routing and Merge Gates

Date: 2026-04-26

## Position

Do not merge coding adapters by default. Route first, merge only after executable gates and LoRA drift analysis show that a merge will not erase lane-specific behavior.

The current merge profile supports weighted PEFT merging, but that is a final packaging step, not a training-success proof. At the current 0.5B base scale, disjoint coding lanes should stay independently addressable until routing latency becomes a real blocker.

## Commands

Build the adapter registry:

```powershell
npm run training:adapter-registry
```

Analyze local LoRA drift:

```powershell
npm run training:lora-drift
```

Plan a merge packet without dispatch:

```powershell
python scripts\system\dispatch_coding_model_merge_hf_job.py plan
```

Dispatch is intentionally blocked when `pre_merge_gates` are declared unless `--force` is supplied:

```powershell
python scripts\system\dispatch_coding_model_merge_hf_job.py dispatch
```

## Current Evidence

Registry:

- `artifacts/adapter_registry/registry.json`
- `artifacts/adapter_registry/registry.md`

Latest drift report:

- `artifacts/adapter_registry/drift/latest/drift_report.json`
- `artifacts/adapter_registry/drift/latest/drift_report.md`

Observed local drift result:

- `coding-approval-metrics-v1` versus `geoseal-stage6-repair-v7` has near-zero cosine and about 50% sign conflict.
- That is a route-first signal, not a linear-merge signal.
- Two adjacent geoseal checkpoints are effectively identical and are safe as checkpoint alternatives, not separate lane parents.

## Promotion Rule

An adapter can route when:

- Its registry entry exists.
- Its local or remote repo is traceable.
- Its task lane is explicit.
- It has a frozen eval or executable benchmark report.

An adapter can enter a merge profile only when:

- Solo executable accuracy is at least 95% of its own accepted baseline.
- Stage 6 regression guard passes.
- Functional coding benchmark passes the configured gate.
- Drift analysis returns `linear_candidate`, `ties_candidate`, or `dare_ties_candidate`.
- The model card includes lineage: base model, parent adapters, weights, reports, and drift report.

If drift returns `route_only_conflict_high` or `route_only_insufficient_overlap`, do not merge. Route the adapter by prompt/task lane instead.
