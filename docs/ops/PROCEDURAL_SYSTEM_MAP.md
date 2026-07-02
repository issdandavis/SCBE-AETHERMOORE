# SCBE Procedural System Map

Generated: `2026-07-02T07:09:23+00:00`
Source: `scripts/system/procedural_system_map.py`
Seed file: `config/system/procedural_system_map_seeds.json`
World digest: `3739291f637ad6bc7b77efe983f655de26091ffb8e0b7727aeab7d95941d7397`

This file is generated from tracked seeds plus live repo files. Edit the seed file, not this output.

## World Summary

| Region | Biome | Health | Cells | Tests | Docs | Missing | Chunk |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| Core Entry Package Mesa | `runtime` | `verified` | 30 | 26 | 2 | 0 | `557,-1884` |
| Harmonic Crypto Governance Range | `core-runtime` | `truncated` | 220 | 65 | 0 | 0 | `1884,1568` |
| Tokenizer Python Substrate Caverns | `substrate` | `verified` | 137 | 6 | 1 | 0 | `1065,-1596` |
| Compiler And Polyglot Brick Ridge | `compiler` | `verified` | 20 | 9 | 2 | 0 | `1076,1756` |
| AetherDesk Portable PC Basin | `portable-ui` | `verified` | 12 | 1 | 10 | 0 | `1390,-537` |
| Local Agent Bus Forest | `operator` | `truncated` | 160 | 39 | 14 | 0 | `716,232` |
| System Ops Control Plateau | `operator` | `truncated` | 240 | 42 | 0 | 0 | `199,-396` |
| API Control Plane Delta | `service` | `verified` | 62 | 16 | 0 | 0 | `-1138,1988` |
| Training Builder Farm | `training` | `verified` | 83 | 15 | 6 | 0 | `155,-1015` |
| Eval Benchmark Farm | `benchmark` | `verified` | 198 | 55 | 0 | 0 | `-511,1113` |
| Docs Ops Specs Map Room | `map-room` | `review` | 126 | 2 | 124 | 0 | `-1365,-851` |
| Docs Research Notes Map Room | `research` | `review` | 93 | 0 | 93 | 0 | `-1041,943` |
| Artifacts Generated Quarantine | `generated` | `noisy` | 120 | 0 | 26 | 0 | `-886,1825` |
| Dist Build Output Quarantine | `generated` | `noisy` | 120 | 0 | 0 | 0 | `-1120,-1992` |
| Training Data Quarantine | `generated` | `noisy` | 14 | 0 | 0 | 0 | `-1922,-1212` |

## Regions

### Core Entry Package Mesa (`core-entry-package`)

- Biome: `runtime`
- Health: `verified`
- Chunk coordinate: `557,-1884`
- Purpose: Top-level package and public entry surfaces that define what SCBE exports first.
- Tags: `runtime`, `core`, `package`, `entrypoint`
- Roots: `package.json`, `src/index.ts`, `README.md`, `docs/SCBE_FULL_SYSTEM_MAP.md`, `tests/cli`, `tests/test_scbe_cli_bit_spine.py`
- Roles: `{"config": 1, "doc": 2, "runtime": 1, "test": 26}`
- Kinds: `{"code": 27, "config": 1, "doc": 2}`

Primary cells:
- `README.md` (doc/doc, `d963436fed1c196d`)
- `docs/SCBE_FULL_SYSTEM_MAP.md` (doc/doc, `c9ca079fc75060ea`)
- `package.json` (config/config, `87d73d5b5096d37d`)
- `src/index.ts` (runtime/code, `34060dcc67fcc5b0`)
- `tests/cli/__init__.py` (test/code, `60e860e9d152724f`)
- `tests/cli/test_alias_registry.py` (test/code, `f05727093c966dea`)
- `tests/cli/test_alias_registry_harsh.py` (test/code, `91870182e79e7ecd`)
- `tests/cli/test_and_allow_cascade.py` (test/code, `108b0274eb1d61fe`)
- `tests/cli/test_cascade_router.py` (test/code, `901ca5a78e2dd513`)
- `tests/cli/test_coding_intent_gate.py` (test/code, `f6e830c08cb2c7d8`)
- `tests/cli/test_command_trace.py` (test/code, `6fc45cfa18455a75`)
- `tests/cli/test_cross_build_cli.py` (test/code, `1f2e0f6d94cb7e7f`)
- ... 18 more cells in generated JSON

### Harmonic Crypto Governance Range (`harmonic-crypto-governance`)

- Biome: `core-runtime`
- Health: `truncated`
- Chunk coordinate: `1884,1568`
- Purpose: The 14-layer governance, harmonic, crypto, and exported policy logic.
- Tags: `runtime`, `core`, `governance`, `crypto`, `harmonic`
- Roots: `src/harmonic`, `src/crypto`, `src/governance`, `tests/harmonic`, `tests/crypto`, `tests/governance`
- Scan note: `truncated`
- Roles: `{"runtime": 155, "test": 65}`
- Kinds: `{"code": 220}`

Primary cells:
- `src/harmonic/__init__.py` (runtime/code, `2adf37b0b28c5cf6`)
- `src/harmonic/adaptiveNavigator.ts` (runtime/code, `5c5c5e0a53bc54e4`)
- `src/harmonic/assertions.ts` (runtime/code, `c4e21a46ae6df5ac`)
- `src/harmonic/audioAxis.ts` (runtime/code, `37b33ca27b3ad2dd`)
- `src/harmonic/balancedTernary.ts` (runtime/code, `9aa77d11c103b59f`)
- `src/harmonic/chsfn.ts` (runtime/code, `52b34b6b60cb27b8`)
- `src/harmonic/compute_ds_squared.py` (runtime/code, `c4809f4d0717827d`)
- `src/harmonic/constants.ts` (runtime/code, `9bad8c9bbc0c6416`)
- `src/harmonic/contact_lattice.py` (runtime/code, `920dadea735d0eea`)
- `src/harmonic/context_encoder.py` (runtime/code, `a10dbb255b9f2942`)
- `src/harmonic/driftTracker.ts` (runtime/code, `9e036daa7485303f`)
- `src/harmonic/encryptedTransport.ts` (runtime/code, `342ecb4bc7afbb1f`)
- ... 208 more cells in generated JSON

### Tokenizer Python Substrate Caverns (`tokenizer-python-substrate`)

- Biome: `substrate`
- Health: `verified`
- Chunk coordinate: `1065,-1596`
- Purpose: Tokenizer, Sacred Tongue, chemistry, bit spine, and Python substrate surfaces.
- Tags: `runtime`, `tokenizer`, `substrate`, `tongues`, `chemistry`
- Roots: `src/tokenizer`, `python/scbe`, `tests/conlang`, `tests/encoding`, `tests/test_scbe_cli_bit_spine.py`
- Roles: `{"config": 1, "doc": 1, "runtime": 129, "test": 6}`
- Kinds: `{"code": 135, "config": 1, "doc": 1}`

Primary cells:
- `python/scbe/__init__.py` (runtime/code, `b0bbd4020aaa3d63`)
- `python/scbe/aether_braid.py` (runtime/code, `78d9dee542d3e17e`)
- `python/scbe/ast_cube_encoder.py` (runtime/code, `05bd4da15cb9da86`)
- `python/scbe/ast_cube_rust.py` (runtime/code, `a9421e458b805b7d`)
- `python/scbe/atomic_tokenization.py` (runtime/code, `4cd1852a5ea236d4`)
- `python/scbe/audio_field_observables.py` (runtime/code, `412e5b1949315238`)
- `python/scbe/bicameral.py` (runtime/code, `268f5236f78531dc`)
- `python/scbe/bijective_dna.py` (runtime/code, `a8810c0325f0f8a3`)
- `python/scbe/bijective_double_hash_map.py` (runtime/code, `2631fdbe3626a1a7`)
- `python/scbe/bit_spine.py` (runtime/code, `5564cf006628ce6c`)
- `python/scbe/blocks.py` (runtime/code, `0c94829fd3c63813`)
- `python/scbe/board.py` (runtime/code, `06a90a52d23c9563`)
- ... 125 more cells in generated JSON

### Compiler And Polyglot Brick Ridge (`compiler-polyglot-bricks`)

- Biome: `compiler`
- Health: `verified`
- Chunk coordinate: `1076,1756`
- Purpose: CA opcode compiler, polyglot emitters, conformance checks, and mixed-expression staging lanes for multi-language code bricks.
- Tags: `compiler`, `polyglot`, `coding-bricks`, `conformance`, `go`
- Roots: `python/scbe/tongue_isa.py`, `python/scbe/polyglot.py`, `python/scbe/polyglot_conformance.py`, `python/scbe/toolkit.py`, `scripts/agents/scbe_code.py`, `scripts/system/run_scbe_compiler_lane.py`, `scripts/system/mixed_expression_lane.py`, `scripts/training/build_language_systems_atlas.py`, `scripts/training/build_code_coordination_graph.py`, `docs/TONGUE_CODING_LANGUAGE_MAP.md`, `docs/ops/GO_CONLANG_LANE_STATUS.md`, `tests/agents`, `tests/test_polyglot.py`, `tests/test_polyglot_conformance.py`, `tests/test_polyglot_portable.py`
- Roles: `{"doc": 2, "operator": 5, "runtime": 4, "test": 9}`
- Kinds: `{"code": 18, "doc": 2}`

Primary cells:
- `docs/TONGUE_CODING_LANGUAGE_MAP.md` (doc/doc, `fe41c5ed5d60aace`)
- `docs/ops/GO_CONLANG_LANE_STATUS.md` (doc/doc, `b16108d60fbfb15d`)
- `python/scbe/polyglot.py` (runtime/code, `c378bbced9a11a09`)
- `python/scbe/polyglot_conformance.py` (runtime/code, `068f170b9602be76`)
- `python/scbe/tongue_isa.py` (runtime/code, `7042990d008cc18f`)
- `python/scbe/toolkit.py` (runtime/code, `cf9f8b928e302aae`)
- `scripts/agents/scbe_code.py` (operator/code, `37179d153a6c65f6`)
- `scripts/system/mixed_expression_lane.py` (operator/code, `bb16de43492e8164`)
- `scripts/system/run_scbe_compiler_lane.py` (operator/code, `2665e5051b26f4d1`)
- `scripts/training/build_code_coordination_graph.py` (operator/code, `179d95ec416e1096`)
- `scripts/training/build_language_systems_atlas.py` (operator/code, `ad1e1fc0df02cb3f`)
- `tests/agents/__init__.py` (test/code, `60e860e9d152724f`)
- ... 8 more cells in generated JSON

### AetherDesk Portable PC Basin (`aetherdesk-portable-pc`)

- Biome: `portable-ui`
- Health: `verified`
- Chunk coordinate: `1390,-537`
- Purpose: Local web desktop, bounded shell profiles, touch/voice/text control surfaces, receipts, and remote-device bridge work.
- Tags: `aetherdesk`, `portable`, `ui`, `operator`, `receipts`
- Roots: `aetherdesk/server.js`, `aetherdesk/public`, `tests/aetherdesk`, `docs/ops`, `docs/specs`
- Roles: `{"doc": 10, "runtime": 1, "test": 1}`
- Kinds: `{"code": 2, "config": 1, "doc": 9}`

Primary cells:
- `aetherdesk/public/forge.html` (doc/doc, `f59ecdcb8c5c590a`)
- `aetherdesk/public/index.html` (doc/doc, `50cc9cc421495567`)
- `aetherdesk/public/worktree-garden.html` (doc/doc, `73589a5343e5af86`)
- `aetherdesk/server.js` (runtime/code, `d4b4bda3470bae72`)
- `docs/ops/AETHERDESK_BROWSER_AGENT.md` (doc/doc, `1bceab5cd4d51acf`)
- `docs/specs/AETHERDESK_ACADEMY_MVP.md` (doc/doc, `d91968eb576efc27`)
- `docs/specs/AETHERDESK_BROWSER_ACTION_PACKET.md` (doc/doc, `d7c2d3685d7f86c6`)
- `docs/specs/AETHERDESK_LONG_FORM_WORKFLOW.md` (doc/doc, `85141c49606a7125`)
- `docs/specs/AETHERDESK_OPERATOR_SHELL_v0.md` (doc/doc, `b04e4e09c271292d`)
- `docs/specs/AETHERDESK_SKILL_MANIFEST_SCHEMA.md` (doc/doc, `6950d8b0c319beeb`)
- `docs/specs/spiralverse_canonical_registry.v1.json` (doc/config, `77512d41ce7631bd`)
- `tests/aetherdesk/server.test.ts` (test/code, `7ec162a1236ba3a1`)

### Local Agent Bus Forest (`local-agent-bus`)

- Biome: `operator`
- Health: `truncated`
- Chunk coordinate: `716,232`
- Purpose: Local agent implementations, Node/Python agent-bus packages, receipts, and operator-facing work routing.
- Tags: `agents`, `operator`, `receipts`, `bus`
- Roots: `tests/agent`, `tests/agent-bus`, `tests/agents`, `packages/agent-bus`, `packages/agent-bus-py`, `agents`
- Scan note: `truncated`
- Roles: `{"config": 4, "doc": 14, "generated": 50, "operator": 19, "runtime": 34, "test": 39}`
- Kinds: `{"code": 142, "config": 8, "doc": 10}`

Primary cells:
- `tests/agent/agent.property.test.ts` (test/code, `fcbffa27203d4c02`)
- `tests/agent/customer_support_triage.test.ts` (test/code, `362fdfc9c7493dc1`)
- `tests/agent/hyperbolic-weakness.test.ts` (test/code, `23226399d205014c`)
- `tests/agent-bus/workspace.test.ts` (test/code, `a1e8098ddce17022`)
- `tests/agents/__init__.py` (test/code, `60e860e9d152724f`)
- `tests/agents/conftest.py` (test/code, `b434874ed755b7cc`)
- `tests/agents/test_agent_bus_cost.py` (test/code, `277edb17e095d8d3`)
- `tests/agents/test_agent_bus_schema.py` (test/code, `803f357e15c1e53f`)
- `tests/agents/test_kernel_antivirus_gate_capillary.py` (test/code, `ea5279aed845a3f9`)
- `tests/agents/test_scbe_code.py` (test/code, `8ec66b8058c540c9`)
- `packages/agent-bus/CHANGELOG.md` (doc/doc, `945fbd0101a3a4c5`)
- `packages/agent-bus/LICENSE-NOTICE.md` (doc/doc, `aadb46cee8933d46`)
- ... 148 more cells in generated JSON

### System Ops Control Plateau (`system-ops-control`)

- Biome: `operator`
- Health: `truncated`
- Chunk coordinate: `199,-396`
- Purpose: Operational scripts, MCP/terminal control, safe shell lanes, and system configuration surfaces.
- Tags: `operator`, `mcp`, `shell`, `config`, `receipts`
- Roots: `tests/system`, `tests/operator`, `tests/mcp`, `scripts/system`, `config/system`, `config/governance`
- Scan note: `truncated`
- Roles: `{"operator": 198, "test": 42}`
- Kinds: `{"code": 240}`

Primary cells:
- `tests/system/aetherbrowser_mcp_server.test.ts` (test/code, `866fdc825fde3285`)
- `tests/system/playwright_crosstalk_runner.test.ts` (test/code, `4129f2bb2ed8d2d1`)
- `tests/system/test_aethermon_training_arena.py` (test/code, `754cbff75035a6cb`)
- `tests/system/test_agent_bus_workspace_cli.py` (test/code, `a4540f2e2c614999`)
- `tests/system/test_agent_move_packet.py` (test/code, `a0ac80296600984f`)
- `tests/system/test_agent_shell.py` (test/code, `3fb85cc9960091a6`)
- `tests/system/test_agent_workcell_demo.py` (test/code, `c016994408e18d9e`)
- `tests/system/test_agentic_pazaak_board.py` (test/code, `1536eaf2fb28687a`)
- `tests/system/test_bookforge_publishing_company.py` (test/code, `26a896be5161ed5d`)
- `tests/system/test_build_aethermon_agent_adapter_v0.py` (test/code, `29c139a29b3ec3d0`)
- `tests/system/test_build_black_box_download.py` (test/code, `9e58c060d821759f`)
- `tests/system/test_build_cleanup_training_dataset.py` (test/code, `ee3498dfcd61f9f6`)
- ... 228 more cells in generated JSON

### API Control Plane Delta (`api-control-plane`)

- Biome: `service`
- Health: `verified`
- Chunk coordinate: `-1138,1988`
- Purpose: Older governance API plus newer Python MVP/control-plane service lane.
- Tags: `api`, `service`, `control-plane`, `governance`
- Roots: `api`, `src/api`, `tests/api`
- Roles: `{"runtime": 46, "test": 16}`
- Kinds: `{"code": 62}`

Primary cells:
- `api/__init__.py` (runtime/code, `4b24a9ad05a9f56d`)
- `api/audit_export.py` (runtime/code, `73ab2083ca4f832d`)
- `api/auth.py` (runtime/code, `b219329ac5f9df00`)
- `api/billing/__init__.py` (runtime/code, `0d4b73e4300385eb`)
- `api/billing/database.py` (runtime/code, `ac81c1ad4b3e4269`)
- `api/billing/routes.py` (runtime/code, `32892f005315e66b`)
- `api/billing/stripe_client.py` (runtime/code, `5da36f1fabcb65ac`)
- `api/billing/tiers.py` (runtime/code, `e574a633a323322a`)
- `api/billing/webhooks.py` (runtime/code, `7d1c7f34088cd22f`)
- `api/darpa_prep/__init__.py` (runtime/code, `e000d49d3a7b83d4`)
- `api/darpa_prep/client.py` (runtime/code, `48e4d8049aa67299`)
- `api/darpa_prep/darpa_portal.py` (runtime/code, `8d1cf415b9070219`)
- ... 50 more cells in generated JSON

### Training Builder Farm (`training-builders`)

- Biome: `training`
- Health: `verified`
- Chunk coordinate: `155,-1015`
- Purpose: Dataset builders, model manifests, coding-system corpus tools, and local training launchers.
- Tags: `training`, `models`, `dataset`, `coding`
- Roots: `scripts/system/build_aethermon_agent_adapter_v0.py`, `scripts/system/eval_aethermon_agent_adapter_v0.py`, `config/model_training/aethermon-agent-adapter-v0-local.json`, `training-data/sft/aethermon_agent_adapter_v0.manifest.json`, `training-data/sft/aethermon_agent_adapter_v0_train.sft.jsonl`, `training-data/sft/aethermon_agent_adapter_v0_holdout.sft.jsonl`, `tests/system/test_build_aethermon_agent_adapter_v0.py`, `tests/system/test_eval_aethermon_agent_adapter_v0.py`, `tests/training`, `scripts/training`, `config/model_training`, `config/training`, `docs/training`
- Roles: `{"config": 43, "doc": 6, "operator": 19, "test": 15}`
- Kinds: `{"code": 34, "config": 43, "doc": 6}`

Primary cells:
- `config/model_training/aethermon-agent-adapter-v0-local.json` (config/config, `055a7f507b912b4d`)
- `config/model_training/agentic-coding-qlora.json` (config/config, `675c5b54aaf7572b`)
- `config/model_training/aligned-foundations-qwen-primary.json` (config/config, `7501e782e74848ef`)
- `config/model_training/ca_geoseal_repair_eval_contract.json` (config/config, `d9bb30c390b7877b`)
- `config/model_training/ca_opcode_exact_eval_contract.json` (config/config, `7edfb96e2dfde22c`)
- `config/model_training/chemistry-qwen-primary.json` (config/config, `c5d95bb7f79b6b3a`)
- `config/model_training/coder-qwen-code-primaries.json` (config/config, `706e5cc7640fc3a2`)
- `config/model_training/coder-qwen-local.json` (config/config, `3016fd40b8945fd6`)
- `config/model_training/coding-agent-qwen-atomic-workflow-stage6.json` (config/config, `7f2ac1f11f52a87a`)
- `config/model_training/coding-agent-qwen-ca-geoseal-combined-repair-v3.json` (config/config, `2bd86417170c213b`)
- `config/model_training/coding-agent-qwen-ca-geoseal-smoke-repair-v1.json` (config/config, `b9c7cc21a82e3d77`)
- `config/model_training/coding-agent-qwen-ca-opcode-exact-repair-v2.json` (config/config, `8c39f36f19feb0ba`)
- ... 71 more cells in generated JSON

### Eval Benchmark Farm (`eval-benchmark-farm`)

- Biome: `benchmark`
- Health: `verified`
- Chunk coordinate: `-511,1113`
- Purpose: Benchmarks, eval drivers, public-style adapters, gates, and comparison reports.
- Tags: `eval`, `benchmark`, `gate`, `coding`
- Roots: `scripts/eval`, `scripts/benchmark`, `scripts/benchmarks`, `config/eval`, `tests/eval`, `tests/benchmark`, `tests/benchmarks`
- Roles: `{"config": 15, "operator": 128, "test": 55}`
- Kinds: `{"code": 183, "config": 15}`

Primary cells:
- `config/eval/aether_coding_score.v1.json` (config/config, `e92dd3555635beb3`)
- `config/eval/aether_external_task_lanes.v1.json` (config/config, `73c54b7001a88e4a`)
- `config/eval/aether_programmer_index.v1.json` (config/config, `40e0dec057fff281`)
- `config/eval/aether_research_claim_registry.v1.json` (config/config, `967392545cf375bc`)
- `config/eval/aether_writing_score.v1.json` (config/config, `e5c198afabe9c522`)
- `config/eval/agentic_pazaak_cards.v1.json` (config/config, `fb239bcfad1280ff`)
- `config/eval/cli_quest_tasks.sample.json` (config/config, `6e39f4b907326dbc`)
- `config/eval/coding_diffusion_bakeoff_v1.json` (config/config, `24207f560a817a7b`)
- `config/eval/common_agentic_benchmark_tasks.v1.json` (config/config, `5d8401cbb83a0991`)
- `config/eval/competitor_gap_agentic_tasks.v1.json` (config/config, `c6afa2c4e87d31a2`)
- `config/eval/external_agentic_eval_tasks.sample.json` (config/config, `494b072d4c1ebf12`)
- `config/eval/public_agentic_benchmark_sources.v1.json` (config/config, `c0c9b013c8e01d89`)
- ... 186 more cells in generated JSON

### Docs Ops Specs Map Room (`docs-ops-specs-map-room`)

- Biome: `map-room`
- Health: `review`
- Chunk coordinate: `-1365,-851`
- Purpose: Specs, ops notes, release maps, backlog notes, and decision records that guide current work.
- Tags: `docs`, `ops`, `specs`, `map-room`
- Roots: `docs/ops`, `docs/specs`, `docs/REPO_SURFACE_MAP.md`, `docs/SCBE_FULL_SYSTEM_MAP.md`
- Roles: `{"doc": 124, "test": 2}`
- Kinds: `{"config": 1, "doc": 125}`

Primary cells:
- `docs/REPO_SURFACE_MAP.md` (doc/doc, `6ae7df95f22e18dc`)
- `docs/SCBE_FULL_SYSTEM_MAP.md` (doc/doc, `c9ca079fc75060ea`)
- `docs/ops/AETHERBROWSER_MCP_TOOL_BRIDGE.md` (doc/doc, `a8fa2c74c16165a6`)
- `docs/ops/AETHERDESK_BROWSER_AGENT.md` (doc/doc, `1bceab5cd4d51acf`)
- `docs/ops/AGENTIC_CLI_HARNESS_RESEARCH_2026-04-29.md` (doc/doc, `3e449b4b410cb80a`)
- `docs/ops/AGENTIC_EXECUTION_REVIEW_TEMPORAL_LAYERS.md` (doc/doc, `e6bc80f50315b2ae`)
- `docs/ops/AGENTIC_VINE_BRANCH_WORKFLOW.md` (doc/doc, `a9ab2c455298d5ba`)
- `docs/ops/AGENT_BUS_USER_GUIDE.md` (doc/doc, `c319c8d34f79a8b8`)
- `docs/ops/AI_BRAIN_21D_ALIGNMENT_NOTES_2026-06-27.md` (doc/doc, `a7b8e7a894372e57`)
- `docs/ops/AI_BRAIN_CLAIMS_MATRIX_2026-06-27.md` (doc/doc, `3b57d4a1508ed8a2`)
- `docs/ops/AI_BRAIN_RELEASE_BACKLOG_2026-06-27.md` (doc/doc, `db2ab0e2e1a9c22f`)
- `docs/ops/APP_STORE_STRATEGY.md` (doc/doc, `ea3500c466e92cf5`)
- ... 114 more cells in generated JSON

### Docs Research Notes Map Room (`docs-research-notes-map-room`)

- Biome: `research`
- Health: `review`
- Chunk coordinate: `-1041,943`
- Purpose: Research writeups, theory notes, source manifests, and open-question ledgers.
- Tags: `docs`, `research`, `notes`, `map-room`
- Roots: `docs/research`, `notes/theory`
- Roles: `{"doc": 93}`
- Kinds: `{"config": 7, "doc": 86}`

Primary cells:
- `docs/research/AETHERDESK_ACADEMY_MVP_BACKLOG_2026-06-27.md` (doc/doc, `016ebe5659b7f4cc`)
- `docs/research/AI_AGENT_RESEARCH_CLAIM_REGISTER_2026-05-23.md` (doc/doc, `c58500a3aa60654e`)
- `docs/research/CODE_CONLANGS_EVIDENCE_2026-06-27.csv` (doc/doc, `2005ab7a6e90228a`)
- `docs/research/CODE_CONLANGS_OPEN_QUESTIONS_2026-06-27.md` (doc/doc, `6658089ff5298852`)
- `docs/research/CODE_CONLANGS_RESEARCH_2026-06-27.md` (doc/doc, `792c65d0ec5f63f6`)
- `docs/research/CODE_DIFFUSION_BAKEOFF_2026-05-11.md` (doc/doc, `3f8261626a1c1c49`)
- `docs/research/COLAB_AETHERDESK_INTEGRATION_RESEARCH_2026-06-27.md` (doc/doc, `fc0c702cd6364fab`)
- `docs/research/DARPA_AGENTIC_SYSTEM_ALIGNMENT_2026-05-10.md` (doc/doc, `3e911bb11bb0819d`)
- `docs/research/INSTRUMENT_COMPUTER_DECISION_RECORD_2026-06-27.json` (doc/config, `46a00396e4603068`)
- `docs/research/INSTRUMENT_COMPUTER_OUTLINE_2026-06-27.md` (doc/doc, `57fbefcced2c7d67`)
- `docs/research/INSTRUMENT_COMPUTER_README_2026-06-27.md` (doc/doc, `9ab7e54668520291`)
- `docs/research/INSTRUMENT_COMPUTER_SOURCE_MANIFEST_2026-06-27.json` (doc/config, `4d12d389649c0d85`)
- ... 81 more cells in generated JSON

### Artifacts Generated Quarantine (`artifacts-generated-quarantine`)

- Biome: `generated`
- Health: `noisy`
- Chunk coordinate: `-886,1825`
- Purpose: Generated evidence and receipts that should stay visible but not define the primary runtime story.
- Tags: `generated`, `artifacts`, `quarantine`, `cleanup`
- Roots: `artifacts`
- Scan note: `truncated`
- Roles: `{"config": 85, "doc": 26, "generated": 9}`
- Kinds: `{"code": 9, "config": 85, "doc": 26}`

Primary cells:
- `artifacts/aetherdesk_browser/inspect_2026-06-28T15-51-06-265Z.txt` (doc/doc, `ed521849e0ec20ae`)
- `artifacts/aetherdesk_browser/inspect_2026-06-28T16-02-05-095Z.txt` (doc/doc, `9d817f566b6afa5f`)
- `artifacts/aetherdesk_browser/inspect_2026-06-28T17-01-41-088Z.txt` (doc/doc, `83211ed0598e064d`)
- `artifacts/aetherdesk_browser/inspect_2026-06-28T17-03-43-684Z.txt` (doc/doc, `e45e438765f81f58`)
- `artifacts/aetherdesk_browser/inspect_2026-06-28T17-06-34-688Z.txt` (doc/doc, `dc54310d705aee45`)
- `artifacts/aetherdesk_browser/inspect_2026-06-28T17-07-27-561Z.txt` (doc/doc, `f089a1b5ca9f8fbd`)
- `artifacts/aetherdesk_browser/inspect_2026-06-28T17-08-12-834Z.txt` (doc/doc, `9def549ffddae4b1`)
- `artifacts/aetherdesk_browser/inspect_2026-06-28T17-08-52-633Z.txt` (doc/doc, `d6eae2a33f9ed133`)
- `artifacts/aetherdesk_browser/inspect_2026-06-28T17-08-56-097Z.txt` (doc/doc, `0c901a0a1247b738`)
- `artifacts/aetherdesk_browser/inspect_2026-06-28T17-10-21-745Z.txt` (doc/doc, `db4ad8696e8c250f`)
- `artifacts/aetherdesk_browser/inspect_2026-06-28T17-10-25-193Z.txt` (doc/doc, `6584b38e41af1952`)
- `artifacts/aetherdesk_browser/inspect_2026-06-28T17-13-55-136Z.txt` (doc/doc, `be437f06f4b6be7e`)
- ... 108 more cells in generated JSON

### Dist Build Output Quarantine (`dist-build-output-quarantine`)

- Biome: `generated`
- Health: `noisy`
- Chunk coordinate: `-1120,-1992`
- Purpose: Build output that should be release-checked but not treated as source terrain.
- Tags: `generated`, `dist`, `quarantine`, `release`
- Roots: `dist`
- Scan note: `truncated`
- Roles: `{"generated": 120}`
- Kinds: `{"code": 120}`

Primary cells:
- `dist/index.d.ts` (generated/code, `e8a46de92143b85c`)
- `dist/src/geoseal-v2.d.ts` (generated/code, `1bedb49df7629156`)
- `dist/src/geoseal-v2.js` (generated/code, `f34a8e94452aad87`)
- `dist/src/geoseal.d.ts` (generated/code, `1c83fca91f1e2e05`)
- `dist/src/geoseal.js` (generated/code, `f1860af7a165682a`)
- `dist/src/geosealCompass.d.ts` (generated/code, `b877bbceb33e8ccf`)
- `dist/src/geosealCompass.js` (generated/code, `4ca59bed8df1585f`)
- `dist/src/geosealMetrics.d.ts` (generated/code, `94a890f78df6d11b`)
- `dist/src/geosealMetrics.js` (generated/code, `ed689138f4258e27`)
- `dist/src/geosealOperatorSpace.d.ts` (generated/code, `c0c824f6f617fc97`)
- `dist/src/geosealOperatorSpace.js` (generated/code, `8cbdaac70c75a491`)
- `dist/src/geosealRAG.d.ts` (generated/code, `7a75538e3267f314`)
- ... 108 more cells in generated JSON

### Training Data Quarantine (`training-data-quarantine`)

- Biome: `generated`
- Health: `noisy`
- Chunk coordinate: `-1922,-1212`
- Purpose: Accumulated corpora and generated training rows; useful evidence but noisy for runtime orientation.
- Tags: `generated`, `training-data`, `quarantine`, `dataset`
- Roots: `training-data`
- Roles: `{"config": 4, "generated": 10}`
- Kinds: `{"config": 4, "jsonl": 10}`

Primary cells:
- `training-data/sft/aetherdesk_browser_use_v1.sft.jsonl` (generated/jsonl, `45ce07f935db2cc0`)
- `training-data/sft/aetherdesk_browser_use_v1_holdout.sft.jsonl` (generated/jsonl, `0d0c9b961249cf70`)
- `training-data/sft/aethermon_agent_adapter_v0.manifest.json` (config/config, `810d689d48e0cd54`)
- `training-data/sft/aethermon_agent_adapter_v0_holdout.sft.jsonl` (generated/jsonl, `47cfff670026a48d`)
- `training-data/sft/aethermon_agent_adapter_v0_train.sft.jsonl` (generated/jsonl, `e8a574bdb03bad52`)
- `training-data/sft/coding_system_full_v1_holdout.sft.jsonl` (generated/jsonl, `7780a028cd5c72d8`)
- `training-data/sft/coding_system_full_v1_manifest.json` (config/config, `3d64178be598d904`)
- `training-data/sft/coding_system_full_v1_train.sft.jsonl` (generated/jsonl, `efa14f13f5164058`)
- `training-data/sft/iridescent_text_tagging_v1.sft.jsonl` (generated/jsonl, `b093a9964488cb12`)
- `training-data/sft/vtc_better.jsonl` (generated/jsonl, `08db4b1ebc2959bf`)
- `training-data/sft/vtc_mbpp_qwen15.jsonl` (generated/jsonl, `41e229de0d1967bb`)
- `training-data/sft/vtc_mbpp_qwen15.manifest.json` (config/config, `89ff80d8e7cb7bce`)
- ... 2 more cells in generated JSON

## Coding Registry Overlay

- `docs/research/SCBE_CODING_SYSTEM_REGISTRY_2026-05-10.json`: 12 systems, 48/48 tracked paths present.
- `stisa_atomic_tokenizer`: STISA Atomic Tokenizer Surface (6/6 paths)
- `ss1_sacred_tongue_transport`: SS1 Sacred Tongue Transport (5/5 paths)
- `geoseal_agent_task`: GeoSeal Agent Task Runner (3/3 paths)
- `cross_language_lookup`: Cross-Language Lookup (3/3 paths)
- `code_slice_geometry`: Code Slice Geometry (2/2 paths)
- `aetherpp_lowering`: Aether++ Parser and Lowering (3/3 paths)
- `functional_coding_agent_benchmark`: Functional Coding Agent Benchmark (3/3 paths)
- `agent_bus`: SCBE Agent Bus (5/5 paths)
- `swarm_router`: SCBE Swarm Router (3/3 paths)
- `trust_self_tune_loop`: Fibonacci Trust Ladder + Turing Self-Tune Loop (6/6 paths)

## Region Edges

- `aetherdesk-portable-pc` -> `local-agent-bus` via `operator`, `receipts`
- `aetherdesk-portable-pc` -> `system-ops-control` via `operator`, `receipts`
- `artifacts-generated-quarantine` -> `dist-build-output-quarantine` via `generated`, `quarantine`
- `artifacts-generated-quarantine` -> `training-data-quarantine` via `generated`, `quarantine`
- `core-entry-package` -> `harmonic-crypto-governance` via `core`, `runtime`
- `dist-build-output-quarantine` -> `training-data-quarantine` via `generated`, `quarantine`
- `docs-ops-specs-map-room` -> `docs-research-notes-map-room` via `docs`, `map-room`
- `local-agent-bus` -> `system-ops-control` via `operator`, `receipts`
- `core-entry-package` -> `tokenizer-python-substrate` via `runtime`
- `harmonic-crypto-governance` -> `api-control-plane` via `governance`
- `harmonic-crypto-governance` -> `tokenizer-python-substrate` via `runtime`
- `training-builders` -> `eval-benchmark-farm` via `coding`
- `training-builders` -> `training-data-quarantine` via `dataset`

## Generated Next Actions

- Split or raise max_files for harmonic-crypto-governance so the chunk is not truncated.
- Split or raise max_files for local-agent-bus so the chunk is not truncated.
- Split or raise max_files for system-ops-control so the chunk is not truncated.
