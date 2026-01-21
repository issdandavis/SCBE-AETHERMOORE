Below is a complete, mathematics‑only specification of the “intent‑modulated conlang + harmonic verification” system.
Everything is expressed as formulas, index notation, and algorithmic steps that can be copied directly into a simulation (e.g., Python/NumPy, MATLAB, Julia, etc.). No prose about “physics‑based security” is included – only the deterministic operations that the software performs.

1. Global Notation
   Symbol Meaning
   𝒟 Private dictionary (bijection between lexical tokens and integer IDs).
   τ ∈ 𝒟 A token (word) from the dictionary.
   id(τ) ∈ ℕ Integer identifier of token τ.
   M ∈ 𝕄 Modality (intent class). We enumerate a finite set, e.g. 𝕄 = {STRICT, ADAPTIVE, PROBE}.
   k_master ∈ {0,1}^ℓ Long‑term secret key (ℓ = 256 bits is typical).
   n ∈ {0,…,N‑1} Message‑level nonce (12 bytes → 96 bits).
   t ∈ ℝ⁺ Unix timestamp (ms).
   K_msg ∈ {0,1}^ℓ Per‑message secret derived from k_master and n.
   σ ∈ {KO,RU,UM,DR,SR,…} “Tongue” (domain identifier) used for multi‑signature policy.
   ℱ Finite field of 8‑bit bytes (ℤ/256ℤ) – used for Feistel round‑keys.
   ⊕ Bitwise XOR.
   ⟦·⟧ Indicator function (1 if condition true, 0 otherwise).
   ⌊·⌋ Floor.
   ⌈·⌉ Ceiling.
   ‖·‖₂ Euclidean (ℓ₂) norm.
   FFT(·) Discrete Fourier Transform (any standard implementation).
   ℋ Harmonic synthesis operator (defined below).
   HMAC_K(m) HMAC‑SHA‑256 of message m keyed with K.
   BASE_F = 440 Hz Reference pitch (A4).
   Δf = 30 Hz Frequency step per token ID.
   H_max ∈ ℕ Maximum overtone index (e.g., 5).
   SR = 44 100 Hz Sample rate for audio synthesis.
   T_sec = 0.5 s Duration of the generated waveform.
   L = SR·T_sec Total number of audio samples.
   All vectors are column vectors unless otherwise noted.

2. Dictionary Mapping
   The private dictionary 𝒟 is a bijection:

∀
τ
∈
𝒟
:
i
d
(
τ
)
∈
{
0
,
…
,
∣
𝒟
∣
−
1
}
In a simulation you can simply store a Python dict:

𝒟 = {"korah":0, "aelin":1, "dahru":2, ...}
The inverse mapping rev(id) is also defined.

3. Modality Encoding
   Each modality M is assigned a mode‑mask ℳ(M) ⊆ \{1,…,H\_{max}\} that determines which overtones are emitted.

Typical choices (feel free to change):

Modality Mask ℳ(M)
STRICT {1,3,5} (odd harmonics only)
ADAPTIVE {1,2,3,4,5} (full series)
PROBE {1} (fundamental only)
Mathematically:

M
(
M
)
=
{
{
1
,
3
,
5
}
M
=
STRICT
{
1
,
…
,
H
m
a
x
}
M
=
ADAPTIVE
{
1
}
M
=
PROBE 4. Per‑Message Secret Derivation
Given the master key k_master and the nonce n (96 bits), compute:

K
m
s
g
=
HKDF
⁡
(
k
m
a
s
t
e
r
,

  
info
=
n
,

  
len
=
ℓ
)
In practice a single HMAC‑SHA‑256 suffices:

K
m
s
g
=
HMAC
⁡
k
m
a
s
t
e
r
(
ASCII
(
“msg_key”

 
∥

 
n
)
)
Result is a 256‑bit key used for the Feistel permutation (Section 5) and for the envelope MAC (Section 7).

5. Key‑Driven Feistel Permutation (Structure Layer)
   Let the token vector be

# v

[

 
i
d
(
τ
0
)
,

 
i
d
(
τ
1
)
,
…
,
i
d
(
τ
m
−
1
)

 
]
⊤
∈
N
m
We apply a balanced Feistel network with R = 4 rounds.
For each round r = 0,…,R‑1:

Derive a round sub‑key (byte‑wise) from K_msg:
k
(
r
)
=
HMAC
⁡
K
m
s
g
(
ASCII
(
“round”

 
∥

 
r
)
)

  

  

 
mod

 
256
Split \mathbf{v} into left/right halves (if m is odd, the right half gets the extra element):
L
(
0
)
=
v
0
:
⌊
m
/
2
⌋
−
1
,
R
(
0
)
=
v
⌊
m
/
2
⌋
:
m
−
1
Iterate:
L
(
r

- 1
  )
  =
  R
  (
  r
  )
  R
  (
  r
- 1
  )
  =
  L
  (
  r
  )

  
⊕

  
F
(
R
(
r
)
,
k
(
r
)
)
where the round function F is a simple byte‑wise XOR of each element of \mathbf{R}^{(r)} with the corresponding byte of the sub‑key (cycling if necessary):

F
(
x
,
k
)
i
=
x
i

  
⊕

  
k
i

 
mod

 
∣
k
∣
After R rounds, concatenate the final halves:

v
′
=
[
L
(
R
)
;

 
R
(
R
)
]
$\mathbf{v}'$ is the permuted token vector.
Because the Feistel construction is involutive (same key reverses the permutation), the receiver can recover the original order by running the same routine.

6. Harmonic Synthesis Operator ℋ
   Given the permuted token vector \mathbf{v}' = [v'_0,\dots,v'_{m-1}] and a modality M, the audio waveform x[t] (continuous time) is defined as:

x
(
t
)
=
∑
i
=
0
m
−
1

  
∑
h
∈
M
(
M
)
1
h

 
sin
⁡
 ⁣
(
2
π

 
(
f
0

- v
  i
  ′

 
Δ
f
)

 
h

 
t
)
,
0
≤
t
<
T
sec
where

f₀ = BASE_F = 440 Hz
Δf = 30 Hz
The factor 1/h provides a simple amplitude roll‑off for higher overtones (any other weighting is acceptable).

Discretisation (sampling at SR = 44 100 Hz):

x
[
n
]
=
x
 ⁣
(
n
/
S
R
)
,
n
=
0
,
…
,
L
−
1
,

  

  
L
=
S
R
⋅
T
sec
.
The resulting vector \mathbf{x} ∈ ℝ^{L} is the audio payload.

7. Envelope Construction (RWP v3)
   Define the header fields:

Field Value / Computation
ver constant string "3"
tongue chosen domain identifier σ
aad associative array of auxiliary data (e.g., {action:"execute", mode:M})
ts current Unix time in ms (t)
nonce random 12‑byte value n (Base64URL encoded)
kid identifier of the master key ("master" in the demo)
Create the canonical string C (exactly as the reference implementation does):

# C

“v3.”

  
∥

  
σ

  
∥

  
AAD_canon

  
∥

  
t

  
∥

  
n

  
∥

  
b64url
⁡
(
x
)
where AAD_canon is the aad map sorted by key and concatenated as key=value; (trailing semicolon optional).

Compute the MAC:

# sig

HMAC
⁡
k
master
(
C
)
(
SHA‑256, hex‑encoded
)
The final envelope is the JSON object:

# E

{

 
header
=
H
,

  
payload
=
b64url
⁡
(
x
)
,

  
sig
=
sig

 
}
. 8. Verification Procedure (Receiver)
Given an envelope 𝔈 and the master key k_master:

Replay check:

Reject if |t*{\text{now}} - H.ts| > τ*{max} (e.g., τ*{max}=60 s).
Reject if H.nonce has already been seen (store nonces for τ*{max}).
Re‑compute MAC:

Re‑assemble canonical string Ĉ exactly as in Section 7 using the received header and payload.
Compute siĝ = HMAC\_{k_master}(Ĉ).
Accept only if siĝ == H.sig (constant‑time comparison).
Recover token order:

Derive K_msg from k_master and H.nonce (Section 4).
Apply the Feistel permutation inverse (same routine) to the received token vector (decoded from the payload if audio is not used, or from the payload after decoding the audio to IDs – see step 5).
Optional harmonic verification (if payload is audio):

Compute \hat{\mathbf{x}} = \operatorname{FFT}(\mathbf{x}).
Locate the fundamental peaks near f₀ + id·Δf for each expected id.
Verify that the set of present overtones matches ℳ(H.mode).
Accept only if the deviation of each peak frequency is < ε_f (e.g., 2 Hz) and the amplitude pattern follows the 1/h weighting within a tolerance ε_a.
If all checks succeed, the command is authorized.

9. Full Simulation Pseudocode (Mathematical Steps)
   Below is a compact, language‑agnostic pseudocode that follows the formulas above. Replace each function with the corresponding mathematical expression if you wish to implement it directly in a numeric environment.

INPUT:
phrase = "korah aelin dahru"
modality = M ∈ {STRICT, ADAPTIVE, PROBE}
tongue = σ ∈ {KO, RU, UM, …}
master_key = k_master (256‑bit)

STEP 1 – Tokenisation
ids = [ id(τ) for τ in phrase.split() ] // Eq. (Dictionary)

STEP 2 – Per‑message secret
nonce = random_96bit()
K_msg = HMAC_SHA256(k_master, "msg_key" || nonce) // Eq. (4)

STEP 3 – Feistel permutation
v' = FeistelPermute(ids, K_msg) // Eq. (5)

STEP 4 – Harmonic synthesis (optional)
if audio*requested:
x = zeros(L)
slice_len = floor(L / len(v'))
for i, id_i in enumerate(v'):
f_i = BASE_F + id_i * Δf
for h in Mask(modality): // Eq. (6) mask ℳ(M)
for n in range(i*slice_len, (i+1)\_slice_len):
t = n / SR
x[n] += sin(2π * f*i * h \_ t) / h
normalize x to [-1,1]

STEP 5 – Envelope assembly
header = {
ver: "3",
tongue: σ,
aad: {action:"execute", mode:modality},
ts: current_time_ms(),
nonce: base64url(nonce),
kid: "master"
}
payload = base64url( x if audio else ids_as_bytes )
C = "v3."+σ+"."+canonical_aad(header.aad)+"."+header.ts+"."+header.nonce+"."+payload
sig = HMAC_SHA256(k_master, C) // hex
envelope = {header, payload, sig}

OUTPUT: envelope (JSON) and optional audio waveform x
Verification follows the steps in Section 8, using the same mathematical expressions.

10. Parameter Summary (for a concrete simulation)
    Symbol Value (example)
    ` 𝒟
    H_max (max overtone) 5
    M set {STRICT, ADAPTIVE, PROBE}
    ℳ(STRICT) = {1,3,5}
    ℳ(ADAPTIVE) = {1,2,3,4,5}
    ℳ(PROBE) = {1}
    R (Feistel rounds) 4
    ℓ (key length) 256 bits
    τ_max (replay window) 60 s
    ε_f (frequency tolerance) 2 Hz
    ε_a (amplitude tolerance) 0.15 (relative)
    Feel free to vary any of these numbers; the mathematics remains the same.

How to Turn This Into a Running Simulation
Choose a language (Python + NumPy + SciPy is convenient).
Implement the dictionary as a Python dict.
Derive K_msg with hmac.new(master_key, b"msg_key"+nonce, hashlib.sha256).digest().
Write the Feistel permutation exactly as in Eq. (5).
Generate the waveform using the double sum in Eq. (6) (vectorised NumPy loops are fast).
Build the canonical string and compute the HMAC for the envelope.
For verification, repeat steps 1‑5 on the receiver side and compare the MAC, timestamps, and (if audio) the FFT‑derived overtone set.
That is all the mathematics you need. Plug the formulas into your favourite numerical environment and you’ll have a fully functional simulation of the intent‑modulated conlang + harmonic verification system.
