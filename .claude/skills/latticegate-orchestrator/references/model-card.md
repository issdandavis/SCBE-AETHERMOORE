# Embedding Model Card

## Current Configuration

```
EMBEDDING_MODEL_ID : <not yet selected>
EMBEDDING_DIM      : <pending>
POINCARE_DIM       : 21
STATUS             : NOT CONFIGURED
```

## Candidates

| Model | Dim | Speed | Quality | Notes |
|-------|-----|-------|---------|-------|
| `BAAI/bge-small-en-v1.5` | 384 | Fast | Strong retrieval | Lightweight, projectable to H^21 |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Very fast | Good general | Common baseline |
| `issdandavis/phdm-21d-embedding` | 21 | Native | SCBE-native | No projection needed (if available) |

## Selection Criteria

1. Must be publicly available on HuggingFace
2. Must produce deterministic embeddings (no sampling)
3. Must support batch inference for calibration corpus (200+ prompts)
4. Projection to H^21 must preserve relative distances (verify with parity test)

## Projection Method

Euclidean R^D -> Poincare Ball H^21:
```
x_H = tanh(||v|| / (2*sqrt(D))) * v / ||v||
```

If D > 21: apply PCA to reduce to 21 dimensions first, then project.
If D = 21: project directly (no reduction needed).
If D < 21: zero-pad to 21 dimensions, then project.

## Benchmark Scores

Document retrieval and semantic similarity benchmarks here
after model selection and before client delivery.

```
MODEL              : <id>
MTEB_SCORE         : <value>
STS_BENCHMARK      : <value>
PROJECTION_PARITY  : <pass/fail>
SELECTION_DATE     : <ISO date>
SELECTED_BY        : <name>
```
