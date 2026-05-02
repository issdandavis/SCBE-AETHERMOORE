# 2026-05-02 Pre-Train Inventory

Snapshot of working-tree state on `chore/release-4.0.3-housekeeping` after the
GeoSeal coder pair bench v2. Classifies every dirty/untracked path so the next
training pass can pull from a frozen manifest instead of a fuzzy diff.

Bench artifact this inventory is paired with:
`artifacts/bench/geoseal_coder_pair_20260502T085810Z.json`.

## A. Keep — green lane (folds into training manifest)

Tests run 2026-05-02 05:47 PT, all green:

- `tests/test_tile_lang.py` — 3/3 passed (Python parity)
- `tests/coding_spine/test_deterministic_tongue_router.py` — 4/4 passed
- `tests/L2-unit/tileLang.unit.test.ts` — 4/4 passed (vitest)

Files:

| Path | Status | Lines | Role |
|------|--------|-------|------|
| `packages/kernel/src/tileLang.ts` | NEW | 64 | Tile↔Sacred-Tongue striping (TS canonical) |
| `python/scbe/tile_lang.py` | NEW | 36 | Python parity port |
| `packages/kernel/src/index.ts` | MOD | +1 | Re-export for `tileLang.js` |
| `tests/L2-unit/tileLang.unit.test.ts` | NEW | 36 | Round-trip + diagonal striping |
| `tests/test_tile_lang.py` | NEW | 20 | Python parity tests |
| `src/coding_spine/deterministic_tongue_router.py` | NEW | 194 | Wraps atomic-token router with prompt-cleanup + force override |
| `tests/coding_spine/test_deterministic_tongue_router.py` | NEW | 34 | Map-contamination + force-tongue gates |
| `scripts/serve_geoseal_harness.py` | NEW | 249 | FastAPI bridge that emits `deterministic_route` per pair call |
| `scripts/system/bench_geoseal_coder_pair.py` | NEW | 356 | Three-track bench (coding + routing + deterministic baseline) |
| `scripts/system/import_hf_model_to_ollama.py` | NEW | 230 | HF→Ollama Modelfile import helper |
| `scripts/training_data/build_balanced_tongue_routing_sft.py` | NEW | 132 | 72-row balanced SFT seed (12 per tongue) |
| `notes/sessions/2026-05-02-session.md` | NEW | 169 | Session note (yin-yang token, valence-friction, 6D merge) |
| `notes/Cross Talk.md` | MOD | +13 | Codex XTALK-MANUAL-20260502 sync packet |

## B. Auto-regenerated (regenerate on next run, do not hand-merge)

| Path | Why |
|------|-----|
| `training-data/sft/coding_system_full_v1_manifest.json` | timestamp bump only |
| `training-data/sft/coding_system_full_v1_train.sft.jsonl` | CRLF-only (regenerated) |
| `training-data/sft/coding_system_full_v1_holdout.sft.jsonl` | CRLF-only (regenerated) |
| `training-data/sft/bijective_dsl_v5_holdout_manifest.json` | timestamp bump only |
| `sealed_blobs/1_2_3_5_8_13.json` | RWP envelope re-rolled by test fixture |

Treat (B) as derived state. Re-run the generators rather than committing
churn diffs.

## C. Out of scope tonight (revisit after training cycle)

| Path | Note |
|------|------|
| `.claude/settings.local.json` | LF→CRLF only |
| `.scbe/cli-context.json` | local pytest temp dir paths |
| `scripts/scbe-system-cli.py` | CRLF-only |
| `tests/test_telemetry_advanced_math.json` | large, unrelated to this lane |
| `.gitignore` | one-line `.scbe/tmp/` add — fold in next chore commit |
| `ui/geoseal-console/` (untracked) | static console paired with the harness bridge; folds in with the GeoSeal lane once console UI changes are reviewed |
| `.cursor/plans/major_build+launch_restructure_b8eec43c.plan.md` | cursor planner state |

## D. Flagged — needs review before merge, not a training input

`.github/workflows/nightly-ops.yml` (MOD) had a broken YAML structure:
the `env: { SCBE_MODE: ci }` block was positioned **inside the `steps:` list**
between two step entries, and the original `Plan` step was removed.

**Resolution 2026-05-02:** Restored from HEAD via `git checkout HEAD --
.github/workflows/nightly-ops.yml`. Validated with `yaml.safe_load`. No longer
flagged — file is back to the prior valid version. Excluded from the training
manifest as not an input either way.

## Manifest readiness

Lanes ready for the training packet build:

- **Coding spine** — deterministic router + bench script + balanced SFT seed.
- **TileLang kernel** — TS+Py parity ports with green tests.
- **GeoSeal harness** — bridge with `deterministic_route` echo + pair bench v2 result.

## Status 2026-05-02 (auto-mode pass)

1. `nightly-ops.yml` restored from HEAD — YAML parses, no longer flagged.
2. Frozen manifest written to
   `training-data/manifests/2026-05-02-pretrain-manifest.json` (6 lanes,
   16 files, all SHA256 verified against working tree).
3. Executable promotion gate spec written to
   `training-data/manifests/2026-05-02-promotion-gate.md` (G1 code, G2
   routing, G3 coding, G4 packet integrity, G5 chemistry-deferred).

Next move (held for explicit go — these are content/training actions):

1. Build/refresh aligned-foundations + chemistry + coding packet corpora
   (step 3 of the night plan).
2. Run the executable promotion gate against the new corpora.
3. Promote only what passes G1-G4 (G5 still deferred until chemistry lane lands).
