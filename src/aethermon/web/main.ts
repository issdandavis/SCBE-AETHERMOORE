/**
 * @file main.ts
 * @module aethermon/web/main
 * @layer Layer 14
 * @component AETHERMON Web — Browser Game UI
 *
 * The visual AETHERMON client: a virtual-pet device shell rendered in
 * DOM + canvas, driving the exact same tested game core as the CLI.
 * Procedural pixel sprites, animated battles, region-tinted scenes,
 * localStorage saves, and canon synesthesia tones (each tongue sounds
 * its note — KO=A 220Hz … DR=G 392Hz).
 *
 * Built with esbuild into demos/aethermon/aethermon.js (see
 * `npm run game:aethermon:web`).
 */

import type {
  BattleAction,
  BattleState,
  Combatant,
  GameState,
  MonsterState,
  StatKey,
  TongueCode,
} from '../types.js';
import { STAT_KEYS, TONGUE_NOTES } from '../types.js';
import { getMove } from '../moves.js';
import { STARTER_EGG_IDS, getSpecies } from '../species.js';
import { REGIONS, getRegion } from '../regions.js';
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
import type { RegionId } from '../regions.js';

// ---------------------------------------------------------------------------
//  Tiny DOM + audio toolkit
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
//  Game state container
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
    /* storage unavailable; keep playing in memory */
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
//  Rendering
// ---------------------------------------------------------------------------

function setScreen(id: 'screen-title' | 'screen-egg' | 'screen-main' | 'screen-battle'): void {
  for (const screen of ['screen-title', 'screen-egg', 'screen-main', 'screen-battle']) {
    $(screen).classList.toggle('hidden', screen !== id);
  }
}

function applyRegionTint(): void {
  const tongue = state ? getRegion(state.region).tongue : 'KO';
  document.documentElement.style.setProperty('--tint', ELEMENT_HEX[tongue]);
}

/** Paint the current region's backdrop onto a scene canvas. */
function drawScene(canvasId: string): void {
  if (!state) return;
  const canvas = document.getElementById(canvasId) as HTMLCanvasElement | null;
  if (!canvas) return;
  drawSprite(canvas, sceneGrid(state.region as RegionId, 64, 34, spriteFrame), 1);
}

/** Element-colored glow around a sprite canvas. */
function applyGlow(canvasId: string, element: TongueCode): void {
  const canvas = document.getElementById(canvasId);
  if (canvas) canvas.style.filter = `drop-shadow(0 0 7px ${ELEMENT_HEX[element]})`;
}

function renderButtons(
  container: HTMLElement,
  buttons: Array<{ label: string; onClick: () => void; cls?: string; title?: string }>
): void {
  container.replaceChildren();
  for (const spec of buttons) {
    const button = el('button', `btn ${spec.cls ?? ''}`.trim(), spec.label) as HTMLButtonElement;
    if (spec.title) button.title = spec.title;
    button.addEventListener('click', () => {
      sfx.click();
      spec.onClick();
    });
    container.append(button);
  }
}

function meter(label: string, value: number, max = 100): HTMLElement {
  const wrap = el('div', 'meter');
  wrap.append(el('span', 'meter-label', label));
  const track = el('div', 'meter-track');
  const fill = el('div', 'meter-fill');
  fill.style.width = `${Math.max(0, Math.min(100, (value / max) * 100))}%`;
  if (value <= max * 0.25) fill.classList.add('low');
  track.append(fill);
  wrap.append(track);
  return wrap;
}

function statusLcd(): void {
  if (!state) return;
  const region = getRegion(state.region);
  $('lcd').textContent =
    `${region.name} · Gen ${state.generation} · Arena ${state.arenaRank}/${ARENA_LADDER.length}` +
    (isChampion(state) ? ' · CHAMPION ★' : '');
}

const logLines: string[] = [];
function pushLog(text: string, cls = ''): void {
  logLines.push(text);
  if (logLines.length > 60) logLines.shift();
  const log = $('log');
  const line = el('div', `log-line ${cls}`.trim(), text);
  log.append(line);
  while (log.children.length > 8) log.removeChild(log.firstChild as Node);
  log.scrollTop = log.scrollHeight;
}

// ── Title screen ─────────────────────────────────────────────────────────

function renderTitle(): void {
  // Fresh line, fresh screen: clear old messages and the region tint.
  logLines.length = 0;
  $('log').replaceChildren();
  document.documentElement.style.setProperty('--tint', ELEMENT_HEX.KO);
  setScreen('screen-title');
  const eggRow = $('egg-row');
  eggRow.replaceChildren();
  let chosen = STARTER_EGG_IDS[0];
  const cards: HTMLElement[] = [];
  for (const eggId of STARTER_EGG_IDS) {
    const species = getSpecies(eggId);
    const card = el('div', 'egg-card');
    const canvas = document.createElement('canvas');
    canvas.className = 'pixel';
    drawSprite(canvas, spriteForSpecies(species), 6);
    card.append(canvas, el('div', 'egg-name', species.name));
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

  renderButtons($('buttons'), [
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
  $('lcd').textContent = 'A creature of Aethermoore is waiting.';
}

// ── Egg screen ───────────────────────────────────────────────────────────

function renderEgg(): void {
  if (!state?.egg) return renderMain();
  setScreen('screen-egg');
  const species = getSpecies(state.egg.speciesId);
  const canvas = $('egg-canvas') as HTMLCanvasElement;
  drawSprite(canvas, spriteForSpecies(species, spriteFrame), 10);
  $('egg-title').textContent =
    `${species.name} · Generation ${state.egg.generation ?? state.generation}`;
  $('egg-warmth').textContent =
    '♥'.repeat(state.egg.warmth) + '·'.repeat(Math.max(0, 3 - state.egg.warmth));
  statusLcd();

  renderButtons($('buttons'), [
    {
      label: 'WARM THE EGG',
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

// ── Main (care) screen ───────────────────────────────────────────────────

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
  drawScene('main-scene');
  drawSprite($('monster-canvas') as HTMLCanvasElement, spriteForSpecies(species, spriteFrame), 8);
  applyGlow('monster-canvas', species.element);
  $('monster-name').textContent = `${monster.nickname}`;
  $('monster-species').textContent =
    `${species.name} · ${species.stage} · ${species.element}/${species.alignment}`;
  ($('monster-species') as HTMLElement).style.color = ELEMENT_HEX[species.element];
  $('monster-stats').textContent =
    `Lv.${monster.level}  XP ${monster.xp}/${xpToNext(monster.level)}  ` +
    `HP ${stats.hp} ATK ${stats.atk} DEF ${stats.def} SPD ${stats.spd}`;
  $('monster-extra').textContent =
    `Gen ${monster.generation} · Scars ${monster.scars} · Hollow ${monster.hollowExposure} · ` +
    `Lifespan ${lifespanRemaining(monster)} · sounds in ${TONGUE_NOTES[species.element]}`;

  const meters = $('meters');
  meters.replaceChildren(
    meter('FOOD', monster.care.hunger),
    meter('ENRG', monster.care.energy),
    meter('MOOD', monster.care.mood),
    meter('BOND', monster.care.bond),
    meter('DISC', monster.care.discipline)
  );

  const region = getRegion(state.region);
  const buttons: Array<{ label: string; onClick: () => void; cls?: string; title?: string }> = [
    { label: 'FEED', onClick: () => care(() => feed(monster)) },
    { label: 'TRAIN', onClick: renderTrainPicker },
    { label: 'PLAY', onClick: () => care(() => play(monster)) },
    { label: 'REST', onClick: () => care(() => rest(monster)) },
    { label: 'PRAISE', onClick: () => care(() => praise(monster)) },
    { label: 'SCOLD', onClick: () => care(() => scold(monster)) },
    { label: 'BATTLE', cls: 'danger', onClick: () => void startWildBattle() },
    { label: 'ARENA', cls: 'danger', onClick: () => void startArenaBattle() },
    { label: 'TRAVEL', onClick: renderTravelPicker },
    { label: 'PATHS', onClick: renderPaths, title: 'Evolution paths' },
  ];
  if (region.touchesHollow) {
    buttons.push({
      label: 'THE GAP',
      cls: 'hollow',
      onClick: () => {
        if (!state || !state.monster) return;
        const result = communeWithGap(state, state.monster);
        pushLog(result.message, result.ok ? 'hollow-text' : '');
        if (result.ok) tone(66, 600, 0, 0.06);
        afterAction();
      },
    });
  }
  buttons.push({ label: muted ? 'UNMUTE' : 'MUTE', onClick: toggleMute });
  buttons.push({
    label: 'NEW LINE',
    title: 'Abandon this save and start over',
    onClick: () => {
      if (window.confirm('Abandon this line and start a new game?')) {
        safeRemoveItem(SAVE_KEY);
        state = null;
        renderTitle();
      }
    },
  });
  renderButtons($('buttons'), buttons);
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
    $('buttons'),
    (STAT_KEYS as readonly StatKey[])
      .map((stat) => ({
        label: `TRAIN ${stat.toUpperCase()}`,
        onClick: () => {
          care(() => train(monster, stat));
        },
      }))
      .concat([{ label: 'BACK', onClick: renderMain }])
  );
}

function renderTravelPicker(): void {
  if (!state) return;
  renderButtons(
    $('buttons'),
    REGIONS.map((region) => ({
      label: region.id === state!.region ? `· ${region.name} ·` : region.name,
      onClick: () => {
        pushLog(travel(state!, region.id));
        tone(TONGUE_FREQ[region.tongue], 160);
        afterAction();
      },
    })).concat([{ label: 'BACK', onClick: renderMain }])
  );
}

function renderPaths(): void {
  if (!state?.monster) return;
  const options = evolutionOptions(state.monster);
  if (options.length === 0) {
    pushLog(`${state.monster.nickname} has reached its final form.`);
  }
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

/** Post-action bookkeeping: evolution, rebirth, autosave, re-render. */
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
  overlay.style.setProperty('--flash-color', color);
  $('overlay-title').textContent = title;
  $('overlay-sub').textContent = subtitle;
  overlay.classList.remove('hidden');
  overlay.classList.remove('animate');
  void overlay.offsetWidth; // restart the CSS animation
  overlay.classList.add('animate');
  setTimeout(() => overlay.classList.add('hidden'), 2400);
}

// ── Battle screen ────────────────────────────────────────────────────────

interface BattleSession {
  battle: BattleState;
  enemySpeciesId: string;
  wasArena: boolean;
  busy: boolean;
}
let session: BattleSession | null = null;

async function startWildBattle(): Promise<void> {
  if (!state?.monster) return;
  const enemy = generateWildEncounter(state, state.monster);
  await beginBattle(enemy, false);
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
  session = {
    battle: createBattle(mine, enemy, battleSeed(state)),
    enemySpeciesId: enemy.speciesId,
    wasArena,
    busy: false,
  };
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
  $('battle-mine-name').textContent = `${battle.a.name} Lv.${battle.a.level}`;
  $('battle-foe-name').textContent = `${battle.b.name} Lv.${battle.b.level}`;
  battleHp('a', battle.a);
  battleHp('b', battle.b);

  const species = getSpecies(battle.a.speciesId);
  renderButtons(
    $('buttons'),
    species.moves
      .map((moveId) => {
        const move = getMove(moveId);
        return {
          label: move.name.toUpperCase(),
          title: `${move.element} · ${move.effect === 'heal' ? 'heal' : `pow ${move.power}`} · acc ${move.accuracy}`,
          onClick: () => void playerTurn({ type: 'move', moveId }),
        };
      })
      .concat([
        {
          label: 'GUARD',
          title: 'Halve damage this round',
          onClick: () => void playerTurn({ type: 'guard' }),
        },
        { label: 'RUN', title: 'Flee (counts as a loss)', onClick: () => void fleeBattle() },
      ])
  );
}

/** Restartable CSS animation: remove, reflow, add. */
function replayClass(node: HTMLElement, className: string): void {
  node.classList.remove(className);
  void node.offsetWidth;
  node.classList.add(className);
}

/** Floating combat number over a fighter (visual only — no game RNG). */
function damageFloat(fighterId: string, text: string, cls: string): void {
  const fighter = $(fighterId);
  const float = el('span', `dmg-float ${cls}`.trim(), text);
  float.style.left = `${30 + Math.random() * 40}%`;
  fighter.append(float);
  setTimeout(() => float.remove(), 950);
}

/** Burst of element-colored sparks on impact (visual only). */
function sparkBurst(fighterId: string, element: TongueCode): void {
  const fighter = $(fighterId);
  for (let i = 0; i < 7; i++) {
    const spark = el('span', 'spark');
    spark.style.background = ELEMENT_HEX[element];
    spark.style.setProperty('--dx', `${(Math.random() - 0.5) * 70}px`);
    spark.style.setProperty('--dy', `${-20 - Math.random() * 50}px`);
    spark.style.left = '50%';
    spark.style.top = '40%';
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
    const actorCombatant = event.actor === 'A' ? battle.a : battle.b;
    const actorFighter = event.actor === 'A' ? 'fighter-a' : 'fighter-b';
    const targetFighter = event.actor === 'A' ? 'fighter-b' : 'fighter-a';
    const targetCanvas = event.actor === 'A' ? 'battle-foe' : 'battle-mine';
    if (event.kind === 'move' || event.kind === 'crit') {
      const moveElement = event.moveId ? getMove(event.moveId).element : actorCombatant.element;
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
      sfx.heal(actorCombatant.element);
      if (event.healed !== undefined) damageFloat(actorFighter, `+${event.healed}`, 'heal');
    } else if (event.kind === 'faint') {
      sfx.faint();
      $(event.actor === 'A' ? 'battle-mine' : 'battle-foe').classList.add('fainted');
    }
    battleHp('a', battle.a);
    battleHp('b', battle.b);
    await sleep(420);
  }
  session.busy = false;
  if (battle.over) {
    await finishBattle(false);
  } else {
    renderBattle();
  }
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
//  Boot
// ---------------------------------------------------------------------------

function boot(): void {
  state = loadState();
  applyRegionTint();
  setInterval(() => {
    spriteFrame = (spriteFrame + 1) % 2;
    if (session) {
      renderBattle();
    } else if (state?.egg && !$('screen-egg').classList.contains('hidden')) {
      const species = getSpecies(state.egg.speciesId);
      drawSprite($('egg-canvas') as HTMLCanvasElement, spriteForSpecies(species, spriteFrame), 10);
    } else if (state?.monster && !$('screen-main').classList.contains('hidden')) {
      const species = getSpecies(state.monster.speciesId);
      drawScene('main-scene');
      drawSprite(
        $('monster-canvas') as HTMLCanvasElement,
        spriteForSpecies(species, spriteFrame),
        8
      );
    }
  }, 650);

  if (!state) {
    renderTitle();
  } else if (state.egg) {
    pushLog(`Welcome back, ${state.tamerName}.`);
    renderEgg();
  } else {
    pushLog(`Welcome back, ${state.tamerName}.`);
    renderMain();
  }
}

document.addEventListener('DOMContentLoaded', boot);
