/**
 * @file scenes.ts
 * @module aethermon/web/scenes
 * @layer Layer 14
 * @component AETHERMON Web — Procedural Region Backdrops
 *
 * Each canon region gets a deterministic parametric scene: a tinted sky
 * gradient, twinkling motes of light, a ground band, and a motif drawn
 * from the region's character — Ember Reach raises forge spires and
 * embers, the Aerial Expanse stacks clouds and wind streaks, the Null
 * Vale glitches, Glass Drift runs data lattices, Ward Sanctum lights
 * its pylons, Bastion Fields steps its fractal towers. Scenes are plain
 * color grids (like sprites), so the browser and the dependency-free
 * PNG renderer share them. `frame` animates twinkle/embers/wind.
 */

import type { RegionId } from '../regions.js';
import { getRegion } from '../regions.js';
import { createRng, nextInt, type Rng } from '../rng.js';
import { ELEMENT_HEX, type SpriteGrid } from './sprites.js';

function hexToRgbTuple(hex: string): [number, number, number] {
  const n = Number.parseInt(hex.replace('#', ''), 16);
  return [(n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff];
}

/** Blend two hex colors; t=0 → a, t=1 → b. Returns rgb() string. */
function blend(a: string, b: string, t: number): string {
  const [ar, ag, ab] = hexToRgbTuple(a);
  const [br, bg, bb] = hexToRgbTuple(b);
  const mix = (x: number, y: number): number => Math.round(x + (y - x) * t);
  return `rgb(${mix(ar, br)},${mix(ag, bg)},${mix(ab, bb)})`;
}

const NIGHT = '#07070d';

interface ScenePainter {
  grid: SpriteGrid;
  width: number;
  height: number;
  set(x: number, y: number, color: string): void;
  rect(x: number, y: number, w: number, h: number, color: string): void;
}

function painter(width: number, height: number): ScenePainter {
  const grid: SpriteGrid = Array.from({ length: height }, () =>
    Array.from({ length: width }, () => null)
  );
  const set = (x: number, y: number, color: string): void => {
    if (x >= 0 && y >= 0 && x < width && y < height) grid[y][x] = color;
  };
  return {
    grid,
    width,
    height,
    set,
    rect(x, y, w, h, color) {
      for (let yy = y; yy < y + h; yy++) for (let xx = x; xx < x + w; xx++) set(xx, yy, color);
    },
  };
}

/** Upward triangle silhouette with apex at (apexX, topY). */
function spire(
  p: ScenePainter,
  apexX: number,
  topY: number,
  baseY: number,
  halfWidth: number,
  color: string
): void {
  for (let y = topY; y <= baseY; y++) {
    const t = (y - topY) / Math.max(1, baseY - topY);
    const w = Math.max(0, Math.round(halfWidth * t));
    p.rect(apexX - w, y, w * 2 + 1, 1, color);
  }
}

function cloud(p: ScenePainter, cx: number, cy: number, r: number, color: string): void {
  for (let y = -Math.ceil(r / 2); y <= Math.ceil(r / 2); y++) {
    for (let x = -r; x <= r; x++) {
      if ((x * x) / (r * r) + (y * y * 4) / (r * r) <= 1) p.set(cx + x, cy + y, color);
    }
  }
}

/**
 * Render a region backdrop as a color grid (width × height cells).
 * Deterministic per (region, size); `frame` animates particles.
 */
export function sceneGrid(
  regionId: RegionId,
  width: number,
  height: number,
  frame = 0
): SpriteGrid {
  const region = getRegion(regionId);
  const tint = ELEMENT_HEX[region.tongue];
  const p = painter(width, height);
  const rng: Rng = createRng([...regionId].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7));
  const groundY = Math.floor(height * 0.82);

  // Sky gradient — darkest at the top, tinted toward the horizon.
  for (let y = 0; y < groundY; y++) {
    const t = y / groundY;
    const color = blend(NIGHT, tint, 0.04 + t * 0.16);
    p.rect(0, y, width, 1, color);
  }
  // Ground band.
  p.rect(0, groundY, width, 1, blend(tint, NIGHT, 0.55));
  for (let y = groundY + 1; y < height; y++) {
    p.rect(0, y, width, 1, blend(NIGHT, tint, 0.1 - Math.min(0.08, (y - groundY) * 0.02)));
  }

  // Twinkling motes of light — sparse, mostly faint.
  const starCount = Math.floor(width * 0.3);
  for (let i = 0; i < starCount; i++) {
    const x = nextInt(rng, 0, width - 1);
    const y = nextInt(rng, 0, Math.floor(groundY * 0.7));
    const bright = (i + frame) % 5 === 0;
    p.set(x, y, bright ? blend(tint, '#FFFFFF', 0.5) : blend(NIGHT, tint, 0.3));
  }

  const silhouette = blend(NIGHT, tint, 0.22);
  const glow = blend(tint, '#FFFFFF', 0.35);

  switch (regionId) {
    case 'ember_reach': {
      for (let i = 0; i < 4; i++) {
        const x = nextInt(rng, 3, width - 4);
        spire(
          p,
          x,
          nextInt(rng, Math.floor(height * 0.3), Math.floor(height * 0.55)),
          groundY,
          nextInt(rng, 2, 4),
          silhouette
        );
      }
      for (let i = 0; i < 14; i++) {
        // Embers rise: frame shifts them upward.
        const x = nextInt(rng, 0, width - 1);
        const y = groundY - 1 - ((nextInt(rng, 0, groundY) + frame * 2) % groundY);
        p.set(x, y, i % 3 === 0 ? glow : tint);
      }
      break;
    }
    case 'aerial_expanse': {
      for (let i = 0; i < 5; i++) {
        cloud(
          p,
          nextInt(rng, 4, width - 5),
          nextInt(rng, 3, Math.floor(groundY * 0.7)),
          nextInt(rng, 3, 6),
          blend(NIGHT, tint, 0.3)
        );
      }
      for (let i = 0; i < 8; i++) {
        // Wind streaks drift sideways with the frame.
        const y = nextInt(rng, 2, groundY - 2);
        const x = (nextInt(rng, 0, width - 1) + frame * 3) % width;
        p.rect(x, y, 4, 1, blend(NIGHT, tint, 0.5));
      }
      break;
    }
    case 'null_vale': {
      for (let i = 0; i < 12; i++) {
        const w = nextInt(rng, 1, 4);
        const x = nextInt(rng, 0, width - w);
        const y = nextInt(rng, 2, groundY - 3);
        const flicker = (i + frame) % 4 === 0;
        p.rect(x, y, w, nextInt(rng, 1, 2), flicker ? glow : blend(NIGHT, tint, 0.4));
      }
      // Broken ground: bite gaps out of the ground line.
      for (let i = 0; i < 6; i++) {
        p.rect(nextInt(rng, 0, width - 3), groundY, nextInt(rng, 1, 3), 1, NIGHT);
      }
      break;
    }
    case 'glass_drift': {
      for (let x = 2; x < width; x += 7) {
        for (let y = 2; y < groundY; y++) p.set(x, y, blend(NIGHT, tint, 0.18));
        for (let y = 4; y < groundY; y += 5) p.set(x, y, (x + y + frame) % 2 === 0 ? glow : tint);
      }
      for (let i = 0; i < 2; i++) {
        const x = nextInt(rng, 4, width - 8);
        p.rect(
          x,
          nextInt(rng, Math.floor(height * 0.35), Math.floor(height * 0.5)),
          4,
          groundY,
          silhouette
        );
      }
      break;
    }
    case 'ward_sanctum': {
      for (let i = 0; i < 3; i++) {
        const x = Math.floor(((i + 1) * width) / 4);
        const top = nextInt(rng, Math.floor(height * 0.35), Math.floor(height * 0.5));
        spire(p, x, top, groundY, 2, silhouette);
        p.set(x, top - 1, (i + frame) % 2 === 0 ? glow : tint); // ward light pulses
      }
      break;
    }
    case 'bastion_fields': {
      for (let i = 0; i < 3; i++) {
        const x = nextInt(rng, 2, width - 12);
        let w = nextInt(rng, 7, 10);
        let top = groundY;
        // Stepped fractal tower: stacked, shrinking blocks.
        for (let level = 0; level < 4 && w > 1; level++) {
          const h = nextInt(rng, 2, 4);
          top -= h;
          p.rect(x + Math.floor((10 - w) / 2), top, w, h, silhouette);
          w -= 2;
        }
        p.set(x + 5, top - 1, frame % 2 === 0 ? glow : tint);
      }
      break;
    }
  }
  return p.grid;
}
