# Neural evidence before Sacred Egg hatching

This change applies the existing Python neural-security components to the
GeoSeal-backed Sacred Egg integrator. It is an opt-in server configuration;
once a gate is configured, a hatch caller cannot omit evidence to bypass it.

## Components reused

| Existing component | Role in the gate |
| --- | --- |
| ai_brain/unified_state.py | Recompute the 21D Poincare embedding and dH from observed states |
| ai_brain/detection.py | Phase/distance, curvature, Lissajous, decimal drift, and six-tonic sensors |
| ai_brain/mirror_shift.py | Structural and governance deltas in parallel/perpendicular channels |
| ai_brain/governance_adapter.py | Six signed micro-states, valence rules, asymmetry persistence, multiscale assessment |
| crypto/pqc_liboqs.py | Public-key-only ML-DSA-65 verification, requiring a real backend |
| sacred_egg_integrator.py | Existing ritual checks and GeoSeal decryption after the neural gate |

The separate 54D cognitive_governance representation and the TypeScript Egg
implementation remain separate implementations. This patch does not silently
reinterpret their coordinates as this 21D schema.

## What the review corrected

- For points inside the unit ball, use the equivalent stable identity:
  dH(u,v) = 2 asinh(||u-v|| / sqrt((1-||u||²)(1-||v||²))).
  This avoids rounding acosh(1 + tiny) to zero. Reject non-finite, mismatched,
  boundary and out-of-ball coordinates instead of repairing the denominator.
  Preserve small nonzero movement in the embedding itself.
- Wrap phase differences modulo 2 pi before measuring circular distance.
- Participation ratio and spectral entropy describe relative eigenvalue
  structure. Normalize the spectrum before division rather than adding an
  absolute epsilon that changes the result with units. An all-zero spectrum
  has no observed activity. Small full-dimensional noise is not low rank merely
  because its amplitude is small; valence and tonic checks still observe
  inactivity independently.

The distance is the Poincare-ball metric used by
[Nickel and Kiela](https://papers.nips.cc/paper/2017/file/59dfa2df42d9e3d41f5b02bfc32229dd-Paper.pdf).
The asinh expression follows algebraically from that acosh formula.
The default signature algorithm is
[ML-DSA, FIPS 204](https://csrc.nist.gov/pubs/fips/204/final);
the geometric measurements are additional access criteria, not a new PQ primitive.

## Configure the gate

Import NeuralEggGate, NeuralGatePolicy and NeuralEvidence from
symphonic_cipher.scbe_aethermoore.ai_brain.egg_governance, and
neural_hatch_request from symphonic_cipher.scbe_aethermoore.sacred_egg_integrator.

1. Configure a trusted reference state, maximum dH, and an audience identifying
   the deployment/session. Configure distinct trusted witness public keys
   (three required by default). Different keys do not by themselves establish
   organizational or sensor independence.
2. Supply claim_nonce(audience, nonce, expires_at), backed by an atomic shared
   challenge store. It must reject unknown, expired and already consumed
   challenges, including requests handled by another worker. The gate does not
   supply a process-local production replay store.
3. Construct NeuralEggGate(policy, witness_keys, claim_nonce, audit=local_sink).
   Attach it with SacredEggIntegrator(tokenizer, neural_gate=gate).
4. Collect 8–128 timestamped 21D samples by default. Witnesses independently
   authorize and attest the exact request and measurements. Use
   neural_hatch_request(...) and gate.signing_message(request, evidence) to
   produce the bytes to sign. They include the entire shell and ciphertext,
   context, tongue, ritual, path, nonce, times, policy, baseline and key set.
5. Attach the signatures by witness ID to NeuralEvidence. Pass it as the
   neural_evidence keyword to hatch_egg. No private key belongs in this evidence.

Protocol v1 signs sorted compact UTF-8 JSON emitted by signing_message.
Cross-language signers must match those bytes exactly, including number encoding;
use a future explicitly versioned canonical encoding for different serializers.

All authentication, freshness and bounded-input checks precede sensor work.
The receiver derives the embeddings, distances and scores itself. It evaluates
the uncorrected states with alignment disabled and contraction strength zero.
Individual sensor flags and valence violations cannot be averaged into ALLOW.
A missing window is QUARANTINE. Authentication/replay/backend failures are DENY.
The existing hatch result still exposes only sealed noise or the hatched payload;
detailed reports go only to the trusted audit sink.

## Operational limits and review

- Default thresholds are research heuristics. Calibrate against held-out benign
  and adversarial traces before enabling this on a production secret path.
  Signed evidence establishes who attested a window, not whether its meaning
  is correct. Witnesses must not blindly sign agent-supplied measurements.
- The five sensors share input state and are not proven independent. Six-tonic
  scoring currently uses sample-index frequency ratios, not calibrated wall-clock
  Hz. The preserved timestamps provide freshness/order, not a physical-frequency
  proof.
- Static or opposing signals are observations requiring review. Do not label every
  hold as an attack, or feed it directly into online weight updates. Preserve the
  per-sensor scores and six signed counts; validate confirmed cases in a separate
  evaluation/training workflow. A gate ALLOW also does not attest that the later
  GeoSeal decrypt or downstream task succeeded.
- This adds protection only to instances configured with the gate. It does not
  migrate legacy Eggs, repair the separate TypeScript quorum/key-framing issues,
  implement an invertible geometric cipher, or prove a new hybrid PQ combiner.
- Reverting this integration removes the extra access condition. Rollback should
  close the affected endpoint rather than silently serve it without the gate.

Focused regressions cover cancellation and boundary distances, spectral unit
invariance, phase wraps, complete-request signature binding, distinct witness
keys, freshness, replay, malformed measurements, conflicting signed channels,
static observations, and the gate-before-decrypt call order. Signature integration
uses real ML-DSA when available; the GeoSeal call-order test explicitly uses a test
double, and separate envelope roundtrips require native liboqs.
