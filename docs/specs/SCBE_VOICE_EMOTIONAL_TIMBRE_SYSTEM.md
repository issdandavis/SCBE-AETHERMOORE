# SCBE Voice Emotional Timbre System

Status: active draft  
Updated: 2026-03-14  
Scope: Layer 3 Langues metric + Layer 6 breathing transform + Layer 7 phase transform + Layer 14 Audio axis

---

## Purpose

This document defines the voice-side extension of the Langues metric for SCBE-driven text-to-speech, narration, and character dialogue.

The goal is not generic "emotion control." The goal is a governed audio rendering path where:

- the Six Sacred Tongues drive emotional timbre,
- Layer 6 plans breath like a human reader,
- Layer 7 shapes prosodic phase without breaking semantic intent,
- Layer 14 emits an audio-ready control surface for TTS engines.

This spec is designed to sit in front of `scripts/voice_gen_hf.py` and any later Kokoro, Chatterbox, XTTS, or SSML-capable renderer.

---

## Quick Start

For an MVP implementation, do this in order:

1. Resolve a canonical tongue mixture `p` from the line, speaker, and scene.
2. Convert `p` into the timbre vector `T`.
3. Run Layer 6 breath planning at clause boundaries.
4. Run Layer 7 phase shaping to bias timing and stress.
5. Emit one Layer 14 `voice_packet` and let the renderer degrade gracefully if a target engine lacks a control.

If a renderer cannot support a field directly:

- preserve `tongue_mix`, `timbre`, and `breath_plan` in the sidecar,
- map unsupported behavior into pauses and chunk boundaries,
- never silently drop the control packet.

---

## Canonical Layer Mapping

- Layer 3: weighted Langues state
- Layer 6: breath amplitude and respiratory cadence
- Layer 7: prosodic phase offsets and timing curvature
- Layer 14: audio-axis realization into timbre, pauses, breaths, intensity, and telemetry

Layer 14 does not replace Layers 3, 6, or 7. It is the realization layer that turns their governed state into sound.

---

## Design Principle

Speech should sound like someone who means what they are saying and needs air to say it.

That means:

- breaths happen before the voice runs out,
- pauses carry meaning instead of dead silence,
- tongue blends affect body-placement of the sound,
- emotional intensity changes timing, not just pitch,
- phase control nudges delivery rhythm rather than flattening it into a preset.

---

## Input State

For each line or narration segment, define:

- `text`: normalized spoken text
- `speaker`: character or narrator id
- `tongue_logits z in R^6`: raw tongue activation proposal
- `profile`: `lws` or `phdm`
- `scene_intensity e in [0,1]`
- `breath_load b0 in [0,1]`
- `pause_map`: punctuation and clause boundaries
- `speaker_baseline`: default register, rate, and articulation

Tongue order is canonical:

`[KO, AV, RU, CA, UM, DR]`

---

## Minimal Packet Schema

Every voice line should be reducible to one minimal packet:

```json
{
  "speaker": "Narrator",
  "text": "Example line.",
  "profile": "phdm",
  "scene_intensity": 0.42,
  "tongue_logits": { "KO": 0.1, "AV": 0.2, "RU": 0.1, "CA": 0.0, "UM": 0.3, "DR": 0.3 },
  "speaker_baseline": {
    "voice_code": "am_adam",
    "rate": 1.0,
    "pitch_shift_st": 0.0,
    "style": "plain"
  }
}
```

Everything else in this document describes how that packet is expanded into a governed Layer 14 render payload.

---

## Stage 1: Tongue Mixture

Reuse Langues weighting from `docs/LANGUES_WEIGHTING_SYSTEM.md`.

Let `w_l` be the active profile weights and `z_l` the raw tongue activations for the line.

Normalize the emotional mixture:

`p_l = exp(w_l * z_l) / sum_j exp(w_j * z_j)`

where:

- `p_l in (0,1)`
- `sum_l p_l = 1`

This yields a governed tongue mixture instead of a single hard label.

Recommended interpretation:

- KO: warmth, tenderness, chest resonance, cooperative softness
- AV: openness, lift, air, light-facing curiosity
- RU: gravity, lower-center resonance, inherited weight
- CA: sparkle, agility, quick articulation, playful lift
- UM: hollowness, silence tolerance, grief-weighted softness
- DR: forward pressure, jaw-set resolve, hard attack

---

## Stage 2: Emotional Timbre Vector

Map tongue mixture `p` to an emotional timbre vector:

`T = [warmth, brightness, weight, grain, openness, tension, softness, silence_affinity]`

Each component is a weighted sum of tongue basis values:

`T_k = sum_l p_l * M_(l,k)`

where `M` is the tongue-to-timbre basis matrix.

Recommended initial basis:

| Tongue | Warmth | Brightness | Weight | Grain | Openness | Tension | Softness | Silence |
|--------|--------|------------|--------|-------|----------|---------|----------|---------|
| KO | 0.95 | 0.45 | 0.55 | 0.20 | 0.70 | 0.30 | 0.90 | 0.35 |
| AV | 0.55 | 0.85 | 0.30 | 0.15 | 0.95 | 0.25 | 0.70 | 0.40 |
| RU | 0.45 | 0.20 | 0.95 | 0.50 | 0.30 | 0.40 | 0.45 | 0.55 |
| CA | 0.65 | 0.90 | 0.35 | 0.25 | 0.85 | 0.35 | 0.60 | 0.20 |
| UM | 0.40 | 0.25 | 0.70 | 0.35 | 0.35 | 0.50 | 0.80 | 1.00 |
| DR | 0.35 | 0.50 | 0.90 | 0.65 | 0.40 | 0.95 | 0.25 | 0.15 |

Use this vector to drive:

- pitch floor and ceiling
- formant tilt / perceived body placement
- attack softness
- consonant firmness
- pause tolerance
- audible breath probability

---

## Stage 3: Layer 6 Breath Planning

Layer 6 is the respiratory planner. It should decide when the speaker must breathe before the line becomes inhuman.

Define a breath-need score at each clause boundary:

`B_n = sigma(a1*s_n + a2*p_n + a3*e + a4*UM + a5*RU + a6*DR - a7*KO)`

where:

- `s_n` = syllables since last breath, normalized to `[0,1]`
- `p_n` = punctuation pressure at boundary `n`
- `e` = scene intensity
- `UM`, `RU`, `DR`, `KO` are tongue mixture components from `p`
- `sigma` is the logistic function

Default coefficient seed for first implementation:

- `a1 = 2.2`
- `a2 = 1.4`
- `a3 = 1.1`
- `a4 = 1.2`
- `a5 = 0.8`
- `a6 = 1.0`
- `a7 = 0.6`

These are starting values, not canonically fixed constants. They are intended to produce plausible human breathing before model-specific tuning.

Suggested punctuation pressure:

- comma: `0.35`
- em pause / dash: `0.50`
- semicolon / colon: `0.60`
- sentence end: `0.85`
- paragraph break: `1.00`

Breath insertion rule:

- if `B_n >= 0.58`, insert a micro-breath or full breath
- if projected syllable count exceeds 16 without a breath, force a breath candidate
- if projected time exceeds 5.5 seconds without a breath, force a full breath

Breath classes:

- `micro`: 90-160 ms, nearly silent
- `soft`: 160-280 ms, low audibility
- `full`: 280-520 ms, clearly human
- `shaken`: 300-600 ms, intensity-modulated and slightly irregular

Human-read constraint:

No generated line should exceed plausible breath support for the target delivery rate. The breath planner must prefer natural clause boundaries over uniform cadence.

---

## Stage 4: Layer 7 Phase Control

Layer 7 shapes prosodic timing, not lexical meaning.

Define per-line phase offset:

`phi_line = sum_l p_l * phi_l + phi_scene + phi_speaker`

This phase offset modulates:

- onset delay,
- stress placement,
- pause asymmetry,
- rise/fall timing,
- breath recovery timing.

Interpretation guidelines:

- KO shifts toward smoother phrase entries and warmer decays
- AV shifts toward lighter phrase rise and exploratory lift
- RU lengthens phrase settles and anchor syllables
- CA increases agile timing variance and playful rebound
- UM expands silence windows and slower release
- DR sharpens attack timing and compresses hesitation

Hard rule:

Phase modulation may change prosody, but it must not reduce word intelligibility or scramble canonical dialogue intent.

---

## Stage 5: Layer 14 Audio Axis Realization

Layer 14 converts the governed state into engine-facing controls.

Recommended Layer 14 output payload:

```json
{
  "speaker": "Polly (Raven)",
  "text": "Took you long enough.",
  "tongue_mix": { "KO": 0.08, "AV": 0.14, "RU": 0.09, "CA": 0.18, "UM": 0.12, "DR": 0.39 },
  "timbre": {
    "warmth": 0.42,
    "brightness": 0.61,
    "weight": 0.63,
    "grain": 0.41,
    "openness": 0.48,
    "tension": 0.70,
    "softness": 0.29,
    "silence_affinity": 0.24
  },
  "breath_plan": [
    { "index": 0, "kind": "micro", "before_token": "Took", "duration_ms": 110 }
  ],
  "phase": {
    "line_phase": 0.67,
    "pause_skew": 0.18,
    "stress_bias": "front-loaded"
  },
  "render": {
    "rate": 1.02,
    "pitch_shift_st": 0.3,
    "dynamic_range": 0.58,
    "breath_gain_db": -24.0,
    "pause_gain": 0.72,
    "attack_ms": 22,
    "release_ms": 85
  }
}
```

This payload can be converted into:

- Kokoro text chunking and pause insertion,
- Chatterbox-style paralinguistic tags,
- SSML `<break>`, `<prosody>`, and breath markers,
- post-processing envelopes for gain and silence handling.

Renderer fallback rules:

- If the engine has no breath token support, convert `breath_plan` into pause duration plus optional breath-noise post-processing.
- If the engine has no pitch control, preserve timing and pause controls and leave pitch fields in the sidecar for later rendering.
- If the engine has no dynamic-range control, preserve attack/release and pause structure.
- If the engine is fully text-only, split the text into governed chunks and retain the full Layer 14 packet alongside the audio artifact.

---

## Breath Understanding Rules

To make TTS breathe like a human reader, enforce the following:

1. Breath is planned from syntax plus emotional load, not from punctuation alone.
2. A line with grief, awe, or fear should breathe earlier even if punctuation is sparse.
3. Sentence-final pauses are not automatically breaths; they become breaths only if the support model says recovery is needed.
4. UM and RU increase silence tolerance.
5. DR increases pressure and shorter pre-attack preparation, but high DR with high intensity still requires audible recovery after forceful lines.
6. CA favors quick micro-breaths rather than long dramatic pulls.
7. KO suppresses harsh inhalation noise unless scene intensity is high.

---

## Recommended Engine Mapping

### Kokoro / basic TTS engines

Use Layer 14 to drive:

- chunk splitting,
- pause insertion,
- speaking rate,
- punctuation rewrites,
- optional textual breath tokens such as `[breath]` in a preprocessing step.

### Chatterbox / expressive TTS engines

Use Layer 14 to drive:

- expressive tags,
- emotion exaggeration,
- audible breath placement,
- clause-specific pace shifts.

### Voice cloning engines

Treat cloned identity as the speaker baseline and Layer 14 as the runtime modifier.
Do not bake all emotion into the clone itself.

---

## Scene Presets

### Archive discovery

- dominant tongues: `RU + AV`
- breath: measured, sparse, audible only on long clauses
- phase: slow settle, low attack

### Protective confrontation

- dominant tongues: `KO + DR`
- breath: controlled but real, post-line recovery
- phase: firm onset, reduced hesitation

### Grief or threshold scene

- dominant tongues: `UM + RU`
- breath: earlier intake, longer silence windows
- phase: delayed release, downward tail

### Inventive banter

- dominant tongues: `CA + AV`
- breath: quick micro-breaths
- phase: playful asymmetry and faster rebound

---

## Example: Polly First-Line Read

Line:

`Took you long enough.`

Recommended interpretation:

- primary: `DR`
- secondary: `CA`
- trace: `AV`

Why:

- Polly is sardonic, precise, and unimpressed.
- The line should land as a clipped observation, not a theatrical taunt.
- Breath should be minimal, with a tiny pre-line intake if it begins a scene.

Target realization:

- slightly forward attack
- short phrase
- low-to-mid pitch contour
- tight pause after `Took`
- no exaggerated smile-tone

---

## Implementation Notes For `scripts/voice_gen_hf.py`

Recommended future additions:

1. Add a preprocessing layer that converts raw text into a `voice_packet`.
2. Add optional `--tongue-mix`, `--scene-intensity`, and `--breath-style` flags.
3. Emit a sidecar JSON file per line containing Layer 14 controls.
4. Add a `--render-style scbe` mode that uses this spec rather than plain text-only synthesis.

Suggested sidecar filename:

`line.wav.json`

Suggested MVP order:

1. Emit sidecar JSON without changing waveform generation.
2. Use sidecar `breath_plan` to split text into synthesis chunks.
3. Add pause-duration control between chunks.
4. Add pitch/rate/attack mapping for engines that support it.
5. Add optional breath-noise overlays for engines that do not.

---

## Output Contract

Every governed render request should be able to emit:

### StateVector

```yaml
StateVector:
  layer_3_profile: phdm
  tongue_mix:
    KO: 0.08
    AV: 0.14
    RU: 0.09
    CA: 0.18
    UM: 0.12
    DR: 0.39
  layer_6_breath_load: 0.61
  layer_7_phase_offset: 0.67
  layer_14_render_mode: scbe_voice
```

### DecisionRecord

```yaml
DecisionRecord:
  action: ALLOW
  signature: SCBE-VOICE-L14
  timestamp: 2026-03-14T00:00:00Z
  reason: "Line is renderable with governed breath, phase, and timbre controls."
  confidence: 0.84
```

---

## Guardrails

- Do not claim breath realism if breaths are inserted on fixed intervals only.
- Do not flatten all tongue influence into one generic "emotion" slider.
- Do not let phase modulation destroy diction.
- Do not let Layer 14 override canonical character voice maps without explicit speaker-level permission.
- Keep tongue naming and ordering canonical: `KO, AV, RU, CA, UM, DR`.

---

## Action Summary

```yaml
action_summary:
  build:
    files_changed:
      - docs/specs/SCBE_VOICE_EMOTIONAL_TIMBRE_SYSTEM.md
    rationale: "Define a canonical SCBE voice-control spec grounded in Langues weighting, breathing, phase, and Audio axis behavior."
  document:
    files_changed:
      - docs/specs/SCBE_VOICE_EMOTIONAL_TIMBRE_SYSTEM.md
    rationale: "Provide formulas, breath rules, engine mapping, and output contracts for human-style TTS rendering."
  route:
    services_to_update: []
    pending_integrations:
      - "Wire `scripts/voice_gen_hf.py` to emit Layer 14 sidecar voice packets."
      - "Add tests for breath insertion, tongue-mix normalization, and phase-safe timing."
```
