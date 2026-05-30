#!/usr/bin/env node
'use strict';

const { spawnSync, execSync } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const readline = require('node:readline');

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const VERSION = '0.1.0';
const SCHEMA_PAD = 'polly_pad_v1';
const SCHEMA_RUN = 'polly_run_v1';
const SCHEMA_AUDIT = 'polly_audit_receipt_v1';
const GENESIS_HASH = '0'.repeat(64);

// ---------------------------------------------------------------------------
// Workspace management
// ---------------------------------------------------------------------------

function findWorkspaceRoot(startDir) {
  let dir = path.resolve(startDir);
  const root = path.parse(dir).root;
  while (true) {
    const candidate = path.join(dir, '.polly');
    if (fs.existsSync(candidate) && fs.statSync(candidate).isDirectory()) {
      return dir;
    }
    if (dir === root) return null;
    dir = path.dirname(dir);
  }
}

function requireWorkspace() {
  const ws = findWorkspaceRoot(process.cwd());
  if (!ws) {
    console.error('No .polly workspace found. Run `polly init` to create one.');
    process.exit(1);
  }
  return ws;
}

function readPad(ws) {
  const padPath = path.join(ws, '.polly', 'pad.json');
  if (!fs.existsSync(padPath)) return null;
  try {
    return JSON.parse(fs.readFileSync(padPath, 'utf8'));
  } catch (_) {
    return null;
  }
}

function writePad(ws, pad) {
  pad.updated_at = new Date().toISOString();
  const padPath = path.join(ws, '.polly', 'pad.json');
  const tmpPath = padPath + '.tmp.' + Date.now();
  fs.writeFileSync(tmpPath, JSON.stringify(pad, null, 2), 'utf8');
  fs.renameSync(tmpPath, padPath);
}

function initPad(name, ws) {
  return {
    schema_version: SCHEMA_PAD,
    pad_id: 'pad-' + Date.now().toString(36),
    name: name || 'default',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    attached_repo: detectGitRoot(ws),
    tasks: [],
    notes: [],
    run_counter: 0,
    config: {},
  };
}

// ---------------------------------------------------------------------------
// Audit receipts
// ---------------------------------------------------------------------------

function auditPath(ws) {
  return path.join(ws, '.polly', 'audit.jsonl');
}

function sortCanonical(value) {
  if (Array.isArray(value)) return value.map(sortCanonical);
  if (value && typeof value === 'object') {
    return Object.keys(value)
      .sort()
      .reduce((outObj, key) => {
        outObj[key] = sortCanonical(value[key]);
        return outObj;
      }, {});
  }
  return value;
}

function canonicalJson(value) {
  return JSON.stringify(sortCanonical(value));
}

function computeAuditHash(receipt) {
  const material = Object.assign({}, receipt);
  delete material.event_hash;
  return crypto.createHash('sha256').update(canonicalJson(material), 'utf8').digest('hex');
}

function readAuditEvents(ws) {
  const filePath = auditPath(ws);
  if (!fs.existsSync(filePath)) return [];
  const lines = fs.readFileSync(filePath, 'utf8').split(/\r?\n/).filter((line) => line.trim());
  return lines.map((line, idx) => {
    try {
      return JSON.parse(line);
    } catch (err) {
      const wrapped = new Error('Invalid JSON in audit ledger at line ' + (idx + 1) + ': ' + err.message);
      wrapped.auditLine = idx + 1;
      throw wrapped;
    }
  });
}

function appendAudit(ws, action, subject, payload) {
  const events = readAuditEvents(ws);
  const prevHash = events.length ? events[events.length - 1].event_hash : GENESIS_HASH;
  const receipt = {
    schema_version: SCHEMA_AUDIT,
    event_id: 'evt-' + Date.now().toString(36) + '-' + crypto.randomBytes(4).toString('hex'),
    ts: new Date().toISOString(),
    actor: 'polly',
    action,
    subject,
    payload: payload || {},
    prev_hash: prevHash,
  };
  receipt.event_hash = computeAuditHash(receipt);
  const filePath = auditPath(ws);
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.appendFileSync(filePath, canonicalJson(receipt) + '\n', 'utf8');
  return receipt;
}

function verifyAudit(ws) {
  let events;
  try {
    events = readAuditEvents(ws);
  } catch (err) {
    return {
      ok: false,
      count: 0,
      head_hash: GENESIS_HASH,
      broken_at: err.auditLine || 1,
      reason: err.message,
    };
  }

  let prevHash = GENESIS_HASH;
  for (let i = 0; i < events.length; i++) {
    const event = events[i];
    if (event.prev_hash !== prevHash) {
      return {
        ok: false,
        count: events.length,
        head_hash: prevHash,
        broken_at: i + 1,
        reason: 'previous hash mismatch',
      };
    }
    const expected = computeAuditHash(event);
    if (event.event_hash !== expected) {
      return {
        ok: false,
        count: events.length,
        head_hash: prevHash,
        broken_at: i + 1,
        reason: 'event hash mismatch',
      };
    }
    prevHash = event.event_hash;
  }
  return {
    ok: true,
    count: events.length,
    head_hash: prevHash,
    broken_at: null,
    reason: null,
  };
}

function exportAudit(ws) {
  const verified = verifyAudit(ws);
  return Object.assign(
    {
      ledger: auditPath(ws),
      events: verified.ok ? readAuditEvents(ws) : [],
    },
    verified
  );
}

// ---------------------------------------------------------------------------
// Git helpers
// ---------------------------------------------------------------------------

function detectGitRoot(dir) {
  try {
    return execSync('git rev-parse --show-toplevel', { cwd: dir, stdio: ['pipe', 'pipe', 'pipe'] })
      .toString()
      .trim();
  } catch (_) {
    return null;
  }
}

function getGitInfo(dir) {
  try {
    const branch = execSync('git rev-parse --abbrev-ref HEAD', { cwd: dir, stdio: ['pipe', 'pipe', 'pipe'] })
      .toString()
      .trim();
    const sha = execSync('git rev-parse --short HEAD', { cwd: dir, stdio: ['pipe', 'pipe', 'pipe'] })
      .toString()
      .trim();
    return { branch, sha };
  } catch (_) {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Task helpers
// ---------------------------------------------------------------------------

function nextTaskId(tasks) {
  return 'task-' + String(tasks.length + 1).padStart(3, '0');
}

function addTask(pad, text) {
  const task = {
    id: nextTaskId(pad.tasks),
    text,
    state: 'pending',
    created_at: new Date().toISOString(),
  };
  return Object.assign({}, pad, { tasks: [...pad.tasks, task] });
}

function updateTask(pad, id, state) {
  const tasks = pad.tasks.map((t) => (t.id === id ? Object.assign({}, t, { state, updated_at: new Date().toISOString() }) : t));
  return Object.assign({}, pad, { tasks });
}

function printTasks(pad) {
  const pending = (pad.tasks || []).filter((t) => t.state !== 'done');
  const done = (pad.tasks || []).filter((t) => t.state === 'done');
  if (!pad.tasks || pad.tasks.length === 0) {
    console.log('No tasks yet. Use `polly task add <text>` to add one.');
    return;
  }
  if (pending.length) {
    console.log('Pending:');
    pending.forEach((t) => console.log(`  [ ] ${t.id}: ${t.text}`));
  }
  if (done.length) {
    console.log('Done:');
    done.forEach((t) => console.log(`  [x] ${t.id}: ${t.text}`));
  }
}

// ---------------------------------------------------------------------------
// Run helpers
// ---------------------------------------------------------------------------

function nextRunId(pad) {
  return 'run-' + String((pad.run_counter || 0) + 1).padStart(3, '0');
}

function saveRun(ws, run) {
  const runsDir = path.join(ws, '.polly', 'runs');
  if (!fs.existsSync(runsDir)) fs.mkdirSync(runsDir, { recursive: true });
  fs.writeFileSync(path.join(runsDir, run.run_id + '.json'), JSON.stringify(run, null, 2), 'utf8');
}

function loadRun(ws, runId) {
  const runPath = path.join(ws, '.polly', 'runs', runId + '.json');
  if (!fs.existsSync(runPath)) return null;
  try {
    return JSON.parse(fs.readFileSync(runPath, 'utf8'));
  } catch (_) {
    return null;
  }
}

function listRuns(ws) {
  const runsDir = path.join(ws, '.polly', 'runs');
  if (!fs.existsSync(runsDir)) return [];
  return fs
    .readdirSync(runsDir)
    .filter((f) => f.endsWith('.json'))
    .map((f) => {
      try {
        return JSON.parse(fs.readFileSync(path.join(runsDir, f), 'utf8'));
      } catch (_) {
        return null;
      }
    })
    .filter(Boolean)
    .sort((a, b) => (a.run_id < b.run_id ? -1 : 1));
}

// ---------------------------------------------------------------------------
// LLM router
// ---------------------------------------------------------------------------

async function fetchWithTimeout(url, opts, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...opts, signal: controller.signal });
    clearTimeout(timer);
    return res;
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

async function tryOllama(prompt, model) {
  model = model || 'llama3.2';
  try {
    const res = await fetchWithTimeout(
      'http://localhost:11434/api/chat',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model,
          messages: [{ role: 'user', content: prompt }],
          stream: false,
        }),
      },
      8000
    );
    if (!res.ok) return null;
    const data = await res.json();
    const text = data && data.message && data.message.content ? data.message.content : null;
    if (!text) return null;
    return { text, model_used: model, source: 'ollama' };
  } catch (_) {
    return null;
  }
}

async function tryAnthropic(prompt) {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) return null;
  try {
    const res = await fetchWithTimeout(
      'https://api.anthropic.com/v1/messages',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': key,
          'anthropic-version': '2023-06-01',
        },
        body: JSON.stringify({
          model: 'claude-haiku-4-5-20251001',
          max_tokens: 2048,
          messages: [{ role: 'user', content: prompt }],
        }),
      },
      30000
    );
    if (!res.ok) return null;
    const data = await res.json();
    const text =
      data && data.content && data.content[0] && data.content[0].text ? data.content[0].text : null;
    if (!text) return null;
    return { text, model_used: 'claude-haiku-4-5-20251001', source: 'anthropic' };
  } catch (_) {
    return null;
  }
}

async function tryOpenAI(prompt) {
  const key = process.env.OPENAI_API_KEY;
  if (!key) return null;
  try {
    const res = await fetchWithTimeout(
      'https://api.openai.com/v1/chat/completions',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer ' + key,
        },
        body: JSON.stringify({
          model: 'gpt-4o-mini',
          messages: [{ role: 'user', content: prompt }],
        }),
      },
      30000
    );
    if (!res.ok) return null;
    const data = await res.json();
    const text =
      data &&
      data.choices &&
      data.choices[0] &&
      data.choices[0].message &&
      data.choices[0].message.content
        ? data.choices[0].message.content
        : null;
    if (!text) return null;
    return { text, model_used: 'gpt-4o-mini', source: 'openai' };
  } catch (_) {
    return null;
  }
}

function templateFallback(prompt) {
  const text = [
    '## Template Response (no LLM available)',
    '',
    'Prompt received:',
    prompt.slice(0, 200) + (prompt.length > 200 ? '...' : ''),
    '',
    '### Checklist',
    '- [ ] Review the prompt above',
    '- [ ] Identify key requirements',
    '- [ ] Break into actionable steps',
    '- [ ] Assign priorities',
    '- [ ] Set success criteria',
    '',
    '_Configure Ollama (localhost:11434), ANTHROPIC_API_KEY, or OPENAI_API_KEY to get real model responses._',
  ].join('\n');
  return { text, model_used: 'template', source: 'fallback' };
}

async function routeToModel(prompt) {
  const ollama = await tryOllama(prompt);
  if (ollama && ollama.text) return ollama;
  const anthropic = await tryAnthropic(prompt);
  if (anthropic && anthropic.text) return anthropic;
  const openai = await tryOpenAI(prompt);
  if (openai && openai.text) return openai;
  return templateFallback(prompt);
}

// ---------------------------------------------------------------------------
// Recipes
// ---------------------------------------------------------------------------

const RECIPES = {
  research: {
    description: 'Research thoroughly with key findings, sources, and open questions',
    build: (args) => 'Research thoroughly with key findings, sources, open questions:\n\n' + args,
  },
  write: {
    description: 'Write content with clear structure',
    build: (args) => 'Write the following with clear structure:\n\n' + args,
  },
  review: {
    description: 'Code review for a file or snippet',
    build: (args) => {
      const parts = args.split(/\s+/);
      const filePath = parts[0];
      let fileContent = '';
      if (filePath && fs.existsSync(filePath)) {
        try {
          fileContent = fs.readFileSync(filePath, 'utf8').slice(0, 4000);
        } catch (_) {
          fileContent = '[could not read file]';
        }
      }
      const extra = parts.slice(1).join(' ');
      return (
        'Code review the following' +
        (extra ? ' (' + extra + ')' : '') +
        ':\n\n```\n' +
        (fileContent || args) +
        '\n```\n\nProvide: summary, issues, suggestions, severity.'
      );
    },
  },
  plan: {
    description: 'Step-by-step plan with phases, dependencies, risks, success criteria',
    build: (args) =>
      'Step-by-step plan for:\n\n' + args + '\n\nInclude phases, deps, risks, success criteria.',
  },
  debug: {
    description: 'Debug an issue with root causes and fixes',
    build: (args) => 'Debug this issue with root causes and fixes:\n\n' + args,
  },
  convert: {
    description: 'Convert the following content',
    build: (args) => 'Convert the following:\n\n' + args,
  },
  summarize: {
    description: 'Summarize concisely',
    build: (args) => 'Summarize concisely:\n\n' + args,
  },
};

// ---------------------------------------------------------------------------
// Output helpers
// ---------------------------------------------------------------------------

function out(data, asJson) {
  if (asJson) {
    console.log(JSON.stringify(data, null, 2));
  } else if (typeof data === 'string') {
    console.log(data);
  } else {
    console.log(JSON.stringify(data, null, 2));
  }
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

const COMMANDS = {
  async init(args, flags) {
    const name = args[0] || 'default';
    const ws = process.cwd();
    const pollyDir = path.join(ws, '.polly');
    const runsDir = path.join(pollyDir, 'runs');
    const snapsDir = path.join(pollyDir, 'snapshots');
    const padPath = path.join(pollyDir, 'pad.json');

    if (fs.existsSync(padPath)) {
      const existing = readPad(ws);
      if (flags.json) {
        out({ status: 'exists', pad: existing }, true);
      } else {
        console.log('Workspace already exists: ' + pollyDir);
        console.log('Pad: ' + (existing && existing.name ? existing.name : '(unknown)'));
        console.log('Run `polly status` to see current state.');
      }
      return;
    }

    fs.mkdirSync(runsDir, { recursive: true });
    fs.mkdirSync(snapsDir, { recursive: true });

    const pad = initPad(name, ws);
    writePad(ws, pad);
    appendAudit(ws, 'workspace.init', pad.pad_id, { name: pad.name, attached_repo: pad.attached_repo });

    if (flags.json) {
      out({ status: 'created', pad }, true);
    } else {
      console.log('Polly workspace initialized: ' + pollyDir);
      console.log('Pad name: ' + pad.name);
      console.log('');
      console.log('Quick start:');
      console.log('  polly status          # see workspace state');
      console.log('  polly task add <text> # add a task');
      console.log('  polly ask <prompt>    # ask a model');
      console.log('  polly run research <topic> # use a recipe');
      console.log('  polly shell           # interactive REPL');
    }
  },

  async status(args, flags) {
    const ws = requireWorkspace();
    const pad = readPad(ws);
    if (!pad) {
      console.error('pad.json not found — workspace may be corrupted.');
      process.exit(1);
    }
    if (flags.json) {
      const gitInfo = getGitInfo(ws);
      out({ ...pad, _workspace: ws, _git: gitInfo }, true);
      return;
    }
    const gitInfo = getGitInfo(ws);
    const pending = (pad.tasks || []).filter((t) => t.state !== 'done').length;
    const done = (pad.tasks || []).filter((t) => t.state === 'done').length;
    const runs = listRuns(ws);
    const lastRun = runs.length ? runs[runs.length - 1] : null;
    console.log('Pad name    : ' + pad.name);
    console.log('Workspace   : ' + ws);
    console.log('Tasks       : ' + pending + ' pending, ' + done + ' done');
    console.log('Runs        : ' + (pad.run_counter || 0));
    if (lastRun) console.log('Last run    : ' + lastRun.run_id + ' (' + lastRun.started_at + ')');
    if (gitInfo) console.log('Git         : ' + gitInfo.branch + ' @ ' + gitInfo.sha);
    console.log('Updated     : ' + pad.updated_at);
  },

  async new(args, flags) {
    const ws = requireWorkspace();
    const old = readPad(ws);
    const name = args[0] || 'default';
    const pad = initPad(name, ws);
    pad.run_counter = old && old.run_counter ? old.run_counter : 0;
    writePad(ws, pad);
    appendAudit(ws, 'workspace.new', pad.pad_id, { name: pad.name, previous_pad_id: old ? old.pad_id : null });
    if (flags.json) {
      out({ status: 'replaced', pad }, true);
    } else {
      console.log('New pad created: ' + pad.name + ' (' + pad.pad_id + ')');
    }
  },

  async task(args, flags) {
    const ws = requireWorkspace();
    const [sub, ...rest] = args;

    if (!sub || sub === 'list') {
      const pad = readPad(ws);
      if (flags.json) {
        out(pad ? pad.tasks : [], true);
      } else {
        printTasks(pad || { tasks: [] });
      }
      return;
    }

    if (sub === 'add') {
      const text = rest.join(' ');
      if (!text) {
        console.error('Usage: polly task add <text>');
        process.exit(1);
      }
      let pad = readPad(ws);
      pad = addTask(pad, text);
      writePad(ws, pad);
      const added = pad.tasks[pad.tasks.length - 1];
      appendAudit(ws, 'task.add', added.id, { text: added.text, state: added.state });
      if (flags.json) {
        out(added, true);
      } else {
        console.log('Added ' + added.id + ': ' + added.text);
      }
      return;
    }

    if (sub === 'done') {
      const id = rest[0];
      if (!id) {
        console.error('Usage: polly task done <task-id>');
        process.exit(1);
      }
      let pad = readPad(ws);
      const exists = (pad.tasks || []).find((t) => t.id === id);
      if (!exists) {
        console.error('Task not found: ' + id);
        process.exit(1);
      }
      pad = updateTask(pad, id, 'done');
      writePad(ws, pad);
      appendAudit(ws, 'task.done', id, { text: exists.text });
      if (flags.json) {
        out({ status: 'done', id }, true);
      } else {
        console.log('Marked done: ' + id);
      }
      return;
    }

    if (sub === 'rm' || sub === 'remove') {
      const id = rest[0];
      if (!id) {
        console.error('Usage: polly task rm <task-id>');
        process.exit(1);
      }
      let pad = readPad(ws);
      const before = (pad.tasks || []).length;
      pad = Object.assign({}, pad, { tasks: (pad.tasks || []).filter((t) => t.id !== id) });
      if (pad.tasks.length === before) {
        console.error('Task not found: ' + id);
        process.exit(1);
      }
      writePad(ws, pad);
      appendAudit(ws, 'task.remove', id, {});
      if (flags.json) {
        out({ status: 'removed', id }, true);
      } else {
        console.log('Removed: ' + id);
      }
      return;
    }

    console.error('Unknown task subcommand: ' + sub + '. Use: add, list, done, rm');
    process.exit(1);
  },

  async ask(args, flags) {
    const ws = requireWorkspace();
    const prompt = args.join(' ');
    if (!prompt) {
      console.error('Usage: polly ask <prompt>');
      process.exit(1);
    }

    if (!flags.json) process.stdout.write('Thinking...');
    const started_at = new Date().toISOString();
    const result = await routeToModel(prompt);
    const finished_at = new Date().toISOString();
    if (!flags.json) process.stdout.write('\r\x1b[K');

    let pad = readPad(ws);
    const run_id = nextRunId(pad);
    const run = {
      schema_version: SCHEMA_RUN,
      run_id,
      command: 'ask',
      prompt,
      result: result.text,
      model_used: result.model_used,
      source: result.source,
      started_at,
      finished_at,
    };
    saveRun(ws, run);
    pad = Object.assign({}, pad, { run_counter: (pad.run_counter || 0) + 1 });
    writePad(ws, pad);
    appendAudit(ws, 'run.ask', run_id, {
      source: result.source,
      model_used: result.model_used,
      prompt_chars: prompt.length,
      result_chars: result.text.length,
    });

    if (flags.json) {
      out(run, true);
    } else {
      console.log(result.text);
      console.log('\n[' + run_id + ' via ' + result.source + ':' + result.model_used + ']');
    }
  },

  async run(args, flags) {
    const ws = requireWorkspace();
    const [recipe, ...recipeArgs] = args;

    if (!recipe) {
      console.error('Usage: polly run <recipe> [args...]');
      console.error('Recipes: ' + Object.keys(RECIPES).join(', '));
      process.exit(1);
    }

    const recipeObj = RECIPES[recipe];
    if (!recipeObj) {
      console.error('Unknown recipe: ' + recipe + '. Available: ' + Object.keys(RECIPES).join(', '));
      process.exit(1);
    }

    const prompt = recipeObj.build(recipeArgs.join(' '));

    if (flags['dry-run']) {
      if (flags.json) {
        out({ dry_run: true, recipe, prompt }, true);
      } else {
        console.log('--- Dry run prompt preview ---');
        console.log(prompt);
        console.log('--- End preview ---');
      }
      return;
    }

    if (!flags.json) process.stdout.write('Thinking...');
    const started_at = new Date().toISOString();
    const result = await routeToModel(prompt);
    const finished_at = new Date().toISOString();
    if (!flags.json) process.stdout.write('\r\x1b[K');

    let pad = readPad(ws);
    const run_id = nextRunId(pad);
    const run = {
      schema_version: SCHEMA_RUN,
      run_id,
      command: 'run',
      recipe,
      prompt,
      result: result.text,
      model_used: result.model_used,
      source: result.source,
      started_at,
      finished_at,
      dry_run: false,
    };
    saveRun(ws, run);
    pad = Object.assign({}, pad, { run_counter: (pad.run_counter || 0) + 1 });
    writePad(ws, pad);
    appendAudit(ws, 'run.recipe', run_id, {
      recipe,
      source: result.source,
      model_used: result.model_used,
      prompt_chars: prompt.length,
      result_chars: result.text.length,
    });

    if (flags.json) {
      out(run, true);
    } else {
      console.log(result.text);
      console.log('\n[' + run_id + ' via ' + result.source + ':' + result.model_used + ']');
    }
  },

  async runs(args, flags) {
    const ws = requireWorkspace();
    const allRuns = listRuns(ws);

    if (flags.json) {
      out(allRuns, true);
      return;
    }

    if (!allRuns.length) {
      console.log('No runs yet. Use `polly ask` or `polly run` to create one.');
      return;
    }

    const col = (s, w) => String(s || '').padEnd(w).slice(0, w);
    console.log(col('run_id', 10) + '  ' + col('command:recipe', 20) + '  ' + col('timestamp', 24) + '  ' + 'prompt (preview)');
    console.log('-'.repeat(90));
    for (const r of allRuns) {
      const cmdCol = r.recipe ? r.command + ':' + r.recipe : r.command || '';
      const preview = (r.prompt || '').replace(/\n/g, ' ').slice(0, 50);
      console.log(col(r.run_id, 10) + '  ' + col(cmdCol, 20) + '  ' + col(r.started_at, 24) + '  ' + preview);
    }
  },

  async show(args, flags) {
    const ws = requireWorkspace();
    const runId = args[0];
    if (!runId) {
      console.error('Usage: polly show <run-id>');
      process.exit(1);
    }
    const run = loadRun(ws, runId);
    if (!run) {
      console.error('Run not found: ' + runId);
      process.exit(1);
    }
    if (flags.json) {
      out(run, true);
      return;
    }
    console.log('Run ID  : ' + run.run_id);
    console.log('Command : ' + (run.recipe ? run.command + ':' + run.recipe : run.command));
    console.log('Model   : ' + run.model_used + ' (' + run.source + ')');
    console.log('Started : ' + run.started_at);
    console.log('Finished: ' + run.finished_at);
    console.log('');
    console.log('--- Prompt ---');
    console.log(run.prompt);
    console.log('');
    console.log('--- Result ---');
    console.log(run.result);
  },

  async export(args, flags) {
    const ws = requireWorkspace();
    const runId = args[0];
    if (!runId) {
      console.error('Usage: polly export <run-id>');
      process.exit(1);
    }
    const run = loadRun(ws, runId);
    if (!run) {
      console.error('Run not found: ' + runId);
      process.exit(1);
    }
    console.log(JSON.stringify(run, null, 2));
  },

  async snapshot(args, flags) {
    const ws = requireWorkspace();
    const pad = readPad(ws);
    const allRuns = listRuns(ws);
    const snapsDir = path.join(ws, '.polly', 'snapshots');
    if (!fs.existsSync(snapsDir)) fs.mkdirSync(snapsDir, { recursive: true });
    const snapId = 'snap-' + Date.now().toString(36);
    const snapPath = path.join(snapsDir, snapId + '.json');
    const snap = {
      schema_version: 'polly_snapshot_v1',
      snap_id: snapId,
      created_at: new Date().toISOString(),
      pad,
      runs: allRuns,
    };
    fs.writeFileSync(snapPath, JSON.stringify(snap, null, 2), 'utf8');
    appendAudit(ws, 'snapshot.create', snapId, { path: snapPath, run_count: allRuns.length });
    if (flags.json) {
      out({ status: 'saved', snap_id: snapId, path: snapPath }, true);
    } else {
      console.log('Snapshot saved: ' + snapPath);
    }
  },

  async attach(args, flags) {
    const ws = requireWorkspace();
    const targetPath = args[0] || process.cwd();
    const gitRoot = detectGitRoot(targetPath);
    if (!gitRoot) {
      console.error('No git repo found at: ' + targetPath);
      process.exit(1);
    }
    let pad = readPad(ws);
    pad = Object.assign({}, pad, { attached_repo: gitRoot });
    writePad(ws, pad);
    appendAudit(ws, 'repo.attach', gitRoot, {});
    if (flags.json) {
      out({ status: 'attached', attached_repo: gitRoot }, true);
    } else {
      console.log('Attached repo: ' + gitRoot);
    }
  },

  async detach(args, flags) {
    const ws = requireWorkspace();
    let pad = readPad(ws);
    pad = Object.assign({}, pad, { attached_repo: null });
    writePad(ws, pad);
    appendAudit(ws, 'repo.detach', 'workspace', {});
    if (flags.json) {
      out({ status: 'detached' }, true);
    } else {
      console.log('Detached from repo.');
    }
  },

  async handoff(args, flags) {
    const ws = requireWorkspace();
    const pad = readPad(ws);
    const allRuns = listRuns(ws);
    const lastRun = allRuns.length ? allRuns[allRuns.length - 1] : null;
    const gitInfo = getGitInfo(ws);
    const pending = (pad.tasks || []).filter((t) => t.state !== 'done');
    const packet = {
      schema_version: 'polly_handoff_v1',
      created_at: new Date().toISOString(),
      pad_summary: {
        pad_id: pad.pad_id,
        name: pad.name,
        pending_tasks: pending,
        run_count: pad.run_counter || 0,
        last_run: lastRun
          ? { run_id: lastRun.run_id, command: lastRun.command, started_at: lastRun.started_at }
          : null,
      },
      git: gitInfo,
      context: {
        cwd: process.cwd(),
        node_version: process.version,
        platform: process.platform,
      },
    };
    console.log(JSON.stringify(packet, null, 2));
  },

  async doctor(args, flags) {
    const checks = [];

    // Node version
    const nodeMajor = parseInt(process.version.replace('v', '').split('.')[0], 10);
    checks.push({
      label: 'Node >= 20',
      ok: nodeMajor >= 20,
      detail: process.version,
    });

    // Workspace
    const ws = findWorkspaceRoot(process.cwd());
    checks.push({ label: 'Workspace (.polly/)', ok: !!ws, detail: ws || 'not found' });

    // Ollama
    let ollamaOk = false;
    try {
      const res = await fetchWithTimeout('http://localhost:11434/api/tags', {}, 2000);
      ollamaOk = res.ok;
    } catch (_) {}
    checks.push({ label: 'Ollama (localhost:11434)', ok: ollamaOk, detail: ollamaOk ? 'reachable' : 'not reachable' });

    // Anthropic key
    const hasAnthropic = !!process.env.ANTHROPIC_API_KEY;
    checks.push({ label: 'ANTHROPIC_API_KEY', ok: hasAnthropic, detail: hasAnthropic ? 'set' : 'not set' });

    // OpenAI key
    const hasOpenAI = !!process.env.OPENAI_API_KEY;
    checks.push({ label: 'OPENAI_API_KEY', ok: hasOpenAI, detail: hasOpenAI ? 'set' : 'not set' });

    // Git
    const gitRoot = detectGitRoot(process.cwd());
    checks.push({ label: 'Git repo', ok: !!gitRoot, detail: gitRoot || 'not a git repo' });

    if (flags.json) {
      out(checks, true);
      return;
    }

    for (const c of checks) {
      const mark = c.ok ? '✓' : '✗';
      console.log((c.ok ? '\x1b[32m' : '\x1b[31m') + mark + '\x1b[0m ' + c.label + ' — ' + c.detail);
    }

    const anyLlm = ollamaOk || hasAnthropic || hasOpenAI;
    if (!anyLlm) {
      console.log('');
      console.log(
        'Tip: No LLM available. Start Ollama (https://ollama.ai) or set ANTHROPIC_API_KEY / OPENAI_API_KEY.'
      );
    }
  },

  async tools(args, flags) {
    const [sub, ...rest] = args;
    if (!sub || sub === 'list') {
      if (flags.json) {
        const list = Object.entries(RECIPES).map(([k, v]) => ({ name: k, description: v.description }));
        out(list, true);
        return;
      }
      console.log('Available recipes:');
      for (const [k, v] of Object.entries(RECIPES)) {
        console.log('  ' + k.padEnd(12) + v.description);
      }
      return;
    }
    if (sub === 'run') {
      await COMMANDS.run(rest, flags);
      return;
    }
    console.error('Unknown tools subcommand: ' + sub + '. Use: list, run');
    process.exit(1);
  },

  async audit(args, flags) {
    const ws = requireWorkspace();
    const [sub] = args;

    if (!sub || sub === 'verify') {
      const result = verifyAudit(ws);
      if (flags.json) {
        out(result, true);
      } else if (result.ok) {
        console.log('Audit OK: ' + result.count + ' receipts, head=' + result.head_hash);
      } else {
        console.log('Audit FAILED at receipt ' + result.broken_at + ': ' + result.reason);
        console.log('Head before failure: ' + result.head_hash);
      }
      process.exit(result.ok ? 0 : 2);
    }

    if (sub === 'list') {
      const events = readAuditEvents(ws);
      if (flags.json) {
        out(events, true);
        return;
      }
      if (!events.length) {
        console.log('No audit receipts yet.');
        return;
      }
      const col = (s, w) => String(s || '').padEnd(w).slice(0, w);
      console.log(col('event', 16) + '  ' + col('action', 18) + '  ' + col('subject', 22) + '  ' + 'time');
      console.log('-'.repeat(82));
      for (const event of events) {
        console.log(col(event.event_id, 16) + '  ' + col(event.action, 18) + '  ' + col(event.subject, 22) + '  ' + event.ts);
      }
      return;
    }

    if (sub === 'export') {
      out(exportAudit(ws), true);
      return;
    }

    console.error('Unknown audit subcommand: ' + sub + '. Use: verify, list, export');
    process.exit(1);
  },

  async shell(args, flags) {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout, prompt: 'polly> ' });
    console.log('Polly shell v' + VERSION + '. Type .exit to quit, .help for commands.');
    rl.prompt();
    rl.on('line', async (line) => {
      const trimmed = line.trim();
      if (!trimmed) {
        rl.prompt();
        return;
      }
      if (trimmed === '.exit' || trimmed === '.quit') {
        rl.close();
        return;
      }
      if (trimmed === '.help') {
        console.log('Commands: ' + Object.keys(COMMANDS).join(', '));
        console.log('Type .exit or .quit to leave.');
        rl.prompt();
        return;
      }
      try {
        const { args: parsedArgs, flags: parsedFlags } = parseArgs(trimmed.split(/\s+/));
        const [cmd, ...cmdArgs] = parsedArgs;
        if (!cmd) {
          rl.prompt();
          return;
        }
        const handler = COMMANDS[cmd];
        if (!handler) {
          console.error('Unknown command: ' + cmd);
        } else {
          await handler(cmdArgs, parsedFlags);
        }
      } catch (err) {
        console.error('Error: ' + err.message);
      }
      rl.prompt();
    });
    rl.on('close', () => {
      console.log('Bye.');
      process.exit(0);
    });
  },
};

// ---------------------------------------------------------------------------
// Arg parser
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const args = [];
  const flags = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const eqIdx = a.indexOf('=');
      if (eqIdx !== -1) {
        flags[a.slice(2, eqIdx)] = a.slice(eqIdx + 1);
      } else if (i + 1 < argv.length && !argv[i + 1].startsWith('-')) {
        flags[a.slice(2)] = argv[i + 1];
        i++;
      } else {
        flags[a.slice(2)] = true;
      }
    } else if (a.startsWith('-') && a.length === 2) {
      flags[a.slice(1)] = true;
    } else {
      args.push(a);
    }
  }
  return { args, flags };
}

// ---------------------------------------------------------------------------
// Help
// ---------------------------------------------------------------------------

const HELP = `polly v${VERSION} — governed terminal workpad for AI operators

Usage:
  polly <command> [options]

Commands:
  init [name]              Create a new .polly workspace in the current directory
  status                   Show workspace state (--json for full JSON)
  new [name]               Replace pad with a fresh one (keeps run counter)
  task add <text>          Add a task
  task list                List tasks (default subcommand)
  task done <id>           Mark task done
  task rm <id>             Remove task
  ask <prompt>             Send prompt to best available LLM, save run receipt
  run <recipe> [args...]   Run a named recipe through the LLM
  runs                     List all run receipts
  show <run-id>            Show full run details
  export <run-id>          Export run as JSON
  snapshot                 Save pad + runs snapshot to .polly/snapshots/
  attach [path]            Attach workspace to a git repo
  detach                   Detach from git repo
  handoff                  Export handoff packet (always JSON)
  audit verify             Verify hash-chained audit receipts
  audit list               List audit receipts
  audit export             Export audit receipts as JSON
  doctor                   Check environment (Node, Ollama, API keys, git)
  tools list               List available recipes
  tools run <name> [args]  Run a recipe
  shell                    Interactive REPL

Recipes (use with \`polly run <recipe> <args>\`):
  research   Research with key findings, sources, open questions
  write      Write content with clear structure
  review     Code review (pass a file path as first arg)
  plan       Step-by-step plan with phases, deps, risks, success criteria
  debug      Debug with root causes and fixes
  convert    Convert content
  summarize  Summarize concisely

Global flags:
  --json         Output JSON instead of human text
  --dry-run      (run command) Print prompt preview, skip model call
  --debug        Print stack trace on error
  -h, --help     Show this help
  -v, --version  Show version

LLM routing priority:
  1. Ollama (localhost:11434, llama3.2, 8s timeout)
  2. Anthropic (ANTHROPIC_API_KEY, claude-haiku-4-5-20251001, 30s)
  3. OpenAI   (OPENAI_API_KEY, gpt-4o-mini, 30s)
  4. Template fallback (no model required)

Examples:
  polly init MyProject
  polly task add "Fix the login bug"
  polly task done task-001
  polly ask "What is a Poincare ball model?"
  polly run research "hyperbolic geometry in AI safety"
  polly run review src/index.ts
  polly run plan --dry-run "migrate to new API"
  polly audit verify
  polly runs --json
  polly handoff | pbcopy
`;

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const rawArgs = process.argv.slice(2);
  if (!rawArgs.length || rawArgs[0] === '--help' || rawArgs[0] === '-h') {
    console.log(HELP);
    process.exit(0);
  }
  if (rawArgs[0] === '--version' || rawArgs[0] === '-v') {
    console.log('polly v' + VERSION);
    process.exit(0);
  }
  const { args, flags } = parseArgs(rawArgs);
  const [command, ...rest] = args;
  if (!command) {
    console.log(HELP);
    process.exit(0);
  }
  const handler = COMMANDS[command];
  if (!handler) {
    console.error('Unknown command: ' + command + '\nRun `polly --help` for usage.');
    process.exit(1);
  }
  try {
    await handler(rest, flags);
  } catch (err) {
    console.error('Error:', err.message);
    if (flags.debug) console.error(err.stack);
    process.exit(1);
  }
}

main();
