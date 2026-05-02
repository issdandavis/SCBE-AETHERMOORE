/**
 * @file tileLang.ts
 * @module kernel/tileLang
 * @layer Layer 1 (composition), Layer 3 (locality / tiling)
 *
 * Map-layer tile addressing ↔ Sacred Tongue lane binding.
 * Every integer grid cell gets a deterministic Lang for routing tags, SS1 envelopes,
 * and voxel lifted addresses — same six tongues as LANGS / Langues metric.
 */

import type { Lang, Voxel6 } from './scbe_voxel_types.js';
import { LANGS } from './scbe_voxel_types.js';

/** Integer cell on a 2D tile grid (maps, TMX layers, UI grids). */
export interface TileCoord {
  readonly row: number;
  readonly col: number;
}

const TILE_KEY_RE = /^tile:(-?\d+):(-?\d+)$/;

/** Canonical string id for logs and cross-talk (stable sort key). */
export function tileKey(row: number, col: number): string {
  return `tile:${row}:${col}`;
}

/** Parse {@link tileKey} output; invalid shapes return null. */
export function parseTileKey(key: string): TileCoord | null {
  const m = TILE_KEY_RE.exec(key.trim());
  if (!m) return null;
  return { row: Number(m[1]), col: Number(m[2]) };
}

/**
 * Diagonal striping: adjacent cells step through tongues; period 6 in each axis.
 * A1: same row/col mod invariants as bijective mod on non-negative indices.
 */
export function langAtTile(row: number, col: number): Lang {
  const n = LANGS.length;
  const r = ((row % n) + n) % n;
  const c = ((col % n) + n) % n;
  return LANGS[(r + c) % n] as Lang;
}

/**
 * Lift a tile (and optional vertical layer) into the first three axes of a 6D voxel.
 * Remaining components default to 0 (caller may fill V, P, S for policy / trust / entropy).
 */
export function tileToVoxel6(row: number, col: number, layer: number = 0): Voxel6 {
  return [row, col, layer, 0, 0, 0];
}

/** Neighbour offsets (4-connect) for locality checks. */
export const TILE_NEIGH4: ReadonlyArray<readonly [number, number]> = [
  [-1, 0],
  [1, 0],
  [0, -1],
  [0, 1],
] as const;

/** Tongues for the 4-neighbourhood of (row,col), in neighbour order. */
export function neighbourLangs(row: number, col: number): Lang[] {
  return TILE_NEIGH4.map(([dr, dc]) => langAtTile(row + dr, col + dc));
}
