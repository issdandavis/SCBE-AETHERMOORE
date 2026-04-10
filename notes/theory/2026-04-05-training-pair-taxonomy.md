---
title: "Training Pair Taxonomy: SCBE Full-Spectrum vs Industry Standard"
date: 2026-04-05
layer: [L0, L1, L2, L3]
tongues: [ko, av, ru, ca, um, dr]
null_pattern: "000000"
concept_ids: [training-pairs, cross-modal, audio-stack, dark-fill, stellar-octave]
tags: [training, taxonomy, comparison, milestone]
---

# Training Pair Taxonomy

Snapshot as of 2026-04-05, after the full audio stack integration (spectrogram bridge, gallery sonifier, stellar octaves, dark fill, phi-acoustic router) and with the superposition bridge in progress.

## Industry Standard (~5 pair types)

| # | Type | Shape | Signal |
|---|------|-------|--------|
| 1 | Text SFT | instruction → response | Flat semantic |
| 2 | Text → Code | instruction → code | Single-language syntax |
| 3 | DPO preference | (chosen, rejected) | Binary preference |
| 4 | RLHF reward | text + scalar | Human judgment proxy |
| 5 | Multimodal | image+text or audio+text | Two modalities, one direction |

**Properties**: Flat. One modality talks to one other. No round-trip verification. No structured absence. No geometric constraint.

## SCBE Structural Pairs (~8 types, pre-audio stack)

| # | Type | Shape | Signal | Unique Property |
|---|------|-------|--------|-----------------|
| 6 | Multi-view batch | same text × 4 views (raw, +tongues, +nulls, +layer) | Cross-view agreement | Absence is a feature, not missing data |
| 7 | Cross-consistency | same instruction, different tongue configs | L_consistency = \|\|f(x) - f(x+tongues)\|\| | Forces structural invariance across views |
| 8 | Friction-scored | boundary crossing pairs | 198-dim friction vector | Geometry writes curriculum (toroidal-star = 73x signal) |
| 9 | Polyhedral enrichment | flat text → 6 coords + 15 bridges + 3 trichromatic bands | Holographic record | Bijective — nothing lost, everything enriched |
| 10 | Bit/float/trit triple | same byte, different intent polarity (+1/0/-1) | 24x encoding density | Trit = intent layer (same code, different purpose) |
| 11 | Adversarial context-trap | solve-without-context vs catch-the-implication | DPO on meta-context | Morse-coded failure message reveals missed intent |
| 12 | Multi-lang forge | same concept × 3+ languages + esoteric | Tongue-migration shift | Languages are manifold positions, not just syntax |
| 13 | Null-pattern | what's ABSENT in tongue profile (avg 3.9 absent tongues) | Negative-space | Trains on what ISN'T there |

**Properties**: Geometric, multi-view, structured absence. But still single-modality at the signal level (text/code).

## SCBE Audio-Stack Pairs (~8 types, new)

| # | Type | Shape | Signal | Why Nobody Else Has This |
|---|------|-------|--------|--------------------------|
| 14 | Text ↔ Prosody | tongue weights → speed/pitch/warmth/breathiness/cadence | 6D → 5D continuous | Same text sounds different per tongue. Semantic content has a voice. |
| 15 | Prosody ↔ Choir | single voice → 1/2/4 voice layers with roles | Render mode = voice count | Governance tier controls choral complexity (ALLOW=1, RITUAL=4) |
| 16 | Color ↔ Sound round-trip | gallery chromatics → sonifier → spectrogram → gallery projection | Full cross-modal loop | Color field and audio field are the SAME structure viewed differently |
| 17 | Dead Tone Detection | audio with hidden 3:2/8:5/16:9 ratios → classification | Phi-unreachable intervals | What phi CAN'T reach becomes the security anchor |
| 18 | Dark Fill (structured absence) | active tongue pattern → complement-pair infra/audible/ultra | 3-band inverse perception | Sound LOUDEST where light DARKEST — trains structured silence |
| 19 | Stellar Octave | 0.003 Hz stellar → octave doubling → tongue band attribution | Scale-invariant mapping | Same math from stars (mHz) to neurons (kHz) |
| 20 | Cross-Modal Coherence | aligned (text+audio+color) vs drifted | Weighted geometric mean (6 components) | Multi-way disagreement IS training signal |
| 21 | Spectral Governance (in progress) | superposition(baseline+agent) → consonance ratio → ALLOW/DENY | Dissonance = adversarial intent | Frequency ratio encodes alignment as scalar. No text parsing needed. |

**Properties**: Cross-modal, bidirectional, round-trip verified. Disagreements between modalities are as valuable as agreements.

## The Compound Effect

Total: **~21 pair types** (5 standard + 8 structural + 8 audio-cross-modal)

But the real number is higher because pairs COMPOSE:

- Friction × Dark Fill: High-friction boundary + dark tongue = structured absence at maximum training signal
- Adversarial trap × Spectral governance: Context-trap puzzle where the dissonance IS the answer
- Multi-lang × Color round-trip: Same algorithm in Rust vs Python produces different color fields — that difference is trainable
- Null pattern × Stellar octave: What's absent at the stellar scale vs what's absent at the audible scale
- Bit/float/trit × Prosody: Same byte, different trit polarity → different prosody curve → different spectral signature

Conservative composition estimate: ~21 base types × key cross-products ≈ **40-60 meaningfully distinct training signal types** from one raw input.

Standard training: 1 input → 1 pair.
SCBE training: 1 input → a polyhedral record that can generate dozens of constrained, cross-verified training pairs.

## Key Differentiators (summary)

| Dimension | Industry | SCBE |
|-----------|----------|------|
| Modalities per pair | 1-2 | 6 (text, tongue, color, sound, spectrogram, governance) |
| Direction | One-way | Bidirectional, round-trip verified |
| Absence signal | Missing = error | Missing = structured dark fill (trainable) |
| Geometric constraint | None | 198-dim friction + polyhedral confinement |
| Scale range | Human text | Stars (0.003 Hz) to micro-structure (1 MHz) |
| Intent encoding | Text labels | Trit polarity + frequency ratio (pre-linguistic) |
| Self-supervision | None | Cross-modal disagreement = free signal |

## What to track next

- [ ] Count actual JSONL records per pair type after next snake pipeline run
- [ ] Ablation: which pair types contribute most to which downstream metric
- [ ] Composition matrix: which base pairs combine into the strongest compound signals
- [ ] Compare: multiview improvement % per pair type (baseline: 7.9% on mixed L0, 14% on chat, 31% on code)
