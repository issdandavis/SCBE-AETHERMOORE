# Multi-Model Modal Matrix

Status: EXPERIMENTAL
Last updated: February 19, 2026

## Purpose
Extend single-model multimodal processing to a matrix over multiple models and modalities.

## Formal object
For `N` models and `K` modalities, define matrix `M` where each cell is:

`cell_{i,j} = (prediction, confidence, latency_ms, drift, risk)`

- `i`: model index
- `j`: modality index

## Derived signals
- Per-modality agreement:
  - agreement across models within each modality.
- Per-model reliability:
  - rolling reliability score per model across modalities.
- Cross-model drift:
  - divergence of model outputs over time.
- Conflict mass:
  - weighted disagreement aggregate used as penalty term.

## Reducer
Reliability-weighted vote with disagreement penalty:

1. Compute weighted support for each decision class.
2. Apply conflict penalty from conflict mass and drift.
3. Emit final decision: `ALLOW | QUARANTINE | DENY`.

## Integration with SCBE
- Layer 12 input: reducer score and conflict penalty feed harmonic policy scoring.
- Layer 13 input: reducer class and confidence feed final decision gate.
- Audit: persist per-cell metrics and reducer trace for replay.

## Minimal API sketch

```text
ingest(model_id, modality_id, prediction, confidence, latency_ms, drift, risk)
derive_signals() -> {agreement, reliability, cross_model_drift, conflict_mass}
reduce() -> {decision, confidence, rationale}
```

## Three-phase implementation

### Phase 1: Data model and reducer
- implement matrix schema and reducer in one module.
- emit deterministic JSON traces.

### Phase 2: SCBE wiring
- pass reducer outputs into L12/L13 adapters.
- add replay tests and failure slices.

### Phase 3: benchmark and promotion
- run Q3-6 experiment against single-model multimodal baseline.
- publish reproducible artifact bundle.

## Experiment design (Q3-6)
- Baseline: single-model multimodal scaffold.
- Candidate: multi-model modal matrix reducer.
- Metrics: AUC, F1, latency, and calibration error.
- Pass criteria: statistically significant decision-quality lift with bounded latency overhead.
