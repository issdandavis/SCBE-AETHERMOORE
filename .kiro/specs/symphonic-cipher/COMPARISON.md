# Symphonic Cipher - Repository Comparison

## 📊 Current State Analysis

### Repository Structure

We have **TWO** repositories:

1. **Main Repo** (`SCBE_Production_Pack` / `issdandavis/scbe-aethermoore-demo`)
   - TypeScript implementation of SCBE 14-layer architecture
   - Has: Hyperbolic geometry, PQC, Quasicrystal lattice
   - Missing: Symphonic Cipher (FFT-based signing)

2. **Demo Repo** (`scbe-aethermoore-demo` - cloned locally)
   - Python implementation of Symphonic Cipher
   - Has: Full DSP pipeline, Feistel network, harmonic synthesis
   - Missing: TypeScript version

## 🔍 What Exists in Python (Demo Repo)

### Python Symphonic Cipher Components

Located in: `scbe-aethermoore-demo/src/symphonic_cipher/`

| File                        | Purpose                           | Status      |
| --------------------------- | --------------------------------- | ----------- |
| `core.py`                   | Dictionary mapping, Feistel, HKDF | ✅ Complete |
| `dsp.py`                    | DSP pipeline (gain, EQ, reverb)   | ✅ Complete |
| `harmonic_scaling_law.py`   | Harmonic scaling H(d,R)           | ✅ Complete |
| `topological_cfi.py`        | Control flow integrity            | ✅ Complete |
| `dual_lattice_consensus.py` | Byzantine consensus               | ✅ Complete |
| `flat_slope_encoder.py`     | Flat slope encoding               | ✅ Complete |
| `ai_verifier.py`            | AI-based verification             | ✅ Complete |

### Python Implementation Details

**From `core.py`:**

```python
# Constants
BASE_FREQ = 440.0       # Hz
FREQ_STEP = 30.0        # Hz
MAX_HARMONIC = 5        # Overtones
SAMPLE_RATE = 44_100    # SR
DURATION_SEC = 0.5      # Signal duration
FEISTEL_ROUNDS = 4      # Rounds
KEY_LEN_BITS = 256      # Key length
```

**Key Classes:**

- `ConlangDictionary` - Token to ID mapping
- `ModalityEncoder` - Overtone masks per intent
- `FeistelPermutation` - 4-round XOR-based scrambling
- `HarmonicSynthesizer` - Waveform generation
- `SymphonicCipher` - Main API

**Note:** Python implementation uses **NumPy** for FFT (`np.fft.fft`)

## 🎯 What We Need in TypeScript (Main Repo)

### TypeScript Symphonic Cipher Components

Based on the technical reference document, we need:

| Component          | File                                     | Status     | Priority    |
| ------------------ | ---------------------------------------- | ---------- | ----------- |
| Complex Numbers    | `src/symphonic/core/Complex.ts`          | ❌ Missing | 🔴 Critical |
| FFT (Cooley-Tukey) | `src/symphonic/core/FFT.ts`              | ❌ Missing | 🔴 Critical |
| Feistel Network    | `src/symphonic/core/Feistel.ts`          | ❌ Missing | 🔴 Critical |
| Z-Base-32 Encoding | `src/symphonic/core/ZBase32.ts`          | ❌ Missing | 🔴 Critical |
| Symphonic Agent    | `src/symphonic/agents/SymphonicAgent.ts` | ❌ Missing | 🟡 High     |
| Hybrid Crypto      | `src/symphonic/crypto/HybridCrypto.ts`   | ❌ Missing | 🟡 High     |
| API Server         | `src/symphonic/server.ts`                | ❌ Missing | 🟢 Medium   |

### Key Differences: Python vs TypeScript

| Aspect              | Python (Demo)        | TypeScript (Needed)          |
| ------------------- | -------------------- | ---------------------------- |
| **FFT Library**     | NumPy (`np.fft.fft`) | Custom implementation        |
| **Feistel Rounds**  | 4 rounds             | 6 rounds (per spec)          |
| **Encoding**        | Base64               | Z-Base-32                    |
| **Dependencies**    | NumPy, SciPy         | Zero (Node.js crypto only)   |
| **Use Case**        | Conlang tokens       | Transaction intents (JSON)   |
| **Signal Duration** | 0.5 seconds          | Variable (based on payload)  |
| **Sample Rate**     | 44,100 Hz            | Not applicable (byte stream) |

## 🔄 Migration Strategy

### Option 1: Port Python to TypeScript (Recommended)

**Pros:**

- Proven algorithm (Python version works)
- Can reference Python code for correctness
- Maintain consistency across implementations

**Cons:**

- NumPy FFT → Custom FFT (more work)
- Different use case (conlang → JSON intents)

### Option 2: Fresh TypeScript Implementation

**Pros:**

- Optimized for TypeScript/Node.js
- Zero dependencies from start
- Follows technical reference document exactly

**Cons:**

- More testing needed
- No reference implementation

**Decision:** Use **Option 1** - Port from Python with modifications

## 📋 Implementation Plan

### Phase 1: Core Primitives (Port from Python)

1. **Complex.ts** - Port complex number math
   - Python uses built-in `complex` type
   - TypeScript needs custom class

2. **FFT.ts** - Port FFT algorithm
   - Python: `np.fft.fft(signal)`
   - TypeScript: Custom Cooley-Tukey implementation
   - Reference: Python's FFT for correctness testing

3. **Feistel.ts** - Port Feistel network
   - Python: `core.py` - `FeistelPermutation` class
   - TypeScript: Adapt to 6 rounds (vs 4 in Python)
   - Use Node.js `crypto.createHmac` (same as Python `hmac`)

4. **ZBase32.ts** - New implementation
   - Python uses Base64
   - TypeScript needs Z-Base-32 for human readability

### Phase 2: Symphonic Agent (Adapt from Python)

5. **SymphonicAgent.ts** - Port harmonic synthesis
   - Python: `core.py` - `HarmonicSynthesizer` class
   - TypeScript: Adapt for JSON intents (not conlang tokens)
   - Remove audio-specific features (sample rate, duration)
   - Focus on byte stream → spectrum

### Phase 3: Integration (New for TypeScript)

6. **HybridCrypto.ts** - New integration layer
   - Combine with existing SCBE crypto
   - Generate harmonic signatures
   - Verify signatures

7. **server.ts** - New API server
   - Express endpoints
   - Sign/verify intents

## 🧪 Testing Strategy

### Cross-Language Validation

1. **Test Vectors** - Generate in Python, verify in TypeScript
   - Same input → same FFT output
   - Same key + intent → same signature

2. **Property Tests** - Verify mathematical properties
   - FFT linearity
   - Feistel reversibility
   - Signature determinism

3. **Performance Comparison**
   - Python (NumPy FFT): ~0.1ms for N=1024
   - TypeScript (Custom FFT): Target <0.5ms for N=1024

## 📊 Feature Parity Matrix

| Feature            | Python (Demo)    | TypeScript (Main)   | Notes              |
| ------------------ | ---------------- | ------------------- | ------------------ |
| **Core Math**      |
| Complex Numbers    | ✅ Built-in      | ❌ Need class       | Port required      |
| FFT                | ✅ NumPy         | ❌ Custom needed    | Port algorithm     |
| Feistel (4 rounds) | ✅ Complete      | ❌ Need 6 rounds    | Adapt              |
| HKDF               | ✅ Complete      | ✅ Exists in crypto | Reuse              |
| **Encoding**       |
| Base64             | ✅ Used          | ❌ Not needed       | -                  |
| Z-Base-32          | ❌ Not used      | ❌ Need new         | Implement          |
| **Synthesis**      |
| Harmonic Synthesis | ✅ Audio-based   | ❌ Need byte-based  | Adapt              |
| Spectrum Analysis  | ✅ NumPy FFT     | ❌ Custom FFT       | Port               |
| **Integration**    |
| Conlang Tokens     | ✅ Complete      | ❌ Not needed       | Different use case |
| JSON Intents       | ❌ Not used      | ❌ Need new         | New feature        |
| API Server         | ❌ Not in Python | ❌ Need new         | New feature        |
| **Testing**        |
| Unit Tests         | ✅ pytest        | ❌ Need vitest      | Port tests         |
| Integration Tests  | ✅ Complete      | ❌ Need new         | New tests          |

## 🎯 Key Decisions

### 1. FFT Implementation

**Decision:** Implement custom Cooley-Tukey FFT in TypeScript

**Rationale:**

- Zero dependencies requirement
- Python uses NumPy (not portable)
- Technical reference provides full algorithm
- Performance acceptable for N ≤ 4096

### 2. Feistel Rounds

**Decision:** Use 6 rounds (not 4 like Python)

**Rationale:**

- Technical reference specifies 6 rounds
- Better security margin
- Minimal performance impact (<100μs)

### 3. Encoding Format

**Decision:** Use Z-Base-32 (not Base64)

**Rationale:**

- Human-readable (verbal confirmation)
- Reduces transcription errors
- Technical reference specifies Z-Base-32

### 4. Use Case Adaptation

**Decision:** JSON intents (not conlang tokens)

**Rationale:**

- Main repo is for blockchain/RWP v3
- Python demo is for conlang research
- Different target audience

## 📈 Success Criteria

### Functional Requirements

✅ **Port Complete** when:

1. All TypeScript components implemented
2. All unit tests pass
3. Integration tests pass
4. Performance targets met

### Compatibility Requirements

✅ **Cross-Language Compatible** when:

1. Same FFT input → same output (Python vs TypeScript)
2. Same Feistel key + data → same output
3. Test vectors validate across languages

### Performance Requirements

✅ **Performance Acceptable** when:

1. FFT (N=1024): <500μs
2. Signing (1KB): <1ms
3. Verification (1KB): <1ms

## 🚀 Next Steps

1. ✅ **Requirements Complete** - This document
2. ⏳ **Design Document** - Detailed TypeScript architecture
3. ⏳ **Implementation** - Port Python → TypeScript
4. ⏳ **Testing** - Cross-language validation
5. ⏳ **Integration** - Add to SCBE-AETHERMOORE package
6. ⏳ **Documentation** - API reference and examples

## 📝 Notes

- Python implementation is **reference** for correctness
- TypeScript implementation is **production** for npm package
- Both implementations serve different use cases
- Cross-language test vectors ensure compatibility

---

**Conclusion:** We need to implement the Symphonic Cipher in TypeScript by porting the proven Python algorithms while adapting for the TypeScript/Node.js ecosystem and JSON intent use case.
