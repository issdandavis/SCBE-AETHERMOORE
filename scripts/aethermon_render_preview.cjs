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
const { STAGE_ORDER } = require('../dist/src/aethermon/types.js');

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
    for (let gx = 0; gx < grid.length; gx++) {
      const color = grid[gy][gx];
      if (!color) continue;
      raster.rect(x + gx * scale, y + gy * scale, scale, scale, parseColor(color));
    }
  }
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
  drawText(raster, '39 SPECIES OF THE AETHERMOORE REALM', margin, 46, DIM, 2);

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

// ── Battle mock: what the web game's battle screen looks like ───────────

function renderBattleMock(outFile) {
  const width = 920;
  const height = 600;
  const raster = new Raster(width, height);

  // Region-tinted backdrop (Aerial Expanse).
  const tint = hexToRgb(ELEMENT_HEX.AV);
  for (let y = 0; y < height; y++) {
    const t = Math.max(0, 1 - y / (height * 0.7));
    raster.rect(0, y, width, 1, [
      Math.round(10 + tint[0] * 0.14 * t),
      Math.round(10 + tint[1] * 0.14 * t),
      Math.round(18 + tint[2] * 0.1 * t),
      255,
    ]);
  }

  drawText(raster, 'AETHERMON', 30, 22, GOLD, 4);
  drawText(raster, 'AERIAL EXPANSE - WILD BATTLE', 30, 52, DIM, 2);

  const mine = getSpecies('blazewarden');
  const foe = getSpecies('skywarden');
  const mineGrid = spriteForSpecies(mine);
  const foeGrid = spriteForSpecies(foe);

  // Fighters.
  drawSpriteGrid(raster, mineGrid, 120, 150, 12);
  drawSpriteGrid(raster, foeGrid, width - 120 - foeGrid.length * 12, 130, 12);
  drawText(raster, 'VS', Math.floor(width / 2) - 12, 220, GOLD, 4);

  // Name plates + HP bars.
  function plate(x, name, element, hp, maxHp) {
    drawText(raster, name, x, 340, hexToRgb(ELEMENT_HEX[element]), 2);
    raster.rect(x, 360, 280, 16, [28, 28, 43, 255]);
    raster.frame(x, 360, 280, 16, [45, 45, 68, 255]);
    const ratio = hp / maxHp;
    raster.rect(x + 2, 362, Math.round(276 * ratio), 12, ratio > 0.25 ? [81, 224, 138, 255] : [255, 99, 71, 255]);
    drawText(raster, `${hp}/${maxHp}`, x + 290, 362, DIM, 2);
  }
  plate(80, `${mine.name} LV 18`, mine.element, 96, 121);
  plate(width - 80 - 360, `${foe.name} LV 17`, foe.element, 41, 117);

  // Battle log panel.
  raster.rect(60, 400, width - 120, 90, PANEL);
  raster.frame(60, 400, width - 120, 90, [38, 38, 58, 255]);
  drawText(raster, 'BLAZEWARDEN USES SOLAR LANCE - 38 DAMAGE', 76, 414, [216, 216, 232, 255], 2);
  drawText(raster, 'ITS SUPER EFFECTIVE', 76, 438, hexToRgb('#6FE09A'), 2);
  drawText(raster, 'SKYWARDEN USES SKYFALL DIVE - 22 DAMAGE', 76, 462, [216, 216, 232, 255], 2);

  // Move buttons.
  const moves = mine.moves.map((id) => id.replace(/_/g, ' ').toUpperCase()).concat(['GUARD', 'RUN']);
  const btnW = Math.floor((width - 120 - (moves.length - 1) * 10) / moves.length);
  moves.forEach((label, i) => {
    const bx = 60 + i * (btnW + 10);
    raster.rect(bx, 510, btnW, 46, [30, 30, 48, 255]);
    raster.frame(bx, 510, btnW, 46, i >= moves.length - 2 ? [120, 120, 150, 255] : parseColor(ELEMENT_HEX[mine.element]));
    const scale = textWidth(label, 2) > btnW - 8 ? 1 : 2;
    drawText(raster, label, bx + Math.max(4, Math.floor((btnW - textWidth(label, scale)) / 2)), 510 + (scale === 1 ? 20 : 16), [216, 216, 232, 255], scale);
  });

  fs.writeFileSync(outFile, raster.png());
  console.log(`wrote ${outFile} (${width}x${height})`);
}

const outDir = process.argv[2] ?? 'artifacts/aethermon';
fs.mkdirSync(outDir, { recursive: true });
renderSpriteSheet(path.join(outDir, 'aethermon-species-sheet.png'));
renderBattleMock(path.join(outDir, 'aethermon-battle-preview.png'));
