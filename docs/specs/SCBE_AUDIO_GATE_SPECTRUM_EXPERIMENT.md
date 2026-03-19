# SCBE Audio Gate Spectrum Experiment

Last updated: 2026-03-17

## Why this note exists

The repo already has real audio and acoustics primitives:

- [audioAxis.ts](/C:/Users/issda/SCBE-AETHERMOORE/packages/kernel/src/audioAxis.ts)
- [vacuumAcoustics.ts](/C:/Users/issda/SCBE-AETHERMOORE/packages/kernel/src/vacuumAcoustics.ts)
- [temporalIntent.ts](/C:/Users/issda/SCBE-AETHERMOORE/packages/kernel/src/temporalIntent.ts)

But it does **not** yet have a full production audio-generation engine.

So the right move is:

1. state what is already real
2. define what "expand the gate to a spectrum" actually means
3. run controlled tests before claiming voice-quality gains

## What is already real

### Audio Axis

[audioAxis.ts](/C:/Users/issda/SCBE-AETHERMOORE/packages/kernel/src/audioAxis.ts) already computes frame-level features:

- `energy`
- `centroid`
- `flux`
- `hfRatio`
- `stability`

This is a telemetry layer, not a synthesizer.

### Vacuum Acoustics

[vacuumAcoustics.ts](/C:/Users/issda/SCBE-AETHERMOORE/packages/kernel/src/vacuumAcoustics.ts) already provides:

- nodal surface calculations
- cymatic resonance checks
- bottle-beam intensity
- flux redistribution
- standing-wave amplitude
- cavity resonance

This is a spatial/acoustic math layer, not a DAW.

### Harmonic / Temporal layers

[packages/kernel/src/index.ts](/C:/Users/issda/SCBE-AETHERMOORE/packages/kernel/src/index.ts) exposes:

- hyperbolic distance
- breath transform
- phase modulation
- multi-well potential
- harmonic scaling

That is enough to define an audio-governance experiment, not enough to claim "physics-based natural speech rendering" yet.

## Clean interpretation of the idea

"Expand the gate to a spectrum" should mean:

- move from one scalar allow/quarantine/deny score
- to a **banded audio quality/risk profile** across time and frequency

Instead of:

- one final gate score for the whole utterance

Use:

- per-frame spectral telemetry
- per-band drift
- per-band stability
- per-band harmonic-wall pressure
- per-scene spatial resonance checks

## Proposed model

### 1. Audio state vector

For each frame `t`, compute:

`A_t = [energy, centroid, flux, hfRatio, stability, breathPhase, temporalDrift, harmonicCost]`

Where:

- first five come from `audioAxis`
- `breathPhase` comes from Layer 6/7 modulation
- `temporalDrift` comes from timing mismatch
- `harmonicCost` comes from the wall

### 2. Spectrum gate

For each frame, split the spectrum into bands:

- `B1` low / body
- `B2` low-mid / warmth
- `B3` mid / intelligibility
- `B4` upper-mid / presence
- `B5` high / air
- `B6` sibilant / instability edge

Then compute:

`Gate_t = [g1, g2, g3, g4, g5, g6]`

Each `g_i` is not just "good/bad." It is:

- stable
- pressured
- near-break
- quarantined

This matches the intuition that real voices live near boundaries in some bands without collapsing globally.

## Practical meaning of the "vibrato edge"

The earlier conversation is directionally right but too poetic if left ungrounded.

A better engineering interpretation is:

- some bands can approach instability without making the whole frame invalid
- controlled oscillation near a boundary may be desirable
- global failure happens when too many bands cross the threshold together or when the wrong bands destabilize

So:

- `allowed edge` != `failure`
- `spectral pressure` can be a feature
- but it needs bounded monitoring

## Voxel rotation idea

The useful version of "rotate sound through the voxel thing" is:

- map frame-level audio state into a 6D addressable representation
- rotate or traverse that representation under controlled transforms
- compare output coherence before and after rotation

Not:

- "spin sound because it feels right"

Candidate 6D voxel mapping:

`V = [body, clarity, air, phase, pressure, semanticIntent]`

Example:

- `body` from low-band energy
- `clarity` from mid-band intelligibility
- `air` from high-band ratio
- `phase` from temporal phase transform
- `pressure` from drift/harmonic-wall cost
- `semanticIntent` from tongue-weight or prompt class

Then test:

- fixed rotation
- slow phase rotation
- resonance-aligned rotation

Measure:

- stability delta
- intelligibility delta
- coherence delta
- perceived realism delta

## Controlled test batches

Do not jump straight to novel scenes. Use three controls first.

### Control A: Known clean human speech

Input:

- short clean spoken samples
- multiple speakers

Goal:

- establish baseline feature ranges

Measures:

- centroid variance
- flux variance
- hfRatio profile
- frame stability histogram

### Control B: Known synthetic TTS

Input:

- flat TTS
- emotional TTS
- multi-speaker TTS

Goal:

- measure where synthetic speech diverges from the clean human baseline

### Control C: Processed synthetic TTS through SCBE audio stack

Input:

- same TTS samples
- add SCBE band gate, breath/phase modulation, optional voxel rotation

Goal:

- determine whether the processed output moves closer to the human baseline or just becomes stranger

## Evaluation criteria

Use both machine and human checks.

### Machine-side

- word error rate / Whisper re-transcription
- spectral coherence drift
- per-band gate profile
- timing regularity
- resonance consistency

### Human-side

- intelligibility
- emotional plausibility
- room believability
- "sounds alive" rating
- "sounds broken" rating

## Pivot log integration

The pivot or long-form conversation logs should not go directly into audio generation.

Use them for:

- emotional state labeling
- relationship context
- pause/hesitation patterns
- control vs collapse patterns
- recurring lexical and semantic motifs

Then derive:

- intent labels
- scene-phase labels
- allowed edge-pressure ranges
- per-character temporal pacing priors

That is the safe bridge from lore logs to audio experiments.

## What not to claim yet

Do not claim yet that:

- the 14-layer pipeline is already a complete audio engine
- harmonic wall alone creates natural vibrato
- voxel rotation improves voice realism

Those are hypotheses until tested.

## Immediate next implementation

1. Add a small TS or Python experiment runner that:
   - loads WAV
   - computes audioAxis features per frame
   - derives 6 band metrics
   - emits JSON telemetry

2. Add an "audio gate spectrum" report:
   - per-band state over time
   - flagged instability windows
   - recommended corrective action

3. Add optional voxel projection:
   - map frame to 6D
   - apply deterministic rotation
   - compare before/after telemetry

4. Run the three-control experiment set before touching full narrative scenes

## Bottom line

The strong version of the idea is not:

- "SCBE is secretly already a DAW"

It is:

- SCBE already has enough signal-processing, harmonic, and spatial primitives to support a serious controlled audio-governance experiment.

That is worth building.
