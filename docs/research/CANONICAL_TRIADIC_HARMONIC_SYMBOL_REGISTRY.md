# Canonical Triadic and Harmonic Symbol Registry

Status: working registry for experimental alignment  
Date: 2026-03-25  
Scope: tri-manifold lattice, kernel math chain, causality-triadic lane, 21D state schema

## Why this exists

The repo uses related but non-identical `triadic` and `harmonic` constructs.

This file prevents fake coherence by separating:

1. the `tri-manifold lattice` lane
2. the `kernel formula chain` lane
3. the `causality axiom` Layer 11 lane
4. the `state21_v1` schema

Rule:

- same symbol means same primitive
- if the primitive differs, the symbol must be qualified

## Canonical lanes

| Lane | File | Canonical purpose |
| --- | --- | --- |
| Tri-manifold lattice | [tri_manifold_lattice.py](/C:/Users/issda/SCBE-AETHERMOORE/src/symphonic_cipher/scbe_aethermoore/ai_brain/tri_manifold_lattice.py) | Windowed temporal drift aggregation over three timescales |
| Kernel math chain | [scbe_math_reference.py](/C:/Users/issda/SCBE-AETHERMOORE/src/scbe_math_reference.py) | Canonical formula chain for gate math: distance -> persistence -> wall -> omega |
| Causality axiom Layer 11 | [causality_axiom.py](/C:/Users/issda/SCBE-AETHERMOORE/src/symphonic_cipher/scbe_aethermoore/axiom_grouped/causality_axiom.py) | Time-ordered distance over hyperbolic, temporal, entropy, and fidelity channels |
| 21D runtime state | [STATE_MANIFOLD_21D_PRODUCT_METRIC.md](/C:/Users/issda/SCBE-AETHERMOORE/docs/specs/STATE_MANIFOLD_21D_PRODUCT_METRIC.md) | Fixed schema for canonical state snapshots |

## Lane 1: tri-manifold lattice primitives

Source: [tri_manifold_lattice.py](/C:/Users/issda/SCBE-AETHERMOORE/src/symphonic_cipher/scbe_aethermoore/ai_brain/tri_manifold_lattice.py)

### Symbols

| Symbol | Meaning | Type / range |
| --- | --- | --- |
| `d1` | immediate window average hyperbolic distance | `R>=0` |
| `d2` | memory window average hyperbolic distance | `R>=0` |
| `d_g` | governance window average hyperbolic distance | `R>=0` |
| `lambda_immediate` | immediate manifold weight | `R>0` |
| `lambda_memory` | memory manifold weight | `R>0` |
| `lambda_governance` | governance manifold weight | `R>0` |
| `d_tri_window3` | weighted Euclidean triadic distance | `R>=0` |
| `R_harm` | harmonic base ratio | `R>0`, default `1.5` |
| `d_dim` | harmonic dimension count | `Z>=0`, default `6` |
| `H_scale` | harmonic scale factor | `R>=0` |
| `harmonic_cost_lattice` | scaled triadic cost | `R>=0` |

### Formulas

```text
d_tri_window3 = sqrt(lambda_immediate * d1^2
                   + lambda_memory * d2^2
                   + lambda_governance * d_g^2)

H_scale(d_dim, R_harm) = R_harm^(d_dim^2)

harmonic_cost_lattice = d_tri_window3 * H_scale(d_dim, R_harm)
```

### Default weights

```text
lambda_immediate = 0.5
lambda_memory = 0.3
lambda_governance = 0.2
```

## Lane 2: kernel math chain primitives

Source: [scbe_math_reference.py](/C:/Users/issda/SCBE-AETHERMOORE/src/scbe_math_reference.py)

### Symbols

| Symbol | Meaning | Type / range |
| --- | --- | --- |
| `d_hyp` | Poincare hyperbolic distance between two points | `R>=0` |
| `x_persist` | intent persistence multiplier | `R>=0`, capped at `3.0` |
| `R_wall` | harmonic wall base | `R>1`, default `1.5` |
| `H_eff_kernel` | effective wall cost | `R>=1` |
| `harm_score` | inverted wall score | `[0,1]` |
| `I_fast` | fast timescale input | `R>=0` |
| `I_memory` | memory timescale input | `R>=0` |
| `I_governance` | governance timescale input | `R>=0` |
| `d_tri_phi3` | phi-aggregated triadic risk | `R>=0` |
| `Omega` | five-lock gate product | `[0,1]` |

### Formulas

```text
x_persist = min(3.0, (0.5 + accumulated_intent * 0.25) * (1 + (1 - trust)))

H_eff_kernel(d_hyp, x_persist, R_wall) = R_wall^(d_hyp^2 * x_persist)

harm_score = 1 / (1 + log(max(1, H_eff_kernel)))

d_tri_phi3 = (0.3 * I_fast^phi
            + 0.5 * I_memory^phi
            + 0.2 * I_governance^phi)^(1 / phi)

Omega = pqc_valid * harm_score * drift_factor * triadic_stable * spectral_score
```

## Lane 3: causality-axiom Layer 11 primitives

Source: [causality_axiom.py](/C:/Users/issda/SCBE-AETHERMOORE/src/symphonic_cipher/scbe_aethermoore/axiom_grouped/causality_axiom.py)

### Symbols

| Symbol | Meaning | Type / range |
| --- | --- | --- |
| `u, ref_u` | current and reference Poincare points | open unit ball |
| `d_H` | hyperbolic distance | `R>=0` |
| `tau, ref_tau` | temporal coordinates | `R` |
| `eta, ref_eta` | entropy coordinates | `R` |
| `F_q` | quantum fidelity | `[0,1]` for non-identical amplitudes |
| `d_tri_temporal4` | Layer 11 distance over four components | `R>=0` |

### Formula

```text
d_tri_temporal4 = sqrt(d_H^2 + (Delta tau)^2 + (Delta eta)^2 + (1 - F_q))
```

## Lane 4: canonical state21_v1 schema

Source: [STATE_MANIFOLD_21D_PRODUCT_METRIC.md](/C:/Users/issda/SCBE-AETHERMOORE/docs/specs/STATE_MANIFOLD_21D_PRODUCT_METRIC.md)

### Fixed slot layout

| Slots | Names | Interpretation |
| --- | --- | --- |
| `s[0:6]` | `u_ko..u_dr` | tongue position in `B^6` |
| `s[6:12]` | `theta_ko..theta_dr` | tongue phase in `T^6` |
| `s[12:21]` | telemetry block | governance channels in `R^9` |

### Telemetry block

| Slot | Name |
| --- | --- |
| `s[12]` | `flux_breath` |
| `s[13]` | `flux_rate` |
| `s[14]` | `coherence_spectral` |
| `s[15]` | `coherence_spin` |
| `s[16]` | `coherence_triadic` |
| `s[17]` | `d_star` |
| `s[18]` | `h_eff` |
| `s[19]` | `risk_score` |
| `s[20]` | `trust_score` |

## Do not collapse these symbols

These names are similar but not interchangeable.

| Wrong collapse | Why it is wrong | Safe name |
| --- | --- | --- |
| `d_tri_window3 == d_tri_temporal4` | one is 3-window weighted drift, one is 4-term temporal/entropy/fidelity distance | keep both qualified |
| `H_scale == H_eff_kernel` | one is pure dimensional scale, one includes runtime persistence `x_persist` | keep both qualified |
| `d_g == I_governance` | one is a windowed hyperbolic distance, one is a normalized triadic risk input | keep both qualified |
| `coherence_triadic == d_tri_*` | one is a telemetry slot, the others are raw or derived distances | keep telemetry separate |

## Safe shared variable set for experiments

These are safe to share across representation-ablation runs.

| Symbol | Meaning |
| --- | --- |
| `A` | shared anchor vocabulary |
| `X` | shared probe set |
| `k_core` | core neighborhood size |
| `k_tangent` | tangential neighborhood ceiling |
| `E^(r)` | embedding matrix for run `r` |
| `G^(r)` | graph induced from run `r` |
| `A_i^(r)` | local quadratic probe matrix around anchor `i` in run `r` |
| `Delta_proc` | Procrustes alignment error |
| `Delta_D` | pairwise distance-matrix drift |
| `Delta_A,i` | local quadratic drift for anchor `i` |

## Naming rule for future work

Before introducing a new symbol:

1. search whether it already exists in a different lane
2. if the primitive differs, add a qualifier
3. if the primitive matches, reuse the existing symbol and definition

Fail-closed rule:

- if a proposed symbol cannot be mapped cleanly to an existing lane, mark the proposal `experimental_unbound` until the mapping is explicit
