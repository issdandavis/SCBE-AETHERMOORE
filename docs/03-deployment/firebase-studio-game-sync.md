# Firebase Studio Game Sync

Cloud-first sync for emulator sessions and sidekick memory.

## What this adds

- Sync JSONL rows to Firestore collections.
- Upload source JSONL files to Firebase Storage.
- Keep local machine light: generate and train in cloud, use local only for control.

## Prerequisites

1. Firebase project with Firestore enabled.
2. Service account credentials configured using one of:
   - `GOOGLE_APPLICATION_CREDENTIALS` (path to service account JSON)
   - `FIREBASE_CONFIG` (JSON string)
   - `FIREBASE_SERVICE_ACCOUNT_KEY` (JSON string)
3. Optional storage bucket:
   - `FIREBASE_STORAGE_BUCKET=your-project.appspot.com`
4. Python package:

```bash
pip install firebase-admin google-cloud-firestore
```

## Sync command

```bash
python scripts/firebase_studio_sync.py \
  --glob "training-data/rom_sessions/*.jsonl" \
  --glob "training-data/game_sessions/*.jsonl" \
  --glob "training-data/sidekick/*.jsonl" \
  --collection-prefix aethermoor \
  --storage-prefix training-data
```

## Dry run first

```bash
python scripts/firebase_studio_sync.py --dry-run
```

## Firestore collections used

- `aethermoor_rom_sessions`
- `aethermoor_sidekick_memory`
- `aethermoor_sidekick_sft`
- `aethermoor_training_rows` (fallback for other JSONL files)

## Cloud-only lane

1. Run emulator and build datasets in Colab/GCP/AWS.
2. Sync generated JSONL to Firebase Studio with `firebase_studio_sync.py`.
3. Trigger training jobs from cloud runners.
4. Keep local system as orchestration terminal only.
