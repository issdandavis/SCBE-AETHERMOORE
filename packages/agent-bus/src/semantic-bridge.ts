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
 * Atom taxonomy:
 *   Domain atoms   (content): BLOCK, TRANSFORM, FLOW, WATER
 *   Discourse atoms (pragmatic turn-taking): ANNOUNCE, EXPAND, REQUEST, PIVOT, CARRY, HOLD
 *
 * Discourse profiles are detected from compound atom patterns and exposed on
 * every DecompositionResult so the bus can route accordingly.
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
  // ─── Domain atoms (content primitives) ─────────────────────────────────────

  BLOCK: {
    semanticId: 'BLOCK',
    bucketId: 'CORE:CONSTRAINT:OBSTRUCTION',
    taskType: 'governance',
    valence: 2,
    // KO(high): sees the obstacle; AV(low): stops movement;
    // RU(high): rigid constraint; CA(high): policy check;
    // UM(high): edge condition; DR(low): blocks creation.
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
    // KO(med): watches state; AV(high): state changes;
    // RU(high): preserves form; CA(high): compute-heavy;
    // UM(low): not edge; DR(med): output generated.
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
    // KO(med): track path; AV(high): moves continuously;
    // RU(med): shaped channel; CA(low): not compute-heavy;
    // UM(med): has edges; DR(high): downstream output.
    dims: [0.6, 0.95, 0.55, 0.25, 0.45, 0.8],
    forms: ['flow', 'flows', 'stream', 'pipeline', 'control flow', 'data flow', 'event stream'],
  },
  WATER: {
    semanticId: 'WATER',
    bucketId: 'CORE:MATERIAL:FLOWING_SOLVENT',
    taskType: 'research',
    valence: 2,
    // KO(high): highly visible; AV(high): phase changes;
    // RU(low): amorphous; CA(low): not compute;
    // UM(med): container walls; DR(med): rain/growth.
    dims: [0.88, 0.9, 0.2, 0.1, 0.5, 0.6],
    forms: ['water', 'river', 'rain', 'steam', 'ice', 'liquid'],
  },

  // ─── Discourse atoms (pragmatic / turn-taking primitives) ──────────────────
  //
  // These model the micro-grammar of how humans hold, steer, and earn the
  // conversational floor. They compose with domain atoms to produce profiles:
  //   ANNOUNCE + EXPAND  → 'long_turn'        (floor held, developing a point)
  //   PIVOT    + BLOCK   → 'governance_steer' (steering around a denial)
  //   CARRY              → 'warranted_claim'  (memory-backed assertion)
  //   REQUEST            → 'floor_hold'       (requesting permission to continue)
  //   HOLD alone         → 'backchannel'      (listener co-construction only)

  ANNOUNCE: {
    semanticId: 'ANNOUNCE',
    bucketId: 'DISCOURSE:FLOOR:PRE_ANNOUNCE',
    taskType: 'research',
    valence: 3,
    // KO(med): aware of listener; AV(low): pauses to set up;
    // RU(high): creates frame/structure; CA(low): not compute-heavy;
    // UM(med): opens possibility space; DR(very high): creates expectation contract.
    dims: [0.6, 0.3, 0.88, 0.18, 0.38, 0.92],
    forms: [
      'let me explain',
      'i want to say',
      'the thing about',
      'what you need to know',
      'let me tell you',
      'to give you context',
      'a few things',
      'three things',
      'two things',
      'one thing',
    ],
  },
  EXPAND: {
    semanticId: 'EXPAND',
    bucketId: 'DISCOURSE:FLOOR:EXAMPLE_CHAIN',
    taskType: 'research',
    valence: 4,
    // KO(med): observing examples; AV(high): moving through chain;
    // RU(med): maintaining pattern; CA(high): cumulative reasoning;
    // UM(low): not edge; DR(high): generates insight from accumulation.
    dims: [0.55, 0.82, 0.58, 0.88, 0.2, 0.74],
    forms: [
      'for example',
      'for instance',
      'another example',
      'another case',
      'think about',
      'just like',
      'the same way',
      'consider this',
      'similarly',
      'take for example',
      'to illustrate',
    ],
  },
  REQUEST: {
    semanticId: 'REQUEST',
    bucketId: 'DISCOURSE:FLOOR:PERMISSION_TOKEN',
    taskType: 'governance',
    valence: 2,
    // KO(high): perceptive of social space; AV(low): paused at boundary;
    // RU(med): maintains relational structure; CA(low): not logical;
    // UM(very high): operates at permission edge; DR(low): asks not generates.
    dims: [0.82, 0.18, 0.48, 0.12, 0.92, 0.1],
    forms: [
      'bear with me',
      'i know this is a lot',
      'almost done',
      'one more thing',
      'if i can',
      'does that make sense',
      'you know what i mean',
      'just to finish',
      'to wrap up',
      'last thing',
    ],
  },
  PIVOT: {
    semanticId: 'PIVOT',
    bucketId: 'DISCOURSE:STEER:REDIRECT',
    taskType: 'governance',
    valence: 3,
    // KO(high): draws attention; AV(high): direction change;
    // RU(low): disrupts prior structure; CA(med): logical reorientation;
    // UM(high): operates at edge of prior frame; DR(med): installs new vector.
    dims: [0.92, 0.88, 0.12, 0.62, 0.85, 0.52],
    forms: [
      'but',
      'however',
      'actually',
      'what i mean is',
      "here's the thing",
      'look',
      'the point is',
      'that said',
      'although',
      'to be fair',
      'i mean',
      'wait',
      'no but',
    ],
  },
  CARRY: {
    semanticId: 'CARRY',
    bucketId: 'DISCOURSE:WARRANT:PERSONAL_MEMORY',
    taskType: 'research',
    valence: 2,
    // KO(very high): perception of past event; AV(med): movement through time;
    // RU(low): fluid not rigid; CA(low): affective not logical;
    // UM(med): personal boundary, vulnerability; DR(high): generates credibility.
    dims: [0.92, 0.62, 0.22, 0.15, 0.58, 0.8],
    forms: [
      'i remember',
      'i was there',
      'when i',
      "i've seen",
      'back when',
      'i used to',
      'i once',
      'in my experience',
      'true story',
      'i had',
      'i was in',
    ],
  },
  HOLD: {
    semanticId: 'HOLD',
    bucketId: 'DISCOURSE:LISTENER:BACKCHANNEL',
    taskType: 'general',
    valence: 1,
    // KO(high): attentive; AV(very low): not moving, holding still;
    // RU(med): maintains conversation structure; CA(very low): not logical;
    // UM(low): not at edge; DR(very low): receiving not generating.
    dims: [0.88, 0.08, 0.62, 0.08, 0.35, 0.08],
    forms: [
      'mm',
      'mhm',
      'right',
      'yeah',
      'sure',
      'okay',
      'i see',
      'go on',
      'i hear you',
      'tell me more',
      'uh huh',
    ],
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

// ─── Discourse profile detection ─────────────────────────────────────────────

/**
 * Discourse profiles — compound patterns that describe how the floor is managed:
 *
 *   governance_steer  PIVOT + BLOCK  — speaker is redirecting around a denial
 *   long_turn         ANNOUNCE + EXPAND — speaker has floor, developing a point
 *   warranted_claim   CARRY present  — claim is backed by personal memory
 *   floor_hold        REQUEST present — asking permission to continue
 *   backchannel       HOLD only       — pure listener co-construction
 */
export type DiscourseProfile =
  'governance_steer' | 'long_turn' | 'warranted_claim' | 'floor_hold' | 'backchannel' | null;

export function detectDiscourseProfile(atoms: AtomHit[]): DiscourseProfile {
  const ids = new Set(atoms.map((a) => a.semanticId));
  // Compound: PIVOT + BLOCK → someone is steering around a denial/constraint
  if (ids.has('PIVOT') && ids.has('BLOCK')) return 'governance_steer';
  // Compound: ANNOUNCE + EXPAND → speaker holds the floor, developing a point
  if (ids.has('ANNOUNCE') && ids.has('EXPAND')) return 'long_turn';
  // Single: CARRY → claim is warranted by personal memory
  if (ids.has('CARRY')) return 'warranted_claim';
  // Single: REQUEST → seeking permission to continue
  if (ids.has('REQUEST')) return 'floor_hold';
  // Listener-only: HOLD with no other atoms
  if (ids.has('HOLD') && ids.size === 1) return 'backchannel';
  return null;
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
  /**
   * Discourse profile from compound atom patterns, or null if none detected.
   * governance_steer overrides taskType to 'governance' in detectTaskType().
   */
  discourseProfile: DiscourseProfile;
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

  const discourseProfile = detectDiscourseProfile(atomHits);

  let taskType = currentTaskType;
  // governance_steer overrides any current type — PIVOT+BLOCK is unambiguous
  if (discourseProfile === 'governance_steer') {
    taskType = 'governance';
  } else if (taskType === 'general' && dominant) {
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
    discourseProfile,
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

// ─── Spoken Longform Dialogue Scoring ─────────────────────────────────────────
//
// Bridge: semantic decomposition → spoken-longform-dialogue rubric.
// Reference: .agents/skills/spoken-longform-dialogue/references/semantic-bus-scoring.md

export interface DialogueDimension {
  name: string;
  max: number;
  score: number;
  evidence: string[];
  warning?: string;
}

export interface DialogueScoreResult {
  schemaVersion: 'scbe-dialogue-score-v1';
  total: number;
  max: number;
  profile: DiscourseProfile;
  atoms: Array<{ semanticId: string; count: number }>;
  dimensions: DialogueDimension[];
  densityWarnings: string[];
  strongestFix: string;
}

/**
 * Score a spoken dialogue passage using the semantic atom tokenizer.
 *
 * Returns a 7-dimension rubric (total 10) with baseline hints from the
 * discourse profile, plus density warnings and a single strongest fix.
 */
export function scoreDialogue(input: string): DialogueScoreResult {
  const d = decompose(input);
  const atomMap = new Map(d.atoms.map((a) => [a.semanticId, a.count]));
  const has = (id: string) => atomMap.has(id);
  const count = (id: string) => atomMap.get(id) ?? 0;

  // ── Density warnings ──
  const densityWarnings: string[] = [];
  if (count('PIVOT') >= 4) {
    densityWarnings.push('PIVOT >= 4: likely over-steered; add a clean return or cut a branch.');
  }
  if (count('EXPAND') >= 4 && !has('CARRY')) {
    densityWarnings.push('EXPAND >= 4 with no CARRY: examples may feel generic.');
  }
  if (count('REQUEST') >= 3) {
    densityWarnings.push(
      'REQUEST >= 3: speaker may sound like they are asking permission too often.'
    );
  }
  if (has('ANNOUNCE') && !has('EXPAND')) {
    densityWarnings.push('ANNOUNCE with no EXPAND: promised a long turn but did not develop it.');
  }
  if (!has('HOLD') && !input.match(/silence|paused|looked|glanced|flinched|nodded|shook/i)) {
    densityWarnings.push(
      'No HOLD atom and no listener body in prose: the other person may disappear.'
    );
  }

  // ── Profile baseline defaults ──
  const profile = d.discourseProfile;

  // Start from zeros; apply profile baselines, then atom evidence.
  let reasonToSpeak = 0; // max 2
  let concreteMemory = 0; // max 2
  let emotionalPressure = 0; // max 2
  let listenerReaction = 0; // max 1
  let physicalAnchor = 0; // max 1 (semantic atoms cannot reliably detect)
  let controlledDivergence = 0; // max 1
  let cleanReturn = 0; // max 1 (semantic atoms cannot reliably detect)

  // Profile baselines
  if (profile === 'long_turn') {
    reasonToSpeak = Math.max(reasonToSpeak, 1);
    if (has('EXPAND')) controlledDivergence = Math.max(controlledDivergence, 1);
  } else if (profile === 'warranted_claim') {
    concreteMemory = Math.max(concreteMemory, 1);
    emotionalPressure = Math.max(emotionalPressure, 1);
  } else if (profile === 'floor_hold') {
    reasonToSpeak = Math.max(reasonToSpeak, 1);
    if (input.match(/noticed|looked at|watched|saw them/i)) {
      listenerReaction = Math.max(listenerReaction, 1);
    }
  } else if (profile === 'backchannel') {
    // Listener-only signal; not scored as a long turn
    reasonToSpeak = 0;
  } else if (profile === 'governance_steer') {
    reasonToSpeak = Math.max(reasonToSpeak, 1);
    emotionalPressure = Math.max(emotionalPressure, 1);
  }

  // Atom evidence — reason to speak now (max 2)
  if (has('ANNOUNCE')) {
    reasonToSpeak = Math.max(reasonToSpeak, 1);
    if (count('ANNOUNCE') >= 2 || has('EXPAND')) reasonToSpeak = 2;
  }
  if (has('REQUEST')) {
    reasonToSpeak = Math.max(reasonToSpeak, 1);
  }
  if (has('PIVOT')) {
    reasonToSpeak = Math.max(reasonToSpeak, 1);
  }
  if (input.match(/No\.|That is not what happened\.|I can answer that, but not quickly\./i)) {
    reasonToSpeak = 2; // strong scene trigger
  }

  // Atom evidence — concrete memory / example (max 2)
  if (has('CARRY')) {
    concreteMemory = Math.max(concreteMemory, 1);
    // Upgrade to 2 only when the memory contains who/where/when/object/stakes
    if (
      input.match(
        /\b(March|April|May|June|July|August|September|October|November|December|January|February|20\d\d|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b/i
      ) &&
      input.match(/\b(hand|cup|door|car|table|chair|desk|window|street|room|office|kitchen)\b/i)
    ) {
      concreteMemory = 2;
    }
  }
  if (has('EXPAND')) {
    concreteMemory = Math.max(concreteMemory, 1);
    if (has('CARRY') && count('EXPAND') >= 2) concreteMemory = 2;
  }

  // Atom evidence — emotional pressure (max 2)
  if (has('CARRY') || has('PIVOT') || has('BLOCK')) {
    emotionalPressure = Math.max(emotionalPressure, 1);
  }
  // Upgrade to 2 requires wound language in prose
  if (input.match(/cost|lost|failed|hurt|afraid|ashamed|could not|would not|never did|regret/i)) {
    emotionalPressure = Math.max(emotionalPressure, 1);
    if (has('CARRY') || has('BLOCK')) emotionalPressure = 2;
  }

  // Atom evidence — listener reaction (max 1)
  if (has('HOLD')) {
    listenerReaction = 1;
  }
  if (has('REQUEST') && input.match(/noticed|looked at|watched|saw them/i)) {
    listenerReaction = 1;
  }
  if (input.match(/silence|paused|looked|glanced|flinched|nodded|shook|turned away/i)) {
    listenerReaction = 1;
  }

  // Atom evidence — controlled divergence (max 1)
  if (has('PIVOT') || has('EXPAND')) {
    controlledDivergence = Math.max(controlledDivergence, 1);
  }

  // Clean return / coda (max 1) — mostly manual; weak heuristics only
  if (
    input.match(
      /That is why|So when I say|What I mean is|I am telling you this because|But the point is|And that was before/i
    )
  ) {
    cleanReturn = Math.max(cleanReturn, 1);
  }

  // ── Build dimensions ──
  const dimensions: DialogueDimension[] = [
    {
      name: 'Reason to speak now',
      max: 2,
      score: Math.min(reasonToSpeak, 2),
      evidence: [
        ...(has('ANNOUNCE') ? ['ANNOUNCE: forecasts turn structure'] : []),
        ...(has('REQUEST') ? ['REQUEST: permission token'] : []),
        ...(has('PIVOT') ? ['PIVOT: resistance or reframing'] : []),
      ],
      warning: reasonToSpeak === 0 ? 'No floor marker and no scene trigger detected.' : undefined,
    },
    {
      name: 'Concrete memory or example',
      max: 2,
      score: Math.min(concreteMemory, 2),
      evidence: [
        ...(has('CARRY') ? ['CARRY: personal-memory warrant'] : []),
        ...(has('EXPAND') ? ['EXPAND: example chain'] : []),
      ],
      warning:
        has('CARRY') && concreteMemory < 2
          ? 'CARRY present but memory lacks who/where/when/object/stakes.'
          : undefined,
    },
    {
      name: 'Emotional pressure',
      max: 2,
      score: Math.min(emotionalPressure, 2),
      evidence: [
        ...(has('CARRY') ? ['CARRY: memory carries affective residue'] : []),
        ...(has('PIVOT') ? ['PIVOT: steering against resistance'] : []),
        ...(has('BLOCK') ? ['BLOCK: constraint or denial'] : []),
      ],
      warning:
        emotionalPressure === 0
          ? 'Atoms cannot prove wound; inspect prose for cost or fear.'
          : undefined,
    },
    {
      name: 'Listener reaction',
      max: 1,
      score: Math.min(listenerReaction, 1),
      evidence: [
        ...(has('HOLD') ? ['HOLD: listener co-construction signal'] : []),
        ...(has('REQUEST') ? ['REQUEST: speaker notices listener'] : []),
      ],
      warning:
        listenerReaction === 0 ? 'No HOLD atom and no visible listener body in prose.' : undefined,
    },
    {
      name: 'Physical anchor',
      max: 1,
      score: Math.min(physicalAnchor, 1),
      evidence: [],
      warning: 'Must be manually checked for object, sound, or setting anchor.',
    },
    {
      name: 'Controlled divergence',
      max: 1,
      score: Math.min(controlledDivergence, 1),
      evidence: [
        ...(has('PIVOT') ? ['PIVOT: branch or redirection'] : []),
        ...(has('EXPAND') ? ['EXPAND: example development'] : []),
      ],
      warning: count('PIVOT') >= 3 ? 'High pivot count without visible return phrase.' : undefined,
    },
    {
      name: 'Clean return / coda',
      max: 1,
      score: Math.min(cleanReturn, 1),
      evidence: cleanReturn > 0 ? ['Steering phrase detected near end.'] : [],
      warning: 'Must be manually checked: last sentence should change the present scene.',
    },
  ];

  const total = dimensions.reduce((s, dim) => s + dim.score, 0);
  const max = dimensions.reduce((s, dim) => s + dim.max, 0);

  // ── Strongest fix ──
  let strongestFix = '';
  if (total < 6) {
    strongestFix =
      'This reads as exposition. Add one concrete memory (CARRY) or a scene trigger (ANNOUNCE/REQUEST) to earn the long turn.';
  } else {
    const weakest = dimensions
      .filter((d) => d.score < d.max)
      .sort((a, b) => a.score / a.max - b.score / b.max)[0];
    if (weakest) {
      switch (weakest.name) {
        case 'Reason to speak now':
          strongestFix =
            'Add a trigger line at the start: "No." or "That is not what happened." or "I can answer that, but not quickly."';
          break;
        case 'Concrete memory or example':
          strongestFix =
            'Insert one specific scene: who was there, what object they touched, what went wrong.';
          break;
        case 'Emotional pressure':
          strongestFix =
            'Surface the wound: what did the speaker lose, fail, or fear? Make the cost visible.';
          break;
        case 'Listener reaction':
          strongestFix =
            'Add one silent listener beat after the memory lands: hand on cup, eyes moving to the door, refusal to answer.';
          break;
        case 'Physical anchor':
          strongestFix =
            'Anchor the speech to one object, sound, or setting detail that the speaker touches or notices.';
          break;
        case 'Controlled divergence':
          strongestFix =
            'The side path needs a sharper return phrase: "But the point is..." or "That is why..."';
          break;
        case 'Clean return / coda':
          strongestFix =
            'End by changing the present scene, not summarizing the theme. Return from story-world to the current room.';
          break;
      }
    } else {
      strongestFix = 'All dimensions strong. The turn can safely run multiple paragraphs.';
    }
  }

  return {
    schemaVersion: 'scbe-dialogue-score-v1',
    total,
    max,
    profile,
    atoms: d.atoms.map((a) => ({ semanticId: a.semanticId, count: a.count })),
    dimensions,
    densityWarnings,
    strongestFix,
  };
}
