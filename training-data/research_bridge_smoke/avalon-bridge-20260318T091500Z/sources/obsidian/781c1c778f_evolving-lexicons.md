# Evolving Lexicons

> Self-mutating language driven by coherence and hyperbolic drift — cryptographic speciation.

## How It Works

After each successful cross-translation, tokens can **mutate** based on:
1. Coherence score between source and destination
2. Proximity to realm centers in 6D Poincare space
3. Random phonotactic drift (syllable pool mutation)

Two agents using the system separately will slowly grow **mutually unintelligible dialects** — like biological speciation but for encryption.

## Parameters
- `mutation_rate` (default 0.01): Probability of mutation per translation
- `drift_strength` (default 0.05): How far mutations drift from the realm center

## Bijection Preservation

Critical invariant: after every mutation, the lexicon must remain **bijective** (256 unique tokens). If a proposed mutation would create a duplicate, it's abandoned.

## Cryptographic Implications

- Two agents who share a key but evolve separately become cryptographically divergent
- Their token streams become incompatible over time
- Reconciliation requires sharing mutation logs
- This is a feature, not a bug: forward secrecy through linguistic drift

## Cross-References
- [[Six Sacred Tongues]] — Base lexicon structure
- [[CDDM Framework]] — Realm centers from `REALM_CENTERS_6D`
- [[Hyperbolic Geometry References]] — Poincare ball for drift computation

## Academic Grounding
- Nowak & Krakauer (1999) "The Evolution of Language" — linguistic drift models
- Bybee (2010) "Language, Usage and Cognition" — frequency-driven sound change
- The mutation mechanism is a Markov chain on the space of bijections from `{0..255}` to token sets
