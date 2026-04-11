# Memory Overlay Eval Set

This eval lane is for the smallest useful MemPalace + SCBE benchmark:

- verbatim memory retrieval first
- SCBE semantic-token rerank second
- hand-labeled path targets

Each row in `memory_overlay_seed.jsonl` should contain:

```json
{
  "id": "memory-overlay-001",
  "query": "Natural-language retrieval prompt",
  "expected_paths": ["repo-relative/path/to/the/right/file.md"],
  "type": "note|code|historical|reference|generic",
  "notes": "Why this file is the correct target"
}
```

Use repo-relative `expected_paths` values. The benchmark script normalizes them
to absolute paths internally. `expected_path` is still accepted for backward
compatibility, but new eval rows should use `expected_paths`.

Benchmark modes:

- `baseline`: TF-IDF over the verbatim memory substrate
- `mempalace_style`: baseline + deterministic filename/path/title/phrase rerank
- `overlay`: mempalace-style rerank + SCBE semantic/tongue/rhombic sidecars

Run:

```powershell
python scripts/system/memory_overlay_benchmark.py
```

Override the corpus roots if you want to benchmark a different slice:

```powershell
python scripts/system/memory_overlay_benchmark.py `
  --corpus-root "notes/System Library/Indexes" `
  --corpus-root "docs/01-architecture" `
  --corpus-root "python/scbe"
```
