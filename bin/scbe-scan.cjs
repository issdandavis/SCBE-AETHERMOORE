#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');

function loadApi() {
  const apiPath = path.resolve(__dirname, '..', 'dist', 'src', 'index.js');
  try {
    return require(apiPath);
  } catch {
    throw new Error(
      `Unable to load built SCBE API at ${apiPath}. Run npm run build before using scbe-scan from source.`
    );
  }
}

function help() {
  process.stdout.write(`scbe-scan

Usage:
  scbe-scan "text to evaluate"
  scbe-scan --json "text to evaluate"
  scbe-scan --batch prompts.txt

Options:
  --json   Emit full JSON records.
  --batch  Read one prompt per line from a UTF-8 file.
`);
}

function parse(argv) {
  const args = { json: false, batch: '', text: [], help: false };
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === '--help' || token === '-h') {
      args.help = true;
    } else if (token === '--json') {
      args.json = true;
    } else if (token === '--batch') {
      args.batch = argv[++i] || '';
    } else {
      args.text.push(token);
    }
  }
  return args;
}

const DECISION_ICON = {
  ALLOW: '[OK]',
  QUARANTINE: '[??]',
  ESCALATE: '[!!]',
  DENY: '[XX]',
};

function printRecord(record, json) {
  if (json) {
    process.stdout.write(`${JSON.stringify(record, null, 2)}\n`);
    return;
  }
  const icon = DECISION_ICON[record.decision] || '[??]';
  const decision = record.decision.padEnd(10, ' ');
  process.stdout.write(
    `${icon} ${decision}    score=${record.score.toFixed(4)}  d*=${record.d_star.toFixed(4)}  pd=${record.phase_deviation.toFixed(4)}  len=${record.input_len}\n`
  );
}

function main() {
  const args = parse(process.argv);
  if (args.help) {
    help();
    return;
  }
  const api = loadApi();
  const inputs = args.batch
    ? fs
        .readFileSync(args.batch, 'utf-8')
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean)
    : [args.text.join(' ').trim()].filter(Boolean);
  if (!inputs.length) {
    help();
    process.exitCode = 1;
    return;
  }
  const records = api.scanBatch(inputs);
  for (const record of records) {
    printRecord(record, args.json);
  }
}

main();
