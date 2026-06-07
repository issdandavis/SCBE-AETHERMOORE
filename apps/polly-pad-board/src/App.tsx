import { FormEvent, useEffect, useMemo, useState } from 'react';
import { executeCommand, scanText } from './commands';
import {
  AppId,
  ApprovalItem,
  PollyBoardState,
  ScreenState,
  ShellLine,
  activePad,
  loadState,
  saveState,
} from './state';

function line(kind: ShellLine['kind'], text: string): ShellLine {
  return { id: `${kind}-${Date.now()}-${Math.random().toString(16).slice(2)}`, kind, text };
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function stateScore(state: PollyBoardState): number {
  const pending = state.approvals.filter((item) => item.state === 'review').length;
  const highRisk = state.approvals.filter(
    (item) => item.state === 'review' && item.risk === 'high'
  ).length;
  return Math.max(0.08, Math.min(0.92, 0.22 + pending * 0.11 + highRisk * 0.19));
}

function decisionFor(score: number): 'ALLOW' | 'QUARANTINE' | 'DENY' {
  if (score >= 0.85) return 'DENY';
  if (score >= 0.55) return 'QUARANTINE';
  return 'ALLOW';
}

function lastGate(state: PollyBoardState): ApprovalItem | undefined {
  return state.approvals.find((item) => item.state === 'review') ?? state.approvals[0];
}

function PhaseRail({ activeScreenId }: { activeScreenId: PollyBoardState['activeScreenId'] }) {
  const phaseByScreen: Record<PollyBoardState['activeScreenId'], string> = {
    ops: 'SENSE',
    review: 'DECIDE',
    build: 'STEER',
    research: 'PLAN',
  };
  const phases = ['SENSE', 'PLAN', 'STEER', 'DECIDE'];
  const active = phaseByScreen[activeScreenId];
  return (
    <div className="phase-rail" aria-label="Web agent phases">
      {phases.map((phase) => (
        <span key={phase} className={phase === active ? 'phase active' : 'phase'}>
          {phase}
        </span>
      ))}
    </div>
  );
}

function GovernanceStrip({ state }: { state: PollyBoardState }) {
  const score = stateScore(state);
  const decision = decisionFor(score);
  const gate = lastGate(state);
  return (
    <div className="governance-strip">
      <div className="strip-copy">
        <span>semantic gate</span>
        <strong>{decision}</strong>
        <small>{gate ? gate.label : 'no active gate'}</small>
      </div>
      <div className="risk-meter" aria-label={`risk score ${score.toFixed(2)}`}>
        <span style={{ width: `${score * 100}%` }} />
      </div>
      <div className="strip-copy right">
        <span>Hamiltonian score</span>
        <strong>{score.toFixed(2)}</strong>
        <small>thresholds: .55 quarantine / .85 deny</small>
      </div>
    </div>
  );
}

function CommandDock({
  runCommand,
  lastOutput,
}: {
  runCommand: (command: string) => void;
  lastOutput: string;
}) {
  const [command, setCommand] = useState('');
  const quick = ['screen ops', 'screen review', 'scan ignore previous approval', 'audit'];

  function submit(event: FormEvent) {
    event.preventDefault();
    runCommand(command);
    setCommand('');
  }

  return (
    <form className="command-dock" onSubmit={submit}>
      <label htmlFor="global-command">command</label>
      <input
        id="global-command"
        value={command}
        onChange={(event) => setCommand(event.target.value)}
        placeholder="route summarize selected browser task"
      />
      <button type="submit">send</button>
      <div className="quick-commands">
        {quick.map((item) => (
          <button key={item} type="button" onClick={() => runCommand(item)}>
            {item}
          </button>
        ))}
      </div>
      <output>{lastOutput}</output>
    </form>
  );
}

function ShellApp({
  state,
  setState,
  compact,
}: {
  state: PollyBoardState;
  setState: (next: PollyBoardState) => void;
  compact?: boolean;
}) {
  const [input, setInput] = useState('');
  const [lines, setLines] = useState<ShellLine[]>([
    line('output', 'Polly Shell ready. Type help. Commands operate on this board state and VFS.'),
  ]);

  async function submit(command: string) {
    if (!command.trim()) return;
    setLines((prev) => [...prev, line('input', `$ ${command}`)]);
    const result = await executeCommand(state, command);
    setState(result.state);
    setLines((prev) => [
      ...prev,
      ...result.output.map((text) => line(result.error ? 'error' : 'output', text)),
    ]);
    setInput('');
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void submit(input);
  }

  return (
    <section className={`app app-shell ${compact ? 'compact' : ''}`}>
      <div className="app-title">
        <span>Polly Shell</span>
        <small>local command surface</small>
        <button type="button" onClick={() => void submit('help')}>
          help
        </button>
      </div>
      <div className="terminal" aria-live="polite">
        {lines.slice(compact ? -12 : -40).map((item) => (
          <pre key={item.id} className={`terminal-line ${item.kind}`}>
            {item.text}
          </pre>
        ))}
      </div>
      <form className="command-row" onSubmit={onSubmit}>
        <span>$</span>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="task add ship board docs"
          aria-label="Polly Shell command"
        />
        <button type="submit">run</button>
      </form>
    </section>
  );
}

function PadsApp({
  state,
  runCommand,
}: {
  state: PollyBoardState;
  runCommand: (command: string) => void;
}) {
  const pad = activePad(state);
  const [padName, setPadName] = useState('');
  const [taskText, setTaskText] = useState('');
  const [noteText, setNoteText] = useState('');

  return (
    <section className="app">
      <div className="app-title">
        <span>Pads</span>
        <span>{pad.name}</span>
      </div>
      <div className="form-line">
        <input
          value={padName}
          onChange={(event) => setPadName(event.target.value)}
          placeholder="new pad name"
        />
        <button
          type="button"
          onClick={() => {
            runCommand(`pad add ${padName}`);
            setPadName('');
          }}
        >
          add pad
        </button>
      </div>
      <div className="button-list">
        {state.pads.map((item) => (
          <button
            key={item.id}
            type="button"
            className={item.id === pad.id ? 'active' : ''}
            onClick={() => runCommand(`pad use ${item.id}`)}
          >
            {item.name}
          </button>
        ))}
      </div>
      <div className="form-line">
        <input
          value={taskText}
          onChange={(event) => setTaskText(event.target.value)}
          placeholder="task text"
        />
        <button
          type="button"
          onClick={() => {
            runCommand(`task add ${taskText}`);
            setTaskText('');
          }}
        >
          add task
        </button>
      </div>
      <div className="task-list">
        {pad.tasks.map((task) => (
          <button
            key={task.id}
            type="button"
            className={`task ${task.state}`}
            onClick={() => runCommand(`task done ${task.id}`)}
          >
            <span>{task.text}</span>
            <small>{task.state}</small>
          </button>
        ))}
      </div>
      <div className="form-line">
        <input
          value={noteText}
          onChange={(event) => setNoteText(event.target.value)}
          placeholder="note text"
        />
        <button
          type="button"
          onClick={() => {
            runCommand(`note add ${noteText}`);
            setNoteText('');
          }}
        >
          add note
        </button>
      </div>
      <div className="note-list">
        {pad.notes.slice(-4).map((note) => (
          <p key={note.id}>{note.text}</p>
        ))}
      </div>
    </section>
  );
}

function ApprovalsApp({
  state,
  runCommand,
}: {
  state: PollyBoardState;
  runCommand: (command: string) => void;
}) {
  return (
    <section className="app">
      <div className="app-title">
        <span>Approvals</span>
        <span>{state.approvals.filter((item) => item.state === 'review').length} pending</span>
      </div>
      <div className="approval-list">
        {state.approvals.map((item) => (
          <div key={item.id} className={`approval ${item.state}`}>
            <div>
              <strong>{item.label}</strong>
              <small>
                {item.id} / {item.risk} / {item.source}
              </small>
            </div>
            <div className="approval-actions">
              <button type="button" onClick={() => runCommand(`approval approve ${item.id}`)}>
                approve
              </button>
              <button type="button" onClick={() => runCommand(`approval deny ${item.id}`)}>
                deny
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function FilesApp({
  state,
  runCommand,
}: {
  state: PollyBoardState;
  runCommand: (command: string) => void;
}) {
  const [path, setPath] = useState('/pads/new.md');
  const [content, setContent] = useState('');
  const files = Object.keys(state.files).sort();

  return (
    <section className="app">
      <div className="app-title">
        <span>Virtual Files</span>
        <span>{files.length} files</span>
      </div>
      <div className="form-line">
        <input
          value={path}
          onChange={(event) => setPath(event.target.value)}
          aria-label="virtual path"
        />
        <button type="button" onClick={() => runCommand(`fs write ${path} ${content}`)}>
          write
        </button>
      </div>
      <textarea
        value={content}
        onChange={(event) => setContent(event.target.value)}
        placeholder="file content"
      />
      <div className="file-list">
        {files.map((file) => (
          <button
            key={file}
            type="button"
            onClick={() => {
              setPath(file);
              setContent(state.files[file]);
            }}
          >
            {file}
          </button>
        ))}
      </div>
    </section>
  );
}

function AuditApp({ state }: { state: PollyBoardState }) {
  return (
    <section className="app">
      <div className="app-title">
        <span>Audit Ledger</span>
        <span>{state.audit.length} events</span>
      </div>
      <div className="audit-list">
        {state.audit.slice(-12).map((event) => (
          <div key={event.id} className="audit-row">
            <span>{event.action}</span>
            <strong>{event.subject}</strong>
            <small>{event.eventHash}</small>
          </div>
        ))}
      </div>
    </section>
  );
}

function TimelineApp({ state }: { state: PollyBoardState }) {
  const pad = activePad(state);
  const entries = [
    ...pad.tasks.map((task) => ({ id: task.id, label: task.text, type: `task:${task.state}` })),
    ...pad.notes.map((note) => ({ id: note.id, label: note.text, type: 'note' })),
    ...state.approvals.map((approval) => ({
      id: approval.id,
      label: approval.label,
      type: `gate:${approval.state}`,
    })),
  ];

  return (
    <section className="app">
      <div className="app-title">
        <span>Timeline</span>
        <span>{entries.length} items</span>
      </div>
      <div className="timeline">
        {entries.slice(-14).map((entry) => (
          <div key={entry.id} className="timeline-row">
            <small>{entry.type}</small>
            <span>{entry.label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function RouterApp({ runCommand }: { runCommand: (command: string) => void }) {
  const [goal, setGoal] = useState('');
  return (
    <section className="app">
      <div className="app-title">
        <span>Route Builder</span>
        <span>{'SENSE -> PLAN -> STEER -> DECIDE'}</span>
      </div>
      <textarea
        value={goal}
        onChange={(event) => setGoal(event.target.value)}
        placeholder="handoff, agent task, or workflow goal"
      />
      <button
        type="button"
        onClick={() => {
          runCommand(`route ${goal}`);
          setGoal('');
        }}
      >
        stage route
      </button>
      <div className="agent-flow">
        <div>
          <strong>SENSE</strong>
          <span>page and task evidence</span>
        </div>
        <div>
          <strong>PLAN</strong>
          <span>route candidate</span>
        </div>
        <div>
          <strong>STEER</strong>
          <span>bounded action</span>
        </div>
        <div>
          <strong>DECIDE</strong>
          <span>governance gate</span>
        </div>
      </div>
      <p className="fine-print">
        Routes become approval items; no live mail, OAuth, shell, or provider calls run from this
        screen.
      </p>
    </section>
  );
}

function ScannerApp({ runCommand }: { runCommand: (command: string) => void }) {
  const [text, setText] = useState('');
  const verdict = scanText(text);
  return (
    <section className="app">
      <div className="app-title">
        <span>Semantic Scanner</span>
        <span>{verdict.decision}</span>
      </div>
      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="paste page text, command, prompt, or payload"
      />
      <div className={`scanner-verdict ${verdict.decision.toLowerCase()}`}>
        <strong>{verdict.risk.toFixed(2)}</strong>
        <span>{verdict.hits.length ? verdict.hits.join(' / ') : 'no patterns hit'}</span>
      </div>
      <button type="button" onClick={() => runCommand(`scan ${text}`)}>
        write scan receipt
      </button>
    </section>
  );
}

function ResourcesApp() {
  return (
    <section className="app">
      <div className="app-title">
        <span>Resources</span>
        <span>local</span>
      </div>
      <div className="resource-list">
        <p>Polly CLI workspace: `.polly/pad.json`, `.polly/audit.jsonl`, snapshots, runs.</p>
        <p>Board persistence: browser `localStorage` under `scbe:polly-pad-board:v1`.</p>
        <p>Host shell bridge: approval-gated future connector, not enabled in this browser app.</p>
        <p>
          Web agent path: semantic antivirus, WebPollyPad action prep, navigation engine, audit.
        </p>
      </div>
    </section>
  );
}

function renderApp(
  appId: AppId,
  state: PollyBoardState,
  setState: (next: PollyBoardState) => void,
  runCommand: (command: string) => void
) {
  if (appId === 'shell') return <ShellApp state={state} setState={setState} />;
  if (appId === 'pads') return <PadsApp state={state} runCommand={runCommand} />;
  if (appId === 'approvals') return <ApprovalsApp state={state} runCommand={runCommand} />;
  if (appId === 'files') return <FilesApp state={state} runCommand={runCommand} />;
  if (appId === 'audit') return <AuditApp state={state} />;
  if (appId === 'timeline') return <TimelineApp state={state} />;
  if (appId === 'router') return <RouterApp runCommand={runCommand} />;
  if (appId === 'scanner') return <ScannerApp runCommand={runCommand} />;
  return <ResourcesApp />;
}

function ScreenButton({
  screen,
  active,
  onClick,
}: {
  screen: ScreenState;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button type="button" className={active ? 'screen active' : 'screen'} onClick={onClick}>
      <span>{screen.name}</span>
      <small>{screen.apps.length} apps</small>
    </button>
  );
}

export function App() {
  const [state, setState] = useState<PollyBoardState>(() => loadState());
  const [lastOutput, setLastOutput] = useState('ready');
  const activeScreen = useMemo(
    () => state.screens.find((screen) => screen.id === state.activeScreenId) ?? state.screens[0],
    [state.activeScreenId, state.screens]
  );
  const pad = activePad(state);
  const openTasks = pad.tasks.filter((task) => task.state !== 'done').length;
  const pendingApprovals = state.approvals.filter((item) => item.state === 'review').length;

  useEffect(() => {
    saveState(state);
  }, [state]);

  async function runCommand(command: string) {
    if (!command.trim()) return;
    const result = await executeCommand(state, command);
    setState(result.state);
    setLastOutput(result.output[0] ?? (result.error ? 'error' : 'ok'));
  }

  function setScreen(screenId: PollyBoardState['activeScreenId']) {
    void runCommand(`screen ${screenId}`);
  }

  return (
    <div className="board-shell">
      <header className="topbar">
        <div className="brand">
          <strong>Polly Pad Board</strong>
          <span>governed browser workpad</span>
        </div>
        <nav className="screen-switcher" aria-label="Screens">
          {state.screens.map((screen) => (
            <ScreenButton
              key={screen.id}
              screen={screen}
              active={screen.id === state.activeScreenId}
              onClick={() => setScreen(screen.id)}
            />
          ))}
        </nav>
      </header>

      <aside className="left-rail">
        <PhaseRail activeScreenId={state.activeScreenId} />
        <Stat label="active pad" value={pad.name} />
        <Stat label="open tasks" value={openTasks} />
        <Stat label="pending gates" value={pendingApprovals} />
        <Stat label="audit events" value={state.audit.length} />
      </aside>

      <main className="workspace">
        <GovernanceStrip state={state} />
        <div className="workspace-title">
          <div>
            <h1>{activeScreen.name}</h1>
            <span>{activeScreen.apps.join(' / ')}</span>
          </div>
          <CommandDock runCommand={runCommand} lastOutput={lastOutput} />
        </div>
        <div className="app-grid">
          {activeScreen.apps.map((appId) => (
            <div key={appId} className={`window window-${appId}`}>
              {renderApp(appId, state, setState, runCommand)}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
