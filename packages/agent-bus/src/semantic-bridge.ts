/**
 * @file semantic-bridge.ts
 * @module agent-bus/semantic-bridge
 *
 * Lightweight semantic atom scanner for the agent bus.
 *
 * Contains a self-contained surface-form table extracted from
 * src/tokenizer/semantic-atom.ts. Zero external dependencies — runs
 * inside the bus process without spawning Python.
 *
 * Responsibilities:
 *   - detectTaskType(task)   → infer taskType from dominant semantic atom
 *   - buildAtomLedger(task)  → compact {atoms, inputHash} for result envelopes
 */

import { createHash } from 'node:crypto';

// ─── Minimal atom table (surface-form data only) ─────────────────────────────

const ATOMS: Array<{
  semanticId: string;
  bucketId: string;
  taskType: string;
  forms: string[];
}> = [
  {
    semanticId: 'BLOCK',
    bucketId: 'CORE:CONSTRAINT:OBSTRUCTION',
    taskType: 'governance',
    forms: [
      'block',
      'blocks',
      'blocked',
      'barrier',
      'dam',
      'error',
      'exception',
      'deny',
      'failed test',
    ],
  },
  {
    semanticId: 'TRANSFORM',
    bucketId: 'CORE:OPERATION:STATE_CHANGE',
    taskType: 'coding',
    forms: [
      'transform',
      'transforms',
      'change',
      'convert',
      'compile',
      'compute',
      'add',
      'subtract',
      'multiply',
      'divide',
    ],
  },
  {
    semanticId: 'FLOW',
    bucketId: 'CORE:MOTION:DIRECTED_CONTINUITY',
    taskType: 'research',
    forms: ['flow', 'flows', 'stream', 'pipeline', 'control flow', 'data flow', 'event stream'],
  },
  {
    semanticId: 'WATER',
    bucketId: 'CORE:MATERIAL:FLOWING_SOLVENT',
    taskType: 'research',
    forms: ['water', 'river', 'rain', 'steam', 'ice', 'liquid'],
  },
];

// Pre-sorted longest-first per atom to prefer multi-word surface forms.
const COMPILED_ATOMS = ATOMS.map((a) => ({
  ...a,
  forms: [...a.forms].sort((x, y) => y.length - x.length),
}));

function normalize(text: string): string {
  return text.toLowerCase().replace(/\s+/g, ' ').trim();
}

// ─── Public API ───────────────────────────────────────────────────────────────

export interface AtomHit {
  semanticId: string;
  bucketId: string;
  count: number;
}

export interface AtomLedger {
  schemaVersion: 'scbe-atom-ledger-v1';
  inputHash: string;
  tokenCount: number;
  atoms: AtomHit[];
}

/**
 * Scan `task` for semantic atom surface forms.
 * Returns one hit per distinct atom (with a count of non-overlapping matches).
 */
export function scanAtoms(task: string): AtomHit[] {
  const n = normalize(task);
  const hits: AtomHit[] = [];

  for (const atom of COMPILED_ATOMS) {
    let count = 0;
    const occupied: Array<[number, number]> = [];

    for (const form of atom.forms) {
      const pattern = new RegExp(
        `(^|\\b)${form.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(\\b|$)`,
        'g'
      );
      let m: RegExpExecArray | null;
      while ((m = pattern.exec(n)) !== null) {
        const start = m.index + m[1].length;
        const end = start + form.length;
        const overlaps = occupied.some(([s, e]) => start < e && s < end);
        if (!overlaps) {
          occupied.push([start, end]);
          count += 1;
        }
      }
    }

    if (count > 0) {
      hits.push({ semanticId: atom.semanticId, bucketId: atom.bucketId, count });
    }
  }

  // Sort by count descending so dominant atom is first.
  return hits.sort((a, b) => b.count - a.count);
}

/**
 * Detect the task type from the dominant semantic atom.
 * Returns the existing `currentType` unchanged if no atoms match or if
 * `currentType` is already something other than 'general'.
 */
export function detectTaskType(task: string, currentType: string): string {
  if (currentType !== 'general') return currentType;
  const hits = scanAtoms(task);
  if (hits.length === 0) return currentType;
  const dominant = hits[0].semanticId;
  const atom = COMPILED_ATOMS.find((a) => a.semanticId === dominant);
  return atom?.taskType ?? currentType;
}

/**
 * Build a compact atom ledger for attaching to result envelopes.
 */
export function buildAtomLedger(task: string): AtomLedger {
  const atoms = scanAtoms(task);
  return {
    schemaVersion: 'scbe-atom-ledger-v1',
    inputHash: createHash('sha256').update(task).digest('hex').slice(0, 16),
    tokenCount: atoms.reduce((s, a) => s + a.count, 0),
    atoms,
  };
}
