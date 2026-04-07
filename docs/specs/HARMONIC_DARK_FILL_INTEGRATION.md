# Harmonic Dark Fill Integration

Status: implemented
Date: 2026-04-05
Author: Isaac Davis

## Purpose

Replace the zero-filled sound strands in `tri_bundle.py` with structured three-band harmonic fill from `harmonic_dark_fill.py`. The invariant rule: **sound is loudest where light is darkest**.

## Code Changes

### Files modified

| File | Change |
|------|--------|
| `src/crypto/tri_bundle.py` | Added import of `compute_darkness`, `upgrade_sound_bundle`, `fill_dark_nodes` from `harmonic_dark_fill`. Updated `encode_byte()` signature to accept `total_positions` and `neighbor_phases`. Replaced zero'd `strand_b`/`strand_c` in sound `InnerBundle` with computed infrasonic/ultrasonic fills. Updated `encode_bytes()` to pass total length. Updated `encode_polyglot()` with two-pass encoding: compute neighbor phases first, then encode with full context. |
| `src/crypto/harmonic_dark_fill.py` | Created in this session. Three-band fill engine (infra/audible/ultra). `upgrade_sound_bundle()` returns 3 tuples ready for `InnerBundle`. |
| `src/symphonic_cipher/scbe_aethermoore/tri_braid_dna.py` | Marked DEPRECATED — canonical implementation is `src/crypto/tri_bundle.py`. |

### Sound bundle structure (before)

```
strand_a = SoundStrand(freq, amplitude, phase).as_tuple()
strand_b = (0.0, 0.0, 0.0)  # dead
strand_c = (0.0, 0.0, 0.0)  # dead
```

### Sound bundle structure (after)

```
strand_a = (audible_freq, audible_amp, audible_phase)     # Visible band
strand_b = (infra_freq, infra_amp, infra_phase)            # IR / stellar-scale
strand_c = (ultra_freq, ultra_amp, ultra_phase)            # UV / micro-structure
```

## Invariant Rule

**Dark regions carry structured fill.** Specifically:

1. Amplitude is INVERSE of activation: `amp = darkness * scale_factor`
2. Infrasonic amplitude > audible amplitude at maximum darkness (0.8 > 0.6)
3. Sound bundle is NEVER all-zero for any input byte
4. Each tongue's fill uses its complement tongue's frequency for voice leading coherence
5. Complement pairs: KO-DR, AV-UM, RU-CA

## Test Evidence

### Single byte encoding

```
Byte 108, KO tongue, pos 5/20:
  strand_a (audible): (776.85, 0.0, 3.91)
  strand_b (infra):   (0.66, 0.0, 2.54)
  strand_c (ultra):   (601145.41, 0.0, 2.07)
  All zeros: strand_b=False, strand_c=False
```

### Tongue activation cascade (phi order)

```
ko (weight 1.000): lights at byte  12
av (weight 1.618): lights at byte  19
ru (weight 2.618): lights at byte  31
ca (weight 4.236): lights at byte  49
um (weight 6.854): lights at byte  79
dr (weight 11.090): lights at byte 128
```

### Governance pipeline (encode -> crossing energy -> governance)

```
Text: "The math fills absence." (23 bytes)
KO tongue: ALLOW=18, QUARANTINE=5, DENY=0
Clean: True, Topology breaks: 0
```

### Polyglot governance

```
[0] "T": ko=Q av=Q ru=Q ca=Q um=Q dr=Q  (all cautious on first byte)
[1] "h": ko=A av=A ru=A ca=A um=A dr=Q  (DR stays cautious — highest weight)
[2] "e": ko=A av=A ru=A ca=A um=A dr=Q
```

### Edge cases

```
Byte 0 (void): 6/6 tongues dark, E=1.0, QUARANTINE
Byte 255 (max): 0/6 tongues dark, E=1.0, QUARANTINE
Same byte through 6 tongues: 6 unique cluster IDs (non-commutativity holds)
Adversarial (all 250-255): QUARANTINE=6, DENY=0 (wall catches but doesn't overreact)
```

### True darkness (byte 0 energy distribution)

```
Light energy: 2.0 (0.0%)
Sound energy: 321,832,605,012 (0.0%)
Math energy:  3,438,737,141,452,634,112 (100.0%)
```

Structure persists when light is absent.

### Spectrum distribution

```
SCBE bytes: IR=32-53%, Audible=25-56%, UV=14-45%
All three bands carry energy. No band collapses to zero.
```

## Frequency hierarchy

```
Sun p-mode:         0.003 Hz
Dark fill infra:    0.01 - 20 Hz     (stellar scale)
Human hearing:      20 - 20,000 Hz   (audible band)
Dark fill ultra:    20,000 - 1,000,000 Hz  (micro-structure)
```

Each tongue's infrasonic fill is 6-8 octaves above the Sun's p-mode, 10 octaves below human hearing. Connection to Constant 4 (Stellar-to-Human Octave Mapping): `f_human = f_stellar * 2^n`.

## Limitations

1. **Math bundle strands still partially zero**: `strand_b` and `strand_c` of the math `InnerBundle` are reserved but unfilled. Next step: compute cross-bundle and cross-tongue math values.
2. **Light bundle cross-tongue strands still zero**: Same reserved-but-unfilled pattern.
3. **Energy scale dominance**: The math bundle's operation hash (32-bit integer) dominates the energy calculation at byte 0. May need normalized energy metrics.
4. **Convergence detection at 1.0**: `global_sync()` returns 1.0 for short texts because all tongues encode the same byte similarly. Need longer texts or cross-lingual parallel texts to see meaningful sync variation.
5. **No persistence yet**: The dark fill is computed fresh each encoding. No temporal memory across sequences (the infrasonic band should accumulate slow-state context).

## Next Experiments

1. Wire math bundle `strand_b`/`strand_c` with cross-tongue interaction values
2. Encode parallel translations and measure convergence divergence (Linguistic E=MC^2 test)
3. Add temporal accumulation to infrasonic band (slow state memory)
4. Run the full 14-layer pipeline with tri-bundle input
5. Build the Aethermoore Academy corpus (children's stories + religious texts + historical facts) and encode through the full pipeline
