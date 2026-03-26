# Core Formulas — Session 2026-03-25

**Author**: Issac Daniel Davis
**Patent**: USPTO #63/961,403
**Status**: Documented from Grok research session + Claude implementation

---

## 1. Harmonic Wall (existing, multiple variants)

### Standard form (tri-manifold-lattice.ts)
```
H(d, R) = R^(d^2)
```
- d = hyperbolic distance from safe center
- R = realm radius (default 1.5 = perfect fifth, or 4.0)

### With intent (layer_13.py)
```
H(d, R, I) = R^((d * gamma_I)^2)
gamma_I = 1 + beta * (1 - I) / 2
```

### With flux parameter (test_scbe_chain.py)
```
H_eff(d, R, x) = R^(d^2 * x)
```
- x = flux modulator (can be time-varying)

### Triadic temporal distance (causality_axiom.py)
```
d_tri = sqrt(d_H^2 + delta_tau^2 + delta_eta^2 + (1 - F_q))
```
- d_H = hyperbolic distance in context space
- delta_tau = temporal difference
- delta_eta = entropy difference
- F_q = quantum fidelity

### Triadic windowed distance (tri-manifold-lattice.ts)
```
d_tri(t) = sqrt(lambda_1 * d_1^2 + lambda_2 * d_2^2 + lambda_3 * d_G^2)
```
- d_1 = immediate window distance
- d_2 = memory window distance
- d_G = governance window distance
- lambda_i >= 0, sum(lambda_i) = 1

---

## 2. Multi-Scale Semantic Field (NEW — from Grok session)

### Nested representation
```
h = f_S(S, f_M(M, f_Z(Z)))
```
- Z = letter-chain carrier field
- M = morphological decomposition
- S = semantic/context embedding
- Each layer constrains the next

### Linear fusion variant
```
h = alpha * Z + beta * M + gamma * S
```
- Convex combination when alpha + beta + gamma = 1
- Learnable via softmax: [alpha, beta, gamma] = softmax([w_Z, w_M, w_S])

---

## 3. Foam Matrix (NEW — Plateau's Laws as regularization)

### Surface tension energy
```
E_surface = integral(dA)  (minimize total membrane area)
```

### Plateau border stability
```
Three films meeting at 120-degree angles (Plateau borders)
Four borders meeting at ~109.47 degrees (tetrahedral vertices)
Mean curvature H = constant across each segment
```

### Sacred Tongue duality
```
Hexagonal lattice (foam bubbles): 120-degree internal angles
Triangular lattice (tongue pathways): 60-degree internal angles
360 / 6 tongues = 60 degrees per tongue
Tongues are the geometric dual of the foam walls
```

### DR weight containment
```
Surface tension counter-force proportional to membrane area
Expansion of DR bubble -> increased total surface area -> pushback
Self-balancing without manual regularization
```

---

## 4. Triangulated PHDM Lattice (NEW — built and tested)

### Construction
```
21 PHDM nodes (6 tongue + 6 phase + 9 telemetry)
30 tokenizer edges (Sacred Tongue channels)
30 triangulated faces (squares -> triangles via diagonal stitch)
30 governance vertices at stitch points
```

### Barycentric interpolation with governance
```
result = (w1 * val_A + w2 * val_B) * governance_factor
governance_factor = 1 + w3 * (governance_weight - 1)
w1 + w2 + w3 = 1 (convex combination)
```

### Three-string overlay
```
String 1: Tokenizer edges (WHAT — semantic content)
String 2: Governance vertices (WHO — compression authority)
String 3: Triadic temporal (WHEN — time validity)
```

### Key property
```
Governance changes blend WITHOUT changing tokenizer values.
Semantics stay the same. Authority changes.
Can't be prompt-injected (not in semantic channel).
Can't be fine-tuned away (not a weight, it's a vertex).
```

---

## 5. Local Quadratic Energy (NEW — from research session)

### Node as quadratic field
```
E_i(x) = x^T * A_i * x
```
- A_i = local interaction matrix (symmetric, PSD)
- Each node defines its own curvature and attraction/repulsion

### System evolution
```
dx/dt = -grad(sum_i E_i(x))
```
- Continuous relaxation toward equilibrium
- No discrete optimization loop needed

### Constraint
```
A_i = A_i^T (symmetric)
A_i >= 0 (positive semi-definite for stability)
```

---

## 6. Null-Space Signatures (existing — documented)

### Definition
```
v = [v_KO, v_AV, v_RU, v_CA, v_UM, v_DR]
Normalize so max(v) = 1.0
threshold tau = 0.05 to 0.08
Null set N = {tongues where v_i < tau}
```

### Attack fingerprints
```
Encoding attacks:     __#___  (only RU active)
Tool exfiltration:    __##__  (only RU + CA)
Spin drift:           ####__  (UM + DR absent)
Direct override:      #_#___  (KO present, AV absent)
```

---

## 7. Notarization (NEW — built and tested)

### Certificate
```
cert.sha256 = SHA-256(data)
cert.sha3_256 = SHA-3-256(data)
cert.tongue_encoded = tongue_encode(SHA-256_bytes, tongue)
cert.hmac = HMAC-SHA-256(signing_key, canonical_json(cert))
cert.timestamp = UTC timestamp
cert.nonce = random 16 bytes
```

### Verification
```
valid = HMAC-SHA-256(key, canonical_json(cert)) == cert.hmac
```

---

## 8. Tangential Probe Framework (NEW — research design)

### Tangential sets
```
T_k(a_i) = N_k(a_i) - N_k_small(a_i)
Core: top k1 neighbors
Tangential: ranks k1+1 to k2
```

### Measurements
```
Overlap: Jaccard(T_k_old, T_k_new)
Drift: (1/|T|) * sum(||x_old - x_new||)
Bridge loss: count tangents connecting to different domain clusters
Curvature: eigenvalues of local A_i matrix
```

### Ablation experiment
```
Control: full corpus
Ablated: corpus minus dense block (e.g., biblical canon)
Measure: centrality shifts, tangential overlap, eigenvalue spectra
```

---

## 9. Whitehole Training Gateway (NEW — architecture)

### Routing
```
interaction -> embedding -> GeoSeal score -> route -> dataset lane

Whitehole: trusted -> direct training
Gray orbit: ambiguous -> human review / eval
Blackhole: toxic -> adversarial corpus / deny set
```

---

## 10. Langues Metric (existing)

```
L(x, t) = sum_l w_l * exp(beta_l * (d_l + sin(omega_l * t + phi_l)))
```

Properties:
- Positivity: L > 0 always (exp > 0, w_l > 0)
- Monotonicity: increases with d_l
- Convexity: unique minimum at d_l = 0
- Stability: Lyapunov V = L >= 0, dV/dt <= 0
- Smoothness: C-infinity

---

## Test Results (2026-03-25)

| System | Tests | Status |
|--------|-------|--------|
| Triangulated PHDM Lattice | 22 | All pass |
| Notarization Service | 13 | All pass |
| Adversarial Detection (improved) | 60 | All pass |
| Novel attack stress test | 14/15 blocked | 0 FP |
| Full test collection | 5,435 | Collected |
