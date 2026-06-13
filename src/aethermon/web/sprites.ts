/**
 * @file sprites.ts
 * @module aethermon/web/sprites
 * @layer Layer 14
 * @component AETHERMON Web — Procedural Pixel-Art Sprites (v2)
 *
 * Every species gets a deterministic pixel creature with a real
 * silhouette: each species maps to a body archetype (blob, biped,
 * winged, drake, golem, wisp) whose parametric mask shapes the body;
 * seeded noise only textures the inside. A dark outline pass and
 * top-light shading make the creatures read at a glance, wings flap and
 * wisps flicker between animation frames, VENOM creatures grow horns,
 * and APEX creatures wear crowns. Stage controls grid size, so
 * evolution visibly grows the creature. No image assets — the sprites
 * are math, like everything else in Aethermoore.
 */

import type { Alignment, SpeciesDef, Stage, TongueCode } from '../types.js';
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

/**
 * Sprite grid size (pixels per side) by stage — non-decreasing, so a
 * hatchling never shrinks and every evolution visibly grows.
 */
const STAGE_GRID: Record<Stage, number> = {
  EGG: 10,
  MOTE: 12,
  SPRITE: 14,
  GUARDIAN: 16,
  PARAGON: 18,
  APEX: 20,
};

/** Body archetypes — the silhouette language of Aethermoore fauna. */
export type BodyArchetype = 'blob' | 'biped' | 'winged' | 'drake' | 'golem' | 'wisp';

/** Hand-assigned archetype per species (fallback: blob). */
const SPECIES_ARCHETYPE: Record<string, BodyArchetype> = {
  // Motes
  kindlemote: 'blob',
  glimmote: 'blob',
  shademote: 'blob',
  galewing: 'winged',
  // Sprites
  pyreling: 'biped',
  gnashling: 'drake',
  bitling: 'golem',
  runeling: 'golem',
  veilkit: 'biped',
  gloomkit: 'drake',
  zephyrkit: 'winged',
  squallkin: 'winged',
  // Guardians
  blazewarden: 'biped',
  ashrevenant: 'wisp',
  vexmaw: 'drake',
  cipherwarden: 'biped',
  glitchfiend: 'wisp',
  runewarden: 'golem',
  umbrawarden: 'golem',
  nullshade: 'wisp',
  skywarden: 'winged',
  stormherald: 'winged',
  fracture_shade: 'wisp',
  // Paragons
  solarchon: 'biped',
  chaosdrake: 'drake',
  oraclemind: 'wisp',
  aegisgolem: 'golem',
  duskmonarch: 'biped',
  zephyrarchon: 'winged',
  tempest_regent: 'winged',
  paradox_wraith: 'wisp',
  // Apexes
  radiant_sovereign: 'biped',
  lattice_sovereign: 'golem',
  void_sovereign: 'drake',
  storm_sovereign: 'winged',
};

/** Archetype for a species id. */
export function archetypeFor(speciesId: string): BodyArchetype {
  return SPECIES_ARCHETYPE[speciesId] ?? 'blob';
}

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

// ---------------------------------------------------------------------------
//  Silhouette masks — (u, v) in [0,1]² over the LEFT half (mirrored)
// ---------------------------------------------------------------------------

function inEllipse(u: number, v: number, cu: number, cv: number, ru: number, rv: number): boolean {
  const du = (u - cu) / ru;
  const dv = (v - cv) / rv;
  return du * du + dv * dv <= 1;
}

/**
 * Archetype silhouette for the left half of the grid. `frame` animates
 * wings (up/down) and wisp tendrils. `jitter` is a stable per-species
 * random in [0,1) that varies proportions within an archetype.
 */
function inSilhouette(
  archetype: BodyArchetype,
  u: number,
  v: number,
  frame: number,
  jitter: number
): boolean {
  const flap = frame % 2 === 0 ? 0.06 : -0.08;
  switch (archetype) {
    case 'blob':
      return inEllipse(u, v, 0.5, 0.56, 0.4 + jitter * 0.08, 0.36 + jitter * 0.06);
    case 'biped': {
      const head = inEllipse(u, v, 0.5, 0.24, 0.22 + jitter * 0.05, 0.16);
      const torso = inEllipse(u, v, 0.5, 0.58, 0.26 + jitter * 0.06, 0.26);
      const arm = inEllipse(u, v, 0.2, 0.55 + flap * 0.5, 0.09, 0.18);
      const leg = u > 0.3 && u < 0.46 && v > 0.78 && v < 0.97;
      return head || torso || arm || leg;
    }
    case 'winged': {
      const body = inEllipse(u, v, 0.5, 0.55, 0.2, 0.24 + jitter * 0.05);
      const head = inEllipse(u, v, 0.5, 0.3, 0.15, 0.12);
      const wing = inEllipse(u, v, 0.16, 0.42 + flap, 0.17, 0.3 + (frame % 2) * 0.06);
      const tail = u > 0.42 && v > 0.78 && v < 0.94 && (u + v) % 0.2 > 0.04;
      return body || head || wing || tail;
    }
    case 'drake': {
      const head = inEllipse(u, v, 0.5, 0.3, 0.3, 0.2);
      const jaw = v > 0.42 && v < 0.52 && u > 0.18;
      const haunch = inEllipse(u, v, 0.42, 0.72, 0.34, 0.2);
      const hornSpike = v < 0.14 && u > 0.24 && u < 0.36;
      const tailSpike = v > 0.9 && ((u * 10) | 0) % 2 === 0 && u > 0.25;
      return head || jaw || haunch || hornSpike || tailSpike;
    }
    case 'golem': {
      const headBlock = u > 0.28 && u < 0.72 && v > 0.08 && v < 0.3;
      const torsoBlock = u > 0.14 && u < 0.86 && v > 0.36 && v < 0.72;
      const shoulder = u > 0.02 && u < 0.22 && v > 0.34 && v < 0.52;
      const legBlock = u > 0.26 && u < 0.48 && v > 0.78 && v < 0.96;
      return headBlock || torsoBlock || shoulder || legBlock;
    }
    case 'wisp': {
      const hood = inEllipse(u, v, 0.5, 0.34, 0.3 + jitter * 0.06, 0.26);
      // Ragged tendrils: column length varies, flickering with frame.
      const column = Math.floor(u * 6);
      const tendrilLength =
        0.55 + 0.32 * Math.abs(Math.sin(column * 2.7 + jitter * 9 + frame * 1.3));
      const tendril = u > 0.08 && v > 0.4 && v < tendrilLength + 0.35 && column % 2 === 0;
      return hood || tendril;
    }
  }
}

// ---------------------------------------------------------------------------
//  Sprite generation
// ---------------------------------------------------------------------------

/** Draw an egg: oval shell with seeded speckles in the element color. */
function eggSprite(species: SpeciesDef, rng: Rng, size: number): SpriteGrid {
  const grid = emptyGrid(size);
  const cx = (size - 1) / 2;
  const cy = size * 0.55;
  const shell = '#EDE7DA';
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = (x - cx) / (size * 0.36);
      const dy = (y - cy) / (size * 0.44);
      if (dx * dx + dy * dy <= 1) {
        grid[y][x] = nextFloat(rng) < 0.22 ? ELEMENT_HEX[species.element] : shell;
      }
    }
  }
  outlinePass(grid, shade(ELEMENT_HEX[species.element], 0.3));
  return grid;
}

/** Surround the silhouette with a dark outline (readability pass). */
function outlinePass(grid: SpriteGrid, outlineColor: string): void {
  const size = grid.length;
  const isBody = (x: number, y: number): boolean =>
    x >= 0 && y >= 0 && x < size && y < size && grid[y][x] !== null && grid[y][x] !== outlineColor;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      if (grid[y][x] !== null) continue;
      if (isBody(x - 1, y) || isBody(x + 1, y) || isBody(x, y - 1) || isBody(x, y + 1)) {
        grid[y][x] = outlineColor;
      }
    }
  }
}

/**
 * Generate the deterministic sprite for a species. Frame 0/1 animate:
 * wings flap, wisps flicker, eyes blink.
 */
export function spriteForSpecies(species: SpeciesDef, frame = 0): SpriteGrid {
  const size = STAGE_GRID[species.stage];
  const rng = createRng(hashString(species.id));
  if (species.stage === 'EGG') return eggSprite(species, rng, size);

  const archetype = archetypeFor(species.id);
  const jitter = nextFloat(rng);
  const base = ELEMENT_HEX[species.element];
  const light = shade(base, 1.5);
  const dark = shade(base, 0.6);
  const outline = shade(base, 0.28);
  const accent = ALIGNMENT_HEX[species.alignment];

  const grid = emptyGrid(size);
  const half = Math.ceil(size / 2);

  // 1) Silhouette fill (mirrored), with seeded texture inside the mask.
  // Masks are symmetric in full-body coordinates: u spans 0..0.5 on the
  // left half and mirrors across the spine.
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < half; x++) {
      const u = x / (size - 1);
      const v = y / (size - 1);
      const roll = nextFloat(rng); // always consume — keeps stream stable
      if (!inSilhouette(archetype, u, v, frame, jitter)) continue;
      let color = base;
      if (roll < 0.1) color = accent;
      else if (roll < 0.24) color = light;
      else if (roll > 0.86) color = dark;
      grid[y][x] = color;
      grid[y][size - 1 - x] = color;
    }
  }

  // 2) Directional shading: lit from above, shadowed beneath.
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      if (grid[y][x] === null) continue;
      const aboveEmpty = y === 0 || grid[y - 1][x] === null;
      const belowEmpty = y === size - 1 || grid[y + 1][x] === null;
      if (aboveEmpty && grid[y][x] === base) grid[y][x] = light;
      else if (belowEmpty && grid[y][x] === base) grid[y][x] = dark;
    }
  }

  // 3) Features: horns for VENOM, crown for APEX.
  const headY = archetype === 'drake' ? Math.round(size * 0.28) : Math.round(size * 0.2);
  if (species.alignment === 'VENOM') {
    const hornX = Math.round(size * 0.3);
    for (const hx of [hornX, size - 1 - hornX]) {
      grid[Math.max(0, headY - 2)][hx] = accent;
      grid[Math.max(0, headY - 1)][hx] = dark;
    }
  }
  if (species.stage === 'APEX') {
    const mid = Math.floor((size - 1) / 2);
    for (const cxp of [Math.round(size * 0.32), mid, size - 1 - Math.round(size * 0.32)]) {
      grid[0][cxp] = accent;
      grid[1][cxp] = accent;
    }
  }

  // 4) Eyes: symmetric, in the head zone — they make it a creature.
  const eyeY =
    archetype === 'wisp'
      ? Math.round(size * 0.32)
      : archetype === 'drake'
        ? Math.round(size * 0.32)
        : Math.round(size * 0.26);
  const eyeX = Math.round(size * 0.36);
  const eyeColor = species.alignment === 'VENOM' ? '#FF3355' : '#141428';
  const blink = frame % 2 === 1 && archetype !== 'wisp';
  grid[eyeY][eyeX] = blink ? dark : eyeColor;
  grid[eyeY][size - 1 - eyeX] = blink ? dark : eyeColor;
  if (!blink && size >= 14) {
    grid[eyeY - 1][eyeX] = '#FFFFFF';
    grid[eyeY - 1][size - 1 - eyeX] = '#FFFFFF';
  }

  // 5) Outline pass last, so it hugs the final silhouette.
  outlinePass(grid, outline);
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
    for (let x = 0; x < grid[y].length; x++) {
      const color = grid[y][x];
      if (!color) continue;
      ctx.fillStyle = color;
      ctx.fillRect(x * scale, y * scale, scale, scale);
    }
  }
}
