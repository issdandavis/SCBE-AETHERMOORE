# Storage Cleanup - 2026-05-02

Purpose: reclaim local disk space without deleting source code, personal tax/business docs, or active repo files.

## Before

- C: free space was about 11.1 GB.
- SCBE-AETHERMOORE was about 18.4 GB.
- Largest repo local/generated roots were artifacts (about 7.9 GB), .venv-training (about 4.8 GB), and .git (about 2.3 GB).

## Actions Taken

- Saved .venv-training package list before cleanup; detailed copy is stored in private repo
  `issdandavis/SCBE-private` at `ops/storage-ledgers/2026-05-02/`.
- Saved artifact inventory before deleting generated artifact directories; detailed copy is stored in private repo
  `issdandavis/SCBE-private` at `ops/storage-ledgers/2026-05-02/`.
- Removed regenerable training virtual environment: `.venv-training/`.
- Removed cache roots:
  - `C:\SCBE_CACHE\hf`
  - `C:\SCBE_CACHE\npm`
  - `C:\SCBE_CACHE\pip`
  - `C:\Users\issda\.cache\huggingface`
  - `C:\Users\issda\.cache\puppeteer`
  - `C:\Users\issda\.cache\pre-commit`
  - contents of `C:\Users\issda\AppData\Local\Temp`
- Removed generated/local artifact directories:
  - `artifacts/kaggle_output`
  - `artifacts/kaggle_outputs`
  - `artifacts/browser_profiles`
  - `artifacts/merged_models`
  - `artifacts/merged`
  - `artifacts/training`
  - `artifacts/tongue-table-lora-*`
- Ran `git gc --prune=now` to compact local Git objects.
- Ran npm/pip cache cleanup commands.

## After

- C: free space is about 28.5 GB.
- SCBE-AETHERMOORE is about 6.2 GB.
- Caches under `C:\SCBE_CACHE`, `C:\Users\issda\.cache`, and `AppData\Local\Temp` are near zero.

## Not Touched

- Source code folders.
- Personal/tax/business document folders.
- OneDrive files.
- Dropbox selective-sync conflict folders.
- `.ollama/models` style local model payloads.

## Remaining Large Areas

- `C:\Users\issda\OneDrive`: about 26.6 GB.
- `C:\Users\issda\Dropbox`: about 15.4 GB, including multiple `SCBE (Selective Sync Conflict *)` folders.
- `C:\Python314`: about 1.5 GB.
- `C:\Users\issda\.ollama`: about 0.6 GB.

Dropbox conflict folders are likely a major target, but they should be handled with sync-aware verification because deleting local Dropbox content can propagate deletion to cloud.
