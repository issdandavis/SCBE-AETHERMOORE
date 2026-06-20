/**
 * @file rng.ts
 * @module aethermon/rng
 * @layer Layer 3
 * @component AETHERMON — Deterministic RNG
 *
 * Mulberry32 PRNG. Every game system threads explicit RNG state so a
 * save file (seed included) replays identically — battles, encounters,
 * and variance are all reproducible.
 *
 * A3: Causality — outcomes are deterministic from (state, seed).
 */

/** Mutable RNG handle. */
export interface Rng {
  state: number;
}

/** Create an RNG from a 32-bit seed. */
export function createRng(seed: number): Rng {
  return { state: seed >>> 0 };
}

/** Next float in [0, 1). Advances state (mulberry32). */
export function nextFloat(rng: Rng): number {
  rng.state = (rng.state + 0x6d2b79f5) >>> 0;
  let t = rng.state;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}

/** Integer in [min, max] inclusive. */
export function nextInt(rng: Rng, min: number, max: number): number {
  return min + Math.floor(nextFloat(rng) * (max - min + 1));
}

/** True with probability p. */
export function chance(rng: Rng, p: number): boolean {
  return nextFloat(rng) < p;
}

/** Pick a uniformly random element. Throws on empty array. */
export function pick<T>(rng: Rng, items: readonly T[]): T {
  if (items.length === 0) throw new RangeError('pick() on empty array');
  return items[nextInt(rng, 0, items.length - 1)];
}
