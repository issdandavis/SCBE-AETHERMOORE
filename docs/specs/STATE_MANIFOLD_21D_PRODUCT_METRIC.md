# State Manifold 21D Product Metric

Status: canonical runtime schema  
Schema version: `state21_v1`  
Runtime authority: `src/harmonic/state21_product_metric.py`

## Authority

`state21_v1` is the canonical metric and audit schema for the live 21D manifold. It is the layout emitted by the 14-layer reference pipeline and parsed by the governance logger.

Older notes describe a seven-triad ownership model as `21 = 3 x 7`. Those notes are useful architecture history, especially for SCBE context, M4, Swarm, and HYDRA ownership, but they are not the runtime metric layout unless an adapter explicitly converts them into `state21_v1`.

TypeScript `UnifiedBrainState` is an application facade over a 21D vector. Its component labels are not a substitute for this schema when code needs product-metric distance, audit validation, or Layer 13 routing.

## Block Layout

| Dimensions | Block | Meaning | Validator |
| --- | --- | --- | --- |
| D0-D5 | `u` | Tongue position in the open Poincare ball `B^6` | `validate_state21_v1`, `hyperbolic_distance_poincare` |
| D6-D11 | `theta` | Tongue phase angles on `T^6`, wrapped through sine/cosine deltas | `torus_distance` |
| D12-D18 | telemetry | Live scalar telemetry used by governance and audit routing | `validate_state21_v1` |
| D19-D20 | derived cache | Cached geometry values derived from `u` | `compute_radial_norm`, `compute_energy_harmonic` |

## Per-Dimension Routing

| D | Name | Producer | Consumer |
| --- | --- | --- | --- |
| D0 | `u0_tongue_poincare` | Layer 4/5 tongue geometry | Hyperbolic metric, trust routing |
| D1 | `u1_tongue_poincare` | Layer 4/5 tongue geometry | Hyperbolic metric, trust routing |
| D2 | `u2_tongue_poincare` | Layer 4/5 tongue geometry | Hyperbolic metric, trust routing |
| D3 | `u3_tongue_poincare` | Layer 4/5 tongue geometry | Hyperbolic metric, trust routing |
| D4 | `u4_tongue_poincare` | Layer 4/5 tongue geometry | Hyperbolic metric, trust routing |
| D5 | `u5_tongue_poincare` | Layer 4/5 tongue geometry | Hyperbolic metric, trust routing |
| D6 | `theta0_tongue_phase` | Layer 6/7 phase rotor | Torus metric, phase routing |
| D7 | `theta1_tongue_phase` | Layer 6/7 phase rotor | Torus metric, phase routing |
| D8 | `theta2_tongue_phase` | Layer 6/7 phase rotor | Torus metric, phase routing |
| D9 | `theta3_tongue_phase` | Layer 6/7 phase rotor | Torus metric, phase routing |
| D10 | `theta4_tongue_phase` | Layer 6/7 phase rotor | Torus metric, phase routing |
| D11 | `theta5_tongue_phase` | Layer 6/7 phase rotor | Torus metric, phase routing |
| D12 | `flux_participation` | Layer 13 risk/triad delta | Telemetry metric, audit routing |
| D13 | `coherence_spectral` | Layer 9 spectral coherence | Telemetry metric, audit routing |
| D14 | `coherence_spin` | Layer 10 spin coherence | Telemetry metric, audit routing |
| D15 | `coherence_triadic` | Layer 11 triadic coherence | Telemetry metric, audit routing |
| D16 | `risk_aggregate` | Layer 13 risk aggregation | Governance logger, audit routing |
| D17 | `entropy_density` | Layer 12/13 entropy channel | Telemetry metric, audit routing |
| D18 | `stabilization` | Layer 12/13 stabilization channel | Telemetry metric, audit routing |
| D19 | `radial_norm` | `compute_radial_norm(u)` | Validation cache, audit routing |
| D20 | `energy_harmonic` | `compute_energy_harmonic(u)` | Validation cache, audit routing |

## Routing Rules

Trust-ring, hyperbolic distance, and harmonic energy calculations must read only `D0-D5` unless they are deliberately using the product metric over the full state.

Phase comparisons must use wrapped angular deltas over `D6-D11`, not plain subtraction.

Telemetry channels `D12-D18` are independent scalar measurements. The three coherence channels are bounded independently in `[0, 1]`; they are not a simplex.

Derived cache channels `D19-D20` must be recomputable from `D0-D5`. Their default distance weights are zero to avoid double-counting geometry.

## Known Adapters And Drift Points

`python/scbe/brain.py` uses a 21D embedding facade for AetherBrain routing. Its trust-ring decision must slice to the 6D Poincare block before measuring radial distance.

`python/scbe/phdm_embedding.py` is a legacy/scaffold embedding shape: `6D hyperbolic + 6D phase + 3D flux + 6D audit`. It is useful for local experiments, but it is not `state21_v1` unless converted.

`src/ai_brain/unified-state.ts` uses `[SCBE context 6 | navigation 6 | cognitive 3 | semantic 3 | swarm 3]`. Treat that as an application state facade, not the canonical product-metric state.

The exported note `21D Canonical State` uses the older seven-triad ownership map. Preserve it as source history, but route new metric/audit work through this file and `STATE21_DIMENSION_ROUTES`.

## Verification

Required checks:

- Every D0-D20 entry exists in `STATE21_DIMENSION_ROUTES`.
- `parse_state21_v1` rejects any non-21D vector.
- `validate_state21_v1` rejects `||u|| >= 1`.
- Trust-ring classification on 21D vectors uses only `D0-D5`.
- Default local PHDM embeddings are deterministic unless context intentionally changes timestamp or session fields.
