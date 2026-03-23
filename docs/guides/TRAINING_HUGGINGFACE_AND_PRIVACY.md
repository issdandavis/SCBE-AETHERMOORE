# Training, Hugging Face, And Privacy

This is the training and publish lane for turning runs, notes, and structured tasks into governed datasets and models.

## Core Files

- `src/integrations/huggingface.ts`
- `training/cstm_nursery.py`
- `src/training/auto_ledger.py`
- `scripts/build_offload_sft_records.py`
- `scripts/build_protected_corpus.py`
- `scripts/privacy_leakage_audit.py`
- `notebooks/scbe_pivot_training_v2.ipynb`

## Main Use Cases

- generate nursery-based training artifacts
- stage SFT data from offload runs
- audit and ledger records before training
- build a protected corpus before synthetic generation
- publish or query artifacts through Hugging Face

## Fast Commands

### Nursery training scaffold

```powershell
python training/cstm_nursery.py --story training-data/hf-digimon-egg/cstm_seed_story.json --cohort-size 3
```

### Build SFT staging from offload runs

```powershell
python scripts/build_offload_sft_records.py
```

### Ledger and clean staged SFT data

```powershell
python -m src.training.auto_ledger
```

### Build a protected corpus

```powershell
python scripts/build_protected_corpus.py --input training-data --output training/protected_corpus.jsonl --manifest training/protected_corpus.manifest.json
```

### Audit a protected corpus before synthetic release

```powershell
python scripts/privacy_leakage_audit.py --protected training/protected_corpus.jsonl --out training/privacy_audit.json
```

## When To Use This Lane

- You are converting useful work into reusable training data.
- You want a privacy-preserving synthetic-data prep path.
- You need HF publishing or local dataset hygiene.

## Rule Of Thumb

- Raw/source material stays private or archived.
- Protected corpora are intermediate assets.
- Only audited synthetic or ledgered outputs should be treated as publish-ready.
