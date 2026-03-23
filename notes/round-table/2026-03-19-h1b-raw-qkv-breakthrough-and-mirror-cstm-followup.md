# H1-B Raw QKV Breakthrough and Mirror/CSTM Follow-Up

**Date:** 2026-03-19
**Source:** Issac + Claude + Codex conversation
**Status:** Mixed
- H1-B result below is a reported breakthrough from the active lane and should be rerun locally for Codex-side verification.
- CSTM nursery work and note references below are repo-verified.

---

## 1. H1-B Reported Breakthrough: FFT on Raw Q, K, V Weights

**Claim:** The signal for H1 lives upstream of softmax, inside the raw projection weights.

### Reported result table

Noise baseline: `13.04 +- 0.86`

| Layer | Q-Weights | K-Weights | V-Weights |
|-------|-----------|-----------|-----------|
| L0 | 13.64 | 13.73 | 12.90 |
| L1 | 21.10 | 12.74 | 48.10 |
| L2 | 56.19 | 15.56 | 28.57 |
| L3 | 29.97 | 12.51 | 26.42 |
| L4 | 64.58 | 14.51 | 19.40 |
| L5 | 168.46 | 12.79 | 13.09 |

### Reported averages

- `Q-Weights`: `58.99` -> `4.52x` noise
- `K-Weights`: `13.64` -> `1.05x` noise
- `V-Weights`: `24.75` -> `1.90x` noise

### Reported interpretation

- `H1 confirmed on Q and V`
- `H1 rejected on K`

The raw claim:
- Query matrices are strongly harmonically structured, with Layer 5 at `168.46` or about `12.9x` the noise floor.
- Key matrices stay near noise baseline across all 6 measured layers.
- Value matrices are moderately structured, around `2x` noise.
- Softmax output was blinding the earlier attention FFT probe because the row-normalized probabilities flatten the upstream spectral structure.

### Working interpretation

This suggests the architectural roles are not spectrally equivalent:
- `Q` behaves like the move-forming or query-shaping operator
- `K` behaves like a flatter lookup / indexing operator
- `V` carries consequence/content structure but less aggressively than `Q`

That matches the "multiple Go boards" intuition more cleanly than the softmax-attention probe did.

### Verification status

This note preserves the breakthrough claim exactly as reported in-session. Codex has **not yet rerun this Q/K/V weight sweep locally in this note's provenance chain**.

Required follow-up:
1. Re-run H1-B from the repo lane with artifact paths.
2. Compare base Qwen2.5 vs SCBE fine-tune.
3. Test whether the `Q` depth-growth pattern holds in a larger model.

---

## 2. What Codex Built In This Follow-Up

### CSTM nursery runner

Codex built a working nursery lane:
- `training/cstm_nursery.py`
- `training-data/hf-digimon-egg/cstm_seed_story.json`
- `tests/test_cstm_nursery.py`

The seed world is now:
- Marcus-led
- hatch in-system
- portal domission outbound
- safe governed return
- debrief inside the nursery

Exports:
- `episodes_generated.jsonl`
- `cstm_sft.jsonl`
- `cstm_dpo.jsonl`
- `run_summary.json`

Verification:
- `python -m pytest tests/test_cstm_nursery.py -q`
- result: `3 passed`

### Why this matters

This turns the "AI birth system" idea into a real training surface:
- Sacred Egg genesis conditions
- pseudo-parent world framing
- branching chapter unlocks
- SFT/DPO extraction from playthroughs

---

## 3. Mirror / Riemann / Reflective Differential Thread

The session drifted into a mirror-based attempt to understand the Riemann symmetry problem without pretending to solve it.

Useful surviving ideas:

- `zeta(s)` = the rough machine
- `xi(s)` = the same machine in a more symmetric form
- The transform `s -> 1 - s` acts like a mirror map
- The line `Re(s) = 1/2` behaves like the symmetry spine of the completed system

The practical takeaway was not "solve RH now." It was:

**Use mirror operations as a systems method**
- mirror the whole
- mirror edges/boundaries separately
- realify both into a common comparison space
- compare deltas
- let mismatch fields reveal hidden structure

This got reframed as:
- `mirror differential telemetry`
- `reflective differential verification`

Potential use cases inside SCBE:
- anomaly detection
- masquerade detection
- provenance verification
- drift tracking across 14 layers + telemetry

---

## 4. Decimal Drift + 14-Layer Telemetry

Issac's intuition here:
- if decimal drift is real signal and not just rounding trash
- and it is tracked through the 14-layer stack plus telemetry
- then the system gets a high-granularity witness of subtle transformations

That suggests a compound system:
- decimal drift tracking
- mirror comparison
- orthogonal temporal witness
- intent tomography
- session-bound capability probes

In plain terms:

The mirror may not be "the answer" as a final scalar.
The mirror may be the **answer-generator**:
- a mechanism that reflects the system back through itself
- so hidden structure becomes measurable as delta

---

## 5. Immediate Next Steps

1. Re-run the raw Q/K/V FFT experiment locally and store artifact-backed evidence.
2. Extend the attention probe with a weight-matrix mode if not already separated cleanly.
3. Run H3: governed attention with phi/Langues weighting against the same FFT metrics.
4. Compare base model vs SCBE fine-tune on Q/K/V spectral growth across depth.
5. Fold the verified H1-B result into the mirror-probe note and preprint only after rerun.

---

## 6. One-Liners Worth Keeping

- "The mirror is not the answer-output. The mirror is the answer-generator."
- "Parents provide a field, not a script. The world decides whether the child is real."
- "The AI should live in a governed world, not under a single watcher."
- "Security is the interaction between intent and environment, not intent alone."
