/**
 * Post-build step: copies dist/src/index.d.ts → dist/index.d.ts so that
 * consumers using `import … from 'scbe-aethermoore'` resolve types from the
 * package root even if their tooling doesn't follow the "types" field.
 *
 * If the source .d.ts doesn't exist (e.g. tsc errored), this script exits
 * cleanly so the real error surfaces from tsc, not from here.
 */

import { copyFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = join(root, 'dist', 'src', 'index.d.ts');
const dest = join(root, 'dist', 'index.d.ts');

if (existsSync(src)) {
  copyFileSync(src, dest);
  console.log('write_root_index_dts: dist/index.d.ts written');
} else {
  console.log('write_root_index_dts: dist/src/index.d.ts not found, skipping');
}
