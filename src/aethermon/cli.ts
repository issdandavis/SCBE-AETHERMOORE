/**
 * @file cli.ts
 * @module aethermon/cli
 * @layer Layer 14
 * @component AETHERMON — Playable Terminal Game
 *
 * Run interactively:   npm run game:aethermon
 * Scripted demo:       npm run game:aethermon:demo   (no input, no saves)
 *
 * Flags: --demo, --seed <n>, --save <path>
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import * as readline from 'node:readline';
import type { BattleAction, Combatant, GameState, MonsterState, Stage } from './types.js';
import { RESIDUE_CAP, STAGE_MIN_LEVEL, TONGUE_NOTES } from './types.js';
import { getMove } from './moves.js';
import { STARTER_EGG_IDS, getSpecies } from './species.js';
import { REGIONS, getRegion } from './regions.js';
import {
  cleanUp,
  describeCare,
  effectiveStats,
  feed,
  hourOf,
  isNight,
  isStatKey,
  lifespanRemaining,
  patch,
  play,
  praise,
  rest,
  scold,
  train,
  tuckIn,
  weightBand,
  xpToNext,
} from './monster.js';
import { evolutionOptions, evolve, selectEvolution } from './evolution.js';
import {
  applyBattleResult,
  autoBattle,
  chooseAiAction,
  createBattle,
  performRound,
  toCombatant,
} from './battle.js';
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
} from './game.js';
import { createRng, nextInt } from './rng.js';

// ---------------------------------------------------------------------------
//  Terminal helpers
// ---------------------------------------------------------------------------

const useColor = process.stdout.isTTY === true && process.env.NO_COLOR === undefined;
const paint = (code: string, text: string): string =>
  useColor ? `\x1b[${code}m${text}\x1b[0m` : text;
const bold = (t: string): string => paint('1', t);
const dim = (t: string): string => paint('2', t);

const ELEMENT_COLOR: Record<string, string> = {
  KO: '31', // red
  AV: '33', // yellow
  RU: '32', // green
  CA: '36', // cyan
  UM: '34', // blue
  DR: '35', // magenta
};

function elementPaint(element: string, text: string): string {
  return paint(ELEMENT_COLOR[element] ?? '0', text);
}

const STAGE_ART: Record<Stage, string[]> = {
  EGG: ['   ___ ', '  /(@)\\', '  \\___/'],
  MOTE: ['       ', '  (o.o)', '  ~( )~'],
  SPRITE: ['   /\\ ', '  (^w^)', '  /|__|\\'],
  GUARDIAN: ['  [=A=] ', '  /|#|\\', '   d b '],
  PARAGON: [' \\[***]/ ', '  |###|', '  // \\\\'],
  APEX: ['\\\\[ΩΩΩ]//', ' <{###}>', '  _/ \\_'],
};

function hpBar(current: number, max: number, width = 20): string {
  const filled = Math.round((Math.max(0, current) / Math.max(1, max)) * width);
  const bar = '█'.repeat(filled) + '░'.repeat(width - filled);
  return `[${bar}] ${current}/${max}`;
}

function line(): void {
  console.log(dim('─'.repeat(56)));
}

/**
 * Buffered stdin reader. Unlike readline/promises, lines that arrive
 * while no question is pending are queued instead of dropped — so piped
 * scripts (`printf '...' | cli`) drive the game exactly like a player.
 * Returns null on EOF.
 */
class LineReader {
  private readonly queue: string[] = [];
  private readonly waiters: Array<(value: string | null) => void> = [];
  private closed = false;
  private readonly rl: readline.Interface;

  constructor(input: NodeJS.ReadableStream) {
    this.rl = readline.createInterface({ input });
    this.rl.on('line', (text) => {
      const waiter = this.waiters.shift();
      if (waiter) waiter(text);
      else this.queue.push(text);
    });
    this.rl.on('close', () => {
      this.closed = true;
      for (const waiter of this.waiters.splice(0)) waiter(null);
    });
  }

  /** Prompt and read one line; null when input is exhausted. */
  ask(prompt: string): Promise<string | null> {
    process.stdout.write(prompt);
    const queued = this.queue.shift();
    if (queued !== undefined) {
      process.stdout.write(`${queued}\n`); // echo for piped transcripts
      return Promise.resolve(queued);
    }
    if (this.closed) {
      process.stdout.write('\n');
      return Promise.resolve(null);
    }
    return new Promise((resolve) => this.waiters.push(resolve));
  }

  close(): void {
    this.rl.close();
  }
}

// ---------------------------------------------------------------------------
//  Display
// ---------------------------------------------------------------------------

function showMonsterCard(monster: MonsterState): void {
  const species = getSpecies(monster.speciesId);
  const stats = effectiveStats(monster);
  line();
  for (const row of STAGE_ART[species.stage]) {
    console.log(elementPaint(species.element, row));
  }
  console.log(
    `${bold(monster.nickname)} the ${elementPaint(species.element, species.name)} ` +
      dim(`(${species.stage} · ${species.element} · ${species.alignment})`)
  );
  console.log(dim(species.lore));
  console.log(
    `Lv.${monster.level}  XP ${monster.xp}/${xpToNext(monster.level)}  ` +
      `W${monster.battlesWon}/L${monster.battlesLost}  Age ${monster.ageTicks} ticks`
  );
  console.log(
    `Gen ${monster.generation}  Scars ${monster.scars}  Hollow ${monster.hollowExposure}  ` +
      `Lifespan ${lifespanRemaining(monster)} ticks left  ` +
      dim(`sounds in ${TONGUE_NOTES[species.element]}`)
  );
  console.log(
    `HP ${stats.hp}  ATK ${stats.atk}  DEF ${stats.def}  SPD ${stats.spd} ` +
      dim(
        `(trained +${monster.trainBonus.hp}/+${monster.trainBonus.atk}/` +
          `+${monster.trainBonus.def}/+${monster.trainBonus.spd})`
      )
  );
  console.log(describeCare(monster.care));
  const band = weightBand(monster);
  console.log(
    `Weight ${monster.weightKb}kb${band === 'IDEAL' ? '' : paint('33', ` (${band})`)}  ` +
      `Hour ${hourOf(monster)}/24 ${isNight(monster) ? '☾ night' : '☀ day'}  ` +
      `Residue ${monster.residue}/${RESIDUE_CAP}` +
      (monster.glitched ? '  ' + paint('31', 'GLITCHED — needs a patch') : '')
  );
  console.log(`Moves: ${species.moves.map((id) => getMove(id).name).join(', ')}`);
  line();
}

function announceEvolutionPaths(monster: MonsterState): void {
  const options = evolutionOptions(monster);
  if (options.length === 0) {
    console.log(`${monster.nickname} has reached its final form.`);
    return;
  }
  console.log(bold('Evolution paths:'));
  for (const option of options) {
    const target = getSpecies(option.requirement.targetId);
    const status = option.eligible ? paint('32', 'READY') : dim(option.blockedBy.join(', '));
    console.log(`  → ${target.name} ${dim(`(${target.alignment})`)} — ${status}`);
  }
}

/**
 * Check the lifespan clock; if the generation has ended, hold the
 * memorial and hand the tamer the next egg. Returns true on rebirth.
 */
function announceRebirth(state: GameState): boolean {
  const rebirth = checkRebirth(state);
  if (!rebirth) return false;
  const heirloom = rebirth.heirloom;
  console.log('');
  console.log(paint('35', '☾ ☾ ☾  THE SPIRAL TURNS  ☾ ☾ ☾'));
  console.log(`${rebirth.memorialEntry} has lived out its season and returns to the egg.`);
  if (heirloom.hp + heirloom.atk + heirloom.def + heirloom.spd > 0) {
    console.log(
      `Its strength echoes forward to Generation ${rebirth.nextGeneration}: ` +
        `+${heirloom.hp} HP, +${heirloom.atk} ATK, +${heirloom.def} DEF, +${heirloom.spd} SPD.`
    );
  }
  console.log(`A ${getSpecies(rebirth.eggSpeciesId).name} rests in your hands once more.`);
  return true;
}

function maybeEvolve(state: GameState, monster: MonsterState): void {
  while (selectEvolution(monster) !== null) {
    const result = evolve(monster);
    if (!result) break;
    const species = getSpecies(result.toSpeciesId);
    console.log('');
    console.log(paint('33', '✦ ✦ ✦  EVOLUTION  ✦ ✦ ✦'));
    console.log(
      bold(`${monster.nickname} evolved: ${result.fromName} → ${result.toName}!`) +
        ` ${dim(`(${species.stage})`)}`
    );
    if (species.stage === 'APEX') {
      state.hallOfFame.push(`${monster.nickname} the ${species.name}`);
      console.log(paint('35', `${monster.nickname} has reached APEX and enters the Hall of Fame!`));
    }
  }
}

// ---------------------------------------------------------------------------
//  Battles
// ---------------------------------------------------------------------------

async function interactiveBattle(
  reader: LineReader,
  state: GameState,
  enemy: Combatant,
  wasArena: boolean
): Promise<void> {
  const monster = state.monster;
  if (!monster) return;
  const mine = toCombatant(monster);
  const rng = createRng(state.rngState);
  const battle = createBattle(mine, enemy, nextInt(rng, 0, 2 ** 31 - 1));
  state.rngState = rng.state;

  console.log('');
  console.log(bold(`⚔  ${mine.name} (Lv.${mine.level}) vs ${enemy.name} (Lv.${enemy.level})`));

  while (!battle.over) {
    console.log('');
    console.log(`  ${mine.name.padEnd(18)} ${hpBar(mine.hp, mine.stats.hp)}`);
    console.log(`  ${enemy.name.padEnd(18)} ${hpBar(enemy.hp, enemy.stats.hp)}`);
    const species = getSpecies(mine.speciesId);
    species.moves.forEach((id, i) => {
      const move = getMove(id);
      const kind = move.effect === 'heal' ? 'heal' : `pow ${move.power}`;
      console.log(
        `    [${i + 1}] ${move.name} ${dim(`(${move.element}, ${kind}, acc ${move.accuracy})`)}`
      );
    });
    console.log(`    [g] Guard   [r] Run`);
    const answer = ((await reader.ask('  Action> ')) ?? 'r').trim().toLowerCase();

    if (answer === 'r') {
      console.log(`${mine.name} retreats! ${dim('(counts as a loss)')}`);
      const aftermath = applyBattleResult(monster, false);
      recordBattleOutcome(state, monster, enemy.level, false, wasArena);
      if (aftermath.scarred) {
        console.log(dim(`${monster.nickname} carries a new scar. (${monster.scars} total)`));
      }
      return;
    }
    let action: BattleAction;
    if (answer === 'g') {
      action = { type: 'guard' };
    } else {
      const idx = Number.parseInt(answer, 10) - 1;
      const moveId = species.moves[idx];
      if (moveId === undefined) {
        console.log(dim('  Pick a listed move, g, or r.'));
        continue;
      }
      action = { type: 'move', moveId };
    }
    const enemyAction = chooseAiAction(battle, 'B');
    for (const event of performRound(battle, action, enemyAction)) {
      console.log(`  ${event.text}`);
    }
  }

  const won = battle.winner === 'A';
  const aftermath = applyBattleResult(monster, won);
  const levels = recordBattleOutcome(state, monster, enemy.level, won, wasArena);
  console.log('');
  if (battle.winner === 'DRAW') console.log(bold('A draw!'));
  else console.log(won ? paint('32', bold('VICTORY!')) : paint('31', bold('Defeat...')));
  if (aftermath.scarred) {
    console.log(
      dim(`${monster.nickname} carries a new scar. (${monster.scars} total — its guard hardens.)`)
    );
  }
  if (aftermath.strained) {
    console.log(
      paint('33', `${monster.nickname} is overworked — it needs a proper rest before fighting on.`)
    );
  }
  if (aftermath.glitchedByStrain) {
    console.log(
      paint('31', `${monster.nickname} glitches from the strain! Patch it before training again.`)
    );
  }
  if (levels > 0) console.log(bold(`${monster.nickname} grew to Lv.${monster.level}!`));
  maybeEvolve(state, monster);
  if (wasArena && won) {
    if (isChampion(state)) {
      console.log(paint('33', bold('\n★ ★ ★  SPIRAL ARENA CHAMPION  ★ ★ ★')));
      console.log(`${state.tamerName} and ${monster.nickname} now rule the Spiral Arena!`);
    } else {
      const rival = nextArenaRival(state);
      if (rival) console.log(`Next arena rival: ${rival.name}, ${rival.title} (Lv.${rival.level})`);
    }
  }
}

// ---------------------------------------------------------------------------
//  Save / load
// ---------------------------------------------------------------------------

function savePath(argv: string[]): string {
  const idx = argv.indexOf('--save');
  if (idx >= 0 && argv[idx + 1]) return path.resolve(argv[idx + 1]);
  return path.resolve(process.cwd(), '.aethermon-save.json');
}

function saveGame(state: GameState, file: string): void {
  fs.writeFileSync(file, serializeGame(state), 'utf8');
  console.log(dim(`Saved to ${file}`));
}

function loadGame(file: string): GameState | null {
  if (!fs.existsSync(file)) return null;
  return deserializeGame(fs.readFileSync(file, 'utf8'));
}

// ---------------------------------------------------------------------------
//  Interactive mode
// ---------------------------------------------------------------------------

async function interactiveMain(argv: string[]): Promise<void> {
  const reader = new LineReader(process.stdin);
  const file = savePath(argv);
  const seedIdx = argv.indexOf('--seed');
  const seed =
    seedIdx >= 0 && argv[seedIdx + 1] ? Number(argv[seedIdx + 1]) : Date.now() & 0x7fffffff;

  console.log(paint('36', bold('\n  A E T H E R M O N')));
  console.log(dim('  Raise a digital creature of the Aethermoore realm.\n'));

  let state = loadGame(file);
  if (state) {
    console.log(`Welcome back, ${bold(state.tamerName)}.`);
  } else {
    const tamer = ((await reader.ask('Your tamer name> ')) ?? '').trim() || 'Tamer';
    console.log('\nChoose your egg:');
    STARTER_EGG_IDS.forEach((id, i) => {
      const species = getSpecies(id);
      console.log(
        `  [${i + 1}] ${elementPaint(species.element, species.name)} — ${dim(species.lore)}`
      );
    });
    let eggId: string | undefined;
    while (!eggId) {
      const pickAnswer = await reader.ask('Egg> ');
      if (pickAnswer === null) {
        console.log(dim('No input — goodbye.'));
        reader.close();
        return;
      }
      eggId = STARTER_EGG_IDS[Number.parseInt(pickAnswer.trim(), 10) - 1];
    }
    state = newGame(tamer, eggId, seed);
  }

  // Generational loop: raise a creature; when its season ends it
  // returns to the egg and the line continues.
  while (true) {
    // Egg phase (rebirth eggs re-enter here)
    while (state.egg) {
      const species = getSpecies(state.egg.speciesId);
      console.log(
        `\nYou hold a ${elementPaint(species.element, bold(species.name))} ` +
          dim(`(Generation ${state.egg.generation ?? state.generation})`)
      );
      console.log('  [1] Warm the egg   [2] Save & quit');
      const eggAnswer = ((await reader.ask('> ')) ?? '2').trim();
      if (eggAnswer === '2') {
        saveGame(state, file);
        reader.close();
        return;
      }
      const eggNickname =
        state.egg.warmth + 1 >= 3 ? ((await reader.ask('Name it> ')) ?? '').trim() : '';
      console.log(warmEgg(state, eggNickname || 'Aether').message);
    }
    if (!state.monster) {
      reader.close();
      return;
    }

    // Raising phase
    let reborn = false;
    while (state.monster && !reborn) {
      const monster = state.monster;
      const region = getRegion(state.region);
      console.log('');
      console.log(
        bold(`${monster.nickname}`) +
          dim(
            ` · Lv.${monster.level} · Gen ${monster.generation} · ${region.name}` +
              ` · arena ${state.arenaRank}/${ARENA_LADDER.length}` +
              (isChampion(state) ? ' · CHAMPION' : '')
          )
      );
      if (isNight(monster)) {
        console.log(paint('34', '  ☾ Night has fallen — tuck it in [z] before midnight.'));
      }
      if (monster.glitched) {
        console.log(paint('31', '  ⚠ It is glitching — apply a patch [p].'));
      }
      console.log(
        '  [1] Status   [2] Feed    [3] Train   [4] Play    [5] Rest\n' +
          '  [6] Praise   [7] Scold   [8] Wild battle   [9] Arena\n' +
          '  [c] Clean pen   [p] Patch   [z] Tuck in\n' +
          '  [t] Travel   [e] Evolution paths   [s] Save   [q] Save & quit' +
          (region.touchesHollow ? '\n  ' + paint('35', '[h] Approach the gap') : '')
      );
      const choice = ((await reader.ask('> ')) ?? 'q').trim().toLowerCase();
      switch (choice) {
        case '1':
          showMonsterCard(monster);
          break;
        case '2':
          console.log(feed(monster).message);
          break;
        case '3': {
          const stat = ((await reader.ask('Train which? (hp/atk/def/spd)> ')) ?? '')
            .trim()
            .toLowerCase();
          if (isStatKey(stat)) console.log(train(monster, stat).message);
          else console.log(dim('Unknown stat.'));
          break;
        }
        case '4':
          console.log(play(monster).message);
          break;
        case '5':
          console.log(rest(monster).message);
          break;
        case '6':
          console.log(praise(monster).message);
          break;
        case '7':
          console.log(scold(monster).message);
          break;
        case 'c':
          console.log(cleanUp(monster).message);
          break;
        case 'p':
          console.log(patch(monster).message);
          break;
        case 'z':
          console.log(tuckIn(monster).message);
          break;
        case '8': {
          const enemy = generateWildEncounter(state, monster);
          await interactiveBattle(reader, state, enemy, false);
          break;
        }
        case '9': {
          const rival = nextArenaRival(state);
          if (!rival) {
            console.log(paint('33', 'You have already conquered the Spiral Arena!'));
            break;
          }
          console.log(`Arena rung ${state.arenaRank + 1}: ${rival.name}, ${rival.title}`);
          await interactiveBattle(reader, state, arenaCombatant(rival), true);
          break;
        }
        case 't': {
          console.log('Where to?');
          REGIONS.forEach((r, i) => {
            const marker = r.id === state.region ? ' (here)' : '';
            console.log(
              `  [${i + 1}] ${elementPaint(r.tongue, r.name)}${marker} — ${dim(r.description)}`
            );
          });
          const destination = ((await reader.ask('Region> ')) ?? '').trim();
          const target = REGIONS[Number.parseInt(destination, 10) - 1];
          if (target) console.log(travel(state, target.id));
          else console.log(dim('You stay where you are.'));
          break;
        }
        case 'h': {
          const result = communeWithGap(state, monster);
          console.log(result.ok ? paint('35', result.message) : dim(result.message));
          break;
        }
        case 'e':
          announceEvolutionPaths(monster);
          break;
        case 's':
          saveGame(state, file);
          break;
        case 'q':
          saveGame(state, file);
          reader.close();
          return;
        default:
          console.log(dim('Pick an option from the menu.'));
      }
      if (state.monster) {
        maybeEvolve(state, monster);
        reborn = announceRebirth(state);
      }
    }
  }
}

// ---------------------------------------------------------------------------
//  Demo mode (non-interactive, deterministic)
// ---------------------------------------------------------------------------

function demoMain(argv: string[]): void {
  const seedIdx = argv.indexOf('--seed');
  const seed = seedIdx >= 0 && argv[seedIdx + 1] ? Number(argv[seedIdx + 1]) : 42;

  console.log(paint('36', bold('\n  A E T H E R M O N — scripted demo')));
  console.log(dim(`  seed ${seed}; no input needed, nothing is written to disk.\n`));

  const state = newGame('Demo Tamer', 'ember_egg', seed);
  while (state.egg) console.log(warmEgg(state, 'Cinder').message);
  const monster = state.monster;
  if (!monster) throw new Error('demo: hatch failed');
  showMonsterCard(monster);

  console.log(travel(state, 'aerial_expanse'));

  let battles = 0;
  while (monster.level < STAGE_MIN_LEVEL.GUARDIAN && battles < 60) {
    // Care loop: keep meters healthy, train ATK toward the VENOM branch,
    // sweep the pen, patch glitches, and honor the sleep schedule.
    if (monster.care.hunger < 40) console.log(dim(feed(monster).message));
    if (monster.care.energy < 30) console.log(dim(rest(monster).message));
    if (monster.residue >= 2) console.log(dim(cleanUp(monster).message));
    if (monster.glitched) console.log(dim(patch(monster).message));
    if (isNight(monster)) console.log(dim(tuckIn(monster).message));
    if (battles % 3 === 0) train(monster, 'atk');
    if (battles === 20) {
      console.log(travel(state, 'null_vale'));
      console.log(paint('35', communeWithGap(state, monster).message));
    }

    const enemy = generateWildEncounter(state, monster);
    const rng = createRng(state.rngState);
    const battle = autoBattle(toCombatant(monster), enemy, nextInt(rng, 0, 2 ** 31 - 1));
    state.rngState = rng.state;
    battles += 1;
    const won = battle.winner === 'A';
    const aftermath = applyBattleResult(monster, won);
    recordBattleOutcome(state, monster, enemy.level, won, false);
    console.log(
      `Battle ${battles}: vs ${enemy.name} (Lv.${enemy.level}) — ` +
        `${won ? paint('32', 'WIN') : paint('31', 'LOSS')} in ${battle.turn} ` +
        `turn${battle.turn === 1 ? '' : 's'} ` +
        dim(`→ Lv.${monster.level}${aftermath.scarred ? ` · scar #${monster.scars}` : ''}`)
    );
    maybeEvolve(state, monster);
    if (announceRebirth(state)) break;
  }

  // Take a swing at the arena ladder.
  for (let i = 0; i < 4 && state.monster; i++) {
    const rival = nextArenaRival(state);
    if (!rival || rival.level > monster.level + 4) break;
    const rng = createRng(state.rngState);
    const battle = autoBattle(
      toCombatant(monster),
      arenaCombatant(rival),
      nextInt(rng, 0, 2 ** 31 - 1)
    );
    state.rngState = rng.state;
    const won = battle.winner === 'A';
    applyBattleResult(monster, won);
    recordBattleOutcome(state, monster, rival.level, won, true);
    console.log(
      `Arena rung ${state.arenaRank + (won ? 0 : 1)}: ${rival.name} (${rival.title}) — ` +
        `${won ? paint('32', 'WIN') : paint('31', 'LOSS')} in ${battle.turn} ` +
        `turn${battle.turn === 1 ? '' : 's'}`
    );
    maybeEvolve(state, monster);
    if (!won) break;
  }

  showMonsterCard(monster);
  announceEvolutionPaths(monster);
  console.log(
    `\nDemo complete: ${state.totalBattlesWon} wins / ${state.totalBattlesLost} losses, ` +
      `arena ${state.arenaRank}/${ARENA_LADDER.length}, ` +
      `${monster.scars} scars, hollow ${monster.hollowExposure}, ` +
      `lineage ${monster.lineage.join(' → ')}.`
  );
  console.log(dim('Run `npm run game:aethermon` to play interactively.'));
}

// ---------------------------------------------------------------------------
//  Entry point
// ---------------------------------------------------------------------------

if (require.main === module) {
  const argv = process.argv.slice(2);
  if (argv.includes('--demo')) {
    demoMain(argv);
  } else {
    interactiveMain(argv).catch((err: unknown) => {
      console.error(err);
      process.exitCode = 1;
    });
  }
}
