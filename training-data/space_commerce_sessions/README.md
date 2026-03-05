# Space Commerce Sessions

Drop JSONL records here for spaceship economy and trade behavior.

Recommended JSONL shape:

```json
{"instruction":"...", "input":"...", "output":"...", "source":"space_commerce_sessions", "tongue":"KO"}
```

or chat format:

```json
{"messages":[{"role":"system","content":"..."},{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}
```

This folder is consumed by:
- `scripts/system/polly_cross_model_bootstrap.py`
- `training/vertex_hydra_trainer.py` (via category matching)

