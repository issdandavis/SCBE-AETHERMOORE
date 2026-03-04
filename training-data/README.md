---
dataset_info:
  - config_name: game_sessions
    features:
      - name: prompt
        dtype: string
      - name: response
        dtype: string
      - name: metadata
        dtype: string
    splits:
      - name: train
        num_examples: 328
  - config_name: gacha_sessions
    features:
      - name: prompt
        dtype: string
      - name: response
        dtype: string
      - name: metadata
        dtype: string
    splits:
      - name: train
        num_examples: 5
  - config_name: architecture_sessions
    features:
      - name: prompt
        dtype: string
      - name: response
        dtype: string
      - name: metadata
        dtype: string
    splits:
      - name: train
        num_examples: 21
  - config_name: tongues_sessions
    features:
      - name: prompt
        dtype: string
      - name: response
        dtype: string
      - name: metadata
        dtype: string
    splits:
      - name: train
        num_examples: 7
  - config_name: math_sessions
    features:
      - name: prompt
        dtype: string
      - name: response
        dtype: string
      - name: metadata
        dtype: string
    splits:
      - name: train
        num_examples: 5
  - config_name: game_design_sessions
    features:
      - name: prompt
        dtype: string
      - name: response
        dtype: string
      - name: metadata
        dtype: string
    splits:
      - name: train
        num_examples: 68
  - config_name: lore_sessions
    features:
      - name: prompt
        dtype: string
      - name: response
        dtype: string
      - name: metadata
        dtype: string
    splits:
      - name: train
        num_examples: 36
  - config_name: music_sessions
    features:
      - name: prompt
        dtype: string
      - name: response
        dtype: string
      - name: metadata
        dtype: string
    splits:
      - name: train
        num_examples: 7
  - config_name: all
    features:
      - name: prompt
        dtype: string
      - name: response
        dtype: string
      - name: metadata
        dtype: string
    splits:
      - name: train
        num_examples: 10978
configs:
  - config_name: game_sessions
    data_files: "game_sessions/*.jsonl"
  - config_name: gacha_sessions
    data_files: "gacha_sessions/*.jsonl"
  - config_name: architecture_sessions
    data_files: "architecture_sessions/*.jsonl"
  - config_name: tongues_sessions
    data_files: "tongues_sessions/*.jsonl"
  - config_name: math_sessions
    data_files: "math_sessions/*.jsonl"
  - config_name: game_design_sessions
    data_files: "game_design_sessions/*.jsonl"
  - config_name: lore_sessions
    data_files: "lore_sessions/*.jsonl"
  - config_name: music_sessions
    data_files: "music_sessions/*.jsonl"
  - config_name: all
    data_files: "**/*.jsonl"
    default: true
license: mit
language:
  - en
task_categories:
  - text-generation
tags:
  - scbe-aethermoore
  - ai-safety
  - hyperbolic-geometry
  - post-quantum-cryptography
  - isekai-game
  - sft
  - instruction-tuning
  - sacred-tongues
pretty_name: "SCBE-AETHERMOORE Training Dataset"
size_categories:
  - 10K<n<100K
---

# SCBE-AETHERMOORE Training Dataset

Supervised fine-tuning (SFT) dataset for the SCBE-AETHERMOORE hyperbolic geometry AI safety and governance framework.

## Overview

This dataset contains 10,978 training pairs spanning the full SCBE-AETHERMOORE system: 14-layer architecture knowledge, Six Sacred Tongues encoding, isekai gameplay sessions, gacha combat, mathematical proofs, world lore, game design documents, and original music compositions. It is designed for instruction-tuning language models to understand and operate within the SCBE governance framework.

**Author**: Issac Davis
**License**: MIT
**Language**: English
**Task**: text-generation (SFT / instruction-tuning)

## Dataset Structure

### Configs

| Config | Description | Examples |
|--------|-------------|----------|
| `game_sessions` | Aethermoor isekai gameplay SFT (scene choices, state transitions) | 328 |
| `gacha_sessions` | Gacha tower combat, pulls, and arc choices | 5 |
| `architecture_sessions` | SCBE 14-layer architecture, PHDM, governance runtime | 21 |
| `tongues_sessions` | Six Sacred Tongues phonotactics, encoding, cross-translation | 7 |
| `math_sessions` | Ternary Braid Algebra, emergent patterns, mathematical proofs | 5 |
| `game_design_sessions` | Isekai game design, minigames, hybrid systems, emulator concepts | 68 |
| `lore_sessions` | World lore, characters, Everweave canon, RP transcripts | 36 |
| `music_sessions` | Original song compositions with production metadata | 7 |
| `all` (default) | All JSONL files merged (includes bulk SFT, Notion exports, evals) | 10,978 |

### Data Fields

All records are normalized to these core fields:

| Field | Type | Description |
|-------|------|-------------|
| `prompt` | string | The instruction, question, or scene prompt (normalized from `prompt` or `instruction` fields) |
| `response` | string | The expected response or completion |
| `metadata` | string (JSON) | Source metadata including category, session ID, timestamps, and domain tags |

Some files use `instruction` instead of `prompt` as the input field. The merge script normalizes everything to `prompt`/`response`.

### Additional Fields (file-dependent)

| Field | Appears In | Description |
|-------|-----------|-------------|
| `id` | instruction-tuning, knowledge-base, evals, sft_bulk | Unique identifier |
| `category` | instruction-tuning, knowledge-base, evals, sft_bulk | Domain category tag |
| `event_type` | session files | Event classification |
| `provenance` | gacha_sessions | Data lineage tag |
| `rho_e` | gacha_sessions | Entropy density |
| `ternary_alignment` | gacha_sessions | Ternary braid state |
| `expected` | evals | Expected answer for grading |
| `difficulty` | evals | easy / medium / hard |

## Categories in Detail

### Game Sessions (gameplay SFT)
Live gameplay transcripts from the Aethermoor isekai game engine. Each record contains a scene prompt with zone/inventory/quest state, the player's chosen action, and the resulting game state including Sacred Tongue alignment, layer activations, reputation, bond score, and inventory changes.

### Gacha Sessions (gacha combat)
Gacha tower combat sessions with pull results, arc stage progression, entropy density measurements, and ternary braid alignment vectors.

### Architecture Sessions
Detailed explanations of the SCBE-AETHERMOORE 14-layer pipeline, Grand Unified Governance function G(xi, i, poly), PHDM manifold, and runtime governance logic.

### Tongues Sessions
Deep dives into the Six Sacred Tongues (KO, AV, RU, CA, UM, DR): phonotactic structure, byte-to-token mapping algorithms, cross-translation attestation, and phi-weighted scoring.

### Math Sessions
Mathematical foundations: Ternary Braid Algebra (Mirror-Shift-Refactor), 9-state phase diagram, fractal dimension convergence to phi, and emergent pattern analysis.

### Game Design Sessions
Design documents for the isekai game: core loops, minigame systems, emulator hybrid architecture, PollyPad mechanics, and open-source pilot specifications.

### Lore Sessions
World-building for Aethermoor and Everweave: character profiles (Izack, Polly, Clay, Eldrin, Aria, Zara, Kael), deep lore, the Thalorion Compendium, and roleplay session transcripts.

### Music Sessions
Original song compositions with full lyrics, chord progressions, BPM, key, mood, instrument palette, and production notes.

### Bulk SFT (in `all` config only)
Large-scale extracted pairs from the SCBE codebase, governance rules, Spiralverse protocol, Hydra architecture, kernel manifests, Notion workspace exports, and Ouroboros self-improvement logs.

## Usage

### Load with HuggingFace Datasets

```python
from datasets import load_dataset

# Load a specific config
game_data = load_dataset("path/to/training-data", "game_sessions")

# Load all data (default config)
full_data = load_dataset("path/to/training-data", "all")

# Load from local directory
full_data = load_dataset("json", data_files="training-data/**/*.jsonl")
```

### Load a single category

```python
from datasets import load_dataset

arch = load_dataset("json", data_files="training-data/architecture_sessions/*.jsonl")
```

### Convert to chat format for fine-tuning

```python
def to_chat_messages(example):
    return {
        "messages": [
            {"role": "user", "content": example["prompt"]},
            {"role": "assistant", "content": example["response"]},
        ]
    }

chat_data = full_data["train"].map(to_chat_messages)
```

### Use the merged file

After running `scripts/merge_training_data.py`, a deduplicated merged file is available:

```python
from datasets import load_dataset

merged = load_dataset("json", data_files="training-data/merged_sft.jsonl")
```

## Source

All training data is derived from:

- **SCBE-AETHERMOORE** -- 14-Layer Cryptographic-Geometric AI Safety Stack
- **Crystal Cranium v3.0.0** -- PHDM as AI Brain Architecture
- **Aethermoor Game Engine** -- Isekai RPG with Sacred Tongue governance
- **Notion Workspace** -- Research notes, context rooms, and AI coordination

**Author**: Issac Davis
**Repository**: [github.com/issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE)
**Date**: February 2026
