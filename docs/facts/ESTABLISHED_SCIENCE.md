# Established Science — Facts Lane

These are true whether SCBE exists or not. The river was here before us.

---

## Geometry

- **Hyperbolic distance**: d_H = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
  - Lobachevsky & Bolyai, 1830s. Distance grows exponentially near the boundary of the Poincare disk.

- **Plateau's Laws**: Soap films form smooth surfaces where three films meet at exactly 120 degrees, four borders meet at ~109.47 degrees (tetrahedral angle), and mean curvature is constant per segment.
  - Joseph Plateau, 1873. Proved rigorously by Jean Taylor, 1976.

- **Minimal surfaces minimize area**: A minimal surface has zero mean curvature. Soap films naturally find minimum-area configurations.
  - Lagrange posed the problem, 1760. Douglas & Rado solved it, 1931.

- **Hexagonal-triangular duality**: Hexagons (120 degree internal angles) and triangles (60 degree internal angles) are dual tilings of the plane.
  - Euclidean geometry. Hexagons are the most efficient space-filling polygon.

- **Triangles are rigid**: A triangle cannot deform without changing edge lengths. Quadrilaterals can. This is why bridges use trusses.

## Numbers

- **Golden ratio**: phi = (1 + sqrt(5)) / 2 = 1.6180339887...
  - Euclid, ~300 BC. Appears in Fibonacci sequences, phyllotaxis, quasicrystals.

- **Fibonacci sequence**: Each number is the sum of the two before it. The ratio of consecutive terms converges to phi.

- **Phi-scaled frequencies produce irrational beat ratios**: This prevents resonance and creates quasiperiodic (never exactly repeating) patterns.

## Cryptography

- **SHA-256**: Deterministic hash. Same input always produces same 256-bit output. Computationally infeasible to reverse or find collisions.
  - NIST FIPS 180-4.

- **SHA-3 (Keccak)**: Independent hash family from SHA-2. Different internal structure (sponge construction).
  - NIST FIPS 202, 2015.

- **HMAC**: Keyed hash for authentication. HMAC-SHA-256 proves both integrity and authenticity.
  - RFC 2104, RFC 5869.

- **ML-KEM-768 / ML-DSA-65**: Post-quantum key encapsulation and digital signatures based on lattice problems (Learning With Errors).
  - NIST FIPS 203 / 204, 2024.

## Stability

- **Lyapunov stability**: A system is stable if there exists a function V(x) > 0 where dV/dt <= 0 along the system's trajectory.
  - Aleksandr Lyapunov, 1892. The foundation of all stability proofs.

- **Energy minimization**: A system governed by dx/dt = -grad(E(x)) will always decrease in energy. dE/dt = -||grad(E)||^2 <= 0.
  - Gradient flow. Basic calculus of variations.

- **Convex combinations stay in the convex hull**: If weights sum to 1 and are all >= 0, the result is inside the shape defined by the corners. It can't escape.
  - Barycentric coordinates. Affine geometry.

## Physics

- **Surface tension minimizes area**: The energy of a film is proportional to its surface area. The film contracts until it reaches minimum area.
  - Young-Laplace equation.

- **Quasicrystals**: Ordered but never exactly repeating atomic arrangements. Long-range orientational order without translational periodicity.
  - Dan Shechtman, 1982 (Nobel Prize 2011).

- **Liquid crystals**: Mesophase between solid crystal and liquid. Orientational order without full positional order. Director field, Frank elastic energy.
  - Friedrich Reinitzer, 1888. Full theory by Frank, Oseen, Leslie, Ericksen.

## Information Theory

- **Shannon entropy**: H = -sum(p_i * log2(p_i)). Measures information content / uncertainty.
  - Claude Shannon, 1948.

- **Mutual information**: How much knowing X tells you about Y. I(X;Y) = H(X) + H(Y) - H(X,Y).

## Computation

- **Turing machine**: A tape + head + state transitions can compute anything computable. The tape can be infinite.
  - Alan Turing, 1936.

- **Godel's incompleteness**: Any sufficiently powerful formal system contains true statements it cannot prove about itself.
  - Kurt Godel, 1931.

## The Riemann Hypothesis (unproven but established)

- **Riemann zeta function**: zeta(s) = sum(1/n^s) for n = 1 to infinity.
- **The hypothesis**: All non-trivial zeros have real part exactly 1/2.
- **Status**: Unproven. Millennium Prize Problem ($1M).
- **Importance**: Controls the distribution of prime numbers.
- Bernhard Riemann, 1859.

---

*These facts exist whether we use them or not. Our system is built ON them, not FROM them. The difference matters.*
