/**
 * @file main.ts
 * @module aethermon/web/main
 * @layer Layer 14
 * @component AETHERMON Web — Browser Game UI
 *
 * The visual AETHERMON client: a virtual-pet handheld ("Spiral Unit")
 * rendered in DOM + canvas, driving the exact same tested game core as
 * the CLI. Procedural pixel sprites, region dioramas, animated battles,
 * a hex tongue-map, an illustrated Codex, and canon synesthesia — every
 * Sacred Tongue has its color and its note (KO=A 220Hz … DR=G 392Hz),
 * surfaced everywhere as element chips.
 *
 * Navigable by pointer, keyboard (arrows + A/S/Enter/Esc), or the drawn
 * D-pad and A/B buttons. Built with esbuild into
 * demos/aethermon/aethermon.js (see `npm run game:aethermon:web`).
 */

import type {
  Alignment,
  BattleAction,
  BattleState,
  Combatant,
  GameState,
  MonsterState,
  StatKey,
  TongueCode,
} from '../types.js';
import { STAGE_ORDER, STAT_KEYS, TONGUE_NAMES, TONGUE_NOTES } from '../types.js';
import { getMove } from '../moves.js';
import { STARTER_EGG_IDS, getSpecies, speciesByStage } from '../species.js';
import { REGIONS, getRegion } from '../regions.js';
import type { RegionId } from '../regions.js';
import {
  effectiveStats,
  feed,
  lifespanRemaining,
  play,
  praise,
  rest,
  scold,
  train,
  xpToNext,
} from '../monster.js';
import { evolutionOptions, evolve, selectEvolution } from '../evolution.js';
import {
  applyBattleResult,
  chooseAiAction,
  createBattle,
  performRound,
  toCombatant,
} from '../battle.js';
import {
  ARENA_LADDER,
  arenaCombatant,
  checkRebirth,
  communeWithGap,
  deserializeGame,
  generateWildEncounter,
  isChampion,
  newGame,
  nextArenaRival,
  recordBattleOutcome,
  serializeGame,
  travel,
  warmEgg,
} from '../game.js';
import { createRng, nextInt } from '../rng.js';
import { ALIGNMENT_HEX, ELEMENT_HEX, drawSprite, spriteForSpecies } from './sprites.js';
import { sceneGrid } from './scenes.js';

// ---------------------------------------------------------------------------
//  DOM + audio toolkit
// ---------------------------------------------------------------------------

const SAVE_KEY = 'aethermon-save';

function $(id: string): HTMLElement {
  const node = document.getElementById(id);
  if (!node) throw new Error(`missing #${id}`);
  return node;
}

function el(tag: string, className = '', text = ''): HTMLElement {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Canon synesthesia frequencies (Hz) per tongue. */
const TONGUE_FREQ: Record<TongueCode, number> = {
  KO: 220,
  AV: 247,
  RU: 277,
  CA: 311,
  UM: 349,
  DR: 392,
};

/** Meter presentation: icon glyph + accent color. */
const CARE_METERS: ReadonlyArray<{
  key: keyof MonsterState['care'];
  label: string;
  color: string;
}> = [
  { key: 'hunger', label: 'FOOD', color: '#e0a24a' },
  { key: 'energy', label: 'ENRG', color: '#4ac0e0' },
  { key: 'mood', label: 'MOOD', color: '#e0e04a' },
  { key: 'bond', label: 'BOND', color: '#e04a8a' },
  { key: 'discipline', label: 'DISC', color: '#8a8ae0' },
];

let audioCtx: AudioContext | null = null;
let muted = false;

function tone(freq: number, durationMs: number, delayMs = 0, gain = 0.04): void {
  if (muted) return;
  try {
    audioCtx = audioCtx ?? new AudioContext();
    const osc = audioCtx.createOscillator();
    const amp = audioCtx.createGain();
    osc.type = 'square';
    osc.frequency.value = freq;
    const start = audioCtx.currentTime + delayMs / 1000;
    amp.gain.setValueAtTime(gain, start);
    amp.gain.exponentialRampToValueAtTime(0.0001, start + durationMs / 1000);
    osc.connect(amp).connect(audioCtx.destination);
    osc.start(start);
    osc.stop(start + durationMs / 1000 + 0.02);
  } catch {
    /* audio is garnish — never let it break the game */
  }
}

const sfx = {
  hit: (element: TongueCode) => tone(TONGUE_FREQ[element], 130),
  miss: () => tone(110, 90),
  heal: (element: TongueCode) => {
    tone(TONGUE_FREQ[element], 90);
    tone(TONGUE_FREQ[element] * 1.5, 90, 100);
  },
  faint: () => {
    tone(196, 140);
    tone(147, 180, 130);
    tone(98, 260, 300);
  },
  evolve: () => {
    [220, 277, 349, 440, 554].forEach((f, i) => tone(f, 150, i * 110, 0.05));
  },
  levelUp: () => {
    tone(440, 90);
    tone(660, 120, 90);
  },
  click: () => tone(520, 35, 0, 0.02),
};

// ---------------------------------------------------------------------------
//  Chips & bars (Sacred Tongue synesthesia made visible)
// ---------------------------------------------------------------------------

/** Element chip: colored pill with tongue code + its canon note. */
function elementChip(element: TongueCode): HTMLElement {
  const chip = el('span', 'chip');
  chip.style.setProperty('--c', ELEMENT_HEX[element]);
  chip.title = `${TONGUE_NAMES[element]} — note ${TONGUE_NOTES[element]}`;
  chip.append(document.createTextNode(element));
  chip.append(el('span', 'note', TONGUE_NOTES[element]));
  return chip;
}

/** Alignment chip: AEGIS / VENOM / FLUX, colored by triangle role. */
function alignmentChip(alignment: Alignment): HTMLElement {
  const cls = alignment === 'VENOM' ? 'venom' : alignment === 'FLUX' ? 'flux' : '';
  const chip = el('span', `chip align ${cls}`.trim(), alignment);
  return chip;
}

function bar(fillClass: string, value: number, max: number, low = false): HTMLElement {
  const track = el('div', 'track');
  const fill = el('div', `fill ${fillClass}${low ? ' low' : ''}`);
  // A4: clamp the normalized fill to [0, 100]% so out-of-range stats/meters
  // (every stat bar and care meter flows through here) never overflow the track.
  fill.style.width = `${Math.max(0, Math.min(100, (value / max) * 100))}%`;
  track.append(fill);
  return track;
}

function statRow(label: string, key: StatKey, value: number, max: number): HTMLElement {
  const row = el('div', 'stat-row');
  row.append(
    el('span', 'stat-label', label),
    bar(key, value, max),
    el('span', 'stat-val', String(value))
  );
  return row;
}

function careMeterRow(label: string, value: number, color: string): HTMLElement {
  const row = el('div', 'meter');
  const track = bar('care', value, 100, value <= 25);
  (track.firstChild as HTMLElement).style.setProperty('--mc', color);
  row.append(el('span', 'meter-label', label), track, el('span', 'meter-val', String(value)));
  return row;
}

// ---------------------------------------------------------------------------
//  Game state
// ---------------------------------------------------------------------------

let state: GameState | null = null;
let spriteFrame = 0;

// Persistence is optional — blocked/sandboxed storage must never crash
// the game, so every localStorage touch goes through these guards.
function safeGetItem(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
function safeSetItem(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* keep playing in memory */
  }
}
function safeRemoveItem(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}
function saveState(): void {
  if (state) safeSetItem(SAVE_KEY, serializeGame(state));
}
function loadState(): GameState | null {
  const raw = safeGetItem(SAVE_KEY);
  if (!raw) return null;
  try {
    return deserializeGame(raw);
  } catch {
    return null;
  }
}
function battleSeed(game: GameState): number {
  const rng = createRng(game.rngState);
  const seed = nextInt(rng, 0, 2 ** 31 - 1);
  game.rngState = rng.state;
  return seed;
}

// ---------------------------------------------------------------------------
//  Screens & chrome
// ---------------------------------------------------------------------------

type ScreenId =
  'screen-title' | 'screen-egg' | 'screen-main' | 'screen-battle' | 'screen-codex' | 'screen-map';

const SCREENS: ScreenId[] = [
  'screen-title',
  'screen-egg',
  'screen-main',
  'screen-battle',
  'screen-codex',
  'screen-map',
];

function setScreen(id: ScreenId): void {
  for (const screen of SCREENS) $(screen).classList.toggle('hidden', screen !== id);
}

function currentTongue(): TongueCode {
  return state ? getRegion(state.region).tongue : 'KO';
}

function applyRegionTint(): void {
  document.documentElement.style.setProperty('--tint', ELEMENT_HEX[currentTongue()]);
}

/** Paint the current region's backdrop onto a scene canvas if present. */
function drawScene(canvasId: string): void {
  if (!state) return;
  const canvas = document.getElementById(canvasId) as HTMLCanvasElement | null;
  if (canvas) drawSprite(canvas, sceneGrid(state.region as RegionId, 64, 34, spriteFrame), 1);
}

function applyGlow(canvasId: string, element: TongueCode): void {
  const canvas = document.getElementById(canvasId);
  if (canvas) canvas.style.filter = `drop-shadow(0 0 7px ${ELEMENT_HEX[element]})`;
}

function statusLcd(): void {
  const lcd = $('lcd');
  lcd.replaceChildren();
  if (!state) {
    lcd.append(el('span', '', 'SPIRAL UNIT READY'));
    lcd.append(el('span', '', 'φ'));
    return;
  }
  const region = getRegion(state.region);
  lcd.append(el('span', '', `${region.name.toUpperCase()} · GEN ${state.generation}`));
  const right = el('span', '');
  right.append(document.createTextNode(`ARENA ${state.arenaRank}/${ARENA_LADDER.length}`));
  if (isChampion(state)) {
    const champ = el('span', 'champ', ' ★');
    right.append(champ);
  }
  lcd.append(right);
}

// ── In-screen log ─────────────────────────────────────────────────────────

const logLines: string[] = [];
function pushLog(text: string, cls = ''): void {
  logLines.push(text);
  if (logLines.length > 60) logLines.shift();
  const log = $('log');
  log.append(el('div', `log-line ${cls}`.trim(), text));
  while (log.children.length > 4) log.removeChild(log.firstChild as Node);
  log.scrollTop = log.scrollHeight;
}

// ---------------------------------------------------------------------------
//  Menu buttons with D-pad / keyboard focus
// ---------------------------------------------------------------------------

interface MenuButton {
  label: string;
  onClick: () => void;
  cls?: string;
  title?: string;
}

let focusIndex = 0;
const MENU_COLS = 3;

function renderButtons(buttons: MenuButton[]): void {
  const container = $('buttons');
  container.replaceChildren();
  for (const spec of buttons) {
    const button = el('button', `btn ${spec.cls ?? ''}`.trim(), spec.label) as HTMLButtonElement;
    if (spec.title) button.title = spec.title;
    button.addEventListener('click', () => {
      sfx.click();
      spec.onClick();
    });
    button.addEventListener('mouseenter', () => setFocus([...container.children].indexOf(button)));
    container.append(button);
  }
  focusIndex = Math.min(focusIndex, buttons.length - 1);
  if (focusIndex < 0) focusIndex = 0;
  paintFocus();
}

function menuButtons(): HTMLButtonElement[] {
  return [...$('buttons').children] as HTMLButtonElement[];
}

function paintFocus(): void {
  const buttons = menuButtons();
  buttons.forEach((b, i) => b.classList.toggle('focus', i === focusIndex));
}

function setFocus(index: number): void {
  const count = menuButtons().length;
  if (count === 0) return;
  focusIndex = ((index % count) + count) % count;
  paintFocus();
}

function moveFocus(dir: 'up' | 'down' | 'left' | 'right'): void {
  const count = menuButtons().length;
  if (count === 0) return;
  const delta = dir === 'left' ? -1 : dir === 'right' ? 1 : dir === 'up' ? -MENU_COLS : MENU_COLS;
  setFocus(focusIndex + delta);
  litDpad(dir);
}

function activateFocused(): void {
  const buttons = menuButtons();
  const target = buttons[focusIndex];
  if (target) target.click();
}

/** Back = click a BACK button if present. */
function pressBack(): void {
  const back = menuButtons().find((b) => b.textContent === 'BACK');
  if (back) back.click();
}

function litDpad(dir: string): void {
  const btn = document.querySelector(`.dpad button[data-dir="${dir}"]`);
  if (!btn) return;
  btn.classList.add('lit');
  setTimeout(() => btn.classList.remove('lit'), 140);
}

// ── Title screen ──────────────────────────────────────────────────────────

function renderTitle(): void {
  logLines.length = 0;
  $('log').replaceChildren();
  document.documentElement.style.setProperty('--tint', ELEMENT_HEX.KO);
  setScreen('screen-title');
  statusLcd();

  const eggRow = $('egg-row');
  eggRow.replaceChildren();
  let chosen = STARTER_EGG_IDS[0];
  const cards: HTMLElement[] = [];
  for (const eggId of STARTER_EGG_IDS) {
    const species = getSpecies(eggId);
    const card = el('div', 'egg-card');
    const canvas = document.createElement('canvas');
    canvas.className = 'pixel';
    drawSprite(canvas, spriteForSpecies(species), 5);
    card.append(canvas, elementChip(species.element), el('div', 'egg-name', species.name));
    card.style.setProperty('--egg-color', ELEMENT_HEX[species.element]);
    card.title = species.lore;
    card.addEventListener('click', () => {
      chosen = eggId;
      for (const other of cards) other.classList.remove('selected');
      card.classList.add('selected');
      sfx.click();
    });
    cards.push(card);
    eggRow.append(card);
  }
  cards[0].classList.add('selected');

  renderButtons([
    {
      label: 'BEGIN',
      cls: 'primary',
      onClick: () => {
        const name = ($('tamer-name') as HTMLInputElement).value.trim() || 'Tamer';
        state = newGame(name, chosen, Date.now() & 0x7fffffff);
        saveState();
        applyRegionTint();
        renderEgg();
      },
    },
  ]);
}

// ── Egg screen ────────────────────────────────────────────────────────────

function renderEgg(): void {
  if (!state?.egg) return renderMain();
  setScreen('screen-egg');
  applyRegionTint();
  const species = getSpecies(state.egg.speciesId);
  drawScene('egg-scene');
  drawSprite($('egg-canvas') as HTMLCanvasElement, spriteForSpecies(species, spriteFrame), 9);
  $('egg-title').textContent =
    `${species.name} · Generation ${state.egg.generation ?? state.generation}`;
  $('egg-warmth').textContent =
    '♥'.repeat(state.egg.warmth) + '·'.repeat(Math.max(0, 3 - state.egg.warmth));
  statusLcd();

  renderButtons([
    {
      label: 'WARM',
      cls: 'primary',
      onClick: () => {
        if (!state?.egg) return;
        const needsName = state.egg.warmth + 1 >= 3;
        let nickname = 'Aether';
        if (needsName) {
          nickname =
            (window.prompt('Name your creature:', 'Aether') ?? 'Aether').trim() || 'Aether';
        }
        const result = warmEgg(state, nickname);
        pushLog(result.message);
        tone(330, 80);
        saveState();
        if (result.hatched) {
          sfx.evolve();
          renderMain();
        } else {
          renderEgg();
        }
      },
    },
  ]);
}

// ── Care screen ───────────────────────────────────────────────────────────

function renderMain(): void {
  if (!state) return;
  if (state.egg) return renderEgg();
  const monster = state.monster;
  if (!monster) return renderTitle();
  setScreen('screen-main');
  applyRegionTint();
  statusLcd();

  const species = getSpecies(monster.speciesId);
  const stats = effectiveStats(monster);
  const region = getRegion(state.region);
  drawScene('main-scene');
  drawSprite($('monster-canvas') as HTMLCanvasElement, spriteForSpecies(species, spriteFrame), 6);
  applyGlow('monster-canvas', species.element);
  $('region-tag').textContent = region.name;

  $('monster-name').textContent = monster.nickname;
  $('chip-element').replaceChildren(elementChip(species.element));
  $('chip-align').replaceChildren(alignmentChip(species.alignment));

  const xpNeed = xpToNext(monster.level);
  ($('xp-fill') as HTMLElement).style.width =
    `${Math.min(100, (monster.xp / Math.max(1, xpNeed)) * 100)}%`;

  const statMax = 220;
  $('stat-panel').replaceChildren(
    statRow('HP', 'hp', stats.hp, statMax),
    statRow('ATK', 'atk', stats.atk, statMax),
    statRow('DEF', 'def', stats.def, statMax),
    statRow('SPD', 'spd', stats.spd, statMax)
  );

  $('meters').replaceChildren(
    ...CARE_METERS.map((m) => careMeterRow(m.label, monster.care[m.key] as number, m.color))
  );

  // Evolution hint: the branch it would take now, or the best locked one.
  const options = evolutionOptions(monster);
  const evo = $('evo-hint');
  evo.replaceChildren();
  if (options.length === 0) {
    evo.append(el('span', '', '▲'), el('span', '', 'Final form'));
  } else {
    const eligible = selectEvolution(monster);
    if (eligible) {
      evo.append(
        el('span', 'ready', '▲ READY:'),
        el('span', 'ready', getSpecies(eligible.targetId).name)
      );
    } else {
      const soonest = options[0];
      evo.append(
        el('span', '', '▲ next:'),
        el('span', '', getSpecies(soonest.requirement.targetId).name),
        el('span', '', `— ${soonest.blockedBy[0] ?? ''}`)
      );
    }
  }

  // Status tags.
  const tags = $('tags');
  tags.replaceChildren(
    el('span', 'tag', `Lv.${monster.level}`),
    el('span', 'tag', `Gen ${monster.generation}`),
    el('span', 'tag', `Life ${lifespanRemaining(monster)}`)
  );
  if (monster.scars > 0) tags.append(el('span', 'tag scar', `${monster.scars} scars`));
  if (monster.hollowExposure > 0)
    tags.append(el('span', 'tag hollow', `Hollow ${monster.hollowExposure}`));

  const buttons: MenuButton[] = [
    { label: 'FEED', onClick: () => care(() => feed(monster)) },
    { label: 'TRAIN', onClick: renderTrainPicker },
    { label: 'PLAY', onClick: () => care(() => play(monster)) },
    { label: 'REST', onClick: () => care(() => rest(monster)) },
    { label: 'PRAISE', onClick: () => care(() => praise(monster)) },
    { label: 'SCOLD', onClick: () => care(() => scold(monster)) },
    { label: 'BATTLE', cls: 'danger', onClick: () => void startWildBattle() },
    { label: 'ARENA', cls: 'danger', onClick: () => void startArenaBattle() },
    { label: 'MAP', onClick: renderMap },
    { label: 'CODEX', onClick: renderCodex },
    { label: 'PATHS', onClick: renderPaths, title: 'Evolution paths' },
  ];
  if (region.touchesHollow) {
    buttons.push({
      label: 'THE GAP',
      cls: 'hollow',
      onClick: () => {
        if (!state?.monster) return;
        const result = communeWithGap(state, state.monster);
        pushLog(result.message, result.ok ? 'hollow-text' : '');
        if (result.ok) tone(66, 600, 0, 0.06);
        afterAction();
      },
    });
  }
  buttons.push({ label: muted ? 'UNMUTE' : 'MUTE', onClick: toggleMute });
  buttons.push({
    label: 'RESET',
    title: 'Abandon this save and start over',
    onClick: () => {
      if (window.confirm('Abandon this line and start a new game?')) {
        safeRemoveItem(SAVE_KEY);
        state = null;
        renderTitle();
      }
    },
  });
  renderButtons(buttons);
}

function toggleMute(): void {
  muted = !muted;
  renderMain();
}

function care(action: () => { ok: boolean; message: string }): void {
  const result = action();
  pushLog(result.message, result.ok ? '' : 'warn');
  afterAction();
}

function renderTrainPicker(): void {
  if (!state?.monster) return;
  const monster = state.monster;
  renderButtons(
    (STAT_KEYS as readonly StatKey[])
      .map((stat) => ({
        label: `TRAIN ${stat.toUpperCase()}`,
        onClick: () => care(() => train(monster, stat)),
      }))
      .concat([{ label: 'BACK', onClick: renderMain }])
  );
}

function renderPaths(): void {
  if (!state?.monster) return;
  const options = evolutionOptions(state.monster);
  if (options.length === 0) pushLog(`${state.monster.nickname} has reached its final form.`);
  for (const option of options) {
    const target = getSpecies(option.requirement.targetId);
    pushLog(
      option.eligible
        ? `→ ${target.name}: READY`
        : `→ ${target.name}: ${option.blockedBy.join(', ')}`,
      option.eligible ? 'good' : ''
    );
  }
  renderMain();
}

// ── Codex (illustrated bestiary) ──────────────────────────────────────────

function renderCodex(): void {
  if (!state) return;
  setScreen('screen-codex');
  statusLcd();
  const owned = new Set(state.monster?.lineage ?? []);
  const currentId = state.monster?.speciesId;
  const body = $('codex-body');
  body.replaceChildren();

  for (const stage of STAGE_ORDER) {
    const list = speciesByStage(stage);
    if (list.length === 0) continue;
    body.append(el('div', 'codex-stage-label', stage));
    const grid = el('div', 'codex-grid');
    for (const species of list) {
      const cell = el('div', `codex-cell${owned.has(species.id) ? ' owned' : ''}`);
      cell.style.setProperty('--cc', ELEMENT_HEX[species.element]);
      const canvas = document.createElement('canvas');
      canvas.className = 'pixel';
      drawSprite(canvas, spriteForSpecies(species), 3);
      if (species.id === currentId)
        canvas.style.filter = `drop-shadow(0 0 5px ${ELEMENT_HEX[species.element]})`;
      cell.append(canvas, elementChip(species.element), el('div', 'cx-name', species.name));
      cell.title = species.lore;
      grid.append(cell);
    }
    body.append(grid);
  }
  renderButtons([{ label: 'BACK', cls: 'primary', onClick: renderMain }]);
}

// ── Region map (tongue hexagon) ───────────────────────────────────────────

function renderMap(): void {
  if (!state) return;
  setScreen('screen-map');
  statusLcd();
  const wheel = $('map-wheel');
  wheel.replaceChildren();

  const size = 260;
  const center = size / 2;
  const radius = 96;
  const points = REGIONS.map((_, i) => {
    const angle = (-90 + i * 60) * (Math.PI / 180);
    return { x: center + radius * Math.cos(angle), y: center + radius * Math.sin(angle) };
  });

  // Spokes + hexagon ring behind the nodes.
  const svgNs = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgNs, 'svg');
  const hex = document.createElementNS(svgNs, 'polygon');
  hex.setAttribute('points', points.map((p) => `${p.x},${p.y}`).join(' '));
  hex.setAttribute('fill', 'none');
  hex.setAttribute('stroke', 'rgba(255,255,255,.12)');
  hex.setAttribute('stroke-width', '1');
  svg.append(hex);
  for (const p of points) {
    const line = document.createElementNS(svgNs, 'line');
    line.setAttribute('x1', String(center));
    line.setAttribute('y1', String(center));
    line.setAttribute('x2', String(p.x));
    line.setAttribute('y2', String(p.y));
    line.setAttribute('stroke', 'rgba(255,255,255,.07)');
    svg.append(line);
  }
  wheel.append(svg);

  // Travel action shared by the visual wheel nodes (pointer) and the
  // focusable menu buttons below (keyboard / D-pad).
  const travelTo = (region: (typeof REGIONS)[number]): void => {
    if (!state) return;
    pushLog(travel(state, region.id));
    tone(TONGUE_FREQ[region.tongue], 160);
    saveState();
    renderMain();
  };

  REGIONS.forEach((region, i) => {
    const node = el(
      'div',
      `region-node${region.id === state!.region ? ' here' : ''}${region.touchesHollow ? ' hollow' : ''}`
    );
    node.style.setProperty('--rc', ELEMENT_HEX[region.tongue]);
    node.style.left = `${points[i].x}px`;
    node.style.top = `${points[i].y}px`;
    node.append(
      elementChip(region.tongue),
      el('div', 'rn-name', region.name),
      el(
        'div',
        'rn-tag',
        region.touchesHollow ? '◇ the gap' : region.id === state!.region ? 'you are here' : 'travel'
      )
    );
    node.title = region.description;
    node.addEventListener('click', () => {
      sfx.click();
      travelTo(region);
    });
    wheel.append(node);
  });

  const hub = el('div', 'wheel-center', 'φ');
  wheel.append(hub);

  // Region choices as focusable menu buttons so the map is fully operable by
  // keyboard / D-pad (moveFocus + A), not only by pointer clicks on the wheel.
  const buttons: MenuButton[] = REGIONS.map((region) => ({
    label: region.id === state!.region ? `· ${region.name} ·` : region.name,
    cls: region.touchesHollow ? 'hollow' : '',
    title: region.description,
    onClick: () => travelTo(region),
  }));
  buttons.push({ label: 'BACK', cls: 'primary', onClick: renderMain });
  renderButtons(buttons);
}

// ── Post-action bookkeeping ───────────────────────────────────────────────

function afterAction(): void {
  if (!state) return;
  const monster = state.monster;
  if (monster) {
    while (selectEvolution(monster) !== null) {
      const before = getSpecies(monster.speciesId);
      const result = evolve(monster);
      if (!result) break;
      const after = getSpecies(result.toSpeciesId);
      sfx.evolve();
      flashOverlay(
        'EVOLUTION',
        `${monster.nickname}: ${before.name} → ${after.name}`,
        ALIGNMENT_HEX[after.alignment]
      );
      pushLog(`✦ ${monster.nickname} evolved into ${after.name}! (${after.stage})`, 'good');
      if (after.stage === 'APEX') {
        state.hallOfFame.push(`${monster.nickname} the ${after.name}`);
        pushLog(`${monster.nickname} enters the Hall of Fame!`, 'good');
      }
    }
    const rebirth = checkRebirth(state);
    if (rebirth) {
      sfx.faint();
      flashOverlay('THE SPIRAL TURNS', rebirth.memorialEntry, '#B05CFF');
      pushLog(
        `${rebirth.memorialEntry} — its strength echoes into Generation ${rebirth.nextGeneration}.`,
        'hollow-text'
      );
      saveState();
      renderEgg();
      return;
    }
  }
  saveState();
  renderMain();
}

function flashOverlay(title: string, subtitle: string, color: string): void {
  const overlay = $('overlay');
  overlay.style.setProperty('--flash', color);
  $('overlay-title').textContent = title;
  $('overlay-sub').textContent = subtitle;
  overlay.classList.remove('hidden', 'animate');
  void overlay.offsetWidth;
  overlay.classList.add('animate');
  setTimeout(() => overlay.classList.add('hidden'), 2400);
}

// ---------------------------------------------------------------------------
//  Battle
// ---------------------------------------------------------------------------

interface BattleSession {
  battle: BattleState;
  wasArena: boolean;
  busy: boolean;
}
let session: BattleSession | null = null;

async function startWildBattle(): Promise<void> {
  if (!state?.monster) return;
  await beginBattle(generateWildEncounter(state, state.monster), false);
}

async function startArenaBattle(): Promise<void> {
  if (!state?.monster) return;
  const rival = nextArenaRival(state);
  if (!rival) {
    pushLog('You have already conquered the Spiral Arena!', 'good');
    renderMain();
    return;
  }
  pushLog(`Arena rung ${state.arenaRank + 1}: ${rival.name}, ${rival.title}`);
  await beginBattle(arenaCombatant(rival), true);
}

async function beginBattle(enemy: Combatant, wasArena: boolean): Promise<void> {
  if (!state?.monster) return;
  const mine = toCombatant(state.monster);
  session = { battle: createBattle(mine, enemy, battleSeed(state)), wasArena, busy: false };
  setScreen('screen-battle');
  renderBattle();
  pushLog(`⚔ ${mine.name} vs ${enemy.name} (Lv.${enemy.level})`);
  await sleep(150);
}

function battleHp(side: 'a' | 'b', combatant: Combatant): void {
  const fill = $(`hp-${side}`);
  fill.style.width = `${(combatant.hp / Math.max(1, combatant.stats.hp)) * 100}%`;
  fill.classList.toggle('low', combatant.hp <= combatant.stats.hp * 0.25);
  $(`hp-${side}-text`).textContent = `${combatant.hp}/${combatant.stats.hp}`;
}

function renderBattle(): void {
  if (!session || !state?.monster) return;
  const { battle } = session;
  drawScene('battle-scene');
  drawSprite(
    $('battle-mine') as HTMLCanvasElement,
    spriteForSpecies(getSpecies(battle.a.speciesId), spriteFrame),
    6
  );
  drawSprite(
    $('battle-foe') as HTMLCanvasElement,
    spriteForSpecies(getSpecies(battle.b.speciesId), spriteFrame),
    6
  );
  applyGlow('battle-mine', battle.a.element);
  applyGlow('battle-foe', battle.b.element);
  $('pa-name').textContent = `${battle.a.name} L${battle.a.level}`;
  $('pb-name').textContent = `${battle.b.name} L${battle.b.level}`;
  $('pa-chip').replaceChildren(elementChip(battle.a.element));
  $('pb-chip').replaceChildren(elementChip(battle.b.element));
  $('turn-tag').textContent = `TURN ${battle.turn}`;
  battleHp('a', battle.a);
  battleHp('b', battle.b);

  const species = getSpecies(battle.a.speciesId);
  const moves: MenuButton[] = species.moves.map((moveId) => {
    const move = getMove(moveId);
    return {
      label: move.name.toUpperCase(),
      cls: 'move',
      title: `${TONGUE_NAMES[move.element]} · ${move.effect === 'heal' ? 'heal' : `pow ${move.power}`} · acc ${Math.round(move.accuracy * 100)}%`,
      onClick: () => void playerTurn({ type: 'move', moveId }),
    };
  });
  moves.push({
    label: 'GUARD',
    title: 'Halve damage this round',
    onClick: () => void playerTurn({ type: 'guard' }),
  });
  moves.push({
    label: 'RUN',
    cls: 'danger',
    title: 'Flee (counts as a loss)',
    onClick: () => void fleeBattle(),
  });
  renderButtons(moves);
}

function replayClass(node: HTMLElement, className: string): void {
  node.classList.remove(className);
  void node.offsetWidth;
  node.classList.add(className);
}

function damageFloat(fighterId: string, text: string, cls: string): void {
  const float = el('span', `dmg-float ${cls}`.trim(), text);
  float.style.left = `${30 + Math.random() * 40}%`;
  $(fighterId).append(float);
  setTimeout(() => float.remove(), 950);
}

function sparkBurst(fighterId: string, element: TongueCode): void {
  const fighter = $(fighterId);
  for (let i = 0; i < 8; i++) {
    const spark = el('span', 'spark');
    spark.style.background = ELEMENT_HEX[element];
    spark.style.color = ELEMENT_HEX[element];
    spark.style.setProperty('--dx', `${(Math.random() - 0.5) * 74}px`);
    spark.style.setProperty('--dy', `${-20 - Math.random() * 54}px`);
    spark.style.left = '50%';
    spark.style.top = '38%';
    fighter.append(spark);
    setTimeout(() => spark.remove(), 650);
  }
}

async function playerTurn(action: BattleAction): Promise<void> {
  if (!session || session.busy || !state?.monster) return;
  session.busy = true;
  const { battle } = session;
  const enemyAction = chooseAiAction(battle, 'B');
  const events = performRound(battle, action, enemyAction);
  for (const event of events) {
    pushLog(event.text, event.kind === 'crit' ? 'good' : '');
    const actor = event.actor === 'A' ? battle.a : battle.b;
    const actorFighter = event.actor === 'A' ? 'fighter-a' : 'fighter-b';
    const targetFighter = event.actor === 'A' ? 'fighter-b' : 'fighter-a';
    const targetCanvas = event.actor === 'A' ? 'battle-foe' : 'battle-mine';
    if (event.kind === 'move' || event.kind === 'crit') {
      const moveElement = event.moveId ? getMove(event.moveId).element : actor.element;
      sfx.hit(moveElement);
      replayClass($(actorFighter), event.actor === 'A' ? 'lunge-right' : 'lunge-left');
      replayClass($(targetCanvas), 'shake');
      if (event.damage !== undefined) {
        damageFloat(targetFighter, `-${event.damage}`, event.kind === 'crit' ? 'crit' : '');
        sparkBurst(targetFighter, moveElement);
      }
    } else if (event.kind === 'miss') {
      sfx.miss();
      damageFloat(targetFighter, 'MISS', 'miss');
    } else if (event.kind === 'heal' || event.kind === 'drain') {
      sfx.heal(actor.element);
      if (event.healed !== undefined) damageFloat(actorFighter, `+${event.healed}`, 'heal');
    } else if (event.kind === 'faint') {
      sfx.faint();
      $(event.actor === 'A' ? 'battle-mine' : 'battle-foe').classList.add('fainted');
    }
    $('turn-tag').textContent = `TURN ${battle.turn}`;
    battleHp('a', battle.a);
    battleHp('b', battle.b);
    await sleep(420);
  }
  session.busy = false;
  if (battle.over) await finishBattle(false);
  else renderBattle();
}

async function fleeBattle(): Promise<void> {
  if (!session || session.busy) return;
  pushLog('You retreat! (counts as a loss)', 'warn');
  await finishBattle(true);
}

async function finishBattle(fled: boolean): Promise<void> {
  if (!session || !state?.monster) return;
  const monster = state.monster;
  const { battle, wasArena } = session;
  const won = !fled && battle.winner === 'A';
  const enemyLevel = battle.b.level;
  const aftermath = applyBattleResult(monster, won);
  const levels = recordBattleOutcome(state, monster, enemyLevel, won, wasArena);
  if (battle.winner === 'DRAW') pushLog('A draw!');
  else pushLog(won ? '★ VICTORY!' : 'Defeat...', won ? 'good' : 'warn');
  if (aftermath.scarred) pushLog(`A new scar. (${monster.scars} total — its guard hardens.)`);
  if (aftermath.strained) pushLog(`${monster.nickname} is overworked — let it rest.`, 'warn');
  if (levels > 0) {
    sfx.levelUp();
    pushLog(`${monster.nickname} grew to Lv.${monster.level}!`, 'good');
  }
  if (wasArena && won && isChampion(state)) {
    flashOverlay('SPIRAL ARENA CHAMPION', `${state.tamerName} & ${monster.nickname}`, '#FFD75A');
    pushLog('★ ★ ★ You rule the Spiral Arena! ★ ★ ★', 'good');
  } else if (wasArena && won) {
    const rival = nextArenaRival(state);
    if (rival) pushLog(`Next arena rival: ${rival.name}, ${rival.title} (Lv.${rival.level})`);
  }
  $('battle-mine').classList.remove('fainted');
  $('battle-foe').classList.remove('fainted');
  session = null;
  await sleep(500);
  afterAction();
}

// ---------------------------------------------------------------------------
//  Global controls (keyboard + drawn D-pad / A / B)
// ---------------------------------------------------------------------------

function wireControls(): void {
  document.querySelectorAll<HTMLButtonElement>('.dpad button[data-dir]').forEach((btn) => {
    btn.addEventListener('click', () =>
      moveFocus(btn.dataset.dir as 'up' | 'down' | 'left' | 'right')
    );
  });
  $('btn-a').addEventListener('click', () => {
    sfx.click();
    activateFocused();
  });
  $('btn-b').addEventListener('click', () => {
    sfx.click();
    pressBack();
  });

  window.addEventListener('keydown', (e) => {
    if ((e.target as HTMLElement)?.tagName === 'INPUT') return;
    switch (e.key) {
      case 'ArrowUp':
      case 'w':
        moveFocus('up');
        e.preventDefault();
        break;
      case 'ArrowDown':
      case 's':
        moveFocus('down');
        e.preventDefault();
        break;
      case 'ArrowLeft':
      case 'a':
        moveFocus('left');
        e.preventDefault();
        break;
      case 'ArrowRight':
      case 'd':
        moveFocus('right');
        e.preventDefault();
        break;
      case 'Enter':
      case ' ':
        activateFocused();
        e.preventDefault();
        break;
      case 'Escape':
      case 'Backspace':
        pressBack();
        e.preventDefault();
        break;
    }
  });
}

// ---------------------------------------------------------------------------
//  Boot
// ---------------------------------------------------------------------------

function boot(): void {
  wireControls();
  state = loadState();
  applyRegionTint();
  setInterval(() => {
    spriteFrame = (spriteFrame + 1) % 2;
    if (session) {
      renderBattle();
    } else if (state?.egg && !$('screen-egg').classList.contains('hidden')) {
      drawScene('egg-scene');
      drawSprite(
        $('egg-canvas') as HTMLCanvasElement,
        spriteForSpecies(getSpecies(state.egg.speciesId), spriteFrame),
        9
      );
    } else if (state?.monster && !$('screen-main').classList.contains('hidden')) {
      drawScene('main-scene');
      drawSprite(
        $('monster-canvas') as HTMLCanvasElement,
        spriteForSpecies(getSpecies(state.monster.speciesId), spriteFrame),
        6
      );
    }
  }, 650);

  if (!state) {
    renderTitle();
  } else {
    pushLog(`Welcome back, ${state.tamerName}.`);
    if (state.egg) renderEgg();
    else renderMain();
  }
}

document.addEventListener('DOMContentLoaded', boot);
