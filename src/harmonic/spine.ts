/**
 * @file spine.ts
 * @module harmonic/spine
 * @layer Layer 1 … Layer 14 (all)
 * @component The Spine — articulated 14-layer backbone
 * @version 1.0.0
 *
 * "How do the layers fit together?" — the way a rainbow articulated slug
 * fits together. A fixed chain of distinct segments joined by ratcheting
 * detents: modular, but coupled; it flexes and *holds a pose* instead of
 * fusing rigid or falling apart.
 *
 * This module wires that structure over the canonical 14-layer pipeline:
 *
 *   • The **cord** (signless backbone) is negabinary (base -2). Its
 *     alternating per-bit polarity is the single thread that runs through
 *     every segment and binds the chain — see negabinary.ts.
 *   • Each **segment** is a layer (L1…L14), governed by exactly one of the
 *     five axioms (Unitarity / Locality / Causality / Symmetry /
 *     Composition) — the axiom is the *detent* at that joint.
 *   • Each **detent** is a balanced-ternary trit: +1 ALLOW (joint holds),
 *     0 uncertain, -1 DENY (joint failed its axiom → the pose breaks).
 *
 * Articulating the spine threads a pose (14 trits) into a signless cord
 * and reads back: the whole-spine collapse (does it fit together right
 * now?), which axiom is the weakest joint, and the net tongue polarity.
 *
 * This is the discrete half of the Five Duals — "quorum governs
 * irreversibility." The continuous state vector bends; the spine clicks.
 *
 * @see src/harmonic/negabinary.ts   — the signless cord primitive
 * @see src/harmonic/balancedTernary.ts — the detent alphabet
 * @see docs/LAYER_INDEX.md          — the 14 layers
 */

import type { TongueCode } from '../tokenizer/index.js';
import {
  type Trit,
  fromBalancedTernary,
  governanceToTrit,
  toBalancedTernary,
} from './balancedTernary.js';
import { NegaBinary } from './negabinary.js';

// ---------------------------------------------------------------------------
//  Axioms (the five detent kinds) and the 14 segments
// ---------------------------------------------------------------------------

/** The five Quantum Axioms — one governs each joint. */
export type AxiomName = 'unitarity' | 'locality' | 'causality' | 'symmetry' | 'composition';

/** All axioms, in canonical order. */
export const AXIOMS: readonly AxiomName[] = [
  'unitarity',
  'locality',
  'causality',
  'symmetry',
  'composition',
] as const;

/** Governance decision tiers, collapsed to a detent by {@link detentFromDecision}. */
export type Decision = 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';

/** One segment of the spine: a layer and the axiom that clicks it into place. */
export interface SpineSegment {
  /** Layer number 1..14. */
  readonly layer: number;
  /** Human-readable layer name (from the Layer Index). */
  readonly name: string;
  /** The axiom governing this joint — its detent kind. */
  readonly axiom: AxiomName;
}

/**
 * The 14 segments in pipeline order, each mapped to its axiom (the Quantum
 * Axiom Mesh from CLAUDE.md):
 *   Unitarity   → L2, L4, L7   (norm preservation)
 *   Locality    → L3, L8       (spatial bounds)
 *   Causality   → L6, L11, L13 (time ordering)
 *   Symmetry    → L5, L9, L10, L12 (gauge invariance)
 *   Composition → L1, L14      (pipeline integrity)
 */
export const SPINE: readonly SpineSegment[] = [
  { layer: 1, name: 'Complex Context State', axiom: 'composition' },
  { layer: 2, name: 'Realification', axiom: 'unitarity' },
  { layer: 3, name: 'Weighted Transform', axiom: 'locality' },
  { layer: 4, name: 'Poincaré Embedding', axiom: 'unitarity' },
  { layer: 5, name: 'Hyperbolic Distance', axiom: 'symmetry' },
  { layer: 6, name: 'Breathing Transform', axiom: 'causality' },
  { layer: 7, name: 'Phase Transform', axiom: 'unitarity' },
  { layer: 8, name: 'Multi-Well Realms', axiom: 'locality' },
  { layer: 9, name: 'Spectral Coherence', axiom: 'symmetry' },
  { layer: 10, name: 'Spin Coherence', axiom: 'symmetry' },
  { layer: 11, name: 'Triadic Distance', axiom: 'causality' },
  { layer: 12, name: 'Harmonic Scaling', axiom: 'symmetry' },
  { layer: 13, name: 'Decision & Risk', axiom: 'causality' },
  { layer: 14, name: 'Audio Axis', axiom: 'composition' },
] as const;

/** Number of vertebrae in the spine. */
export const SPINE_LENGTH = SPINE.length;

/** Segment lookup by layer number; throws on an out-of-range layer. */
export function segmentOf(layer: number): SpineSegment {
  const segment = SPINE.find((s) => s.layer === layer);
  if (!segment) throw new RangeError(`No spine segment for layer ${layer} (expected 1..14)`);
  return segment;
}

// ---------------------------------------------------------------------------
//  Detents
// ---------------------------------------------------------------------------

/** Collapse a governance decision to a detent trit (ALLOW +1 / DENY -1 / else 0). */
export function detentFromDecision(decision: Decision): Trit {
  return governanceToTrit(decision);
}

/** Input to {@link articulateSpine}: an ordered trit list or a per-layer map. */
export type SpineInput = readonly Trit[] | Readonly<Partial<Record<number, Trit>>>;

/** A segment plus the detent it is currently holding. */
export interface Vertebra extends SpineSegment {
  detent: Trit;
}

/** The result of articulating the spine into a pose. */
export interface SpinePose {
  /** The 14 segments, each with its detent. */
  readonly vertebrae: Vertebra[];
  /** The pose: 14 detents in layer order. */
  readonly pose: Trit[];
  /** Signless negabinary backbone (pose value → base -2). */
  readonly cord: NegaBinary;
  /** The pose read as a single balanced-ternary integer. */
  readonly poseValue: number;
  /** Net polarity of the cord. */
  readonly polarity: 'positive' | 'negative' | 'balanced';
  /** Tongue affinity implied by the cord polarity (KO / AV / RU). */
  readonly tongue: TongueCode;
  /** Weakest detent per axiom (a -1 anywhere dominates that axiom). */
  readonly axiomRollup: Record<AxiomName, Trit>;
  /** Whole-spine collapse: +1 fully articulated, 0 holds-uncertain, -1 broken. */
  readonly collapse: Trit;
  /** True if any joint failed its axiom (a detent of -1). */
  readonly broken: boolean;
  /** Layer numbers whose joint is broken (detent -1). */
  readonly brokenAt: number[];
}

function normalizeDetents(input: SpineInput): Trit[] {
  const detents: Trit[] = new Array(SPINE_LENGTH).fill(0) as Trit[];
  if (Array.isArray(input)) {
    for (let i = 0; i < SPINE_LENGTH; i++) {
      const t = (input as readonly Trit[])[i];
      if (t !== undefined) detents[i] = t;
    }
  } else {
    const map = input as Partial<Record<number, Trit>>;
    for (let i = 0; i < SPINE_LENGTH; i++) {
      const t = map[SPINE[i].layer];
      if (t !== undefined) detents[i] = t;
    }
  }
  return detents;
}

/**
 * Articulate the spine from a set of per-layer detents into a pose.
 *
 * Threads the pose (14 trits) into an integer, encodes it as the signless
 * negabinary cord, and reads back the whole-spine collapse plus per-axiom
 * diagnostics. A single broken joint (detent -1) breaks the whole pose —
 * that is what "the layers don't fit together" looks like, and the
 * axiomRollup names which axiom gave way.
 *
 * @example
 *   // Every joint holds → fully articulated.
 *   articulateSpine(new Array(14).fill(1)).collapse === 1
 *
 *   // L13 (Causality) denies → the spine is broken there.
 *   const pose = articulateSpine({ 13: -1 });
 *   pose.collapse === -1;
 *   pose.brokenAt === [13];
 *   pose.axiomRollup.causality === -1;
 */
export function articulateSpine(input: SpineInput): SpinePose {
  const pose = normalizeDetents(input);
  const vertebrae: Vertebra[] = SPINE.map((segment, i) => ({ ...segment, detent: pose[i] }));

  // The signless cord: the pose read as a balanced-ternary integer, then
  // represented in negabinary. Its alternating polarity binds the chain.
  const poseValue = fromBalancedTernary(pose);
  const cord = NegaBinary.fromInt(poseValue);
  const { polarity } = cord.polarityProfile();

  // Per-axiom rollup: the weakest joint (min trit) of each axiom's layers.
  const axiomRollup = {} as Record<AxiomName, Trit>;
  for (const axiom of AXIOMS) {
    const detents = vertebrae.filter((v) => v.axiom === axiom).map((v) => v.detent);
    axiomRollup[axiom] = (detents.length ? (Math.min(...detents) as Trit) : 0) as Trit;
  }

  const brokenAt = vertebrae.filter((v) => v.detent === -1).map((v) => v.layer);
  const broken = brokenAt.length > 0;
  const allHold = pose.every((t) => t === 1);
  const collapse: Trit = broken ? -1 : allHold ? 1 : 0;

  return {
    vertebrae,
    pose,
    cord,
    poseValue,
    polarity,
    tongue: cord.tonguePolarity(),
    axiomRollup,
    collapse,
    broken,
    brokenAt,
  };
}

// ---------------------------------------------------------------------------
//  Display
// ---------------------------------------------------------------------------

const DETENT_GLYPH: Record<string, string> = { '1': '+', '0': '·', '-1': 'T' };

/** Render a pose as a human-readable articulated slug. */
export function formatSpine(pose: SpinePose): string {
  const chain = pose.vertebrae
    .map((v) => `[L${v.layer}${DETENT_GLYPH[String(v.detent)]}]`)
    .join('-');
  const collapseWord =
    pose.collapse === 1 ? 'ARTICULATED' : pose.collapse === -1 ? 'BROKEN' : 'HOLDING';
  const rollup = AXIOMS.map((a) => `${a}:${DETENT_GLYPH[String(pose.axiomRollup[a])]}`).join('  ');
  return [
    'SCBE Spine — 14 segments on a negabinary cord',
    '',
    `  ${chain}`,
    '',
    `  cord (base -2): ${pose.cord.toString()}   value: ${pose.poseValue}`,
    `  polarity: ${pose.polarity}   tongue: ${pose.tongue}`,
    `  axioms:   ${rollup}`,
    `  collapse: ${DETENT_GLYPH[String(pose.collapse)]} ${collapseWord}` +
      (pose.broken ? `  (broken at L${pose.brokenAt.join(', L')})` : ''),
    '',
  ].join('\n');
}

// ---------------------------------------------------------------------------
//  Convenience: encode / decode a pose as a compact word
// ---------------------------------------------------------------------------

/** Encode a pose as a balanced-ternary string (e.g. "11T0…"), MST first. */
export function poseWord(pose: SpinePose): string {
  return toBalancedTernary(pose.poseValue, SPINE_LENGTH)
    .trits.map((t) => (t === -1 ? 'T' : String(t)))
    .join('');
}
