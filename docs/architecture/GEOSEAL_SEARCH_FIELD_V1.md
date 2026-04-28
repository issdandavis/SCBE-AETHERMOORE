# GeoSeal Search Field v1

GeoSeal search is treated as a deterministic control surface for agent-bus exploration.

The first implementation lives in `src/ai_orchestration/search_field.py` and emits a compact trace:

```json
{
  "candidate_id": "cand-1",
  "projection": {
    "transform_class": 3,
    "symmetry": 1,
    "intent": 5
  },
  "grade": [3, 2, 4],
  "residue": 12,
  "theta_degrees": 38.25,
  "score": 0.82,
  "decision": "ALLOW"
}
```

## Parameter Groups

- Projection: dimensions that define the unstable search slice.
- Modulus: residue buckets for each projected dimension.
- Grading: discrete gemstone-style axes.
- Phase: weighted residue to damped rotation.
- Constraints: entropy, agreement, harmonic, and iteration gates.
- Consensus: quorum, agreement threshold, and max iterations.

## Coupling Rules

The policy adaptation rule is intentionally small:

- high entropy lowers damping
- low agreement raises phase scale
- high stability lowers phase scale

This keeps exploration from oscillating without adding a large hyperparameter surface.

## Verification

Focused test:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest tests/test_geoseal_search_field.py -q
```

Expected result at implementation time:

`5 passed`
