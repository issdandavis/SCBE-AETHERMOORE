/**
 * @file voxel_store.test.ts
 * @module governance/voxel_store
 * @layer L13 Risk Decision
 *
 * Tests for hash-based voxel store with Merkle tree integrity.
 */

import { describe, it, expect } from 'vitest';
import { VoxelStore } from '../../src/governance/voxel_store.js';

describe('VoxelStore', () => {
  it('rejects invalid shard counts', () => {
    expect(() => new VoxelStore(0)).toThrow('INVALID_SHARD_COUNT');
    expect(() => new VoxelStore(-1)).toThrow('INVALID_SHARD_COUNT');
    expect(() => new VoxelStore(1.5)).toThrow('INVALID_SHARD_COUNT');
  });

  it('stores and retrieves a voxel by content-addressed ID', () => {
    const store = new VoxelStore(4);
    const data = new Uint8Array([1, 2, 3, 4]);
    const voxel = store.put(data);

    expect(voxel.id).toBeInstanceOf(Uint8Array);
    expect(voxel.id.length).toBe(64); // SHA-512 = 64 bytes
    expect(voxel.data).toEqual(data);
    expect(voxel.shard).toBeGreaterThanOrEqual(0);
    expect(voxel.shard).toBeLessThan(4);

    const retrieved = store.get(voxel.id);
    expect(retrieved).toBeDefined();
    expect(retrieved!.data).toEqual(data);
  });

  it('is idempotent — same content returns same voxel', () => {
    const store = new VoxelStore(4);
    const data = new Uint8Array([10, 20, 30]);
    const first = store.put(data);
    const second = store.put(data);

    expect(first).toBe(second); // same object reference
    expect(store.size()).toBe(1);
  });

  it('distinguishes different content', () => {
    const store = new VoxelStore(4);
    const a = store.put(new Uint8Array([1]));
    const b = store.put(new Uint8Array([2]));

    expect(store.size()).toBe(2);
    expect(a.id).not.toEqual(b.id);
  });

  it('reports has() correctly', () => {
    const store = new VoxelStore(2);
    const voxel = store.put(new Uint8Array([42]));

    expect(store.has(voxel.id)).toBe(true);
    expect(store.has(new Uint8Array(64))).toBe(false);
  });

  it('returns zero root for empty store', () => {
    const store = new VoxelStore(1);
    const root = store.root();

    expect(root).toBeInstanceOf(Uint8Array);
    expect(root.length).toBe(64);
    expect(root.every((b) => b === 0)).toBe(true);
  });

  it('computes a deterministic Merkle root', () => {
    const store = new VoxelStore(4);
    store.put(new Uint8Array([1, 2, 3]));
    store.put(new Uint8Array([4, 5, 6]));

    const root1 = store.root();
    const root2 = store.root();

    expect(root1).toEqual(root2);
    expect(root1.length).toBe(64);
    // Root should not be all zeros (non-empty store)
    expect(root1.some((b) => b !== 0)).toBe(true);
  });

  it('Merkle root changes when content changes', () => {
    const store1 = new VoxelStore(4);
    store1.put(new Uint8Array([1]));
    const root1 = store1.root();

    const store2 = new VoxelStore(4);
    store2.put(new Uint8Array([1]));
    store2.put(new Uint8Array([2]));
    const root2 = store2.root();

    expect(root1).not.toEqual(root2);
  });

  it('handles single-voxel Merkle root', () => {
    const store = new VoxelStore(1);
    const voxel = store.put(new Uint8Array([99]));
    const root = store.root();

    // Single leaf: root is the leaf ID itself
    expect(root).toEqual(voxel.id);
  });

  it('handles odd number of leaves in Merkle tree', () => {
    const store = new VoxelStore(8);
    store.put(new Uint8Array([1]));
    store.put(new Uint8Array([2]));
    store.put(new Uint8Array([3])); // odd leaf count

    const root = store.root();
    expect(root.length).toBe(64);
    expect(root.some((b) => b !== 0)).toBe(true);
  });

  it('assigns shards within valid range', () => {
    const shardCount = 7;
    const store = new VoxelStore(shardCount);
    const shards = new Set<number>();

    for (let i = 0; i < 50; i++) {
      const voxel = store.put(new Uint8Array([i]));
      expect(voxel.shard).toBeGreaterThanOrEqual(0);
      expect(voxel.shard).toBeLessThan(shardCount);
      shards.add(voxel.shard);
    }

    // With 50 items across 7 shards, we expect reasonable distribution
    expect(shards.size).toBeGreaterThanOrEqual(2);
  });
});
