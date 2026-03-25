#!/usr/bin/env node
/**
 * @file scbe_skill_tool_bridge.mjs
 * @module scripts/system/scbe_skill_tool_bridge
 * @description Cross-platform skill-tool bridge that maps SCBE skill
 *              definitions to MCP tool schemas. Supports --action quick | full.
 */

import { readdirSync, readFileSync, existsSync } from 'fs';
import { resolve, join } from 'path';

const ROOT = resolve(import.meta.dirname, '..', '..');
const SKILLS_DIR = resolve(ROOT, 'skills');

const args = process.argv.slice(2);
const actionIdx = args.indexOf('--action');
const action = actionIdx !== -1 ? args[actionIdx + 1] : 'quick';

console.log(`[skill-bridge] action=${action}`);

if (!existsSync(SKILLS_DIR)) {
  console.log('[skill-bridge] No skills/ directory found — nothing to bridge');
  process.exit(0);
}

const dirs = readdirSync(SKILLS_DIR, { withFileTypes: true })
  .filter((d) => d.isDirectory())
  .map((d) => d.name);

console.log(`[skill-bridge] Found ${dirs.length} skill(s): ${dirs.join(', ')}`);

for (const dir of dirs) {
  const manifest = join(SKILLS_DIR, dir, 'manifest.json');
  if (existsSync(manifest)) {
    const data = JSON.parse(readFileSync(manifest, 'utf8'));
    console.log(`  [${dir}] ${data.name || dir} — ${data.description || 'no description'}`);
    if (action === 'full' && data.tools) {
      for (const tool of data.tools) {
        console.log(`    tool: ${tool.name || tool}`);
      }
    }
  } else {
    console.log(`  [${dir}] (no manifest.json)`);
  }
}

console.log('[skill-bridge] Done');
