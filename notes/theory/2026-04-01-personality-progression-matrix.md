# AI Personality Matrix + Progression Matrix + Tri-Polar Octobix

Date: April 1, 2026
Source: GPT session notes + Claude formalization

## AI Personality Matrix (8 Axes)

P = [A, F, R, E, C, O, T, τ]

| Axis | Symbol | Range | Description |
|------|--------|-------|-------------|
| Assertiveness | A | 0→1 | Passive → Directive |
| Formality | F | 0→1 | Casual → Institutional |
| Risk Tolerance | R | 0→1 | Conservative → Aggressive |
| Empathy | E | 0→1 | Cold → Human-centric |
| Creativity | C | 0→1 | Deterministic → Generative |
| Obedience | O | 0→1 | Independent → Strict |
| Transparency | T | 0→1 | Opaque → Explain reasoning |
| Temporal Focus | τ | 0→1 | Short-term → Long-term |

## Derived Behavioral Functions

- Decision Aggression: D = A · R · (1 - O)
- Safety Bias: S = (1 - R) · O
- Generative Variance: V = C · (1 - O)
- Explanation Depth: X = T · F · (1 + E)

## SCBE Integration (corrected formulas)

Using canonical formula (NOT retired R^(d²)):

- Modified harmonic wall: H_eff(d, pd, P) = 1/(1+φ·d_H+2·pd) × (1 + αR - βO)
- Hyperbolic trust drift: Δd = γ · (R - O)
- Roundtable vote weight: w_i = (O_i + (1 - R_i)) / 2

## Predefined Archetypes

Guardian (RU): A=0.6 F=1.0 R=0.0 E=0.5 C=0.1 O=1.0 T=0.9 τ=0.9
Explorer (CA): A=0.9 F=0.4 R=0.8 E=0.3 C=0.9 O=0.4 T=0.5 τ=0.6
Observer (AV): A=0.3 F=0.6 R=0.2 E=0.4 C=0.3 O=0.8 T=0.9 τ=0.7

## Tri-Polar Octobix Nodal Field

Ψ(x) = Σ over 8 octobix directions × 3 tri-phases of cos(b_i · x + θ_k)

- 8 directions: cube vertices (±1, ±1, ±1) / √3
- 3 phases: 0°, 120°, 240°
- Nodal surface Ψ(x) = 0 defines decision boundaries
- Full cubic symmetry (Oh group)
- Connects to: OctoArmor routing, cymatic voxel storage, crystallography wave bases

## Progression Matrix

Stage(x) = max{k : T(x) ≥ θ_k, C(x) ≥ κ_k, S(x) ≥ σ_k, R(x) ≤ ρ_k, d_H(x,0) ≤ δ_k}

Stages: dormant (0-0.2), observed (0.2-0.4), active (0.4-0.6), trusted (0.6-0.8), governance-grade (0.8-1.0)

Key property: allows regression, quarantine, ejection — not just forward progress.

## Connections to Existing Repo

- OctoArmor = routing hub (src/aetherbrowser/router.py, trilane_router.py)
- Hydra Armor = HYDRA + governance + antivirus layers
- OctoArms = orchestration skill with bounded worker packets
- The 8 personality axes could weight which OctoArmor lane gets selected
- The 3 tri-polar phases map to trilane router's 3 execution paths

## Status in Literature

- Components all established (Markov chains, CMMI, RL value functions, crystallography)
- The specific composition is novel and potentially patentable
- Formal name: "Geometric Progression Matrix" or "Field-Conditioned State Transition System"
