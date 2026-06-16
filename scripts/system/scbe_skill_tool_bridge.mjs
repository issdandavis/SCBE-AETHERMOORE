#!/usr/bin/env node
/**
 * @file scbe_skill_tool_bridge.mjs
 * @module scripts/system/scbe_skill_tool_bridge
 * @description Cross-platform skill-tool bridge that maps SCBE skill
 *              definitions to MCP tool schemas. Supports --action quick | full.
 */

import { readdirSync, readFileSync, existsSync, statSync } from 'fs';
import { basename, dirname, resolve, join, relative } from 'path';

const ROOT = resolve(import.meta.dirname, '..', '..');
const SKILLS_DIR = resolve(ROOT, 'skills');

const args = process.argv.slice(2);
const actionIdx = args.indexOf('--action');
const action = actionIdx !== -1 ? args[actionIdx + 1] : 'quick';

console.log(`[skill-bridge] action=${action}`);

if (!existsSync(SKILLS_DIR)) {
  console.log('[skill-bridge] No skills/ directory found - nothing to bridge');
  process.exit(0);
}

function findSkillFiles(root) {
  const found = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const path = join(root, entry.name);
    if (entry.isDirectory()) {
      found.push(...findSkillFiles(path));
    } else if (entry.isFile() && entry.name === 'SKILL.md') {
      found.push(path);
    }
  }
  return found;
}

function parseSkillMarkdown(path) {
  const text = readFileSync(path, 'utf8');
  const frontmatter = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  const data = {};

  if (frontmatter) {
    for (const line of frontmatter[1].split(/\r?\n/)) {
      const match = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
      if (match) {
        data[match[1]] = match[2].trim().replace(/^['"]|['"]$/g, '');
      }
    }
  }

  return {
    name: data.name || basename(dirname(path)),
    description: data.description || 'no description',
    path,
  };
}

function readSkill(path) {
  const manifest = join(dirname(path), 'manifest.json');
  const skill = parseSkillMarkdown(path);

  if (!existsSync(manifest) || !statSync(manifest).isFile()) {
    return skill;
  }

  return { ...skill, ...JSON.parse(readFileSync(manifest, 'utf8')), path };
}

const skills = findSkillFiles(SKILLS_DIR).map(readSkill);

console.log(`[skill-bridge] Found ${skills.length} skill(s): ${skills.map((skill) => skill.name).join(', ')}`);

for (const skill of skills) {
  const id = relative(SKILLS_DIR, dirname(skill.path));
  console.log(`  [${id}] ${skill.name} - ${skill.description || 'no description'}`);

  if (action === 'full') {
    console.log(`    skill: ${relative(ROOT, skill.path)}`);

    if (skill.tools) {
      for (const tool of skill.tools) {
        console.log(`    tool: ${tool.name || tool}`);
      }
    }
  }
}

console.log('[skill-bridge] Done');
