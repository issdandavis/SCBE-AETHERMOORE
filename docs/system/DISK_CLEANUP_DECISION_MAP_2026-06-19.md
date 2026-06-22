# Disk Cleanup Decision Map - 2026-06-19

Read-only audit. Nothing in this map has been deleted.

## Current Drive

| Item | Size |
| --- | ---: |
| C: used | 211.95 GB |
| C: free | 25.21 GB |
| Shell elevated | no |

## Biggest Levers

| Rank | Path / Action | Size | Risk | Recommendation |
| ---: | --- | ---: | --- | --- |
| 1 | `C:\pagefile.sys` | 19.65 GB | admin/system | Shrink only from Administrator PowerShell. Best single win. |
| 2 | `C:\Users\issda\OneDrive` | 19.12 GB | user data | Review/move/offline before deleting. Biggest data area. |
| 3 | `C:\Users\issda\AppData\Local` | 13.30 GB | mixed app data | Clean targeted caches only; do not bulk delete. |
| 4 | `C:\hiberfil.sys` | 4.70 GB | admin/system | `powercfg /h off` if hibernate is not needed. |
| 5 | `C:\SCBE_CACHE` | 2.94 GB | re-downloadable cache | Good deletion candidate. |
| 6 | `C:\Users\issda\.ollama` | 2.72 GB | re-downloadable models | Remove unused model(s), keep active 1.5B if needed. |

## OneDrive Map

| Path | Size | Decision |
| --- | ---: | --- |
| `C:\Users\issda\OneDrive\SCBE-Archives` | 4.71 GB | Review. Likely archive/cold data, not blind delete. |
| `...\SCBE-Archives\repo_generated_2026-04-11` | 2.39 GB | Candidate if duplicated or obsolete generated output. |
| `...\SCBE-Archives\training_cold_2026-04-11` | 1.90 GB | Cold training data. Do not delete without explicit approval. |
| `C:\Users\issda\OneDrive\Offload` | 3.91 GB | Review/move local-only. |
| `...\Offload\CrossDevice` | 2.73 GB | Candidate for review. |
| `...\Offload\Zomboid` | 1.00 GB | Candidate if game/dev sync noise is unwanted. |
| `C:\Users\issda\OneDrive\Dropbox` | 3.10 GB | Review. |
| `...\Dropbox\Mobile Uploads` | 2.99 GB | Candidate if photos/videos are already backed up elsewhere. |
| `C:\Users\issda\OneDrive\Organized` | 2.61 GB | Review. |
| `...\Organized\PhoneBackups` | 2.47 GB | Candidate if duplicated elsewhere. |
| `C:\Users\issda\OneDrive\Documents` | 2.50 GB | Review carefully. |
| `...\Documents\Misc_Docs` | 1.94 GB | Review carefully; likely personal docs. |
| `...\Documents\GitHub` | 0.51 GB | Candidate if old clones/generated deps. |

## AppData / Tool Map

| Path | Size | Decision |
| --- | ---: | --- |
| `C:\Users\issda\AppData\Local\Programs\Ollama` | 3.00 GB | App install/runtime. Do not delete manually. |
| `C:\Users\issda\AppData\Local\Ollama` | 1.30 GB | Ollama app data. Prefer `ollama rm` for models. |
| `C:\Users\issda\.ollama` | 2.72 GB | Model store. `qwen2.5-coder:3b` is 1.9 GB; `1.5b` is 986 MB. |
| `C:\Users\issda\AppData\Local\ms-playwright` | 0.67 GB | Re-downloadable browser cache. Good candidate if Playwright can reinstall. |
| `C:\Users\issda\AppData\Local\npm-cache` | 0.49 GB | Re-downloadable. Good candidate. |
| `C:\Users\issda\AppData\Local\Temp` | 0.19 GB | Usually safe to clean with Windows cleanup or targeted delete. |
| `C:\Users\issda\AppData\Local\Microsoft\OneDrive` | 3.38 GB | OneDrive app cache/db. Do not manual delete while OneDrive is running. |
| `C:\Users\issda\AppData\Local\Microsoft\Edge` | 0.91 GB | Browser cache/profile. Use Edge settings, not blind delete. |

## SCBE Repo

The repo is not the problem.

| Path | Size |
| --- | ---: |
| `C:\Users\issda\SCBE-AETHERMOORE` | 0.70 GB |
| `.git` | 0.25 GB |
| `node_modules` | 0.15 GB |
| `artifacts` | 0.03 GB |

Do not spend time deleting repo internals unless we are cleaning clutter, not freeing serious space.

## Safe First Batch

These are re-downloadable or generated and do not touch personal files.

| Action | Approx Free |
| --- | ---: |
| Clear `C:\SCBE_CACHE` | 2.94 GB |
| Remove `qwen2.5-coder:3b` via Ollama | 1.90 GB |
| Clear Playwright browser cache | 0.67 GB |
| Clear npm cache | 0.49 GB |
| Clear temp | 0.19 GB |
| Total | ~6.19 GB |

## High Impact With Your Review

| Candidate | Approx Free |
| --- | ---: |
| OneDrive `SCBE-Archives\repo_generated_2026-04-11` | 2.39 GB |
| OneDrive `Offload\CrossDevice` | 2.73 GB |
| OneDrive `Dropbox\Mobile Uploads` | 2.99 GB |
| OneDrive `Organized\PhoneBackups` | 2.47 GB |
| OneDrive `Documents\Misc_Docs` | 1.94 GB |
| Total if all approved | ~12.52 GB |

## Admin-Only Batch

Run only from Administrator PowerShell.

| Action | Approx Free |
| --- | ---: |
| `powercfg /h off` | 4.70 GB |
| Shrink pagefile from 19.65 GB to 8 GB | ~11.65 GB |
| Total | ~16.35 GB |

## Recommended Order

1. Safe first batch: caches + unused 3B model. Expected: ~6 GB.
2. User-reviewed OneDrive batch: pick old archive/mobile/phone backup chunks. Expected: up to ~12.5 GB.
3. Admin-only system batch if still needed. Expected: ~16 GB.

This avoids deleting personal documents first and still gives a realistic route to 30+ GB.
