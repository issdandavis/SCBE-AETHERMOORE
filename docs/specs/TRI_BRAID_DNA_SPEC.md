# Tri-Braid DNA Encoding Specification

Status: active design
Date: 2026-04-05
Author: Isaac Davis
Scope: Three-braid signal architecture for polyglot semantic lattice encoding

## Core Architecture

Three primary signal braids, each containing 3 sub-strands, forming a 3x3x3 dense encoding bundle.

### The Three Braids

| Braid | Signal Type | Role | Sub-strands |
|-------|-------------|------|-------------|
| **LIGHT** | Binary (bits) | What IS — presence/absence | L0: raw byte, L1: tongue token, L2: orientation packet |
| **SOUND** | Math/Audio (harmonics) | What RESONATES — fills dark nodes | S0: nodal frequency, S1: octave mapping, S2: phase angle |
| **INTENT** | Ternary (trits) | Which WAY — polarity/direction | I0: primary trit, I1: mirror trit, I2: governance trit |

### Why Three Braids

DNA uses 2 strands and 4 bases → 64 codons.

Tri-braid uses 3 braids and 3 sub-strands each → 27 base states per position, scaling through phi to (3^phi)^3 effective states per cluster.

The third braid (SOUND) is the innovation. Binary tells you what exists. Trits tell you which direction. Sound fills the SILENCE — the nodes NOT activated by current data. Musical scale patterns project discrete mathematical relationships into the dark zones of the nodal bundle, providing ambient harmonic structure where there would otherwise be null.

### The Dark Node Problem

In any given moment, only a subset of the 6 Sacred Tongues are active for a given input. The inactive tongues produce null activations — dark nodes. Without the sound braid, these dark nodes are pure absence. With the sound braid, the dark nodes carry harmonic reinforcement patterns that:

1. Maintain coherent phase across the full bundle (no dead zones)
2. Project mathematical relationships as musical intervals
3. Provide the "background music" that keeps the lattice warm
4. Enable the dark nodes to carry structural information even when not data-active

Source: `src/symphonic_cipher/scbe_aethermoore/vacuum_acoustics.py`

Nodal surface equation:
```
N(x; n, m) = cos(n*pi*x1/L)*cos(m*pi*x2/L) - cos(m*pi*x1/L)*cos(n*pi*x2/L) = 0
```

Where N=0 = dark node. The sound braid injects harmonic energy at these cancellation points.

## Braid Topology

### Level 1: Inner Braid (3 sub-strands per braid)

Each braid is a 3-strand plait:

```
LIGHT:  [L0]---[L1]---[L2]
         \  /    \  /
          \/      \/
          /\      /\
         /  \    /  \
SOUND:  [S0]---[S1]---[S2]
         \  /    \  /
          \/      \/
          /\      /\
         /  \    /  \
INTENT: [I0]---[I1]---[I2]
```

### Level 2: Outer Braid (3 braids into 1 bundle)

The three inner braids plait together:

```
LIGHT ──╲   ╱── LIGHT ──╲   ╱──
         ╲ ╱              ╲ ╱
          ╳                ╳
         ╱ ╲              ╱ ╲
SOUND ──╱   ╲── SOUND ──╱   ╲──
         ╲   ╱              ╲   ╱
          ╲ ╱                ╲ ╱
           ╳                  ╳
          ╱ ╲                ╱ ╲
INTENT ─╱   ╲── INTENT ──╱   ╲──
```

### Level 3: Phi-Scaled Density

The braid density is not uniform. It scales as (3^phi)^3:

```
3^phi = 3^1.618 = 5.298...
(3^phi)^3 = 5.298^3 = 148.8...
```

This means ~149 effective distinguishable states per cluster position, compared to 27 for flat 3^3. The phi scaling creates non-uniform density where some compositions are "thicker" (more distinguishable) than others — matching the phi-weighted tongue importance.

### Codon Structure

A single position in the tri-braid encodes:

```python
@dataclass
class TriBraidCodon:
    # LIGHT braid
    raw_byte: int           # L0: 0-255
    tongue_token: str       # L1: e.g. "nav'un" (KO for byte 108)
    orientation: float[6]   # L2: 6-tongue activation vector

    # SOUND braid
    nodal_freq: float       # S0: frequency from vacuum acoustics nodal surface
    octave_map: float       # S1: stellar-to-human octave transposition
    phase_angle: float      # S2: wave phase at this position

    # INTENT braid
    primary_trit: int       # I0: {-1, 0, +1} from dual ternary
    mirror_trit: int        # I1: {-1, 0, +1} mirror channel
    governance: int         # I2: {-1, 0, +1} = DENY / QUARANTINE / ALLOW
```

### Digichain Cluster Identity

A digichain cluster is a sequence of codons whose identity is determined by the COMPOSITION of its inner braided matrices, not just the sequence.

Two clusters with the same codons in different braid arrangements are DIFFERENT digichains — because the crossing pattern of the braid matters. This is topological: you cannot deform one braid into another without cutting.

The cluster identity hash:

```
cluster_id = hash(
    light_braid_crossings,
    sound_braid_crossings,
    intent_braid_crossings,
    outer_braid_crossings,
    phi_density_at_position
)
```

## Musical Scale Projection

### Discrete Calculations as Musical Patterns

The SOUND braid carries discrete mathematical calculations encoded as musical intervals:

| Musical Interval | Frequency Ratio | Mathematical Operation |
|------------------|-----------------|----------------------|
| Unison | 1:1 | Identity |
| Octave | 2:1 | Binary doubling |
| Perfect Fifth | 3:2 | Phi approximation (1.5 ≈ R_harm default) |
| Perfect Fourth | 4:3 | Inverse fifth |
| Major Third | 5:4 | Geometric mean step |
| Minor Third | 6:5 | Complement |

### Harmonic Reinforcement Pattern

For inactive tongue positions, the sound braid projects:

```
S(t, tongue_k) = A_k * sin(2*pi*f_k*t + phase_k)
```

where:
- `f_k = f_base * phi^k` (frequency scales with tongue phi weight)
- `A_k = 1 - activation_k` (amplitude is INVERSE of data activation — louder when darker)
- `phase_k` = derived from the active tongues' phase relationships

This means the SOUND is loudest where the LIGHT is darkest. The math fills the silence.

## Connection to Existing Architecture

### Binary-First Training Stack (L0-L3)

The tri-braid extends the 4-layer binary-first stack:

| Stack Layer | Tri-Braid Mapping |
|-------------|-------------------|
| L0 binary | LIGHT.L0 (raw byte) |
| L1 symbolic byte | LIGHT.L1 (tongue token) |
| L2 orientation | LIGHT.L2 + INTENT (full orientation = activation + direction) |
| L3 lexical | Emergent from cluster sequences |

### Dual Ternary (9-state phase space)

Source: `src/symphonic_cipher/scbe_aethermoore/ai_brain/dual_ternary.py`

The INTENT braid's I0 × I1 gives the 9-state dual ternary space:
```
(-1,-1) (-1,0) (-1,+1)
( 0,-1) ( 0,0) ( 0,+1)
(+1,-1) (+1,0) (+1,+1)
```

Adding I2 (governance trit) extends to 27 states = 3^3.

### Hamiltonian Braid Dynamics

Source: `src/symphonic_cipher/scbe_aethermoore/ai_brain/hamiltonian_braid.py`

The existing braid dynamics (rail points, phase deviation, valid transitions) govern the OUTER braid — the crossing pattern of LIGHT/SOUND/INTENT. The Chebyshev distance constraint (max 1 step per timestep) prevents impossible jumps in the braid topology.

### Vacuum Acoustics / Audio Axis

Source: `src/symphonic_cipher/scbe_aethermoore/vacuum_acoustics.py`
Source: `src/symphonic_cipher/audio/stellar_octave_mapping.py`

These provide the SOUND braid's mathematical content:
- Nodal surfaces → where to inject harmonic energy
- Octave mapping → frequency scaling from abstract to audible
- Bottle beam intensity → reinforcement pattern shape

### Polyhedral Friction

Source: `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/polyhedral_flow.py`

The friction between polyhedra IS the sound braid's training signal. Where polyhedral shells meet and vibrate, the torsional distortion creates the harmonic pattern that fills the dark nodes.

## Training Loss Extension

Extends the binary-first training loss:

```
L_total = L_byte          # LIGHT.L0
        + λ_t * L_tongue  # LIGHT.L1
        + λ_n * L_null    # LIGHT.L2 (null pattern)
        + λ_s * L_sound   # SOUND braid (predict harmonic fill)
        + λ_i * L_intent  # INTENT braid (predict trit state)
        + λ_w * L_word    # Lexical layer (emergent from clusters)
        + λ_q * L_policy  # Governance posture
        + λ_g * L_geometry # Polyhedral friction
```

New term:
```
L_sound = || predicted_harmonic_fill - actual_dark_node_pattern ||^2
```

This teaches the model to predict what harmonic pattern SHOULD fill the inactive nodes — learning the ambient mathematical structure of the encoding space.

## Linguistic E=MC² Connection

The tri-braid IS the measurement apparatus for the Linguistic E=MC² hypothesis:

- **E** (emotional derivative) = the rate of change of cluster identity across a text sequence
- **M** (cross-linguistic metrics) = the LIGHT braid synchronization across parallel translations
- **C²** (constants squared) = the SOUND braid's invariant harmonic patterns (same everywhere)
- **T** (observation time) = the length of the parallel corpus window

Where all languages' LIGHT braids synchronize AND the SOUND braids match = **universal emotional invariant**.

Where the INTENT braids diverge despite LIGHT synchronization = **cultural-specific directional framing of the same concept**.
