/**
 * @file sprites.ts
 * @module aethermon/web/sprites
 * @layer Layer 14
 * @component AETHERMON Web — Procedural Pixel-Art Sprites
 *
 * Every species gets a unique, deterministic pixel creature: a mirrored
 * half-grid seeded by the species id (same RNG as the game), colored by
 * its Sacred Tongue with alignment accents. Stage controls canvas size,
 * so evolution visibly *grows* the creature. No image assets — the
 * sprites are math, like everything else in Aethermoore.
 */

import type { SpeciesDef, Stage, TongueCode, Alignment } from '../types.js';
import { createRng, nextFloat, type Rng } from '../rng.js';

/** Canon synesthesia colors per tongue (SYNESTHESIA_MAP hexes). */
export const ELEMENT_HEX: Record<TongueCode, string> = {
  KO: '#DC3C3C',
  AV: '#DCB43C',
  RU: '#3CDC78',
  CA: '#3CDCDC',
  UM: '#5A5AE6',
  DR: '#DC3CDC',
};

/** Alignment accent colors. */
export const ALIGNMENT_HEX: Record<Alignment, string> = {
  AEGIS: '#FFD75A',
  VENOM: '#B05CFF',
  FLUX: '#7AE0FF',
};

/** Sprite grid size (pixels per side) by stage — evolution grows you. */
const STAGE_GRID: Record<Stage, number> = {
  EGG: 12,
  MOTE: 10,
  SPRITE: 12,
  GUARDIAN: 14,
  PARAGON: 16,
  APEX: 18,
};

function hashString(text: string): number {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function shade(hex: string, factor: number): string {
  const n = Number.parseInt(hex.slice(1), 16);
  const channel = (shift: number): number =>
    Math.max(0, Math.min(255, Math.round(((n >> shift) & 0xff) * factor)));
  return `rgb(${channel(16)},${channel(8)},${channel(0)})`;
}

/** A rendered sprite: square pixel grid of CSS colors (null = empty). */
export type SpriteGrid = (string | null)[][];

function emptyGrid(size: number): SpriteGrid {
  return Array.from({ length: size }, () => Array.from({ length: size }, () => null));
}

/** Draw an egg: oval shell with seeded speckles in the element color. */
function eggSprite(species: SpeciesDef, rng: Rng, size: number): SpriteGrid {
  const grid = emptyGrid(size);
  const cx = (size - 1) / 2;
  const cy = size * 0.55;
  const shell = '#EDE7DA';
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = (x - cx) / (size * 0.34);
      const dy = (y - cy) / (size * 0.42);
      if (dx * dx + dy * dy <= 1) {
        grid[y][x] = nextFloat(rng) < 0.22 ? ELEMENT_HEX[species.element] : shell;
      }
    }
  }
  return grid;
}

/**
 * Generate the deterministic sprite for a species. `frame` 0 is the idle
 * pose; frame 1 blinks and shifts a few pixels for a tiny animation.
 */
export function spriteForSpecies(species: SpeciesDef, frame = 0): SpriteGrid {
  const size = STAGE_GRID[species.stage];
  const rng = createRng(hashString(species.id));
  if (species.stage === 'EGG') return eggSprite(species, rng, size);

  const grid = emptyGrid(size);
  const base = ELEMENT_HEX[species.element];
  const dark = shade(base, 0.55);
  const light = shade(base, 1.45);
  const accent = ALIGNMENT_HEX[species.alignment];
  const half = Math.ceil(size / 2);
  const cx = (size - 1) / 2;
  const cy = (size - 1) / 2;

  // Mirrored half-grid body: density shaped by an elliptical mask.
  for (let y = 1; y < size - 1; y++) {
    for (let x = 0; x < half; x++) {
      const dx = (x - cx) / (size * 0.52);
      const dy = (y - cy) / (size * 0.48);
      const mask = 1 - (dx * dx + dy * dy);
      if (mask <= 0) {
        nextFloat(rng); // keep the stream stable regardless of mask
        continue;
      }
      const roll = nextFloat(rng);
      if (roll < mask * 0.92) {
        let color = base;
        if (roll < mask * 0.14) color = accent;
        else if (roll < mask * 0.3) color = light;
        else if (roll > mask * 0.78) color = dark;
        grid[y][x] = color;
        grid[y][size - 1 - x] = color;
      }
    }
  }

  // Eyes: always present, symmetric — they make it a creature.
  const eyeY = Math.round(size * 0.38);
  const eyeX = Math.round(size * 0.3);
  const eyeColor = species.alignment === 'VENOM' ? '#FF3355' : '#141428';
  const blink = frame % 2 === 1;
  grid[eyeY][eyeX] = blink ? dark : eyeColor;
  grid[eyeY][size - 1 - eyeX] = blink ? dark : eyeColor;
  if (!blink && size >= 14) {
    grid[eyeY - 1][eyeX] = '#FFFFFF';
    grid[eyeY - 1][size - 1 - eyeX] = '#FFFFFF';
  }

  // Feet anchors so creatures sit on the ground line.
  const footY = size - 1;
  const footX = Math.round(size * 0.32);
  grid[footY][footX] = dark;
  grid[footY][size - 1 - footX] = dark;

  // APEX creatures get a crown row.
  if (species.stage === 'APEX') {
    const crownY = 0;
    for (const cxp of [Math.round(size * 0.3), Math.round(cx), Math.round(size * 0.7) - 1]) {
      grid[crownY][cxp] = accent;
    }
  }
  return grid;
}

/** Paint a sprite grid onto a canvas, pixel-perfect and upscaled. */
export function drawSprite(canvas: HTMLCanvasElement, grid: SpriteGrid, scale = 8): void {
  const size = grid.length;
  canvas.width = size * scale;
  canvas.height = size * scale;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const color = grid[y][x];
      if (!color) continue;
      ctx.fillStyle = color;
      ctx.fillRect(x * scale, y * scale, scale, scale);
    }
  }
}
