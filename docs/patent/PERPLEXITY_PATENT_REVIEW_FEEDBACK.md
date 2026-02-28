# Perplexity Patent Spec Review — Feb 28, 2026

Source: Perplexity AI analysis of SCBE_COMPLETE_MATH_AND_CLAIMS.md

## Key Action Items

### Structure
- [ ] Add "Definitions" section near top (plaintext, ciphertext, context vector, intent space, trajectory, swarm, node, trust score, chaos sequence, fractal gate)
- [ ] Add described system diagrams ("Figure 1", "Figure 2") even as text descriptions

### Claim Refinements

**Axis 1 (Core SCBE)**
- [ ] Claim 1: Add "computationally indistinguishable from random" language to noise property
- [ ] Claim 4/5: Add dependent claim tying logistic outputs to spectral phase vector [0,1)
- [ ] Claim 6: Specify "discrete Fourier transform", plaintext as real-valued vector
- [ ] Claim 7: Explicitly tie z_0 derivation to context commitment chi and intent F_I

**Axis 2 (Neural Defense)**
- [ ] Claim 10: Add "decryption attempted only upon acceptance by energy-based authorization"
- [ ] Claim 11/16: New dependent claim — training uses only contexts passing fractal+trajectory+swarm
- [ ] Claim 15: Tie confidence to swarm validity_factor explicitly

**Axis 3 (Intent Configuration)**
- [ ] Claim 18: Add broader independent claim not naming specific words
- [ ] Claim 19: Add broader dependent — "constructed language designed for cryptographic parameterization"
- [ ] Claim 21/23: Make linkage explicit — intent changes actual diffusion parameters

**Axis 4 (Temporal Trajectory)**
- [ ] Claim 25: Add "decryption succeeds only when intent at time t within geodesic tolerance"
- [ ] Claim 29: Call them "self-expiring decryption capabilities" + "without revocation/key rotation"
- [ ] Claim 32: Add "replays produce outputs indistinguishable from noise"

**Axis 5 (Swarm Consensus)**
- [ ] Claim 34: Add trust = f(behavioral auth, swarm deviation, trajectory coherence over time)
- [ ] Claim 41: Add description of cheap-to-expensive filter cascade rationale
- [ ] Claim 46: Add BFT assumptions in description

**Claim 50 (Fail-to-Noise)**
- [ ] Add semi-formal indistinguishability statement in spec text

### General Drafting
- [ ] Use generic "KDF" in claims, "SHA512" in dependent claims only
- [ ] Verify all ranges use consistent notation [a,b] vs [a,b)
- [ ] Tie each test to specific claim numbers
- [ ] Add "tests are illustrative, not limiting" note
- [ ] Add coordinated-combination novelty statement

### Reference Implementation
- Perplexity provided a Python skeleton using kyber-py and dilithium-py
- Should be implemented as `scripts/scbe_reference_impl.py`
- Covers: context, KEM, chaos diffusion, FFT, fractal gate, envelope
- Stubs for: Hopfield, intent vocab, trajectory, swarm

## Full Review Text

(See conversation log for complete feedback)
