# Model Artifact Consolidation Status - 2026-04-28

## Purpose

Consolidate local model artifacts without deleting daily tools, uninstalling applications, or moving canonical project files.

## Action Taken

Added a hardlink-based model artifact consolidator:

- `scripts/system/consolidate_model_artifacts.py`
- `tests/system/test_consolidate_model_artifacts.py`

The consolidator scans only model artifact extensions:

- `.safetensors`
- `.bin`
- `.gguf`
- `.pt`
- `.pth`
- `.ckpt`
- `.onnx`
- `.model`

Default roots:

- `models/`
- `artifacts/`
- `training/runs/`

It skips `.git`, `node_modules`, Python caches, and pytest caches.

## Result

Initial dry run:

- scanned model artifact files: 89
- duplicate groups: 12
- planned reclaimable duplicate bytes: 493,562,003
- planned reclaimable duplicate size: about 470.7 MB

Apply run:

- hardlinked files: 14
- hardlinked bytes: 493,562,003
- original paths preserved: yes
- unique model files deleted: no

Idempotency check:

- rerunning with `--apply` reports duplicate paths as `already_linked`
- no additional files are modified on the second run

Hardlink verification examples:

- `artifacts/tongue-table-lora-v2-weighted/lora_final_probe/optimizer.pt`
  and `artifacts/tongue-table-lora-v2-weighted-rerun/checkpoint-50/optimizer.pt`
  now share the same hardlinked storage.
- `models/hf/scbe-pivot-qwen-0.5b/adapter_model.safetensors`
  and `models/hf/scbe-pivot-qwen-0.5b/checkpoint-150/adapter_model.safetensors`
  now share the same hardlinked storage.

## What Was Not Touched

- Ollama model store was not modified.
- Hugging Face cache was not modified.
- Chrome Remote Desktop was not modified.
- Claude/Codex/tooling installs were not modified.
- Personal documents, tax files, and project source files were not deleted.
- Unique model artifacts were not removed.

## Command

```powershell
python scripts/system/consolidate_model_artifacts.py --min-mb 1 --apply
```

## Rule Going Forward

Use hardlink consolidation for exact duplicate generated model artifacts first. Do not delete or move model roots unless the model is verified offloaded and not used by daily tools.

