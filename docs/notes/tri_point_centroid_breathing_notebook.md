# Tri-Point Centroid + Breathing Flux (Notebook Notes)

## Breakthrough (captured)
- Use a moving reference center `c(t)` for hyperbolic distance instead of fixed origin `0`.
- `d_H(u,c)` becomes anisotropic because denominator depends on `||c||` and `||u-c||`.
- `c` is defined as a Fréchet-style centroid over trusted neighbors + deterministic oscillation.
- This creates a stronger drift response to small perturbations during centroid swings.

## Core formula

a) Hyperbolic distance to reference:

`d_H(u,c) = arccosh( 1 + 2||u-c||^2 / ((1-||u||^2)(1-||c||^2)) )`

b) Tri-point centroid sketch:

`c(t) = FréchetMean(u1, u2, u3) + Oscillation(t)`

where `u1,u2,u3` are trusted neighbors / nearest trusted points.

## Why this helps
- Removes pure monotonic/euclidean-equivalent behavior from static-origin metric.
- Attackers cannot trivially “aim” for fixed safe shell at `0`.
- Dynamic center (`c`) + oscillation raises local wall cost for out-of-formation trajectories.

## Swarm interpretation
- 6D agents are flight-form geometry states.
- Tri-point centroid is a virtual formation leader.
- GFSS/anisotropy can exclude anomalous agents from centroid updates to avoid pulling safe-zone off-course.

## Constant-time vs time-dilation
- **Constant-time**: cryptographic primitives execute in near fixed timing.
- **Variable time**: governance/response-time can be stretched as a defense action, while detection itself remains constant-time.
- Trusted paths: near-zero wait. Suspicious paths can be delayed (or penalized) without leaking timing in cryptographic checks.

## Implementation status in repo
- Updated `src/agent/swarm.ts`:
  - Added trust-filtered tri-point centroid path.
  - Added small oscillatory breathing offset.
  - Added constructor config via `TriPointCentroidConfig`.

## Next coding step
- Route this centroid into any additional modules currently using raw origin distance.
- Add a “trusted-only neighbor exclusion” hook for high-coherence anomaly detectors.
