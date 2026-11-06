/**
 * @file nestedPatchAttention.ts
 * @module harmonic/nestedPatchAttention
 * @layer Layer 4, Layer 5, Layers 1-14
 * @component Nested patch attention
 *
 * Attention length is the patch. A long patch stays one block until a density
 * break splits it, and the children are the nested blocks. Each block is placed
 * by the existing Layer 4 Poincaré map, denser blocks closer to the origin.
 * The six tongue views are a scatter around that point. The same six-view
 * array is then dressed by scbe14LayerPipeline.
 *
 * Layer 4 and Layer 5 stay the primary maps. This module does not replace d_H.
 */

import { TONGUE_LABELS, type TongueLabel } from './gyroscopicInterlattice.js';
import {
  layer4PoincareEmbedding,
  layer5HyperbolicDistance,
  mobiusAdd,
  scbe14LayerPipeline,
  type Pipeline14Result,
} from './pipeline14.js';

export const TOKEN_VIEWS: readonly TongueLabel[] = TONGUE_LABELS;
const VIEW_COUNT = TOKEN_VIEWS.length;
const EPS_BALL = 0.01;
const MAX_DEPTH = 8;

export interface ViewToken {
  /** One number per tongue, in KO, AV, RU, CA, UM, DR order. */
  views: number[];
}

export interface AttentionRow {
  /** Token index in the patch. A block summary uses the block start and scope 'block'. */
  query: number;
  scope: 'token' | 'block';
  keys: number[];
  weights: number[];
}

export interface DensityRegion {
  start: number;
  end: number;
  depth: number;
  density: number;
  /** Mean of the six tongue views. This is the array the scatter sits around. */
  views: number[];
  center: number[];
  /** Six points, one per tongue, around `center`. */
  scatter: number[][];
  dressed: Pipeline14Result;
}

export interface NestedPatch {
  tokenCount: number;
  attention: AttentionRow[];
  /** Dense regions first. */
  regions: DensityRegion[];
  /** Layer 5 distance between the densest region and the sparsest. Zero for one region. */
  spanDistance: number;
}

interface Block {
  start: number;
  end: number;
  depth: number;
  density: number;
  views: number[];
  children: Block[];
}

function assertToken(token: ViewToken, index: number): void {
  if (!token || !Array.isArray(token.views) || token.views.length !== VIEW_COUNT) {
    throw new RangeError(`Token ${index} needs ${VIEW_COUNT} tongue views`);
  }
  if (token.views.some((value) => !Number.isFinite(value))) {
    throw new RangeError(`Token ${index} has a non-finite view`);
  }
}

function meanViews(tokens: ViewToken[], start: number, end: number): number[] {
  const views = new Array(VIEW_COUNT).fill(0);
  const width = end - start;
  for (let i = start; i < end; i++) {
    for (let k = 0; k < VIEW_COUNT; k++) views[k] += tokens[i].views[k];
  }
  return views.map((value) => value / width);
}

function mass(views: number[]): number {
  return Math.hypot(...views);
}

function splitAt(tokens: ViewToken[], start: number, end: number): number | null {
  if (end - start < 2) return null;
  const gaps: number[] = [];
  for (let i = start + 1; i < end; i++) {
    gaps.push(Math.abs(mass(tokens[i].views) - mass(tokens[i - 1].views)));
  }
  const ordered = [...gaps].sort((a, b) => a - b);
  const median = ordered[Math.floor(ordered.length / 2)];
  let bestAt = -1;
  let bestGap = -1;
  for (let i = 0; i < gaps.length; i++) {
    if (gaps[i] > bestGap) {
      bestGap = gaps[i];
      bestAt = start + 1 + i;
    }
  }
  if (bestGap <= 0 || bestGap < 2 * median) return null;
  return bestAt;
}

function buildBlock(tokens: ViewToken[], start: number, end: number, depth: number): Block {
  const views = meanViews(tokens, start, end);
  const density = mass(views);
  const cut = depth >= MAX_DEPTH ? null : splitAt(tokens, start, end);
  const children =
    cut === null
      ? []
      : [buildBlock(tokens, start, cut, depth + 1), buildBlock(tokens, cut, end, depth + 1)];
  return { start, end, depth, density, views, children };
}

function flatten(block: Block, out: Block[]): void {
  out.push(block);
  for (const child of block.children) flatten(child, out);
}

function softmax(logits: number[]): number[] {
  const peak = Math.max(...logits);
  const lifted = logits.map((value) => Math.exp(value - peak));
  const total = lifted.reduce((sum, value) => sum + value, 0) || 1;
  return lifted.map((value) => value / total);
}

function score(left: number[], right: number[]): number {
  let dot = 0;
  for (let i = 0; i < VIEW_COUNT; i++) dot += left[i] * right[i];
  return dot / Math.sqrt(VIEW_COUNT);
}

function attendBlock(tokens: ViewToken[], block: Block, rows: AttentionRow[]): void {
  if (block.children.length === 0) {
    for (let query = block.start; query < block.end; query++) {
      const keys: number[] = [];
      const logits: number[] = [];
      for (let key = block.start; key < block.end; key++) {
        keys.push(key);
        logits.push(score(tokens[query].views, tokens[key].views));
      }
      rows.push({ query, scope: 'token', keys, weights: softmax(logits) });
    }
    return;
  }
  const keys = block.children.map((child) => child.start);
  const logits = block.children.map((child) => score(block.views, child.views));
  rows.push({ query: block.start, scope: 'block', keys, weights: softmax(logits) });
  for (const child of block.children) attendBlock(tokens, child, rows);
}

/** Radial slot before Layer 4. Rank 0 is the densest region. */
export function placementRadius(rank: number, count: number): number {
  if (count <= 1) return 0.35;
  return 0.15 + (0.7 * rank) / (count - 1);
}

function placementPreimage(views: number[], rank: number, count: number): number[] {
  const norm = mass(views);
  const unit =
    norm < 1e-12
      ? views.map((_, index) => (index === 0 ? 1 : 0))
      : views.map((value) => value / norm);
  const radius = placementRadius(rank, count);
  return unit.map((value) => value * radius);
}

function scatterAround(center: number[], views: number[]): number[][] {
  return views.map((value, index) => {
    const angle = (2 * Math.PI * index) / VIEW_COUNT;
    const scale = 0.05 * Math.tanh(Math.abs(value));
    const offset = new Array(center.length).fill(0);
    offset[0] = scale * Math.cos(angle);
    offset[1] = scale * Math.sin(angle);
    return layer4PoincareEmbedding(mobiusAdd(center, offset), 1, EPS_BALL);
  });
}

function dressViews(views: number[]): Pipeline14Result {
  const features: number[] = [];
  for (let i = 0; i < VIEW_COUNT; i++) features.push(views[i]);
  for (let i = 0; i < VIEW_COUNT; i++) features.push((2 * Math.PI * i) / VIEW_COUNT);
  return scbe14LayerPipeline(features, { D: VIEW_COUNT });
}

/**
 * Read a variable-length patch. Long patches nest only where token density breaks.
 * Regions are sorted dense to sparse, scattered by the six tongue views, and dressed
 * through all 14 layers.
 */
export function dressPatchForModels(tokens: ViewToken[]): NestedPatch {
  if (!Array.isArray(tokens) || tokens.length === 0) {
    throw new RangeError('A patch needs at least one token');
  }
  tokens.forEach(assertToken);

  const root = buildBlock(tokens, 0, tokens.length, 0);
  const blocks: Block[] = [];
  flatten(root, blocks);
  const ranked = [...blocks].sort((a, b) => b.density - a.density || a.start - b.start);

  const attention: AttentionRow[] = [];
  attendBlock(tokens, root, attention);

  const regions = ranked.map((block, rank) => {
    const center = layer4PoincareEmbedding(
      placementPreimage(block.views, rank, ranked.length),
      1,
      EPS_BALL
    );
    return {
      start: block.start,
      end: block.end,
      depth: block.depth,
      density: block.density,
      views: block.views,
      center,
      scatter: scatterAround(center, block.views),
      dressed: dressViews(block.views),
    };
  });

  const spanDistance =
    regions.length > 1
      ? layer5HyperbolicDistance(regions[0].center, regions[regions.length - 1].center)
      : 0;

  return { tokenCount: tokens.length, attention, regions, spanDistance };
}
