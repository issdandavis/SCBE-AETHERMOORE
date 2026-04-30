# Worktree Triage - 2026-04-29

This note maps the current dirty tree so cleanup can preserve useful work instead of flattening it. No files were deleted or reverted during this pass.

## Current Posture

- The tree is intentionally dirty: Cursor, Codex, generated training artifacts, benchmark work, compliance scaffolding, and GeoSeal command work are all present together.
- Treat this state as an integration staging area, not as trash.
- Highest-risk runtime lanes were tested first: agent router, Vercel bridge task parity, GeoSeal command surfaces, and training consolidation helpers.

## Verified Gates

```powershell
python scripts/system/agent_router_smoke.py coding
```

Result: passed. The smoke produced a `PASS` decision with 56 benchmark records and an executable Python pass rate of 1.0.

```powershell
python scripts/system/agent_router_smoke.py system_build
```

Result: passed. Required repo paths, required package scripts, selected API Node syntax checks, and Python compile checks all passed.

```powershell
python -m black --check tests\test_agent_router_bridge_tasks.py
```

Result: passed.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_agent_router_bridge_tasks.py tests/test_agentic_benchmark_ladder.py tests/test_agent_task_run_and_external_eval.py tests/benchmark/test_cli_competitive_benchmark.py tests/benchmark/test_representation_kaleidoscope.py -q
```

Result: 21 passed after formatting the new benchmark and router helper scripts.

```powershell
python -m black --check scripts\system\agent_router_smoke.py scripts\benchmark\agentic_benchmark_ladder.py scripts\benchmark\build_representation_kaleidoscope.py scripts\benchmark\cli_competitive_benchmark.py scripts\benchmark\external_agentic_eval_driver.py scripts\system\build_training_hub.py scripts\system\training_surfaces_connect.py scripts\system\preflight_zero_cost_training.py scripts\system\free_compute_agent_array.py scripts\system\code_slice_geometry.py scripts\training\build_jupiter_ring_feedback.py
```

Result: passed after formatting those 11 files.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_build_training_hub.py tests/test_training_surfaces_connect.py tests/test_build_jupiter_ring_feedback.py tests/test_preflight_zero_cost_training.py tests/test_cross_language_lookup.py tests/test_build_stage6_balanced_extras.py tests/test_free_compute_agent_array.py tests/test_code_slice_geometry.py -q
```

Result: 22 passed.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/test_geoseal_agent_routing.py tests/test_geoseal_cli_tokenizer_atomic.py tests/test_geoseal_mission_compass.py tests/test_tokenizer_execution_lattice_role_spec.py -q
```

Result: 211 passed.

## Bucket 1 - Runtime, API, and Dispatch

Keep and review carefully before merge.

- `.github/workflows/agent-router.yml`
- `api/_agent_common.js`
- `api/agent/chat.js`
- `api/agent/search.js`
- `docs/static/polly-sidebar.js`
- `docs/agents.html`
- `scripts/system/agent_router_smoke.py`
- `tests/test_agent_router_bridge_tasks.py`
- `tests/test_agent_task_run_and_external_eval.py`

Purpose observed: expand the public agent bridge from basic research tasks into web search, coding, system build, and agentic ladder tasks. The bridge, page, and workflow task lists now have a parity test.

## Bucket 2 - GeoSeal and Tokenizer Execution Lattice

Keep and split into a focused commit once reviewed.

- `src/geoseal_cli.py`
- `bin/geoseal.cjs`
- `src/geoseal_mission_compass.py`
- `docs/specs/GEOSEAL_MARS_MISSION_COMPASS_v1.md`
- `docs/specs/TOKENIZER_EXECUTION_LATTICE_ROLE_v1.md`
- `src/crypto/sacred_tongue_payload_bijection.py`
- `tests/test_geoseal_cli_tokenizer_atomic.py`
- `tests/test_geoseal_mission_compass.py`
- `tests/test_tokenizer_execution_lattice_role_spec.py`
- `tests/test_sacred_tongue_payload_bijection.py`

Purpose observed: make GeoSeal more useful as a command surface, cross-language mapping layer, reversible payload lane, and Mars-style terrain/action compass.

## Bucket 3 - Agentic Benchmark and Evaluation Harness

Keep as the benchmark ladder lane.

- `benchmarks/scbe_agentic_v1/`
- `scripts/benchmark/agentic_benchmark_ladder.py`
- `scripts/benchmark/build_representation_kaleidoscope.py`
- `scripts/benchmark/cli_competitive_benchmark.py`
- `scripts/benchmark/external_agentic_eval_driver.py`
- `scripts/benchmarks/`
- `tests/benchmark/test_cli_competitive_benchmark.py`
- `tests/benchmark/test_representation_kaleidoscope.py`
- `tests/benchmarks/`
- `tests/test_agentic_benchmark_ladder.py`

Purpose observed: compare the CLI and agent harness against external-style agentic task expectations, including representation consistency and execution governance.

## Bucket 4 - Training Consolidation and Free Compute Lanes

Keep, but do not push every generated output blindly.

- `docs/training-hub.html`
- `scripts/system/build_training_hub.py`
- `scripts/system/training_surfaces_connect.py`
- `scripts/system/preflight_zero_cost_training.py`
- `scripts/system/free_compute_agent_array.py`
- `scripts/system/code_slice_geometry.py`
- `scripts/system/build_cross_language_lookup.py`
- `scripts/training/build_jupiter_ring_feedback.py`
- `scripts/hf_jobs/`
- `training-data/agentic_coding/jupiter_ring_feedback.jsonl`
- `tests/test_build_training_hub.py`
- `tests/test_training_surfaces_connect.py`
- `tests/test_preflight_zero_cost_training.py`
- `tests/test_free_compute_agent_array.py`
- `tests/test_code_slice_geometry.py`
- `tests/test_build_jupiter_ring_feedback.py`

Purpose observed: consolidate local, GitHub, Hugging Face, Kaggle, Colab, and feedback-loop surfaces into routeable training buckets.

## Bucket 5 - DSL and Functional Coding Agent Work

Keep staged files together.

- `config/model_training/dsl_synthesis_v1_eval_contract.json`
- `python/scbe/dsl/__init__.py`
- `python/scbe/dsl/primitives.py`
- `scripts/dsl/synthesize_triples.py`
- `scripts/eval/functional_coding_agent_benchmark.py`
- `scripts/eval/gate_functional_benchmark.py`
- `scripts/eval/score_adapter_frozen.py`
- `scripts/eval/score_dsl_executable.py`
- `scripts/eval/score_foundation_bundle_gate.py`
- `scripts/eval/score_stage6_regression.py`
- `scripts/build_stage6_repair_sft.py`
- `scripts/build_stage6_balanced_extras.py`
- `scripts/build_stage6_must_pass_boost.py`

Purpose observed: expand DSL synthesis, scoring, stage-six repair, and functional coding-agent evaluation.

## Bucket 6 - Compliance and Public Proof Surface

Review as product/docs work, not core runtime.

- `config/compliance/`
- `docs/compliance/`
- `scripts/system/fetch_public_compliance_corpus.py`
- `tests/test_fetch_public_compliance_corpus.py`
- `content/articles/platforms/generated/bedtime-build-notes-20260429/`
- `scripts/publish/build_bedtime_article_campaign.py`
- `scripts/publish/post_to_bluesky.py`

Purpose observed: early compliance scaffolding and article/public-output generation.

## Bucket 7 - Generated or Local-State Churn

Do not delete unless verified elsewhere or intentionally regenerated.

- `artifacts/`
- `training/runs/`
- `training-data/sft/*manifest.json`
- `unsloth_compiled_cache/`

Immediate rule: generated does not mean worthless. Preserve manifests and final outputs; clear only rebuildable caches after offload or explicit confirmation.

## Next Cleanup Order

1. Commit or shelve runtime bridge parity work after one Vercel deploy check.
2. Commit or shelve GeoSeal command and Mars compass work after focused CLI smoke tests.
3. Commit or shelve benchmark/training consolidation after package script checks.
4. Move generated article/training output into an offload lane only after manifesting byte counts and destination paths.
5. Ignore `unsloth_compiled_cache/` until disk pressure requires verified cache cleanup.
