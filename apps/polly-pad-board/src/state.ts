export type ScreenId = 'ops' | 'review' | 'build' | 'research';
export type AppId =
  | 'shell'
  | 'pads'
  | 'approvals'
  | 'files'
  | 'audit'
  | 'timeline'
  | 'router'
  | 'scanner'
  | 'resources';
export type TaskState = 'pending' | 'done';
export type ApprovalState = 'review' | 'approved' | 'denied';

export interface PollyTask {
  id: string;
  text: string;
  state: TaskState;
  createdAt: string;
  completedAt?: string;
}

export interface PollyNote {
  id: string;
  text: string;
  createdAt: string;
}

export interface PollyPad {
  id: string;
  name: string;
  createdAt: string;
  tasks: PollyTask[];
  notes: PollyNote[];
}

export interface ApprovalItem {
  id: string;
  label: string;
  risk: 'low' | 'medium' | 'high';
  state: ApprovalState;
  source: string;
  createdAt: string;
  decidedAt?: string;
}

export interface AuditEvent {
  id: string;
  ts: string;
  actor: string;
  action: string;
  subject: string;
  payload: Record<string, unknown>;
  prevHash: string;
  eventHash: string;
}

export interface ScreenState {
  id: ScreenId;
  name: string;
  apps: AppId[];
}

export interface PollyBoardState {
  schemaVersion: 'polly_pad_board_v1';
  activeScreenId: ScreenId;
  activePadId: string;
  screens: ScreenState[];
  pads: PollyPad[];
  approvals: ApprovalItem[];
  files: Record<string, string>;
  audit: AuditEvent[];
}

export interface ShellLine {
  id: string;
  kind: 'input' | 'output' | 'error';
  text: string;
}

export const STORAGE_KEY = 'scbe:polly-pad-board:v1';
export const GENESIS_HASH = '0'.repeat(64);

let sequence = 0;

export function makeId(prefix: string): string {
  sequence += 1;
  return `${prefix}-${Date.now().toString(36)}-${sequence.toString(36)}`;
}

export function stableHash(input: string): string {
  let h1 = 0xdeadbeef;
  let h2 = 0x41c6ce57;
  for (let i = 0; i < input.length; i += 1) {
    const ch = input.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (h2 >>> 0).toString(16).padStart(8, '0') + (h1 >>> 0).toString(16).padStart(8, '0');
}

export function appendAudit(
  state: PollyBoardState,
  action: string,
  subject: string,
  payload: Record<string, unknown> = {}
): PollyBoardState {
  const prevHash = state.audit.length
    ? state.audit[state.audit.length - 1].eventHash
    : GENESIS_HASH;
  const eventBase = {
    id: makeId('evt'),
    ts: new Date().toISOString(),
    actor: 'polly-board',
    action,
    subject,
    payload,
    prevHash,
  };
  const eventHash = stableHash(JSON.stringify(eventBase));
  return {
    ...state,
    audit: [...state.audit, { ...eventBase, eventHash }],
  };
}

export function createInitialState(): PollyBoardState {
  const now = new Date().toISOString();
  const padId = 'pad-default';
  const base: PollyBoardState = {
    schemaVersion: 'polly_pad_board_v1',
    activeScreenId: 'ops',
    activePadId: padId,
    screens: [
      { id: 'ops', name: 'Ops', apps: ['shell', 'pads', 'timeline', 'files'] },
      { id: 'review', name: 'Review', apps: ['scanner', 'approvals', 'audit', 'router'] },
      { id: 'build', name: 'Build', apps: ['shell', 'files', 'scanner', 'audit'] },
      { id: 'research', name: 'Research', apps: ['pads', 'resources', 'timeline', 'audit'] },
    ],
    pads: [
      {
        id: padId,
        name: 'Main Workpad',
        createdAt: now,
        tasks: [
          {
            id: 'task-open-board',
            text: 'Wire visual board into Polly Pad workflow',
            state: 'pending',
            createdAt: now,
          },
        ],
        notes: [
          {
            id: 'note-source',
            text: 'Source: Kimi Agent Web OS Build archive; adapted into SCBE Polly Pad Board.',
            createdAt: now,
          },
        ],
      },
    ],
    approvals: [
      {
        id: 'gate-live-shell',
        label: 'Connect host shell bridge after governance endpoint exists',
        risk: 'high',
        state: 'review',
        source: 'system',
        createdAt: now,
      },
      {
        id: 'gate-agent-bus',
        label: 'Attach board events to agent-bus packet planner',
        risk: 'medium',
        state: 'review',
        source: 'system',
        createdAt: now,
      },
    ],
    files: {
      '/pads/main.md':
        '# Main Workpad\n\nUse `task add`, `note add`, and `route` to build the board state.\n',
      '/handoff/README.md':
        'Local board state only. No live OAuth, mail, or provider calls are made from this app.\n',
    },
    audit: [],
  };
  return appendAudit(base, 'board.init', 'polly-pad-board', { padId });
}

export function activePad(state: PollyBoardState): PollyPad {
  return state.pads.find((pad) => pad.id === state.activePadId) ?? state.pads[0];
}

export function updateActivePad(
  state: PollyBoardState,
  updater: (pad: PollyPad) => PollyPad
): PollyBoardState {
  const activeId = activePad(state).id;
  return {
    ...state,
    activePadId: activeId,
    pads: state.pads.map((pad) => (pad.id === activeId ? updater(pad) : pad)),
  };
}

export function loadState(): PollyBoardState {
  if (typeof localStorage === 'undefined') return createInitialState();
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return createInitialState();
    const parsed = JSON.parse(raw) as PollyBoardState;
    if (parsed.schemaVersion !== 'polly_pad_board_v1') return createInitialState();
    return parsed;
  } catch {
    return createInitialState();
  }
}

export function saveState(state: PollyBoardState): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}
