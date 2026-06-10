#!/usr/bin/env node

const path = require('node:path');

const pkgRoot = path.resolve(__dirname, '..');
const { decompose, recompose } = require(path.join(pkgRoot, 'dist', 'index.js'));

const task = process.argv.slice(2).join(' ').trim();
if (!task) {
  process.stderr.write('Usage: node packages/agent-bus/scripts/semantic_hex_bridge.cjs "<text>"\n');
  process.exit(2);
}

const decomp = decompose(task);
const recomposed = recompose(decomp.combinedHex);
process.stdout.write(
  `${JSON.stringify(
    {
      schema_version: 'scbe.agent_bus.semantic_hex_bridge.v1',
      ok: Boolean(recomposed.closest),
      input_hash: decomp.inputHash,
      combined_hex: decomp.combinedHex,
      combined_binary: decomp.combinedBinary,
      dominant: decomp.dominant,
      recomposed_closest: recomposed.closest,
      note: 'Semantic recomposition is nearest-atom routing evidence, not lossless natural-language identity.',
    },
    null,
    2
  )}\n`
);
