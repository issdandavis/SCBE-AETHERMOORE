# Symphonic Cipher

**Intent-Modulated Conlang + Harmonic Verification System**

A mathematically rigorous authentication protocol that combines:
- Private conlang (constructed language) dictionary mapping
- Modality-driven harmonic synthesis
- Key-driven Feistel permutation
- Studio engineering DSP pipeline
- AI-based feature extraction and verification
- RWP v3 cryptographic envelope

## Overview

The Symphonic Cipher authenticates commands by encoding them as audio waveforms with specific harmonic signatures. Different "intent modalities" (STRICT, ADAPTIVE, PROBE) produce different overtone patterns that can be verified through FFT analysis.

### Architecture

```
[Conlang Phrase] → [Token IDs] → [Feistel Permutation] → [Harmonic Synthesis]
        ↓
[DSP Chain: Gain → EQ → Compression → Reverb → Panning]
        ↓
[RWP v3 Envelope: HMAC-SHA256 + Nonce + Timestamp]
        ↓
[Verification: MAC Check + Harmonic Analysis + AI Classification]
```

## Mathematical Foundation

### 1. Dictionary Mapping (Section 2)

Bijection between lexical tokens and integer IDs:

```
∀τ ∈ D: id(τ) ∈ {0, ..., |D|-1}
```

### 2. Modality Encoding (Section 3)

Each modality M determines which overtones are emitted via mask M(M):

| Modality | Mask M(M) | Description |
|----------|-----------|-------------|
| STRICT | {1, 3, 5} | Odd harmonics (binary intent) |
| ADAPTIVE | {1, 2, 3, 4, 5} | Full series (non-binary intent) |
| PROBE | {1} | Fundamental only |

### 3. Per-Message Secret (Section 4)

```
K_msg = HMAC_{k_master}(ASCII("msg_key" || n))
```

### 4. Feistel Permutation (Section 5)

4-round balanced Feistel network:

```
L^(r+1) = R^(r)
R^(r+1) = L^(r) ⊕ F(R^(r), k^(r))
```

### 5. Harmonic Synthesis (Section 6)

```
x(t) = Σᵢ Σₕ∈M(M) (1/h) sin(2π(f₀ + vᵢ'·Δf)·h·t)
```

Where:
- f₀ = 440 Hz (base frequency)
- Δf = 30 Hz (frequency step per token ID)

### 6. DSP Pipeline (Sections 3.2-3.10)

- **Gain Stage**: v₁ = g · v₀, where g = 10^(G_dB/20)
- **Mic Pattern Filter**: v₂[i] = v₁[i] · (a + (1-a)·cos(θᵢ - θ_axis))
- **Parametric EQ**: Biquad IIR filter with peak/shelf modes
- **Compressor**: Piecewise-linear gain reduction with attack/release
- **Convolution Reverb**: z[n] = (x * h)[n]
- **Stereo Panning**: Constant-power law L/R distribution

### 7. RWP v3 Envelope (Section 7)

```
C = "v3." || σ || AAD_canon || t || n || b64url(x)
sig = HMAC_{k_master}(C)
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Example

```python
from symphonic_cipher import SymphonicCipher, Modality

# Create cipher with auto-generated key
cipher = SymphonicCipher()

# Encode a conlang phrase
envelope = cipher.encode(
    phrase="korah aelin dahru",
    modality=Modality.ADAPTIVE,
    tongue="KO"
)

# Verify envelope
success, message = cipher.verify(envelope)
print(f"Verified: {success}")
```

### With DSP Processing

```python
from symphonic_cipher import SymphonicCipher, Modality
from symphonic_cipher.dsp import DSPChain

# Create cipher and DSP chain
cipher = SymphonicCipher()
dsp = DSPChain()

# Configure studio engineering stages
dsp.configure_compressor(threshold_db=-20, ratio=4.0)
dsp.configure_reverb(wet_mix=0.2)
dsp.configure_panning(pan_position=0.3)

# Encode and process
envelope, components = cipher.encode(
    "korah aelin",
    modality=Modality.STRICT,
    return_components=True
)

# Get raw audio and process through DSP
import numpy as np
import base64
audio = np.frombuffer(
    base64.urlsafe_b64decode(envelope['payload'] + '=='),
    dtype=np.float32
)
stereo = dsp.process(audio)
```

### AI Verification

```python
from symphonic_cipher.ai_verifier import (
    FeatureExtractor,
    HarmonicVerifier,
    IntentClassifier
)

# Extract features
extractor = FeatureExtractor()
features = extractor.extract(audio_signal)

# Harmonic verification
verifier = HarmonicVerifier()
report = verifier.verify(audio_signal, "ADAPTIVE")
print(f"Result: {report.result.value}")

# AI classification
classifier = IntentClassifier()
is_authentic, confidence = classifier.classify(features)
```

## Running the Demo

```bash
python demo.py
```

This demonstrates all components:
1. Dictionary mapping
2. Modality encoding
3. Feistel permutation
4. Harmonic synthesis
5. DSP chain processing
6. RWP v3 envelope
7. Feature extraction
8. Harmonic verification
9. AI classification
10. End-to-end flow

## Running Tests

```bash
pytest symphonic_cipher/tests/ -v
```

## Security Properties

1. **HMAC-SHA256 Integrity**: Envelope tampering is detected
2. **Nonce-based Replay Protection**: Each message uses unique nonce
3. **Timestamp Expiry**: Messages expire after 60 seconds
4. **Key-driven Permutation**: Token order is secret without key
5. **Harmonic Verification**: Modality must match declared intent
6. **AI Liveness Detection**: Synthetic/replay audio is flagged

## Constants

| Symbol | Value | Description |
|--------|-------|-------------|
| f₀ | 440 Hz | Base frequency (A4) |
| Δf | 30 Hz | Frequency step per token ID |
| H_max | 5 | Maximum overtone index |
| SR | 44,100 Hz | Sample rate |
| T_sec | 0.5 s | Waveform duration |
| R | 4 | Feistel rounds |
| τ_max | 60,000 ms | Replay window |
| ε_f | 2 Hz | Frequency tolerance |
| ε_a | 0.15 | Amplitude tolerance |

## Conlang Vocabulary

Default vocabulary:

| Token | ID | Frequency |
|-------|-----|-----------|
| korah | 0 | 440 Hz |
| aelin | 1 | 470 Hz |
| dahru | 2 | 500 Hz |
| melik | 3 | 530 Hz |
| sorin | 4 | 560 Hz |
| tivar | 5 | 590 Hz |
| ulmar | 6 | 620 Hz |
| vexin | 7 | 650 Hz |

Extended vocabulary supports negative IDs (e.g., "shadow" = -1 → 410 Hz).

## License

MIT License

## References

- HMAC-SHA256: RFC 2104
- Feistel Networks: Luby-Rackoff, 1988
- Biquad Filters: Audio EQ Cookbook
- MFCC: Davis & Mermelstein, 1980
