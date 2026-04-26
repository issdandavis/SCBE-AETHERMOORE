# Worktree Triage 2026-04-22

Current branch: `feature/cli-code-tongues`

This is a routing sheet for the current dirty worktree. It does not assume all changes belong together. The point is to separate high-value code/doc work from local mail and proposal handling so future commits stay coherent.

## Bucket A: Keep and commit soon

These look like legitimate product, architecture, or evaluation work and should be grouped into focused commits instead of left mixed with the mail/proposal lane.

### Core code and tests

- `api/darpa_prep/models.py`
- `api/darpa_prep/routes.py`
- `python/scbe/defensive_mesh.py`
- `python/scbe/tongue_code_lanes.py`
- `src/coding_spine/__init__.py`
- `src/coding_spine/router.py`
- `src/coding_spine/shared_ir.py`
- `src/crypto/sacred_tongues.py`
- `src/geoseal_cli.py`
- `src/neurogolf/family_lattice.py`
- `src/neurogolf/ir.py`
- `src/neurogolf/package.py`
- `src/neurogolf/solver.py`
- `src/neurogolf/structural_encode.py`
- `src/symphonic_cipher/scbe_aethermoore/cli_toolkit.py`
- `src/tongues/role_registry.py`
- `src/tokenizer/code_weight_packets.py`
- `tests/crypto/test_sacred_tongues.py`
- `tests/security-engine/redblue-arena.test.ts`
- `tests/test_advanced_mathematics.py`
- `tests/test_geoseal_agent_routing.py`
- `tests/test_geoseal_cli_tokenizer_atomic.py`
- `tests/test_neurogolf_onnx_emit.py`
- `tests/test_neurogolf_solver.py`
- `tests/test_protected_corpus_pipeline.py`
- `tests/test_sacred_tongues_crossmodal.py`
- `tests/test_sensitive_output_redaction.py`

### Evaluation and training support

- `config/model_training/coder-qwen-context-aware.json`
- `scripts/eval/drill_structure_preflight.py`
- `scripts/eval_brick1_gates.py`
- `scripts/eval/coding_method_real_task_probe.py`
- `scripts/audit_kaggle_training_abbr.py`
- `scripts/merge_polly_unified_0_5b.py`
- `scripts/merge_polly_unified_0_5b_weighted.py`
- `scripts/merge_polly_unified_0_5b_weighted_native.py`
- `scripts/smoke/`
- `scripts/smoke_matrix_polly_0_5b.py`

### Architecture, system docs, and specs

- `ARCHITECTURE.md`
- `CANONICAL_SYSTEM_STATE.md`
- `CONCEPTS.md`
- `LAYER_INDEX.md`
- `README_INDEX.md`
- `REPO_BOUNDARY_PLAN.md`
- `REPO_SURFACE_MAP.md`
- `SCBE_SYSTEM_OVERVIEW.md`
- `SPEC.md`
- `SPLIT_NOTICE.md`
- `STATE_OF_SYSTEM.md`
- `docs/ARCHITECTURE.md`
- `docs/CANONICAL_SYSTEM_STATE.md`
- `docs/CODING_SYSTEMS_MASTER_REFERENCE.md`
- `docs/LAYER_INDEX.md`
- `docs/REPO_BOUNDARY_PLAN.md`
- `docs/SCBE_SYSTEM_CLI.md`
- `docs/SCBE_SYSTEM_OVERVIEW.md`
- `docs/STATE_OF_SYSTEM.md`
- `docs/TONGUE_CODING_LANGUAGE_MAP.md`
- `docs/specs/ACCORDION_HOLOGRAPHIC_SEMANTIC_CABINET.md`
- `docs/specs/ATOMIC_TOKENIZER_GEOSEAL_CODING_STACK.md`
- `docs/map-room/CODING_METHOD_REAL_TASK_PROBE_2026-04-21.md`

## Bucket B: Commit later, but only as separate topic branches or focused commits

These may be valid, but they are broad enough or domain-specific enough that they should not ride along with unrelated code changes.

### Workflow and ops changes

- `.github/workflows/daily-repo-stats.yml`
- `.github/workflows/overnight-pipeline.yml`
- `.github/workflows/research-feed.yml`
- `docs/business/GTM_PLAYBOOK.md`
- `docs/map-room/decision_log.jsonl`
- `docs/map-room/session_handoff_latest.md`
- `package.json`
- `scripts/ci/review_code_scanning.py`
- `scripts/scbe-system-cli.py`

### MATHBAC strategy and support code

- `scripts/mathbac/strategy5_hyperbolic.py`
- `scripts/mathbac_md_to_pdf.py`
- `scripts/dava/cross_check_bridge_evidence.py`
- `scripts/send_collin_countersig.py`
- `scripts/send_jen_thanks.py`

### Repo guide and pitch surfaces

- `ALIASES.md`
- `PITCH_EMAIL_BANK_INNOVATION_LAB.md`
- `config/scbe_core_axioms_v1.yaml`
- `src/README.md`
- `src/extension-bridge/README.md`
- `src/lambda/README.md`
- `src/minimal/README.md`
- `src/symphonic_cipher/scbe_aethermoore/PATENT_SPECIFICATION.md`
- `src/symphonic_cipher/scbe_aethermoore/README.md`
- `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/SPECIFICATION.md`

## Bucket C: Keep local for now, do not mix into normal GitHub hygiene commits

These are tied to Proton/mail handling, countersigning, or partner packet exchange. They may be useful, but they should stay isolated until you explicitly decide whether they belong in the repo.

### Mail automation and extraction

- `scripts/mail/proton_extract_10769_attachments.py`
- `scripts/mail/proton_extract_collin_attachments.py`
- `scripts/mail/proton_fetch_collin_bodies.py`
- `scripts/mail/proton_fetch_collin_headers.py`
- `scripts/mail/proton_fetch_collin_new.py`
- `scripts/mail/proton_fetch_headers_10768_10769.py`
- `scripts/mail/proton_send_kernel_ack.py`
- `scripts/mail/proton_send_strategy5_reply.py`
- `scripts/mail/proton_send_substrate_reply.py`
- `scripts/mail/proton_send_telemetry_reply.py`
- `scripts/mail/proton_send_v2_cover.py`

### Proposal exchange artifacts and signed documents

- `docs/proposals/DARPA_MATHBAC/from_collin_20260421_kernel/`
- `docs/proposals/DARPA_MATHBAC/signed/`

Reason:

- these paths are close to live correspondence and executed documents
- they are high-context and easy to mispackage
- they do not belong in “routine cleanup” commits

## Bucket D: Likely local noise or machine-state artifacts

These do not look like canonical source and are good candidates for `.gitignore` or local quarantine instead of future commits.

- `training/ingest/local_cloud_sync_state.json`
- `training/ingest/latest_local_cloud_sync.txt`
- `tests/test_telemetry_advanced_math.json`

Reason:

- these look like local sync state or generated output
- they will create repeated churn if left ungoverned

## Safe next actions

### If the goal is “clean GitHub without losing work”

1. Create topic commits from Bucket A only.
2. Leave Bucket C out of normal pushes until explicitly reviewed.
3. Add ignore rules for Bucket D before the next cleanup pass.
4. Split Bucket B by concern:
   `workflow`, `docs`, `mathbac`, `cli`, `pitch`

### Suggested commit slices

- `darpa-prep-and-geoseal`
- `neurogolf-core-and-tests`
- `sacred-tongues-and-tokenizer`
- `architecture-doc-refresh`
- `workflow-and-cli-ops`

## Commands for the next cleanup pass

Review only Bucket A code:

```powershell
git diff -- api/ python/ src/ tests/
```

Review only local mail/proposal lane:

```powershell
git status --short -- docs/proposals/DARPA_MATHBAC scripts/mail scripts/send_collin_countersig.py scripts/send_jen_thanks.py
```

Review likely ignore candidates:

```powershell
git status --short -- training/ingest tests/test_telemetry_advanced_math.json
```

Stage a focused code commit without touching proposal/mail artifacts:

```powershell
git add api/darpa_prep python/scbe src/coding_spine src/crypto src/geoseal_cli.py src/neurogolf src/tongues src/tokenizer tests
```

## Things not to do

- Do not run a blanket `git add .`
- Do not delete `docs/proposals/DARPA_MATHBAC/signed/` in a cleanup reflex
- Do not mix `scripts/mail/` with general website or repo hygiene commits
- Do not assume the architecture doc churn is synchronized; it needs its own pass
