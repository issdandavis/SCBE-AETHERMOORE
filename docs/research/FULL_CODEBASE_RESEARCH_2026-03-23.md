# Full Codebase Research Map — 2026-03-23

## Scope

This report is the repo-wide map for `SCBE-AETHERMOORE` generated from a full file scan. It covers every file under the repository root except VCS internals and transient caches such as `.git`, `node_modules`, and `__pycache__`.

The goal is two-layered:

1. Provide a human research summary of the active system lanes.
2. Provide exhaustive machine-readable file inventories in JSON and CSV.

## Repo Identity

SCBE-AETHERMOORE is a hybrid monorepo spanning a TypeScript governance and crypto core, Python API/runtime services, operator scripts, dataset and artifact lanes, and extensive documentation/research surfaces.

## Totals

- Generated at: `2026-03-24T06:16:59.066903+00:00`
- Total files mapped: `39746`
- Text files: `37917`
- Total mapped lines: `7387696`
- Total mapped bytes: `1915053073`

## Lane Distribution

- `core`: `365` files
- `dataset`: `289` files
- `documentation`: `758` files
- `generated`: `1905` files
- `operations`: `395` files
- `runtime`: `1017` files
- `support`: `34465` files
- `validation`: `552` files

## State Distribution

- `active`: `35647` files
- `archive`: `539` files
- `dataset`: `287` files
- `documentation`: `421` files
- `generated`: `1905` files
- `operations`: `395` files
- `test`: `552` files

## Dominant Aspects By Line Count

| Aspect | Files | Lines | Bytes | Notes |
|---|---:|---:|---:|---|
| `external` | 26538 | 3576426 | 152352160 | Aspect discovered during full-file scan. |
| `training` | 1815 | 1972423 | 378764088 | Aspect discovered during full-file scan. |
| `artifacts` | 1904 | 453524 | 870159087 | Generated evidence, reports, outputs, and experiment products. |
| `docs` | 758 | 228733 | 12984169 | Specs, research notes, product documentation, and operational guides. |
| `training-data` | 289 | 144440 | 262029334 | Corpora, datasets, and training-oriented source material. |
| `scripts` | 395 | 97770 | 3672731 | Operational control plane, automation, research tooling, deployment, and daily workflows. |
| `src/symphonic_cipher` | 206 | 97348 | 3275722 | Cipher-specific implementation lane tied to symphonic constructs. |
| `symphonic_cipher` | 94 | 56736 | 1901647 | Aspect discovered during full-file scan. |
| `content` | 236 | 42206 | 2923797 | Aspect discovered during full-file scan. |
| `demo` | 45 | 37832 | 1563846 | Aspect discovered during full-file scan. |
| `kindle-app` | 1138 | 33250 | 139189400 | Aspect discovered during full-file scan. |
| `scbe-visual-system` | 59 | 21303 | 769284 | Aspect discovered during full-file scan. |
| `notebooks` | 13 | 20549 | 3292637 | Aspect discovered during full-file scan. |
| `src/fleet` | 48 | 20106 | 624314 | Aspect discovered during full-file scan. |
| `hydra` | 36 | 19872 | 740093 | Aspect discovered during full-file scan. |
| `tests/harmonic` | 34 | 18777 | 711140 | Aspect discovered during full-file scan. |
| `packages` | 52 | 17047 | 541202 | Aspect discovered during full-file scan. |
| `public` | 33 | 16818 | 774111 | Aspect discovered during full-file scan. |
| `agents` | 54 | 16200 | 564267 | Aspect discovered during full-file scan. |
| `src/crypto` | 33 | 15057 | 502373 | TypeScript cryptography, envelopes, replay guards, key derivation, integrity layers. |
| `tests/L2-unit` | 30 | 14215 | 518234 | Aspect discovered during full-file scan. |
| `src/harmonic` | 70 | 13218 | 468295 | 14-layer harmonic pipeline, hyperbolic geometry, wall and projection math. |
| `.n8n_local_iso` | 738 | 12530 | 56131217 | Aspect discovered during full-file scan. |
| `src/browser` | 20 | 12192 | 397001 | Aspect discovered during full-file scan. |
| `src/ai_brain` | 26 | 12170 | 432540 | AI cognition and embedding-adjacent reasoning modules. |
| `examples` | 59 | 11142 | 895062 | Aspect discovered during full-file scan. |
| `notes` | 173 | 11033 | 465480 | Aspect discovered during full-file scan. |
| `tests/ai_brain` | 21 | 10154 | 398279 | Aspect discovered during full-file scan. |
| `.hypothesis` | 2533 | 10116 | 1306125 | Aspect discovered during full-file scan. |
| `conference-app` | 39 | 9476 | 325863 | Aspect discovered during full-file scan. |

## System-Aspects Research Summary

### external

- Description: Aspect discovered during full-file scan.
- Files: `26538`
- Lines: `3576426`
- Bytes: `152352160`
- Top extensions: `[('.md', 15162), ('.ts', 5653), ('.json', 2202), ('<none>', 842), ('.swift', 574), ('.py', 435)]`
- Representative entrypoints: `['external/Entropicdefenseengineproposal/ARCHITECTURE_VISUAL.txt']`

### training

- Description: Aspect discovered during full-file scan.
- Files: `1815`
- Lines: `1972423`
- Bytes: `378764088`
- Top extensions: `[('.json', 1457), ('.jsonl', 113), ('.bin', 111), ('.zip', 63), ('.md', 21), ('.txt', 21)]`
- Representative entrypoints: `['training/NOTION_CODEBASE_COMPARISON.md']`

### artifacts

- Description: Generated evidence, reports, outputs, and experiment products.
- Files: `1904`
- Lines: `453524`
- Bytes: `870159087`
- Top extensions: `[('.md', 1201), ('.db', 367), ('.json', 171), ('.csv', 94), ('.png', 24), ('.jsonl', 11)]`
- Representative entrypoints: `['artifacts/adversarial_governance_test.json']`

### docs

- Description: Specs, research notes, product documentation, and operational guides.
- Files: `758`
- Lines: `228733`
- Bytes: `12984169`
- Top extensions: `[('.md', 679), ('.json', 18), ('.png', 14), ('.txt', 14), ('.html', 7), ('.pdf', 5)]`
- Representative entrypoints: `['README.md', 'docs/LANGUES_WEIGHTING_SYSTEM.md', 'SPEC.md']`

### training-data

- Description: Corpora, datasets, and training-oriented source material.
- Files: `289`
- Lines: `144440`
- Bytes: `262029334`
- Top extensions: `[('.md', 143), ('.jsonl', 91), ('.json', 28), ('.png', 19), ('.jpg', 6), ('.csv', 2)]`
- Representative entrypoints: `['training-data/OPEN_SOURCE_DATASETS.md']`

### scripts

- Description: Operational control plane, automation, research tooling, deployment, and daily workflows.
- Files: `395`
- Lines: `97770`
- Bytes: `3672731`
- Top extensions: `[('.py', 268), ('.ps1', 89), ('.sh', 12), ('.bat', 11), ('.mjs', 5), ('.js', 4)]`
- Representative entrypoints: `['scripts/hydra_command_center.ps1']`

### src/symphonic_cipher

- Description: Cipher-specific implementation lane tied to symphonic constructs.
- Files: `206`
- Lines: `97348`
- Bytes: `3275722`
- Top extensions: `[('.py', 203), ('.md', 3)]`
- Representative entrypoints: `['src/symphonic_cipher/__init__.py']`

### symphonic_cipher

- Description: Aspect discovered during full-file scan.
- Files: `94`
- Lines: `56736`
- Bytes: `1901647`
- Top extensions: `[('.py', 92), ('.md', 2)]`
- Representative entrypoints: `['symphonic_cipher/__init__.py']`

### content

- Description: Aspect discovered during full-file scan.
- Files: `236`
- Lines: `42206`
- Bytes: `2923797`
- Top extensions: `[('.md', 216), ('.txt', 12), ('.json', 6), ('.py', 1), ('.docx', 1)]`
- Representative entrypoints: `['content/articles/2026-03-05-25d-quadtree-octree-hybrid.md']`

### demo

- Description: Aspect discovered during full-file scan.
- Files: `45`
- Lines: `37832`
- Bytes: `1563846`
- Top extensions: `[('.py', 39), ('.html', 2), ('.md', 1), ('.twee', 1), ('.txt', 1), ('.ts', 1)]`
- Representative entrypoints: `['demo/README.md']`

### kindle-app

- Description: Aspect discovered during full-file scan.
- Files: `1138`
- Lines: `33250`
- Bytes: `139189400`
- Top extensions: `[('.png', 904), ('.jpg', 106), ('.xml', 19), ('.json', 19), ('.html', 18), ('.bin', 8)]`
- Representative entrypoints: `['kindle-app/android/.gitignore']`

### scbe-visual-system

- Description: Aspect discovered during full-file scan.
- Files: `59`
- Lines: `21303`
- Bytes: `769284`
- Top extensions: `[('.tsx', 25), ('.ts', 19), ('.js', 4), ('.json', 4), ('.cjs', 2), ('.yml', 1)]`
- Representative entrypoints: `['scbe-visual-system/.github/workflows/build.yml']`

### notebooks

- Description: Aspect discovered during full-file scan.
- Files: `13`
- Lines: `20549`
- Bytes: `3292637`
- Top extensions: `[('.ipynb', 12), ('.py', 1)]`
- Representative entrypoints: `['notebooks/colab_aethermoor_datagen.ipynb']`

### src/fleet

- Description: Aspect discovered during full-file scan.
- Files: `48`
- Lines: `20106`
- Bytes: `624314`
- Top extensions: `[('.ts', 43), ('.py', 5)]`
- Representative entrypoints: `['src/fleet/__init__.py']`

### hydra

- Description: Aspect discovered during full-file scan.
- Files: `36`
- Lines: `19872`
- Bytes: `740093`
- Top extensions: `[('.py', 36)]`
- Representative entrypoints: `['hydra/__init__.py']`

### tests/harmonic

- Description: Aspect discovered during full-file scan.
- Files: `34`
- Lines: `18777`
- Bytes: `711140`
- Top extensions: `[('.ts', 34)]`
- Representative entrypoints: `['tests/harmonic/adaptiveNavigator.test.ts']`

### packages

- Description: Aspect discovered during full-file scan.
- Files: `52`
- Lines: `17047`
- Bytes: `541202`
- Top extensions: `[('.ts', 45), ('.json', 2), ('.md', 2), ('<none>', 1), ('.txt', 1), ('.py', 1)]`
- Representative entrypoints: `['packages/kernel/package.json']`

### public

- Description: Aspect discovered during full-file scan.
- Files: `33`
- Lines: `16818`
- Bytes: `774111`
- Top extensions: `[('.json', 22), ('.html', 8), ('.png', 2), ('.js', 1)]`
- Representative entrypoints: `['public/.well-known/assetlinks.json']`

### agents

- Description: Aspect discovered during full-file scan.
- Files: `54`
- Lines: `16200`
- Bytes: `564267`
- Top extensions: `[('.py', 53), ('.md', 1)]`
- Representative entrypoints: `['agents/__init__.py']`

### src/crypto

- Description: TypeScript cryptography, envelopes, replay guards, key derivation, integrity layers.
- Files: `33`
- Lines: `15057`
- Bytes: `502373`
- Top extensions: `[('.py', 17), ('.ts', 16)]`
- Representative entrypoints: `['src/index.ts', 'src/crypto/index.ts']`

### tests/L2-unit

- Description: Aspect discovered during full-file scan.
- Files: `30`
- Lines: `14215`
- Bytes: `518234`
- Top extensions: `[('.ts', 30)]`
- Representative entrypoints: `['tests/L2-unit/asymmetricMovement.unit.test.ts']`

### src/harmonic

- Description: 14-layer harmonic pipeline, hyperbolic geometry, wall and projection math.
- Files: `70`
- Lines: `13218`
- Bytes: `468295`
- Top extensions: `[('.ts', 51), ('.map', 11), ('.py', 8)]`
- Representative entrypoints: `['src/index.ts', 'src/harmonic/index.ts']`

### .n8n_local_iso

- Description: Aspect discovered during full-file scan.
- Files: `738`
- Lines: `12530`
- Bytes: `56131217`
- Top extensions: `[('.js', 574), ('.css', 142), ('.json', 18), ('.html', 1), ('<none>', 1), ('.sqlite-shm', 1)]`
- Representative entrypoints: `['.n8n_local_iso/.cache/n8n/public/assets/AddDataTableModal-NM_jzV6e.js']`

### src/browser

- Description: Aspect discovered during full-file scan.
- Files: `20`
- Lines: `12192`
- Bytes: `397001`
- Top extensions: `[('.ts', 14), ('.py', 6)]`
- Representative entrypoints: `['src/browser/agent.ts']`

### src/ai_brain

- Description: AI cognition and embedding-adjacent reasoning modules.
- Files: `26`
- Lines: `12170`
- Bytes: `432540`
- Top extensions: `[('.ts', 24), ('.py', 2)]`
- Representative entrypoints: `['src/index.ts', 'src/ai_brain/index.ts']`

### examples

- Description: Aspect discovered during full-file scan.
- Files: `59`
- Lines: `11142`
- Bytes: `895062`
- Top extensions: `[('.py', 29), ('.json', 10), ('.md', 4), ('<none>', 3), ('.toml', 3), ('.ts', 3)]`
- Representative entrypoints: `['examples/MyAgent/.bedrock_agentcore.yaml']`

### notes

- Description: Aspect discovered during full-file scan.
- Files: `173`
- Lines: `11033`
- Bytes: `465480`
- Top extensions: `[('.md', 172), ('.json', 1)]`
- Representative entrypoints: `['notes/.obsidian/app.json']`

### tests/ai_brain

- Description: Aspect discovered during full-file scan.
- Files: `21`
- Lines: `10154`
- Bytes: `398279`
- Top extensions: `[('.ts', 21)]`
- Representative entrypoints: `['tests/ai_brain/audit.test.ts']`

### .hypothesis

- Description: Aspect discovered during full-file scan.
- Files: `2533`
- Lines: `10116`
- Bytes: `1306125`
- Top extensions: `[('<none>', 2531), ('.gz', 2)]`
- Representative entrypoints: `['.hypothesis/constants/00275fbf23a2c678']`

### conference-app

- Description: Aspect discovered during full-file scan.
- Files: `39`
- Lines: `9476`
- Bytes: `325863`
- Top extensions: `[('.ts', 20), ('.tsx', 14), ('.json', 3), ('.html', 1), ('.css', 1)]`
- Representative entrypoints: `['conference-app/package-lock.json']`

### src/physics_sim

- Description: Physics-oriented simulation lane.
- Files: `12`
- Lines: `8637`
- Bytes: `248141`
- Top extensions: `[('.py', 12)]`
- Representative entrypoints: `['src/physics_sim/__init__.py']`

### .github

- Description: Aspect discovered during full-file scan.
- Files: `77`
- Lines: `8380`
- Bytes: `282470`
- Top extensions: `[('.yml', 74), ('.md', 2), ('<none>', 1)]`
- Representative entrypoints: `['.github/CODEOWNERS']`

### tests/fleet

- Description: Aspect discovered during full-file scan.
- Files: `13`
- Lines: `7776`
- Bytes: `280419`
- Top extensions: `[('.ts', 13)]`
- Representative entrypoints: `['tests/fleet/autoRetrigger.test.ts']`

### package-lock.json

- Description: Aspect discovered during full-file scan.
- Files: `1`
- Lines: `7346`
- Bytes: `272318`
- Top extensions: `[('.json', 1)]`
- Representative entrypoints: `['package-lock.json']`

### src/spiralverse

- Description: Intent-auth, communication, and Spiralverse language plane.
- Files: `15`
- Lines: `7333`
- Bytes: `236876`
- Top extensions: `[('.py', 9), ('.ts', 6)]`
- Representative entrypoints: `['src/spiralverse/__init__.py']`

### mcp

- Description: Aspect discovered during full-file scan.
- Files: `15`
- Lines: `7314`
- Bytes: `254813`
- Top extensions: `[('.ts', 4), ('.py', 4), ('.json', 3), ('.md', 2), ('.html', 1), ('.mjs', 1)]`
- Representative entrypoints: `['mcp/apps/cymatic-voxel-app/README.md']`

### src/api

- Description: Newer FastAPI control plane, HYDRA routes, SaaS, mesh, billing.
- Files: `12`
- Lines: `6321`
- Bytes: `209689`
- Top extensions: `[('.ts', 7), ('.py', 5)]`
- Representative entrypoints: `['src/api/main.py']`

### src/ai_orchestration

- Description: Aspect discovered during full-file scan.
- Files: `10`
- Lines: `6267`
- Bytes: `215330`
- Top extensions: `[('.py', 10)]`
- Representative entrypoints: `['src/ai_orchestration/__init__.py']`

### experiments

- Description: Aspect discovered during full-file scan.
- Files: `16`
- Lines: `6119`
- Bytes: `216350`
- Top extensions: `[('.py', 10), ('.json', 6)]`
- Representative entrypoints: `['experiments/exp_decimal_drift_discrimination.py']`

### workflows

- Description: Aspect discovered during full-file scan.
- Files: `24`
- Lines: `6067`
- Bytes: `208280`
- Top extensions: `[('.json', 17), ('.py', 3), ('.sh', 2), ('.md', 1), ('.yaml', 1)]`
- Representative entrypoints: `['workflows/n8n/ai2ai_research_debate_payload.sample.json']`

## Largest Text Files

| Path | Lines | Summary |
|---|---:|---|
| `training/sft_records/sft_combined.json` | 721706 | [ |
| `artifacts/onedrive-migration/20260321-091502/SCBE_Archives/local-files.txt` | 53459 | ﻿AETHERMOORE_CONSTANTS_IP_GUIDE.txt |
| `artifacts/onedrive-migration/20260321-092524/SCBE_Archives/local-files.txt` | 53459 | ﻿AETHERMOORE_CONSTANTS_IP_GUIDE.txt |
| `external/claude-code-plugins-plus-skills/marketplace/src/data/unified-search-index.json` | 49058 | { |
| `training-data/mega_ingest_sft.jsonl` | 43583 | {"prompt": "Describe the SCBE-AETHERMOORE browser agent architecture and its governance integration.", "response": "The  |
| `training-data/mega_tetris_enriched_sft.jsonl` | 43583 | {"prompt": "Describe the SCBE-AETHERMOORE browser agent architecture and its governance integration.", "response": "The  |
| `external/claude-code-plugins-plus-skills/marketplace/src/data/skills-catalog.json` | 40670 | { |
| `artifacts/training/training_merged.jsonl` | 28678 | {"prompt": "Describe the SCBE-AETHERMOORE browser agent architecture and its governance integration.", "response": "The  |
| `training/sft_records/sft_combined.jsonl` | 28133 | {"timestamp": "2026-02-22T05:38:11.100078+00:00", "tool": "tongue_encode", "inputs": {"tongue": "KO", "byte_count": 22}, |
| `artifacts/notion_export_unpacked/Export-d3f8086e-07e0-444f-9291-10b7fe375b22/🔬 Overnight Research Pipeline - 100 Topics 2d1f96de82e580b39622f18cf961e8c5.csv` | 25547 | ﻿Name,Status,Priority,Code Destination,Research Output,Code Output,Platform |
| `artifacts/notion_export_unpacked/Export-d3f8086e-07e0-444f-9291-10b7fe375b22/🔬 Overnight Research Pipeline - 100 Topics 2d1f96de82e580b39622f18cf961e8c5_all.csv` | 25547 | ﻿Name,Code Destination,Code Output,Platform,Priority,Research Output,Status |
| `training/ingest/local_cloud_sync_state.json` | 24267 | { |
| `training/runs/local_cloud_sync/20260324T061625Z/index.json` | 23552 | { |
| `training/runs/local_cloud_sync/20260324T060824Z/index.json` | 23548 | { |
| `training/runs/local_cloud_sync/20260324T061224Z/index.json` | 23548 | { |
| `training/runs/local_cloud_sync/20260324T060624Z/index.json` | 23544 | { |
| `training/runs/local_cloud_sync/20260324T052622Z/index.json` | 23536 | { |
| `training/runs/local_cloud_sync/20260324T053222Z/index.json` | 23536 | { |
| `training/runs/local_cloud_sync/20260324T053823Z/index.json` | 23536 | { |
| `training/runs/local_cloud_sync/20260324T044022Z/index.json` | 23532 | { |
| `training/runs/local_cloud_sync/20260324T041621Z/index.json` | 23516 | { |
| `training/runs/local_cloud_sync/20260324T034423Z/index.json` | 23512 | { |
| `training/runs/local_cloud_sync/20260324T035021Z/index.json` | 23512 | { |
| `training/runs/local_cloud_sync/20260324T033622Z/index.json` | 23508 | { |
| `training/runs/local_cloud_sync/20260324T032022Z/index.json` | 23504 | { |

## Extension Distribution

| Extension | Count |
|---|---:|
| `.md` | 17818 |
| `.ts` | 6196 |
| `.json` | 4114 |
| `<none>` | 3982 |
| `.py` | 1925 |
| `.png` | 1085 |
| `.js` | 702 |
| `.swift` | 574 |
| `.sh` | 410 |
| `.db` | 371 |
| `.jsonl` | 244 |
| `.csv` | 216 |
| `.yaml` | 213 |
| `.css` | 174 |
| `.yml` | 166 |
| `.jpg` | 129 |
| `.txt` | 123 |
| `.bin` | 121 |
| `.kt` | 113 |
| `.tsx` | 112 |
| `.ps1` | 104 |
| `.astro` | 91 |
| `.html` | 88 |
| `.zip` | 72 |
| `.prose` | 64 |

## Research Conclusions

1. The repo is not one product surface; it is a mesh of core math, runtime services, operator control, research, and content pipelines.
2. The TypeScript core and Python runtime lanes coexist rather than cleanly replacing one another; both must be mapped when making claims about the system.
3. `scripts/` is a real operational control plane, not just glue code.
4. `docs/`, `artifacts/`, and `training-data/` are substantial parts of system knowledge, but they should be separated from proof of runtime behavior.
5. Any future benchmark or architecture claim should cite both the canonical core lane and the exact runtime lane used.

## Exhaustive Inventory Artifacts

- JSON map: `artifacts/research/full_codebase_map.json`
- CSV map: `artifacts/research/full_codebase_map.csv`
- Lane stats: `artifacts/research/full_codebase_lane_stats.json`

