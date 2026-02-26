/**
 * @file cli.unit.test.ts
 * @module tests/L2-unit/cli
 * @layer Layer 14
 * @component CLI integration tests
 * @version 1.0.0
 *
 * Tests the unified `scbe` CLI and `six-tongues-cli.py` via subprocess.
 */

import { describe, it, expect } from 'vitest';
import { execSync } from 'child_process';

function resolvePython(): string | null {
  const envPython = process.env.PYTHON_BIN?.trim();
  const candidates = [
    envPython,
    process.platform === 'win32' ? 'python' : 'python3',
    'python3',
    'python',
  ].filter((v): v is string => Boolean(v && v.length > 0));

  for (const candidate of candidates) {
    try {
      execSync(`${candidate} --version`, {
        cwd: process.cwd(),
        encoding: 'utf-8',
        stdio: 'pipe',
        timeout: 5000,
      });
      return candidate;
    } catch {
      // keep scanning candidates
    }
  }
  return null;
}

const PYTHON = resolvePython();

function run(cmd: string): string {
  return execSync(cmd, {
    cwd: process.cwd(),
    encoding: 'utf-8',
    timeout: 15000,
  }).trim();
}

const maybeDescribe = PYTHON ? describe : describe.skip;

maybeDescribe('Unified scbe CLI', () => {
  describe('selftest', () => {
    it('passes all checks', () => {
      const out = run(`${PYTHON!} scbe selftest`);
      expect(out).toContain('selftest OK');
    });
  });

  describe('tongues encode', () => {
    it('encodes text to KO tokens', () => {
      const out = run(`${PYTHON!} scbe tongues encode --tongue ko --text "hello"`);
      // h=0x68=6*16+8 → prefix[6]=nav, suffix[8]=or → nav'or
      expect(out).toContain("nav'or");
    });

    it('accepts lowercase tongue codes', () => {
      const out = run(`${PYTHON!} scbe tongues encode --tongue av --text "a"`);
      // 'a'=0x61=6*16+1 → prefix[6]=nurel, suffix[1]=e → nurel'e
      expect(out).toBe("nurel'e");
    });

    it('accepts uppercase tongue codes', () => {
      const out = run(`${PYTHON!} scbe tongues encode --tongue RU --text "a"`);
      expect(out).toBeTruthy();
    });
  });

  describe('tongues decode', () => {
    it('decodes tokens back to text', () => {
      const out = run(
        `${PYTHON!} scbe tongues decode --tongue ko --as-text --text "nav'or nav'uu nav'un nav'un nav'esh"`
      );
      expect(out).toBe('hello');
    });
  });

  describe('tongues roundtrip', () => {
    for (const tongue of ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']) {
      it(`${tongue}: encode then decode recovers original`, () => {
        const encoded = run(
          `${PYTHON!} scbe tongues encode --tongue ${tongue} --text "roundtrip test 123"`
        );
        const decoded = run(
          `${PYTHON!} scbe tongues decode --tongue ${tongue} --as-text --text "${encoded}"`
        );
        expect(decoded).toBe('roundtrip test 123');
      });
    }
  });

  describe('tongues list', () => {
    it('shows all 6 tongues', () => {
      const out = run(`${PYTHON!} scbe tongues list`);
      expect(out).toContain("KO");
      expect(out).toContain("AV");
      expect(out).toContain("RU");
      expect(out).toContain("CA");
      expect(out).toContain("UM");
      expect(out).toContain("DR");
      expect(out).toContain("Kor'aelin");
      expect(out).toContain("Draumric");
    });
  });

  describe('pipeline run', () => {
    it('returns a valid decision', () => {
      const out = run(`${PYTHON!} scbe pipeline run --text "test input"`);
      expect(out).toMatch(/Decision:\s+(ALLOW|QUARANTINE|ESCALATE|DENY)/);
    });

    it('returns JSON when --json flag is set', () => {
      const out = run(`${PYTHON!} scbe pipeline run --json --text "test"`);
      const parsed = JSON.parse(out);
      expect(parsed).toHaveProperty('H_eff');
      expect(parsed).toHaveProperty('decision');
      expect(parsed).toHaveProperty('d_star');
    });
  });

  describe('ai explain', () => {
    it('explains a layer by number', () => {
      const out = run(`${PYTHON!} scbe ai explain L12`);
      expect(out).toContain('Harmonic Wall');
    });

    it('finds layers by concept name', () => {
      const out = run(`${PYTHON!} scbe ai explain breathing`);
      expect(out).toContain('L6');
    });
  });

  describe('ai lint', () => {
    it('lints a Python file', () => {
      const out = run(`${PYTHON!} scbe ai lint src/crypto/h_lwe.py`);
      expect(out).toContain('Compiles: OK');
    });

    it('lints a TypeScript file', () => {
      const out = run(`${PYTHON!} scbe ai lint src/harmonic/mmx.ts`);
      expect(out).toContain('Header: yes');
    });

    it('reports error for missing file', () => {
      try {
        run(`${PYTHON!} scbe ai lint nonexistent_file.py`);
        // If it didn't throw, the output should contain Error
        expect(true).toBe(false); // should not reach
      } catch (e: any) {
        // execSync throws on non-zero exit — check stderr/stdout
        expect(e.stdout?.toString() || e.stderr?.toString() || '').toContain('Error');
      }
    });
  });

  describe('ai review', () => {
    it('reviews a file with metrics', () => {
      const out = run(`${PYTHON!} scbe ai review src/crypto/h_lwe.py`);
      expect(out).toContain('code');
      expect(out).toContain('Functions');
      expect(out).toContain('Classes');
    });
  });

  describe('ai check', () => {
    it('runs combined lint+review', () => {
      const out = run(`${PYTHON!} scbe ai check src/crypto/h_lwe.py`);
      expect(out).toContain('===');
      expect(out).toContain('code');
    });
  });

  describe('status', () => {
    it('shows project stats', () => {
      const out = run(`${PYTHON!} scbe status`);
      expect(out).toContain('SCBE-AETHERMOORE');
      expect(out).toContain('TypeScript');
      expect(out).toContain('Python');
      expect(out).toContain('14-Layer Pipeline');
    });
  });
});

maybeDescribe('Cross-CLI parity', () => {
  it('scbe and scbe-cli.py produce identical KO tokens', () => {
    const scbeOut = run(`${PYTHON!} scbe tongues encode --tongue ko --text "parity"`);
    const cliOut = run(`${PYTHON!} scbe-cli.py encode --tongue ko --text "parity"`);
    expect(scbeOut).toBe(cliOut);
  });

  it('scbe and six-tongues-cli.py produce identical KO tokens', () => {
    const scbeOut = run(`${PYTHON!} scbe tongues encode --tongue ko --text "parity"`);
    const sixOut = run(`${PYTHON!} six-tongues-cli.py encode --tongue KO --text "parity"`);
    expect(scbeOut).toBe(sixOut);
  });

  it('all 3 CLIs decode identically', () => {
    const tokens = run(`${PYTHON!} scbe tongues encode --tongue ko --text "three way"`);
    const d1 = run(`${PYTHON!} scbe tongues decode --tongue ko --as-text --text "${tokens}"`);
    const d2 = run(`${PYTHON!} scbe-cli.py decode --tongue ko --as-text --text "${tokens}"`);
    const d3 = run(`${PYTHON!} six-tongues-cli.py decode --tongue KO --as-text --text "${tokens}"`);
    expect(d1).toBe('three way');
    expect(d2).toBe('three way');
    expect(d3).toBe('three way');
  });
});
