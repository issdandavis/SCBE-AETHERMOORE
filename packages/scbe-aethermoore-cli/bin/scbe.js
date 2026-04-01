#!/usr/bin/env node
'use strict';

const path = require('path');

const CLI_VERSION = require('../package.json').version;
const REPO_ONLY_COMMANDS = new Set([
  'doctor',
  'use',
  'config',
  'colab',
  'pollypad',
  'run',
  'flow',
  'workflow',
  'web',
  'antivirus',
  'aetherauth',
  'notion-gap',
  'self-improve',
  'docs',
  'legacy',
]);

let cachedModules = null;

function print(line = '') {
  process.stdout.write(`${line}\n`);
}

function fail(message) {
  process.stderr.write(`${message}\n`);
  process.exit(1);
}

function resolveLocalModule(...segments) {
  return path.resolve(__dirname, '..', '..', '..', ...segments);
}

function loadPreferLocal(localPath, packageId) {
  try {
    return require(localPath);
  } catch (localError) {
    try {
      return require(packageId);
    } catch (packageError) {
      const detail =
        packageError && packageError.message ? packageError.message : localError.message;
      throw new Error(
        `Unable to load scbe-aethermoore core library. Install scbe-aethermoore or build the repo first. (${detail})`
      );
    }
  }
}

function getModules() {
  if (cachedModules) {
    return cachedModules;
  }

  cachedModules = {
    core: loadPreferLocal(resolveLocalModule('dist', 'src', 'index.js'), 'scbe-aethermoore'),
    tokenizer: loadPreferLocal(
      resolveLocalModule('dist', 'src', 'tokenizer', 'index.js'),
      'scbe-aethermoore/tokenizer'
    ),
    governance: loadPreferLocal(
      resolveLocalModule('dist', 'src', 'governance', 'index.js'),
      'scbe-aethermoore/governance'
    ),
    spiralverse: loadPreferLocal(
      resolveLocalModule('dist', 'src', 'spiralverse', 'index.js'),
      'scbe-aethermoore/spiralverse'
    ),
  };

  return cachedModules;
}

function parseArgs(argv) {
  const positional = [];
  const options = {};

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--help' || token === '-h') {
      options.help = true;
      continue;
    }
    if (!token.startsWith('--')) {
      positional.push(token);
      continue;
    }

    const key = token
      .slice(2)
      .replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    const next = argv[index + 1];
    if (next && !next.startsWith('--')) {
      options[key] = next;
      index += 1;
      continue;
    }
    options[key] = true;
  }

  return { positional, options };
}

function requirePositional(positional, index, label) {
  const value = positional[index];
  if (!value) {
    fail(`Missing ${label}. Run "scbe --help" for usage.`);
  }
  return value;
}

function parseBoolean(value, label) {
  if (value === true) {
    return true;
  }
  if (typeof value !== 'string') {
    fail(`Missing --${label}. Expected true or false.`);
  }
  if (value === 'true') return true;
  if (value === 'false') return false;
  fail(`Invalid boolean for --${label}: ${value}. Expected true or false.`);
}

function requireBooleanOptions(options, labels) {
  const result = {};
  for (const label of labels) {
    result[label] = parseBoolean(options[label], label.replace(/[A-Z]/g, (match) => `-${match.toLowerCase()}`));
  }
  return result;
}

function ensureTongue(tokenizer, tongue) {
  const normalized = String(tongue).toUpperCase();
  if (!tokenizer.TONGUE_CODES.includes(normalized)) {
    fail(`Unknown tongue "${tongue}". Expected one of: ${tokenizer.TONGUE_CODES.join(', ')}`);
  }
  return normalized;
}

function printHelp() {
  print('scbe-aethermoore-cli');
  print('');
  print('Usage:');
  print('  scbe version');
  print('  scbe info');
  print('  scbe tongues list');
  print('  scbe tongues encode <TONGUE> <INPUT> [--hex] [--no-prefix]');
  print('  scbe tongues decode <SPELLTEXT> [--tongue <TONGUE>] [--hex]');
  print('  scbe policy suggest <ACTION>');
  print('  scbe policy required <standard|strict|critical>');
  print('  scbe offline trust-state --keys-valid <bool> --time-trusted <bool> --manifest-current <bool> --key-rotation-needed <bool> --integrity-ok <bool>');
  print('  scbe offline gate <ACTION> --laws-present <bool> --laws-hash-valid <bool> --manifest-present <bool> --manifest-sig-ok <bool> --keys-present <bool> --audit-intact <bool> --voxel-root-ok <bool>');
  print('  scbe selftest');
  print('');
  print('Repo-only operational commands are intentionally not shipped in this package.');
}

function handleVersion() {
  const { core } = getModules();
  print(`scbe-aethermoore-cli ${CLI_VERSION}`);
  print(`scbe-aethermoore ${core.VERSION || 'unknown'}`);
}

function handleInfo() {
  const { core, tokenizer, governance, spiralverse } = getModules();
  const info = {
    cliPackage: 'scbe-aethermoore-cli',
    cliVersion: CLI_VERSION,
    corePackage: 'scbe-aethermoore',
    coreVersion: core.VERSION || 'unknown',
    packagedSurface: ['crypto', 'governance', 'harmonic', 'spiralverse', 'tokenizer', 'ai_brain'],
    blockedRepoCommands: Array.from(REPO_ONLY_COMMANDS).sort(),
    supportedCommands: [
      'version',
      'info',
      'tongues list',
      'tongues encode',
      'tongues decode',
      'policy suggest',
      'policy required',
      'offline trust-state',
      'offline gate',
      'selftest',
    ],
    tongues: tokenizer.TONGUE_CODES.map((code) => ({
      code,
      name: tokenizer.TONGUES[code].name,
      domain: tokenizer.TONGUES[code].domain,
    })),
    policyLevels: ['standard', 'strict', 'critical'],
    trustStates: Object.values(governance.TrustState),
    sampleCriticalTongues: spiralverse.getRequiredTongues('critical'),
  };
  print(JSON.stringify(info, null, 2));
}

function handleTongues(commandArgs) {
  const { tokenizer } = getModules();
  const { positional, options } = parseArgs(commandArgs);
  const subcommand = requirePositional(positional, 0, 'tongues subcommand');

  if (subcommand === 'list') {
    const payload = tokenizer.TONGUE_CODES.map((code) => tokenizer.TONGUES[code]);
    print(JSON.stringify(payload, null, 2));
    return;
  }

  if (subcommand === 'encode') {
    const tongue = ensureTongue(tokenizer, requirePositional(positional, 1, 'tongue'));
    const input = positional.slice(2).join(' ');
    if (!input) {
      fail('Missing input to encode.');
    }
    let bytes;
    if (options.hex) {
      if (!/^[0-9a-fA-F]+$/.test(input) || input.length % 2 !== 0) {
        fail('Hex input must contain an even number of hexadecimal characters.');
      }
      bytes = Buffer.from(input, 'hex');
    } else {
      bytes = Buffer.from(input, 'utf8');
    }
    const encoded = tokenizer.encode(bytes, tongue, options.noPrefix ? false : true);
    print(encoded);
    return;
  }

  if (subcommand === 'decode') {
    const spellText = positional.slice(1).join(' ');
    if (!spellText) {
      fail('Missing spell-text to decode.');
    }
    const tongue = options.tongue ? ensureTongue(tokenizer, options.tongue) : undefined;
    const decoded = tokenizer.decode(spellText, tongue);
    print(options.hex ? decoded.toString('hex') : decoded.toString('utf8'));
    return;
  }

  fail(`Unknown tongues subcommand "${subcommand}".`);
}

function handlePolicy(commandArgs) {
  const { spiralverse } = getModules();
  const { positional } = parseArgs(commandArgs);
  const subcommand = requirePositional(positional, 0, 'policy subcommand');

  if (subcommand === 'suggest') {
    const action = requirePositional(positional, 1, 'action');
    print(spiralverse.suggestPolicy(action));
    return;
  }

  if (subcommand === 'required') {
    const level = requirePositional(positional, 1, 'policy level');
    print(JSON.stringify(spiralverse.getRequiredTongues(level), null, 2));
    return;
  }

  fail(`Unknown policy subcommand "${subcommand}".`);
}

function handleOffline(commandArgs) {
  const { governance } = getModules();
  const { positional, options } = parseArgs(commandArgs);
  const subcommand = requirePositional(positional, 0, 'offline subcommand');

  if (subcommand === 'trust-state') {
    const trustContext = requireBooleanOptions(options, [
      'keysValid',
      'timeTrusted',
      'manifestCurrent',
      'keyRotationNeeded',
      'integrityOk',
    ]);
    const state = governance.evaluateTrustState({
      keys_valid: trustContext.keysValid,
      time_trusted: trustContext.timeTrusted,
      manifest_current: trustContext.manifestCurrent,
      key_rotation_needed: trustContext.keyRotationNeeded,
      integrity_ok: trustContext.integrityOk,
    });
    print(state);
    return;
  }

  if (subcommand === 'gate') {
    const action = requirePositional(positional, 1, 'action');
    const gateContext = requireBooleanOptions(options, [
      'lawsPresent',
      'lawsHashValid',
      'manifestPresent',
      'manifestSigOk',
      'keysPresent',
      'auditIntact',
      'voxelRootOk',
    ]);
    const result = governance.failClosedGate(
      {
        laws_present: gateContext.lawsPresent,
        laws_hash_valid: gateContext.lawsHashValid,
        manifest_present: gateContext.manifestPresent,
        manifest_sig_ok: gateContext.manifestSigOk,
        keys_present: gateContext.keysPresent,
        audit_intact: gateContext.auditIntact,
        voxel_root_ok: gateContext.voxelRootOk,
      },
      action
    );
    print(JSON.stringify(result, null, 2));
    return;
  }

  fail(`Unknown offline subcommand "${subcommand}".`);
}

function handleSelfTest() {
  const { core, tokenizer, governance, spiralverse } = getModules();
  const sample = 'hello world';
  const encoded = tokenizer.encode(Buffer.from(sample, 'utf8'), 'KO');
  const decoded = tokenizer.decode(encoded);
  const strictPolicy = spiralverse.suggestPolicy('deploy');
  const criticalTongues = spiralverse.getRequiredTongues('critical');
  const trustState = governance.evaluateTrustState({
    keys_valid: true,
    time_trusted: true,
    manifest_current: true,
    key_rotation_needed: false,
    integrity_ok: true,
  });
  const gateResult = governance.failClosedGate(
    {
      laws_present: true,
      laws_hash_valid: true,
      manifest_present: true,
      manifest_sig_ok: true,
      keys_present: true,
      audit_intact: true,
      voxel_root_ok: true,
    },
    'diagnostics.run'
  );
  const keys = governance.PQCrypto.generateSigningKeys();
  const message = Buffer.from('scbe-selftest', 'utf8');
  const signature = governance.PQCrypto.sign(keys.secretKey, message);
  const verified = governance.PQCrypto.verify(keys.publicKey, message, signature);
  const fingerprint = governance.PQCrypto.fingerprint(keys.publicKey);

  const results = {
    status:
      decoded.toString('utf8') === sample &&
      strictPolicy === 'strict' &&
      criticalTongues.includes('ru') &&
      criticalTongues.includes('um') &&
      criticalTongues.includes('dr') &&
      trustState === governance.TrustState.T0_Trusted &&
      gateResult.pass === true &&
      verified
        ? 'ok'
        : 'failed',
    cliVersion: CLI_VERSION,
    coreVersion: core.VERSION || 'unknown',
    tokenizerRoundtrip: decoded.toString('utf8') === sample,
    strictPolicy,
    criticalTongues,
    trustState,
    gatePass: gateResult.pass,
    pqVerified: verified,
    pqFingerprint: fingerprint,
  };

  print(JSON.stringify(results, null, 2));
  if (results.status !== 'ok') {
    process.exit(1);
  }
}

function main() {
  const argv = process.argv.slice(2);
  const first = argv[0];

  if (!first || first === '--help' || first === '-h' || first === 'help') {
    printHelp();
    return;
  }

  if (REPO_ONLY_COMMANDS.has(first)) {
    fail(`The "${first}" command is repo-only and is intentionally not shipped in scbe-aethermoore-cli.`);
  }

  if (first === 'version') {
    handleVersion();
    return;
  }
  if (first === 'info') {
    handleInfo();
    return;
  }
  if (first === 'tongues') {
    handleTongues(argv.slice(1));
    return;
  }
  if (first === 'policy') {
    handlePolicy(argv.slice(1));
    return;
  }
  if (first === 'offline') {
    handleOffline(argv.slice(1));
    return;
  }
  if (first === 'selftest') {
    handleSelfTest();
    return;
  }

  fail(`Unknown command "${first}". Run "scbe --help" for usage.`);
}

main();
