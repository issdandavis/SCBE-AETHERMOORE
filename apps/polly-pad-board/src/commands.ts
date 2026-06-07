import {
  ApprovalItem,
  PollyBoardState,
  activePad,
  appendAudit,
  makeId,
  updateActivePad,
} from './state';

export interface CommandResult {
  state: PollyBoardState;
  output: string[];
  error?: boolean;
}

export const HELP_LINES = [
  'help',
  'screens | screen <ops|review|build|research>',
  'pads | pad add <name> | pad use <id>',
  'task add <text> | task done <id>',
  'note add <text>',
  'approval list | approval approve <id> | approval deny <id>',
  'route <goal or handoff request>',
  'scan <text>',
  'fs ls | fs read <path> | fs write <path> <text>',
  'hash <text> | json <json> | calc <expr>',
  'audit | export',
];

function ok(state: PollyBoardState, output: string[]): CommandResult {
  return { state, output };
}

function fail(state: PollyBoardState, message: string): CommandResult {
  return { state, output: [message], error: true };
}

function tail(command: string, prefix: string): string {
  return command.slice(prefix.length).trim();
}

function safeCalc(expr: string): number {
  if (!/^[\d\s+\-*/%.()]+$/.test(expr)) {
    throw new Error('Only digits, whitespace, parentheses, and arithmetic operators are allowed.');
  }
  // This expression is constrained above to arithmetic characters only.
  // eslint-disable-next-line no-new-func
  return Function(`"use strict"; return (${expr})`)() as number;
}

async function sha256(text: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

export interface ScanVerdict {
  decision: 'ALLOW' | 'QUARANTINE' | 'DENY';
  risk: number;
  hits: string[];
}

export function scanText(text: string): ScanVerdict {
  const rules = [
    {
      label: 'instruction override',
      pattern: /ignore (all )?(previous|prior|system)/i,
      weight: 0.35,
    },
    {
      label: 'secret extraction',
      pattern: /(api[\s_-]?key|token|password|private key|credential)/i,
      weight: 0.28,
    },
    {
      label: 'shell destructive',
      pattern: /(rm\s+-rf|format\s+c:|del\s+\/f|shutdown\s+\/s)/i,
      weight: 0.4,
    },
    {
      label: 'network exfiltration',
      pattern: /(curl|wget|Invoke-WebRequest).*(http|https):\/\//i,
      weight: 0.22,
    },
    {
      label: 'automation escalation',
      pattern: /(bypass|disable).*(approval|governance|audit|scanner)/i,
      weight: 0.32,
    },
  ];
  const hits = rules.filter((rule) => rule.pattern.test(text));
  const compoundLift = hits.length >= 2 ? 0.18 : 0;
  const risk = Math.min(0.99, hits.reduce((sum, hit) => sum + hit.weight, 0.08) + compoundLift);
  const decision = risk >= 0.85 ? 'DENY' : risk >= 0.55 ? 'QUARANTINE' : 'ALLOW';
  return { decision, risk, hits: hits.map((hit) => hit.label) };
}

export async function executeCommand(
  state: PollyBoardState,
  rawCommand: string
): Promise<CommandResult> {
  const command = rawCommand.trim();
  if (!command) return ok(state, []);

  if (command === 'help') return ok(state, HELP_LINES);

  if (command === 'screens') {
    return ok(
      state,
      state.screens.map(
        (screen) =>
          `${screen.id}${screen.id === state.activeScreenId ? ' *' : ''}: ${screen.apps.join(', ')}`
      )
    );
  }

  if (command.startsWith('screen ')) {
    const screenId = tail(command, 'screen ') as PollyBoardState['activeScreenId'];
    if (!state.screens.some((screen) => screen.id === screenId))
      return fail(state, `Unknown screen: ${screenId}`);
    const next = appendAudit({ ...state, activeScreenId: screenId }, 'screen.switch', screenId, {});
    return ok(next, [`screen: ${screenId}`]);
  }

  if (command === 'pads') {
    return ok(
      state,
      state.pads.map((pad) => {
        const open = pad.tasks.filter((task) => task.state !== 'done').length;
        return `${pad.id}${pad.id === state.activePadId ? ' *' : ''}: ${pad.name} (${open} open tasks, ${pad.notes.length} notes)`;
      })
    );
  }

  if (command.startsWith('pad add ')) {
    const name = tail(command, 'pad add ');
    if (!name) return fail(state, 'Pad name is required.');
    const id = makeId('pad');
    const pad = { id, name, createdAt: new Date().toISOString(), tasks: [], notes: [] };
    const next = appendAudit(
      { ...state, activePadId: id, pads: [...state.pads, pad] },
      'pad.add',
      id,
      { name }
    );
    return ok(next, [`created pad ${id}: ${name}`]);
  }

  if (command.startsWith('pad use ')) {
    const id = tail(command, 'pad use ');
    if (!state.pads.some((pad) => pad.id === id)) return fail(state, `Unknown pad: ${id}`);
    const next = appendAudit({ ...state, activePadId: id }, 'pad.use', id, {});
    return ok(next, [`active pad: ${id}`]);
  }

  if (command.startsWith('task add ')) {
    const text = tail(command, 'task add ');
    if (!text) return fail(state, 'Task text is required.');
    const id = makeId('task');
    const next = updateActivePad(state, (pad) => ({
      ...pad,
      tasks: [...pad.tasks, { id, text, state: 'pending', createdAt: new Date().toISOString() }],
    }));
    return ok(appendAudit(next, 'task.add', id, { padId: activePad(next).id, text }), [
      `added task ${id}`,
    ]);
  }

  if (command.startsWith('task done ')) {
    const id = tail(command, 'task done ');
    let changed = false;
    const next = updateActivePad(state, (pad) => ({
      ...pad,
      tasks: pad.tasks.map((task) => {
        if (task.id !== id) return task;
        changed = true;
        return { ...task, state: 'done', completedAt: new Date().toISOString() };
      }),
    }));
    if (!changed) return fail(state, `Task not found on active pad: ${id}`);
    return ok(appendAudit(next, 'task.done', id, { padId: activePad(next).id }), [
      `completed task ${id}`,
    ]);
  }

  if (command.startsWith('note add ')) {
    const text = tail(command, 'note add ');
    if (!text) return fail(state, 'Note text is required.');
    const id = makeId('note');
    const next = updateActivePad(state, (pad) => ({
      ...pad,
      notes: [...pad.notes, { id, text, createdAt: new Date().toISOString() }],
    }));
    return ok(appendAudit(next, 'note.add', id, { padId: activePad(next).id }), [
      `added note ${id}`,
    ]);
  }

  if (command === 'approval list') {
    return ok(
      state,
      state.approvals.map(
        (item) => `${item.id}: ${item.state.toUpperCase()} ${item.risk} - ${item.label}`
      )
    );
  }

  if (command.startsWith('approval approve ') || command.startsWith('approval deny ')) {
    const approving = command.startsWith('approval approve ');
    const id = tail(command, approving ? 'approval approve ' : 'approval deny ');
    let found = false;
    const nextApprovals = state.approvals.map((item) => {
      if (item.id !== id) return item;
      found = true;
      return {
        ...item,
        state: approving ? 'approved' : 'denied',
        decidedAt: new Date().toISOString(),
      } satisfies ApprovalItem;
    });
    if (!found) return fail(state, `Approval not found: ${id}`);
    const next = appendAudit(
      { ...state, approvals: nextApprovals },
      approving ? 'approval.approve' : 'approval.deny',
      id,
      {}
    );
    return ok(next, [`${approving ? 'approved' : 'denied'} ${id}`]);
  }

  if (command.startsWith('route ')) {
    const label = tail(command, 'route ');
    if (!label) return fail(state, 'Route goal is required.');
    const id = makeId('route');
    const item: ApprovalItem = {
      id,
      label,
      risk: 'medium',
      state: 'review',
      source: 'polly-shell',
      createdAt: new Date().toISOString(),
    };
    const next = appendAudit(
      { ...state, approvals: [...state.approvals, item] },
      'route.request',
      id,
      { label }
    );
    return ok(next, [`routing request staged for review: ${id}`]);
  }

  if (command.startsWith('scan ')) {
    const verdict = scanText(tail(command, 'scan '));
    const next = appendAudit(state, 'scanner.scan', verdict.decision.toLowerCase(), {
      risk: verdict.risk,
      hits: verdict.hits,
    });
    return ok(next, [
      `${verdict.decision} risk=${verdict.risk.toFixed(2)} hits=${verdict.hits.join(', ') || 'none'}`,
    ]);
  }

  if (command === 'fs ls') return ok(state, Object.keys(state.files).sort());

  if (command.startsWith('fs read ')) {
    const path = tail(command, 'fs read ');
    if (!Object.prototype.hasOwnProperty.call(state.files, path))
      return fail(state, `File not found: ${path}`);
    return ok(state, [state.files[path]]);
  }

  if (command.startsWith('fs write ')) {
    const args = tail(command, 'fs write ');
    const firstSpace = args.indexOf(' ');
    if (firstSpace < 1) return fail(state, 'Usage: fs write <path> <text>');
    const path = args.slice(0, firstSpace);
    const content = args.slice(firstSpace + 1);
    const next = appendAudit(
      { ...state, files: { ...state.files, [path]: content } },
      'fs.write',
      path,
      {
        bytes: content.length,
      }
    );
    return ok(next, [`wrote ${content.length} bytes to ${path}`]);
  }

  if (command.startsWith('hash ')) return ok(state, [await sha256(tail(command, 'hash '))]);

  if (command.startsWith('json ')) {
    try {
      return ok(state, [JSON.stringify(JSON.parse(tail(command, 'json ')), null, 2)]);
    } catch (error) {
      return fail(state, error instanceof Error ? error.message : 'Invalid JSON');
    }
  }

  if (command.startsWith('calc ')) {
    try {
      return ok(state, [String(safeCalc(tail(command, 'calc ')))]);
    } catch (error) {
      return fail(state, error instanceof Error ? error.message : 'Invalid arithmetic expression');
    }
  }

  if (command === 'audit') {
    return ok(
      state,
      state.audit
        .slice(-12)
        .map((event) => `${event.ts} ${event.action} ${event.subject} ${event.eventHash}`)
    );
  }

  if (command === 'export') return ok(state, [JSON.stringify(state, null, 2)]);

  return fail(state, `Unknown command: ${command}. Type help.`);
}
