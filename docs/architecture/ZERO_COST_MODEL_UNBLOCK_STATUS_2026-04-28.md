# Zero-Cost Model Unblock Status - 2026-04-28

## Decision

The SCBE-owned model lane stays zero-dollar by default. Local training remains the preferred path, but the current Windows environment is blocked by Python/Torch dependency readiness, so the active fallback is free Colab GPU execution rather than paid Hugging Face Jobs.

## Current Local Blocker

- Local launcher sees an NVIDIA GTX 1660 Ti Max-Q with 6144 MB VRAM.
- The active local Python is 3.14, while the local training stack still needs a Torch-compatible Python environment.
- The Python launcher lists stale 3.12 entries, but the referenced 3.12 executables are missing.
- `torch` and `unsloth` are not available locally, so the zero-cost preflight correctly emits a script and blocks cloud dispatch.

## Added Fallback

The free Colab notebook is:

`notebooks/scbe_zero_cost_local_0p5b_colab.ipynb`

Catalog alias:

```powershell
python scripts/system/colab_workflow_catalog.py url zero-cost
```

The notebook:

- clones the active `chore/repo-launch-restructure` branch,
- loads `config/model_training/scbe-zero-cost-local-0.5b.json`,
- trains a Qwen2.5-Coder-0.5B LoRA adapter from the consolidated SCBE regularized buckets,
- saves metrics and adapter files under `/content/scbe-zero-cost-local-0.5b-lora`,
- creates `/content/scbe-zero-cost-local-0.5b-lora.zip`,
- leaves Hugging Face upload disabled unless explicitly enabled.

## Operating Rule

Use this order:

1. Run local preflight.
2. If local Torch is unavailable, use the free Colab notebook.
3. Download or Drive-copy the adapter zip.
4. Import the adapter back into the local model store.
5. Do not use paid Hugging Face Jobs unless explicitly authorized.
