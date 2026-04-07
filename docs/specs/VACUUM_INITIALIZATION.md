# Vacuum Initialization

Status: research spec
Date: 2026-03-31
Scope: initializing nodal networks at the cymatic ground state for anomaly detection

## Core Concept

In quantum field theory, the vacuum is not empty -- it is the lowest energy state
with zero-point fluctuations. All particles are excitations above this ground state.

Apply this to the SCBE nodal network:

1. Initialize all nodes at the cymatic vacuum: nodal lines where N(x1,x2) = 0
2. The vacuum IS the baseline. No activity = ground state.
3. Any agent activity is a perturbation above vacuum.
4. Drift detection becomes: deviation from vacuum.
5. Governance becomes: which perturbations are authorized excitations?

## Mathematical Foundation

### Cymatic Nodal Surface (already implemented in vacuumAcoustics.ts)

```
N(x1, x2) = cos(n*pi*x1/L) * cos(m*pi*x2/L) - cos(m*pi*x1/L) * cos(n*pi*x2/L)
```

The zeros of N define standing wave cancellation patterns -- places where
destructive interference creates silence. These are topological invariants
(they don't change under continuous deformation).

### Vacuum State

Define the vacuum state V as the configuration where all nodes sit on
nodal lines:

```
V = { x : N(x; n, m) = 0 for all active modes (n, m) }
```

This is the ground state. Zero energy. Zero perturbation.

### Perturbation as Activity

When an agent acts, it perturbs the state away from vacuum:

```
S(t) = V + delta(t)
```

where delta(t) is the perturbation vector.

### Drift = ||delta(t)||

Drift detection is trivially well-defined:

```
drift = ||S(t) - V|| = ||delta(t)||
```

No need to compute complex trajectory metrics. Just measure
deviation from the known ground state.

### Authorized vs Unauthorized Excitations

The governance question: is delta(t) an authorized excitation?

Authorized: delta lies within the trust tube (Hamiltonian braid)
Unauthorized: delta lies outside the trust tube

The trust tube radius is set by the harmonic wall:
```
H(||delta||) = 1 / (1 + phi * ||delta|| + 2 * pd)
```

Small perturbations (legitimate work) → H close to 1 → ALLOW
Large perturbations (adversarial) → H close to 0 → DENY

## Connection to Pump Architecture

The pump aquifer IS the vacuum state. It contains the baseline
tongue profiles and null patterns for "normal" operation. When a
query arrives, the pump computes how far the query's profile is
from the aquifer baseline -- that's the perturbation magnitude.

```
Vacuum state = aquifer centroids (1000 bundles)
Perturbation = ||query_profile - nearest_centroid||
Governance = H(perturbation)
```

## Connection to Null Space

The null pattern IS the vacuum's mode structure. At vacuum:
- All tongues are at baseline activation
- No tongue is abnormally active or suppressed
- The null pattern reflects the natural distribution

A query that activates only 1 tongue (narrow profile) is a
high-energy perturbation above vacuum -- like a laser pulse
in a quiet room. The null-space detection catches it because
the vacuum state has a broad, even profile.

## Connection to Sacred Eggs

The Sacred Egg genesis protocol IS vacuum initialization:
- Before hatching: egg is at ground state (sealed)
- Hatching conditions: geometric + linguistic + temporal alignment
- After hatching: the system enters its first excited state

The genesis rows (6 identity records) define the vacuum state
for Polly -- the baseline from which all subsequent activity
is measured as perturbation.

## Implementation Status

- vacuumAcoustics.ts: EXISTS (nodal surface computation)
- Pump aquifer: EXISTS (1000 baseline bundles = vacuum state proxy)
- Null pattern: EXISTS (absence profile = mode structure)
- Sacred Egg genesis: EXISTS (6 identity rows = initial vacuum)
- Formal vacuum initialization protocol: NOT YET IMPLEMENTED

## Next Steps

1. Define vacuum state formally as Frechet mean of aquifer bundle profiles
2. Compute perturbation magnitude for each pump cycle
3. Add perturbation score to PumpPacket (how far from vacuum)
4. Test: do vacuum-relative perturbation scores correlate with
   adversarial detection better than absolute tongue profiles?
5. If yes: vacuum initialization becomes the canonical startup protocol

## The Deeper Insight

The vacuum is not absence. The vacuum is the lowest-energy configuration
of the full system. It has structure (nodal lines), symmetry (mode numbers),
and energy (zero-point fluctuations). Building from vacuum means every
subsequent state has a well-defined relationship to the ground truth.

This is why "training from bytes first" (L0 substrate) works the same way --
you establish the ground state before adding excitations (words, meaning, expression).

Vacuum initialization = L0.
Perturbation measurement = L2 (pump orientation).
Expression from oriented state = L3.

The whole stack is vacuum → perturbation → governance → expression.
