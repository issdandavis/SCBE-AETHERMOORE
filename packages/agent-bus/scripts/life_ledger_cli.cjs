#!/usr/bin/env node
'use strict';
/**
 * Life Ledger CLI — manage per-agent life simulation records.
 *
 * Usage:
 *   node life_ledger_cli.cjs init --ledger path/to/record.json --agent-id agent-1 [--name "Polly"]
 *   node life_ledger_cli.cjs encounter --ledger path/to/record.json --agent-id agent-2 [--alignment 0.8] [--name "Zara"]
 *   node life_ledger_cli.cjs status --ledger path/to/record.json
 *   node life_ledger_cli.cjs skill --ledger path/to/record.json --skill governance --xp 50
 *   node life_ledger_cli.cjs career-start --ledger path/to/record.json --role "navigator"
 *   node life_ledger_cli.cjs career-end --ledger path/to/record.json --role "navigator"
 *   node life_ledger_cli.cjs task-done --ledger path/to/record.json --role "navigator"
 *   node life_ledger_cli.cjs join-group --ledger path/to/record.json --group "scbe-fleet"
 *   node life_ledger_cli.cjs leave-group --ledger path/to/record.json --group "scbe-fleet"
 *   node life_ledger_cli.cjs known-check --ledger path/to/record.json --agent-id agent-2
 */

const path = require('node:path');
const fs = require('node:fs');

const pkgRoot = path.resolve(__dirname, '..');
const {
  createLifeRecord,
  encounter,
  gainSkillXP,
  startCareer,
  endCareer,
  completeTask,
  joinGroup,
  leaveGroup,
  isKnown,
  getAlignmentScore,
  summarize,
  serializeLifeRecord,
  deserializeLifeRecord,
} = require(path.join(pkgRoot, 'dist', 'index.js'));

function parseArgs(argv) {
  const flags = {};
  const positionals = [];
  for (let i = 2; i < argv.length; i++) {
    const tok = argv[i];
    if (tok.startsWith('--')) {
      const key = tok.slice(2);
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) { flags[key] = true; }
      else { flags[key] = next; i++; }
    } else {
      positionals.push(tok);
    }
  }
  return { command: positionals[0] ?? 'help', flags };
}

function printJson(obj) {
  process.stdout.write(JSON.stringify(obj, null, 2) + '\n');
}

function loadRecord(ledgerPath) {
  if (!fs.existsSync(ledgerPath)) throw new Error(`ledger not found: ${ledgerPath}`);
  return deserializeLifeRecord(fs.readFileSync(ledgerPath, 'utf8'));
}

function saveRecord(ledgerPath, record) {
  const tmp = ledgerPath + '.tmp';
  fs.writeFileSync(tmp, serializeLifeRecord(record), 'utf8');
  fs.renameSync(tmp, ledgerPath);
}

function requireFlag(flags, key) {
  if (!flags[key]) throw new Error(`--${key} is required`);
  return String(flags[key]);
}

function main() {
  const { command, flags } = parseArgs(process.argv);

  if (command === 'help' || flags.help) {
    process.stdout.write([
      'Life Ledger CLI',
      '',
      'Commands:',
      '  init --ledger <path> --agent-id <id> [--name <display_name>]',
      '  encounter --ledger <path> --agent-id <id> [--alignment <float>] [--name <name>]',
      '  status --ledger <path>',
      '  skill --ledger <path> --skill <name> --xp <n>',
      '  career-start --ledger <path> --role <role>',
      '  career-end --ledger <path> --role <role>',
      '  task-done --ledger <path> --role <role>',
      '  join-group --ledger <path> --group <id>',
      '  leave-group --ledger <path> --group <id>',
      '  known-check --ledger <path> --agent-id <id>',
      '',
    ].join('\n'));
    return;
  }

  const ledgerPath = path.resolve(requireFlag(flags, 'ledger'));

  if (command === 'init') {
    if (fs.existsSync(ledgerPath)) {
      printJson({ ok: false, error: `ledger already exists: ${ledgerPath}` });
      process.exitCode = 1;
      return;
    }
    const agentId = requireFlag(flags, 'agent-id');
    const name = flags.name ? String(flags.name) : undefined;
    const record = createLifeRecord(agentId, name);
    saveRecord(ledgerPath, record);
    printJson({ ok: true, action: 'created', agent_id: agentId, ledger: ledgerPath });
    return;
  }

  if (command === 'encounter') {
    const record = loadRecord(ledgerPath);
    const encounteredId = requireFlag(flags, 'agent-id');
    const alignmentSignal = flags.alignment !== undefined ? parseFloat(String(flags.alignment)) : undefined;
    const name = flags.name ? String(flags.name) : undefined;
    const result = encounter(record, encounteredId, alignmentSignal, name);
    saveRecord(ledgerPath, record);
    printJson({
      schema_version: 'scbe.agent_bus.life_ledger.encounter.v1',
      ok: true,
      ...result,
    });
    return;
  }

  if (command === 'status') {
    const record = loadRecord(ledgerPath);
    printJson({
      schema_version: 'scbe.agent_bus.life_ledger.status.v1',
      ok: true,
      summary: summarize(record),
    });
    return;
  }

  if (command === 'skill') {
    const record = loadRecord(ledgerPath);
    const skillName = requireFlag(flags, 'skill');
    const xp = parseInt(String(requireFlag(flags, 'xp')), 10);
    const result = gainSkillXP(record, skillName, xp);
    saveRecord(ledgerPath, record);
    printJson({ ok: true, skill: result });
    return;
  }

  if (command === 'career-start') {
    const record = loadRecord(ledgerPath);
    const role = requireFlag(flags, 'role');
    const entry = startCareer(record, role);
    saveRecord(ledgerPath, record);
    printJson({ ok: true, career_entry: entry });
    return;
  }

  if (command === 'career-end') {
    const record = loadRecord(ledgerPath);
    const role = requireFlag(flags, 'role');
    const ok = endCareer(record, role);
    if (ok) saveRecord(ledgerPath, record);
    printJson({ ok, role });
    process.exitCode = ok ? 0 : 1;
    return;
  }

  if (command === 'task-done') {
    const record = loadRecord(ledgerPath);
    const role = requireFlag(flags, 'role');
    const ok = completeTask(record, role);
    if (ok) saveRecord(ledgerPath, record);
    printJson({ ok, role });
    process.exitCode = ok ? 0 : 1;
    return;
  }

  if (command === 'join-group') {
    const record = loadRecord(ledgerPath);
    const groupId = requireFlag(flags, 'group');
    const joined = joinGroup(record, groupId);
    if (joined) saveRecord(ledgerPath, record);
    printJson({ ok: joined, action: joined ? 'joined' : 'already_member', group: groupId });
    return;
  }

  if (command === 'leave-group') {
    const record = loadRecord(ledgerPath);
    const groupId = requireFlag(flags, 'group');
    const left = leaveGroup(record, groupId);
    if (left) saveRecord(ledgerPath, record);
    printJson({ ok: left, action: left ? 'left' : 'not_member', group: groupId });
    return;
  }

  if (command === 'known-check') {
    const record = loadRecord(ledgerPath);
    const agentId = requireFlag(flags, 'agent-id');
    const known = isKnown(record, agentId);
    const alignment = getAlignmentScore(record, agentId);
    printJson({
      schema_version: 'scbe.agent_bus.life_ledger.known_check.v1',
      ok: true,
      agent_id: agentId,
      is_known: known,
      alignment_score: alignment,
    });
    return;
  }

  throw new Error(`unknown command: ${command}`);
}

try {
  main();
} catch (err) {
  process.stderr.write(`${err instanceof Error ? err.message : String(err)}\n`);
  process.exitCode = 1;
}
