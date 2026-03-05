# Graphics Feedback

Use this folder for visual-quality feedback rows (what looks bad, what to improve).

Recommended JSONL shape:

```json
{"instruction":"Improve game visual quality while preserving performance", "input":"Current issue: sprites look flat and noisy", "output":"Use 3-value palette ramps, stronger silhouettes, and per-biome color keys.", "source":"graphics_feedback", "tongue":"AV"}
```

or chat format:

```json
{"messages":[{"role":"system","content":"You are a game art director."},{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}
```

These rows train AV/DR quality behavior in the HYDRA configuration.

