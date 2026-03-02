# AetherMoore + AetherBrowse Master Reference
Version: 0.2
Status: Canonical runtime reference

## 0) Truth sources (files that define reality)
- LAYER_INDEX.md
- docs/scbe_full_system_layer_manifest.json
- docs/SCBE_FULL_SYSTEM_LAYER_MAP.md
- src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py
- src/symphonic_cipher/scbe_aethermoore/layers_9_12.py
- src/symphonic_cipher/scbe_aethermoore/layer_13.py
- src/symphonic_cipher/qasi_core.py
- agents/browser/session_manager.py
- agents/browser/action_validator.py
- agents/browser/bounds_checker.py
- agents/browser/phdm_brain.py
- agents/browser/main.py
- docs/AETHERBROWSE_GOVERNANCE.md

## 1) Axiom mapping table (unitarity/locality/causality/symmetry/composition)
| Axiom | Layers | Runtime role |
| --- | --- | --- |
| unitarity | L2, L4, L5, L7 | Realification/isometry, embedding invariants, hyperbolic transform structure |
| locality | L3, L8 | Localized geometry weighting and realm nearest-neighbor projection |
| causality | L6, L11, L12, L13 | Temporal modulation, triadic temporal distance, risk growth, decision transitions |
| symmetry | L5, L9, L10, L12 | Invariant distance law, symmetric coherence contracts, harmonic response |
| composition | L1, L14 | State packing and final sensory/audio coupling |

## 2) 14-layer runtime equations (with symbol legend)
Legend
- c(t): complex input context state
- x: realified state vector in R^(2D)
- x_prime: weighted real vector
- u: point in Poincare ball
- d_H(.,.): hyperbolic distance
- d_star: realm distance
- S_spec: spectral coherence
- C_spin: spin coherence
- d_tri: triadic distance
- H: harmonic scaling
- rho: risk score

Layer 1 - Complex Context State
- c(t) = [exp(i*identity), intent, trajectory, exp(i*timing/1000), exp(i*commitment), signature]
- runtime: layer_1_complex_context

Layer 2 - Realification
- Phi_1(c) = [Re(c1), Im(c1), ..., Re(cn), Im(cn)]
- runtime: layer_2_realify

Layer 3 - Weighted Transform
- x_prime = G^(1/2) x with G PSD
- runtime: build_langues_metric, layer_3_weighted

Layer 4 - Poincare Embedding
- u = alpha * tanh(norm(x_prime)) * x_prime / norm(x_prime)
- runtime: layer_4_poincare

Layer 5 - Hyperbolic Distance (invariant)
- d_H(u,v) = arccosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
- runtime: layer_5_hyperbolic_distance

Layer 6 - Breathing Transform
- b(t) = 1 + B_max * sin(omega*t)
- norm map: tanh(b(t) * artanh(norm(u))) * u / norm(u)
- runtime: layer_6_breathing

Layer 7 - Phase Transform
- T_phase(u) = R_phi(a oplus u) (Moebius + rotation)
- runtime: layer_7_phase

Layer 8 - Multi-well Realms
- d_star = min_k d_H(u, mu_k)
- runtime: layer_8_multi_well

Layer 9 - Spectral Coherence
- S_spec = 1 - r_HF, r_HF = high frequency power / total power
- runtime: layer_9_spectral_coherence, compute_spectral_coherence

Layer 10 - Spin Coherence
- C_spin = |mean(exp(i*phi_j))| in [0,1]
- runtime: layer_10_spin_coherence, compute_spin_coherence

Layer 11 - Triadic Distance
- Weighted L2 aggregate in L9..L12 module
- runtime: layer_11_triadic_distance, compute_triadic_distance

Layer 12 - Harmonic Scaling
- runtime_profile bounded: H = 1 / (1 + d_star + 2 * phase_deviation)
- audit_profile wall: H = R^(d_star^2) in qasi_core.harmonic_scaling
- alt_profile in L13: H = 1 + alpha * tanh(beta * d_star)
- runtime: layer_12_harmonic_scaling, layers_9_12.harmonic_scaling, qasi_core.harmonic_scaling

Layer 13 - Decision & Risk
- risk_prime = BehavioralRisk * H(d_star) * Time_Multi * Intent_Multi
- decision gates:
  - session-level runtime: ALLOW / QUARANTINE / ESCALATE / DENY (PHDM + bounds merge)
  - layer13 profile: ALLOW / WARN / REVIEW / DENY
- runtime: layer_13_decision, compute_composite_risk

Layer 14 - Audio Axis
- bounded modulation envelope from risk + coherence + intent phase
- runtime: layer_14_audio_axis

## 3) Runtime decision cascade (ALLOW / QUARANTINE / ESCALATE / DENY)
1. ActionValidator builds embedding, sensitivity, and governance scores.
2. SimplePHDM.check_containment computes radius + hyperbolic risk path.
3. BoundsChecker.check_all_bounds returns violations and local decision.
4. ActionValidator merges PHDM, bounds, authority, and verifier results.
5. Session.execute_action enforces final action handling:
   - DENY: no execute, audit entry only
   - ESCALATE: review-required lane
   - QUARANTINE: execute only on allowed quarantine policy
   - ALLOW: dispatch backend action
6. Backend result plus payload + error context is logged in audit.

## 4) Wrapper execution graph (planner -> validator -> bounds_checker -> backend)
Planner / API -> ActionValidator -> PHDM + BoundsChecker + Symphonic verifier -> Decision merge -> Session -> Backend dispatch -> Audit

- Planner/API: agents/browser/main.py (/v1/browse, /v1/safety-check, /v1/integrations/n8n/browse)
- Validator: agents/browser/action_validator.py
- Bounds engine: agents/browser/bounds_checker.py
- Session gate: agents/browser/session_manager.py
- Backends: agents/browsers/* via backend factory (cdp, playwright, selenium, chrome_mcp, mock)

## 5) Numeric stability policy (runtime)
- EPS default: 1e-10 in hot path modules.
- Poincare clamp: norm <= 1 - EPS.
- Hyperbolic safety:
  - safe_arccosh(x) = arccosh(max(1, x))
  - safe_artanh(x) = artanh(clamp(x, -1+EPS, 1-EPS))
- Harmonic safety:
  - wall-profile forms use log/exp clamps
  - bounded profiles are hot-path default
- Deterministic fallback behavior for degenerate cases:
  - zero-length signal
  - empty phase lists
  - zero power spectra
  - invalid geometry inputs

## 6) Spec vs runtime divergence ledger (tracked, versioned, intentional)
| Topic | Spec (docs) | Runtime (code) | Profile ID | Status | Why |
| --- | --- | --- | --- | --- | --- |
| L12 harmonic scaling | canonical wall form appears as exponential style | runtime hot path uses bounded 1/(1+d+2*phase_deviation) | L12_SCORE | intentional | bounded profile prevents overflow in production | 
| L12 audit profile | historical wall form in descriptions | qasi_core keeps R^(d^2) with clamp gating | L12_WALL | intentional | retained for audit, pricing, and review parity |
| L11 triadic formula | mixed prose references | runtime exposes weighted and 14-layer-compatible variants | L11_TRIADIC_A / L11_TRIADIC_B | intentional | context-dependent, both are now explicit |
| consensus thresholds | 2f+1 wording in notes | runtime uses weighted allow/quarantine/escalate/deny thresholds + quorum branches | CONSENSUS_PROFILE | needs pinning | should pin one naming convention per protocol layer |
