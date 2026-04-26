import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const outFile = resolve(repoRoot, 'dist', 'index.d.ts');

const body = `export * from './src/index.js';
export { default } from './src/index.js';
`;

await mkdir(dirname(outFile), { recursive: true });
await writeFile(outFile, body, 'utf8');
console.log(`wrote ${outFile}`);
