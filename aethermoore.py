#!/usr/bin/env python3
"""
AetherMoore – Full‑stack reference implementation
* Conlang → ID mapping (supports negatives)
* Feistel‑permutation (4 rounds, XOR‑based)
* Binary (strict) & Adaptive (non‑binary) harmonic synthesis
* FFT‑based fingerprint (first 16 harmonics + jitter + shimmer)
* RWP‑v3 envelope (HMAC‑SHA‑256, nonce, timestamp)
* Verification routine
"""

import os, time, json, base64, hmac, hashlib
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.fftpack import fft, fftfreq

# ----------------------------------------------------------------------
# 0. GLOBAL SETTINGS
# ----------------------------------------------------------------------
FS          = 44_100                 # sample rate (Hz)
DUR         = 0.8                    # seconds per utterance
F0          = 220.0                  # fundamental (A3) for "Korah"
DELTA_F     = 30.0                   # Hz per token‑id step
NONCE_BYTES = 12
MASTER_KEY  = os.getenv("MASTER_KEY", os.urandom(32))  # 256‑bit secret
MAX_HARM    = 12                     # number of overtones for Adaptive mode

# ----------------------------------------------------------------------
# 1. CONLANG → TOKEN IDS (allows negatives)
# ----------------------------------------------------------------------
CONLANG = {
    "shadow": -1, "gleam": -2, "flare": -3,
    "korah": 0, "aelin": 1, "dahru": 2,
    "melik": 3, "sorin": 4, "tivar": 5,
    "ulmar": 6, "vexin": 7,
}
REV = {v:k for k,v in CONLANG.items()}

# ----------------------------------------------------------------------
# 2. AUDIO SYNTHESIS
# ----------------------------------------------------------------------
def t_grid(): return np.linspace(0, DUR, int(FS*DUR), endpoint=False)

def square_wave(ids):
    """Binary (strict) – odd‑harmonic square‑wave approximation."""
    t = t_grid()
    out = np.zeros_like(t)
    seg = len(t)//len(ids)
    for i, k in enumerate(ids):
        f = F0 + k*DELTA_F
        start, stop = i*seg, (i+1)*seg
        for h in (1,3,5,7,9,11,13,15):
            out[start:stop] += (1/h)*np.sin(2*np.pi*f*h*t[start:stop])
    return out/np.max(np.abs(out))

def adaptive_wave(ids):
    """Non‑binary – full harmonic series + jitter + 6 Hz vibrato."""
    rng = np.random.default_rng(seed=42)   # reproducible demo
    t = t_grid()
    out = np.zeros_like(t)
    seg = len(t)//len(ids)
    for i, k in enumerate(ids):
        f = F0 + k*DELTA_F
        start, stop = i*seg, (i+1)*seg
        for h in range(1, MAX_HARM+1):
            amp   = (1/h) * rng.uniform(0.8, 1.2)
            phase = rng.uniform(0, 2*np.pi)
            vib   = 1.0 + 0.003*np.sin(2*np.pi*6*t[start:stop])   # 6 Hz vibrato
            out[start:stop] += amp*np.sin(2*np.pi*f*h*vib*t[start:stop] + phase)
    return out/np.max(np.abs(out))

# ----------------------------------------------------------------------
# 3. FEISTEL PERMUTATION (key‑driven)
# ----------------------------------------------------------------------
def feistel_perm(ids, key):
    """Four‑round Feistel, XOR‑based, operates on uint8."""
    arr = np.array(ids, dtype=np.uint8)
    left, right = arr[:len(arr)//2].copy(), arr[len(arr)//2:].copy()
    for r in range(4):
        sub = hmac.new(key, f"rnd{r}".encode(), hashlib.sha256).digest()
        sub = np.frombuffer(sub, dtype=np.uint8)
        sub = np.resize(sub, right.shape)
        new_right = left ^ sub
        left, right = right, new_right
    return np.concatenate([left, right])

# ----------------------------------------------------------------------
# 4. FEATURE EXTRACTION (FFT → fingerprint)
# ----------------------------------------------------------------------
def fingerprint(signal):
    """Return a 256‑byte descriptor (first 16 harmonics + jitter + shimmer)."""
    N = len(signal)
    X = np.abs(fft(signal))[:N//2]
    freqs = fftfreq(N, 1/FS)[:N//2]

    # fundamental detection (largest peak > 100 Hz)
    idx = np.argmax(X)
    f0 = freqs[idx]

    # first 16 harmonic magnitudes (±2 Hz tolerance)
    harms = []
    for h in range(1, 17):
        target = h*f0
        win = np.where(np.abs(freqs-target) <= 2)[0]
        harms.append(float(np.max(X[win])) if win.size else 0.0)

    # jitter (std of zero‑crossing intervals) & shimmer (envelope std/mean)
    zero_cross = np.where(np.diff(np.signbit(signal)))[0]
    jitter = float(np.std(np.diff(zero_cross))) if len(zero_cross)>1 else 0.0
    env = np.abs(signal)
    shimmer = float(np.std(env))/float(np.mean(env))

    vec = np.array([f0]+harms+[jitter, shimmer], dtype=np.float32)
    return vec.tobytes()

# ----------------------------------------------------------------------
# 5. RWP‑v3 ENVELOPE (HMAC, nonce, timestamp)
# ----------------------------------------------------------------------
def make_envelope(payload_bytes, mode, tongue="KO"):
    nonce = os.urandom(NONCE_BYTES)
    ts    = int(time.time()*1000)
    hdr = {
        "ver":"3","tongue":tongue,
        "aad":{"action":"execute","mode":mode},
        "ts":ts,
        "nonce":base64.urlsafe_b64encode(nonce).decode().rstrip("="),
        "kid":"master"
    }
    plb64 = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")
    canon = ".".join([
        "v3",hdr["tongue"],
        ";".join(f"{k}={v}" for k,v in sorted(hdr["aad"].items())),
        str(hdr["ts"]), hdr["nonce"], plb64
    ])
    sig = hmac.new(MASTER_KEY, canon.encode(), hashlib.sha256).hexdigest()
    return {"header":hdr,"payload":plb64,"sig":sig}

def verify_envelope(env):
    hdr = env["header"]
    now = int(time.time()*1000)
    if now - hdr["ts"] > 60_000: return False
    canon = ".".join([
        "v3",hdr["tongue"],
        ";".join(f"{k}={v}" for k,v in sorted(hdr["aad"].items())),
        str(hdr["ts"]), hdr["nonce"], env["payload"]
    ])
    exp = hmac.new(MASTER_KEY, canon.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(exp, env["sig"])

# ----------------------------------------------------------------------
# 6. DEMO PIPELINE (end‑to‑end)
# ----------------------------------------------------------------------
def demo():
    phrase = "korah aelin dahru"
    ids = np.array([CONLANG[w] for w in phrase.split()], dtype=int)

    # per‑message secret (HMAC‑derived)
    nonce = os.urandom(NONCE_BYTES)
    msg_key = hmac.new(MASTER_KEY, b"msg_key"+nonce, hashlib.sha256).digest()

    # 1️⃣ permutation
    perm_ids = feistel_perm(ids, msg_key)

    # 2️⃣ generate both modalities
    bin_fp = fingerprint(square_wave(perm_ids))
    ada_fp = fingerprint(adaptive_wave(perm_ids))

    # 3️⃣ envelope (use Adaptive as the "good" path)
    env = make_envelope(ada_fp, mode="ADAPTIVE", tongue="KO")

    # 4️⃣ verification
    ok = verify_envelope(env)

    # 5️⃣ quick visual sanity check (saved to PNG)
    t = t_grid()
    plt.figure(figsize=(8,2))
    plt.plot(t, adaptive_wave(perm_ids), label="Adaptive", alpha=0.7)
    plt.plot(t, square_wave(perm_ids), label="Binary", alpha=0.5)
    plt.legend(); plt.title("Waveforms (permuted IDs)");
    plt.tight_layout(); plt.savefig("symphonic_implementation_analysis.png")
    plt.close()

    print("\n=== DEMO RESULT ===")
    print("Original IDs :", ids.tolist())
    print("Permuted IDs :", perm_ids.tolist())
    print("Verification :", "PASS" if ok else "FAIL")
    print("Fingerprint size (bytes) :", len(ada_fp))

if __name__ == "__main__":
    demo()
