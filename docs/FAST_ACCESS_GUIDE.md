# Fast Access Guide

This is the current local operator index for the live `SCBE-AETHERMOORE` stack.

Use this first when you want the fastest path to the right command or guide. Older docs under `docs/00-overview/` are still useful for public framing, but they are more demo-oriented than the current local workflow.

## Start Here

| Goal | Fastest command | Guide |
| --- | --- | --- |
| Load the local command center | `.\scripts\install_hydra_quick_aliases.ps1` then `issac-help` | [Control Plane And Command Center](guides/CONTROL_PLANE_AND_COMMAND_CENTER.md) |
| Check local system health | `hstatus` and `hqueue` | [Control Plane And Command Center](guides/CONTROL_PLANE_AND_COMMAND_CENTER.md) |
| Use the unified SCBE CLI | `python scripts/scbe-system-cli.py --help` | [Control Plane And Command Center](guides/CONTROL_PLANE_AND_COMMAND_CENTER.md) |
| Build a doctrine-backed swarm work packet | `python scripts/scbe-system-cli.py flow plan --task "..."` | [Action Map Protocol](guides/ACTION_MAP_PROTOCOL.md) |
| Run Sacred Tongues / GeoSeal tooling | `python six-tongues-cli.py` | [GeoSeal And Tongues](guides/GEOSEAL_AND_TONGUES.md) |
| Start the browser/operator lane | `npm run aetherbrowser:service:start` | [AetherBrowser And Operator Lane](guides/AETHERBROWSER_AND_OPERATOR_LANE.md) |
| Verify browser service health | `npm run aetherbrowser:service:verify` | [AetherBrowser And Operator Lane](guides/AETHERBROWSER_AND_OPERATOR_LANE.md) |
| Start the context broker | `python src/mcp/context_broker_mcp.py` | [Context Broker And Memory](guides/CONTEXT_BROKER_AND_MEMORY.md) |
| Run the Android hand / phone lane | `python scripts/system/hydra_android_control.py status` | [Polly Pads And Phone Lane](guides/POLLY_PADS_AND_PHONE_LANE.md) |
| Build or audit training data | `python -m src.training.auto_ledger` | [Training, Hugging Face, And Privacy](guides/TRAINING_HUGGINGFACE_AND_PRIVACY.md) |
| Run protected-corpus privacy prep | `python scripts/build_protected_corpus.py --help` | [Training, Hugging Face, And Privacy](guides/TRAINING_HUGGINGFACE_AND_PRIVACY.md) |
| Record end-to-end workflow telemetry | `haction-start <task>` then `haction-build <run_id>` | [Action Map Protocol](guides/ACTION_MAP_PROTOCOL.md) |
| Run verified cloud sync | `pwsh -File scripts/run_local_cloud_autosync.ps1 -Once` | [Storage, Offload, And Cloud Sync](guides/STORAGE_OFFLOAD_AND_CLOUD_SYNC.md) |
| Audit GitHub workflows | `python scripts/system/github_workflow_audit.py` | [GitHub And CI Operations](guides/GITHUB_AND_CI_OPERATIONS.md) |

## Core System

The live stack breaks into these layers:

1. `Control plane`: PowerShell command center, unified CLI, and npm script entrypoints.
2. `Governance kernel`: harmonic, governance, GeoSeal, Sacred Tongues, and trust scoring.
3. `Execution surfaces`: AetherBrowser, Polly Pads, phone lane, and agentic/fleet runtimes.
4. `Memory + routing`: Context Broker MCP and cross-talk/session state.
5. `Training + publishing`: nursery, protected corpus, auto-ledger, Hugging Face integration.
6. `Storage + operations`: verified offload, local cloud sync, GitHub workflow audit.

## Focused Guides

- [Core System Map](guides/CORE_SYSTEM_MAP.md)
- [Control Plane And Command Center](guides/CONTROL_PLANE_AND_COMMAND_CENTER.md)
- [GeoSeal And Tongues](guides/GEOSEAL_AND_TONGUES.md)
- [AetherBrowser And Operator Lane](guides/AETHERBROWSER_AND_OPERATOR_LANE.md)
- [Context Broker And Memory](guides/CONTEXT_BROKER_AND_MEMORY.md)
- [Polly Pads And Phone Lane](guides/POLLY_PADS_AND_PHONE_LANE.md)
- [Training, Hugging Face, And Privacy](guides/TRAINING_HUGGINGFACE_AND_PRIVACY.md)
- [Article Publishing System](guides/ARTICLE_PUBLISHING_SYSTEM.md)
- [Action Map Protocol](guides/ACTION_MAP_PROTOCOL.md)
- [Storage, Offload, And Cloud Sync](guides/STORAGE_OFFLOAD_AND_CLOUD_SYNC.md)
- [GitHub And CI Operations](guides/GITHUB_AND_CI_OPERATIONS.md)

## Rule Of Thumb

- Use `SCBE-AETHERMOORE` as the live integrated system.
- Treat side repos like `aetherbrowser`, `phdm-21d-embedding`, `six-tongues-geoseal`, and `spiralverse-protocol` as extracted module faces, not competing truths.
- Keep generated outputs under `artifacts/`, `training/`, and cloud/archive paths out of the active code mental model unless you are explicitly auditing runs.
