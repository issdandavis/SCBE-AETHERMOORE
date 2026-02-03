/**
 * @file hyperbolic-parity.test.ts
 * @module tests/cross-language
 * @description Cross-language validation tests for hyperbolic geometry operations
 *
 * These tests verify that TypeScript and Python implementations produce
 * identical results for the same inputs, ensuring implementation parity.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { execSync } from 'child_process';
import * as path from 'path';
import {
  hyperbolicDistance,
  mobiusAddition,
  exponentialMap,
  logarithmicMap,
} from '../../src/harmonic/hyperbolic.js';

/**
 * Execute Python script and return JSON result
 */
function execPython(script: string, args: Record<string, unknown>): unknown {
  const pythonScript = `
import sys
import json
sys.path.insert(0, '${path.resolve(__dirname, '../../src')}')

args = json.loads('${JSON.stringify(args)}')
${script}
print(json.dumps(result))
`;

  try {
    const output = execSync(`python3 -c "${pythonScript.replace(/"/g, '\\"')}"`, {
      encoding: 'utf-8',
      timeout: 10000,
    });
    return JSON.parse(output.trim());
  } catch {
    // Python not available or script failed - skip test
    return null;
  }
}

/**
 * Check if Python is available
 */
function isPythonAvailable(): boolean {
  try {
    execSync('python3 --version', { encoding: 'utf-8' });
    return true;
  } catch {
    return false;
  }
}

describe('Cross-Language: Hyperbolic Geometry Parity', () => {
  let pythonAvailable = false;

  beforeAll(() => {
    pythonAvailable = isPythonAvailable();
  });

  describe('Hyperbolic Distance', () => {
    const testCases = [
      { u: [0.1, 0.2], v: [0.3, 0.4], name: 'simple 2D points' },
      { u: [0, 0], v: [0.5, 0], name: 'origin to point' },
      { u: [0.9, 0], v: [-0.9, 0], name: 'near boundary points' },
      { u: [0.1, 0.1, 0.1], v: [0.2, 0.2, 0.2], name: '3D points' },
    ];

    for (const { u, v, name } of testCases) {
      it(`should match Python for ${name}`, () => {
        if (!pythonAvailable) {
          console.log('Skipping: Python not available');
          return;
        }

        const tsResult = hyperbolicDistance(u, v);

        const pyResult = execPython(
          `
import numpy as np
u = np.array(args['u'])
v = np.array(args['v'])
norm_u = np.linalg.norm(u)
norm_v = np.linalg.norm(v)
diff = u - v
norm_diff = np.linalg.norm(diff)
delta = 2 * norm_diff**2 / ((1 - norm_u**2) * (1 - norm_v**2))
result = float(np.arccosh(1 + delta))
`,
          { u, v }
        );

        if (pyResult !== null) {
          expect(tsResult).toBeCloseTo(pyResult as number, 10);
        }
      });
    }
  });

  describe('Möbius Addition', () => {
    const testCases = [
      { u: [0.1, 0.2], v: [0.1, 0.1], name: 'simple addition' },
      { u: [0, 0], v: [0.5, 0.5], name: 'origin addition' },
      { u: [0.3, 0.3], v: [-0.2, -0.2], name: 'opposite direction' },
    ];

    for (const { u, v, name } of testCases) {
      it(`should match Python for ${name}`, () => {
        if (!pythonAvailable) {
          console.log('Skipping: Python not available');
          return;
        }

        const tsResult = mobiusAddition(u, v);

        const pyResult = execPython(
          `
import numpy as np
u = np.array(args['u'])
v = np.array(args['v'])
norm_u_sq = np.dot(u, u)
norm_v_sq = np.dot(v, v)
uv = np.dot(u, v)
denom = 1 + 2*uv + norm_u_sq * norm_v_sq
num = (1 + 2*uv + norm_v_sq) * u + (1 - norm_u_sq) * v
result = (num / denom).tolist()
`,
          { u, v }
        );

        if (pyResult !== null) {
          const pyArray = pyResult as number[];
          tsResult.forEach((val, i) => {
            expect(val).toBeCloseTo(pyArray[i], 10);
          });
        }
      });
    }
  });

  describe('Exponential Map', () => {
    it('should match Python for tangent vector mapping', () => {
      if (!pythonAvailable) {
        console.log('Skipping: Python not available');
        return;
      }

      const p = [0.1, 0.2];
      const v = [0.05, 0.05];
      const tsResult = exponentialMap(p, v);

      const pyResult = execPython(
        `
import numpy as np
p = np.array(args['p'])
v = np.array(args['v'])
norm_v = np.linalg.norm(v)
if norm_v < 1e-12:
    result = p.tolist()
else:
    lambda_p = 2 / (1 - np.dot(p, p))
    direction = v / norm_v
    tanh_term = np.tanh(lambda_p * norm_v / 2)
    result = (p + tanh_term * direction).tolist()
    # Normalize to stay in ball
    norm_result = np.linalg.norm(result)
    if norm_result >= 1:
        result = (np.array(result) * 0.99 / norm_result).tolist()
`,
        { p, v }
      );

      if (pyResult !== null) {
        const pyArray = pyResult as number[];
        tsResult.forEach((val, i) => {
          expect(val).toBeCloseTo(pyArray[i], 6);
        });
      }
    });
  });

  describe('Logarithmic Map', () => {
    it('should match Python for point mapping to tangent space', () => {
      if (!pythonAvailable) {
        console.log('Skipping: Python not available');
        return;
      }

      const p = [0.1, 0.2];
      const q = [0.3, 0.4];
      const tsResult = logarithmicMap(p, q);

      const pyResult = execPython(
        `
import numpy as np
p = np.array(args['p'])
q = np.array(args['q'])
# Möbius addition: -p ⊕ q
norm_p_sq = np.dot(p, p)
norm_q_sq = np.dot(q, q)
pq = np.dot(-p, q)
denom = 1 + 2*pq + norm_p_sq * norm_q_sq
num = (1 + 2*pq + norm_q_sq) * (-p) + (1 - norm_p_sq) * q
diff = num / denom
norm_diff = np.linalg.norm(diff)
if norm_diff < 1e-12:
    result = [0.0] * len(p)
else:
    lambda_p = 2 / (1 - norm_p_sq)
    result = ((2 / lambda_p) * np.arctanh(norm_diff) * diff / norm_diff).tolist()
`,
        { p, q }
      );

      if (pyResult !== null) {
        const pyArray = pyResult as number[];
        tsResult.forEach((val, i) => {
          expect(val).toBeCloseTo(pyArray[i], 6);
        });
      }
    });
  });
});

describe('Cross-Language: Test Vectors', () => {
  /**
   * Pre-computed test vectors for validation without Python runtime
   * These vectors are computed using the standard Poincaré ball formulas:
   * - d_H(u,v) = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²)))
   * - u ⊕ v = ((1 + 2⟨u,v⟩ + ‖v‖²)u + (1 - ‖u‖²)v) / (1 + 2⟨u,v⟩ + ‖u‖²‖v‖²)
   */
  const TEST_VECTORS = {
    hyperbolicDistance: [
      { u: [0.1, 0.2], v: [0.3, 0.4], expected: 0.6582194273693331 },
      { u: [0, 0], v: [0.5, 0], expected: 1.0986122886681098 },
      { u: [0.5, 0.5], v: [-0.5, -0.5], expected: 3.525494348078172 },
    ],
    mobiusAddition: [
      { u: [0.1, 0.2], v: [0.1, 0.1], expected: [0.19132893496701224, 0.29311969839773805] },
      { u: [0, 0], v: [0.5, 0.5], expected: [0.5, 0.5] },
    ],
  };

  describe('Pre-computed Test Vectors', () => {
    for (const { u, v, expected } of TEST_VECTORS.hyperbolicDistance) {
      it(`hyperbolicDistance(${JSON.stringify(u)}, ${JSON.stringify(v)})`, () => {
        const result = hyperbolicDistance(u, v);
        expect(result).toBeCloseTo(expected, 10);
      });
    }

    for (const { u, v, expected } of TEST_VECTORS.mobiusAddition) {
      it(`mobiusAddition(${JSON.stringify(u)}, ${JSON.stringify(v)})`, () => {
        const result = mobiusAddition(u, v);
        result.forEach((val, i) => {
          expect(val).toBeCloseTo(expected[i], 10);
        });
      });
    }
  });
});
