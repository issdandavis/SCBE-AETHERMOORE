# Core System Map

This guide identifies the core runtime surfaces in `SCBE-AETHERMOORE` and how they are meant to work together.

## Canonical Rule

`SCBE-AETHERMOORE` is the live integration repo. Side repos are extracted lanes or support lanes. Archive snapshots and generated artifacts are not part of the active control surface.

## Core Components

| Lane | Purpose | Main files |
| --- | --- | --- |
| Control plane | Local operator shell, unified CLI, npm entrypoints | `scripts/scbe-system-cli.py`, `scripts/scbe_terminal_ops.py`, `scripts/hydra_command_center.ps1`, `package.json` |
| Governance kernel | 14-layer scoring, trust, drift, decisioning | `src/harmonic/`, `src/governance/`, `src/geoseal.ts`, `CLAUDE.md` |
| Sacred Tongues + GeoSeal | Tokenization, sealing, translation, trust identity | `six-tongues-cli.py`, `src/aaoe/agent_identity.py`, `src/geoseal.ts` |
| Browser/operator lane | Search, provider routing, extension service, operator browser tasks | `src/aetherbrowser/`, `src/browser/`, `scripts/system/aetherbrowser_*.py`, `scripts/verify_aetherbrowser_extension_service.py` |
| Memory + routing | Session continuity, tongue classification, hot/deep memory | `src/mcp/context_broker_mcp.py`, `notes/round-table/`, `notes/_inbox.md` |
| Polly Pads + phone lane | Governed workspaces, Android hand, mobile reading/execution | `src/fleet/polly-pad-runtime.ts`, `src/browser/hydra_android_hand.py`, `scripts/system/hydra_android_control.py` |
| Training + HF | SFT/DPO generation, ledgering, evaluation, publishing | `training/cstm_nursery.py`, `src/training/auto_ledger.py`, `src/integrations/huggingface.ts`, `scripts/build_*`, `notebooks/` |
| Storage + offload | Verified cloud sync, offload, state manifests | `scripts/multi_agent_offload.py`, `scripts/run_local_cloud_autosync.ps1`, `training/local_cloud_sync.json`, `docs/LOCAL_CLOUD_AUTOSYNC.md` |
| GitHub + CI ops | Workflow audit, PR/check visibility, repo health | `scripts/system/github_workflow_audit.py`, `.github/workflows/` |

## Intended Flow

1. A task enters through the command center, system CLI, browser lane, or phone lane.
2. Sacred Tongues and context routing decide the task domain and trust posture.
3. GeoSeal and the governance kernel score the task for execution safety.
4. AetherBrowser, Polly Pads, or agentic/fleet modules execute the work.
5. Cross-talk, MCP memory, and notes capture continuity.
6. Useful outputs become training records, protected corpora, or HF artifacts.
7. GitHub and cloud sync preserve code, manifests, and verified run outputs.

## Repo Portfolio Role

These GitHub repos are best understood as module faces of the main system:

- `aetherbrowser`: extracted browser/runtime lane
- `hyperbolica`: math primitives lane
- `phdm-21d-embedding`: embedding and model/data research lane
- `six-tongues-geoseal`: tokenizer/crypto extraction lane
- `spiralverse-protocol`: protocol/AI-to-AI lane
- `scbe-security-gate`: security hardening lane

These are not supposed to replace the monorepo. They are supposed to present cleaner slices of it.

## Ownership Rule

- `src/`, `tests/`, `docs/`, and `scripts/` are the main code and ops surfaces.
- `artifacts/`, `training/`, cloud sync bundles, and run folders are outputs.
- Snapshot trees like `SCBE-AETHERMOORE-v3.0.0/` and vendored material under `external/` should be treated as archive or reference.
