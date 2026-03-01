# OctoArmor — Hugging Face Connector Notes

## What was added

- `src/fleet/octo_armor.py`
  - `Tentacle.HUGGINGFACE` now uses chat-compatible Hugging Face endpoint first (`.../v1/chat/completions`) and falls back to legacy inference endpoint.
  - Provider API keys are resolved via local secret store (`src.security.secret_store.pick_secret`) with env-var fallback.
  - Cloudflare account lookups also use local secret store fallback.

- `src/fleet/training_flywheel.py`
  - Added as the dedicated module path for `TrainingFlywheel` import expectations.
- `src/fleet/__init__.py`
  - Re-export path updated to import `TrainingFlywheel` from `src.fleet.training_flywheel`.

## Hugging Face expectations

- Set secrets in local store when possible (e.g. `HF_TOKEN`, `HUGGINGFACE_TOKEN`).
- If no local secret is found, runtime env still works as fallback.
- `tentacle_dashboard()` and `list_free_models()` still report Hugging Face as an available free tier provider.

## Where to find implementation

- Core provider hub: `src/fleet/octo_armor.py`
- Flywheel entry point: `src/fleet/training_flywheel.py`
- Public exports: `src/fleet/__init__.py`

