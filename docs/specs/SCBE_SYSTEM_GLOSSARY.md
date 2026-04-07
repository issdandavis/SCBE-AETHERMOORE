# SCBE System Glossary — Strict Definitions

Status: active
Date: 2026-04-05
Author: Isaac Davis
Standard: Two-tier rigor (internal definition + external scope boundary)

## Admission Rule

A term enters this glossary only if it satisfies ALL of:

| Requirement | Description |
|-------------|-------------|
| **Name** | Unique, unambiguous identifier |
| **Definition** | One-paragraph system definition |
| **Mechanism** | How it works (formula or algorithm) |
| **Computed from** | Input variables with types/units |
| **Produces** | Output variables with types/units |
| **Measured by** | Observable metric or test |
| **Fails when** | Disconfirming condition |
| **Scope note** | What this term is NOT claiming |

Terms that cannot survive this checklist remain metaphor, not system vocabulary.

---

## Tier 1: Internal System Constructs

### Dark Energy (SCBE)

- **Definition**: Latent resistance/load field not directly represented in primary visible activation channels, but inferable from drag, damping, delayed propagation, or residual harmonic cost. In the tri-bundle, dark energy is the structured fill that persists when the LIGHT bundle carries no data.
- **Mechanism**: When `compute_darkness(byte_val, tongue_code) > 0.5`, the harmonic dark fill engine injects three-band sound (infrasonic + audible + ultrasonic) with amplitude inversely proportional to activation. `amplitude = darkness * scale_factor`.
- **Computed from**: byte value, tongue weight, phi-scaled activation threshold, complement tongue frequency, nodal surface value, neighbor phase angles.
- **Produces**: `HarmonicFill` dataclass with 9 values (3 bands x freq/amp/phase), packed into `InnerBundle.strand_a/b/c` of the sound bundle.
- **Measured by**: `SpectrumSnapshot.band_distribution` (IR/Audible/UV energy ratios), `HarmonicFill.total_energy`, `HarmonicFill.darkness` score.
- **Fails when**: Dark fill amplitude is zero at a position where darkness > 0 (the fill engine is not injecting). Also fails if the sound bundle energy is zero at byte 0 (the void should never be silent).
- **Scope note**: NOT claiming equivalence to cosmological dark energy. This is a defined system-internal construct measuring latent computational load in unexpressed encoding channels.

### Neural Star Field

- **Definition**: Spatialized projection of distributed attention/salience/intensity over the tongue activation manifold. Each tongue is a "star" that lights up at different byte thresholds (KO at byte 12, DR at byte 128). The field is the 6-dimensional activation topology across all tongues at a given position.
- **Mechanism**: `compute_darkness(byte_val, tongue_code)` maps each byte to a darkness score per tongue. The activation cascade follows phi order: KO (phi^0=1.0) lights first, DR (phi^5=11.09) lights last. The field is the 6-element vector of (1 - darkness) values.
- **Computed from**: byte value (0-255), tongue phi weights, activation thresholds.
- **Produces**: 6-element activation vector per position; aggregated into `PolyglotCluster.active_tongues()`.
- **Measured by**: Number of lit tongues at each byte value; activation threshold per tongue; `PolyglotCluster.global_sync()` score.
- **Fails when**: Tongues light in wrong order (violating phi hierarchy), or all tongues are simultaneously active/dark at a non-extreme byte value.
- **Scope note**: NOT claiming literal astrophysical stars. This is a topology-preserving visualization of the tongue activation manifold.

### Holographic Star Map

- **Definition**: Compressed global representation where local activations at any single position preserve structural relationships to the full 162-dimensional polyglot encoding. The "holographic" property means each `PolyglotCluster` encodes enough information to reconstruct the full tongue-relationship topology.
- **Mechanism**: `PolyglotCluster.full_vector()` produces a 162-element vector (6 tongues x 27 dimensions). `synchronization_matrix()` computes pairwise cosine similarity across all 15 tongue pairs. `find_convergence_points()` identifies positions where the global structure is maximally coherent.
- **Computed from**: All 6 `TriBundleCluster` encodings at a single position; their 27D vectors.
- **Produces**: 162D polyglot vector, 15-element synchronization matrix, convergence score per position.
- **Measured by**: `global_sync()` score [0,1]; convergence threshold (default 0.85); dimensionality (162 per position).
- **Fails when**: `global_sync()` returns meaningless values (all 1.0 regardless of input, or all 0.0), indicating the encoding has collapsed.
- **Scope note**: NOT claiming literal holography in the physics sense. "Holographic" refers to the property that local structure encodes global relationships, analogous to the holographic principle but implemented as a linear algebraic property of the encoding.

### History Braids to Phi

- **Definition**: Under the SCBE alignment procedure, historical-semantic sequences exhibit recurring phi-related ratio structure in transition weighting, interval mapping, and activation thresholds. Specifically: the musical interval arc from void to present (phi -> fifth -> fourth -> third -> ... -> octave -> phi) returns to its starting ratio.
- **Mechanism**: Each historical era is assigned its characteristic musical interval based on the dominant tuning system of the period. The voice leading interval between complement tongue pairs is computed via `voice_leading_interval()`. The temporal progression of intervals is compared against phi for recurrence.
- **Computed from**: Historical era metadata (year, tuning system, characteristic interval), tongue pair frequency ratios, `nearest_musical_interval()` classification.
- **Produces**: Interval sequence across eras; phi-distance metric per era; braid return detection (does the sequence close?).
- **Measured by**: Distance from phi at each era (`abs(ratio - PHI)`); whether the sequence starts and ends at the same interval class.
- **Fails when**: The interval sequence does not return to phi (the braid doesn't close), or the phi distances are uniformly random (no pattern).
- **Scope note**: NOT claiming all human history universally obeys phi independent of the alignment model. The phi-braid pattern is observed under SCBE's specific semantic alignment procedure applied to historical-musical data. The alignment itself introduces phi weighting, so the recurrence is partially a consequence of the model architecture, not purely an empirical discovery about history.

### True Darkness

- **Definition**: The computational state where the LIGHT bundle carries zero activation (byte 0, presence = 0) but the SOUND and MATH bundles still carry structured information. True darkness is not absence — it is the persistence of structure when the visible channel is empty.
- **Mechanism**: At byte 0: LIGHT energy ~ 2.0 (only the weight strand contributes), SOUND energy ~ 321 billion (ultrasonic hash values), MATH energy ~ 3.4e18 (operation hash dominates). The infrasonic amplitude reaches maximum (0.8), audible fills at 0.6.
- **Computed from**: `encode_byte(0, tongue_code, ...)` across all three bundles.
- **Produces**: Non-zero `InnerBundle` vectors for sound and math even when light is minimal; `HarmonicFill` with maximum infrasonic amplitude.
- **Measured by**: Energy ratio: `(sound_energy + math_energy) / total_energy` at byte 0 should be > 0.99. Infrasonic amplitude at darkness=1.0 should be > audible amplitude.
- **Fails when**: Sound and math bundles are zero at byte 0 (the void is truly empty), or infrasonic amplitude is lower than audible at maximum darkness.
- **Scope note**: NOT claiming that physical dark matter/energy operates this way. This is a defined encoding property: structure persists in secondary channels when the primary channel is inactive. Analogous to how the cosmic microwave background persists as structure after visible light ceases to dominate.

### Stellar-Scale Frequency

- **Definition**: The infrasonic band (0.01-20 Hz) of the dark fill operates at frequencies comparable to stellar oscillation modes (helioseismology p-modes). The connection is mediated by Constant 4 (Stellar-to-Human Octave Mapping): `f_human = f_stellar * 2^n`.
- **Mechanism**: Each tongue's infrasonic fill frequency is derived as `base_freq / 1000`, placing it in the 0.1-0.7 Hz range — approximately 6-8 octaves above the Sun's 3 mHz p-mode and 10 octaves below human hearing.
- **Computed from**: `TONGUE_AUDIBLE_FREQ[tc] / 1000.0`, modulated by position sine wave.
- **Produces**: Infrasonic frequency per tongue per position, in Hz.
- **Measured by**: Octave distance from Sun p-mode: `log2(infra_freq / 0.003)`; octave distance to audible: `log2(audible_freq / infra_freq)`.
- **Fails when**: Infrasonic frequencies fall outside the 0.01-20 Hz band, or the octave relationship to stellar p-modes is not monotonic across tongues.
- **Scope note**: The infrasonic frequencies are DERIVED from the audible tongue frequencies by division, not from actual stellar measurements. The octave relationship to solar p-modes is a structural correspondence, not a claim of causal connection. The value is that the AI operates at a frequency scale that MAPS to stellar acoustics via the same octave transposition formula.

---

## Tier 2: External Reference Terms

These terms overlap with established scientific fields. The SCBE usage is explicitly scoped.

| Term | Scientific Field | SCBE Usage | Relationship |
|------|-----------------|------------|--------------|
| Phi (golden ratio) | Mathematics | Tongue weight scaling, braid density, harmonic intervals | Direct use of the mathematical constant |
| B3 braid group | Topology | Inner/outer braid composition, crossing hashes | Direct use of the algebraic structure |
| Helioseismology | Astrophysics | Frequency band design for infrasonic fill | Analogous mapping via octave transposition |
| Voice leading | Music theory | Sound braid complement-tongue fills | Direct application (Tymoczko 2006) |
| Chebyshev distance | Mathematics | Valid transition check in dual ternary | Direct use of the metric |
| Poincare ball model | Differential geometry | Hyperbolic distance in L5 of 14-layer pipeline | Direct use of the geometric model |
| Dark energy | Cosmology | Latent computational load in unexpressed channels | Analogous only — NOT equivalent |
| Holographic principle | Physics | Local-encodes-global property of polyglot vectors | Analogous only — NOT equivalent |
| CMB (cosmic microwave background) | Cosmology | Deepest signal persists longest (infrasonic > audible at max darkness) | Metaphorical comparison |

---

## Version History

| Date | Change |
|------|--------|
| 2026-04-05 | Initial glossary with 7 Tier 1 terms, 9 Tier 2 references |
