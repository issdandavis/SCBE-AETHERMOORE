# Numeric Determinism Policy

Version: 0.1
Scope: Runtime-critical math in SCBE AetherBrowse + AetherMoore execution graph

## Policy goals
1) Make numeric behavior reproducible.
2) Separate exact, epsilon-tolerant, and stochastic computations.
3) Enforce explicit tolerances in tests and audits.

## Tier 0 — Bit-exact
Any operation below must be deterministic and exact:
- Transcript hash input canonicalization and digest (where used)
- HKDF key derivation inputs/outputs
- Horadam recurrence / sequence transforms
- SS1 parse + format canonicalization
- Audit record schemas and trace hashing

Acceptance: exact byte/float-equality match for same inputs and environment.

## Tier 1 — Epsilon-tolerant
Apply strict deterministic tolerance checks.
- Domain: Poincaré embedding math, FFT coherence, spectral/spin metrics, triadic distance, decision scores, and bound derivations.

Allowed tolerances:
- `abs_eps = 1e-9`
- `rel_eps = 1e-6`

Monotonicity requirements:
- `d* ↑` must not decrease bounded harmonic score in runtime-compliant profiles (`1/(1+d*+...)`).
- More high-frequency energy must not increase `S_spec`.
- More angular disagreement must not increase `C_spin`.
- Larger risk factors must not lower composite `risk_prime` in layer 12/13 profiles.

Failure policy:
- Any monotonicity violation outside tolerance is a hard error in CI numeric gates.

## Tier 2 — Non-deterministic / randomized allowed
Allowed only where explicitly intentional:
- Noise payloads
- Randomized sampling
- Stochastic fallback content generation

Acceptance: seeded or bounded by policy config; outcome class (class/category) preserved, not raw exact values.

## Runtime clamp policy
- `EPS`: use module defaults (typical `1e-10` to `1e-12`) with no silent overrides.
- `poincare_radius_cap`: `1 - EPS`
- `safe_arccosh(x)`: compute with `max(1, x)`.
- `safe_harmonic_exponent`: clamp exponential argument (`logH`) before `exp`.
- `realify` and FFT outputs: no NaN/Inf propagation; deterministic finite fallback.

## Profile gates (to enforce in implementation)
- `runtime_profile: bounded` for production browser-governance path.
- `audit_profile: wall` for paper-style risk wall analysis, feature parity checks, and experiments.

Record all active profile choices in `docs/AETHERMOORE_AETHERBROWSE_MASTER.md` and every divergence record update.