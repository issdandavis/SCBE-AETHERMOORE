# Training Data Repo Workflow

The code repo and the corpus repo need different rules.

## Why

- GitHub hard-blocks files over `100 MB`.
- GitHub starts getting awkward well before that.
- This repo currently has several generated JSONL files in the `30-116 MB` range.
- Training corpora change often and should not keep polluting code history.

## Split Policy

- Keep scripts, schemas, reports, manifests, and small examples in `SCBE-AETHERMOORE`.
- Move bulk JSONL corpora to a separate training-data repo.
- Stage that repo with GitHub-safe shards under `45 MB` each.
- Preserve a manifest so every shard can be traced back to the source file.

## Staging Command

```powershell
python scripts/system/shard_training_dataset.py `
  --input training-data `
  --output _staging/training-data-repo `
  --dataset-repo issdandavis/scbe-aethermoore-training-data
```

This creates:

- `_staging/training-data-repo/data/...`
- `_staging/training-data-repo/manifests/training_dataset_manifest.json`
- `_staging/training-data-repo/README.md`

## Recommended Repo Layout

```text
scbe-aethermoore-training-data/
  README.md
  manifests/
    training_dataset_manifest.json
  data/
    training-data/
    training-data/sft/
```

## Recommended Push Flow

1. Stage the shards into `_staging/training-data-repo`.
2. Initialize or update a separate GitHub repo for corpus storage.
3. Commit the staged repo there, not in the code repo.
4. Keep the code repo pointed at the manifest and the generation scripts.

## One-Step Build Flow

Use this when you want to turn export bundles and draft roots into staged dataset shards in one pass.

```powershell
python scripts/system/publish_training_dataset_repo.py `
  --include-training-data `
  --claude-export-zip "C:\Users\issda\Downloads\data-2026-03-30-13-50-27-batch-0000.zip" `
  --draft-root "C:\Users\issda\Dropbox" `
  --exclude-glob "training-data/sft/book_drafts_sft.jsonl" `
  --exclude-glob "training-data/sft/avalon_codex_lore_sft.jsonl" `
  --output-repo _staging/training-data-repo `
  --dataset-repo issdandavis/scbe-aethermoore-training-data
```

Use `--exclude-glob` for noisy or quarantined corpora that should stay local until reviewed. Empty JSONL files are skipped automatically.

This will:

- convert Claude project lore exports into JSONL
- convert longform `.md`, `.txt`, `.html`, `.docx`, `.rtf`, and `.odt` draft roots into JSONL
- restage the dataset repo with GitHub-safe shards
- write a build summary under `_staging/training-data-build/`

Add `--git-commit` and `--git-push` when you want the staged dataset repo updated in place.

## Current Large-File Pressure

The worst current offenders are generated corpus files such as:

- `training-data/polly_training_merged.jsonl`
- `training-data/mega_tetris_enriched_sft.jsonl`
- `training-data/mega_ingest_sft.jsonl`
- `training-data/sft/consolidated_root_sft.jsonl`
- `training-data/sft/consolidated_plus_claude_exports_sft/part-0003.jsonl`

Those should be treated as dataset-repo material, not code-repo material.
