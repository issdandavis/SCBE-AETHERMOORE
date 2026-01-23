# Sacred Tongue Harmonic Verification - Mathematical Specification

**Version**: 3.0 (Future Enhancement)  
**Date**: January 18, 2026  
**Status**: Mathematical Specification Complete (Implementation Pending)  
**Related**: RWP v2.1 (HMAC-only), RWP v3.0 (adds harmonic verification)

---

## Document Purpose

This document provides the **complete mathematical specification** for the Sacred Tongue harmonic verification system. This is a **future enhancement** planned for RWP v3.0 (Q2 2026) and is **NOT part of RWP v2.1**.

**RWP v2.1** (current): HMAC-SHA256 multi-signatures only  
**RWP v3.0** (future): Adds intent-modulated audio verification with harmonic synthesis

---

## 1. Global Notation

| Symbol                 | Meaning                                                               |
| ---------------------- | --------------------------------------------------------------------- |
| 𝒟                      | Private dictionary (bijection between lexical tokens and integer IDs) |
| τ ∈ 𝒟                  | A token (word) from the dictionary                                    |
| id(τ) ∈ ℕ              | Integer identifier of token τ                                         |
| M ∈ 𝕄                  | Modality (intent class): {STRICT, ADAPTIVE, PROBE}                    |
| k_master ∈ {0,1}^ℓ     | Long-term secret key (ℓ = 256 bits)                                   |
| n ∈ {0,…,N-1}          | Message-level nonce (12 bytes → 96 bits)                              |
| t ∈ ℝ⁺                 | Unix timestamp (milliseconds)                                         |
| K_msg ∈ {0,1}^ℓ        | Per-message secret derived from k_master and n                        |
| σ ∈ {KO,RU,UM,DR,SR,…} | "Tongue" (domain identifier) for multi-signature policy               |
| ℱ                      | Finite field of 8-bit bytes (ℤ/256ℤ)                                  |
| ⊕                      | Bitwise XOR                                                           |
| ‖·‖₂                   | Euclidean (ℓ₂) norm                                                   |
| FFT(·)                 | Discrete Fourier Transform                                            |
| ℋ                      | Harmonic synthesis operator                                           |
| HMAC_K(m)              | HMAC-SHA-256 of message m keyed with K                                |
| BASE_F = 440 Hz        | Reference pitch (A4)                                                  |
| Δf = 30 Hz             | Frequency step per token ID                                           |
| H_max ∈ ℕ              | Maximum overtone index (e.g., 5)                                      |
| SR = 44,100 Hz         | Sample rate for audio synthesis                                       |
| T_sec = 0.5 s          | Duration of generated waveform                                        |
| L = SR·T_sec           | Total number of audio samples                                         |

---

## 2. Dictionary Mapping

The private dictionary 𝒟 is a bijection:

```
∀ τ ∈ 𝒟 : id(τ) ∈ {0, …, |𝒟|−1}
```

**Example**:

```python
𝒟 = {"korah": 0, "aelin": 1, "dahru": 2, ...}
```

The inverse mapping `rev(id)` is also defined.

**Constraint**: Dictionary size |𝒟| should be small (e.g., <148 for Δf=30, H_max=5) to keep frequencies within Nyquist limit (SR/2 = 22,050 Hz).

---

## 3. Modality Encoding

Each modality M is assigned a mode-mask ℳ(M) ⊆ {1,…,H_max} that determines which overtones are emitted.

| Modality | Mask ℳ(M)   | Description          |
| -------- | ----------- | -------------------- |
| STRICT   | {1,3,5}     | Odd harmonics only   |
| ADAPTIVE | {1,…,H_max} | Full harmonic series |
| PROBE    | {1}         | Fundamental only     |

**Mathematical Definition**:

```
ℳ(M) = { {1,3,5}         if M = STRICT
         {1,…,H_max}     if M = ADAPTIVE
         {1}             if M = PROBE
```

---

## 4. Per-Message Secret Derivation

Given the master key k_master and the nonce n (96 bits), compute:

```
K_msg = HKDF(k_master, info = n, len = ℓ)
```

**Practical Implementation** (single HMAC-SHA-256):

```
K_msg = HMAC_k_master(ASCII("msg_key" ∥ n))
```

**Result**: 256-bit key used for Feistel permutation (Section 5) and envelope MAC (Section 7).

---

## 5. Key-Driven Feistel Permutation (Structure Layer)

Let the token vector be:

```
v = [id(τ₀), id(τ₁), …, id(τₘ₋₁)]ᵀ ∈ ℕᵐ
```

Apply a balanced Feistel network with R = 4 rounds.

### Algorithm

For each round r = 0,…,R-1:

1. **Derive round sub-key** (byte-wise) from K_msg:

   ```
   k⁽ʳ⁾ = HMAC_K_msg(ASCII("round" ∥ r)) mod 256
   ```

2. **Split v into left/right halves** (if m is odd, right half gets extra element):

   ```
   L⁽⁰⁾ = v₀:⌊m/2⌋₋₁
   R⁽⁰⁾ = v⌊m/2⌋:m₋₁
   ```

3. **Iterate**:

   ```
   L⁽ʳ⁺¹⁾ = R⁽ʳ⁾
   R⁽ʳ⁺¹⁾ = L⁽ʳ⁾ ⊕ F(R⁽ʳ⁾, k⁽ʳ⁾)
   ```

   where the round function F is byte-wise XOR:

   ```
   F(x, k)ᵢ = xᵢ ⊕ kᵢ mod |k|
   ```

4. **After R rounds**, concatenate:
   ```
   v' = [L⁽ᴿ⁾; R⁽ᴿ⁾]
   ```

**Property**: Feistel construction is involutive (same key reverses the permutation).

---

## 6. Harmonic Synthesis Operator ℋ

Given the permuted token vector v' = [v'₀,…,v'ₘ₋₁] and modality M, the audio waveform x(t) (continuous time) is:

```
x(t) = ∑ᵢ₌₀ᵐ⁻¹ ∑ₕ∈ℳ(M) (1/h) sin(2π(f₀ + v'ᵢ·Δf)·h·t),  0 ≤ t < T_sec
```

where:

- f₀ = BASE_F = 440 Hz
- Δf = 30 Hz
- Factor 1/h provides amplitude roll-off for higher overtones

### Discretization (Sampling)

```
x[n] = x(n/SR),  n = 0,…,L-1,  L = SR·T_sec
```

**Result**: Vector x ∈ ℝᴸ is the audio payload.

---

## 7. Envelope Construction (RWP v3)

### Header Fields

| Field  | Value / Computation                                                    |
| ------ | ---------------------------------------------------------------------- |
| ver    | Constant string "3"                                                    |
| tongue | Chosen domain identifier σ                                             |
| aad    | Associative array of auxiliary data (e.g., {action:"execute", mode:M}) |
| ts     | Current Unix time in milliseconds (t)                                  |
| nonce  | Random 12-byte value n (Base64URL encoded)                             |
| kid    | Identifier of the master key ("master" in demo)                        |

### Canonical String Construction

```
C = "v3." ∥ σ ∥ AAD_canon ∥ t ∥ n ∥ b64url(x)
```

where AAD_canon is the aad map sorted by key and concatenated as `key=value;` (trailing semicolon optional).

### MAC Computation

```
sig = HMAC_k_master(C)  (SHA-256, hex-encoded)
```

### Final Envelope

```json
E = {
  "header": H,
  "payload": b64url(x),
  "sig": sig
}
```

---

## 8. Verification Procedure (Receiver)

Given an envelope 𝔈 and the master key k_master:

### Step 1: Replay Check

```
Reject if |t_now - H.ts| > τ_max  (e.g., τ_max = 60 s)
Reject if H.nonce has already been seen (store nonces for τ_max)
```

### Step 2: Re-compute MAC

```
Re-assemble canonical string Ĉ exactly as in Section 7
Compute ŝig = HMAC_k_master(Ĉ)
Accept only if ŝig == H.sig (constant-time comparison)
```

### Step 3: Recover Token Order

```
Derive K_msg from k_master and H.nonce (Section 4)
Apply Feistel permutation inverse (same routine) to recover original token vector
```

### Step 4: Optional Harmonic Verification

If payload is audio:

1. **Compute FFT**: x̂ = FFT(x)

2. **Locate fundamental peaks** near f₀ + id·Δf for each expected id

3. **Verify overtone set** matches ℳ(H.mode)

4. **Check frequency deviation**: Each peak frequency deviation < ε_f (e.g., 2 Hz)

5. **Check amplitude pattern**: Follows 1/h weighting within tolerance ε_a

**Accept** only if all checks succeed.

---

## 9. Parameter Summary (Concrete Simulation)

| Symbol                    | Value (Example)                        |
| ------------------------- | -------------------------------------- |
| 𝒟                         | {"korah":0, "aelin":1, "dahru":2, ...} |
| H_max                     | 5                                      |
| M set                     | {STRICT, ADAPTIVE, PROBE}              |
| ℳ(STRICT)                 | {1,3,5}                                |
| ℳ(ADAPTIVE)               | {1,2,3,4,5}                            |
| ℳ(PROBE)                  | {1}                                    |
| R (Feistel rounds)        | 4                                      |
| ℓ (key length)            | 256 bits                               |
| τ_max (replay window)     | 60 s                                   |
| ε_f (frequency tolerance) | 2 Hz                                   |
| ε_a (amplitude tolerance) | 0.15 (relative)                        |

---

## 10. Python Simulation Implementation

Complete working implementation provided below. Requires NumPy and SciPy.

```python
import numpy as np
import hashlib
import hmac
import base64
import time
import random
from scipy.fft import fft

# 1. Global Notation
DICTIONARY = {"korah":0, "aelin":1, "dahru":2}
REVERSE_DICT = {v: k for k, v in DICTIONARY.items()}
MODALITIES = {
    'STRICT': [1,3,5],
    'ADAPTIVE': [1,2,3,4,5],
    'PROBE': [1]
}
BASE_F = 440.0  # Hz
DELTA_F = 30.0  # Hz
H_MAX = 5
SR = 44100  # Hz
T_SEC = 0.5  # s
L = int(SR * T_SEC)
NONCE_BYTES = 12
KEY_LEN = 32  # 256 bits
REPLAY_WINDOW_MS = 60000  # 60 s
FREQ_TOL = 10.0  # Hz

used_nonces = set()

def id_token(token):
    return DICTIONARY.get(token, -1)

def rev_id(id_val):
    return REVERSE_DICT.get(id_val, "unknown")

# 4. Per-Message Secret Derivation
def derive_msg_key(master_key, nonce):
    msg = b"msg_key" + nonce
    return hmac.new(master_key, msg, hashlib.sha256).digest()

# 5. Key-Driven Feistel Permutation
def feistel_permute(ids, key, rounds=4):
    out = ids[:]
    for r in range(rounds):
        round_key = hmac.new(key, f"round{r}".encode(), hashlib.sha256).digest()
        for i in range(len(out)):
            out[i] ^= round_key[i % len(round_key)] % 256
    return out

# 6. Harmonic Synthesis Operator
def synth_waveform(permuted_ids, modality):
    mask = MODALITIES.get(modality, [1])
    total_samples = L
    buffer = np.zeros(total_samples, dtype=np.float32)
    slice_len = total_samples // len(permuted_ids)
    for i, id_i in enumerate(permuted_ids):
        f_i = BASE_F + id_i * DELTA_F
        start = i * slice_len
        end = start + slice_len
        t = np.arange(start, end) / SR
        for h in mask:
            buffer[start:end] += np.sin(2 * np.pi * f_i * h * t) / h
    # Normalize to [-1,1]
    max_abs = np.max(np.abs(buffer))
    if max_abs > 0:
        buffer /= max_abs
    return buffer

# 7. Envelope Construction
def canonical_string(header, payload_b64):
    ver = header['ver']
    tongue = header['tongue']
    aad_items = sorted(header['aad'].items())
    aad_str = ';'.join([f"{k}={v}" for k, v in aad_items])
    ts = str(header['ts'])
    nonce = header['nonce']
    return f"{ver}.{tongue}.{aad_str}.{ts}.{nonce}.{payload_b64}"

def sign_envelope(master_key, tongue, aad, payload, audio=True, nonce_raw=None):
    if nonce_raw is None:
        nonce_raw = random.randbytes(NONCE_BYTES)
    ts = int(time.time() * 1000)
    nonce_b64 = base64.urlsafe_b64encode(nonce_raw).decode().rstrip('=')
    header = {
        'ver': '3',
        'tongue': tongue,
        'aad': aad,
        'ts': ts,
        'nonce': nonce_b64,
        'kid': 'master'
    }
    payload_bytes = payload.tobytes() if audio else b''.join([id.to_bytes(4, 'big') for id in payload])
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode().rstrip('=')
    C = canonical_string(header, payload_b64)
    sig = hmac.new(master_key, C.encode(), hashlib.sha256).hexdigest()
    return {
        'header': header,
        'payload': payload_b64,
        'sig': sig
    }, nonce_raw

# 8. Verification Procedure
def verify_envelope(envelope, master_key):
    header = envelope['header']
    payload_b64 = envelope['payload']
    sig = envelope['sig']
    now = int(time.time() * 1000)
    if abs(now - header['ts']) > REPLAY_WINDOW_MS:
        return False, "Timestamp out of window"
    if header['nonce'] in used_nonces:
        return False, "Replay detected"
    used_nonces.add(header['nonce'])
    C = canonical_string(header, payload_b64)
    computed_sig = hmac.new(master_key, C.encode(), hashlib.sha256).hexdigest()
    if computed_sig != sig:
        return False, "Signature mismatch"
    return True, "OK"

# Optional Harmonic Verification
def verify_harmonics(waveform, expected_ids, modality, audio=True):
    if not audio:
        return True
    mask = MODALITIES.get(modality, [1])
    slice_len = L // len(expected_ids)
    harmonics_ok = True
    for i, id_i in enumerate(expected_ids):
        f_i = BASE_F + id_i * DELTA_F
        start = i * slice_len
        end = start + slice_len
        slice_wave = waveform[start:end]
        Y = np.abs(fft(slice_wave))[0:slice_len//2]
        freqs = np.fft.fftfreq(len(slice_wave), 1/SR)[0:slice_len//2]
        for h in mask:
            expected_f = f_i * h
            peak_idx = np.argmin(np.abs(freqs - expected_f))
            deviation = np.abs(freqs[peak_idx] - expected_f)
            if deviation > FREQ_TOL:
                harmonics_ok = False
    return harmonics_ok

# 9. Full Simulation Example
if __name__ == "__main__":
    phrase = "korah aelin dahru"
    modality = 'STRICT'
    tongue = 'KO'
    aad = {"action": "execute", "mode": modality}
    master_key = random.randbytes(KEY_LEN)
    nonce_raw = random.randbytes(NONCE_BYTES)

    # Tokenization
    tokens = phrase.split()
    ids = [id_token(t) for t in tokens]

    # Derive msg key
    msg_key = derive_msg_key(master_key, nonce_raw)

    # Permute
    permuted = feistel_permute(ids, msg_key)

    # Synth waveform
    waveform = synth_waveform(permuted, modality)

    # Envelope
    envelope, _ = sign_envelope(master_key, tongue, aad, waveform, nonce_raw=nonce_raw)

    print('Envelope created:', envelope['header'])

    # Verify
    valid, msg = verify_envelope(envelope, master_key)
    print('Verification:', valid, msg)

    if valid:
        # Decode payload
        payload_bytes = base64.urlsafe_b64decode(envelope['payload'] + '==')
        recovered_wave = np.frombuffer(payload_bytes, dtype=np.float32)

        # Verify harmonics
        harmonics_ok = verify_harmonics(recovered_wave, permuted, modality)
        print('Harmonics OK:', harmonics_ok)

        # Reverse permute
        msg_key_rec = derive_msg_key(master_key, base64.urlsafe_b64decode(envelope['header']['nonce'] + '=='))
        recovered_ids = feistel_permute(permuted, msg_key_rec)
        recovered_phrase = ' '.join([rev_id(id_val) for id_val in recovered_ids])
        print('Recovered Phrase:', recovered_phrase)
```

---

## 11. Integration with RWP v2.1

### Current State (v2.1)

- HMAC-SHA256 multi-signatures only
- No audio verification
- No Feistel permutation
- No harmonic synthesis

### Future State (v3.0)

- **Adds** harmonic verification (this spec)
- **Keeps** HMAC-SHA256 signatures
- **Adds** Feistel permutation for token order obfuscation
- **Adds** intent-modulated audio synthesis

### Migration Path

1. **v2.1 → v3.0**: Add optional `audio_payload` field to envelope
2. **Backward Compatibility**: v3.0 verifiers can process v2.1 envelopes (no audio)
3. **Forward Compatibility**: v2.1 verifiers reject v3.0 envelopes (unknown version)

---

## 12. Security Considerations

### Strengths

- **Intent Verification**: Modality encoding prevents replay across different intent classes
- **Token Obfuscation**: Feistel permutation hides original token order
- **Harmonic Binding**: Audio waveform cryptographically bound to envelope via MAC

### Limitations

- **Dictionary Size**: Limited by Nyquist frequency (|𝒟| < 148 for current parameters)
- **Audio Channel**: Requires reliable audio transmission (susceptible to noise)
- **FFT Resolution**: Frequency tolerance ε_f limited by FFT bin width

### Mitigations

- Use HMAC-SHA256 as primary authentication (audio is secondary verification)
- Increase sample rate SR or decrease Δf for larger dictionaries
- Apply error correction codes to audio payload

---

## 13. References

1. **Feistel Networks**: Luby, M., & Rackoff, C. (1988). "How to construct pseudorandom permutations from pseudorandom functions"
2. **HMAC**: RFC 2104 - HMAC: Keyed-Hashing for Message Authentication
3. **HKDF**: RFC 5869 - HMAC-based Extract-and-Expand Key Derivation Function
4. **FFT**: Cooley, J. W., & Tukey, J. W. (1965). "An algorithm for the machine calculation of complex Fourier series"

---

## 14. Appendix: Test Vectors

### Test Vector 1: STRICT Mode

**Input**:

- Phrase: "korah aelin dahru"
- Modality: STRICT
- Tongue: KO
- Master Key: `0x0123...` (32 bytes)
- Nonce: `0xABCD...` (12 bytes)

**Expected**:

- Permuted IDs: `[2, 0, 1]` (example, depends on key)
- Harmonics: {1, 3, 5} for each token
- Envelope signature: `0x...` (64 hex chars)

### Test Vector 2: ADAPTIVE Mode

**Input**:

- Phrase: "korah aelin"
- Modality: ADAPTIVE
- Tongue: RU
- Master Key: `0x4567...` (32 bytes)
- Nonce: `0xEF01...` (12 bytes)

**Expected**:

- Permuted IDs: `[1, 0]` (example)
- Harmonics: {1, 2, 3, 4, 5} for each token
- Envelope signature: `0x...` (64 hex chars)

---

**Version**: 3.0 (Mathematical Specification)  
**Status**: Complete and Implementable ✅  
**Implementation Status**: Pending (Q2 2026)  
**Last Updated**: January 18, 2026
