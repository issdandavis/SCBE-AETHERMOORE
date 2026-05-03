# SCBE-AETHERMOORE System Knowledge Map

Generated: 2026-05-02

Purpose: give humans and agents a compact map of where ideas live, where they have code, where they have training data, and where they are still notes-only or generated output. This is a routing document, not a replacement for source files.

## Working Model

The project moves through a repeatable spiral:

1. First-found facts and raw ideas land in the Obsidian notes vault.
2. Stable concepts get organized into repo docs, specs, or system-library snapshots.
3. Implementable concepts move into `src/`, `python/`, `api/`, `agents/`, or `scripts/`.
4. Training concepts become JSONL corpora, profile manifests, evaluation contracts, and gates.
5. Runs produce artifacts, logs, adapter pushes, and post-gate residue digests.
6. Useful residue gets folded back into the next training or implementation pass.

This means a concept can be real while still living at different maturity levels across the tree.

## Main Vaults And Note Surfaces

| Surface | Path | Role | Status |
|---|---|---|---|
| Repo-local Obsidian vault | `notes/` | Human and agent authored notes. Expansion field for theory, sessions, experiments, agent memory, sphere-grid training pairs, and system library snapshots. | Active source-of-context |
| Notes home | `notes/HOME.md` | Human-readable folder map for the vault. Separates user notes from auto-generated `System Library/`. | Active navigation root |
| Tokenizer vault | `notes/System Library/Tokenizer Vault/Tokenizer Vault Index.md` | Snapshot index for tokenizer, langues, atomic op features, adaptive routing, and spiral-ring adjacent surfaces. | Active reference snapshot |
| System library indexes | `notes/System Library/Indexes/` | Curated navigation around source roots, document channels, tokenizer references, and memory augmentation. | Active reference layer |
| Session notes | `notes/sessions/` | Operational summaries: what shipped, broke, changed. | Active but uneven |
| Theory notes | `notes/theory/` | Evergreen frameworks and math/system discoveries. | Active expansion layer |
| Raw note drops | `notes/Note drops/` and `notes/Messges Dumps_trainging files/` | Imported or raw conversation/context dumps. | Useful but noisy |
| Research bridge Obsidian exports | `training-data/research_bridge_smoke/**/sources/obsidian/` | Exported note snapshots used for research/training bridge tests. | Generated/exported; do not treat as primary vault |

## Repo Lanes

| Lane | Primary paths | What lives here | Status |
|---|---|---|---|
| TypeScript package surface | `package.json`, `src/index.ts`, `src/harmonic/`, `src/crypto/`, `src/governance/`, `src/tokenizer/`, `src/symphonic/` | npm package exports, governance math, crypto/tokenizer modules, TypeScript test surface. | Active implementation |
| Python control plane | `src/api/main.py`, `src/api/saas_routes.py`, `src/api/hydra_routes.py` | Newer MVP/control-plane lane with HYDRA and SaaS additions. | Active implementation |
| Older governance API | `api/main.py`, `api/persistence.py`, `api/metering.py` | Production-governance `/v1/*`, persistence, billing-adjacent and authorization flows. | Active/legacy split |
| Operator scripts | `scripts/` | The practical control plane: training dispatch, harness ops, storage labs, Kaggle/Hugging Face, release checks, browser and HYDRA commands. | Very active implementation |
| Agent communications | `src/agent_comms/`, `tests/agent_comms/`, `scripts/serve_geoseal_harness.py` | Harness providers, packet/pair endpoints, provider matrix, lane-change signaling. | Active implementation |
| Training data | `training-data/sft/`, `training-data/dpo/`, `config/model_training/` | JSONL corpora, manifests, profiles, evaluation contracts, promotion gates. | Active canonical corpus lane |
| Generated artifacts | `artifacts/`, `training/runs/`, `dist/` | Logs, reports, run outputs, build output, packaged artifacts. | Generated; inspect but do not treat as source |
| Public docs and launch material | `docs/`, `docs/business/`, `docs/readiness/`, `docs/specs/` | Architecture, readiness, product, proposal, and specification docs. | Mixed authority; verify against code |

## Major System Threads

| Thread | Notes/docs | Implementation | Training/gates | Current read |
|---|---|---|---|---|
| Sacred Tongues and tokenizer stack | `notes/System Library/Tokenizer Vault/Tokenizer Vault Index.md`, `docs/SACRED_TONGUES_TUTORIALS.md`, `docs/TONGUE_CODING_LANGUAGE_MAP.md` | `src/tokenizer/ss1.ts`, `src/crypto/sacred_tongues.py`, `src/crypto/code_lattice.py`, `src/crypto/polyglot_braid.py` | `training-data/sft/*`, `tests/test_code_lattice.py`, `tests/test_polyglot_braid.py` | Implemented in pieces; distributed canon, not one master file |
| Cross-lattice / polyglot braid | `notes/System Library/Tokenizer Vault/`, `docs/TONGUE_CODING_LANGUAGE_MAP.md` | `src/crypto/polyglot_braid.py`, `scripts/generate_polyglot_braid_sft.py` | `training-data/sft/polyglot_braid_sft.jsonl` if generated, `tests/test_polyglot_braid.py` | Active training generator and tests |
| Cross-stitch lattice / trichromatic governance | `notes/theory/`, related system-library snapshots | `scripts/trichromatic_governance_test.py`, `src/governance/trichromatic_governance.py` | `tests/test_trichromatic_governance.py`, `tests/test_trichromatic_integration.py`, `tests/test_scbe_system_trichromatic.py` | Implemented test/prototype surface |
| Dense data bundles and storage compaction | `notes/theory/`, storage notes, research bridge exports | `scripts/system/storage_compaction_lab.py`, `scripts/system/storage_bridge_lab.py`, `hydra/lattice25d_ops.py`, `hydra/octree_sphere_grid.py` | Storage lab artifacts under `artifacts/system_audit/` | Active experimental lab |
| GeoSeal harness and AI-to-AI lanes | `docs/CODING_SYSTEMS_MASTER_REFERENCE.md`, `docs/REPO_SURFACE_MAP.md` | `src/geoseal_cli.py`, `src/api/geoseal_cli_bridge.py`, `src/api/geoseal_service.py`, `src/agent_comms/`, `scripts/terminal/geoseal_harness_terminal.py`, `scripts/serve_geoseal_harness.py` | `tests/agent_comms/`, `tests/terminal/test_geoseal_harness_terminal.py`, `tests/benchmark/test_harness_provider_matrix.py`, `tests/benchmark/test_harness_research_matrix.py` | Active control-plane surface; now includes CLI routing, provider-pair signaling, analog actions, research benchmarks, and HTTP bridge routes |
| Stage 5 command harmony | `config/model_training/stage5_command_harmony_eval_contract.json` | `scripts/build_stage5_command_harmony_signal_shape_boost.py`, `scripts/system/dispatch_coding_agent_hf_job.py` | `training-data/sft/stage5_command_harmony_signal_shape_boost_*.jsonl`, `tests/test_build_stage5_command_harmony_signal_shape_boost.py` | Passed scaffolded gate and pushed adapter |
| Stage 6 atomic workflow | `config/model_training/stage6_atomic_workflow_eval_contract.json` | `scripts/build_stage6_*.py`, `src/governance/stage6_constrained_decoding.py`, `scripts/eval/score_stage6_constrained_decoding.py` | Stage 6 SFT/DPO profiles and tests under `tests/test_stage6_constrained_decoding.py` and `tests/governance/` | Active gate and constrained scaffold lane |
| Post-gate residue digestion | This document plus run artifacts | `scripts/eval/digest_agentic_training_run.py` | `tests/eval/test_digest_agentic_training_run.py`, `artifacts/training_digestion/` | Newly implemented; turns gate logs into compact residue chains |
| Parallelism and scheduler experiments | `config/parallelism/README.md` if present | `scripts/system/parallelism_system.py` | Run reports under `artifacts/parallelism_system/` | Present but still early; dirty/uncommitted at last scan |
| Release readiness | `docs/readiness/`, `package.json`, `scripts/ci/harness_release_readiness.py` | npm and PyPI publish scripts in `package.json`, `scripts/npm_*`, `scripts/pypi_*` | `tests/ci/test_harness_release_readiness.py`, release readiness scripts | Active but requires cleanup before publish |

## Current GeoSeal Surface

GeoSeal has expanded beyond the earlier packet transport layer. Treat it as a local-first command, harness, and bridge control plane.

| Route family | CLI commands / paths | Current role |
|---|---|---|
| Transport and tokenizer | `encode-cmd`, `decode-cmd`, `xlate-cmd`, `binary-to-tokenizer`, `atomic`, `seal`, `verify` | Deterministic command/token transport, decoding, atomic representation, and verification. |
| Coding packets | `code-packet`, `reasoning-code-packet`, `code-roundtrip`, `testing-cli`, `project-scaffold` | Bijective coding packets, reasoning/code trace packaging, round-trip validation, and scaffold tests. |
| Graph and topology | `packet-graph-run`, `interaction-graph`, `topology-view`, `cross-domain-sequence`, `honeycomb-analysis`, `cognition-map`, `cluster-graph`, `formation-graph` | Agentic route graphs, topology views, cognition maps, and multi-domain sequence traces. |
| Handoff and agent communications | `handoff-seal`, `handoff-open`, `agent-harness`, `harness-terminal`, `harness-research`, `terminus-training` | Small-context handoff packets, AI-to-AI harness manifests, provider-pair lane changes, and benchmark/training routes. |
| Operation and replay | `ops`, `emit`, `run`, `swarm`, `shell`, `history`, `replay`, `workflow` | Operator-facing execution wrappers, replayable trajectories, swarm routing, and workflow control. |
| Product and runtime surfaces | `portal-box`, `stream-wheel`, `mars-mission`, `agent`, `arc`, `cursor` | Demo/runtime/product routes and tool integrations that sit on top of GeoSeal transport. |

The current `harness-terminal` surface reports 19 provider definitions and a provider-pair signal format of:

```text
provider-pair:<left-provider>-><right-provider>:<reason>
```

It also exposes six analog action primitives:

```text
observe-room, move-lane, inspect-object, solve-checkpoint, verify-evidence, reset-run
```

The current research benchmark families are:

```text
terminal_bench, swe_bench, coding_agent_cli, codex_style_handoff, scbe_agentic_ladder,
terminal_game_training, m4_mesh, hydra_swarm, kaggle_remote_compute
```

HTTP bridge paths are split between:

| Bridge file | Routes |
|---|---|
| `src/api/geoseal_cli_bridge.py` | Curated in-process dispatch to GeoSeal handlers such as `code-packet`, `reasoning-code-packet`, `packet-graph-run`, `backend-registry`, `agent-harness`, `history`, `replay`, `testing-cli`, and `project-scaffold`. |
| `src/api/geoseal_service.py` | `/v1/geoseal/{command}`, `/v1/harness/tool-bridge`, `/v1/harness/agent-harness`, `/v1/polly/portal-box`, `/v1/polly/stream-wheel`, and `/v1/chat`. |

Focused GeoSeal validation lives in:

```text
tests/agent_comms/
tests/terminal/test_geoseal_harness_terminal.py
tests/benchmark/test_harness_provider_matrix.py
tests/benchmark/test_harness_research_matrix.py
tests/benchmark/test_harness_live_smoke.py
tests/ci/test_harness_release_readiness.py
```

## Canonical Versus Noisy

Use this split when deciding what to trust:

| Class | Trust level | Examples |
|---|---|---|
| Live implementation | Highest for behavior | `src/`, `api/`, `python/`, `agents/`, selected `scripts/` |
| Tests and gates | Highest for proven behavior | `tests/`, `config/model_training/*eval_contract.json`, `scripts/ci/harness_release_readiness.py` |
| Canonical docs/specs | High for intent and architecture | `docs/specs/`, `docs/CANONICAL_SYSTEM_STATE.md`, `docs/REPO_SURFACE_MAP.md`, this file |
| Obsidian notes | High for origin and design history | `notes/`, especially `notes/HOME.md`, `notes/theory/`, `notes/System Library/` |
| Training corpora | High for training payloads, not always source truth | `training-data/sft/`, `training-data/dpo/` |
| Artifacts and exports | Evidence/output, not source | `artifacts/`, `training/runs/`, `training-data/research_bridge_smoke/` |
| Raw dumps | Context only until curated | `notes/Note drops/`, message dumps, external AI exports |

## Next Best Indexing Passes

1. Build a machine-readable companion file for this map: `docs/system_knowledge_map.json`.
2. Add a small scanner that tags each major concept as `notes-only`, `docs-backed`, `implemented`, `tested`, `trained`, or `released`.
3. Link recent successful training runs into the map: Stage 5 scaffolded adapter, Stage 6 constrained scaffold, Kaggle approval metrics.
4. Keep Obsidian vault edits read-only unless explicitly requested; export curated subsets into repo-controlled staging folders when needed.
5. Add a release-clean surface that separates source files from generated artifacts before npm/PyPI/package publication.

## Fast Commands

```powershell
# Find current vaults
python scripts/list_obsidian_vaults.py

# Search notes and docs for a concept
rg -n "cross-stitch|dense bundle|atomic tokenizer|command harmony" notes docs src scripts config tests

# Check training profiles and gates
python scripts/system/geoseal_coding_training_system.py list --json

# Run Stage 5/6 related focused tests
python -m pytest tests/test_geoseal_coding_training_system.py tests/test_stage6_constrained_decoding.py tests/eval/test_digest_agentic_training_run.py -q

# Inspect package/release readiness
python scripts/ci/harness_release_readiness.py
```
