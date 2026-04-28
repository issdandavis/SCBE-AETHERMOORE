# PC Storage Policy - 2026-04-28

This machine was filling from scattered AI/dev runtime caches, not primarily from project source.

## Current Preservation State

- Project checkpoint pushed to GitHub:
  `91d91198 chore: checkpoint project files before cleanup`
- Current branch:
  `chore/repo-launch-restructure`
- Do not delete source, proposal docs, `training-data`, or active model/source artifacts without a verified offsite copy.

## Cache Root

Future rebuildable caches are routed to:

`C:\SCBE_CACHE`

Configured user environment variables:

- `SCBE_CACHE_ROOT`
- `HF_HOME`
- `HUGGINGFACE_HUB_CACHE`
- `TRANSFORMERS_CACHE`
- `PIP_CACHE_DIR`
- `UV_CACHE_DIR`
- `PLAYWRIGHT_BROWSERS_PATH`
- `TORCH_HOME`
- `NPM_CONFIG_CACHE`
- `TEMP`
- `TMP`

Also configured:

- npm user cache: `C:\SCBE_CACHE\npm`
- pip user cache: `C:\SCBE_CACHE\pip`

## Cleanup Rule

When space gets tight, clear rebuildable cache lanes before touching project files:

1. `C:\SCBE_CACHE`
2. browser/runtime caches
3. crash dumps and logs
4. unused global tool caches
5. only then review generated project artifacts with verified offsite copies

## Explicitly Preserved

- Chrome Remote Desktop
- Git, Node, PowerShell, VS Code, Cursor, Obsidian
- Proton, OneDrive, Dropbox
- Ollama program/model assets
- project source/docs/proposal/training data
- tax or personal document paths
