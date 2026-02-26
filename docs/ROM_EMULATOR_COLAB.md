# ROM Emulator Colab Workflow

Use this workflow to generate training JSONL from legally owned ROM sessions.

## Legal Boundary

- Only run ROMs you legally own and dumped yourself.
- This repo does not provide ROM files and does not automate acquisition.

## 1) Install dependencies in Colab

```python
!apt-get -qq install -y tesseract-ocr > /dev/null 2>&1
!pip install -q pyboy Pillow pytesseract huggingface_hub
```

## 2) Run ROM bridge

```python
!python /content/SCBE-AETHERMOORE/demo/rom_emulator_bridge.py \
  --rom /content/your_rom.gb \
  --steps 8000 \
  --sample-every 8 \
  --ocr-every 20 \
  --max-pairs 600 \
  --gif /content/rom_preview.gif \
  --gif-scale 0.45 \
  --gif-fps 10 \
  --gif-max-frames 220 \
  --smart-agent \
  --game pokemon_crystal \
  --story-pack /content/SCBE-AETHERMOORE/training-data/game_design_sessions/isekai_core_loop.jsonl \
  --story-pack /content/SCBE-AETHERMOORE/training-data/game_design_sessions/isekai_minigames.jsonl \
  --story-pack /content/SCBE-AETHERMOORE/training-data/game_design_sessions/isekai_polypad_minigames.jsonl \
  --story-pack-mode both \
  --story-pack-every 700 \
  --i-own-this-rom
```

Supported now: `.gb`, `.gbc` (PyBoy backend).

### Optional: RAM reader test (Pokemon Crystal profile)

```python
!python /content/SCBE-AETHERMOORE/demo/pokemon_memory.py \
  --rom /content/crystal.gbc \
  --steps 1500 \
  --sample-every 25 \
  --test \
  --i-own-this-rom
```

This validates memory snapshots and prints JSON lines from the Crystal RAM profile.

## 3) Push generated JSONL to Hugging Face dataset

```python
import glob
from pathlib import Path
from huggingface_hub import HfApi

DATASET_REPO = "SCBE-AETHER/aethermoor-training-v1"
jsonl_files = glob.glob("/content/SCBE-AETHERMOORE/training-data/rom_sessions/*.jsonl")

api = HfApi()
api.create_repo(repo_id=DATASET_REPO, repo_type="dataset", exist_ok=True, private=True)

for fp in jsonl_files:
    name = Path(fp).name
    api.upload_file(
        path_or_fileobj=fp,
        path_in_repo=f"rom_sessions/{name}",
        repo_id=DATASET_REPO,
        repo_type="dataset",
    )
    print("Uploaded:", name)
```

## 4) Train

Reuse `notebooks/colab_qlora_training.ipynb` data loading + training cells.
The records are compatible with the notebook's `prompt/response` conversion.

## Pure Cloud (light local system)

If you want near-zero local load:

1. Run emulator + dataset generation in Colab only.
2. Push JSONL to Hugging Face dataset repo.
3. Use GCP/AWS GPU for long fine-tunes and eval jobs.
4. Keep local machine as controller only (no long GPU sessions).

## Sidekick growth file (append-only)

Use this to keep a growing memory file that can be retrained nightly:

```python
!python /content/SCBE-AETHERMOORE/scripts/sidekick_memory.py init
!python /content/SCBE-AETHERMOORE/scripts/sidekick_memory.py log \
  --task "Review Poly Pad mission queue" \
  --action "Prioritize low-risk mission and send summary to player" \
  --outcome "Mission queue reordered for safe progression" \
  --tags polypad,missions,sidekick \
  --also-sft
!python /content/SCBE-AETHERMOORE/scripts/sidekick_memory.py build-sft
```

## Firebase Studio sync (optional)

After dataset generation, sync JSONL into Firebase Firestore/Storage:

```python
!pip install -q firebase-admin google-cloud-firestore
!python /content/SCBE-AETHERMOORE/scripts/firebase_studio_sync.py \
  --glob "training-data/rom_sessions/*.jsonl" \
  --glob "training-data/sidekick/*.jsonl" \
  --collection-prefix aethermoor \
  --storage-prefix training-data
```

Set one of these first in your runtime:
- `GOOGLE_APPLICATION_CREDENTIALS`
- `FIREBASE_CONFIG`
- `FIREBASE_SERVICE_ACCOUNT_KEY`
