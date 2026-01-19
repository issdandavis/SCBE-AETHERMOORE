# Dual-Channel Consensus Gate: Mathematical Specification

**Part of SCBE-AETHERMOORE v3.0.0**  
**Patent**: USPTO #63/961,403  
**Layer Integration**: Layer 11 (Triadic Consensus) + Audio Axis  
**Date**: January 18, 2026

---

## 0. Goal

Given a request event at time `t`, output:

```
decision_t ∈ {ALLOW, QUARANTINE, DENY}
```

by requiring agreement between two independent channels:

1. **Crypto channel**: transcript authenticity + freshness + nonce uniqueness
2. **Voice/acoustic channel**: **challenge-bound** acoustic evidence (liveness / response binding)

This is "dual lattice" in the *operational* sense: a **cryptographic transcript lattice** plus a **frequency-bin lattice** (discrete spectral coordinates).

---

## 1. Notation

| Symbol | Meaning |
|--------|---------|
| `K` | Master key (or session root) |
| `P_t` | Request payload (bytes) |
| `AAD_t` | Canonical metadata (bytes) |
| `τ_t` | Timestamp |
| `n_t` | Nonce (unique within defined scope) |
| `c_t ∈ {0,1}^b` | Acoustic challenge bitstring |
| `y_t[n]` | Audio samples (PCM), n=0,...,N-1 |
| `SR` | Sample rate (Hz) |
| `N` | Segment length (samples) |
| `T_s = N/SR` | Segment duration |
| `k ∈ {0,...,N-1}` | DFT bin index |
| `f_k = k·SR/N` | Bin frequency |

---

## 2. Crypto Channel

### 2.1 Transcript Construction (Authenticated Envelope)

Define a transcript:

```
C_t := "scbe.v1" | AAD_t | τ_t | n_t | P_t
```

Compute a MAC tag (HMAC shown; signatures can be substituted later):

```
tag_t := HMAC_K(C_t)
```

### 2.2 Verification Predicate

Let the verifier maintain a nonce set (or database) `N_seen` for a TTL window.

Define:

**MAC validity**:
```
V_mac(t) = 1 if tag_t = HMAC_K(C_t), else 0
```

**Freshness window**:
```
V_time(t) = 1 if |τ_recv - τ_t| ≤ W, else 0
```

**Nonce uniqueness**:
```
V_nonce(t) = 1 if n_t ∉ N_seen, else 0
```

**Crypto score**:
```
S_crypto(t) := V_mac(t) · V_time(t) · V_nonce(t) ∈ {0,1}
```

**State update on accept**: if `S_crypto(t) = 1`, insert `n_t` into `N_seen` atomically.

---

## 3. Voice/Acoustic Channel (Challenge-Bound Evidence)

### 3.1 Rationale

Audio alone is replayable. To make it meaningful, the audio must **depend on a fresh challenge** `c_t`. The cleanest mechanism is a **spectral watermark** bound to `c_t` and verified by correlation.

### 3.2 Challenge Generation

Generate:
```
c_t ← ${0,1}^b
```

Optionally include protocol metadata:
```
chal_t := (τ_t, n_t, c_t, mode)
```

### 3.3 Deterministic Bin Selection (The "Frequency Lattice")

Define an allowed bin range `[k_min, k_max]` and spacing constraint `Δk_min` to reduce leakage/collisions.

Derive a seed:
```
s_t := HMAC_K("bins" | τ_t | n_t | c_t)
```

Use `s_t` as a PRNG seed to deterministically choose `b` distinct bins:
```
{k_1,...,k_b} ⊆ [k_min, k_max]
```

with `|k_i - k_j| ≥ Δk_min` for `i ≠ j`.

Also derive per-bin phases (optional but improves correlation under some pipelines):
```
φ_j := 2π · u_j,  u_j ∈ [0,1) derived from s_t
```

### 3.4 Watermark Waveform (Challenge Encoding)

Choose amplitudes `a_j` (normalized):
```
a_j := 1/√b
```

Define the watermark:
```
s_c_t[n] := Σ(j=1 to b) a_j · (-1)^(c_t,j) · sin(2π k_j · n/N + φ_j)
```

for `n = 0,...,N-1`

Client emits audio:
```
y_t[n] := v_t[n] + γ · s_c_t[n]
```

where:
- `v_t[n]` is the user's voice (or any acoustic carrier)
- `γ > 0` is a small mixing gain

This construction makes the watermark **mathematically checkable** even if the voice content varies.

---

## 4. Acoustic Verification Statistic

### 4.1 Matched-Filter Projections (Bin Probes)

Define per-bin projection (a matched filter):
```
p_j(t) := (2/N) · Σ(n=0 to N-1) y_t[n] · sin(2π k_j · n/N + φ_j)
```

Under the ideal model (bin-aligned, no clipping), this behaves like:
```
p_j(t) ≈ γ · a_j · (-1)^(c_t,j) + η_j
```

where `η_j` is noise/interference (voice energy leakage, channel noise, mic filtering).

### 4.2 Correlation Score (Challenge Binding)

Define the correlation:
```
corr(t) := Σ(j=1 to b) w_j · (-1)^(c_t,j) · p_j(t)
```

with weights `w_j ≥ 0` (often `w_j = 1`, or inverse-variance weights).

Decision rule:
```
V_audio(t) := 1 if corr(t) ≥ β, else 0
```

Audio score:
```
S_audio(t) := V_audio(t) ∈ {0,1}
```

### 4.3 Optional Robustness Gates (Recommended)

To reduce false accepts from random audio energy:

**Minimum watermark-band energy**:
```
Σ(j=1 to b) p_j(t)² ≥ E_min
```

**No heavy clipping detected**:
```
max_n |y_t[n]| < 1 - ε
```

---

## 5. Final Decision Logic (ALLOW / QUARANTINE / DENY)

Use a conservative 3-outcome rule:

**DENY** if crypto fails:
```
S_crypto(t) = 0 ⇒ DENY
```

**ALLOW** if both pass:
```
S_crypto(t) = 1 ∧ S_audio(t) = 1 ⇒ ALLOW
```

**QUARANTINE** if crypto passes but audio fails:
```
S_crypto(t) = 1 ∧ S_audio(t) = 0 ⇒ QUARANTINE
```

("Quarantine" means step-up verification, rate limit, restricted capability set, or human confirmation.)

---

## 6. Parameter Selection Guidelines

These are engineering constraints that make the math behave:

### 6.1 Nyquist and Harmonic Safety

Ensure watermark frequencies are below Nyquist:
```
k_j < N/2  ⟺  f_k_j < SR/2
```

### 6.2 Bin Alignment (Important)

The whole matched-filter / orthogonality story works best when bins are DFT-aligned:
- Choose a fixed `N` and verify over exactly `N` samples (or window consistently)
- Derive bins `k_j` directly (not arbitrary Hz values)

### 6.3 Choose a Practical Band

Typical mics/speakers roll off in high frequencies. A pragmatic band is often mid-high (example only):
- `f_min` ~ 1200–2000 Hz
- `f_max` ~ 6000–8000 Hz

Convert to bins:
```
k_min = ⌈f_min · N/SR⌉
k_max = ⌊f_max · N/SR⌋
```

### 6.4 Bit-Length (b) vs Detectability

- Larger `b` improves challenge binding and reduces chance acceptance
- But requires more bins and increases detectability demands

A practical starting point: `b ∈ [16, 64]`.

### 6.5 Recommended Defaults

**Profile 1: High-Quality Audio (44.1 kHz)**
```
SR = 44100 Hz
N = 22050 samples (0.5 seconds)
f_min = 2000 Hz → k_min = 1000
f_max = 8000 Hz → k_max = 4000
Δk_min = 50 bins (~100 Hz spacing)
b = 32 bits
β = 0.6 (correlation threshold)
γ = 0.05 (5% watermark mixing)
```

**Profile 2: Telephony/VoIP (16 kHz)**
```
SR = 16000 Hz
N = 16000 samples (1.0 second)
f_min = 1200 Hz → k_min = 1200
f_max = 6000 Hz → k_max = 6000
Δk_min = 30 bins (~30 Hz spacing)
b = 24 bits
β = 0.5 (correlation threshold)
γ = 0.08 (8% watermark mixing)
```

---

## 7. What This *Does* and *Does Not* Claim

### What You Can Defend

✅ **Envelope authenticity** reduces to MAC unforgeability (standard cryptographic assumption)

✅ **Replay resistance** requires and reduces to:
- Nonce uniqueness enforcement + timestamp window enforcement

✅ **Challenge binding**: The verifier checks for a deterministic watermark tied to `c_t`; a stale replay will not correlate for new `c_t`

### What You Should NOT Claim Without Empirical Work

❌ "Deepfake-proof"  
❌ "Guaranteed liveness"  
❌ "Biometric identity"  
❌ Any fixed "accuracy %" unless you publish protocol + dataset + operating point

This scheme is best framed as **step-up liveness / response binding** plus **anomaly gating**, not "voice biometric authentication."

---

## 8. Reference Pseudocode

```python
"""
Dual-Channel Consensus Gate
Inputs: AAD_t, P_t, tau_t, n_t, tag_t, audio y[0..N-1]
Secret: K
State: N_seen
"""

def verify_request(AAD_t, P_t, tau_t, n_t, tag_t, y, c_t, K, N_seen, W, beta):
    # --- Crypto channel ---
    C = "scbe.v1" || AAD_t || tau_t || n_t || P_t
    
    S_crypto = (
        tag_t == HMAC(K, C) and
        abs(tau_recv - tau_t) <= W and
        n_t not in N_seen
    )
    
    if not S_crypto:
        return "DENY"
    
    # --- Audio channel (challenge-bound) ---
    # Deterministically re-derive bins/phases from (tau_t, n_t, c_t)
    seed = HMAC(K, "bins" || tau_t || n_t || c_t)
    bins_and_phases = select_bins_and_phases(seed, k_min, k_max, delta_k_min, b)
    
    # Matched-filter projections
    projections = []
    for j, (k_j, phi_j) in enumerate(bins_and_phases):
        p_j = (2/N) * sum(
            y[n] * sin(2*pi*k_j*n/N + phi_j)
            for n in range(N)
        )
        projections.append(p_j)
    
    # Correlation score
    corr = sum(
        w_j * (-1)**c_t[j] * p_j
        for j, (w_j, p_j) in enumerate(zip(weights, projections))
    )
    
    S_audio = (corr >= beta)
    
    # Decision logic
    if S_audio:
        N_seen.add(n_t)  # atomic
        return "ALLOW"
    else:
        N_seen.add(n_t)  # atomic (still prevent replay)
        return "QUARANTINE"
```

---

## 9. Integration with SCBE-AETHERMOORE

### Layer Mapping

| Component | SCBE Layer | Integration |
|-----------|------------|-------------|
| **Crypto Channel** | Layer 11 (Triadic Consensus) | Crypto + Temporal + Spatial alignment |
| **Audio Channel** | Audio Axis (FFT Telemetry) | Frequency-domain pattern detection |
| **Challenge Binding** | Layer 1 (Context Commitment) | SHA-256(d + id) binding |
| **Nonce Management** | Layer 10 (Lyapunov Stability) | State evolution with uniqueness |

### Implementation Files

```
src/
├── symphonic_cipher/
│   ├── audio/
│   │   ├── dual_channel_consensus.py    # Main implementation
│   │   ├── watermark_generator.py       # Challenge encoding
│   │   ├── matched_filter.py            # Bin projections
│   │   └── correlation_verifier.py      # Challenge binding
│   │
│   └── connectors/
│       └── triadic_bridge.py            # L10→L11 dynamics→consensus

tests/
└── symphonic_cipher/
    └── test_dual_channel_consensus.py   # Verification suite
```

---

## 10. Mathematical Properties

### Theorem 1: Replay Resistance

**Statement**: Given nonce uniqueness enforcement and timestamp window `W`, a replayed transcript `C_t` will be rejected with probability 1.

**Proof**: 
1. If `n_t ∈ N_seen`, then `V_nonce(t) = 0` ⇒ `S_crypto(t) = 0` ⇒ DENY
2. If `|τ_recv - τ_t| > W`, then `V_time(t) = 0` ⇒ `S_crypto(t) = 0` ⇒ DENY
∎

### Theorem 2: Challenge Binding

**Statement**: Given a fresh challenge `c_t`, a stale audio recording `y_old` will fail correlation with probability ≥ 1 - 2^(-b).

**Proof**:
1. Old recording contains watermark for `c_old ≠ c_t`
2. Correlation `corr(t) = Σ w_j · (-1)^(c_t,j) · p_j`
3. For random `c_old`, expected correlation ≈ 0 (orthogonal)
4. Probability of accidental match ≤ 2^(-b) (birthday bound)
∎

### Theorem 3: MAC Unforgeability

**Statement**: Under HMAC security assumptions, forging `tag_t` without knowledge of `K` is computationally infeasible.

**Proof**: Reduces to HMAC-SHA256 PRF security (standard cryptographic assumption). ∎

---

## 11. Performance Characteristics

### Computational Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| HMAC computation | O(|C_t|) | Linear in transcript size |
| Bin selection | O(b log b) | PRNG + sorting |
| Watermark generation | O(N · b) | N samples, b bins |
| Matched filtering | O(N · b) | N samples, b projections |
| Correlation | O(b) | b bins |
| **Total** | **O(N · b)** | Dominated by audio processing |

### Latency Estimates

**Profile 1 (44.1 kHz, N=22050, b=32)**:
- Watermark generation: ~5 ms
- Matched filtering: ~10 ms
- Total: ~15 ms

**Profile 2 (16 kHz, N=16000, b=24)**:
- Watermark generation: ~8 ms
- Matched filtering: ~15 ms
- Total: ~23 ms

---

## 12. Security Analysis

### Attack Vectors

| Attack | Mitigation | Effectiveness |
|--------|------------|---------------|
| **Replay** | Nonce uniqueness + timestamp | ✅ Provably secure |
| **Forgery** | HMAC unforgeability | ✅ Cryptographically secure |
| **Challenge prediction** | HMAC-derived bins | ✅ Computationally infeasible |
| **Watermark removal** | Spread-spectrum embedding | ⚠️ Requires empirical validation |
| **Deepfake synthesis** | Challenge binding | ⚠️ Not claimed as defense |

### Threat Model

**In Scope**:
- Replay attacks (stale audio/transcript)
- Forgery attacks (fake transcripts)
- Challenge prediction (guessing bins)

**Out of Scope**:
- Deepfake synthesis (not claimed)
- Side-channel attacks (timing, power)
- Physical attacks (mic tampering)

---

## 13. Patent Claims

### Claim 1: Dual-Channel Consensus Method

"A method for authenticating requests comprising:
(a) verifying cryptographic transcript authenticity via HMAC;
(b) enforcing nonce uniqueness and timestamp freshness;
(c) generating a fresh acoustic challenge bitstring;
(d) deterministically deriving frequency bins from challenge;
(e) embedding challenge-bound watermark in audio;
(f) verifying watermark correlation at receiver;
(g) outputting ALLOW/QUARANTINE/DENY based on dual-channel consensus."

### Claim 2: Challenge-Bound Watermark

"The method of claim 1, wherein the acoustic watermark is generated as:
```
s[n] = Σ(j=1 to b) a_j · (-1)^(c_j) · sin(2π k_j · n/N + φ_j)
```
where bins {k_j} and phases {φ_j} are deterministically derived from challenge c_t."

### Claim 3: Matched-Filter Verification

"The method of claim 1, wherein verification comprises:
(a) computing per-bin projections via matched filtering;
(b) computing correlation score with challenge-dependent signs;
(c) accepting if correlation exceeds threshold β."

---

## 14. References

1. **HMAC Security**: Bellare, M., Canetti, R., & Krawczyk, H. (1996). "Keying Hash Functions for Message Authentication."
2. **Spread-Spectrum Watermarking**: Cox, I. J., et al. (2007). "Digital Watermarking and Steganography."
3. **Matched Filtering**: Turin, G. L. (1960). "An Introduction to Matched Filters."
4. **Acoustic Holography**: Maynard, J. D., et al. (1985). "Nearfield Acoustic Holography."

---

**Status**: ✅ MATHEMATICALLY SPECIFIED | ⏳ IMPLEMENTATION PENDING | 🔐 PATENT-READY  
**Generated**: January 18, 2026 21:15 PST  
**Patent Deadline**: 13 days remaining
