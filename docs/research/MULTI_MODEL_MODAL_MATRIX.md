# Multi-Model Modal Matrix (Experimental)

> **Status:** EXPERIMENTAL -- not authoritative spec.
> **Depends on:** [MULTIMODAL_MATRIX_TRAINING.md](MULTIMODAL_MATRIX_TRAINING.md), `experimental/multimodal/multimodal_matrix.py`
> **Claims Ledger:** CODE_EXISTS_UNTESTED (see [EXPERIMENT_QUEUE.md](../EXPERIMENT_QUEUE.md) Q3-6, Q4-3)

---

## Motivation

The existing `multimodal_matrix.py` scaffold handles **one model, M modalities**. The alignment matrix `A[B, M, M]` measures pairwise modality agreement within a single model.

This spec extends to **N models x M modalities**, where each model independently produces predictions and the system votes across models to produce a governance decision. The core idea: model disagreement is a signal. If 3 of 4 models agree on ALLOW but one flags DENY, that disagreement carries information that a single-model system cannot capture.

---

## Architecture

### Cell Structure

Each cell in the matrix represents one model's output for one modality:

```
Cell(i, j) = {
    prediction: float,        # model i's output for modality j
    confidence: float,        # model i's self-reported confidence [0,1]
    latency_ms: float,        # wall-clock time for this inference
    drift: float,             # deviation from model i's baseline for modality j
    risk: float               # model i's risk score for this input
}
```

### Full Matrix

```
M[N, K] where:
  N = number of models (rows)
  K = number of modalities (columns)
  M[i,j] = Cell(i, j)
```

Example with N=3 models, K=3 modalities (text, image, state):

```
              | Text           | Image          | State          |
Model_A (GPT) | (0.82, 0.91, ...) | (0.75, 0.88, ...) | (0.90, 0.95, ...) |
Model_B (Claude) | (0.85, 0.93, ...) | (0.71, 0.82, ...) | (0.88, 0.91, ...) |
Model_C (Local) | (0.79, 0.87, ...) | (0.80, 0.90, ...) | (0.92, 0.97, ...) |
```

### Derived Signals

From the matrix, compute:

**Per-modality agreement** (column-wise):
```
agreement_j = 1 - std([M[i,j].prediction for i in 0..N]) / mean([...])
```
High agreement = models converge. Low agreement = modality is ambiguous or adversarial.

**Per-model reliability** (row-wise):
```
reliability_i = mean([M[i,j].confidence * (1 - M[i,j].drift) for j in 0..K])
```
High reliability = model is confident and stable. Low = model is drifting or uncertain.

**Cross-model drift** (off-diagonal):
```
cross_drift[i,k] = |M[i,:].drift - M[k,:].drift|_2
```
High cross-drift between two models = one may be compromised.

**Conflict mass** (analogous to existing `conflict_penalty`):
```
conflict = sum(relu(-agreement_j) for j in 0..K) / K
```

---

## Reducer: Matrix -> Governance Decision

The reducer collapses the N x K matrix into a single ALLOW / QUARANTINE / DENY decision.

### Step 1: Weighted Model Vote

Each model casts a vote weighted by its reliability:

```
vote_i = reliability_i * mean([M[i,j].risk for j in 0..K])
```

### Step 2: Aggregate Risk

```
risk_agg = sum(vote_i for i in 0..N) / sum(reliability_i for i in 0..N)
```

This is a reliability-weighted mean of per-model risk scores.

### Step 3: Disagreement Penalty

```
disagreement = std([mean(M[i,:].risk) for i in 0..N])
risk_final = risk_agg + lambda_disagree * disagreement
```

Model disagreement INCREASES risk. If models can't agree, the system errs toward caution.

### Step 4: Decision

```
if risk_final < theta_1:       ALLOW
elif risk_final < theta_2:     QUARANTINE
else:                          DENY
```

Default thresholds: theta_1 = 0.33, theta_2 = 0.67 (matching L13 in the 14-layer pipeline).

---

## Integration with Existing Code

### From `multimodal_matrix.py`

The existing `governance_proxy(A)` computes coherence, drift, conflict from the modality alignment matrix `A[B,M,M]`. The multi-model extension adds a second governance layer:

```
Level 1 (existing): governance_proxy(A_single_model)
  -> coherence, drift, conflict per modality pair

Level 2 (new): multi_model_reducer(M[N,K])
  -> agreement, reliability, cross_drift, conflict per model pair
  -> ALLOW / QUARANTINE / DENY
```

Level 2 wraps Level 1: each model independently produces its `governance_proxy` outputs, then the reducer aggregates across models.

### Wire to L13 Decision Gate

The `risk_final` from the reducer feeds directly into the existing L13 risk decision gate:

```
Risk' = risk_final / max(H_score, epsilon)
```

where `H_score` comes from the harmonic wall (L12). This preserves the superexponential cost property: even if the multi-model reducer produces a moderate risk score, the harmonic wall amplifies it if the models are operating far from the trusted center.

### Wire to SCBE Telemetry

New telemetry channels for the multi-model matrix:

| Channel | Source | Feed to |
|---------|--------|---------|
| `mm_agreement` | Per-modality agreement vector | L9 spectral coherence analog |
| `mm_reliability` | Per-model reliability vector | L10 spin coherence analog |
| `mm_cross_drift` | Cross-model drift matrix | L11 triadic temporal analog |
| `mm_conflict` | Conflict mass scalar | L13 risk gate input |

---

## Implementation Plan

### Phase 1: Data Structure (extend `multimodal_matrix.py`)

Add:
- `ModelCell` dataclass with (prediction, confidence, latency_ms, drift, risk)
- `MultiModelMatrix` class holding N x K grid of `ModelCell`
- `multi_model_reducer(matrix) -> (risk_final, decision, telemetry_dict)`

### Phase 2: Dummy Multi-Model Training

Extend `DummyMultimodalDataset` to simulate N models with configurable disagreement rates. Train the reducer weights (lambda_disagree, theta_1, theta_2) on synthetic adversarial scenarios.

### Phase 3: Governance Integration

Wire `multi_model_reducer` output into L13 decision gate. Add telemetry channels to existing `governance_proxy` interface.

---

## Experiment Design (see EXPERIMENT_QUEUE.md Q3-6)

**Hypothesis**: The multi-model reducer matches or exceeds single-model decisions on clean inputs and catches adversarial inputs that fool any single model.

**Setup**: 3 simulated models with independent noise. Inject adversarial inputs that fool 1 of 3 models.

**Pass criterion**: Reducer DENY rate on adversarial inputs >= 95%. Reducer ALLOW rate on clean inputs >= 95%. Reducer decision matches single-model consensus within 5% on clean inputs.

---

## Relationship to Patent Claims

This is a **research extension**, not a current patent claim. If experiments validate the hypothesis, it could become:

- A new dependent claim under Claim 1 (14-layer pipeline) describing multi-model aggregation in L13
- A new independent claim for the multi-model voting matrix as a governance mechanism

Current status in CLAIMS_EVIDENCE_LEDGER: not yet listed (add as CODE_EXISTS_UNTESTED after Phase 1 implementation).

---

*See [LANGUAGE_GUARDRAILS.md](../LANGUAGE_GUARDRAILS.md) for writing standards applied to this document.*
