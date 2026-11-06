'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { scbeHome } = require('./provider-registry');

const COMMAND_NAME = /^[a-z][a-z0-9-]{0,31}$/;
const RESERVED = new Set([
  'help',
  'model',
  'tools',
  'permissions',
  'status',
  'resume',
  'clear',
  'compact',
  'commands',
  'command',
  'primitives',
  'wafer',
  'exit',
  'quit',
]);

function commandDirectories(workspaceRoot, options = {}) {
  return {
    user: path.join(scbeHome(options.env, options.home), 'commands'),
    project: path.join(path.resolve(workspaceRoot), '.scbe', 'commands'),
  };
}

function normalizeName(value) {
  const name = String(value || '')
    .trim()
    .toLowerCase()
    .replace(/^\//, '');
  if (!COMMAND_NAME.test(name) || RESERVED.has(name)) {
    throw new Error('command name must be a non-reserved 1-32 character kebab-case name');
  }
  return name;
}

function parseCommandFile(text) {
  const raw = String(text || '').replace(/^\uFEFF/, '');
  const metadata = {};
  let template = raw;
  if (raw.startsWith('---\n') || raw.startsWith('---\r\n')) {
    const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/);
    if (match) {
      for (const line of match[1].split(/\r?\n/)) {
        const separator = line.indexOf(':');
        if (separator > 0) {
          metadata[line.slice(0, separator).trim()] = line.slice(separator + 1).trim();
        }
      }
      template = raw.slice(match[0].length);
    }
  }
  return { metadata, template: template.trim() };
}

function serializeCommand(command) {
  const description = String(command.description || '').replace(/[\r\n]+/g, ' ').trim();
  const scope = command.scope || 'user';
  return [
    '---',
    `description: ${description || `Custom /${command.name} prompt`}`,
    `scope: ${scope}`,
    '---',
    String(command.template || '').trim(),
    '',
  ].join('\n');
}

function loadDirectory(dir, scope) {
  if (!fs.existsSync(dir)) return [];
  const rows = [];
  for (const file of fs.readdirSync(dir).filter((name) => name.endsWith('.md')).sort()) {
    const name = path.basename(file, '.md').toLowerCase();
    if (!COMMAND_NAME.test(name) || RESERVED.has(name)) continue;
    try {
      const parsed = parseCommandFile(fs.readFileSync(path.join(dir, file), 'utf8'));
      if (!parsed.template) continue;
      rows.push({
        name,
        scope,
        path: path.join(dir, file),
        description: parsed.metadata.description || `Custom /${name} prompt`,
        template: parsed.template,
      });
    } catch (_error) {
      // Listing one command must not fail because a sibling command is corrupt.
    }
  }
  return rows;
}

function listCommands(workspaceRoot, options = {}) {
  const dirs = commandDirectories(workspaceRoot, options);
  const user = loadDirectory(dirs.user, 'user');
  const project = loadDirectory(dirs.project, 'project');
  const combined = new Map(user.map((command) => [command.name, command]));
  for (const command of project) combined.set(command.name, command);
  return [...combined.values()].sort((a, b) => a.name.localeCompare(b.name));
}

function getCommand(workspaceRoot, name, options = {}) {
  const normalized = normalizeName(name);
  return listCommands(workspaceRoot, options).find((command) => command.name === normalized) || null;
}

function commandPath(workspaceRoot, name, scope, options = {}) {
  const dirs = commandDirectories(workspaceRoot, options);
  if (scope !== 'user' && scope !== 'project') throw new Error('scope must be user or project');
  return path.join(dirs[scope], `${normalizeName(name)}.md`);
}

function saveCommand(workspaceRoot, input, options = {}) {
  const name = normalizeName(input.name);
  const scope = input.scope === 'project' ? 'project' : 'user';
  const template = String(input.template || '').trim();
  if (!template || template.length > 20_000 || /\0/.test(template)) {
    throw new Error('command template must contain 1-20,000 printable characters');
  }
  const filePath = commandPath(workspaceRoot, name, scope, options);
  if (input.createOnly === true && fs.existsSync(filePath)) {
    throw new Error(`/${name} already exists in ${scope} commands`);
  }
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(
    filePath,
    serializeCommand({ name, scope, template, description: input.description }),
    'utf8'
  );
  return { name, scope, path: filePath, template, description: input.description || '' };
}

function deleteCommand(workspaceRoot, name, options = {}) {
  const normalized = normalizeName(name);
  const existing = options.scope
    ? loadDirectory(commandDirectories(workspaceRoot, options)[options.scope], options.scope).find(
        (command) => command.name === normalized
      )
    : getCommand(workspaceRoot, normalized, options);
  if (!existing) return null;
  fs.unlinkSync(existing.path);
  return existing;
}

function expandCommand(command, args = '') {
  const value = String(args || '').trim();
  let output = command.template;
  const tokens = ['$ARGUMENTS', '{{args}}', '{args}'];
  const hasToken = tokens.some((token) => output.includes(token));
  for (const token of tokens) output = output.split(token).join(value);
  if (!hasToken && value) output = `${output.trim()}\n\nArguments: ${value}`;
  return output.trim();
}

module.exports = {
  RESERVED,
  normalizeName,
  commandDirectories,
  parseCommandFile,
  listCommands,
  getCommand,
  saveCommand,
  deleteCommand,
  expandCommand,
};
