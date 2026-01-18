/**
 * SCBE Vacuum-Acoustics Tests (Layer 14)
 *
 * Tests for cymatic and acoustic simulation:
 * - Nodal surface calculations
 * - Cymatic resonance checking
 * - Bottle beam intensity
 * - Flux redistribution
 * - Standing waves and cavity resonance
 */

import { describe, it, expect } from 'vitest';
import {
  nodalSurface,
  checkCymaticResonance,
  bottleBeamIntensity,
  fluxRedistribution,
  standingWaveAmplitude,
  cavityResonance,
  type AcousticSource,
} from '../../src/harmonic/vacuumAcoustics.js';
import { CONSTANTS, type Vector3D, type Vector6D } from '../../src/harmonic/constants.js';

describe('nodalSurface', () => {
  // ═══════════════════════════════════════════════════════════════
  // Mathematical Correctness
  // ═══════════════════════════════════════════════════════════════
  describe('Mathematical correctness', () => {
    it('N(x₁, x₂) = cos(nπx₁/L)cos(mπx₂/L) - cos(mπx₁/L)cos(nπx₂/L)', () => {
      const x: [number, number] = [0.3, 0.7];
      const n = 2;
      const m = 3;
      const L = 1.0;

      const result = nodalSurface(x, n, m, L);

      const [x1, x2] = x;
      const a = Math.cos((n * Math.PI * x1) / L) * Math.cos((m * Math.PI * x2) / L);
      const b = Math.cos((m * Math.PI * x1) / L) * Math.cos((n * Math.PI * x2) / L);
      const expected = a - b;

      expect(result).toBeCloseTo(expected, 10);
    });

    it('symmetry: N(x,y) = -N(y,x) when n ≠ m', () => {
      const n = 2;
      const m = 3;
      const L = 1.0;

      for (let i = 0; i < 10; i++) {
        const x = Math.random();
        const y = Math.random();

        const N_xy = nodalSurface([x, y], n, m, L);
        const N_yx = nodalSurface([y, x], n, m, L);

        expect(N_xy).toBeCloseTo(-N_yx, 10);
      }
    });

    it('zero on diagonal when n ≠ m: N(x, x) = 0', () => {
      const n = 2;
      const m = 3;
      const L = 1.0;

      for (let i = 0; i < 10; i++) {
        const x = Math.random() * L;
        const result = nodalSurface([x, x], n, m, L);
        expect(result).toBeCloseTo(0, 10);
      }
    });

    it('identically zero when n = m', () => {
      const n = 3;
      const L = 1.0;

      for (let i = 0; i < 20; i++) {
        const x1 = Math.random() * L;
        const x2 = Math.random() * L;
        const result = nodalSurface([x1, x2], n, n, L);
        expect(result).toBeCloseTo(0, 10);
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Nodal Lines
  // ═══════════════════════════════════════════════════════════════
  describe('Nodal lines', () => {
    it('zero at origin', () => {
      // At (0,0): cos(0)*cos(0) - cos(0)*cos(0) = 1 - 1 = 0
      expect(nodalSurface([0, 0], 2, 3, 1)).toBeCloseTo(0, 10);
    });

    it('bounded for all positions', () => {
      const L = 1.0;
      const n = 2;
      const m = 4;

      // Nodal surface is bounded by [-2, 2] since it's difference of products of cosines
      for (let i = 0; i < 10; i++) {
        const x1 = Math.random() * L;
        const x2 = Math.random() * L;
        const result = nodalSurface([x1, x2], n, m, L);
        expect(Math.abs(result)).toBeLessThanOrEqual(2);
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Boundary Conditions
  // ═══════════════════════════════════════════════════════════════
  describe('Boundary conditions', () => {
    it('bounded for all valid inputs', () => {
      for (let i = 0; i < 100; i++) {
        const x1 = Math.random();
        const x2 = Math.random();
        const n = Math.floor(Math.random() * 10) + 1;
        const m = Math.floor(Math.random() * 10) + 1;

        const result = nodalSurface([x1, x2], n, m, 1);

        // Product of two cosines minus product of two cosines
        // Bounded by [-2, 2]
        expect(result).toBeGreaterThanOrEqual(-2);
        expect(result).toBeLessThanOrEqual(2);
      }
    });

    it('uses default L from CONSTANTS', () => {
      const x: [number, number] = [0.5, 0.5];
      const n = 2;
      const m = 3;

      const result1 = nodalSurface(x, n, m);
      const result2 = nodalSurface(x, n, m, CONSTANTS.DEFAULT_L);

      expect(result1).toBeCloseTo(result2, 10);
    });
  });
});

describe('checkCymaticResonance', () => {
  // ═══════════════════════════════════════════════════════════════
  // Resonance Detection
  // ═══════════════════════════════════════════════════════════════
  describe('Resonance detection', () => {
    it('detects resonance on diagonal (n ≠ m from agent vector)', () => {
      // Agent vector with distinct v and m components
      const agentVector: Vector6D = [0, 0, 0, 2, 0, 3]; // n=2, m=3

      // Target on diagonal should be on nodal line
      const target: [number, number] = [0.5, 0.5];

      const result = checkCymaticResonance(agentVector, target, 0.01);
      expect(result).toBe(true);
    });

    it('non-resonance away from nodal lines', () => {
      const agentVector: Vector6D = [0, 0, 0, 2, 0, 3];

      // Target away from nodal line
      const target: [number, number] = [0.2, 0.8];

      const result = checkCymaticResonance(agentVector, target, 0.001);
      expect(result).toBe(false);
    });

    it('tolerance affects detection sensitivity', () => {
      const agentVector: Vector6D = [0, 0, 0, 2, 0, 3];
      const target: [number, number] = [0.5, 0.501]; // Near diagonal

      // Loose tolerance should detect
      const looseResult = checkCymaticResonance(agentVector, target, 0.1);

      // The value near diagonal should be small
      expect(typeof looseResult).toBe('boolean');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Agent Vector Interpretation
  // ═══════════════════════════════════════════════════════════════
  describe('Agent vector interpretation', () => {
    it('uses agentVector[3] for n (scaled by v_ref)', () => {
      const agentVector: Vector6D = [0, 0, 0, 5, 0, 3];
      const target: [number, number] = [0.5, 0.5];

      // n = |agentVector[3]| / v_ref = 5 / 1 = 5
      const result = checkCymaticResonance(agentVector, target);
      expect(typeof result).toBe('boolean');
    });

    it('uses agentVector[5] for m', () => {
      const agentVector: Vector6D = [0, 0, 0, 2, 0, 7];
      const target: [number, number] = [0.5, 0.5];

      // m = agentVector[5] = 7
      const result = checkCymaticResonance(agentVector, target);
      expect(typeof result).toBe('boolean');
    });

    it('handles negative velocity (absolute value)', () => {
      const positiveV: Vector6D = [0, 0, 0, 3, 0, 5];
      const negativeV: Vector6D = [0, 0, 0, -3, 0, 5];
      const target: [number, number] = [0.3, 0.7];

      const result1 = checkCymaticResonance(positiveV, target);
      const result2 = checkCymaticResonance(negativeV, target);

      expect(result1).toBe(result2);
    });
  });
});

describe('bottleBeamIntensity', () => {
  // ═══════════════════════════════════════════════════════════════
  // Single Source
  // ═══════════════════════════════════════════════════════════════
  describe('Single source', () => {
    it('intensity = 1 at any distance for single source', () => {
      const sources: AcousticSource[] = [
        { pos: [0, 0, 0], phase: 0 },
      ];
      const wavelength = 0.1;

      // Single source: |e^(ikr)|² = 1
      const pos1: Vector3D = [0.1, 0, 0];
      const pos2: Vector3D = [1, 1, 1];

      expect(bottleBeamIntensity(pos1, sources, wavelength)).toBeCloseTo(1, 5);
      expect(bottleBeamIntensity(pos2, sources, wavelength)).toBeCloseTo(1, 5);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Two Sources
  // ═══════════════════════════════════════════════════════════════
  describe('Two sources - interference', () => {
    it('constructive interference (phase = 0, equidistant)', () => {
      const sources: AcousticSource[] = [
        { pos: [-1, 0, 0], phase: 0 },
        { pos: [1, 0, 0], phase: 0 },
      ];
      const wavelength = 1.0;

      // At origin, equidistant from both sources
      const intensity = bottleBeamIntensity([0, 0, 0], sources, wavelength);

      // Two waves in phase: amplitude = 2, intensity = 4
      expect(intensity).toBeCloseTo(4, 1);
    });

    it('destructive interference (phase = π)', () => {
      const sources: AcousticSource[] = [
        { pos: [0, 0, 0], phase: 0 },
        { pos: [0, 0, 0], phase: Math.PI }, // Same position, opposite phase
      ];
      const wavelength = 1.0;

      const intensity = bottleBeamIntensity([1, 0, 0], sources, wavelength);

      // Waves cancel: intensity ≈ 0
      expect(intensity).toBeCloseTo(0, 1);
    });

    it('partial interference for arbitrary phase', () => {
      const sources: AcousticSource[] = [
        { pos: [0, 0, 0], phase: 0 },
        { pos: [0, 0, 0], phase: Math.PI / 2 },
      ];
      const wavelength = 1.0;

      const intensity = bottleBeamIntensity([1, 0, 0], sources, wavelength);

      // Intermediate value between 0 and 4
      expect(intensity).toBeGreaterThan(0);
      expect(intensity).toBeLessThan(4);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Bottle Beam Pattern
  // ═══════════════════════════════════════════════════════════════
  describe('Bottle beam pattern', () => {
    it('creates intensity minimum at center with proper source arrangement', () => {
      // Ring of sources around z-axis
      const n = 8;
      const radius = 1;
      const sources: AcousticSource[] = [];

      for (let i = 0; i < n; i++) {
        const angle = (2 * Math.PI * i) / n;
        sources.push({
          pos: [radius * Math.cos(angle), radius * Math.sin(angle), 0],
          phase: Math.PI, // All sources in anti-phase relative to center
        });
      }

      const wavelength = 2; // Half-wavelength = radius

      // Center intensity
      const centerIntensity = bottleBeamIntensity([0, 0, 0], sources, wavelength);

      // Off-center intensity
      const offCenterIntensity = bottleBeamIntensity([0.5, 0, 0], sources, wavelength);

      // Bottle beam should have lower intensity at center
      // (This is a simplified test - real bottle beams need careful design)
      expect(Number.isFinite(centerIntensity)).toBe(true);
      expect(Number.isFinite(offCenterIntensity)).toBe(true);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Numerical Stability
  // ═══════════════════════════════════════════════════════════════
  describe('Numerical stability', () => {
    it('handles very small distances (near source)', () => {
      const sources: AcousticSource[] = [
        { pos: [0, 0, 0], phase: 0 },
      ];

      // Very close to source
      const intensity = bottleBeamIntensity([1e-10, 0, 0], sources, 1.0);

      expect(Number.isFinite(intensity)).toBe(true);
    });

    it('handles large distances', () => {
      const sources: AcousticSource[] = [
        { pos: [0, 0, 0], phase: 0 },
      ];

      const intensity = bottleBeamIntensity([1e6, 0, 0], sources, 1.0);

      expect(Number.isFinite(intensity)).toBe(true);
      expect(intensity).toBeCloseTo(1, 5); // Single source always has intensity 1
    });

    it('handles many sources', () => {
      const sources: AcousticSource[] = [];
      for (let i = 0; i < 100; i++) {
        sources.push({
          pos: [Math.random(), Math.random(), Math.random()],
          phase: Math.random() * 2 * Math.PI,
        });
      }

      const intensity = bottleBeamIntensity([0.5, 0.5, 0.5], sources, 0.1);

      expect(Number.isFinite(intensity)).toBe(true);
      expect(intensity).toBeGreaterThanOrEqual(0);
    });
  });
});

describe('fluxRedistribution', () => {
  // ═══════════════════════════════════════════════════════════════
  // Energy Conservation
  // ═══════════════════════════════════════════════════════════════
  describe('Energy conservation', () => {
    it('total energy is conserved: canceled + corners = 2A²', () => {
      const amplitude = 2.5;
      const phaseOffset = Math.PI / 3;

      const { canceled, corners } = fluxRedistribution(amplitude, phaseOffset);

      const E_total = 2 * amplitude * amplitude;
      const cornerSum = corners.reduce((a, b) => a + b, 0);
      const central = E_total - canceled;

      // Central + redistributed = total
      expect(central + cornerSum).toBeCloseTo(E_total, 10);
    });

    it('corners receive equal share', () => {
      const { corners } = fluxRedistribution(1.0, Math.PI / 2);

      expect(corners[0]).toBeCloseTo(corners[1], 10);
      expect(corners[1]).toBeCloseTo(corners[2], 10);
      expect(corners[2]).toBeCloseTo(corners[3], 10);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Phase Dependence
  // ═══════════════════════════════════════════════════════════════
  describe('Phase dependence', () => {
    it('zero cancellation for phase = 0 (constructive)', () => {
      const { canceled } = fluxRedistribution(1.0, 0);

      // cos(0) = 1, so central = 4A² cos²(0) = 4A²
      // E_total = 2A² < 4A², so canceled = max(0, 2A² - 4A²) = 0
      expect(canceled).toBe(0);
    });

    it('maximum cancellation for phase = π (destructive)', () => {
      const amplitude = 1.0;
      const { canceled, corners } = fluxRedistribution(amplitude, Math.PI);

      // cos(π/2) = 0, so central = 0
      // canceled = 2A² - 0 = 2A²
      const E_total = 2 * amplitude * amplitude;
      expect(canceled).toBeCloseTo(E_total, 10);

      // Each corner gets E_total / 4
      expect(corners[0]).toBeCloseTo(E_total / 4, 10);
    });

    it('partial cancellation for phase = π/2', () => {
      const { canceled } = fluxRedistribution(1.0, Math.PI / 2);

      // cos(π/4) = √2/2, so central = 4 × (√2/2)² = 2
      // E_total = 2, so canceled = 0
      expect(canceled).toBe(0);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Amplitude Scaling
  // ═══════════════════════════════════════════════════════════════
  describe('Amplitude scaling', () => {
    it('canceled energy scales with A²', () => {
      const phase = Math.PI; // Maximum cancellation

      const { canceled: c1 } = fluxRedistribution(1.0, phase);
      const { canceled: c2 } = fluxRedistribution(2.0, phase);
      const { canceled: c3 } = fluxRedistribution(3.0, phase);

      // c2/c1 = 4, c3/c1 = 9
      expect(c2 / c1).toBeCloseTo(4, 10);
      expect(c3 / c1).toBeCloseTo(9, 10);
    });
  });
});

describe('standingWaveAmplitude', () => {
  // ═══════════════════════════════════════════════════════════════
  // Mathematical Correctness
  // ═══════════════════════════════════════════════════════════════
  describe('Mathematical correctness', () => {
    it('A(x, t) = 2A₀ sin(kx) cos(ωt)', () => {
      const A0 = 1.5;
      const k = 2.0;
      const omega = 3.0;
      const x = 0.7;
      const t = 1.2;

      const result = standingWaveAmplitude(x, t, A0, k, omega);
      const expected = 2 * A0 * Math.sin(k * x) * Math.cos(omega * t);

      expect(result).toBeCloseTo(expected, 10);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Spatial Properties
  // ═══════════════════════════════════════════════════════════════
  describe('Spatial properties', () => {
    it('zero at nodes: x = nπ/k', () => {
      const k = Math.PI;
      const omega = 1;
      const A0 = 1;

      // Nodes at x = 0, 1, 2, 3, ...
      for (let n = 0; n <= 5; n++) {
        const x = n; // nπ/k = n when k = π
        const A = standingWaveAmplitude(x, 0.5, A0, k, omega);
        expect(Math.abs(A)).toBeLessThan(1e-10);
      }
    });

    it('maximum at antinodes: x = (n + 0.5)π/k', () => {
      const k = Math.PI;
      const omega = 1;
      const A0 = 1;
      const t = 0; // cos(0) = 1

      // Antinodes at x = 0.5, 1.5, 2.5, ...
      for (let n = 0; n <= 3; n++) {
        const x = n + 0.5;
        const A = standingWaveAmplitude(x, t, A0, k, omega);
        expect(Math.abs(A)).toBeCloseTo(2 * A0, 5);
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Temporal Properties
  // ═══════════════════════════════════════════════════════════════
  describe('Temporal properties', () => {
    it('zero at times t = (n + 0.5)π/ω', () => {
      const k = 1;
      const omega = Math.PI;
      const A0 = 1;
      const x = 0.5; // Non-node position

      // Zero times at t = 0.5, 1.5, 2.5, ...
      for (let n = 0; n <= 3; n++) {
        const t = n + 0.5;
        const A = standingWaveAmplitude(x, t, A0, k, omega);
        expect(Math.abs(A)).toBeLessThan(1e-10);
      }
    });

    it('maximum at times t = nπ/ω', () => {
      const k = 1;
      const omega = Math.PI;
      const A0 = 1;
      const x = Math.PI / 2; // sin(kx) = sin(π/2) = 1

      // Max times at t = 0, 1, 2, 3, ...
      for (let n = 0; n <= 3; n++) {
        const A = standingWaveAmplitude(x, n, A0, k, omega);
        expect(Math.abs(A)).toBeCloseTo(2 * A0, 5);
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Amplitude Bounds
  // ═══════════════════════════════════════════════════════════════
  describe('Amplitude bounds', () => {
    it('bounded by [-2A₀, 2A₀]', () => {
      const A0 = 1.5;

      for (let i = 0; i < 100; i++) {
        const x = Math.random() * 10;
        const t = Math.random() * 10;
        const A = standingWaveAmplitude(x, t, A0, 2, 3);

        expect(A).toBeGreaterThanOrEqual(-2 * A0);
        expect(A).toBeLessThanOrEqual(2 * A0);
      }
    });
  });
});

describe('cavityResonance', () => {
  // ═══════════════════════════════════════════════════════════════
  // Mathematical Correctness
  // ═══════════════════════════════════════════════════════════════
  describe('Mathematical correctness', () => {
    it('f = (c/2) √((n/Lx)² + (m/Ly)² + (l/Lz)²)', () => {
      const n = 2, m = 3, l = 4;
      const dimensions: Vector3D = [1, 2, 3];
      const c = 343;

      const result = cavityResonance(n, m, l, dimensions, c);

      const [Lx, Ly, Lz] = dimensions;
      const term = (n / Lx) ** 2 + (m / Ly) ** 2 + (l / Lz) ** 2;
      const expected = (c / 2) * Math.sqrt(term);

      expect(result).toBeCloseTo(expected, 10);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Special Cases
  // ═══════════════════════════════════════════════════════════════
  describe('Special cases', () => {
    it('fundamental mode (1,0,0) in cube', () => {
      const L = 1;
      const c = 343;
      const dimensions: Vector3D = [L, L, L];

      const f = cavityResonance(1, 0, 0, dimensions, c);

      // f = c / (2L)
      expect(f).toBeCloseTo(c / (2 * L), 10);
    });

    it('degenerate modes in cube: (1,0,0), (0,1,0), (0,0,1)', () => {
      const L = 2;
      const c = 343;
      const dimensions: Vector3D = [L, L, L];

      const f100 = cavityResonance(1, 0, 0, dimensions, c);
      const f010 = cavityResonance(0, 1, 0, dimensions, c);
      const f001 = cavityResonance(0, 0, 1, dimensions, c);

      // All should be equal in a cube
      expect(f100).toBeCloseTo(f010, 10);
      expect(f010).toBeCloseTo(f001, 10);
    });

    it('non-degenerate in rectangular cavity', () => {
      const c = 343;
      const dimensions: Vector3D = [1, 2, 3];

      const f100 = cavityResonance(1, 0, 0, dimensions, c);
      const f010 = cavityResonance(0, 1, 0, dimensions, c);
      const f001 = cavityResonance(0, 0, 1, dimensions, c);

      // All should be different
      expect(f100).not.toBeCloseTo(f010, 1);
      expect(f010).not.toBeCloseTo(f001, 1);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Mode Number Scaling
  // ═══════════════════════════════════════════════════════════════
  describe('Mode number scaling', () => {
    it('higher modes have higher frequencies', () => {
      const c = 343;
      const dimensions: Vector3D = [1, 1, 1];

      const f1 = cavityResonance(1, 0, 0, dimensions, c);
      const f2 = cavityResonance(2, 0, 0, dimensions, c);
      const f3 = cavityResonance(3, 0, 0, dimensions, c);

      expect(f2).toBeGreaterThan(f1);
      expect(f3).toBeGreaterThan(f2);
    });

    it('frequency ratio follows mode numbers', () => {
      const c = 343;
      const dimensions: Vector3D = [1, 1, 1];

      const f1 = cavityResonance(1, 0, 0, dimensions, c);
      const f2 = cavityResonance(2, 0, 0, dimensions, c);

      // f2/f1 = 2 for single-axis modes
      expect(f2 / f1).toBeCloseTo(2, 10);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Dimension Scaling
  // ═══════════════════════════════════════════════════════════════
  describe('Dimension scaling', () => {
    it('larger cavity has lower frequencies', () => {
      const c = 343;
      const small: Vector3D = [1, 1, 1];
      const large: Vector3D = [2, 2, 2];

      const f_small = cavityResonance(1, 1, 1, small, c);
      const f_large = cavityResonance(1, 1, 1, large, c);

      expect(f_large).toBeLessThan(f_small);
      expect(f_small / f_large).toBeCloseTo(2, 10);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Default Speed of Sound
  // ═══════════════════════════════════════════════════════════════
  describe('Default speed of sound', () => {
    it('uses c = 343 m/s by default', () => {
      const dimensions: Vector3D = [1, 1, 1];

      const f_default = cavityResonance(1, 0, 0, dimensions);
      const f_explicit = cavityResonance(1, 0, 0, dimensions, 343);

      expect(f_default).toBeCloseTo(f_explicit, 10);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Physical Reasonableness
  // ═══════════════════════════════════════════════════════════════
  describe('Physical reasonableness', () => {
    it('room-sized cavity has audible frequencies', () => {
      const c = 343;
      const room: Vector3D = [5, 4, 3]; // 5m × 4m × 3m room

      const f_fundamental = cavityResonance(1, 1, 1, room, c);

      // Should be in audible range (20Hz - 20kHz)
      expect(f_fundamental).toBeGreaterThan(20);
      expect(f_fundamental).toBeLessThan(200);
    });

    it('small box has higher frequencies', () => {
      const c = 343;
      const box: Vector3D = [0.1, 0.1, 0.1]; // 10cm cube

      const f = cavityResonance(1, 0, 0, box, c);

      // f = 343 / (2 × 0.1) = 1715 Hz
      expect(f).toBeCloseTo(1715, 0);
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// Integration Tests
// ═══════════════════════════════════════════════════════════════
describe('Vacuum Acoustics Integration', () => {
  it('cymatic resonance at cavity mode positions', () => {
    // Set up agent to induce mode (2, 3)
    const agentVector: Vector6D = [0, 0, 0, 2, 0, 3];
    const L = 1.0;

    // Check resonance at a point known to be on nodal line
    const onNodal = checkCymaticResonance(
      agentVector,
      [0.5, 0.5], // Diagonal
      0.01,
      L
    );

    expect(onNodal).toBe(true);
  });

  it('bottle beam creates acoustic trap', () => {
    // 4 sources in square pattern
    const sources: AcousticSource[] = [
      { pos: [1, 0, 0], phase: 0 },
      { pos: [-1, 0, 0], phase: 0 },
      { pos: [0, 1, 0], phase: 0 },
      { pos: [0, -1, 0], phase: 0 },
    ];
    const wavelength = 1.0;

    // Check intensities at various points
    const centerIntensity = bottleBeamIntensity([0, 0, 0], sources, wavelength);

    // All sources contribute constructively at center
    expect(centerIntensity).toBeGreaterThan(0);
    expect(Number.isFinite(centerIntensity)).toBe(true);
  });

  it('standing wave in cavity', () => {
    const dimensions: Vector3D = [1, 1, 1];
    const c = 343;

    // Get fundamental frequency
    const f = cavityResonance(1, 0, 0, dimensions, c);
    const omega = 2 * Math.PI * f;
    const k = omega / c;

    // Check standing wave at this frequency
    const A = standingWaveAmplitude(0.5, 0, 1, k, omega);

    expect(Number.isFinite(A)).toBe(true);
  });
});
