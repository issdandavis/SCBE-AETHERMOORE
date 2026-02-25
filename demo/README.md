# SCBE-AETHERMOORE Demos

---

## Legal ROM Emulator Bridge (Colab Data Generation)

Run a real local ROM (that you legally own) and export `prompt/response` JSONL
for the existing QLoRA training flow.

### Supported now
- `.gb` and `.gbc` via PyBoy

### Not implemented yet
- `.gba` backend (Pokemon Sapphire and other GBA titles) needs an mGBA/RetroArch adapter

### Local Quick Start
```bash
python demo/rom_emulator_bridge.py \
  --rom /path/to/your_rom.gb \
  --steps 4000 \
  --gif demo/rom_preview.gif \
  --i-own-this-rom
```

### Colab Quick Start
```bash
!apt-get -qq install -y tesseract-ocr > /dev/null 2>&1
!pip install -q pyboy Pillow pytesseract

!python /content/SCBE-AETHERMOORE/demo/rom_emulator_bridge.py \
  --rom /content/your_rom.gb \
  --steps 6000 \
  --sample-every 8 \
  --ocr-every 20 \
  --max-pairs 500 \
  --gif /content/rom_preview.gif \
  --gif-scale 0.5 \
  --gif-max-frames 220 \
  --i-own-this-rom
```

### Output
- JSONL: `training-data/rom_sessions/rom_<id>.jsonl`
- Optional GIF preview: path provided via `--gif`

The JSONL schema is aligned to the existing notebook loader (`prompt` + `response`).

### Optional: Firebase Studio Sync
```bash
python scripts/firebase_studio_sync.py \
  --glob "training-data/rom_sessions/*.jsonl" \
  --glob "training-data/sidekick/*.jsonl" \
  --collection-prefix aethermoor
```
See: `docs/03-deployment/firebase-studio-game-sync.md`

---

## Aethermoor RPG (Ruby/Sapphire-Style Core + Poly Pad)

Simple visual loop, complex systems as optional mini-games.

### Run Locally
```bash
python demo/aethermoor_game.py
```

### Headless (AI autopilot, small GIF)
```bash
python demo/headless.py --steps 1000 --gif demo/headless_small.gif --scale 0.35 --fps 8 --max-frames 180
```

### Core Controls
- `Arrow Keys / WASD`: move and navigate
- `Enter`: interact/confirm (includes "sit at computer" when near terminal)
- `P`: open Poly Pad (phone / in-game PC panel)
- `I`: open CodeLab IDE when standing at a terminal
- `L`: open Lore Library when standing at a terminal
- `B`: quick battle entry when available
- `Esc`: pause/back

### Poly Pad Apps
- `Home`: status + unread alerts
- `Contacts`: call logs and checkpoint guidance
- `Messages`: story/event transcripts
- `Missions`: active objective switching
- `PC Box`: quick party/box inspection + launch computer IDE
- `IDE`: launch coding mini-game tickets (debug/test/refactor actions)
- `Library`: Morrowind-style readable books sourced from Obsidian canon notes

---

## Aethermoor Character Creator + Origin Forge

### Quick Start
```bash
python demo/play_aethermoor.py
```

### Controls
- `Enter`: Start the run
- `1-7`: Choose an action in scene
- `o`: Open Origin Forge (show current party origin cards)
- `q`: Quit and save training data

### What It Generates
- Choice-aligned SFT records
- Companion-disagreement DPO records
- Deterministic origin cards for active party members
- Origin-to-SFT records for companion backstory grounding

Files are written to `demo/training_output/`:
- `sft_aethermoor_<hash>.jsonl`
- `dpo_aethermoor_<hash>.jsonl`
- `origins_aethermoor_<hash>.json`
- `origin_sft_aethermoor_<hash>.jsonl`

### Standalone Origin Builder
```bash
python demo/create_origins.py --names Polly Clay Aria
```

Optional flags:
- `--seed <value>`: deterministic seed override
- `--out-dir <path>`: output directory override

---

## Train Your AI - SCBE Governance Demo

### Quick Start
```bash
streamlit run demo/train_your_ai.py
```

### What This Is
A playable AI governance adventure game where your choices train a real AI model.
Every decision generates SFT training data in HuggingFace-compatible format.

### How It Works
1. Play through governance scenarios (54 scenes, 24 endings)
2. Your choices are recorded as instruction/response training pairs
3. Export as JSONL for fine-tuning on HuggingFace
4. Watch your AI companion level up as you play

### Tech Stack
- Streamlit (UI)
- Twee/Twine game format (content)
- SCBE-AETHERMOORE 14-layer governance (framework)

### Files
- `train_your_ai.py` -- Streamlit app (fully self-contained)
- `governance_simulator.twee` -- Game data (54 scenes, Twee/Twine format)

---

## SCBE Secure Bank Demo

A visual demonstration of the SCBE-AETHERMOORE 14-layer security system protecting financial transactions.

## What This Shows

1. **Real-time Security Visualization** - Watch all 14 security layers process each transaction
2. **Encrypted Envelopes** - See the AES-256-GCM encrypted data with signatures
3. **Attack Simulation** - Click "Simulate Hacker Attack" to see the system block threats

## How to Run

### Option 1: Open Directly
Just open `demo/index.html` in any web browser.

### Option 2: With a Server
```bash
# Using Python
cd demo && python -m http.server 8080

# Using Node
npx serve demo
```

Then visit: http://localhost:8080

## Features Demonstrated

| Feature | How It's Shown |
|---------|----------------|
| 14-Layer Pipeline | Each layer lights up green as it processes |
| Hyperbolic Geometry | Layers 4-7 show Poincare ball operations |
| Post-Quantum Ready | Envelope shows multi-signature structure |
| Replay Protection | Attack simulation shows nonce detection |
| Tamper Detection | Attack simulation shows spectral analysis |

## For Buyers/Investors

This demo shows a simplified visualization of the actual SCBE security system. The real implementation includes:

- **63,000+ lines** of production code
- **1,150+ automated tests** (98% pass rate)
- **Post-quantum cryptography** (ML-KEM-768, ML-DSA-65)
- **Patent-pending** hyperbolic geometry approach

Contact: [Your contact info here]
