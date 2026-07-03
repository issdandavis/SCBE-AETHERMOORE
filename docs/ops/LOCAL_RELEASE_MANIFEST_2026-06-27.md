# Local Release Manifest - 2026-06-27

Scope: local product systems, build artifacts, release targets, and deployment lanes under `C:\Users\issda`.

This is a release-tracking document, not a publish record. No builds, tests, uploads, or registry publishes were run while creating it.

## Executive summary

Primary release candidates:

| Priority | Product | Local root | Release target | Current state | Next gate |
|---|---|---|---|---|---|
| 1 | SCBE-AETHERMOORE / GeoSeal CLI | `C:\Users\issda\SCBE-AETHERMOORE` | npm `scbe-aethermoore@4.2.1`; PyPI `scbe-aethermoore==4.2.1`; GitHub release | metadata ready, branch-base decision required | choose release branch, run npm/PyPI package gates |
| 2 | AetherDesk | `C:\Users\issda\AetherDesk` | local desktop app, React `/desktop/`, possible Vercel/web deployment | package and release scripts present; recent UI/build smoke previously verified in-session | run `release:check`, decide deployment shape |
| 3 | SCBE local coder model | `C:\Users\issda\LocalOnly\models\scbe-qwen15` | local Ollama model `scbe-coder`; HF GGUF repo | Q4/Q5/Q8 GGUF local; Ollama model installed | package usage docs and optional eval card |
| 4 | SCBE hybrid/router and weight-eval lane | `C:\Users\issda\LocalOnly\models` | local research/product CLI; future HF/model card artifacts | router script and weight-eval artifacts present | decide whether to package under SCBE or keep LocalOnly |
| 5 | Patent workbench/evidence packet | `C:\Users\issda\SCBE-AETHERMOORE\docs\legal\patent-workbench` and `C:\Users\issda\LocalOnly\patent\63961403` | private procedural evidence tracker, not public release | metadata and receipt-history fragments captured | wait for USPTO documents/reply, then compare official filing |

Secondary local checkouts are mostly duplicate SCBE worktrees or scratch branches. They should not be release sources unless intentionally selected.

## Registry and version state

Observed registry state during release-prep:

| Registry | Package | Public latest observed | Local version | Meaning |
|---|---|---:|---:|---|
| npm | `scbe-aethermoore` | `4.1.3` | `4.2.1` | npm needs catch-up release |
| PyPI | `scbe-aethermoore` | `4.2.0` | `4.2.1` | PyPI needs smaller follow-up release |

Local SCBE metadata alignment:

| File | Version | Notes |
|---|---:|---|
| `package.json` | `4.2.1` | exposes npm bins `geoseal`, `scbe-geoseal`, `scbe-patent`, `scbe-scan` |
| `pyproject.toml` | `4.2.1` | exposes Python console scripts, but not direct `geoseal` yet |

Important packaging gap:

```text
npm has direct GeoSeal CLI bins.
PyPI currently does not expose direct geoseal/scbe-geoseal console entries.
```

Recommendation:

1. Publish npm as the direct GeoSeal CLI surface after gates pass.
2. Publish PyPI `4.2.1` only after Python build/check gates pass.
3. Add direct PyPI `geoseal` console entry in a separate verified patch unless we choose to include it before any `4.2.1` publish.

## Source roots inventory

### Main product roots

| Root | Kind | Release role | Notes |
|---|---|---|---|
| `C:\Users\issda\SCBE-AETHERMOORE` | main repo | primary SCBE/GeoSeal release source | npm/PyPI/GitHub/Netlify/Vercel configs present |
| `C:\Users\issda\AetherDesk` | standalone app repo | local operator desktop release source | package `aetherdesk@0.1.0`, Vercel config, release scripts present |
| `C:\Users\issda\LocalOnly\models` | local model/product artifacts | local model and hybrid-agent release staging | GGUFs, Ollama model, router, weight-eval artifacts |
| `C:\Users\issda\LocalOnly\tools` | local dev tools | build/research support only | OpenWeights and MergeKit installed locally |
| `C:\Users\issda\LocalOnly\patent\63961403` | private evidence staging | legal/procedural evidence only | not a public product release |

### Duplicate/scratch SCBE checkouts found

These look like worktrees or alternate branch checkouts of the same `scbe-aethermoore` package. Treat as non-release sources unless deliberately promoted.

| Root | Observed role |
|---|---|
| `C:\Users\issda\helm-operator-land-wt` | SCBE worktree/scratch lane |
| `C:\Users\issda\instrument-wt` | SCBE worktree/scratch lane |
| `C:\Users\issda\mountain-v8-wt` | SCBE worktree/scratch lane |
| `C:\Users\issda\SCBE-AETHERMOORE-fix-bandit` | SCBE fix branch checkout |
| `C:\Users\issda\SCBE-AETHERMOORE-main-audit` | SCBE audit checkout |
| `C:\Users\issda\SCBE-AETHERMOORE-security-fix` | SCBE security-fix checkout |
| `C:\Users\issda\scbe-mcp-config-hygiene` | SCBE hygiene checkout |
| `C:\Users\issda\scbe-pr2544-fix` | SCBE PR/fix checkout |
| `C:\Users\issda\scbe-uport-wt` | SCBE worktree/scratch lane |
| `C:\Users\issda\slice-wt` | SCBE worktree/scratch lane |

Do not publish from these without a branch/rebase decision.

## SCBE-AETHERMOORE release target

Local root:

```text
C:\Users\issda\SCBE-AETHERMOORE
```

Known release products:

| Product | Surface | Target | Status |
|---|---|---|---|
| GeoSeal CLI | npm binary | `geoseal`, `scbe-geoseal` | direct npm CLI surface present |
| SCBE package | npm library/CLI | `scbe-aethermoore@4.2.1` | next npm release candidate |
| SCBE package | PyPI package | `scbe-aethermoore==4.2.1` | next PyPI release candidate |
| Patent workbench | repo docs/CLI | `scbe-patent` and `docs/legal/patent-workbench` | internal procedural surface |
| Docs/web demos | static web | Vercel/Netlify configs present | deployment target needs explicit selection |

Branch warning from previous compare:

```text
current local branch matched origin/lane/tool-trajectory-harvester
origin/main...HEAD was divergent: 111 behind / 18 ahead
```

Release rule:

```text
Do not publish from this checkout until the release base is explicitly chosen.
```

Recommended SCBE gates, in order:

```powershell
npm run publish:prepare
npm run publish:check:strict
npm run publish:smoke:consumer
npm publish --dry-run
npm run publish:pypi:build
npm run publish:pypi:check
python -m twine check artifacts/pypi-dist/*
```

Publish commands, only after explicit approval:

```powershell
npm publish
python -m twine upload artifacts/pypi-dist/*
```

GeoSeal smoke gates to run before publishing:

```powershell
node bin/geoseal.cjs doctor --json
node bin/geoseal.cjs providers --json
node bin/geoseal.cjs lanes --json
node bin/geoseal.cjs service-status --json
node bin/geoseal.cjs tokenizer-code-lanes --command shl --tongues all --json
```

Python GeoSeal/SCBE probes should use:

```powershell
$env:SCBE_FORCE_SKIP_LIBOQS='1'
python -m src.geoseal_cli --help
python -m src.geoseal_cli mars-mission --json
```

## AetherDesk release target

Local root:

```text
C:\Users\issda\AetherDesk
```

Observed metadata:

| Field | Value |
|---|---|
| package | `aetherdesk` |
| version | `0.1.0` |
| description | local-first operator desktop with bounded terminal, browser, receipts, notebook, transcripts, and draft tools |
| deployment config | `vercel.json` present |

Important scripts observed:

```text
start
aetherdesk
dev:react
build:react
start:react
test
test:aetherdesk
release:check
release:check:agent
audit:product
aetherdesk:ai-pc:smoke
connector:smoke
web:audit
proton:status
```

Prior in-session state:

- React `/desktop/` route and server were verified earlier in this thread.
- Playwright smoke was reported clean earlier in this thread.
- Windows Fluent/Acrylic UI pass was completed earlier in this thread.

Release role:

| Target | Status | Next gate |
|---|---|---|
| local desktop/server | strongest current lane | run `npm run release:check` |
| React web route `/desktop/` | present | run `npm run build:react` and smoke |
| Vercel/web | config present | decide public/private deployment target |
| MCP/connector lane | scripts present | run connector smoke only if deploying connector |

AetherDesk release rule:

```text
Keep shell execution bounded by allowlisted profiles. Do not turn terminal release into arbitrary host shell execution.
```

## Local model release target

Local root:

```text
C:\Users\issda\LocalOnly\models
```

Ollama models observed:

| Model | Size | Role |
|---|---:|---|
| `scbe-coder:latest` | 986 MB | local SCBE fine-tuned coder |
| `qwen2.5-coder:1.5b` | 986 MB | local base/reference model |

Local GGUF artifacts:

| File | Size | Role |
|---|---:|---|
| `scbe-coding-agent-vtc-qwen15-v1.Q4_K_M.gguf` | 986,048,000 bytes | recommended local Ollama quant |
| `scbe-coding-agent-vtc-qwen15-v1.Q5_K_M.gguf` | 1,125,049,856 bytes | higher-quality quant |
| `scbe-coding-agent-vtc-qwen15-v1.Q8_0.gguf` | 1,646,572,544 bytes | near-lossless local quant |
| `Modelfile` | present | Ollama creation file |
| `README.md` | present | GGUF repo card copy |

Known upstream release target:

```text
issdandavis/scbe-coding-agent-vtc-qwen15-v1-gguf
```

Local product files:

| File | Role |
|---|---|
| `C:\Users\issda\LocalOnly\models\scbe_hybrid.py` | local hybrid/router CLI prototype |
| `C:\Users\issda\LocalOnly\models\SCBE_HYBRID_AND_WEIGHT_EVAL_PLAN.md` | lane plan for product router and weight science |
| `C:\Users\issda\LocalOnly\models\weight_eval\` | local LoRA/ablation/eval artifacts |

Release role:

| Target | Status | Next gate |
|---|---|---|
| local Ollama use | ready locally | document install/use commands |
| HF GGUF model card | already has local copy | ensure README/eval table current before future model updates |
| hybrid router | local prototype | decide whether to move into SCBE repo/package |
| weight-eval results | local research artifacts | summarize into model card or research report when stable |

## Patent workbench / evidence target

Repo workbench:

```text
C:\Users\issda\SCBE-AETHERMOORE\docs\legal\patent-workbench
```

Private recovery map:

```text
C:\Users\issda\LocalOnly\patent\63961403
```

Tracked record:

| Field | Value |
|---|---|
| docket | `SCBE-2026-0001` |
| provisional application | `63/961,403` |
| newly observed application | `19/691,526` |
| filing date | `2026-01-15` |
| title | `System and Method for Hyperbolic Geometry-Based Authorization with Topological Control-Flow Integrity` |
| first named inventor | `Issac Daniel Davis` |

Release role:

```text
internal evidence tracker only; do not publish as product artifact without review.
```

Next step:

```text
Wait for USPTO reply/export. Compare official filed document against recovered claim snapshot when available.
```

## Development tooling inventory

Local-only tooling:

| Tool | Path | Role |
|---|---|---|
| OpenWeights | `C:\Users\issda\LocalOnly\tools\openweights` | remote/job training and model operations support |
| MergeKit | `C:\Users\issda\LocalOnly\tools\mergekit` | same-architecture model merge/ablation support |

Release rule:

```text
These are build/research tools, not products to publish.
```

## Deployment manifest

| Deployment | Product | Environment | Status | Release action |
|---|---|---|---|---|
| npm package | SCBE/GeoSeal | npm registry | candidate `4.2.1` | run npm gates, then publish after approval |
| PyPI package | SCBE Python | PyPI registry | candidate `4.2.1` | run PyPI gates, decide geoseal console gap |
| GitHub release/tag | SCBE-AETHERMOORE | GitHub | not cut | choose release branch/base first |
| Static web/docs | SCBE-AETHERMOORE | Vercel/Netlify configs | config present, not verified this turn | select target and run deploy-specific check |
| AetherDesk local desktop | AetherDesk | Windows localhost/server | recent smoke verified earlier | run release check before packaging |
| AetherDesk web route | AetherDesk | React `/desktop/` and possible Vercel | config present | run build/smoke before deployment |
| AetherDesk skills marketplace | AetherDesk | local Skills app, Ctrl-K command palette, reusable workflow manifests | backlog created | define skill manifest schema and wire existing actions |
| Ollama model | SCBE coder | local Ollama | installed as `scbe-coder` | document usage; optional model smoke |
| HF GGUF | SCBE coder model | Hugging Face repo | released previously | update only if new quant/model created |
| Patent workbench | SCBE legal ops | private local/repo docs | active evidence tracker | keep private, update after USPTO reply |

## Ordered release plan

### Step 1 - Freeze release base

Decide whether release source is:

1. current `SCBE-AETHERMOORE` lane branch;
2. a fresh branch from `origin/main` with cherry-picked release files;
3. a merged/rebased release branch.

Recommended:

```text
Fresh release branch with only release-safe deltas, because the active lane diverges heavily from main.
```

### Step 2 - Run SCBE/GeoSeal package gates

Commands to run only when ready for validation:

```powershell
npm run publish:prepare
npm run publish:check:strict
npm run publish:smoke:consumer
npm publish --dry-run
npm run publish:pypi:build
npm run publish:pypi:check
python -m twine check artifacts/pypi-dist/*
```

### Step 3 - Decide PyPI GeoSeal console handling

Options:

1. publish PyPI `4.2.1` without direct `geoseal` command;
2. add direct PyPI `geoseal` wrapper before publishing;
3. defer PyPI and ship npm first.

Recommended:

```text
Ship npm direct CLI first, then add a verified PyPI geoseal wrapper as a follow-up unless we choose to block 4.2.1 on it.
```

### Step 4 - AetherDesk release gate

Commands to run only when ready for validation:

```powershell
npm run release:check
npm run build:react
npm run aetherdesk:ai-pc:smoke
```

Decide target:

```text
local Windows app only, web/Vercel route, or MCP/connector bundle.
```

### Step 5 - Model release docs

Document local use:

```powershell
ollama run scbe-coder "Write a Python function add(a, b). Return ONLY the code."
```

If making a public model update, update:

```text
HF model card
GGUF README
local Modelfile
model eval table
```

### Step 6 - Patent evidence hold

No public release action. Keep the workbench updated when USPTO sends the next reply.

## Product status labels

Use these labels going forward:

| Label | Meaning |
|---|---|
| `release-candidate` | package/build metadata present, needs gates |
| `local-ready` | works locally, not packaged/published |
| `internal-only` | evidence/research/legal, not public release |
| `duplicate-checkout` | alternate worktree, not a release source |
| `blocked-on-decision` | needs branch/deploy/package choice |
| `blocked-on-evidence` | needs official external document/reply |

## Current status by item

| Item | Label | Why |
|---|---|---|
| SCBE-AETHERMOORE npm | `release-candidate`, `blocked-on-decision` | version ready, branch base unresolved |
| SCBE-AETHERMOORE PyPI | `release-candidate`, `blocked-on-decision` | version ready, direct GeoSeal console gap unresolved |
| GeoSeal CLI npm | `release-candidate` | direct npm bins present |
| AetherDesk | `local-ready`, `blocked-on-decision` | app scripts and recent smoke exist, deployment target not selected |
| SCBE coder GGUF/Ollama | `local-ready` | local Ollama model installed and GGUF files present |
| Hybrid router | `local-ready`, `internal-only` | local prototype, not packaged |
| Weight eval | `internal-only` | research artifacts, not release product yet |
| Patent workbench | `internal-only`, `blocked-on-evidence` | waiting for USPTO reply/export |
| Duplicate SCBE worktrees | `duplicate-checkout` | not release sources unless promoted |

## Non-actions performed while creating this manifest

Not performed:

- no npm build;
- no PyPI build;
- no test suite;
- no registry publish;
- no Vercel/Netlify deploy;
- no Git branch changes;
- no model upload;
- no Patent Center document export.
## Release manifest update - AetherDesk product specs

Added local product specification artifacts for the AetherDesk browser/skill marketplace lane:

| Artifact | Path | Release relevance |
|---|---|---|
| Skill manifest schema | `docs/specs/AETHERDESK_SKILL_MANIFEST_SCHEMA.md` | Defines the stable contract for local skills, copied Kimi-style workflows, CLI/MCP routes, permissions, receipts, and training conversion. |
| Browser action packet | `docs/specs/AETHERDESK_BROWSER_ACTION_PACKET.md` | Defines the browser/AI/human control packet, no-secret boundary, no-repeated-polling rule, and receipt format. |
| Long-form workflow | `docs/specs/AETHERDESK_LONG_FORM_WORKFLOW.md` | Defines sleeping-user mode, checkpointing, approval-blocked tasks, and run handoff format. |

Validation status:

- Not built in this pass.
- Not tested in this pass.
- No training, publish, cloud job, or repeated polling was run.

## Release manifest update - AetherDesk local skill catalog

| Artifact | Path | Release relevance |
|---|---|---|
| Draft app skill catalog | `C:/Users/issda/AetherDesk/react-desktop/src/skills/catalog.json` | Moves copied skill-card ideas toward a data-driven local marketplace. Not wired into runtime yet. |
| Draft browser action presets | `C:/Users/issda/AetherDesk/react-desktop/src/skills/browserActionPresets.json` | Defines safe handoff packets from skill cards to Aether Browser. Not wired into runtime yet. |

Validation status:

- JSON was written but not build-validated in this pass.
- React import wiring was intentionally deferred.

Runtime wiring update:

| Artifact | Path | Release relevance |
|---|---|---|
| AetherDesk React shell | `C:/Users/issda/AetherDesk/react-desktop/src/main.jsx` | Now imports the skill catalog and browser action presets, normalizes skill data, and passes pending browser action packets into Aether Browser. |

Validation status:

- Code changed after the last known verified build.
- Build and browser smoke are still required before release claims.

## Release manifest update - train-orchestrator morning sync

Source: `C:/dev/train-orchestrator/MORNING_BRIEFING.md`

| Artifact | Path | Release relevance |
|---|---|---|
| Morning sync note | `docs/ops/TRAIN_ORCHESTRATOR_MORNING_SYNC_2026-06-27.md` | Mirrors the train-orchestrator overnight results into the SCBE release queue. |
| Blended training corpus | `C:/dev/train-orchestrator/training/blended_corpus.jsonl` | 331 rows, 247 human + 84 verified AI, 74.6% human. Candidate proof fine-tune corpus after license review. |
| Train split | `C:/dev/train-orchestrator/training/blended_corpus.train.jsonl` | 298-row candidate training split. |
| Holdout split | `C:/dev/train-orchestrator/training/blended_corpus.holdout.jsonl` | 33-row held-out evaluation split. |
| FIM corpus | `C:/dev/train-orchestrator/training/blended_corpus_fim.jsonl` | 233 fill-in-the-middle occlusion rows. |
| Train orchestrator briefing | `C:/dev/train-orchestrator/MORNING_BRIEFING.md` | Source briefing for completed local overnight run. |

Release blockers:

- Confirm dataset/license suitability before shipping a model trained on MBPP/HumanEval-derived rows.
- Issac must provide `HF_TOKEN` for live dashboard data.
- Issac must create public HF OAuth app and provide `HF_OAUTH_CLIENT_ID` for device-code login.
- First real fine-tune remains approval-gated and should not run automatically.

Validation status:

- The train-orchestrator briefing claims local execution/build verification.
- This Codex sync pass did not rerun builds, tests, corpus generation, or training.

## Release manifest update - train-orchestrator Colab lane

| Artifact | Path | Release relevance |
|---|---|---|
| Colab backend helper | `C:/dev/train-orchestrator/colab_lane.py` | Generates the portable Colab notebook and zip package from local training artifacts. |
| Colab dashboard page | `C:/dev/train-orchestrator/dashboard/src/pages/Colab.tsx` | Adds a dashboard UI for downloading the notebook/package and opening Colab. |
| Colab route wiring | `C:/dev/train-orchestrator/dashboard/src/App.tsx` | Registers `/colab`. |
| Colab sidebar/nav wiring | `C:/dev/train-orchestrator/dashboard/src/components/Navbar.tsx` | Adds the Colab nav item. |
| Colab page title wiring | `C:/dev/train-orchestrator/dashboard/src/components/Layout.tsx` | Adds page title and breadcrumb. |
| Colab lane docs | `C:/dev/train-orchestrator/COLAB_LANE.md` | Explains usage and boundaries. |

Validation status:

- Not build-validated in this pass.
- Not run through Colab in this pass.
- No upload, training, paid compute, push, publish, or repeated polling was run.

## Release doctrine update - compile is the oven

Release status language now follows:

| Status | Meaning |
|---|---|
| `batter` | Code/spec exists but has not been compiled or run. |
| `baked` | Build/compile succeeded. |
| `served` | User-facing path was run and visible output worked. |
| `burnt` | Compile/run failed. |

Rule:

- Code changes without build/run evidence are `batter`.
- Build success is `baked`.
- Visible user workflow success is `served`.
- Release-ready requires at least `baked`, and user-facing products should reach `served`.

Doctrine file:

`docs/ops/COMPILE_IS_THE_OVEN_DOCTRINE_2026-06-27.md`
