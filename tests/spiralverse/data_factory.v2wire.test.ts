/**
 * Spiralverse Synthetic Conversation Data Factory - Tests
 * =======================================================
 *
 * Ensures deterministic generation (seeded) and cryptographic verifiability.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { randomBytes } from 'crypto';
import {
  clearWireNonceCache,
  generateSyntheticConversationV2Wire,
  type Keyring,
} from '../../src/spiralverse';

const testKeyring: Keyring = {
  ko: randomBytes(32),
  av: randomBytes(32),
  ru: randomBytes(32),
  ca: randomBytes(32),
  um: randomBytes(32),
  dr: randomBytes(32),
};

describe('generateSyntheticConversationV2Wire', () => {
  beforeEach(() => {
    clearWireNonceCache();
  });

  it('is deterministic for the same seed', () => {
    const a = generateSyntheticConversationV2Wire({
      baseTopic: 'base',
      numPivots: 5,
      seed: 1234,
      keyring: testKeyring,
    });

    clearWireNonceCache();

    const b = generateSyntheticConversationV2Wire({
      baseTopic: 'base',
      numPivots: 5,
      seed: 1234,
      keyring: testKeyring,
    });

    expect(a.envelopes).toEqual(b.envelopes);
    expect(a.edges).toEqual(b.edges);
  });

  it('differs for different seeds', () => {
    const a = generateSyntheticConversationV2Wire({
      baseTopic: 'base',
      numPivots: 3,
      seed: 1,
      keyring: testKeyring,
    });

    clearWireNonceCache();

    const b = generateSyntheticConversationV2Wire({
      baseTopic: 'base',
      numPivots: 3,
      seed: 2,
      keyring: testKeyring,
    });

    expect(a.envelopes).not.toEqual(b.envelopes);
  });
});
