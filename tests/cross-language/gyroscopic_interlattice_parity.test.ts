/**
 * @file gyroscopic_interlattice_parity.test.ts
 * @layer Layer 5, Layer 6, Layer 7
 * @component Cross-Language Parity: TypeScript ↔ Python
 *
 * Verifies that the TS and Python implementations of gyroscopic interlattice
 * coupling produce identical numerical results.
 */

import { describe, it, expect } from 'vitest';
import { execSync } from 'child_process';
import { writeFileSync, unlinkSync } from 'fs';
import { join } from 'path';
import {
  TONGUE_LABELS,
  TONGUE_RADII,
  couplingStrength,
  phaseFactor,
  allCouplings,
} from '../../packages/kernel/src/gyroscopicInterlattice.js';

const CWD = 'C:/Users/issda/SCBE-AETHERMOORE';
const TMP_SCRIPT = join(CWD, '_tmp_parity_test.py');

/**
 * Run a Python expression and return its output via temp file (avoids shell quoting issues).
 */
function pyEval(expr: string): string {
  const script = `import sys\nsys.path.insert(0, "src")\nfrom symphonic_cipher.scbe_aethermoore.axiom_grouped.gyroscopic_interlattice import *\nprint(${expr})`;
  writeFileSync(TMP_SCRIPT, script, 'utf-8');
  try {
    return execSync(`python ${TMP_SCRIPT}`, { cwd: CWD, encoding: 'utf-8' }).trim();
  } finally {
    try { unlinkSync(TMP_SCRIPT); } catch { /* ignore */ }
  }
}

describe('Gyroscopic Interlattice Cross-Language Parity', () => {
  it('tongue radii match between TS and Python', () => {
    for (const tongue of TONGUE_LABELS) {
      const pyRadius = parseFloat(pyEval(`TONGUE_RADII['${tongue}']`));
      expect(TONGUE_RADII[tongue]).toBeCloseTo(pyRadius, 8);
    }
  });

  it('coupling strengths match for all 15 pairs', () => {
    const couples = allCouplings();
    for (const c of couples) {
      const tsJ = couplingStrength(c.tongueA, c.tongueB);
      const pyJ = parseFloat(
        pyEval(`coupling_strength('${c.tongueA}', '${c.tongueB}')`)
      );
      // Allow small floating point differences
      if (tsJ > 1e-6) {
        expect(tsJ).toBeCloseTo(pyJ, 6);
      } else {
        // For very small values, check relative error
        expect(Math.abs(tsJ - pyJ) / Math.max(tsJ, pyJ, 1e-15)).toBeLessThan(1e-6);
      }
    }
  });

  it('phase factors match for adjacent tongue pairs', () => {
    const pairs: [string, string][] = [
      ['KO', 'AV'],
      ['AV', 'RU'],
      ['RU', 'CA'],
      ['CA', 'UM'],
      ['UM', 'DR'],
    ];
    for (const [a, b] of pairs) {
      const tsPF = phaseFactor(a as any, b as any);
      const pyPF = pyEval(`phase_factor('${a}', '${b}')`);
      // Python returns a tuple like (0.5, 0.866)
      const [pyReal, pyImag] = pyPF
        .replace('(', '')
        .replace(')', '')
        .split(',')
        .map((s: string) => parseFloat(s.trim()));
      expect(tsPF.real).toBeCloseTo(pyReal, 8);
      expect(tsPF.imag).toBeCloseTo(pyImag, 8);
    }
  });

  it('total coupling count matches (15 pairs)', () => {
    const tsCount = allCouplings().length;
    const pyCount = parseInt(pyEval(`len(all_couplings())`));
    expect(tsCount).toBe(pyCount);
    expect(tsCount).toBe(15);
  });
});
