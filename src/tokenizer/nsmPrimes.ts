/**
 * @file nsmPrimes.ts
 * @module tokenizer/nsmPrimes
 *
 * NSM Prime Anchors for the Sacred Tongues Alphabet.
 *
 * Wierzbicka's ~65 Natural Semantic Metalanguage primes mapped to the six
 * Sacred Tongue dimensions.  Each prime is assigned:
 *   - a radial position r in the Poincaré ball
 *   - a tongue assignment with confidence score
 *   - a grid position in that tongue's 16×16 token grid
 *
 * The phi-extrapolation engine uses the Riemannian exponential map on the
 * Poincaré disk to derive new prime candidates from known anchors.  At each
 * step the tongue advances one position in phi-order and the walk distance
 * scales by φ.  Derived positions that match known primes confirm the
 * geometry; positions that match nothing are empty lattice sites — predicted
 * concepts not in Wierzbicka's list.
 *
 * Tongue order and phase angles:
 *   KO (φ⁰, 0°)   AV (φ¹, 60°)   RU (φ², 120°)
 *   CA (φ³, 180°)  UM (φ⁴, 240°)  DR (φ⁵, 300°)
 */

import type { TongueCode } from './ss1.js';

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

export const PHI = 1.618033988749895;
export const TONGUE_ORDER: TongueCode[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
export const TONGUE_PHASE: Record<TongueCode, number> = {
  KO: 0,
  AV: Math.PI / 3,
  RU: (2 * Math.PI) / 3,
  CA: Math.PI,
  UM: (4 * Math.PI) / 3,
  DR: (5 * Math.PI) / 3,
};
export const TONGUE_WEIGHT: Record<TongueCode, number> = {
  KO: PHI ** 0,
  AV: PHI ** 1,
  RU: PHI ** 2,
  CA: PHI ** 3,
  UM: PHI ** 4,
  DR: PHI ** 5,
};
const POINCARE_EPSILON = 1e-6;
const GRID_SIZE = 16;

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface PrimeSpan {
  readonly tongue: TongueCode;
  readonly confidence: number; // [0, 1]
  readonly note: string;
}

export interface NSMPrime {
  readonly id: string;
  readonly label: string; // canonical Wierzbicka form
  readonly surfaceForms: readonly string[];
  readonly phiOrder: number; // 0 = most atomic
  readonly r: number; // radial Poincaré position
  readonly gridRow: number;
  readonly gridCol: number;
  readonly spans: readonly PrimeSpan[];
  readonly note?: string;
}

export interface PhiExtrapolation {
  readonly sourceId: string;
  readonly n: number;
  readonly derivedTongue: TongueCode;
  readonly derivedR: number;
  readonly derivedTheta: number;
  readonly gridRow: number;
  readonly gridCol: number;
  readonly candidateLabel: string;
  readonly confidence: number;
  readonly isKnownPrime: boolean;
  readonly matchedPrime: string | null;
}

export interface CoverageReport {
  readonly total: number;
  readonly primaryOnly: number;
  readonly crossTongue: number;
  readonly unspanned: number;
  readonly byTongue: Record<TongueCode, number>;
  readonly crossPairs: Array<{ label: string; t1: TongueCode; t2: TongueCode }>;
  readonly unspannedPrimes: string[];
  readonly notes: string[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function isCrossTongue(p: NSMPrime): boolean {
  return p.spans.length > 1 && p.spans[1].confidence >= 0.25;
}

function primaryTongue(p: NSMPrime): TongueCode {
  return p.spans[0].tongue;
}

function primaryConfidence(p: NSMPrime): number {
  return p.spans[0].confidence;
}

function span(t: TongueCode, c: number, note = ''): PrimeSpan {
  return { tongue: t, confidence: c, note };
}

function prime(
  id: string,
  label: string,
  surfaceForms: string[],
  phiOrder: number,
  r: number,
  gridRow: number,
  gridCol: number,
  spans: PrimeSpan[],
  note?: string
): NSMPrime {
  return {
    id,
    label,
    surfaceForms,
    phiOrder,
    r,
    gridRow,
    gridCol,
    spans,
    ...(note ? { note } : {}),
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Prime table
// ─────────────────────────────────────────────────────────────────────────────

export const NSM_PRIMES: readonly NSMPrime[] = [
  // ── KO: Kor'aelin — Control / Intent ──────────────────────────────────
  prime('ko.i', 'I', ['I', 'me', 'myself'], 0, 0.18, 0, 0, [
    span('KO', 1.0, 'self-reference is pure intent'),
  ]),
  prime('ko.you', 'YOU', ['you', 'thou'], 0, 0.18, 0, 1, [
    span('KO', 1.0, 'second-person address'),
  ]),
  prime('ko.want', 'WANT', ['want', 'desire', 'wish'], 0, 0.22, 0, 2, [
    span('KO', 1.0, 'pure intent prime'),
  ]),
  prime('ko.can', 'CAN', ['can', 'be able to'], 0, 0.24, 0, 3, [
    span('KO', 0.9, 'possibility under agent control'),
    span('RU', 0.1, 'policy permits'),
  ]),
  prime(
    'ko.not',
    'NOT',
    ['not', 'no', 'un-'],
    0,
    0.2,
    0,
    4,
    [
      span('KO', 0.5, 'logical negation of intent'),
      span('RU', 0.3, 'policy violation'),
      span('UM', 0.2, 'absence / containment negation'),
    ],
    'hardest to span — genuinely cross-tongue'
  ),
  prime('ko.maybe', 'MAYBE', ['maybe', 'perhaps', 'possibly'], 1, 0.26, 0, 5, [
    span('KO', 0.8, 'uncertain intent'),
    span('RU', 0.2, 'unresolved policy state'),
  ]),
  prime('ko.if', 'IF', ['if', 'when-conditional'], 1, 0.28, 0, 6, [
    span('KO', 0.6, 'conditional intent'),
    span('RU', 0.4, 'conditional policy binding'),
  ]),
  prime(
    'ko.do',
    'DO',
    ['do', 'act', 'perform'],
    1,
    0.3,
    0,
    7,
    [span('KO', 0.6, 'intentional act'), span('CA', 0.4, 'computational operation')],
    'cross-tongue: DO-as-agency vs DO-as-computation'
  ),
  prime('ko.think', 'THINK', ['think', 'believe', 'consider'], 1, 0.28, 0, 8, [
    span('KO', 0.7, 'thinking as intentional mental act'),
    span('DR', 0.3, 'record of internal states'),
  ]),
  prime('ko.this', 'THIS', ['this', 'here-thing'], 1, 0.24, 0, 9, [
    span('KO', 0.7, 'deictic pointing'),
    span('UM', 0.3, 'this specific contained thing'),
  ]),
  prime('ko.because', 'BECAUSE', ['because', 'therefore', 'hence'], 1, 0.3, 0, 10, [
    span('RU', 0.7, 'causal binding rule'),
    span('KO', 0.3, 'reason for intentional act'),
  ]),

  // ── AV: Avali — Transport / Messaging ─────────────────────────────────
  prime('av.say', 'SAY', ['say', 'speak', 'tell'], 0, 0.18, 1, 0, [
    span('AV', 0.8, 'speech as message transport'),
    span('KO', 0.2, 'saying has intentional origin'),
  ]),
  prime('av.words', 'WORDS', ['words', 'language', 'speech'], 0, 0.2, 1, 1, [
    span('AV', 0.7, 'words are transport medium'),
    span('DR', 0.3, 'words as record / witness'),
  ]),
  prime('av.see', 'SEE', ['see', 'perceive visually'], 0, 0.18, 1, 2, [
    span('AV', 0.8, 'visual information transport'),
    span('DR', 0.2, 'seeing as witnessing'),
  ]),
  prime('av.hear', 'HEAR', ['hear', 'listen'], 0, 0.18, 1, 3, [
    span('AV', 1.0, 'auditory transport — pure AV'),
  ]),
  prime('av.move', 'MOVE', ['move', 'go', 'travel'], 0, 0.22, 1, 4, [
    span('AV', 1.0, 'movement is core transport'),
  ]),
  prime('av.touch', 'TOUCH', ['touch', 'contact', 'reach'], 0, 0.24, 1, 5, [
    span('AV', 0.6, 'physical contact as transport endpoint'),
    span('KO', 0.4, 'touch as intentional act'),
  ]),
  prime('av.happen', 'HAPPEN', ['happen', 'occur', 'take place'], 1, 0.26, 1, 6, [
    span('AV', 0.7, 'event transported through time'),
    span('CA', 0.3, 'state transformation'),
  ]),
  prime('av.here', 'HERE', ['here', 'at this place'], 1, 0.24, 1, 7, [
    span('AV', 0.8, 'reference point in transit space'),
    span('KO', 0.2, 'self-located deixis'),
  ]),
  prime('av.where', 'WHERE/PLACE', ['where', 'place', 'location'], 1, 0.26, 1, 8, [
    span('AV', 0.8, 'location in transit space'),
    span('CA', 0.2, 'coordinate / transform input'),
  ]),
  prime('av.near', 'NEAR', ['near', 'close', 'next to'], 1, 0.28, 1, 9, [
    span('AV', 0.8, 'proximity in transit space'),
    span('CA', 0.2, 'small distance transform'),
  ]),
  prime('av.far', 'FAR', ['far', 'distant', 'away'], 1, 0.28, 1, 10, [
    span('AV', 0.8, 'distance in transit space'),
    span('CA', 0.2, 'large distance transform'),
  ]),
  prime('av.side', 'SIDE', ['side', 'beside', 'adjacent'], 2, 0.3, 1, 11, [
    span('AV', 0.6, 'lateral adjacency'),
    span('CA', 0.4, 'spatial relative transform'),
  ]),
  prime('av.above', 'ABOVE', ['above', 'over', 'on top'], 2, 0.32, 1, 12, [
    span('CA', 0.7, 'vertical spatial transform'),
    span('AV', 0.3, 'elevation in transit space'),
  ]),
  prime('av.below', 'BELOW', ['below', 'under', 'beneath'], 2, 0.32, 1, 13, [
    span('CA', 0.7, 'vertical spatial transform'),
    span('AV', 0.3, 'descent in transit space'),
  ]),

  // ── RU: Runethic — Policy / Binding ───────────────────────────────────
  prime('ru.good', 'GOOD', ['good', 'right', 'correct'], 0, 0.18, 2, 0, [
    span('RU', 0.9, 'evaluative policy — permitted'),
    span('KO', 0.1, 'intentionally chosen'),
  ]),
  prime('ru.bad', 'BAD', ['bad', 'wrong', 'harmful'], 0, 0.18, 2, 1, [
    span('RU', 0.9, 'evaluative policy violation'),
    span('KO', 0.1, 'intentionally avoided'),
  ]),
  prime('ru.true', 'TRUE', ['true', 'real', 'actual'], 0, 0.2, 2, 2, [
    span('DR', 0.9, 'authenticated state'),
    span('RU', 0.1, 'policy of truth-telling'),
  ]),
  prime('ru.all', 'ALL', ['all', 'every', 'entire'], 0, 0.22, 2, 3, [
    span('RU', 0.8, 'universal binding'),
    span('CA', 0.2, 'total count'),
  ]),
  prime('ru.some', 'SOME', ['some', 'a few', 'several'], 0, 0.24, 2, 4, [
    span('RU', 0.6, 'partial policy binding'),
    span('CA', 0.4, 'partial count'),
  ]),
  prime('ru.because2', 'BECAUSE', ['because', 'therefore', 'hence'], 1, 0.26, 2, 5, [
    span('RU', 0.7, 'causal binding rule'),
    span('KO', 0.3, 'causal intent'),
  ]),
  prime('ru.kind_of', 'KIND OF', ['kind of', 'type of', 'sort of'], 1, 0.28, 2, 6, [
    span('RU', 0.8, 'taxonomic policy'),
    span('CA', 0.2, 'classification transform'),
  ]),
  prime('ru.part_of', 'PART OF', ['part of', 'component of'], 1, 0.28, 2, 7, [
    span('RU', 0.7, 'mereological binding'),
    span('AV', 0.3, 'transit node containment'),
  ]),
  prime('ru.like', 'LIKE/AS/WAY', ['like', 'as', 'way', 'similar'], 2, 0.3, 2, 8, [
    span('CA', 0.9, 'similarity transform'),
    span('RU', 0.1, 'similarity as binding rule'),
  ]),

  // ── CA: Cassisivadan — Compute / Transforms ───────────────────────────
  prime('ca.one', 'ONE', ['one', 'a', 'single'], 0, 0.18, 3, 0, [
    span('CA', 1.0, 'unit — atomic count'),
  ]),
  prime('ca.two', 'TWO', ['two', 'pair', 'both'], 0, 0.2, 3, 1, [span('CA', 1.0, 'binary count')]),
  prime('ca.much', 'MUCH/MANY', ['much', 'many', 'a lot'], 0, 0.22, 3, 2, [
    span('CA', 0.8, 'large quantity transform'),
    span('RU', 0.2, 'binding over large set'),
  ]),
  prime('ca.little', 'LITTLE/FEW', ['little', 'few', 'not much'], 0, 0.22, 3, 3, [
    span('CA', 0.8, 'small quantity transform'),
    span('RU', 0.2, 'minimal binding'),
  ]),
  prime('ca.big', 'BIG', ['big', 'large', 'great'], 0, 0.24, 3, 4, [
    span('CA', 1.0, 'size as spatial transform magnitude'),
  ]),
  prime('ca.small', 'SMALL', ['small', 'little', 'tiny'], 0, 0.24, 3, 5, [
    span('CA', 1.0, 'small size transform'),
  ]),
  prime('ca.more', 'MORE', ['more', 'additional', 'further'], 0, 0.26, 3, 6, [
    span('CA', 1.0, 'increment transform'),
  ]),
  prime('ca.very', 'VERY', ['very', 'extremely', 'so'], 1, 0.28, 3, 7, [
    span('CA', 0.8, 'intensity amplification'),
    span('KO', 0.2, 'emphasis of intent'),
  ]),
  prime('ca.same', 'THE SAME', ['same', 'identical', 'equal'], 1, 0.28, 3, 8, [
    span('CA', 0.8, 'identity transform'),
    span('RU', 0.2, 'binding equivalence'),
  ]),
  prime('ca.other', 'OTHER', ['other', 'different', 'else'], 1, 0.3, 3, 9, [
    span('CA', 0.7, 'differentiation transform'),
    span('RU', 0.3, 'policy of exclusion'),
  ]),
  prime('ca.thing', 'SOMETHING', ['something', 'thing', 'object'], 1, 0.26, 3, 10, [
    span('CA', 0.7, 'thing as operable object'),
    span('UM', 0.3, 'thing as containable'),
  ]),

  // ── UM: Umbroth — Redaction / Privacy / Containment ──────────────────
  prime('um.inside', 'INSIDE', ['inside', 'within', 'interior'], 0, 0.18, 4, 0, [
    span('UM', 1.0, 'containment — pure UM prime'),
  ]),
  prime('um.have', 'HAVE', ['have', 'possess', 'own'], 0, 0.22, 4, 1, [
    span('UM', 0.8, 'possession as containment'),
    span('DR', 0.2, 'authenticated ownership record'),
  ]),
  prime('um.there_is', 'THERE IS', ['there is', 'exists', 'is present'], 0, 0.24, 4, 2, [
    span('UM', 0.7, 'existence as presence in container'),
    span('CA', 0.3, 'computable existence fact'),
  ]),
  prime('um.live', 'LIVE', ['live', 'alive', 'exist'], 0, 0.26, 4, 3, [
    span('UM', 0.7, 'contained biological existence'),
    span('DR', 0.3, 'temporally continuous record'),
  ]),
  prime('um.die', 'DIE', ['die', 'dead', 'cease'], 0, 0.26, 4, 4, [
    span('UM', 0.7, 'containment ending'),
    span('DR', 0.3, 'temporal record termination'),
  ]),
  prime('um.body', 'BODY', ['body', 'physical form', 'flesh'], 1, 0.28, 4, 5, [
    span('UM', 0.8, 'body as container of experience'),
    span('AV', 0.2, 'physical mover in space'),
  ]),
  prime(
    'um.feel',
    'FEEL',
    ['feel', 'sense', 'experience'],
    1,
    0.3,
    4,
    6,
    [span('UM', 0.7, 'contained inner experience'), span('KO', 0.3, 'mental-intentional state')],
    'genuinely hard to place — inner experience resists externalization'
  ),
  prime(
    'um.someone',
    'SOMEONE',
    ['someone', 'a person', 'somebody'],
    1,
    0.28,
    4,
    7,
    [span('KO', 0.8, 'intentional agent'), span('AV', 0.2, 'addressable node')],
    'primary tongue is KO — listed for cross-coverage audit'
  ),
  prime(
    'um.people',
    'PEOPLE',
    ['people', 'persons', 'humans'],
    1,
    0.3,
    4,
    8,
    [span('DR', 0.7, 'collective witness / record'), span('AV', 0.3, 'social transit network')],
    'primary tongue is DR'
  ),

  // ── DR: Draumric — Authentication / Integrity / Record ─────────────────
  prime('dr.know', 'KNOW', ['know', 'knowledge', 'aware'], 0, 0.18, 5, 0, [
    span('DR', 0.9, 'authenticated internal record'),
    span('KO', 0.1, 'intentional mental state'),
  ]),
  prime('dr.true2', 'TRUE', ['true', 'real', 'actual'], 0, 0.18, 5, 1, [
    span('DR', 0.9, 'authenticated state'),
    span('RU', 0.1, 'policy requirement'),
  ]),
  prime(
    'dr.words2',
    'WORDS',
    ['words', 'record', 'testimony'],
    0,
    0.2,
    5,
    2,
    [span('DR', 0.7, 'words as record / witness medium'), span('AV', 0.3, 'transport medium')],
    'DR isotope of WORDS — same surface, different tongue aspect'
  ),
  prime('dr.now', 'NOW', ['now', 'at this moment', 'currently'], 0, 0.22, 5, 3, [
    span('DR', 0.8, 'present moment as temporal anchor'),
    span('KO', 0.2, 'deictic self-reference in time'),
  ]),
  prime('dr.before', 'BEFORE', ['before', 'prior to', 'earlier'], 0, 0.24, 5, 4, [
    span('DR', 1.0, 'temporal order — pure DR'),
  ]),
  prime('dr.after', 'AFTER', ['after', 'following', 'later'], 0, 0.24, 5, 5, [
    span('DR', 1.0, 'temporal sequence — pure DR'),
  ]),
  prime('dr.when', 'WHEN/TIME', ['when', 'time', 'temporal'], 0, 0.26, 5, 6, [
    span('DR', 0.9, 'time as domain of record'),
    span('CA', 0.1, 'measurable quantity'),
  ]),
  prime('dr.long', 'A LONG TIME', ['a long time', 'for ages', 'long'], 1, 0.28, 5, 7, [
    span('DR', 0.8, 'extended temporal record'),
    span('CA', 0.2, 'large time quantity'),
  ]),
  prime('dr.short', 'A SHORT TIME', ['a short time', 'briefly'], 1, 0.28, 5, 8, [
    span('DR', 0.8, 'brief temporal record'),
    span('CA', 0.2, 'small time quantity'),
  ]),
  prime('dr.for', 'FOR SOME TIME', ['for some time', 'a while'], 1, 0.3, 5, 9, [
    span('DR', 0.8, 'bounded temporal record'),
    span('RU', 0.2, 'time-bound policy'),
  ]),
  prime('dr.moment', 'MOMENT', ['moment', 'instant', 'point in time'], 1, 0.26, 5, 10, [
    span('DR', 0.9, 'minimal temporal record unit'),
    span('AV', 0.1, 'event point'),
  ]),
  prime('dr.people2', 'PEOPLE', ['people', 'folk', 'witnesses'], 1, 0.3, 5, 11, [
    span('DR', 0.7, 'collective witness / record'),
    span('AV', 0.3, 'social graph'),
  ]),
];

// ─────────────────────────────────────────────────────────────────────────────
// Indexes
// ─────────────────────────────────────────────────────────────────────────────

const _byId = new Map<string, NSMPrime>(NSM_PRIMES.map((p) => [p.id, p]));
const _byTongue = new Map<TongueCode, NSMPrime[]>();
for (const p of NSM_PRIMES) {
  const t = primaryTongue(p);
  const bucket = _byTongue.get(t) ?? [];
  bucket.push(p);
  _byTongue.set(t, bucket);
}

export function getPrime(id: string): NSMPrime | undefined {
  return _byId.get(id);
}

export function primesForTongue(tongue: TongueCode): NSMPrime[] {
  return _byTongue.get(tongue) ?? [];
}

// ─────────────────────────────────────────────────────────────────────────────
// Coverage analysis
// ─────────────────────────────────────────────────────────────────────────────

export function coverageReport(): CoverageReport {
  const byTongue = Object.fromEntries(TONGUE_ORDER.map((t) => [t, 0])) as Record<
    TongueCode,
    number
  >;
  const crossPairs: CoverageReport['crossPairs'] = [];
  const unspannedPrimes: string[] = [];
  let primaryOnly = 0;
  let crossTongue = 0;

  for (const p of NSM_PRIMES) {
    const pt = primaryTongue(p);
    byTongue[pt] = (byTongue[pt] ?? 0) + 1;

    if (isCrossTongue(p)) {
      crossTongue++;
      const tongues = p.spans.filter((s) => s.confidence >= 0.25).map((s) => s.tongue);
      for (let i = 0; i < tongues.length; i++) {
        for (let j = i + 1; j < tongues.length; j++) {
          crossPairs.push({ label: p.label, t1: tongues[i], t2: tongues[j] });
        }
      }
    } else if (primaryConfidence(p) < 0.25) {
      unspannedPrimes.push(p.label);
    } else {
      primaryOnly++;
    }
  }

  return {
    total: NSM_PRIMES.length,
    primaryOnly,
    crossTongue,
    unspanned: unspannedPrimes.length,
    byTongue,
    crossPairs,
    unspannedPrimes,
    notes: [
      'NOT spans KO/RU/UM — may be a meta-prime above the alphabet level',
      'FEEL and THINK resist clean assignment — inner experience is genuinely cross-tongue',
      'BECAUSE appears under KO and RU — causal relation is both intent and policy',
      'TRUE appears under RU and DR — epistemic truth vs authenticated truth are different isotopes',
      'WORDS and PEOPLE appear as isotopes in two tongues each — same surface, different tongue aspect',
    ],
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Grid utilities
// ─────────────────────────────────────────────────────────────────────────────

export function gridIndex(row: number, col: number): number {
  return row * GRID_SIZE + col;
}

export function primeGridIndex(p: NSMPrime): number {
  return gridIndex(p.gridRow, p.gridCol);
}

export function gridPositionForTongue(tongue: TongueCode): Map<number, NSMPrime> {
  return new Map(primesForTongue(tongue).map((p) => [primeGridIndex(p), p]));
}

// ─────────────────────────────────────────────────────────────────────────────
// Phi-extrapolation (Riemannian exponential map on the Poincaré disk)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Riemannian exponential map on the 2D Poincaré disk.
 *
 * exp_x(v): walk from x in direction v by geodesic distance ‖v‖.
 * Returns new Cartesian coordinates (x, y) in the open unit disk.
 *
 * Formula: new_r = tanh(arctanh(r_x) + ‖v‖), direction = angle of v.
 */
function poincareExpMap(x: [number, number], v: [number, number]): [number, number] {
  const xr = Math.min(Math.sqrt(x[0] ** 2 + x[1] ** 2), 1 - POINCARE_EPSILON);
  const vr = Math.sqrt(v[0] ** 2 + v[1] ** 2);
  if (vr < POINCARE_EPSILON) return x;

  const newR = Math.min(Math.tanh(Math.atanh(xr) + vr), 1 - POINCARE_EPSILON);
  const vTheta = Math.atan2(v[1], v[0]);
  return [newR * Math.cos(vTheta), newR * Math.sin(vTheta)];
}

/**
 * Walk the geodesic from `p` for `steps` phi-scaled steps.
 *
 * At each step:
 *   - Tongue advances one position in phi-order cycle (KO→AV→RU→CA→UM→DR→KO)
 *   - Walk distance scales by φ (additive in arctanh / hyperbolic space)
 *   - Direction points at the new tongue's phase angle
 *
 * Resulting positions that match known primes confirm the geometry.
 * Positions that match nothing are empty lattice sites — predicted concepts
 * not in Wierzbicka's list.
 */
export function phiExtrapolate(p: NSMPrime, steps = 3): PhiExtrapolation[] {
  const results: PhiExtrapolation[] = [];
  let tongueIdx = TONGUE_ORDER.indexOf(primaryTongue(p));
  let r = p.r;
  const theta0 = TONGUE_PHASE[primaryTongue(p)];
  let x: [number, number] = [r * Math.cos(theta0), r * Math.sin(theta0)];

  for (let step = 1; step <= steps; step++) {
    tongueIdx = (tongueIdx + 1) % TONGUE_ORDER.length;
    const nextTongue = TONGUE_ORDER[tongueIdx];
    const nextTheta = TONGUE_PHASE[nextTongue];

    const stepMag = PHI * r;
    const v: [number, number] = [stepMag * Math.cos(nextTheta), stepMag * Math.sin(nextTheta)];
    const newX = poincareExpMap(x, v);
    const newR = Math.min(Math.sqrt(newX[0] ** 2 + newX[1] ** 2), 1 - POINCARE_EPSILON);
    const newTheta = Math.atan2(newX[1], newX[0]);

    const gRow = Math.min(Math.floor(newR * GRID_SIZE), GRID_SIZE - 1);
    const gCol =
      Math.floor(
        ((((newTheta % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI)) / (2 * Math.PI)) * GRID_SIZE
      ) % GRID_SIZE;

    const candidates = primesForTongue(nextTongue);
    const knownMatch =
      candidates.find((c) => c.gridRow === gRow && Math.abs(c.r - newR) < 0.08) ?? null;

    results.push({
      sourceId: p.id,
      n: step,
      derivedTongue: nextTongue,
      derivedR: newR,
      derivedTheta: newTheta,
      gridRow: gRow,
      gridCol: gCol,
      candidateLabel: knownMatch?.label ?? `[CANDIDATE: ${nextTongue}·${step}]`,
      confidence: knownMatch ? primaryConfidence(knownMatch) : 0,
      isKnownPrime: knownMatch !== null,
      matchedPrime: knownMatch?.id ?? null,
    });

    x = newX;
    r = newR;
  }

  return results;
}

export function phiExtrapolateAll(steps = 2): Map<string, PhiExtrapolation[]> {
  return new Map(NSM_PRIMES.map((p) => [p.id, phiExtrapolate(p, steps)]));
}

export function findEmptyLatticeSites(steps = 2): PhiExtrapolation[] {
  const empty: PhiExtrapolation[] = [];
  for (const extrapolations of phiExtrapolateAll(steps).values()) {
    for (const ex of extrapolations) {
      if (!ex.isKnownPrime) empty.push(ex);
    }
  }
  return empty;
}
