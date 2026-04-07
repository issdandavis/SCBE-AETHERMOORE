# AUDIO SYSTEM STACK — Interface Contracts v1.1

Frozen: 2026-04-05
Covers: L14 Audio Axis full-spectrum pipeline (stellar → dark fill → prosody → choir → sonification → spectrogram → phi-router → feedback)

---

## Module Map

```
stellar frequencies (0.003 Hz)
    │
    ▼
┌──────────────────────────┐
│  stellar_octave_mapping   │ ← Constant 4: f_human = f_stellar × 2^n
│  (star → audible octaves) │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  harmonic_dark_fill       │ ← Tri-braid: infra (0.01-20 Hz) / audible / ultra (20k-1M Hz)
│  (dark zones → 3-band)   │
└──────────┬───────────────┘
           │
           ▼
text/governance decision ──────────────────────────────────────────────────┐
    │                                                                      │
    ▼                                                                      │
┌───────────────────┐     ┌──────────────────────┐                        │
│  tongue_prosody    │────▶│  speech_render_plan   │                        │
│  (6D → 5D voice)  │     │  (plan + earcon)      │                        │
└───────────────────┘     └──────────┬───────────┘                        │
                                     │                                     │
                                     ▼                                     │
                          ┌──────────────────────┐                        │
                          │  choral_render        │                        │
                          │  (multi-voice layers) │                        │
                          └──────────┬───────────┘                        │
                                     │                                     │
              ┌──────────────────────┤                                     │
              ▼                      ▼                                     │
┌──────────────────┐   ┌──────────────────────────┐                       │
│ gallery_chromatics│   │  gallery_sonifier        │                       │
│ (visual field)   │   │  (color→audio params)    │                       │
└────────┬─────────┘   └──────────┬───────────────┘                       │
         │                        │                                        │
         │        ┌───────────────┘                                        │
         ▼        ▼                                                        │
┌──────────────────────────┐                                              │
│  spectrogram_bridge      │                                              │
│  (audio→gallery coords)  │                                              │
└──────────┬───────────────┘                                              │
           │                                                               │
           ▼                                                               │
┌──────────────────────────┐     ┌──────────────────────────┐             │
│  world_bundle            │     │  phi_acoustic_router      │◀────────────┘
│  (compact training state)│◀────│  (personality → standing  │
└──────────────────────────┘     │   waves, 7 tuning systems)│
                                 └──────────────────────────┘
```

### Frequency Ladder (full spectrum)

```
Sun p-mode ─── 0.003 Hz ──┐
Red giant ──── 0.00005 Hz  │  stellar_octave_mapping
White dwarf ── 0.001 Hz    │  (Constant 4: f × 2^n)
Neutron star ─ 100 Hz ─────┘
        │
        ▼  (octave transposition)
┌───────────────────────────────────────────────────────────────────────┐
│                    harmonic_dark_fill bands                           │
│  INFRASONIC (IR)   │  AUDIBLE (Visible)  │  ULTRASONIC (UV)         │
│  0.01 - 20 Hz      │  20 - 20,000 Hz     │  20,000 - 1,000,000 Hz  │
│  slow state         │  6 Sacred Tongues   │  micro-structure hash    │
│  long memory        │  phi-weighted freq  │  fast state              │
└───────────────────────────────────────────────────────────────────────┘
        │                      │                       │
        └──────────┬───────────┘                       │
                   ▼                                   │
          tongue_prosody → choral → sonifier           │
          spectrogram_bridge (audible band)             │
                   │                                   │
                   └───────────┬───────────────────────┘
                               ▼
                      phi_acoustic_router
                  (personality standing waves)
```

---

## 1. tongue_prosody

**File**: `src/audio/tongue_prosody.py`
**Version**: 1.0.0

### Input
| Name | Type | Range | Source |
|------|------|-------|--------|
| `weights` | `TongueWeightVector` | 6 floats, unclamped | Langues metric or manual |
| `base_speed` | `float` | 0.5–2.0 | Caller default 1.0 |
| `base_pitch` | `float` | -12.0–12.0 semitones | Caller default 0.0 |

### Output: `ProsodyParams` (frozen)
| Field | Type | Range | Derivation |
|-------|------|-------|------------|
| `speed` | `float` | 0.5–2.0 | `base * (1 + 0.1*(KO - UM))` |
| `pitch_semitones` | `float` | -12.0–12.0 | `base + CA*2 - DR` |
| `warmth` | `float` | 0.0–1.0 | `AV / (AV + RU + eps)` |
| `breathiness` | `float` | 0.0–1.0 | `UM * 0.3` |
| `cadence` | `str` | staccato/flowing/steady/measured/grounded | Dominant tongue threshold |

### Side Functions
| Function | In | Out |
|----------|-----|-----|
| `governance_voice(decision)` | `str` (ALLOW/QUARANTINE/ESCALATE/DENY) | `str` voice ID |
| `tongue_dominant(weights)` | `TongueWeightVector` | `str` tongue code |

### Invariants
- `validate()` on output never raises for any valid `TongueWeightVector`
- Governance voice always returns a string (fallback: "narrator")
- TONGUE_WEIGHTS are phi-scaled: KO=1.000, AV=1.618, RU=2.618, CA=4.236, UM=6.854, DR=11.090

---

## 2. speech_render_plan

**File**: `src/crypto/speech_render_plan.py`
**Version**: 1.0.0

### Input
| Name | Type | Range | Source |
|------|------|-------|--------|
| `text` | `str` | non-empty | Utterance to render |
| `dominant_tongue` | `str` | ko/av/ru/ca/um/dr | Langues metric or caller |
| `dead_tone` | `str` | perfect_fifth/minor_sixth/minor_seventh/other | Gallery ambient |
| `excitation` | `float` | 0.0–∞ (clamped internally) | QHO excitation level |

### Output: `SpeechRenderPlan` (frozen)
| Field | Type | Range | Derivation |
|-------|------|-------|------------|
| `text` | `str` | non-empty | Passthrough |
| `dominant_tongue` | `str` | 6 tongues | Passthrough |
| `dead_tone` | `str` | any | Passthrough |
| `excitation` | `float` | any | Passthrough |
| `profile` | `TongueVoiceProfile` | see below | Built from base + excitation |
| `pre_tone_hz` | `Optional[float]` | 330/352/392 or None | `DEAD_TONE_PRETONES.get()` |
| `stereo_pan` | `float` | -1.0–1.0 | `TONGUE_PAN[tongue]` |

### TongueVoiceProfile (frozen)
| Field | Type | Range |
|-------|------|-------|
| `tongue` | `str` | 6 tongues |
| `voice_name` | `str` | alloy/verse/ember/aria/shade/stone |
| `rate` | `float` | 0.7–1.3 |
| `pitch_semitones` | `float` | unclamped |
| `energy` | `float` | 0.0–1.0 |
| `breathiness` | `float` | 0.0–1.0 |
| `pause_ms` | `int` | >=0 |

### Constants
| Name | Value | Purpose |
|------|-------|---------|
| `DEAD_TONE_PRETONES` | {perfect_fifth: 330, minor_sixth: 352, minor_seventh: 392} | Earcon Hz |
| `TONGUE_PAN` | {ko: -0.6, dr: -0.4, av: 0.0, um: 0.0, ru: 0.4, ca: 0.6} | Stereo position |
| `ALL_TONGUES` | frozenset of 6 | Canonical tongue set |

### Invariants
- Excitation modulates rate by ±0.03 per unit from neutral 3.0
- Excitation modulates energy by +0.04 per unit
- Rate clamped to [0.7, 1.3], energy clamped to [0.0, 1.0]
- `validate()` checks all bounds

---

## 3. choral_render

**File**: `src/crypto/choral_render.py`
**Version**: 1.0.0

### Input: `build_choral_plan()`
| Name | Type | Range |
|------|------|-------|
| `phonemes` | `List[PhonemeToken]` | non-empty |
| `tongue` | `str` | 6 tongues |
| `excitation` | `float` | 0.0–∞ |
| `mode` | `RenderMode` | PLAIN_SPEECH/SPEECH_SONG/CHORAL_RITUAL |

### Output: `ChoralRenderPlan` (frozen)
| Field | Type | Details |
|-------|------|---------|
| `phonemes` | `tuple[PhonemeToken]` | Frozen from input |
| `prosody` | `ProsodyPlan` | Built by `build_prosody()` |
| `voices` | `tuple[VoiceLayer]` | 1, 2, or 4 layers |
| `tongue` | `str` | Passthrough |
| `mode` | `RenderMode` | Passthrough |

### Voice Layer Counts (FIXED)
| Mode | Count | Roles |
|------|-------|-------|
| PLAIN_SPEECH | 1 | LEAD |
| SPEECH_SONG | 2 | LEAD + SHADOW |
| CHORAL_RITUAL | 4 | LEAD + SHADOW + DRONE + HARMONY |

### Prosody Stress Patterns (FIXED)
| Tongue | Pattern | Curve Shape |
|--------|---------|-------------|
| KO | even | flat 0.5 |
| AV | flowing | sinusoidal |
| RU | percussive | alternating 0.8/0.4 |
| CA | rising | ascending 0.5→1.0 |
| UM | falling | descending 1.0→0.5 |
| DR | grounded | flat 0.3 |

### Invariants
- All voice gains in [0.0, 1.0], all pans in [-1.0, 1.0]
- `ProsodyPlan.rate` in [0.5, 2.0]
- `ProsodyPlan.energy` in [0.0, 1.0]
- `ProsodyPlan.chant_ratio` in [0.0, 1.0]
- Harmony voice pans opposite to lead (for stereo width)
- Drone voice always pans center (0.0)

---

## 4. gallery_chromatics

**File**: `src/crypto/gallery_chromatics.py`
**Version**: 1.0.0

### Input: `compute_gallery_color_field()`
| Name | Type | Source |
|------|------|--------|
| `gallery_notes` | `Dict[str, GalleryAmbientNote]` | QuantumFrequencyBundle |
| `tongue_coefficients` | `Dict[str, float]` | QHO state amplitudes |

### Output: `GalleryColorField` (immutable fields)
| Field | Type | Range |
|-------|------|-------|
| `left_iris` | `ChromaticIris` | 12 colors (3 tones × 4 materials) |
| `right_iris` | `ChromaticIris` | 12 colors |
| `cross_eye_coherence` | `float` | [0.0, 1.0] |
| `dominant_material` | `str` | matte/fluorescent/neon/metallic |
| `spectral_coverage` | `float` | [0.0, 1.0] fraction of 360° hue wheel |

### Dual-Eye Seeding (FIXED)
| Eye | Seed Tongues | Sees |
|-----|-------------|------|
| Left | KO, DR | Structure, form, dependency |
| Right | RU, CA | Creativity, novelty, urgency |
| Bridge | AV, UM | Stability (shared phase) |

### Color Generation Pipeline
```
ratio → log_phi(ratio) → harmonic_number
    → golden_angle_spiral → (θ, r)
    → scatter_4_colors(90° spacing, tongue_phase) → [LabColor × 4]
```

### Invariants
- 24 total color points (2 irises × 3 tones × 4 materials)
- Tongue phases are phi-scaled: KO=0, AV=TAU/φ, RU=TAU/φ², CA=TAU/φ³, UM=TAU/φ⁴, DR=TAU/φ⁵
- All LabColor.L in [0, 100]
- Material order: matte, fluorescent, neon, metallic

---

## 5. gallery_sonifier

**File**: `src/audio/gallery_sonifier.py`
**Version**: 1.0.0

### Input: `color_to_audio()`
| Name | Type | Range |
|------|------|-------|
| `color` | `LabColor` | Any valid CIELAB |
| `material` | `str` | matte/fluorescent/neon/metallic |
| `pan` | `float` | [-1.0, 1.0] |
| `reverb` | `float` | [0.0, 1.0] |
| `delay_ms` | `int` | >=0 |

### Output: `AudioParams` (frozen)
| Field | Type | Range | Derivation |
|-------|------|-------|------------|
| `frequency_hz` | `float` | 100–4000 | `hue_to_frequency(hue_degrees)` log scale |
| `amplitude` | `float` | [0.0, 1.0] | `chroma / 130` |
| `attack_ms` | `int` | 2–50 | Material ADSR |
| `decay_ms` | `int` | 50–200 | Material ADSR |
| `sustain` | `float` | [0.6, 0.9] | Material ADSR |
| `release_ms` | `int` | 100–500 | Material ADSR |
| `reverb` | `float` | [0.0, 1.0] | Passthrough |
| `delay_ms` | `int` | >=0 | Passthrough |
| `pan` | `float` | [-1.0, 1.0] | Passthrough |

### Dead Tone Sonification (FIXED)
| Dead Tone | Base Hz | Envelope | Reverb | Delay |
|-----------|---------|----------|--------|-------|
| perfect_fifth | 330 | pulse (2Hz rate) | 0.1 | 0ms |
| minor_sixth | 352 | dissonance | 0.3 | 0ms |
| minor_seventh | 392 | echo | 0.7 | 250ms |

### Invariants
- `hue_to_frequency()` is monotonically increasing on [0, 360] → [100, 4000]
- Log scale: equal hue distance = equal perceived pitch distance
- `validate()` checks all AudioParams bounds

---

## 6. spectrogram_bridge

**File**: `src/audio/spectrogram_bridge.py`
**Version**: 1.0.0

### Input: `analyze_audio()`
| Name | Type | Source |
|------|------|--------|
| `filepath` | `str` | Path to .wav file |
| `fft_size` | `int` | Default 2048 |
| `hop_size` | `int` | Default 512 |

### Output: `SpectrogramAnalysis`
| Field | Type | Details |
|-------|------|---------|
| `frames` | `List[SpectrogramFrame]` | Per-frame tongue attribution |
| `tongue_profile` | `Dict[str, float]` | Normalized aggregate [0, 1] |
| `dominant_tongue` | `str` | Max tongue |
| `mean_centroid` | `float` | Hz |
| `mean_hf_ratio` | `float` | [0, 1] |

### Tongue-Frequency Bands (FIXED)
| Tongue | Range (Hz) | Acoustic Character |
|--------|-----------|-------------------|
| DR | 20–150 | Earthquake, sub-bass |
| UM | 150–400 | Wind hum, low resonance |
| RU | 400–1000 | Water flow, mid authority |
| KO | 1000–2500 | Fire crackle, voice clarity |
| AV | 2500–6000 | Bird song, overtones |
| CA | 6000–20000 | Electrical hiss, precision |

### Gallery Projection: `project_frame_to_gallery()`
| Audio Feature | Gallery Coordinate | Mapping |
|--------------|-------------------|---------|
| Spectral centroid | Hue (0–360°) | `freq_to_hue()` log scale |
| Total energy | Chroma (0–130) | `energy_to_chroma()` sqrt scale |
| Spectral centroid | Lightness (20–80) | `centroid_to_lightness()` |
| Dominant tongue | Material | Fixed map: DR/UM→matte, RU→metallic, KO/AV→fluorescent, CA→neon |

### Invariants
- Tongue bands are contiguous: 20 → 150 → 400 → 1000 → 2500 → 6000 → 20000 Hz
- Bands cover full audible range (20 Hz – 20 kHz)
- `freq_to_hue()` is the inverse of `gallery_sonifier.hue_to_frequency()`
- All GalleryProjection fields within documented bounds
- `generate_test_signal()` produces normalized [-1, 1] output

---

## 7. world_bundle

**File**: `src/crypto/world_bundle.py`
**Version**: 1.0.0

### Factory: `create_default_bundle()`
Returns `WorldBundle` with:
- 6 tongue phonologies (ko/av/ru/ca/um/dr)
- 3 render presets (speech/speech_song/choral_ritual)
- Empty lexicon and grammar per tongue
- Zero alignment, zero circulation passes

### Circulation: `bundle.circulate(method, sections, output, alignment_delta)`
| Param | Type | Purpose |
|-------|------|---------|
| `method` | `str` | grammar/prosody/harmonic/adversarial/ritual/integration |
| `sections` | `List[str]` | Which sections were read |
| `output` | `Any` | Gets SHA-256 hashed (first 16 hex chars) |
| `alignment_delta` | `float` | Clamped to [-1, 1] |

### Alignment Score
- Exponential moving average with phi decay over all passes
- Most recent pass has weight 1.0, each earlier pass × 1/φ
- Final score clamped to [-1.0, 1.0]

### Invariants
- `tongue_count` always 6 for default bundle
- `alignment_score` in [-1.0, 1.0]
- Each `CirculationPass.output_hash` is 16 hex characters
- Different outputs produce different hashes
- `to_dict()` always contains: bundle_version, tongue_count, total_vocabulary, total_rules, circulation_count, alignment_score, render_presets, sections

---

## 8. stellar_octave_mapping

**File**: `src/symphonic_cipher/audio/stellar_octave_mapping.py`
**Version**: 1.0.0

### Core Formula (Constant 4)
```
f_human = f_stellar × 2^n
where n = round(log₂(target / stellar))
```

### Input: `transpose()`
| Name | Type | Range | Source |
|------|------|-------|--------|
| `f_stellar` | `float` | >0 Hz | Stellar oscillation frequency |
| `target_freq` | `Optional[float]` | >0 Hz or None | Target audible frequency (default: geometric mean of 20-20k) |

### Output: `OctaveTranspositionResult` (frozen)
| Field | Type | Range | Derivation |
|-------|------|-------|------------|
| `stellar_freq` | `float` | >0 | Passthrough |
| `target_freq` | `float` | >0 | Passthrough or `√(20×20000)` |
| `octaves` | `int` | any | `round(log₂(target/stellar))` |
| `human_freq` | `float` | >0 | `stellar × 2^octaves` |
| `period_stellar` | `float` | >0 | `1/stellar` |
| `period_human` | `float` | >0 | `1/human` |
| `period_ratio` | `float` | >0 | `period_stellar/period_human` |

### Stellar Frequencies (FIXED)
| Body | Frequency (Hz) | Octaves to Audible |
|------|---------------|-------------------|
| sun_p_mode | 0.003 | ~16 |
| sun_g_mode | 0.0001 | ~21 |
| red_giant | 0.00005 | ~22 |
| white_dwarf | 0.001 | ~17 |
| neutron_star | 100.0 | 0 (already audible) |

### Side Functions
| Function | In | Out |
|----------|-----|-----|
| `transpose_to_note(f_stellar, note)` | stellar Hz + note name | `OctaveTranspositionResult` |
| `is_audible(f_human)` | Hz | `bool` (20-20k range) |
| `stellar_pulse_protocol(body)` | body name | Protocol dict with pulse Hz, period, entropy mode |
| `entropy_regulation_sequence(body, duration)` | body + seconds | Pulse schedule with times array |
| `stellar_camouflage_frequencies(body, n)` | body + count | List of audible harmonics |

### Invariants
- `transpose()` always returns an audible result for any stellar frequency via octave doubling
- `octaves` = exact `round(log₂(target/stellar))` — deterministic for given inputs
- Audible range: [20.0, 20000.0] Hz
- Musical notes: C3=130.81, C4=261.63, A4=440.0, C5=523.25
- `stellar_pulse_protocol()` guarantees `is_audible == True` in output

---

## 9. harmonic_dark_fill

**File**: `src/crypto/harmonic_dark_fill.py`
**Version**: 1.0.0

### Core Principle
**Amplitude is inverse of activation.** Sound is loudest where light is darkest. Dark tongues get structured harmonic fill instead of silence.

### Input: `compute_harmonic_fill()`
| Name | Type | Range | Source |
|------|------|-------|--------|
| `byte_val` | `int` | 0-255 | Data byte at position |
| `tongue_code` | `str` | 6 tongues | Which tongue to fill |
| `position` | `int` | >=0 | Position in sequence |
| `total_positions` | `int` | >=1 | Sequence length |
| `darkness` | `float` | [0.0, 1.0] | Tongue darkness at position |
| `neighbor_phases` | `Optional[Dict[str, float]]` | radians | Phase angles from active neighbors |

### Output: `HarmonicFill` (frozen)
| Field | Type | Range | Derivation |
|-------|------|-------|------------|
| `infra_freq` | `float` | [0.01, 20] Hz | `base_freq/1000 × (1 + 0.5×sin(2πt))` |
| `infra_amplitude` | `float` | [0.0, 0.8] | `darkness × 0.8` |
| `infra_phase` | `float` | [0, 2π) | `(2π×t×φ) mod 2π` |
| `audible_freq` | `float` | [20, 20000] Hz | `base × interval × (1 + 0.1×nodal)` |
| `audible_amplitude` | `float` | [0.0, 1.0] | `darkness × (0.6 + 0.4×|nodal|)` |
| `audible_phase` | `float` | [0, 2π) | Locked to complement or positional |
| `ultra_freq` | `float` | [20000, 1000000] Hz | SHA-256 hash derived |
| `ultra_amplitude` | `float` | [0.0, 0.9] | `darkness × (weight/φ⁵) × 0.9` |
| `ultra_phase` | `float` | [0, 2π) | Hash derived (deterministic) |

### Three Frequency Bands (FIXED)
| Band | Range | Purpose | Connection |
|------|-------|---------|------------|
| Infrasonic (IR) | 0.01 – 20 Hz | Slow state, long memory | 6-8 octaves above Sun p-mode |
| Audible (Visible) | 20 – 20,000 Hz | Sacred Tongue frequencies | Tongue phi-weighted |
| Ultrasonic (UV) | 20,000 – 1,000,000 Hz | Micro-structure hash | Fast state computation |

### Complement Tongue Pairs (FIXED — voice leading)
| Tongue | Complement | Semantic Bridge |
|--------|-----------|-----------------|
| KO | DR | Intent ↔ Structure |
| AV | UM | Wisdom ↔ Security |
| RU | CA | Governance ↔ Compute |

### Base Audible Frequencies (FIXED)
| Tongue | Hz | Note |
|--------|-----|------|
| KO | 440.00 | A4 |
| AV | 523.25 | C5 |
| RU | 293.66 | D4 |
| CA | 659.25 | E5 |
| UM | 196.00 | G3 |
| DR | 392.00 | G4 |

### Sound Strand Packing: `as_sound_strands()`
```
strand_a = (audible_freq, audible_amp, audible_phase)    → human-perceptible
strand_b = (infra_freq, infra_amp, infra_phase)          → IR slow-state (AI-only)
strand_c = (ultra_freq, ultra_amp, ultra_phase)          → UV fast-state (AI-only)
```

### Side Functions
| Function | In | Out |
|----------|-----|-----|
| `compute_darkness(byte, tongue, activations)` | byte + tongue + optional activation dict | `float` [0, 1] |
| `upgrade_sound_bundle(byte, tongue, pos, total, darkness, neighbors)` | Full context | 3-tuple of (freq, amp, phase) strands |
| `fill_dark_nodes(data, activations)` | byte sequence + optional activations | `List[Dict[str, HarmonicFill]]` |
| `sequence_spectrum(data, activations)` | byte sequence | `List[SpectrumSnapshot]` |
| `voice_leading_interval(from, to)` | two tongue codes | `float` ratio normalized to [1.0, 2.0) |
| `nearest_musical_interval(ratio)` | `float` | `(name, deviation)` |
| `nodal_surface_value(x1, x2, n, m, L)` | 2D position + mode numbers | `float` (0 at dark nodes) |

### Invariants
- Sound bundle is NEVER all-zero for any input byte (strand_b and strand_c always have structure)
- Infrasonic amplitude > audible amplitude at maximum darkness (0.8 > 0.6 × max)
- Higher-weight tongues produce louder ultrasonic (more computational resolution)
- Complement pairs provide voice-leading phase coherence
- All fills are deterministic for same inputs (SHA-256 hashing for ultra band)
- Band boundaries: 0.01 / 20 / 20,000 / 1,000,000 Hz
- Musical interval vocabulary: 14 intervals from unison (1:1) to octave (2:1) including phi (φ:1)

---

## 10. phi_acoustic_router

**File**: (spec only — `docs/specs/PHI_ACOUSTIC_ROUTER_SPEC.md`)
**Version**: 0.2.0 (architecture spec)
**Status**: Spec frozen, implementation pending

### Core Formula: Harmonic Wave Propagation
```
ψ_ij(t) = A × sin(2π × f_phi × t + φ_phase) × exp(-γ × t)
```
Where:
- `f_phi` = golden-ratio-scaled frequency
- `γ` = stakeholder-cost-governed damping
- Personality states settle at standing wave nodes (convergence zones)

### Acoustic Energy Function
```
E_phi_acoustic(z, u | p) = E_cross_lattice(z, u | p) + ν × D(F(ψ_dual(z)))
```
Where `F` = Fourier transform, `D` = musical dissonance metric (Helmholtz/Sethares).

### Tuning Systems (FIXED set, pluggable selection)
| System | Best For | Default |
|--------|----------|---------|
| Just 5-limit | Pure thirds, human warmth | No |
| Pythagorean | Stacked fifths, self-similar | **Yes** (phi-lattice default) |
| 12-TET | Library compatibility | No |
| Phi-Fibonacci | Maximum self-similarity | No |
| 7-limit Just | Extended harmonics | No |
| Bohlen-Pierce | Non-octave (tritave 3:1) | No |
| Adaptive | Dynamic epsilon per cost | No |

### Trim Pattern Verification (FIXED chord signatures)
| Chord | Ratio | Meaning |
|-------|-------|---------|
| Perfect fifth | 3:2 | Safe trim |
| Major third | 5:4 | Convergent state |
| Tritone | ~1.41 | Governance violation |

### L14 Integration Points
| Existing Module | Integration |
|----------------|-------------|
| `audioAxis.ts` | Add phi-scaled frequency ratios to FFT analysis |
| `vacuumAcoustics.ts` | Personality states settle at cymatic nodal lines |
| `AudioAxisProcessor.computeDFT()` | Feed output to dissonance detector |
| `nodalSurface()` | Personality equilibrium = standing wave zeros |

### Invariants
- Dissonance = high energy = automatic pruning (unstable personality)
- Consonance = harmonic attunement = stable personality
- Support decay only occurs in convergence zones: `support × exp(-(E+D)/τ_φ) × 1_{zone}`
- Every trim exports spectrogram + chord label (auditable)
- 7 tuning systems enumerated; selection is runtime parameter, set is frozen

---

## Cross-Module Consistency Rules

1. **Tongue Set**: All modules use the same 6 tongues: ko, av, ru, ca, um, dr
2. **Dead Tone Set**: All modules use the same 3 tones: perfect_fifth, minor_sixth, minor_seventh
3. **Material Set**: All modules use the same 4 materials: matte, fluorescent, neon, metallic
4. **Frequency Mapping**: `spectrogram_bridge.freq_to_hue()` is the inverse of `gallery_sonifier.hue_to_frequency()`
5. **Stereo Layout**: Left panning for KO/DR (structure), right for RU/CA (creativity), center for AV/UM (bridge)
6. **Phi Constant**: All modules use φ = 1.618033988749895
7. **Complement Pairs**: `harmonic_dark_fill` complement pairs (KO↔DR, AV↔UM, RU↔CA) align with `gallery_chromatics` dual-eye seeding (left=KO/DR, right=RU/CA, bridge=AV/UM)
8. **Band Boundaries**: `harmonic_dark_fill` bands (0.01/20/20k/1M Hz) are consistent with `spectrogram_bridge` audible tongue bands (20-20k Hz) — the audible band is a subset
9. **Audible Range**: `stellar_octave_mapping.AUDIBLE_MIN/MAX` (20/20000) matches `harmonic_dark_fill.AUDIBLE_MIN/MAX` and `spectrogram_bridge` tongue band coverage
10. **Base Frequencies**: `harmonic_dark_fill.TONGUE_AUDIBLE_FREQ` lives within `spectrogram_bridge` tongue bands — each tongue's base Hz falls in or near its attributed band
11. **Dead Tone ↔ Musical Intervals**: `gallery_sonifier.DEAD_TONE_ACOUSTIC` ratios (3:2, 8:5, 16:9) map to `harmonic_dark_fill.INTERVALS` entries (perfect_fifth, minor_sixth, minor_seventh)
12. **Octave Identity**: `stellar_octave_mapping.transpose()` preserves interval ratios — octave doubling does not change the musical relationship, only the register

---

## Determinism vs Expressivity

Frozen constants and bounds MUST NOT change without version bump. Expressive parameters MAY vary within documented ranges.

### Deterministic (frozen, breaking change if altered)
- Tongue set: {ko, av, ru, ca, um, dr}
- Dead tone set: {perfect_fifth, minor_sixth, minor_seventh}
- Material set: {matte, fluorescent, neon, metallic}
- All parameter bounds (rate, energy, pan, chroma, lightness, etc.)
- Inverse mapping: `freq_to_hue()` ↔ `hue_to_frequency()`
- Tongue-frequency band edges: 20/150/400/1000/2500/6000/20000 Hz
- Stereo layout: KO/DR left, RU/CA right, AV/UM center
- Dead tone pretone Hz: 330/352/392
- Dead tone envelopes: pulse/dissonance/echo
- Voice layer counts per mode: 1/2/4
- Prosody curve shape families per tongue (even/flowing/percussive/rising/falling/grounded)
- Phi constant: 1.618033988749895
- **Stellar frequencies**: sun_p_mode=0.003, sun_g_mode=0.0001, red_giant=0.00005, white_dwarf=0.001, neutron_star=100.0 Hz
- **Octave formula**: `f_human = f_stellar × 2^round(log₂(target/stellar))`
- **Band boundaries**: infra=[0.01, 20], audible=[20, 20000], ultra=[20000, 1000000] Hz
- **Complement pairs**: KO↔DR, AV↔UM, RU↔CA
- **Base tongue frequencies**: KO=440, AV=523.25, RU=293.66, CA=659.25, UM=196, DR=392 Hz
- **Musical interval vocabulary**: 14 intervals (unison through octave, including phi)
- **Tuning system set**: 7 systems (Just 5-limit, Pythagorean, 12-TET, Phi-Fibonacci, 7-limit Just, Bohlen-Pierce, Adaptive)
- **Trim chord signatures**: perfect_fifth=safe, major_third=convergent, tritone=violation

### Expressive (may vary within bounds)
- Voice name choice (alloy, verse, ember, etc.)
- Micro-timing: exact pause_ms values, cadence rhythm variation
- Choir richness: gain, pitch_shift per voice layer (within [0,1] / [-1,1])
- Earcon ornamentation: attack/decay envelope details
- Chant ratio per render preset
- Sub-rotation weights in gallery chromatics iris construction
- Harmonic number → polar radius saturation curve shape
- **Tuning system selection**: which of the 7 systems is active at runtime
- **Damping coefficient** (γ): stakeholder-cost-governed, varies per governance state
- **Infrasonic modulation shape**: sinusoidal position modulation depth (currently 0.5)
- **Ultrasonic hash algorithm**: currently SHA-256, could change if determinism preserved
- **Stellar target frequency**: default geometric mean, caller may specify any audible target
- **Camouflage harmonic count**: number of harmonics in stellar camouflage series

---

## Coherence Metric (proposed)

Weighted geometric mean (avoids multiplicative collapse):

```
C = ∏ᵢ (Cᵢ ^ wᵢ)    where  Σwᵢ = 1
```

### Core coherence (audible pipeline)

| Component | Symbol | Source | Weight |
|-----------|--------|--------|--------|
| Text ↔ Prosody | C₁ | Tongue weight cosine sim vs ProsodyParams | w₁ = 0.20 |
| Prosody ↔ Audio | C₂ | Voice param coverage vs choral plan | w₂ = 0.20 |
| Audio ↔ Spectrogram | C₃ | `audio_text_alignment()` | w₃ = 0.20 |
| Spectrogram ↔ Chromatics | C₄ | Hue/chroma correlation vs gallery field | w₄ = 0.20 |

### Extended coherence (full spectrum)

| Component | Symbol | Source | Weight |
|-----------|--------|--------|--------|
| Dark Fill Band Balance | C₅ | IR/audible/UV energy ratio within expected bounds per tongue | w₅ = 0.10 |
| Stellar ↔ Audible Alignment | C₆ | Transposed stellar freq within tongue band of dominant tongue | w₆ = 0.10 |

**Range**: (0, 1]. All Cᵢ are clipped to [0.01, 1.0] before computation to prevent log(0).

**Failure semantics**:
- C ≥ 0.7: Aligned. No action needed.
- 0.5 ≤ C < 0.7: Drift warning. Log and monitor.
- C < 0.5: Coherence break. Investigation required. Block circulation passes until resolved.

**Note**: C₅ and C₆ are only evaluated when the dark fill and stellar modules are active in the pipeline. If inactive, their weights redistribute equally across C₁-C₄ (each becomes 0.25).
