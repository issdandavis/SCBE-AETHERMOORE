#!/usr/bin/env node
/**
 * AETHERMON preview renderer — draws the game's procedural sprites and a
 * battle-screen mock straight to PNG with zero dependencies (node:zlib).
 * Used to generate marketing/preview images and to eyeball the sprite
 * engine without a browser.
 *
 * Usage: node scripts/aethermon_render_preview.cjs [outDir]
 * Requires a build first: tsc -p tsconfig.json
 */

'use strict';

const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');

const { allSpecies, getSpecies } = require('../dist/src/aethermon/species.js');
const { spriteForSpecies, ELEMENT_HEX } = require('../dist/src/aethermon/web/sprites.js');
const { sceneGrid } = require('../dist/src/aethermon/web/scenes.js');
const { STAGE_ORDER, TONGUE_NOTES } = require('../dist/src/aethermon/types.js');
const { createMonster, effectiveStats, xpToNext, lifespanRemaining } = require('../dist/src/aethermon/monster.js');
const { getMove } = require('../dist/src/aethermon/moves.js');

// ── Minimal PNG encoder ─────────────────────────────────────────────────

const CRC_TABLE = (() => {
  const table = new Int32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c;
  }
  return table;
})();

function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const out = Buffer.alloc(8 + data.length + 4);
  out.writeUInt32BE(data.length, 0);
  out.write(type, 4, 'ascii');
  data.copy(out, 8);
  out.writeUInt32BE(crc32(out.subarray(4, 8 + data.length)), 8 + data.length);
  return out;
}

function encodePng(width, height, rgba) {
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 6; // RGBA
  const raw = Buffer.alloc((width * 4 + 1) * height);
  for (let y = 0; y < height; y++) {
    raw[y * (width * 4 + 1)] = 0; // filter: none
    rgba.copy(raw, y * (width * 4 + 1) + 1, y * width * 4, (y + 1) * width * 4);
  }
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', zlib.deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

// ── Tiny raster canvas ──────────────────────────────────────────────────

class Raster {
  constructor(width, height) {
    this.width = width;
    this.height = height;
    this.data = Buffer.alloc(width * height * 4);
  }
  set(x, y, [r, g, b, a = 255]) {
    if (x < 0 || y < 0 || x >= this.width || y >= this.height) return;
    const i = (y * this.width + x) * 4;
    this.data[i] = r;
    this.data[i + 1] = g;
    this.data[i + 2] = b;
    this.data[i + 3] = a;
  }
  rect(x, y, w, h, color) {
    for (let yy = y; yy < y + h; yy++) for (let xx = x; xx < x + w; xx++) this.set(xx, yy, color);
  }
  frame(x, y, w, h, color, thickness = 1) {
    this.rect(x, y, w, thickness, color);
    this.rect(x, y + h - thickness, w, thickness, color);
    this.rect(x, y, thickness, h, color);
    this.rect(x + w - thickness, y, thickness, h, color);
  }
  png() {
    return encodePng(this.width, this.height, this.data);
  }
}

function hexToRgb(hex) {
  const n = Number.parseInt(hex.replace('#', ''), 16);
  return [(n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff, 255];
}

function parseColor(color) {
  if (color.startsWith('#')) return hexToRgb(color);
  const m = color.match(/rgb\((\d+),(\d+),(\d+)\)/);
  return m ? [Number(m[1]), Number(m[2]), Number(m[3]), 255] : [255, 255, 255, 255];
}

// ── 3×5 pixel font ──────────────────────────────────────────────────────

const FONT = {
  A: [0b010, 0b101, 0b111, 0b101, 0b101],
  B: [0b110, 0b101, 0b110, 0b101, 0b110],
  C: [0b011, 0b100, 0b100, 0b100, 0b011],
  D: [0b110, 0b101, 0b101, 0b101, 0b110],
  E: [0b111, 0b100, 0b110, 0b100, 0b111],
  F: [0b111, 0b100, 0b110, 0b100, 0b100],
  G: [0b011, 0b100, 0b101, 0b101, 0b011],
  H: [0b101, 0b101, 0b111, 0b101, 0b101],
  I: [0b111, 0b010, 0b010, 0b010, 0b111],
  J: [0b001, 0b001, 0b001, 0b101, 0b010],
  K: [0b101, 0b101, 0b110, 0b101, 0b101],
  L: [0b100, 0b100, 0b100, 0b100, 0b111],
  M: [0b101, 0b111, 0b111, 0b101, 0b101],
  N: [0b110, 0b101, 0b101, 0b101, 0b101],
  O: [0b010, 0b101, 0b101, 0b101, 0b010],
  P: [0b110, 0b101, 0b110, 0b100, 0b100],
  Q: [0b010, 0b101, 0b101, 0b110, 0b011],
  R: [0b110, 0b101, 0b110, 0b101, 0b101],
  S: [0b011, 0b100, 0b010, 0b001, 0b110],
  T: [0b111, 0b010, 0b010, 0b010, 0b010],
  U: [0b101, 0b101, 0b101, 0b101, 0b111],
  V: [0b101, 0b101, 0b101, 0b101, 0b010],
  W: [0b101, 0b101, 0b111, 0b111, 0b101],
  X: [0b101, 0b101, 0b010, 0b101, 0b101],
  Y: [0b101, 0b101, 0b010, 0b010, 0b010],
  Z: [0b111, 0b001, 0b010, 0b100, 0b111],
  '0': [0b010, 0b101, 0b101, 0b101, 0b010],
  '1': [0b010, 0b110, 0b010, 0b010, 0b111],
  '2': [0b110, 0b001, 0b010, 0b100, 0b111],
  '3': [0b110, 0b001, 0b010, 0b001, 0b110],
  '4': [0b101, 0b101, 0b111, 0b001, 0b001],
  '5': [0b111, 0b100, 0b110, 0b001, 0b110],
  '6': [0b011, 0b100, 0b110, 0b101, 0b010],
  '7': [0b111, 0b001, 0b010, 0b010, 0b010],
  '8': [0b010, 0b101, 0b010, 0b101, 0b010],
  '9': [0b010, 0b101, 0b011, 0b001, 0b110],
  '/': [0b001, 0b001, 0b010, 0b100, 0b100],
  '.': [0b000, 0b000, 0b000, 0b000, 0b010],
  '-': [0b000, 0b000, 0b111, 0b000, 0b000],
  "'": [0b010, 0b010, 0b000, 0b000, 0b000],
  ' ': [0, 0, 0, 0, 0],
};

function drawText(raster, text, x, y, color, scale = 2) {
  let cx = x;
  for (const ch of text.toUpperCase()) {
    const glyph = FONT[ch] ?? FONT[' '];
    for (let row = 0; row < 5; row++) {
      for (let col = 0; col < 3; col++) {
        if ((glyph[row] >> (2 - col)) & 1) {
          raster.rect(cx + col * scale, y + row * scale, scale, scale, color);
        }
      }
    }
    cx += 4 * scale;
  }
  return cx;
}

function textWidth(text, scale = 2) {
  return text.length * 4 * scale;
}

function drawSpriteGrid(raster, grid, x, y, scale) {
  for (let gy = 0; gy < grid.length; gy++) {
    const row = grid[gy] ?? [];
    for (let gx = 0; gx < row.length; gx++) {
      const color = row[gx];
      if (!color) continue;
      raster.rect(x + gx * scale, y + gy * scale, scale, scale, parseColor(color));
    }
  }
}

// ── Compositing helpers (alpha blend, rounded rects, chips, bars) ────────

function blendPixel(raster, x, y, [r, g, b], a = 1) {
  if (x < 0 || y < 0 || x >= raster.width || y >= raster.height) return;
  const i = (y * raster.width + x) * 4;
  const inv = 1 - a;
  raster.data[i] = Math.round(raster.data[i] * inv + r * a);
  raster.data[i + 1] = Math.round(raster.data[i + 1] * inv + g * a);
  raster.data[i + 2] = Math.round(raster.data[i + 2] * inv + b * a);
  raster.data[i + 3] = 255;
}

function cornerOutside(xx, yy, w, h, r) {
  const test = (dx, dy) => dx * dx + dy * dy > r * r;
  if (xx < r && yy < r) return test(r - xx, r - yy);
  if (xx >= w - r && yy < r) return test(xx - (w - r - 1), r - yy);
  if (xx < r && yy >= h - r) return test(r - xx, yy - (h - r - 1));
  if (xx >= w - r && yy >= h - r) return test(xx - (w - r - 1), yy - (h - r - 1));
  return false;
}

function roundRect(raster, x, y, w, h, r, color, a = 1) {
  const rgb = color.length === undefined ? parseColor(color) : color;
  for (let yy = 0; yy < h; yy++)
    for (let xx = 0; xx < w; xx++)
      if (!cornerOutside(xx, yy, w, h, r)) blendPixel(raster, x + xx, y + yy, rgb, a);
}

function roundFrame(raster, x, y, w, h, r, color, a = 1, t = 1) {
  const rgb = color.length === undefined ? parseColor(color) : color;
  for (let yy = 0; yy < h; yy++)
    for (let xx = 0; xx < w; xx++) {
      if (cornerOutside(xx, yy, w, h, r)) continue;
      const edge = xx < t || yy < t || xx >= w - t || yy >= h - t || cornerOutside(xx, yy, w, h, r + 1);
      if (edge) blendPixel(raster, x + xx, y + yy, rgb, a);
    }
}

function vGradient(raster, x, y, w, h, topHex, botHex) {
  const [tr, tg, tb] = hexToRgb(topHex);
  const [br, bg, bb] = hexToRgb(botHex);
  for (let yy = 0; yy < h; yy++) {
    const t = yy / Math.max(1, h - 1);
    const row = [
      Math.round(tr + (br - tr) * t),
      Math.round(tg + (bg - tg) * t),
      Math.round(tb + (bb - tb) * t),
      255,
    ];
    raster.rect(x, y + yy, w, 1, row);
  }
}

/** Element chip (pill): tongue code + note. Returns drawn width. */
function chip(raster, x, y, code, note, hex) {
  const rgb = hexToRgb(hex);
  const w = textWidth(code, 1) + (note ? textWidth(note, 1) + 3 : 0) + 10;
  const h = 13;
  roundRect(raster, x, y, w, h, 4, rgb, 0.16);
  roundFrame(raster, x, y, w, h, 4, rgb, 0.7, 1);
  const light = [Math.min(255, rgb[0] + 90), Math.min(255, rgb[1] + 90), Math.min(255, rgb[2] + 90), 255];
  let cx = drawText(raster, code, x + 5, y + 4, light, 1);
  if (note) drawText(raster, note, cx + 2, y + 4, [rgb[0], rgb[1], rgb[2], 255], 1);
  return w;
}

/** Small labeled bar: LABEL [====] value. Returns next y. */
function labeledBar(raster, x, y, w, label, value, max, fillHex, low, barH = 7, rowH = 12) {
  drawText(raster, label, x, y + Math.floor((barH - 5) / 2) + 1, DIM, 1);
  const barX = x + 26;
  const barW = w - 26 - 20;
  roundRect(raster, barX, y, barW, barH, 2, [22, 22, 34, 255]);
  roundFrame(raster, barX, y, barW, barH, 2, [45, 45, 66, 255], 1, 1);
  const ratio = Math.max(0, Math.min(1, value / max));
  const fill = low ? hexToRgb('#ff5a5a') : hexToRgb(fillHex);
  if (ratio > 0) roundRect(raster, barX + 1, y + 1, Math.max(1, Math.round((barW - 2) * ratio)), barH - 2, 2, fill);
  drawText(raster, String(value), barX + barW + 4, y + Math.floor((barH - 5) / 2) + 1, [216, 216, 232, 255], 1);
  return y + rowH;
}

// ── Poster: full species sprite sheet ───────────────────────────────────

const BG = [10, 10, 18, 255];
const PANEL = [17, 17, 28, 255];
const GOLD = hexToRgb('#FFD75A');
const DIM = [120, 120, 150, 255];

function renderSpriteSheet(outFile) {
  const columns = 8;
  const cellW = 126;
  const cellH = 138;
  const margin = 24;
  const headerH = 30;
  const titleH = 64;

  const byStage = STAGE_ORDER.map((stage) => ({
    stage,
    species: allSpecies().filter((s) => s.stage === stage),
  }));
  let height = titleH + margin;
  for (const group of byStage) {
    height += headerH + Math.ceil(group.species.length / columns) * cellH + 8;
  }
  height += margin;
  const width = columns * cellW + margin * 2;
  const raster = new Raster(width, height);
  raster.rect(0, 0, width, height, BG);

  drawText(raster, 'AETHERMON', margin, 18, GOLD, 5);
  drawText(raster, '40 SPECIES OF THE AETHERMOORE REALM', margin, 46, DIM, 2);

  let y = titleH + margin;
  for (const group of byStage) {
    drawText(raster, group.stage, margin, y, hexToRgb('#7AE0FF'), 3);
    raster.rect(margin + textWidth(group.stage, 3) + 10, y + 6, width - margin * 2 - textWidth(group.stage, 3) - 10, 2, [42, 42, 64, 255]);
    y += headerH;
    group.species.forEach((species, index) => {
      const col = index % columns;
      const row = Math.floor(index / columns);
      const cx = margin + col * cellW;
      const cy = y + row * cellH;
      raster.rect(cx + 4, cy, cellW - 8, cellH - 10, PANEL);
      raster.frame(cx + 4, cy, cellW - 8, cellH - 10, parseColor(ELEMENT_HEX[species.element]));
      const grid = spriteForSpecies(species);
      const scale = Math.floor(90 / grid.length);
      const sx = cx + 4 + Math.floor((cellW - 8 - grid.length * scale) / 2);
      drawSpriteGrid(raster, grid, sx, cy + 10, scale);
      const name = species.name.toUpperCase();
      const nameScale = textWidth(name, 2) > cellW - 14 ? 1 : 2;
      drawText(
        raster,
        name,
        cx + 4 + Math.max(2, Math.floor((cellW - 8 - textWidth(name, nameScale)) / 2)),
        cy + cellH - 32,
        parseColor(ELEMENT_HEX[species.element]),
        nameScale
      );
      drawText(
        raster,
        `${species.element} ${species.alignment}`,
        cx + 4 + Math.max(2, Math.floor((cellW - 8 - textWidth(`${species.element} ${species.alignment}`, 1)) / 2)),
        cy + cellH - 18,
        DIM,
        1
      );
    });
    y += Math.ceil(group.species.length / columns) * cellH + 8;
  }

  fs.writeFileSync(outFile, raster.png());
  console.log(`wrote ${outFile} (${width}x${height})`);
}

// ── Device mock: the full Spiral Unit handheld with a live screen ───────

const ALIGN_HEX = { AEGIS: '#FFD75A', VENOM: '#B05CFF', FLUX: '#7AE0FF' };

/** Draw the deck menu buttons; move buttons get element-colored borders. */
function drawMenu(raster, x, y, w, labels, tintHex, elementBorders) {
  const cols = 3;
  const gap = 6;
  const bw = Math.floor((w - gap * (cols - 1)) / cols);
  const bh = 26;
  labels.forEach((label, i) => {
    const bx = x + (i % cols) * (bw + gap);
    const by = y + Math.floor(i / cols) * (bh + gap);
    const border =
      elementBorders && elementBorders[i]
        ? hexToRgb(elementBorders[i])
        : label === 'BEGIN' || label === 'BACK' || label === 'WARM'
          ? hexToRgb('#ffd75a')
          : label === 'BATTLE' || label === 'ARENA' || label === 'RUN'
            ? hexToRgb('#a04040')
            : label === 'THE GAP'
              ? hexToRgb('#6a3aa0')
              : [52, 52, 78, 255];
    roundRect(raster, bx, by, bw, bh, 8, [34, 34, 50, 255]);
    roundFrame(raster, bx, by, bw, bh, 8, border, 1, 1);
    const scale = textWidth(label, 1) > bw - 6 ? 1 : textWidth(label, 2) > bw - 6 ? 1 : 2;
    drawText(
      raster,
      label,
      bx + Math.max(3, Math.floor((bw - textWidth(label, scale)) / 2)),
      by + Math.floor((bh - 5 * scale) / 2),
      [214, 214, 232, 255],
      scale
    );
  });
  return y + Math.ceil(labels.length / cols) * (bh + gap);
}

function drawDpad(raster, cx, cy) {
  const s = 20;
  const btn = (dx, dy) => {
    roundRect(raster, cx + dx, cy + dy, s, s, 4, [40, 40, 58, 255]);
    roundFrame(raster, cx + dx, cy + dy, s, s, 4, [58, 58, 82, 255], 1, 1);
  };
  btn(s, 0);
  btn(0, s);
  btn(s, s);
  btn(s * 2, s);
  btn(s, s * 2);
  drawText(raster, '.', cx + s + 8, cy + s + 6, DIM, 1);
}

function drawAB(raster, x, y, tintHex) {
  const draw = (cx, cy, label, hex) => {
    const rgb = hexToRgb(hex);
    for (let yy = -18; yy <= 18; yy++)
      for (let xx = -18; xx <= 18; xx++)
        if (xx * xx + yy * yy <= 18 * 18) blendPixel(raster, cx + xx, cy + yy, [42, 42, 62], 1);
    for (let yy = -18; yy <= 18; yy++)
      for (let xx = -18; xx <= 18; xx++) {
        const d = xx * xx + yy * yy;
        if (d <= 18 * 18 && d >= 15 * 15) blendPixel(raster, cx + xx, cy + yy, rgb, 0.7);
      }
    drawText(raster, label, cx - 3, cy - 5, rgb, 2);
  };
  draw(x + 22, y + 8, 'B', '#ff9a7a');
  draw(x + 62, y - 6, 'A', '#ffd75a');
}

/**
 * Composite the whole handheld. mode: 'care' | 'battle'.
 * Draws shell, brow, bezel, live screen, and the control deck so the
 * redesigned UI can be verified without a browser.
 */
function renderDevice(outFile, mode) {
  const W = 470;
  const H = 820;
  const raster = new Raster(W, H);
  const tintHex = mode === 'battle' ? ELEMENT_HEX.AV : ELEMENT_HEX.KO;
  const tint = hexToRgb(tintHex);

  // Backdrop with tongue-tinted glow.
  vGradient(raster, 0, 0, W, H, '#05050a', '#0b0b14');
  for (let yy = 0; yy < 240; yy++)
    for (let xx = 0; xx < W; xx++) {
      const dx = (xx - W / 2) / (W / 2);
      const dy = yy / 240;
      const a = Math.max(0, 0.14 * (1 - dx * dx) * (1 - dy));
      blendPixel(raster, xx, yy, tint, a);
    }

  // Shell — vertical gradient clipped to the rounded body (not a rectangle).
  {
    const [tr, tg, tb] = hexToRgb('#2a2a3a');
    const [brc, bgc, bbc] = hexToRgb('#0e0e16');
    const sw2 = W - 32;
    const sh2 = H - 28;
    for (let yy = 0; yy < sh2; yy++) {
      const t = yy / Math.max(1, sh2 - 1);
      const row = [
        Math.round(tr + (brc - tr) * t),
        Math.round(tg + (bgc - tg) * t),
        Math.round(tb + (bbc - tb) * t),
      ];
      for (let xx = 0; xx < sw2; xx++)
        if (!cornerOutside(xx, yy, sw2, sh2, 36)) blendPixel(raster, 16 + xx, 14 + yy, row, 1);
    }
  }
  roundFrame(raster, 16, 14, W - 32, H - 28, 36, tint, 0.4, 1);
  // corner screws
  for (const [sx, sy] of [
    [30, 30],
    [W - 40, 30],
  ]) {
    for (let yy = -4; yy <= 4; yy++)
      for (let xx = -4; xx <= 4; xx++)
        if (xx * xx + yy * yy <= 16) blendPixel(raster, sx + xx, sy + yy, [40, 40, 58], 1);
  }

  // Brow.
  drawText(raster, 'AETHERMON', 40, 40, [Math.min(255, tint[0] + 60), Math.min(255, tint[1] + 60), Math.min(255, tint[2] + 60), 255], 2);
  drawText(raster, 'PHI', 40 + textWidth('AETHERMON', 2) + 8, 40, hexToRgb('#ffd75a'), 2);
  drawText(raster, 'SPIRAL UNIT', W - 40 - textWidth('SPIRAL UNIT', 1) - 18, 42, DIM, 1);
  for (let yy = -5; yy <= 5; yy++)
    for (let xx = -5; xx <= 5; xx++)
      if (xx * xx + yy * yy <= 25) blendPixel(raster, W - 34, 44, tint, xx * xx + yy * yy >= 9 ? 0.6 : 1);

  // Bezel + screen.
  const bx = 30,
    by = 60,
    bw = W - 60,
    bh = 486;
  roundRect(raster, bx, by, bw, bh, 18, [10, 10, 18, 255]);
  roundFrame(raster, bx, by, bw, bh, 18, [44, 44, 64, 255], 1, 1);
  const sx = bx + 12,
    sy = by + 12,
    sw = bw - 24,
    sh = bh - 24;
  roundRect(raster, sx, sy, sw, sh, 10, [6, 6, 12, 255]);
  // top tongue glow inside screen
  for (let yy = 0; yy < 60; yy++)
    for (let xx = 0; xx < sw; xx++)
      blendPixel(raster, sx + xx, sy + yy, tint, 0.06 * (1 - yy / 60));
  roundFrame(raster, sx, sy, sw, sh, 10, [tint[0], tint[1], tint[2], 255], 0.3, 1);

  // Status bar. Care and battle previews carry mode-appropriate status text.
  const region = mode === 'battle' ? 'AERIAL EXPANSE' : 'EMBER REACH';
  const status = mode === 'battle' ? 'ARENA 4/10' : 'CARE';
  drawText(raster, `${region} · GEN 1`, sx + 8, sy + 7, [Math.min(255, tint[0] + 40), Math.min(255, tint[1] + 40), Math.min(255, tint[2] + 40), 255], 1);
  drawText(raster, status, sx + sw - textWidth(status, 1) - 8, sy + 7, DIM, 1);

  const contentY = sy + 22;
  if (mode === 'care') drawCareScreen(raster, sx + 8, contentY, sw - 16, sh - 60);
  else drawBattleScreen(raster, sx + 8, contentY, sw - 16, sh - 60);

  // Log ticker.
  const logY = sy + sh - 34;
  roundRect(raster, sx, logY, sw, 34, 0, [0, 0, 0, 255], 0.4);
  if (mode === 'care') {
    drawText(raster, 'CINDER DEVOURS THE DATA-RATION.', sx + 8, logY + 6, [214, 214, 232, 255], 1);
    drawText(raster, 'HUNGER RESTORED.', sx + 8, logY + 20, hexToRgb('#6fe09a'), 1);
  } else {
    drawText(raster, 'BLAZEWARDEN USES SOLAR LANCE - 38 DMG', sx + 8, logY + 6, [214, 214, 232, 255], 1);
    drawText(raster, "IT'S SUPER EFFECTIVE!", sx + 8, logY + 20, hexToRgb('#6fe09a'), 1);
  }

  // Control deck.
  const deckY = by + bh + 20;
  drawDpad(raster, 46, deckY);
  const menuLabels =
    mode === 'care'
      ? ['FEED', 'TRAIN', 'PLAY', 'REST', 'PRAISE', 'SCOLD', 'CLEAN', 'PATCH', 'TUCK IN', 'BATTLE', 'ARENA', 'MAP', 'CODEX', 'PATHS', 'THE GAP']
      : ['EMBER JAB', 'CMD BURST', 'SOLAR LNC', 'LAT SLAM', 'GUARD', 'RUN'];
  const borders =
    mode === 'battle'
      ? [ELEMENT_HEX.KO, ELEMENT_HEX.KO, ELEMENT_HEX.KO, ELEMENT_HEX.DR, null, null]
      : null;
  drawMenu(raster, 140, deckY - 4, 210, menuLabels, tintHex, borders);
  drawAB(raster, W - 118, deckY + 20, tintHex);

  // Speaker grille + serial.
  for (let i = 0; i < 6; i++) roundRect(raster, 40 + i * 6, H - 40, 3, 16, 1, [35, 35, 58, 255]);
  drawText(raster, 'MDL SPRL-PHI V2', W - 40 - textWidth('MDL SPRL-PHI V2', 1), H - 32, [58, 58, 78, 255], 1);

  fs.writeFileSync(outFile, raster.png());
  console.log(`wrote ${outFile} (${W}x${H})`);
}

function drawCareScreen(raster, x, y, w, h) {
  const species = getSpecies('blazewarden');
  const monster = createMonster('blazewarden', 'Cinder');
  monster.level = 15;
  monster.xp = Math.floor(xpToNext(15) * 0.62);
  monster.trainBonus = { hp: 12, atk: 24, def: 6, spd: 6 };
  monster.care = { hunger: 82, energy: 48, mood: 90, bond: 66, discipline: 38, careMistakes: 1, starving: false, exhausted: false };
  monster.scars = 2;
  monster.residue = 2;
  const stats = effectiveStats(monster);

  // Diorama stage.
  const stageH = 150;
  const scene = sceneGrid('ember_reach', Math.ceil(w / 4), Math.ceil(stageH / 4), 0);
  // Static-residue piles on the pen floor (mirrors the web client).
  const sceneGroundY = Math.floor(scene.length * 0.82);
  for (let i = 0; i < monster.residue; i++) {
    const px2 = 8 + i * 18;
    for (const [dx, dy] of [[0, -1], [1, -1], [-1, 0], [0, 0], [1, 0], [2, 0]]) {
      const row = scene[sceneGroundY + dy];
      if (row && px2 + dx >= 0 && px2 + dx < row.length) row[px2 + dx] = dy === -1 ? '#4a4a5e' : '#2a2a38';
    }
  }
  roundRect(raster, x, y, w, stageH, 8, [5, 5, 12, 255]);
  for (let gy = 0; gy < scene.length; gy++)
    for (let gx = 0; gx < (scene[gy] || []).length; gx++) {
      const c = scene[gy][gx];
      if (!c) continue;
      const px = x + gx * 4,
        py = y + gy * 4;
      if (px < x + w - 1 && py < y + stageH - 1) raster.rect(px, py, 4, 4, parseColor(c));
    }
  roundFrame(raster, x, y, w, stageH, 8, [44, 44, 64, 255], 1, 1);
  // region tag (name text in a tinted pill)
  const rtw = textWidth('EMBER REACH', 1) + 10;
  roundRect(raster, x + 6, y + 6, rtw, 13, 4, hexToRgb(ELEMENT_HEX.KO), 0.16);
  roundFrame(raster, x + 6, y + 6, rtw, 13, 4, hexToRgb(ELEMENT_HEX.KO), 0.6, 1);
  drawText(raster, 'EMBER REACH', x + 11, y + 10, [255, 200, 160, 255], 1);
  // ground shadow + creature
  const grid = spriteForSpecies(species);
  const cs = 5;
  const gw = grid.length * cs;
  const creatureX = x + Math.floor((w - gw) / 2);
  const creatureY = y + stageH - grid.length * cs - 12;
  for (let sx2 = -22; sx2 <= 22; sx2++)
    blendPixel(raster, x + Math.floor(w / 2) + sx2, y + stageH - 12, [0, 0, 0], 0.4 * (1 - Math.abs(sx2) / 24));
  drawSpriteGrid(raster, grid, creatureX, creatureY, cs);

  let cy = y + stageH + 10;
  drawText(raster, 'CINDER', x, cy, [255, 255, 255, 255], 2);
  let chipX = x + textWidth('CINDER', 2) + 10;
  chipX += chip(raster, chipX, cy - 1, 'KO', TONGUE_NOTES.KO, ELEMENT_HEX.KO) + 4;
  chip(raster, chipX, cy - 1, 'AEGIS', '', ALIGN_HEX[species.alignment]);
  cy += 18;

  // XP bar.
  roundRect(raster, x, cy, w, 5, 2, [18, 18, 28, 255]);
  roundRect(raster, x, cy, Math.round(w * (monster.xp / xpToNext(15))), 5, 2, hexToRgb('#ffd75a'));
  cy += 14;

  // Two columns: stats | care meters, on faint panels.
  const colW = Math.floor((w - 14) / 2);
  const rx = x + colW + 14;
  roundRect(raster, x - 3, cy - 5, colW + 6, 88, 6, [18, 18, 28, 255], 0.55);
  roundRect(raster, rx - 3, cy - 5, colW + 6, 88, 6, [18, 18, 28, 255], 0.55);
  let ly = cy;
  ly = labeledBar(raster, x, ly, colW, 'HP', stats.hp, 220, '#51e08a', false, 8, 16);
  ly = labeledBar(raster, x, ly, colW, 'ATK', stats.atk, 220, '#ff8a6a', false, 8, 16);
  ly = labeledBar(raster, x, ly, colW, 'DEF', stats.def, 220, '#7ab6ff', false, 8, 16);
  ly = labeledBar(raster, x, ly, colW, 'SPD', stats.spd, 220, '#ffe07a', false, 8, 16);
  let ry = cy;
  ry = labeledBar(raster, rx, ry, colW, 'FOD', monster.care.hunger, 100, '#e0a24a', monster.care.hunger <= 25, 8, 16);
  ry = labeledBar(raster, rx, ry, colW, 'ENR', monster.care.energy, 100, '#4ac0e0', monster.care.energy <= 25, 8, 16);
  ry = labeledBar(raster, rx, ry, colW, 'MOD', monster.care.mood, 100, '#e0e04a', false, 8, 16);
  ry = labeledBar(raster, rx, ry, colW, 'BND', monster.care.bond, 100, '#e04a8a', false, 8, 16);

  let ty = Math.max(ly, ry) + 6;
  drawText(raster, '^ NEXT: SOLARCHON - NEEDS LEVEL 22', x, ty, hexToRgb('#ffd75a'), 1);
  ty += 14;
  let tx = x;
  for (const [label, hex] of [
    ['LV.15', '#9aa0b8'],
    ['GEN 1', '#9aa0b8'],
    ['LIFE 190', '#9aa0b8'],
    [`${monster.weightKb}KB`, '#9aa0b8'],
    [`STATIC ${monster.residue}`, '#ffb35a'],
    ['2 SCARS', '#ff9a7a'],
    ['HOLLOW 1', '#c08aff'],
  ]) {
    const tw = textWidth(label, 1) + 8;
    roundFrame(raster, tx, ty, tw, 13, 3, hexToRgb(hex), 0.7, 1);
    drawText(raster, label, tx + 4, ty + 4, hexToRgb(hex), 1);
    tx += tw + 5;
  }
}

function drawBattleScreen(raster, x, y, w, h) {
  const mine = getSpecies('blazewarden');
  const foe = getSpecies('skywarden');
  const stageH = h - 6;
  // scene
  const scene = sceneGrid('aerial_expanse', Math.ceil(w / 4), Math.ceil(stageH / 4), 0);
  roundRect(raster, x, y, w, stageH, 8, [5, 5, 12, 255]);
  for (let gy = 0; gy < scene.length; gy++)
    for (let gx = 0; gx < (scene[gy] || []).length; gx++) {
      const c = scene[gy][gx];
      if (!c) continue;
      const px = x + gx * 4,
        py = y + gy * 4;
      if (px < x + w - 1 && py < y + stageH - 1) raster.rect(px, py, 4, 4, parseColor(c));
    }
  roundFrame(raster, x, y, w, stageH, 8, [44, 44, 64, 255], 1, 1);
  drawText(raster, 'TURN 3', x + w - textWidth('TURN 3', 1) - 8, y + 6, DIM, 1);

  const mineGrid = spriteForSpecies(mine);
  const foeGrid = spriteForSpecies(foe);
  const scale = 4;
  const groundY = y + stageH - 92;
  drawSpriteGrid(raster, mineGrid, x + 30, groundY - mineGrid.length * scale + 60, scale);
  drawSpriteGrid(raster, foeGrid, x + w - 30 - foeGrid.length * scale, groundY - foeGrid.length * scale + 46, scale);
  drawText(raster, 'VS', x + Math.floor(w / 2) - 6, y + Math.floor(stageH / 2) - 20, hexToRgb('#ffd75a'), 3);

  // Fighter nameplates + HP.
  function plate(px, name, element, hp, maxHp, level) {
    drawText(raster, name, px, y + stageH - 46, [255, 255, 255, 255], 1);
    chip(raster, px + textWidth(name, 1) + 6, y + stageH - 49, element, TONGUE_NOTES[element], ELEMENT_HEX[element]);
    const barW = 150;
    roundRect(raster, px, y + stageH - 32, barW, 8, 3, [16, 16, 26, 255]);
    roundFrame(raster, px, y + stageH - 32, barW, 8, 3, [45, 45, 66, 255], 1, 1);
    const ratio = hp / maxHp;
    roundRect(raster, px + 1, y + stageH - 31, Math.round((barW - 2) * ratio), 6, 2, ratio > 0.25 ? hexToRgb('#51e08a') : hexToRgb('#ff6a4a'));
    // ticks
    for (let t = 24; t < barW; t += 24) raster.rect(px + t, y + stageH - 32, 1, 8, [0, 0, 0, 200]);
    drawText(raster, `${hp}/${maxHp} L${level}`, px, y + stageH - 20, DIM, 1);
  }
  plate(x + 10, 'CINDER', 'KO', 96, 121, 18);
  plate(x + w - 160, "SABLE'S", 'AV', 41, 117, 17);
}

const outDir = process.argv[2] ?? 'artifacts/aethermon';
fs.mkdirSync(outDir, { recursive: true });
renderSpriteSheet(path.join(outDir, 'aethermon-species-sheet.png'));
renderDevice(path.join(outDir, 'aethermon-care-ui.png'), 'care');
renderDevice(path.join(outDir, 'aethermon-battle-ui.png'), 'battle');
