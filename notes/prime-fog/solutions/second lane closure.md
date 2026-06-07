---
tags: [prime-fog, closure, falsification, targeting]
updated_at: 2026-06-05
---

# Second Lane Closure

Status: CLOSED as a targeting/search program.

The second-lane search is now resolved from two independent directions:

1. Row-cache lane search: every proposed non-frozen lane has failed the correct
   null. IP, RR, log/spiral axes, gap acceleration, ratio graph resonance,
   residue wheel, numerical emulsion, prime circuit geometry, lambda/graph-map,
   ratio-depth, topology, and cassette/CMPSSZ variants are all rejected under
   the appropriate null floor. Frozen is the only null-clearing axis.
2. Exact-sequence reframe: raw primes and the actual `P(P(n))` anchor sequence
   both reduce to density control. Local gap geometry, ratio curvature,
   residue-lane ranking, and long-range periodogram structure do not narrow the
   search cone beyond the honest density baseline. Apparent wins were flat
   baseline traps where `log p` / density drift masqueraded as signal.

## Decision

Do not spend more compute searching for a second targeting lane unless the
candidate first states which honest baseline it can beat and which null can
falsify it.

Current honest baselines:

- Raw primes: wheel + PNT + LO-S residue anti-correlation.
- `P(P(n))` anchors: empirical density envelope, then held-out local-feature
  improvement over density-only.
- Row-cache scores: NMS count-proxy precision against count-matched nulls;
  use circular-shift null for smooth/autocorrelated scores.

## Final Spectrum Fork

The rotated log-frame result is real but not a targeting lane. Riemann-zero
structure can be recovered from the prime sequence in the log domain; that is
known explicit-formula structure. It helps count primes globally but does not
cheaply point at the next local gap.

The last honest fork was:

```text
Does the P(P(n)) sequence carry its own spectral comb,
or does it only inherit zeta structure through pi(x)?
```

That is now resolved. A proper Gaussian-windowed log-spectrum killed the cutoff
ringing artifact and used the correct localization-ratio-vs-gap-shuffle-null
test:

- Raw primes: 15.63x localization at the first ten Riemann zeros vs null p95
  1.62. Positive control passes; the detector sees the known zeta comb.
- `P(P(n))` superprimes: 1.21x localization vs null p95 1.51. No detectable
  inherited or novel comb at this scale.

This is a structural result, not a targeting result. The rotated log frame is
now closed for the second-lane search.

## Operating Rule

Known answers are still valuable, but only as a ledger:

```text
known truth -> relationships -> candidate axis -> null gate -> lane status
```

Do not promote a relationship to a search lane because it aligns in-sample.
Alignment is only a hypothesis. The gate decides whether it has mass.

## See also

Consolidated capstone (full program narrative, graveyard, methodology toolkit):
[[PRIME_FOG_SECOND_LANE_PROGRAM_SUMMARY]].
