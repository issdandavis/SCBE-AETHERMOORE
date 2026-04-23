# 2026-03-22 Foundation Triage + Card Deck

## Why this pass happened

PRs are stacking up, but the dominant blockers are not isolated feature bugs.
The repo is failing merges because the default merge lanes are too broad,
workflow behavior is noisy, and the codebase shape is too mixed to triage fast.

## Live PR queue snapshot

- `#608` depends on foundation work.
  - Merge-conflicted / rebase needed.
  - Live PR checks are mostly green.
  - Remaining top-level blocker is aggregate `CodeQL`.
- `#550` depends on foundation work.
  - Merge-conflicted / rebase needed.
  - Not a clean narrow fix PR.
- Dependabot PRs are mostly blocked by baseline CI/security patterns, not unique code regressions.

## Live blocker patterns

- Kindle build lane failed because `kindle-app/android/gradlew` was not executable on Linux.
- Security checks lane was unstable and too broad; it needed deterministic tooling setup.
- Default Python merge lane tried to collect optional and experimental tests that require extra services or unpublished modules.
- Remaining CodeQL blockers on `#608` map to these files:
  - `external/codex-skills-live/scbe-n8n-colab-bridge/scripts/colab_n8n_bridge.py`
  - `src/security/secret_store.py`
  - `external/codex-skills-live/hydra-node-terminal-browsing/scripts/hydra_terminal_browse.mjs`
  - `src/video/watermark.ts`
  - `src/crypto/aetherlex-seed.ts`

## Card deck model

Use one compact deck for repo order:

- `Spades` = core engine
  - canonical code and active subprojects
- `Hearts` = docs, notes, training knowledge, content
- `Clubs` = scripts, workflows, support/control plane
- `Diamonds` = generated runtime, deploy, archive pressure, product delivery
- `Red Joker` = disposable generated/runtime
- `Black Joker` = archive, experiment, spillover

Standard reading rules:

- `Ace` = first place to start
- `2-5` = primary lanes
- `6-10` = secondary/support lanes
- `J/Q/K` = noisy edges inside that suit

## Changes landed in this pass

- Added curated core Python merge runner:
  - `scripts/system/run_core_python_checks.py`
- Added card deck generator:
  - `scripts/system/system_card_deck.py`
- Added PR readiness triage:
  - `scripts/system/pr_merge_triage.py`
- Added premerge artifact workflow:
  - `.github/workflows/premerge-triage.yml`
- Hardened:
  - `.github/workflows/security-checks.yml`
  - `.github/workflows/ci.yml`
  - `.github/workflows/scbe-reusable-gates.yml`
  - `.github/workflows/kindle-build.yml`
- Closed the local CodeQL-backed security gaps by:
  - migrating legacy plaintext secret-store entries to encrypted form on first read
  - switching Colab env export checks to `has_secret(...)` so the emitter does not materialize secrets before printing resolver commands
  - keeping HYDRA terminal browse entity decoding and URL blocking on the safe path
  - normalizing watermark polynomial addition so generated Ring-LWE key coefficients stay inside the configured modulus
  - retaining the unbiased random sampling path in `src/crypto/aetherlex-seed.ts`

## Verification

- Python targeted lane:
  - `python -m pytest tests/test_colab_n8n_bridge_security.py tests/test_scbe_n8n_bridge_security.py tests/test_run_core_python_checks.py tests/test_system_card_deck.py tests/test_pr_merge_triage.py -q`
  - result: `25 passed`
- TypeScript targeted lane:
  - `npm test -- tests/hydra-terminal-browse.test.ts tests/crypto/aetherlexSeed.test.ts tests/video/generator.test.ts`
  - result: `92 passed`
- Direct syntax validation:
  - `node --check external/codex-skills-live/hydra-node-terminal-browsing/scripts/hydra_terminal_browse.mjs`

## Card game note

The card-deck idea is strong enough to keep.
The repo version should treat each card as a governed lane:

- suit = system family
- rank = priority / operator order
- face card = noisy/high-attention lane
- combo = approved multi-step workflow

That gives a usable operator map instead of another abstract planning doc.

## Payment note

Cash App is fine as a manual/off-platform payment fallback.
Programmable product billing should still anchor on Stripe or another API-first provider.
Use Cash App for direct/manual intake, not as the primary automation substrate.

## Packaging note

The repo already has meaningful package surfaces:

- npm root package with multiple exports
- PyPI root package with console scripts
- training/Hugging Face automation lane

The next package split should be disciplined and card-based, not one package per thought.
Only split packages where the suit boundary is already real.
