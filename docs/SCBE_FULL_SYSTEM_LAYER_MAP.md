# SCBE Full System Layer Map (Kernel -> AI -> Swarm -> Cloud -> Training)

Last updated: 2026-02-17

## Scope

This map consolidates the current SCBE ecosystem across core repositories under `issdandavis` and documents what is implemented, partial, or conceptual.

## Layer Stack (authoritative operational view)

### Layer 0: Canonical Kernel Contract
- Purpose: protocol authority and term discipline.
- Status: implemented.
- Primary repo: `SCBE-AETHERMOORE`.
- Source surfaces:
1. `SPEC.md`
2. `CONCEPTS.md`

### Layer 1: SCBE Governance Runtime (14-layer core)
- Purpose: deterministic ALLOW/QUARANTINE/DENY decisions.
- Status: implemented.
- Primary repo: `SCBE-AETHERMOORE`.
- Source surfaces:
1. `api/main.py`
2. `README.md`
3. `ARCHITECTURE.md`
4. `docs/hydra/ARCHITECTURE.md` (SCBE as Layer 1 in HYDRA stack)

### Layer 2: GeoSeal / Mixed-Curvature Access Kernel
- Purpose: geometric trust fusion and quarantine/memory-write gating.
- Status: implemented (v2 primitives present).
- Primary repo: `SCBE-AETHERMOORE`.
- Source surfaces:
1. `src/geoseal.py`
2. `src/geoseal_v2.py`
3. `tests/test_geoseal.py`
4. `tests/test_geoseal_v2.py`

### Layer 3: Single-Agent Browser Execution Plane (AetherBrowse)
- Purpose: governed browser execution with containment checks.
- Status: implemented (branch-integrated operational tooling).
- Primary repo: `SCBE-AETHERMOORE`.
- Source surfaces:
1. `agents/browser/main.py`
2. `agents/aetherbrowse_cli.py`
3. `docs/AETHERBROWSE_GOVERNANCE.md`

### Layer 4: Multi-Agent Browser/Task Execution (Swarm Runner)
- Purpose: run 2-5+ governed jobs with verification and per-job decision records.
- Status: implemented.
- Primary repo: `SCBE-AETHERMOORE`.
- Source surfaces:
1. `scripts/aetherbrowse_swarm_runner.py`
2. `examples/aetherbrowse_tasks.sample.json`
3. `schemas/decision_record.schema.json`

### Layer 5: HYDRA Coordination + Governed Swarm
- Purpose: head/limb/librarian/ledger orchestration above SCBE kernel.
- Status: partial (reference architecture documented; runtime pieces distributed).
- Primary repo: `SCBE-AETHERMOORE`.
- Source surfaces:
1. `docs/hydra/ARCHITECTURE.md`
2. `agents/swarm_browser.py`
3. `training/doc_manifest.json` (roundtable-style verification metadata)

### Layer 6: Workflow Orchestration Connectors (Asana + n8n)
- Purpose: scheduled external tasks -> governed browser actions -> feedback loop.
- Status: implemented.
- Primary repo: `SCBE-AETHERMOORE`.
- Source surfaces:
1. `scripts/asana_aetherbrowse_orchestrator.py`
2. `scripts/n8n_aetherbrowse_bridge.py`
3. `workflows/n8n/asana_aetherbrowse_scheduler.workflow.json`
4. `docs/ASANA_AETHERBROWSE_AUTOMATION.md`
5. `docs/N8N_AETHERBROWSE_INTEGRATION.md`

### Layer 7: Cloud Execution Plane
- Purpose: remote headless execution for low-spec local machines.
- Status: implemented.
- Primary repo: `SCBE-AETHERMOORE`.
- Source surfaces:
1. `deploy/gcloud/deploy_aetherbrowse.sh`
2. `deploy/gcloud/Dockerfile.aetherbrowse`
3. `docs/AETHERBROWSE_CLOUD_RUN.md`

### Layer 8: Data/Training Plane (Notion -> JSONL -> HF -> Vertex)
- Purpose: convert system knowledge and operation traces into trainable datasets/models.
- Status: implemented (with secrets/config dependency).
- Primary repos: `SCBE-AETHERMOORE`, `phdm-21d-embedding`.
- Source surfaces:
1. `scripts/notion_access_check.py`
2. `scripts/notion_to_dataset.py`
3. `scripts/push_to_hf.py`
4. `.github/workflows/notion-to-dataset.yml`
5. `.github/workflows/huggingface-sync.yml`
6. `.github/workflows/vertex-training.yml`
7. `phdm-21d-embedding/scripts/markdown_to_jsonl.py`
8. `phdm-21d-embedding/scripts/push_jsonl_dataset.py`

### Layer 9: Ecosystem/Protocol Extensions (Spiralverse + Security Gate)
- Purpose: AI-to-AI protocol + hardened gate modules.
- Status: implemented as satellite repos.
- Primary repos: `spiralverse-protocol`, `scbe-security-gate`.
- Source surfaces:
1. `spiralverse-protocol/README.md`
2. `scbe-security-gate/README.md`

### Layer 10: Space Station / Agentic Swarm Factory Narrative Plane
- Purpose: mission-control metaphor and orbital governance framing.
- Status: conceptual + documentation heavy (not yet full runtime layer).
- Primary repo: `scbe-aethermoore-demo`.
- Source surfaces:
1. `scbe-aethermoore-demo/L1_AETHERMOORE_STATION.md`

## Core Repository Roles

| Repo | Role in stack | Current role |
| --- | --- | --- |
| `SCBE-AETHERMOORE` | canonical kernel + ops plane | primary production repo |
| `phdm-21d-embedding` | training data conversion + HF push | data pipeline utility |
| `aws-lambda-simple-web-app` | mirrored SCBE docs/spec package | secondary source; consolidate selectively |
| `Entropicdefenseengineproposal` | proposal/prototype surfaces | extract unique docs and merge to canonical |
| `spiralverse-protocol` | AI-to-AI protocol extension | keep as module repo |
| `scbe-security-gate` | standalone gate hardening | keep as module repo |
| `scbe-aethermoore-demo` | narrative/demo shell | keep for demos; avoid canonical drift |

## Readiness by objective

| Objective | Status | Notes |
| --- | --- | --- |
| Governed single-agent execution | ready | AetherBrowse + containment checks available |
| Governed multi-job automation | ready | swarm runner + verification + decision records |
| Asana scheduled automation | ready | orchestration script + n8n workflow available |
| Cloud browser operations | ready | Cloud Run deploy artifacts present |
| Notion -> HF dataset flow | ready with config | requires `NOTION_API_KEY` and `HF_TOKEN` secrets |
| Vertex/GKE model training handoff | ready with config | requires `GCP_SA_KEY` and project configuration |
| Full space-station swarm factory runtime | partial | conceptual framing exists; needs mission runtime implementation |

## Highest-value next consolidation actions

1. Declare `SCBE-AETHERMOORE` as sole canonical runtime and spec authority.
2. Import only unique docs/code from satellite repos; do not duplicate whole trees.
3. Promote AetherBrowse + Asana orchestration from feature branch into mainline release.
4. Add one mission-runtime package (`mission_control/`) that operationalizes Layer 10 concepts into runnable workflows.

## Known drift to control

1. Formula notation drift across docs (`H(d,R)` variants) needs one canonical expression policy.
2. Duplicate architecture prose across repos increases training inconsistency.
3. Secret-dependent workflows fail silently if GitHub secrets are absent.

