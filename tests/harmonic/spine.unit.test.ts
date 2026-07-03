/**
 * @file spine.unit.test.ts
 * @component The Spine — 14-segment articulation & detent collapse (L2-unit)
 */

import { describe, expect, it } from 'vitest';
import type { Trit } from '../../src/harmonic/balancedTernary.js';
import { fromBalancedTernary } from '../../src/harmonic/balancedTernary.js';
import {
  AXIOMS,
  SPINE,
  SPINE_LENGTH,
  articulateSpine,
  detentFromDecision,
  formatSpine,
  poseWord,
  segmentOf,
} from '../../src/harmonic/spine.js';

const ALL_HOLD: Trit[] = new Array(14).fill(1) as Trit[];

describe('spine structure', () => {
  it('has 14 segments, layers 1..14 in order, each with a valid axiom', () => {
    expect(SPINE_LENGTH).toBe(14);
    SPINE.forEach((s, i) => {
      expect(s.layer).toBe(i + 1);
      expect(AXIOMS).toContain(s.axiom);
      expect(s.name.length).toBeGreaterThan(0);
    });
  });

  it('maps the Quantum Axiom Mesh exactly', () => {
    const layersOf = (axiom: string) => SPINE.filter((s) => s.axiom === axiom).map((s) => s.layer);
    expect(layersOf('unitarity')).toEqual([2, 4, 7]);
    expect(layersOf('locality')).toEqual([3, 8]);
    expect(layersOf('causality')).toEqual([6, 11, 13]);
    expect(layersOf('symmetry')).toEqual([5, 9, 10, 12]);
    expect(layersOf('composition')).toEqual([1, 14]);
  });

  it('segmentOf looks up by layer and rejects out-of-range', () => {
    expect(segmentOf(5).name).toBe('Hyperbolic Distance');
    expect(() => segmentOf(0)).toThrow(RangeError);
    expect(() => segmentOf(15)).toThrow(RangeError);
  });

  it('detentFromDecision collapses tiers to trits', () => {
    expect(detentFromDecision('ALLOW')).toBe(1);
    expect(detentFromDecision('DENY')).toBe(-1);
    expect(detentFromDecision('QUARANTINE')).toBe(0);
    expect(detentFromDecision('ESCALATE')).toBe(0);
  });
});

describe('articulation', () => {
  it('every joint holding → fully articulated', () => {
    const pose = articulateSpine(ALL_HOLD);
    expect(pose.collapse).toBe(1);
    expect(pose.broken).toBe(false);
    expect(pose.brokenAt).toEqual([]);
    for (const axiom of AXIOMS) expect(pose.axiomRollup[axiom]).toBe(1);
  });

  it('a single broken joint breaks the whole pose and names the axiom', () => {
    const pose = articulateSpine({ 13: -1 }); // L13 = Causality
    expect(pose.collapse).toBe(-1);
    expect(pose.broken).toBe(true);
    expect(pose.brokenAt).toEqual([13]);
    expect(pose.axiomRollup.causality).toBe(-1);
    // Other axioms with no signal default to 0 (uncertain), not broken.
    expect(pose.axiomRollup.unitarity).toBe(0);
  });

  it('all uncertain → holds but uncertain (collapse 0)', () => {
    const pose = articulateSpine(new Array(14).fill(0) as Trit[]);
    expect(pose.collapse).toBe(0);
    expect(pose.broken).toBe(false);
    expect(pose.poseValue).toBe(0);
    expect(pose.cord.toInt()).toBe(0);
  });

  it('accepts a partial per-layer map; unset joints default to uncertain', () => {
    const pose = articulateSpine({ 1: 1, 14: 1 });
    expect(pose.vertebrae[0].detent).toBe(1);
    expect(pose.vertebrae[13].detent).toBe(1);
    expect(pose.vertebrae[6].detent).toBe(0);
    expect(pose.axiomRollup.composition).toBe(1); // L1 & L14 both hold
    expect(pose.collapse).toBe(0); // middle joints uncertain
  });

  it('the negabinary cord encodes the balanced-ternary pose value', () => {
    const pose = articulateSpine(ALL_HOLD);
    expect(pose.poseValue).toBe(fromBalancedTernary(ALL_HOLD));
    expect(pose.cord.toInt()).toBe(pose.poseValue);
    // Signless cord: every digit 0 or 1.
    for (const b of pose.cord.bits) expect(b === 0 || b === 1).toBe(true);
  });

  it('poseWord is a 14-trit balanced-ternary word', () => {
    const word = poseWord(articulateSpine({ 5: 1, 13: -1 }));
    expect(word).toHaveLength(14);
    expect(/^[01T]{14}$/.test(word)).toBe(true);
  });

  it('formatSpine renders the chain, cord, axioms and collapse', () => {
    const text = formatSpine(articulateSpine({ 13: -1 }));
    expect(text).toContain('[L13T]');
    expect(text).toContain('BROKEN');
    expect(text).toContain('causality:T');
    expect(text).toContain('cord (base -2)');
  });
});
