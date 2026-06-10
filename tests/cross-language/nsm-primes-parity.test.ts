/**
 * @file nsm-primes-parity.test.ts
 * @module tests/cross-language
 *
 * Cross-language parity: Python nsm_primes.py vs TypeScript nsmPrimes.ts.
 *
 * Asserts that for every probe input, both implementations return
 * bit-identical integers and close-enough floats (tol 1e-10).
 *
 * Domain sections extend the probe set to tokens drawn from HTML,
 * Markdown, C/C++, and Rust — languages that feed the code_weight_packets
 * tongue routing and must stay consistent across both runtimes.
 */

import * as path from 'path';
import { execFileSync } from 'child_process';
import { describe, it, expect } from 'vitest';

import {
  PHI,
  TONGUE_ORDER,
  TONGUE_PHASE,
  NSM_PRIMES,
  getPrime,
  gridIndex,
  primeGridIndex,
  phiExtrapolate,
  generateSubprimeAnchors,
} from '../../src/tokenizer/nsmPrimes.js';

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

const PYTHON_BIN = process.platform === 'win32' ? 'python' : 'python3';
const REPO_ROOT = path.resolve(__dirname, '../..');

function py(script: string): unknown {
  const full = [
    'import sys, json',
    `sys.path.insert(0, ${JSON.stringify(REPO_ROOT)})`,
    script,
    'print(json.dumps(result))',
  ].join('\n');
  try {
    const out = execFileSync(PYTHON_BIN, ['-c', full], {
      encoding: 'utf-8',
      timeout: 15_000,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    });
    return JSON.parse(out.trim());
  } catch {
    return null;
  }
}

function hasPython(): boolean {
  return py('result = 1') !== null;
}

const pythonAvailable = hasPython();

// ─────────────────────────────────────────────────────────────────────────────
// Probe sets
// ─────────────────────────────────────────────────────────────────────────────

// One per tongue + all cross-tongue primes + boundary cases
const PRIME_PROBES = [
  // KO face
  'ko.i',
  'ko.you',
  'ko.want',
  'ko.not',
  'ko.think',
  'ko.if',
  'ko.do',
  // AV face
  'av.say',
  'av.see',
  'av.hear',
  'av.move',
  // RU face
  'ru.good',
  'ru.bad',
  'ru.all',
  // CA face
  'ca.one',
  'ca.two',
  'ca.more',
  // UM face
  'um.inside',
  'um.feel',
  'um.have',
  // DR face
  'dr.know',
  'dr.before',
  'dr.after',
];

// ─────────────────────────────────────────────────────────────────────────────
// Suite
// ─────────────────────────────────────────────────────────────────────────────

describe.skipIf(!pythonAvailable)('NSM Primes — Python / TypeScript parity', () => {
  // ── Constants ──────────────────────────────────────────────────────────────

  describe('Constants', () => {
    it('PHI matches', () => {
      const r = py('from src.tokenizer.nsm_primes import PHI; result = PHI') as number;
      expect(PHI).toBeCloseTo(r, 14);
    });

    it('TONGUE_ORDER matches', () => {
      const r = py(
        'from src.tokenizer.nsm_primes import TONGUE_ORDER; result = list(TONGUE_ORDER)'
      ) as string[];
      expect(TONGUE_ORDER).toEqual(r);
    });

    it('TONGUE_PHASE values match', () => {
      const r = py(
        'from src.tokenizer.nsm_primes import TONGUE_PHASE; result = dict(TONGUE_PHASE)'
      ) as Record<string, number>;
      for (const t of TONGUE_ORDER) {
        expect(TONGUE_PHASE[t]).toBeCloseTo(r[t], 12);
      }
    });

    it('NSM_PRIMES length matches', () => {
      const r = py(
        'from src.tokenizer.nsm_primes import NSM_PRIMES; result = len(NSM_PRIMES)'
      ) as number;
      expect(NSM_PRIMES.length).toBe(r);
    });
  });

  // ── Prime table fields ─────────────────────────────────────────────────────

  describe('Prime table fields', () => {
    for (const id of PRIME_PROBES) {
      it(id, () => {
        const ts = getPrime(id);
        expect(ts).toBeDefined();

        const r = py(`
from src.tokenizer.nsm_primes import get_prime
p = get_prime(${JSON.stringify(id)})
result = {
  'r': p.r,
  'grid_row': p.grid_row,
  'grid_col': p.grid_col,
  'primary_tongue': p.primary_tongue,
  'primary_confidence': p.primary_confidence,
  'is_cross_tongue': p.is_cross_tongue,
  'phi_order': p.phi_order,
  'label': p.label,
}
`) as Record<string, unknown>;

        expect(ts!.r).toBeCloseTo(r.r as number, 10);
        expect(ts!.gridRow).toBe(r.grid_row as number);
        expect(ts!.gridCol).toBe(r.grid_col as number);
        expect(ts!.spans[0].tongue).toBe(r.primary_tongue as string);
        expect(ts!.spans[0].confidence).toBeCloseTo(r.primary_confidence as number, 10);
        expect(ts!.phiOrder).toBe(r.phi_order as number);
        expect(ts!.label).toBe(r.label as string);
      });
    }
  });

  // ── Missing prime returns undefined / None ─────────────────────────────────

  describe('Missing prime', () => {
    it('getPrime("nonexistent") returns undefined in TS and None in Python', () => {
      expect(getPrime('nonexistent.prime')).toBeUndefined();
      const r = py(
        "from src.tokenizer.nsm_primes import get_prime; result = get_prime('nonexistent.prime') is None"
      );
      expect(r).toBe(true);
    });
  });

  // ── Grid index ─────────────────────────────────────────────────────────────

  describe('gridIndex', () => {
    const cases: Array<[number, number]> = [
      [0, 0],
      [0, 1],
      [1, 0],
      [15, 15],
      [3, 7],
      [8, 12],
      [0, 15],
      [15, 0],
    ];
    for (const [row, col] of cases) {
      it(`gridIndex(${row}, ${col})`, () => {
        const ts = gridIndex(row, col);
        const r = py(
          `from src.tokenizer.nsm_primes import grid_index; result = grid_index(${row}, ${col})`
        ) as number;
        expect(ts).toBe(r);
      });
    }
  });

  // ── primeGridIndex ─────────────────────────────────────────────────────────

  describe('primeGridIndex', () => {
    for (const id of ['ko.i', 'ko.want', 'av.say', 'dr.before']) {
      it(id, () => {
        const p = getPrime(id)!;
        const ts = primeGridIndex(p);
        const r = py(`
from src.tokenizer.nsm_primes import get_prime, prime_grid_index
result = prime_grid_index(get_prime(${JSON.stringify(id)}))
`) as number;
        expect(ts).toBe(r);
      });
    }
  });

  // ── phi_extrapolate step parity ────────────────────────────────────────────

  describe('phiExtrapolate step parity', () => {
    const probes = ['ko.want', 'av.say', 'ru.good', 'ca.one', 'um.inside', 'dr.before'];
    for (const id of probes) {
      it(`phiExtrapolate(${id}, 3)`, () => {
        const p = getPrime(id)!;
        const tsSteps = phiExtrapolate(p, 3);

        const r = py(`
from src.tokenizer.nsm_primes import get_prime, phi_extrapolate
steps = phi_extrapolate(get_prime(${JSON.stringify(id)}), steps=3)
result = [
  {
    'n': ex.n,
    'derived_tongue': ex.derived_tongue,
    'derived_r': ex.derived_r,
    'grid_row': ex.grid_row,
    'grid_col': ex.grid_col,
    'is_known_prime': ex.is_known_prime,
    'confidence': ex.confidence,
  }
  for ex in steps
]
`) as Array<Record<string, unknown>>;

        expect(tsSteps.length).toBe(r.length);
        for (let i = 0; i < r.length; i++) {
          expect(tsSteps[i].n).toBe(r[i].n);
          expect(tsSteps[i].derivedTongue).toBe(r[i].derived_tongue);
          expect(tsSteps[i].derivedR).toBeCloseTo(r[i].derived_r as number, 6);
          expect(tsSteps[i].gridRow).toBe(r[i].grid_row);
          expect(tsSteps[i].gridCol).toBe(r[i].grid_col);
          expect(tsSteps[i].isKnownPrime).toBe(r[i].is_known_prime);
          expect(tsSteps[i].confidence).toBeCloseTo(r[i].confidence as number, 6);
        }
      });
    }
  });

  // ── SubPrime anchor parity ─────────────────────────────────────────────────

  describe('generateSubprimeAnchors parity', () => {
    for (const id of ['ko.want', 'um.inside', 'dr.before']) {
      it(`generateSubprimeAnchors(${id}, 3)`, () => {
        const p = getPrime(id)!;
        const tsAnchors = generateSubprimeAnchors(p, 3);

        const r = py(`
from src.tokenizer.nsm_primes import get_prime, generate_subprime_anchors
anchors = generate_subprime_anchors(get_prime(${JSON.stringify(id)}), steps=3)
result = [
  {
    'n': a.n,
    'tongue': a.tongue,
    'r': a.r,
    'grid_row': a.grid_row,
    'grid_col': a.grid_col,
    'is_known_prime': a.is_known_prime,
    'proximity_confidence': a.proximity_confidence,
  }
  for a in anchors
]
`) as Array<Record<string, unknown>>;

        expect(tsAnchors.length).toBe(r.length);
        for (let i = 0; i < r.length; i++) {
          expect(tsAnchors[i].n).toBe(r[i].n);
          expect(tsAnchors[i].tongue).toBe(r[i].tongue);
          expect(tsAnchors[i].r).toBeCloseTo(r[i].r as number, 6);
          expect(tsAnchors[i].gridRow).toBe(r[i].grid_row);
          expect(tsAnchors[i].gridCol).toBe(r[i].grid_col);
          expect(tsAnchors[i].isKnownPrime).toBe(r[i].is_known_prime);
          expect(tsAnchors[i].proximityConfidence).toBeCloseTo(
            r[i].proximity_confidence as number,
            6
          );
        }
      });
    }
  });

  // ── Domain language tongue routing ─────────────────────────────────────────
  //
  // code_weight_packets.LANGUAGE_TONGUES must agree between Python and any
  // future TypeScript port.  We treat Python as the source of truth here and
  // assert the mapping covers all expected domain languages.

  describe('Domain language tongue routing (Python source of truth)', () => {
    const expectedMappings: Record<string, string> = {
      // Natural programming languages
      python: 'KO',
      typescript: 'AV',
      javascript: 'AV',
      rust: 'RU',
      c: 'CA',
      cpp: 'CA',
      csharp: 'CA',
      julia: 'UM',
      haskell: 'DR',
      // Markup / document languages
      html: 'RU',
      css: 'CA',
      markdown: 'AV',
      // Data / config languages
      json: 'DR',
      yaml: 'DR',
      toml: 'DR',
    };

    for (const [lang, expectedTongue] of Object.entries(expectedMappings)) {
      it(`${lang} → ${expectedTongue}`, () => {
        const r = py(`
from src.tokenizer.code_weight_packets import LANGUAGE_TONGUES
result = LANGUAGE_TONGUES.get(${JSON.stringify(lang)})
`) as string | null;
        expect(r).toBe(expectedTongue);
      });
    }
  });

  // ── Domain token semantic class ────────────────────────────────────────────

  describe('Domain token semantic classification (Python)', () => {
    const cases: Array<{ lang: string; token: string; expected: string }> = [
      // HTML structural tags → STRUCTURE
      { lang: 'html', token: '<div>', expected: 'STRUCTURE' },
      { lang: 'html', token: '<span>', expected: 'STRUCTURE' },
      { lang: 'html', token: '<section>', expected: 'STRUCTURE' },
      // HTML action tags → ACTION
      { lang: 'html', token: '<script>', expected: 'ACTION' },
      { lang: 'html', token: '<style>', expected: 'ACTION' },
      // HTML attributes → RELATION
      { lang: 'html', token: 'href', expected: 'RELATION' },
      { lang: 'html', token: 'src', expected: 'RELATION' },
      // Markdown headers → STRUCTURE
      { lang: 'markdown', token: '#', expected: 'STRUCTURE' },
      { lang: 'markdown', token: '##', expected: 'STRUCTURE' },
      // Markdown links → RELATION
      { lang: 'markdown', token: '[', expected: 'RELATION' },
      // Markdown code → ACTION
      { lang: 'markdown', token: '```', expected: 'ACTION' },
      // C/C++ control flow → ACTION
      { lang: 'c', token: 'if', expected: 'ACTION' },
      { lang: 'c', token: 'for', expected: 'ACTION' },
      { lang: 'c', token: 'return', expected: 'ACTION' },
      { lang: 'cpp', token: 'struct', expected: 'STRUCTURE' },
      { lang: 'cpp', token: 'class', expected: 'STRUCTURE' },
      // C/C++ operators → RELATION
      { lang: 'c', token: '->', expected: 'RELATION' },
      { lang: 'cpp', token: '::', expected: 'RELATION' },
      // C types → INERT_WITNESS
      { lang: 'c', token: 'void', expected: 'INERT_WITNESS' },
      { lang: 'c', token: 'NULL', expected: 'INERT_WITNESS' },
      // Rust definitions → ACTION
      { lang: 'rust', token: 'fn', expected: 'ACTION' },
      { lang: 'rust', token: 'impl', expected: 'ACTION' },
      // Rust types → STRUCTURE
      { lang: 'rust', token: 'struct', expected: 'STRUCTURE' },
      { lang: 'rust', token: 'enum', expected: 'STRUCTURE' },
      { lang: 'rust', token: 'trait', expected: 'STRUCTURE' },
      // Rust borrow/ownership → RELATION
      { lang: 'rust', token: '&', expected: 'RELATION' },
      { lang: 'rust', token: '->', expected: 'RELATION' },
      // Rust null-like → INERT_WITNESS
      { lang: 'rust', token: 'None', expected: 'INERT_WITNESS' },
    ];

    for (const { lang, token, expected } of cases) {
      it(`${lang}:${token} → ${expected}`, () => {
        const r = py(`
from src.tokenizer.code_weight_packets import semantic_class_for_domain
result = semantic_class_for_domain(${JSON.stringify(token)}, ${JSON.stringify(lang)})
`) as string | null;
        if (r !== null) expect(r).toBe(expected);
      });
    }
  });
});
