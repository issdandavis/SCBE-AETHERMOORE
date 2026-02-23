import { sha512 } from '@noble/hashes/sha2.js';

export interface StoredVoxel {
  id: Uint8Array;
  shard: number;
  data: Uint8Array;
}

function toHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

function canonicalBytes(data: Uint8Array): Uint8Array {
  return new Uint8Array(data);
}

function hash(data: Uint8Array): Uint8Array {
  return sha512(data);
}

function bytesCompare(a: Uint8Array, b: Uint8Array): number {
  const len = Math.min(a.length, b.length);
  for (let i = 0; i < len; i++) {
    const diff = a[i]! - b[i]!;
    if (diff !== 0) return diff;
  }
  return a.length - b.length;
}

export class VoxelStore {
  private readonly byKey = new Map<string, StoredVoxel>();

  constructor(private readonly shardCount: number) {
    if (!Number.isInteger(shardCount) || shardCount <= 0) {
      throw new Error('INVALID_SHARD_COUNT');
    }
  }

  put(content: Uint8Array): StoredVoxel {
    const canonical = canonicalBytes(content);
    const id = hash(canonical);
    const key = toHex(id);
    const shard = ((id[0] ?? 0) * 256 + (id[1] ?? 0) + (id[2] ?? 0)) % this.shardCount;
    const existing = this.byKey.get(key);
    if (existing) return existing;
    const stored: StoredVoxel = { id, shard, data: canonical };
    this.byKey.set(key, stored);
    return stored;
  }

  get(id: Uint8Array): StoredVoxel | undefined {
    return this.byKey.get(toHex(id));
  }

  has(id: Uint8Array): boolean {
    return this.byKey.has(toHex(id));
  }

  size(): number {
    return this.byKey.size;
  }

  root(): Uint8Array {
    if (this.byKey.size === 0) return new Uint8Array(64);
    const leaves = Array.from(this.byKey.values())
      .map((v) => v.id)
      .sort(bytesCompare);
    return this.merkle(leaves);
  }

  private merkle(level: Uint8Array[]): Uint8Array {
    if (level.length === 1) return level[0]!;
    const next: Uint8Array[] = [];
    for (let i = 0; i < level.length; i += 2) {
      const left = level[i]!;
      const right = level[i + 1] ?? left;
      const merged = new Uint8Array(left.length + right.length);
      merged.set(left, 0);
      merged.set(right, left.length);
      next.push(hash(merged));
    }
    return this.merkle(next);
  }
}

