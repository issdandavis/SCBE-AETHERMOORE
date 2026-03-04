# Family B — Expanded Provisional (FILED)

**Application**: USPTO #63/961,403
**Filed**: January 15, 2026
**Title**: Context-Bound Cryptographic Authorization System
**Stack**: 14-layer
**Status**: FILED — Missing Parts pending (PTO/SB/15A + $82 by April 19, 2026)
**Non-Provisional Deadline**: January 15, 2027

---

## Independent Claims

### Claim B-1 (Method)

Context-bound cryptographic authorization method with 9 steps:

(a) receive context vector c(t) in C^D;
(b) realify to R^{2D};
(c) embed into Poincare ball with epsilon-clamping;
(d) compute realm distance d*;
(e) extract coherence signals in [0,1];
(f) compute Risk' = Risk_base * H(d*, R);
(g) decide ALLOW/QUARANTINE/DENY via thresholds theta1 < theta2;
(h) create cryptographic envelope on ALLOW/QUARANTINE;
(i) output random noise on failure.

### Claim B-2 (System)

Distributed authorization system with 10 modules:
1. Context acquisition
2. Hyperbolic embedding with clamping
3. Breathing transform (diffeomorphism)
4. Phase transform (isometry)
5. Realm distance
6. Coherence extraction
7. Risk computation with harmonic amplification
8. Decision partitioning
9. AES-256-GCM envelope
10. Fail-to-noise

---

## Dependent Claims

| # | Depends On | Subject |
|---|-----------|---------|
| B-3 | B-1 | Clamping operator projects to boundary via (1-epsilon)*u/||u|| |
| B-4 | B-1 | Hyperbolic embedding Psi_alpha(x) = tanh(alpha*||x||)*x/||x|| |
| B-5 | B-1 | Harmonic scaling H(d*, R) = R^{(d*)^2} with R > 1 |
| B-6 | B-1 | Spectral coherence from FFT energy ratios |
| B-7 | B-1 | Spin coherence as mean phasor magnitude |sum(e^{i*theta})|/N |
| B-8 | B-1 | Breathing transform T_breath(u; b) = tanh(b*artanh(||u||))*u/||u|| |
| B-9 | B-1 | Phase transform T_phase(u) = Q*(a + u) preserving d_H |
| B-10 | B-1 | Risk weights w_d + w_c + w_s + w_tau + w_a = 1 |
| B-11 | B-1 | QUARANTINE sets audit_flag in envelope |
| B-12 | B-1 | Cheapest-rejection-first ordering |
| B-13 | B-12 | Specific check order: timestamp, replay, nonce, context, embedding, realm, coherence, risk, crypto |
| B-14 | B-2 | PHDM module detecting intrusions via geodesic deviation |
| B-15 | B-14 | 16 canonical polyhedra traversed via Hamiltonian path + HMAC chaining |
| B-16 | — | Computer-readable medium performing method of B-1 |
