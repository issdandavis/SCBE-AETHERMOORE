/**
 * @file semantic-bridge.ts
 * @module agent-bus/semantic-bridge
 *
 * Dimensional semantic decomposition engine for the agent bus.
 *
 * Design:
 *   - Every semantic atom carries a 6D dimensional vector keyed to the six
 *     Sacred Tongues (KO/AV/RU/CA/UM/DR) — each dimension is a float in [0,1].
 *   - Vectors quantize to 8 bits per dimension → 48-bit binary fingerprint
 *     → 12-char hex encoding.
 *   - decompose(input) returns atoms + combined dimensional vector + hex
 *     fingerprint for ANY input: natural language, code, or numeric data.
 *   - recompose(hex) returns the atom closest (by cosine similarity) to the
 *     fingerprint — converting numbers back into meaning.
 *   - Words are the delivery mechanism; atoms + dimensions + hex are the
 *     substrate that numbers track.
 *
 * Zero external dependencies. Runs in-process inside the bus.
 */

import { createHash } from 'node:crypto';

// ─── Dimension axis: 6 Sacred Tongue axes ────────────────────────────────────

/**
 * 6-element vector [KO, AV, RU, CA, UM, DR], each in [0, 1].
 *
 *   KO  — observation / perception (what is seen)
 *   AV  — transition / change      (what moves)
 *   RU  — structure / form         (what holds shape)
 *   CA  — calculation / logic      (what is computed)
 *   UM  — boundary / unknown       (what is edge or hidden)
 *   DR  — generation / creation    (what is born)
 */
export type DimVec = [number, number, number, number, number, number];

export const DIM_AXES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;
export type DimAxis = (typeof DIM_AXES)[number];

// ─── Atom table with dimensional vectors ─────────────────────────────────────

export interface AtomEntry {
  semanticId: string;
  bucketId: string;
  taskType: string;
  /** Valence: bonding capacity (0–6). Higher = more combinable. */
  valence: number;
  /** Dimensional signature in the 6-axis Sacred Tongue space. */
  dims: DimVec;
  forms: string[];
}

export const ATOM_TABLE: Record<string, AtomEntry> = {
  BLOCK: {
    semanticId: 'BLOCK',
    bucketId: 'CORE:CONSTRAINT:OBSTRUCTION',
    taskType: 'governance',
    valence: 2,
    // Observation(high): sees the obstacle; Transition(low): stops movement;
    // Structure(high): rigid constraint; Calculation(high): policy check;
    // Boundary(high): edge condition; Generation(low): blocks creation.
    dims: [0.85, 0.1, 0.9, 0.88, 0.8, 0.05],
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
  TRANSFORM: {
    semanticId: 'TRANSFORM',
    bucketId: 'CORE:OPERATION:STATE_CHANGE',
    taskType: 'coding',
    valence: 4,
    // Observation(med): watches state; Transition(high): state changes;
    // Structure(high): preserves form while changing content;
    // Calculation(high): compute-heavy; Boundary(low): not edge; Generation(med).
    dims: [0.5, 0.82, 0.78, 0.92, 0.15, 0.55],
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
  FLOW: {
    semanticId: 'FLOW',
    bucketId: 'CORE:MOTION:DIRECTED_CONTINUITY',
    taskType: 'research',
    valence: 3,
    // Observation(med): track path; Transition(high): moves continuously;
    // Structure(med): shaped channel; Calculation(low): not compute-heavy;
    // Boundary(med): has edges; Generation(high): produces output downstream.
    dims: [0.6, 0.95, 0.55, 0.25, 0.45, 0.8],
    forms: ['flow', 'flows', 'stream', 'pipeline', 'control flow', 'data flow', 'event stream'],
  },
  WATER: {
    semanticId: 'WATER',
    bucketId: 'CORE:MATERIAL:FLOWING_SOLVENT',
    taskType: 'research',
    valence: 2,
    // Observation(high): highly visible; Transition(high): phase changes;
    // Structure(low): amorphous; Calculation(low): not compute;
    // Boundary(med): container walls; Generation(med): rain/growth.
    dims: [0.88, 0.9, 0.2, 0.1, 0.5, 0.6],
    forms: ['water', 'river', 'rain', 'steam', 'ice', 'liquid'],
  },
};

// Pre-sorted forms (longest first) for greedy match.
const COMPILED_TABLE = Object.fromEntries(
  Object.entries(ATOM_TABLE).map(([id, entry]) => [
    id,
    { ...entry, forms: [...entry.forms].sort((a, b) => b.length - a.length) },
  ])
);

// ─── Dimensional math ─────────────────────────────────────────────────────────

/** Weighted-average of multiple DimVec values. Weights default to counts. */
export function combineDims(pairs: Array<{ dims: DimVec; weight: number }>): DimVec {
  if (pairs.length === 0) return [0, 0, 0, 0, 0, 0];
  const total = pairs.reduce((s, p) => s + p.weight, 0);
  const out: DimVec = [0, 0, 0, 0, 0, 0];
  for (const { dims, weight } of pairs) {
    for (let i = 0; i < 6; i++) {
      out[i] += (dims[i] * weight) / total;
    }
  }
  return out;
}

/** Cosine similarity in the 6D space. */
function cosine(a: DimVec, b: DimVec): number {
  let dot = 0;
  let na = 0;
  let nb = 0;
  for (let i = 0; i < 6; i++) {
    dot += a[i] * b[i];
    na += a[i] * a[i];
    nb += b[i] * b[i];
  }
  const denom = Math.sqrt(na) * Math.sqrt(nb);
  return denom === 0 ? 0 : dot / denom;
}

// ─── Binary / hex encoding ────────────────────────────────────────────────────

/**
 * Encode a DimVec as a 12-char hex string.
 * Each of the 6 dimensions is quantized to 8 bits → 6 bytes → 12 hex chars.
 *
 * Format:  [KO_u8][AV_u8][RU_u8][CA_u8][UM_u8][DR_u8]
 */
export function dimsToHex(dims: DimVec): string {
  const bytes = Buffer.alloc(6);
  for (let i = 0; i < 6; i++) {
    bytes[i] = Math.round(Math.min(Math.max(dims[i], 0), 1) * 255);
  }
  return bytes.toString('hex');
}

/**
 * Decode a 12-char hex string back to a DimVec.
 * Inverse of dimsToHex.
 */
export function hexToDims(hex: string): DimVec {
  const cleaned = hex
    .replace(/[^0-9a-f]/gi, '')
    .slice(0, 12)
    .padEnd(12, '0');
  const bytes = Buffer.from(cleaned, 'hex');
  return [
    bytes[0] / 255,
    bytes[1] / 255,
    bytes[2] / 255,
    bytes[3] / 255,
    bytes[4] / 255,
    bytes[5] / 255,
  ];
}

/**
 * Encode a DimVec as a 48-bit binary string (6 groups of 8 bits, space-separated).
 * Human-readable form: "11011011 01001111 ..."
 */
export function dimsToBinary(dims: DimVec): string {
  return dims
    .map((v) => {
      const byte = Math.round(Math.min(Math.max(v, 0), 1) * 255);
      return byte.toString(2).padStart(8, '0');
    })
    .join(' ');
}

// ─── Decomposition ────────────────────────────────────────────────────────────

function normalizeText(text: string): string {
  return text.toLowerCase().replace(/\s+/g, ' ').trim();
}

export interface AtomHit {
  semanticId: string;
  bucketId: string;
  count: number;
  dims: DimVec;
  hex: string;
  binary: string;
}

export interface DecompositionResult {
  schemaVersion: 'scbe-decomposition-v1';
  /** Original text. */
  input: string;
  /** Sha256 truncated to 16 hex chars — stable identity for this input. */
  inputHash: string;
  /** Individual atom matches. */
  atoms: AtomHit[];
  /** Weighted-average of all matched atom dimensions. Zero if no atoms. */
  combinedDims: DimVec;
  /** 12-char hex fingerprint of combinedDims. */
  combinedHex: string;
  /** 48-bit binary representation of combinedDims, space-separated by axis. */
  combinedBinary: string;
  /** Total number of surface-form matches across all atoms. */
  tokenCount: number;
  /** Dominant atom semanticId (most matches), or null if no matches. */
  dominant: string | null;
  /** Auto-detected taskType from dominant atom. */
  taskType: string;
}

/**
 * Decompose any text into semantic atoms with dimensional analysis.
 *
 * The returned `combinedHex` is the numeric fingerprint of the input's meaning.
 * It encodes: [how_observable, how_transitional, how_structural,
 *              how_computational, how_boundary, how_generative]
 * as 6 bytes in Sacred Tongue axis order.
 */
export function decompose(input: string, currentTaskType = 'general'): DecompositionResult {
  const n = normalizeText(input);
  const inputHash = createHash('sha256').update(input).digest('hex').slice(0, 16);
  const atomHits: AtomHit[] = [];

  for (const entry of Object.values(COMPILED_TABLE)) {
    let count = 0;
    const occupied: Array<[number, number]> = [];

    for (const form of entry.forms) {
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
      atomHits.push({
        semanticId: entry.semanticId,
        bucketId: entry.bucketId,
        count,
        dims: entry.dims,
        hex: dimsToHex(entry.dims),
        binary: dimsToBinary(entry.dims),
      });
    }
  }

  atomHits.sort((a, b) => b.count - a.count);
  const tokenCount = atomHits.reduce((s, a) => s + a.count, 0);
  const dominant = atomHits[0]?.semanticId ?? null;

  const combinedDims = combineDims(atomHits.map((a) => ({ dims: a.dims, weight: a.count })));
  const combinedHex = dimsToHex(combinedDims);
  const combinedBinary = dimsToBinary(combinedDims);

  let taskType = currentTaskType;
  if (taskType === 'general' && dominant) {
    taskType = ATOM_TABLE[dominant]?.taskType ?? 'general';
  }

  return {
    schemaVersion: 'scbe-decomposition-v1',
    input,
    inputHash,
    atoms: atomHits,
    combinedDims,
    combinedHex,
    combinedBinary,
    tokenCount,
    dominant,
    taskType,
  };
}

// ─── Recomposition ────────────────────────────────────────────────────────────

export interface RecompositionResult {
  schemaVersion: 'scbe-recomposition-v1';
  /** Input hex fingerprint. */
  inputHex: string;
  /** Decoded dimensional vector. */
  dims: DimVec;
  /** Closest atom by cosine similarity. */
  closest: {
    semanticId: string;
    bucketId: string;
    similarity: number;
    taskType: string;
  } | null;
  /** All atoms ranked by similarity. */
  ranked: Array<{ semanticId: string; similarity: number }>;
  /** Best-guess surface forms (forms of the closest atom). */
  suggestedForms: string[];
}

/**
 * Recompose meaning from a hex fingerprint.
 * Converts numbers back into the nearest atom and its surface forms.
 */
export function recompose(hex: string): RecompositionResult {
  const dims = hexToDims(hex);
  const ranked = Object.values(ATOM_TABLE)
    .map((a) => ({ semanticId: a.semanticId, similarity: cosine(dims, a.dims) }))
    .sort((a, b) => b.similarity - a.similarity);

  const best = ranked[0] ?? null;
  const bestEntry = best ? ATOM_TABLE[best.semanticId] : null;

  return {
    schemaVersion: 'scbe-recomposition-v1',
    inputHex: hex,
    dims,
    closest: best
      ? {
          semanticId: best.semanticId,
          bucketId: bestEntry!.bucketId,
          similarity: best.similarity,
          taskType: bestEntry!.taskType,
        }
      : null,
    ranked,
    suggestedForms: bestEntry?.forms.slice(0, 3) ?? [],
  };
}

// ─── Dimensional analysis ─────────────────────────────────────────────────────

export interface DimensionalAnalysis {
  schemaVersion: 'scbe-dim-analysis-v1';
  atomIds: string[];
  /** Combined dimensional vector of all atoms. */
  resultDims: DimVec;
  resultHex: string;
  resultBinary: string;
  /**
   * Dominant axis: which Sacred Tongue axis is strongest in the combination.
   * This tells you the primary "color" of the composed meaning.
   */
  dominantAxis: DimAxis;
  dominantAxisValue: number;
  /**
   * Whether the combination is dimensionally consistent.
   * Consistent = no atom has zero similarity to the combined vector
   * (each atom contributes something, none is a pure contradiction).
   */
  consistent: boolean;
  /** Per-atom similarity to the combined vector. */
  atomSimilarities: Array<{ semanticId: string; similarity: number }>;
}

/**
 * Analyze the dimensional consistency of combining a set of atoms.
 *
 * Example: FLOW + TRANSFORM is consistent (pipeline that transforms data).
 * BLOCK + FLOW requires care — BLOCK strongly resists the AV axis that FLOW relies on.
 */
export function analyzeDimensions(atomIds: string[]): DimensionalAnalysis {
  const entries = atomIds.map((id) => ATOM_TABLE[id]).filter(Boolean);
  const resultDims = combineDims(entries.map((e) => ({ dims: e.dims, weight: e.valence })));
  const resultHex = dimsToHex(resultDims);
  const resultBinary = dimsToBinary(resultDims);

  let maxVal = -1;
  let maxAxis: DimAxis = 'KO';
  for (let i = 0; i < 6; i++) {
    if (resultDims[i] > maxVal) {
      maxVal = resultDims[i];
      maxAxis = DIM_AXES[i];
    }
  }

  const atomSimilarities = entries.map((e) => ({
    semanticId: e.semanticId,
    similarity: cosine(e.dims, resultDims),
  }));

  const consistent = atomSimilarities.every((a) => a.similarity > 0.3);

  return {
    schemaVersion: 'scbe-dim-analysis-v1',
    atomIds,
    resultDims,
    resultHex,
    resultBinary,
    dominantAxis: maxAxis,
    dominantAxisValue: maxVal,
    consistent,
    atomSimilarities,
  };
}

// ─── Legacy thin API (backwards-compat with prior semantic-bridge) ────────────

export interface AtomLedger {
  schemaVersion: 'scbe-atom-ledger-v1';
  inputHash: string;
  tokenCount: number;
  atoms: Array<{ semanticId: string; bucketId: string; count: number }>;
}

export function scanAtoms(
  task: string
): Array<{ semanticId: string; bucketId: string; count: number }> {
  return decompose(task).atoms.map(({ semanticId, bucketId, count }) => ({
    semanticId,
    bucketId,
    count,
  }));
}

export function detectTaskType(task: string, currentType: string): string {
  return decompose(task, currentType).taskType;
}

export function buildAtomLedger(task: string): AtomLedger {
  const d = decompose(task);
  return {
    schemaVersion: 'scbe-atom-ledger-v1',
    inputHash: d.inputHash,
    tokenCount: d.tokenCount,
    atoms: d.atoms.map(({ semanticId, bucketId, count }) => ({ semanticId, bucketId, count })),
  };
}
