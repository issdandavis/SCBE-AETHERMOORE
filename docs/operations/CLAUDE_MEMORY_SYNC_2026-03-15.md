# Claude Memory Sync - 2026-03-15

Purpose:

- mirror the useful parts of Claude's private memory lane into the repo
- document what is safe to trust, what needs refresh, and what is speculative
- establish a source-of-truth order so agent memory stops outranking live repo state

## Source Of Truth Order

1. Repo files, tested artifacts, and current code under `SCBE-AETHERMOORE`
2. Live GitHub state for branches, PRs, and code-scanning alerts
3. Canon/lore source files and Obsidian vaults
4. Private AI memory folders such as `.claude/projects/.../memory`

Private memory is useful context. It is not authoritative runtime truth.

## Reliable Carry-Forward Notes

These private notes are currently worth keeping and reusing:

- `user_design_philosophy.md`
- `feedback_expression_labels.md`
- `feedback_writing_style.md`
- `user_writing_journey.md`
- `project_webtoon_pipeline.md`
- `project_local_image_runtime.md`
- `project_sweep_sorter_skill.md`
- `project_gemini_md_files.md`
- `everweave.md`

## Needs Refresh Before Reuse

These notes contain useful material but should not be treated as current
implementation truth without re-checking:

- `aetherbrowse.md`
- `kerrigan_browser.md`
- `octopus_architecture.md`
- `tongue-routing-and-reconciliation.md`
- `feedback_system_limits.md`

## Speculative / Design-Forward Notes

These are concept packets, not live capability claims:

- `project_chatterbox_tts.md`
- `project_swle_paper.md`
- `project_toroidal_training_loop.md`

## What Was Synced

The private memory lane was cleaned up to reflect current reality:

- `MEMORY.md` was rewritten into a curated current-state index
- `feedback_system_limits.md` now reflects that local CUDA PyTorch is verified,
  while keeping the disk-space warning
- `project_chatterbox_tts.md` was reframed as an upgrade path, not a done install
- `project_webtoon_pipeline.md` now includes the Chapter 1 mobile QA lane
- `project_local_image_runtime.md` now records the verified Python/CUDA image stack

## Repo Artifacts That Should Be Used Instead Of Private Memory

- Security drift triage:
  - `artifacts/security/codeql_drift_triage_20260314.md`
- Chapter 1 mobile QA:
  - `artifacts/webtoon/ch01/mobile-qa/README.md`
  - `artifacts/webtoon/ch01/mobile-qa/qa-results.md`
- Webtoon series adaptation spine:
  - `artifacts/webtoon/SERIES_STORYBOARD_ROADMAP.md`
  - `artifacts/webtoon/series_storyboard_manifest.json`

## Practical Rule

If a note mentions any of the following, verify it live before acting:

- current branch
- launch status
- running service
- exact test count
- install/runtime state
- pricing
- deployment state

Keep private memory for philosophy, intent, and stable user preferences.
Keep live operational truth in the repo.
