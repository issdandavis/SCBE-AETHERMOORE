/**
 * @file immutable_laws.test.ts
 * @module governance/immutable_laws
 * @layer L13 Governance
 *
 * Tests for ImmutableLaws creation and SHA-512 hash verification.
 * A2: Unitarity check — hash integrity must be preserved.
 */

import { describe, it, expect } from 'vitest';
import { createImmutableLaws, verifyImmutableLawsHash } from '../../src/governance/immutable_laws.js';

function samplePayload() {
  return {
    metric_signature: 'poincare-ball-d5',
    tongues_set: ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as readonly string[],
    geometry_model: 'hyperbolic',
    layer_behaviors: { 1: 'realify', 5: 'distance', 12: 'harmonic-wall' } as Readonly<
      Record<number, string>
    >,
  };
}

describe('ImmutableLaws', () => {
  describe('createImmutableLaws', () => {
    it('creates laws with a SHA-512 hash (64 bytes)', () => {
      const laws = createImmutableLaws(samplePayload());
      expect(laws.laws_hash).toBeInstanceOf(Uint8Array);
      expect(laws.laws_hash.length).toBe(64);
    });

    it('preserves all input fields', () => {
      const payload = samplePayload();
      const laws = createImmutableLaws(payload);
      expect(laws.metric_signature).toBe(payload.metric_signature);
      expect(laws.tongues_set).toEqual(payload.tongues_set);
      expect(laws.geometry_model).toBe(payload.geometry_model);
      expect(laws.layer_behaviors).toEqual(payload.layer_behaviors);
    });

    it('is deterministic — same input yields same hash', () => {
      const a = createImmutableLaws(samplePayload());
      const b = createImmutableLaws(samplePayload());
      expect(Buffer.from(a.laws_hash).toString('hex')).toBe(
        Buffer.from(b.laws_hash).toString('hex')
      );
    });

    it('different inputs produce different hashes', () => {
      const a = createImmutableLaws(samplePayload());
      const b = createImmutableLaws({
        ...samplePayload(),
        metric_signature: 'euclidean-flat',
      });
      expect(Buffer.from(a.laws_hash).toString('hex')).not.toBe(
        Buffer.from(b.laws_hash).toString('hex')
      );
    });
  });

  describe('verifyImmutableLawsHash', () => {
    it('returns true for unmodified laws', () => {
      const laws = createImmutableLaws(samplePayload());
      expect(verifyImmutableLawsHash(laws)).toBe(true);
    });

    it('returns false when metric_signature is tampered', () => {
      const laws = createImmutableLaws(samplePayload());
      const tampered = { ...laws, metric_signature: 'tampered-metric' };
      expect(verifyImmutableLawsHash(tampered)).toBe(false);
    });

    it('returns false when tongues_set is tampered', () => {
      const laws = createImmutableLaws(samplePayload());
      const tampered = { ...laws, tongues_set: ['KO', 'EVIL'] as readonly string[] };
      expect(verifyImmutableLawsHash(tampered)).toBe(false);
    });

    it('returns false when geometry_model is tampered', () => {
      const laws = createImmutableLaws(samplePayload());
      const tampered = { ...laws, geometry_model: 'flat' };
      expect(verifyImmutableLawsHash(tampered)).toBe(false);
    });

    it('returns false when layer_behaviors is tampered', () => {
      const laws = createImmutableLaws(samplePayload());
      const tampered = {
        ...laws,
        layer_behaviors: { 1: 'noop' } as Readonly<Record<number, string>>,
      };
      expect(verifyImmutableLawsHash(tampered)).toBe(false);
    });

    it('returns false when hash bytes are corrupted', () => {
      const laws = createImmutableLaws(samplePayload());
      const corrupt = new Uint8Array(laws.laws_hash);
      corrupt[0] ^= 0xff;
      const tampered = { ...laws, laws_hash: corrupt };
      expect(verifyImmutableLawsHash(tampered)).toBe(false);
    });

    it('returns false when hash length is wrong', () => {
      const laws = createImmutableLaws(samplePayload());
      const tampered = { ...laws, laws_hash: new Uint8Array(32) };
      expect(verifyImmutableLawsHash(tampered)).toBe(false);
    });
  });
});
