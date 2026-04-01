# Signed Zero Governance

> The IEEE 754 signed zero (+0 and -0) is not merely a floating-point artifact. In SCBE-AETHERMOORE, it serves as a structural governance primitive -- a 4-state micro-alphabet for control decisions.

## The 4-State Micro-Alphabet

| Symbol | Magnitude | Sign | Meaning | Governance Action |
|--------|-----------|------|---------|-------------------|
| **+1** | Non-zero | Positive | Constructive | Amplify / advance / approve |
| **-1** | Non-zero | Negative | Destructive | Contract / retreat / reject |
| **+0** | Zero | Positive | Neutral-pass | Abstain / continue / no-op |
| **-0** | Zero | Negative | Neutral-hold | Quarantine / pause / inspect-before-commit |

## Why -0 Matters Most

The most meaningful state is **-0**: zero force but negative phase. This encodes "hold" -- the system is not acting, but it is not passive. It is actively waiting, inspecting, or withholding commitment.

In conventional computing, +0 and -0 are treated as equal (`+0 === -0` in most languages). SCBE exploits the distinction that IEEE 754 preserves in the bit representation:

- `+0` = `0x0000000000000000` (sign bit = 0)
- `-0` = `0x8000000000000000` (sign bit = 1)

This single bit difference carries governance meaning:

| State | Interpretation |
|-------|---------------|
| **+0** (neutral-pass) | "I have no opinion, proceed" |
| **-0** (neutral-hold) | "I have no force to apply, but I am not yet ready to release -- hold" |

## System Mappings

### PHDM (The Brain)

- **-0 = "Don't advance the rail"**: In the Hamiltonian path through the 16 polyhedra, a -0 state on any polyhedron means the reasoning cycle pauses at that vertex. The path does not advance to the next polyhedron until the -0 resolves to +0 (continue) or +1 (advance with force). This prevents premature decisions when governance conditions are uncertain.

### HYDRA (The Body)

- **-0 = "Wait for quorum"**: In the swarm consensus protocol, a -0 vote from any agent means "I am not blocking, but I am not approving -- wait for more information." The swarm cannot reach consensus while any agent holds -0; it must either resolve to +0/+1 (allow consensus) or -1 (block consensus). This prevents the swarm from acting on incomplete information.

### Spiralverse (The Narrative Layer)

- **-0 = "Write-gate tension"**: In the Spiralverse story engine, a -0 state on a narrative node means the story cannot advance past that point. The write-gate is under tension -- there is narrative pressure to continue, but a governance constraint (canon violation, unresolved dependency, missing Sacred Egg) holds the gate closed. The tension is itself a meaningful narrative state.

## Formal Structure

### Isomorphism to {0,1} x {0,1}

The 4-state alphabet is isomorphic to two independent bits:

| State | Magnitude Bit | Sign Bit | Binary |
|-------|--------------|----------|--------|
| +1 | 1 | 0 | (1,0) |
| -1 | 1 | 1 | (1,1) |
| +0 | 0 | 0 | (0,0) |
| -0 | 0 | 1 | (0,1) |

This means the 4-state alphabet can be implemented efficiently as a 2-bit register, with the magnitude bit controlling force and the sign bit controlling phase/direction.

### Ternary State Space

Treating {-1, 0, +1} as a balanced ternary digit (trit), a system with n trits has:

```
3^n possible states
```

With the signed-zero extension (distinguishing +0 from -0), each trit becomes a "quad" with 4 states, but the effective information content remains ternary for magnitude decisions and binary for phase decisions.

### Dual Ternary (Mirrors)

When two ternary systems are coupled (e.g., the PHDM rail state and the HYDRA consensus state), the joint space is:

```
3^(2n) possible joint states
```

For a system with n=6 dimensions (matching the 6 Sacred Tongues), this gives 3^12 = 531,441 joint states -- a rich but tractable governance space.

## Spectral Interpretation

### Rectification and Harmonics

In signal processing, rectification (taking the absolute value of a signal) introduces:

1. **A DC component**: The mean shifts from zero to a positive value
2. **Even harmonics**: Frequency components at 2f, 4f, 6f, etc. that were not present in the original signal

When the signed-zero alphabet is applied to a continuous signal:

- **+1/-1 transitions**: Full-wave behavior, odd harmonics dominate
- **+0 intervals**: Signal is truly zero, no harmonic contribution
- **-0 intervals**: Signal is zero in magnitude but the sign bit preserves phase information -- this creates a characteristic spectral anomaly

The -0 intervals act as an **anomaly fingerprint** in the frequency domain. A spectral analyzer can detect the presence of -0 governance holds by looking for the specific harmonic pattern they produce when the signal is reconstructed.

## Hamiltonian Interpretation

In the Hamiltonian path through the PHDM polyhedra:

| State | Path Behavior |
|-------|--------------|
| **+1** | Move forward along the path (advance to next polyhedron) |
| **-1** | Move backward along the path (retreat to previous polyhedron) |
| **+0** | Idle at current polyhedron (no movement, no hold) |
| **-0** | Idle at current polyhedron with hold (no movement, active inspection) |

The distinction between +0 (idle) and -0 (idle + hold) is critical for the Hamiltonian cycle:

- **+0**: The path can be resumed by any external trigger
- **-0**: The path can only be resumed by resolving the hold condition (governance check, quorum reached, dependency satisfied)

This makes -0 a **gate** on the Hamiltonian path -- a point where the cycle cannot continue until an explicit governance condition is met.

## Integration with 21D Continuous State

The SCBE system operates in a 21-dimensional continuous state space (the canonical state lift). The signed-zero micro-alphabet is the **discrete control plane** that rides alongside this continuous manifold.

### Relationship

- **21D continuous state**: Represents the full geometric position of the system in hyperbolic space -- curvature, distance, phase, entropy, temporal coordinates
- **+/- 1/0 discrete state**: Represents the governance control decisions applied to that position -- advance, retreat, pass, hold

The two planes interact:

1. The continuous state determines what governance decisions are *available* (e.g., if the hyperbolic distance exceeds a threshold, +1/advance may not be permitted)
2. The discrete decisions modify how the continuous state *evolves* (e.g., a -0/hold freezes the state evolution at the current point)

This dual-plane architecture ensures that governance is both geometrically grounded (continuous) and computationally tractable (discrete). The 4-state alphabet provides a minimal but complete set of control actions for any governance situation.
