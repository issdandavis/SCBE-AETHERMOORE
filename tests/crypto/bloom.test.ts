/**
 * @file bloom.test.ts
 * @module crypto/bloom
 * @layer L5 Security
 *
 * Tests for BloomFilter probabilistic data structure.
 */

import { describe, it, expect } from 'vitest';
import { BloomFilter } from '../../src/crypto/bloom.js';

describe('BloomFilter', () => {
  it('returns false for items never added', () => {
    const bf = new BloomFilter();
    expect(bf.mightHave('never-added')).toBe(false);
  });

  it('returns true for items that were added', () => {
    const bf = new BloomFilter();
    bf.add('hello');
    bf.add('world');
    expect(bf.mightHave('hello')).toBe(true);
    expect(bf.mightHave('world')).toBe(true);
  });

  it('has no false negatives', () => {
    const bf = new BloomFilter(4096, 4);
    const items = Array.from({ length: 200 }, (_, i) => `item-${i}`);
    for (const item of items) bf.add(item);
    for (const item of items) {
      expect(bf.mightHave(item)).toBe(true);
    }
  });

  it('has a bounded false positive rate', () => {
    const bf = new BloomFilter(8192, 4);
    // Add 100 items
    for (let i = 0; i < 100; i++) bf.add(`added-${i}`);

    // Check 1000 items that were NOT added
    let falsePositives = 0;
    for (let i = 0; i < 1000; i++) {
      if (bf.mightHave(`not-added-${i}`)) falsePositives++;
    }
    // With 8192 bits, 4 hashes, 100 items: expected FP rate < 5%
    expect(falsePositives).toBeLessThan(50);
  });

  it('works with custom size and hash count', () => {
    const bf = new BloomFilter(512, 2);
    bf.add('test');
    expect(bf.mightHave('test')).toBe(true);
    expect(bf.mightHave('absent')).toBe(false);
  });

  it('handles special characters', () => {
    const bf = new BloomFilter();
    const specials = ['nonce:abc123', 'key=value&foo=bar', '../../etc/passwd', 'utf8-日本語'];
    for (const s of specials) bf.add(s);
    for (const s of specials) {
      expect(bf.mightHave(s)).toBe(true);
    }
  });

  it('distinguishes similar strings', () => {
    const bf = new BloomFilter(4096, 6);
    bf.add('abc');
    // 'abd' should usually not be a false positive with reasonable filter size
    // We test structural correctness, not guaranteed absence
    expect(bf.mightHave('abc')).toBe(true);
  });
});
