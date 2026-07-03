/**
 * @file sprites.ts
 * @module aethermon/web/sprites
 * @layer Layer 14
 * @component AETHERMON Web — Procedural Pixel-Art Sprites (v3)
 *
 * Every species gets a deterministic pixel creature, generated with real
 * pixel-art craft rather than tinted noise:
 *
 *  • Hue-shifted palette ramps — shadows lean cool (toward violet),
 *    highlights lean warm (toward gold), per Sacred Tongue hue.
 *  • Zone-tagged silhouettes — head / body / wing / limb / tendril each
 *    get palette roles (belly patches, wing membranes with lit edges).
 *  • A cellular smoothing pass removes lone pixels and fills pinholes,
 *    so forms read solid instead of static-y.
 *  • Checkerboard dither shading on the lower body (odd grid sizes make
 *    the dither mirror-symmetric for free).
 *  • Seeded per-species features: ears, VENOM horns, AEGIS crests,
 *    stripe/spot markings — identity beyond proportion jitter.
 *
 * Wings still flap and eyes still blink between frames; stage controls
 * grid size so evolution visibly grows the creature. The sprites remain
 * pure math — deterministic from the species id, no image assets.
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
 * Sprite grid size (pixels per side) by stage — non-decreasing so a
 * hatchling never shrinks and every evolution visibly grows. Odd sizes
 * give a true center column (and mirror-symmetric checkerboard dither).
 */
const STAGE_GRID: Record<Stage, number> = {
  EGG: 11,
  MOTE: 13,
  SPRITE: 15,
  GUARDIAN: 17,
  PARAGON: 19,
  APEX: 21,
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

// ---------------------------------------------------------------------------
//  Hue-shifted palette ramps (the pixel-art color trick)
// ---------------------------------------------------------------------------

function hexToHsl(hex: string): [number, number, number] {
  const n = Number.parseInt(hex.slice(1), 16);
  const r = ((n >> 16) & 0xff) / 255;
  const g = ((n >> 8) & 0xff) / 255;
  const b = (n & 0xff) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h: number;
  if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
  else if (max === g) h = ((b - r) / d + 2) / 6;
  else h = ((r - g) / d + 4) / 6;
  return [h * 360, s, l];
}

function hslToRgbString(h: number, s: number, l: number): string {
  h = ((h % 360) + 360) % 360;
  s = Math.max(0, Math.min(1, s));
  l = Math.max(0, Math.min(1, l));
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  let r = 0;
  let g = 0;
  let b = 0;
  if (h < 60) [r, g, b] = [c, x, 0];
  else if (h < 120) [r, g, b] = [x, c, 0];
  else if (h < 180) [r, g, b] = [0, c, x];
  else if (h < 240) [r, g, b] = [0, x, c];
  else if (h < 300) [r, g, b] = [x, 0, c];
  else [r, g, b] = [c, 0, x];
  const to255 = (v: number): number => Math.round((v + m) * 255);
  return `rgb(${to255(r)},${to255(g)},${to255(b)})`;
}

/** A five-step ramp plus support colors, all derived from one hue. */
interface Ramp {
  outline: string;
  shadow: string;
  base: string;
  light: string;
  highlight: string;
  belly: string;
}

/**
 * Build a hue-shifted ramp: shadows shift toward violet-blue and darken;
 * highlights shift toward warm gold and lighten. The belly is a paler,
 * desaturated companion of the base.
 */
function rampFor(hex: string): Ramp {
  const [h, s, l] = hexToHsl(hex);
  return {
    outline: hslToRgbString(h - 24, Math.min(1, s * 0.9), Math.max(0.06, l - 0.34)),
    shadow: hslToRgbString(h - 12, Math.min(1, s * 1.05), Math.max(0.1, l - 0.16)),
    base: hslToRgbString(h, s, l),
    light: hslToRgbString(h + 10, Math.min(1, s * 0.95), Math.min(0.9, l + 0.13)),
    highlight: hslToRgbString(h + 20, s * 0.6, Math.min(0.96, l + 0.28)),
    belly: hslToRgbString(h + 6, s * 0.45, Math.min(0.92, l + 0.22)),
  };
}

/** A rendered sprite: square pixel grid of CSS colors (null = empty). */
export type SpriteGrid = (string | null)[][];

function emptyGrid<T>(size: number, fill: T): T[][] {
  return Array.from({ length: size }, () => Array.from({ length: size }, () => fill));
}

// ---------------------------------------------------------------------------
//  Zone-tagged silhouettes — (u, v) in [0,1]² over the LEFT half (mirrored)
// ---------------------------------------------------------------------------

type Zone = 'head' | 'body' | 'wing' | 'limb' | 'tendril' | 'jaw' | null;

function inEllipse(u: number, v: number, cu: number, cv: number, ru: number, rv: number): boolean {
  const du = (u - cu) / ru;
  const dv = (v - cv) / rv;
  return du * du + dv * dv <= 1;
}

/**
 * Archetype silhouette for the left half, tagged by body zone so the
 * coloring pass can give each part a palette role. `frame` animates
 * wings (up/down) and wisp tendrils; `jitter` varies proportions.
 */
function zoneAt(
  archetype: BodyArchetype,
  u: number,
  v: number,
  frame: number,
  jitter: number
): Zone {
  const flap = frame % 2 === 0 ? 0.05 : -0.09;
  switch (archetype) {
    case 'blob': {
      if (inEllipse(u, v, 0.5, 0.3, 0.3, 0.22)) return 'head';
      if (inEllipse(u, v, 0.5, 0.6, 0.4 + jitter * 0.06, 0.32)) return 'body';
      return null;
    }
    case 'biped': {
      if (inEllipse(u, v, 0.5, 0.22, 0.24 + jitter * 0.04, 0.17)) return 'head';
      if (inEllipse(u, v, 0.5, 0.58, 0.26 + jitter * 0.05, 0.27)) return 'body';
      if (inEllipse(u, v, 0.18, 0.55 + flap * 0.5, 0.09, 0.17)) return 'limb';
      if (u > 0.3 && u < 0.46 && v > 0.79 && v < 0.97) return 'limb';
      return null;
    }
    case 'winged': {
      if (inEllipse(u, v, 0.5, 0.28, 0.16, 0.13)) return 'head';
      if (inEllipse(u, v, 0.5, 0.55, 0.2, 0.25 + jitter * 0.04)) return 'body';
      if (inEllipse(u, v, 0.15, 0.42 + flap, 0.17, 0.28 + (frame % 2) * 0.05)) return 'wing';
      if (u > 0.42 && v > 0.8 && v < 0.94) return 'limb'; // tail fan
      return null;
    }
    case 'drake': {
      if (v < 0.14 && u > 0.24 && u < 0.36) return 'head'; // horn root
      if (inEllipse(u, v, 0.5, 0.3, 0.3, 0.2)) return 'head';
      if (v > 0.4 && v < 0.52 && u > 0.2) return 'jaw';
      if (inEllipse(u, v, 0.44, 0.72, 0.34, 0.21)) return 'body';
      if (v > 0.9 && ((u * 10) | 0) % 2 === 0 && u > 0.28) return 'limb'; // tail spikes
      return null;
    }
    case 'golem': {
      if (u > 0.28 && u < 0.72 && v > 0.08 && v < 0.3) return 'head';
      if (u > 0.16 && u < 0.84 && v > 0.36 && v < 0.72) return 'body';
      if (u > 0.02 && u < 0.22 && v > 0.34 && v < 0.54) return 'limb'; // shoulder
      if (u > 0.26 && u < 0.48 && v > 0.78 && v < 0.96) return 'limb'; // leg
      return null;
    }
    case 'wisp': {
      if (inEllipse(u, v, 0.5, 0.28, 0.3 + jitter * 0.05, 0.22)) return 'head';
      if (inEllipse(u, v, 0.5, 0.48, 0.27, 0.15)) return 'body';
      // Ragged tendrils trail well below the body, flickering per frame.
      const column = Math.floor(u * 7);
      const length = 0.62 + 0.36 * Math.abs(Math.sin(column * 2.7 + jitter * 9 + frame * 1.3));
      if (u > 0.08 && v > 0.5 && v < length + 0.38 && column % 2 === 0) return 'tendril';
      return null;
    }
  }
}

// ---------------------------------------------------------------------------
//  Sprite generation
// ---------------------------------------------------------------------------

/** Egg: smooth ramped shell, seeded element speckles, dithered shadow. */
function eggSprite(species: SpeciesDef, rng: Rng, size: number): SpriteGrid {
  const grid: SpriteGrid = emptyGrid(size, null);
  const shell = rampFor('#EDE7DA');
  const tint = rampFor(ELEMENT_HEX[species.element]);
  const cx = (size - 1) / 2;
  const cy = size * 0.54;
  const ru = size * 0.34;
  const rv = size * 0.42;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = (x - cx) / ru;
      const dy = (y - cy) / rv;
      const roll = nextFloat(rng);
      if (dx * dx + dy * dy > 1) continue;
      let color = shell.base;
      if (dy < -0.45 && dx < 0.2) color = shell.light; // top sheen
      if (dy > 0.45 && (x + y) % 2 === 0) color = shell.shadow; // dithered under-shadow
      if (roll < 0.16) color = tint.base; // element speckles
      grid[y][x] = color;
    }
  }
  outlinePass(grid, tint.outline);
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
 * Cellular smoothing: erase filled cells with ≤1 filled neighbor (specks)
 * and fill holes with ≥6 filled neighbors. Symmetric input stays
 * symmetric. Added cells inherit the majority neighbor zone.
 */
function smooth(zones: Zone[][]): void {
  const size = zones.length;
  const neighborInfo = (x: number, y: number): { count: number; zone: Zone } => {
    let count = 0;
    const tally = new Map<string, number>();
    for (let dy = -1; dy <= 1; dy++) {
      for (let dx = -1; dx <= 1; dx++) {
        if (dx === 0 && dy === 0) continue;
        const nx = x + dx;
        const ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= size || ny >= size) continue;
        const z = zones[ny][nx];
        if (z) {
          count++;
          tally.set(z, (tally.get(z) ?? 0) + 1);
        }
      }
    }
    let best: Zone = 'body';
    let bestCount = 0;
    for (const [z, c] of tally) {
      if (c > bestCount) {
        bestCount = c;
        best = z as Zone;
      }
    }
    return { count, zone: best };
  };
  const next: Zone[][] = zones.map((row) => [...row]);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const { count, zone } = neighborInfo(x, y);
      if (zones[y][x] && count <= 1)
        next[y][x] = null; // lone speck
      else if (!zones[y][x] && count >= 6) next[y][x] = zone; // pinhole
    }
  }
  for (let y = 0; y < size; y++) zones[y] = next[y];
}

/** Seeded per-species marking style. */
type Marking = 'none' | 'stripes' | 'spots';

/**
 * Generate the deterministic sprite for a species. Frame 0/1 animate:
 * wings flap, wisps flicker, eyes blink.
 */
export function spriteForSpecies(species: SpeciesDef, frame = 0): SpriteGrid {
  const size = STAGE_GRID[species.stage];
  const rng = createRng(hashString(species.id));
  if (species.stage === 'EGG') return eggSprite(species, rng, size);

  const archetype = archetypeFor(species.id);
  const ramp = rampFor(ELEMENT_HEX[species.element]);
  const accent = ALIGNMENT_HEX[species.alignment];

  // Seeded identity rolls — consumed in fixed order for determinism.
  const jitter = nextFloat(rng);
  const markingRoll = nextFloat(rng);
  const marking: Marking = markingRoll < 0.38 ? 'stripes' : markingRoll < 0.62 ? 'spots' : 'none';
  const stripePhase = nextFloat(rng) < 0.5 ? 0 : 1;
  const hasEars = nextFloat(rng) < 0.55 && (archetype === 'blob' || archetype === 'biped');

  // 1) Zone silhouette (left half, mirrored). Consume one roll per
  //    half-cell regardless of mask so the stream is frame-stable.
  const zones: Zone[][] = emptyGrid(size, null as Zone);
  const texture: number[][] = emptyGrid(size, 0);
  const half = Math.ceil(size / 2);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < half; x++) {
      const u = x / (size - 1);
      const v = y / (size - 1);
      const roll = nextFloat(rng);
      const zone = zoneAt(archetype, u, v, frame, jitter);
      zones[y][x] = zone;
      zones[y][size - 1 - x] = zone;
      texture[y][x] = roll;
      texture[y][size - 1 - x] = roll;
    }
  }

  // 2) Smooth away specks and pinholes (skip wisps: ragged is the point).
  if (archetype !== 'wisp') smooth(zones);

  // 3) Coloring: palette role per zone, then light/shadow/dither/markings.
  const grid: SpriteGrid = emptyGrid(size, null);
  const zoneOf = (x: number, y: number): Zone =>
    x >= 0 && y >= 0 && x < size && y < size ? zones[y][x] : null;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const zone = zones[y][x];
      if (!zone) continue;
      const v = y / (size - 1);
      let color = ramp.base;

      // Zone palette roles.
      if (zone === 'wing')
        color = ramp.shadow; // membrane
      else if (zone === 'jaw') color = ramp.belly;
      else if (zone === 'tendril')
        color = (x + y) % 2 === 0 ? ramp.base : ramp.shadow; // wispy
      else if (zone === 'limb') color = ramp.shadow;

      // Belly patch: lower-center of the body reads lighter.
      if (zone === 'body' && inEllipse(x / (size - 1), v, 0.5, 0.66, 0.2, 0.2)) {
        color = ramp.belly;
      }

      // Markings on the body coat.
      if (zone === 'body' && color === ramp.base) {
        if (marking === 'stripes' && y % 3 === stripePhase) color = ramp.shadow;
        else if (marking === 'spots' && texture[y][x] < 0.16) color = ramp.shadow;
      }

      // Directional light: lit top edges, occasional highlight; shadowed
      // bottom edges; dithered shadow band low on the form.
      const aboveEmpty = zoneOf(x, y - 1) === null;
      const belowEmpty = zoneOf(x, y + 1) === null;
      if (aboveEmpty) color = ramp.light;
      // Highlight only on the top-LEFT of the head — one coherent light
      // source instead of scattered bright speckles.
      if (aboveEmpty && zone === 'head' && x < (size - 1) / 2) color = ramp.highlight;
      if (belowEmpty && !aboveEmpty) color = ramp.shadow;
      if (!aboveEmpty && !belowEmpty && v > 0.64 && (x + y) % 2 === 0 && zone !== 'tendril') {
        color = ramp.shadow;
      }

      // Sparse accent glints tie the alignment color in.
      if (!aboveEmpty && texture[y][x] > 0.96) color = accent;

      grid[y][x] = color;
    }
  }

  // 4) Features. Symmetric placements: ears, horns, crest.
  const headTop = ((): number => {
    for (let y = 0; y < size; y++) if (zones[y].some((z) => z === 'head')) return y;
    return Math.round(size * 0.2);
  })();
  const earX = Math.round(size * 0.32);
  if (hasEars && headTop >= 2) {
    for (const ex of [earX, size - 1 - earX]) {
      grid[headTop - 1][ex] = ramp.base;
      grid[headTop - 2][ex] = ramp.shadow;
    }
  }
  if (species.alignment === 'VENOM' && headTop >= 2) {
    const hornX = Math.round(size * 0.26);
    for (const hx of [hornX, size - 1 - hornX]) {
      grid[headTop - 1][hx] = ramp.shadow;
      grid[headTop - 2][hx] = accent;
    }
  }
  if (
    species.alignment === 'AEGIS' &&
    (species.stage === 'PARAGON' || species.stage === 'APEX') &&
    headTop >= 2
  ) {
    const mid = (size - 1) / 2;
    grid[headTop - 1][mid] = accent;
    grid[headTop - 2][mid] = accent;
  }
  if (species.stage === 'APEX') {
    const mid = (size - 1) / 2;
    for (const cxp of [Math.round(size * 0.34), mid, size - 1 - Math.round(size * 0.34)]) {
      grid[0][cxp] = accent;
      grid[1][cxp] = accent;
    }
  }

  // 5) Eyes — they make it a creature. Larger grids get a lit 2px eye.
  const eyeY = headTop + Math.max(1, Math.round((archetype === 'drake' ? 0.14 : 0.11) * size));
  const eyeX = Math.round(size * 0.35);
  const eyeColor = species.alignment === 'VENOM' ? '#FF3355' : '#141428';
  const blink = frame % 2 === 1 && archetype !== 'wisp';
  for (const ex of [eyeX, size - 1 - eyeX]) {
    grid[eyeY][ex] = blink ? ramp.shadow : eyeColor;
    if (!blink && size >= 15) {
      grid[eyeY - 1][ex] = '#FFFFFF';
      grid[eyeY][ex + (ex < size / 2 ? -1 : 1)] = eyeColor;
    }
  }

  // 6) Outline hugs the final silhouette; feet get a grounding shadow.
  outlinePass(grid, ramp.outline);
  return grid;
}

/** Paint a sprite grid onto a canvas, pixel-perfect and upscaled. */
export function drawSprite(canvas: HTMLCanvasElement, grid: SpriteGrid, scale = 8): void {
  const rows = grid.length;
  const cols = grid[0]?.length ?? 0;
  canvas.width = cols * scale;
  canvas.height = rows * scale;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < grid[y].length; x++) {
      const color = grid[y][x];
      if (!color) continue;
      ctx.fillStyle = color;
      ctx.fillRect(x * scale, y * scale, scale, scale);
    }
  }
}
