'use strict';

const apiToken = document.querySelector('meta[name="scbe-api-token"]')?.content || '';

const state = {
  sessionId: '',
  busy: false,
  status: null,
  providers: [],
  sessions: [],
  tools: [],
  commands: [],
  trace: [],
  toolCalls: 0,
};

const $ = (selector) => document.querySelector(selector);
const elements = {
  composer: $('#composer'),
  input: $('#messageInput'),
  send: $('#sendButton'),
  log: $('#messageLog'),
  empty: $('#emptyState'),
  title: $('#conversationTitle'),
  modelButton: $('#modelButton'),
  modelLabel: $('#modelLabel'),
  modelDialog: $('#modelDialog'),
  providerSelect: $('#providerSelect'),
  modelInput: $('#modelInput'),
  modelFeedback: $('#modelFeedback'),
  permission: $('#permissionSelect'),
  sessions: $('#sessionList'),
  newSession: $('#newSessionButton'),
  compact: $('#compactButton'),
  workspace: $('#workspaceLabel'),
  health: $('#healthLight'),
  traceList: $('#traceList'),
  orbitNodes: $('#orbitNodes'),
  toolCount: $('#toolCount'),
  toolRegistry: $('#toolRegistry'),
  registryCount: $('#registryCount'),
  commandsButton: $('#commandsButton'),
  commandsDialog: $('#commandsDialog'),
  commandList: $('#commandList'),
  commandName: $('#commandName'),
  commandScope: $('#commandScope'),
  commandDescription: $('#commandDescription'),
  commandTemplate: $('#commandTemplate'),
  commandFeedback: $('#commandFeedback'),
  saveCommand: $('#saveCommandButton'),
  saveModel: $('#saveModelButton'),
  commandApproval: $('#commandApproval'),
  slashButton: $('#slashButton'),
  mechanicsButton: $('#mechanicsButton'),
  mechanicsDialog: $('#mechanicsDialog'),
  mechanicsClose: $('#mechanicsCloseButton'),
  primitiveIndex: $('#primitiveIndex'),
  primitiveStatus: $('#primitiveStatus'),
  primitiveKind: $('#primitiveKind'),
  primitivePattern: $('#primitivePattern'),
  primitiveDescription: $('#primitiveDescription'),
  primitiveForm: $('#primitiveForm'),
  primitiveTape: $('#primitiveTape'),
  primitiveRuntime: $('#primitiveRuntime'),
  compositionGrid: $('#compositionGrid'),
  tongueLanes: $('#tongueLanes'),
  waferSurface: $('#waferSurface'),
  opcodeCells: $('#opcodeCells'),
  waferViewStatus: $('#waferViewStatus'),
  waferName: $('#waferName'),
  waferSubtitle: $('#waferSubtitle'),
  waferEquation: $('#waferEquation'),
  waferCellCount: $('#waferCellCount'),
  waferTrimCost: $('#waferTrimCost'),
  waferNestId: $('#waferNestId'),
  waferNestControl: $('#waferNestControl'),
  waferProvenance: $('#waferProvenance'),
  toast: $('#toast'),
};

let primitiveBlueprints = [
  {
    key: 'DATA',
    kind: 'values',
    suppliedMark: '✓ 98.6%',
    pattern: 'join + take − weave ×',
    description: 'Number-realm operations over leaves 0–9. The conlang’s operate step.',
    form: 'value · operation · value',
    tape: 'read · op · write',
    runtime: ['read_file', 'search_text', 'workspace_info'],
  },
  {
    key: 'BIND',
    kind: 'state',
    suppliedMark: '✓ / calc 100%',
    pattern: 'let x = … ; body(x)',
    description:
      'Name an intermediate, store it, and reuse it. This is the tape’s memory cell without bloating the head.',
    form: 'let x = a ; f(x)',
    tape: 'store ↔ read',
    runtime: ['sessions', 'custom commands', 'edit_file'],
  },
  {
    key: 'BRANCH',
    kind: 'select',
    suppliedMark: '◇ free node',
    pattern: 'if v then a else b',
    description:
      'Choose a path on a value. The up/down signal becomes the yes/no split at the read head.',
    form: 'if · yes / no',
    tape: 'read · choose · move',
    runtime: ['provider routing', 'permissions', 'tool refusal'],
  },
  {
    key: 'LOOP',
    kind: 'iterate',
    suppliedMark: '◇ free node',
    pattern: 'while v: body',
    description:
      'Repeat with carried state. The inscribed circle closes the cycle; BIND holds the counter.',
    form: 'while · repeat · carry',
    tape: 'read · cycle ◯ · return',
    runtime: ['iterative tool rounds', 'resume', 'compact'],
  },
];

let compositionBlueprints = [
  { form: 'a ; b', name: 'Sequence', meaning: 'do a, then b; the tape moves right' },
  { form: 'let x = a ; f(x)', name: 'Bind', meaning: 'name an intermediate, store it, reuse it' },
  { form: 'if v then a else b', name: 'Branch', meaning: 'the up/down signal selects a path' },
  { form: 'while v: body', name: 'Loop', meaning: 'iterate with carried state' },
];

let tongueBlueprints = [
  { name: "Kor'aelin", lane: 'py', phi: 1.0 },
  { name: 'Avali', lane: 'js', phi: 1.62 },
  { name: 'Runethic', lane: 'rust', phi: 2.62 },
  { name: 'Cassisivadan', lane: 'math', phi: 4.24 },
  { name: 'Umbroth', lane: 'hs', phi: 6.85 },
  { name: 'Draumric', lane: 'md', phi: 11.09 },
];

let waferBlueprint = {
  name: 'j-space wafer',
  subtitle: 'the fold heals',
  opcodeCells: 64,
  disk: 'Poincaré disk',
  sheet: '−x₀² + x₁² + x₂² = −1',
  trimCost: 3.997e-15,
  realmDirection: 'realm 0 is the inward nest; realm 3 meets the outer bevel where d_H diverges',
  control: { id: 'nest', label: 'Nest cost', direction: 'inward' },
  provenance:
    'Geometry labels and numeric milestone are project-owner supplied interface data; this interface does not recompute the proof.',
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      'content-type': 'application/json',
      'x-scbe-web-token': apiToken,
      ...(options.headers || {}),
    },
  });
  const payload = await response.json();
  if (!response.ok || payload.ok === false)
    throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

function toast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => elements.toast.classList.remove('show'), 2400);
}

function setBusy(value) {
  state.busy = value;
  elements.send.disabled = value;
  elements.input.disabled = value;
  elements.send.querySelector('span').textContent = value ? 'Working' : 'Send';
}

function revealConversation() {
  elements.empty.hidden = true;
  elements.log.classList.add('active');
}

function appendMessage(role, content, options = {}) {
  revealConversation();
  const article = document.createElement('article');
  article.className = `message ${role}${options.className ? ` ${options.className}` : ''}`;
  const label = document.createElement('span');
  label.className = 'message-role';
  label.textContent = role === 'user' ? 'You' : role === 'assistant' ? 'SCBE' : role;
  const body = document.createElement('div');
  body.className = 'message-content';
  body.textContent = content;
  article.append(label, body);
  elements.log.append(article);
  elements.log.scrollTop = elements.log.scrollHeight;
  return article;
}

function clearMessages() {
  elements.log.replaceChildren();
  elements.log.classList.remove('active');
  elements.empty.hidden = false;
  elements.title.textContent = 'What are we making?';
  state.trace = [];
  state.toolCalls = 0;
  renderTrace();
}

function renderSessionMessages(messages = []) {
  clearMessages();
  for (const message of messages) {
    if (message.role === 'user' || message.role === 'assistant')
      appendMessage(message.role, message.content || '');
  }
}

function shortTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date);
}

function renderSessions() {
  elements.sessions.replaceChildren();
  for (const session of state.sessions) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `session-item${session.id === state.sessionId ? ' active' : ''}`;
    button.dataset.sessionId = session.id;
    const title = document.createElement('strong');
    title.textContent = session.title || 'Conversation';
    const meta = document.createElement('small');
    meta.textContent = `${shortTime(session.updated_at)} · ${session.messages} messages`;
    button.append(title, meta);
    button.addEventListener('click', () => resumeSession(session.id));
    elements.sessions.append(button);
  }
}

function renderTools() {
  elements.toolRegistry.replaceChildren();
  for (const tool of state.tools) {
    const item = document.createElement('li');
    const strong = document.createElement('strong');
    strong.textContent = tool.name;
    item.append(strong, document.createTextNode(` · ${tool.kind}`));
    item.title = tool.description;
    elements.toolRegistry.append(item);
  }
  elements.registryCount.textContent = `${state.tools.length} tools`;
}

function renderProviders() {
  elements.providerSelect.replaceChildren();
  for (const provider of state.providers) {
    const option = document.createElement('option');
    option.value = provider.id;
    option.textContent = `${provider.label}${provider.configured ? '' : ' · key needed'}`;
    elements.providerSelect.append(option);
  }
  if (state.status) {
    elements.providerSelect.value = state.status.provider;
    elements.modelInput.value = state.status.model;
  }
}

function applyStatus(status) {
  state.status = status;
  state.sessionId = status.session_id;
  elements.modelLabel.textContent = `${status.provider}/${status.model}`;
  elements.permission.value = status.permission_mode;
  elements.workspace.textContent = status.workspace;
  elements.title.textContent = status.title || 'Conversation';
  elements.health.classList.add('online');
  renderProviders();
  renderSessions();
}

function renderTrace() {
  elements.traceList.replaceChildren();
  elements.orbitNodes.replaceChildren();
  elements.toolCount.textContent = String(state.toolCalls);
  if (!state.trace.length) {
    const empty = document.createElement('li');
    empty.className = 'trace-empty';
    empty.textContent = 'No tools used yet. Conversation alone is allowed.';
    elements.traceList.append(empty);
    return;
  }
  for (const [index, event] of state.trace.slice(-10).entries()) {
    const item = document.createElement('li');
    const name = document.createElement('strong');
    name.textContent = event.tool || event.type;
    const stateLabel = document.createElement('small');
    stateLabel.textContent =
      event.ok === false
        ? 'failed'
        : event.denied
          ? 'blocked'
          : event.type === 'tool_start'
            ? 'running'
            : 'complete';
    const detail = document.createElement('small');
    detail.textContent = event.duration_ms != null ? `${event.duration_ms}ms` : event.kind || '';
    item.append(name, stateLabel, detail);
    elements.traceList.append(item);

    if (event.type === 'tool_result') {
      const node = document.createElement('span');
      node.className = `orbit-node${event.denied ? ' denied' : event.ok === false ? ' failed' : ''}`;
      node.style.setProperty('--angle', `${(index * 137.5 + 22) % 360}deg`);
      node.style.setProperty('--radius', `${58 + (index % 3) * 30}px`);
      node.title = event.tool || 'tool call';
      elements.orbitNodes.append(node);
    }
  }
}

function ingestEvents(events = []) {
  for (const event of events) {
    if (event.type === 'tool_result') state.toolCalls += 1;
    if (event.type === 'tool_start' || event.type === 'tool_result') state.trace.push(event);
  }
  state.trace = state.trace.slice(-30);
  renderTrace();
}

function renderCommands() {
  elements.commandList.replaceChildren();
  if (!state.commands.length) {
    const empty = document.createElement('p');
    empty.textContent = 'No commands yet. Make the first one below.';
    elements.commandList.append(empty);
    return;
  }
  for (const command of state.commands) {
    const card = document.createElement('div');
    card.className = 'command-card';
    const name = document.createElement('strong');
    name.textContent = `/${command.name}`;
    const description = document.createElement('small');
    description.textContent = `${command.scope} · ${command.description}`;
    const use = document.createElement('button');
    use.type = 'button';
    use.textContent = 'Use';
    use.addEventListener('click', () => {
      elements.commandsDialog.close();
      elements.input.value = `/${command.name} `;
      elements.input.focus();
    });
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'delete';
    remove.textContent = 'Delete';
    remove.addEventListener('click', () => removeCommand(command));
    card.append(name, use, remove, description);
    elements.commandList.append(card);
  }
}

function selectPrimitive(key) {
  const index = primitiveBlueprints.findIndex((primitive) => primitive.key === key);
  if (index < 0) return;
  const primitive = primitiveBlueprints[index];
  document.querySelectorAll('[data-primitive]').forEach((button) => {
    const selected = button.dataset.primitive === primitive.key;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  elements.primitiveIndex.textContent = `${String(index + 1).padStart(2, '0')} / 04`;
  elements.primitiveStatus.textContent = `Supplied mark · ${primitive.suppliedMark}`;
  elements.primitiveKind.textContent = `${primitive.key} · ${primitive.kind}`;
  elements.primitivePattern.textContent = primitive.pattern;
  elements.primitiveDescription.textContent = primitive.description;
  elements.primitiveForm.textContent = primitive.form;
  elements.primitiveTape.textContent = primitive.tape;
  elements.primitiveRuntime.textContent = primitive.runtime.join(' · ');
}

function renderCompositions() {
  elements.compositionGrid.replaceChildren();
  for (const composition of compositionBlueprints) {
    const form = document.createElement('code');
    form.textContent = composition.form;
    const meaning = document.createElement('p');
    const name = document.createElement('strong');
    name.textContent = composition.name;
    meaning.append(name, document.createTextNode(` — ${composition.meaning}.`));
    elements.compositionGrid.append(form, meaning);
  }
}

function renderTongueLanes() {
  elements.tongueLanes.replaceChildren();
  const maximum = Math.max(...tongueBlueprints.map((tongue) => tongue.phi));
  for (const tongue of tongueBlueprints) {
    const row = document.createElement('div');
    row.className = 'tongue-lane';
    const name = document.createElement('span');
    name.textContent = `${tongue.name}/${tongue.lane}`;
    const track = document.createElement('span');
    track.className = 'tongue-track';
    const fill = document.createElement('i');
    fill.style.setProperty('--lane-width', `${(tongue.phi / maximum) * 100}%`);
    track.append(fill);
    const weight = document.createElement('output');
    weight.textContent = `φ${tongue.phi.toFixed(2)}`;
    row.append(name, track, weight);
    elements.tongueLanes.append(row);
  }
}

function buildOpcodeWafer() {
  elements.opcodeCells.replaceChildren();
  const realmRadii = [16, 28, 38, 45];
  const cellsPerRealm = Math.ceil(waferBlueprint.opcodeCells / 4);
  for (let opcode = 0; opcode < waferBlueprint.opcodeCells; opcode += 1) {
    const realm = Math.min(3, Math.floor(opcode / cellsPerRealm));
    const lane = opcode % cellsPerRealm;
    const angle = ((lane * 360) / cellsPerRealm + realm * 7.5 - 90) * (Math.PI / 180);
    const cell = document.createElement('span');
    cell.className = `opcode-cell realm-${realm}`;
    cell.style.setProperty('--cell-x', `${50 + Math.cos(angle) * realmRadii[realm]}%`);
    cell.style.setProperty('--cell-y', `${50 + Math.sin(angle) * realmRadii[realm]}%`);
    cell.title = `Opcode ${String(opcode).padStart(2, '0')} · realm ${realm}`;
    elements.opcodeCells.append(cell);
  }
}

function selectWaferView(view) {
  const descriptions = {
    disk: `Disk view · ${waferBlueprint.realmDirection}.`,
    sheet: `Sheet view · the same ${waferBlueprint.opcodeCells} cells projected onto ${waferBlueprint.sheet}.`,
    spin: 'Spin bands view · four realm bands turn around the fixed inward nest.',
  };
  if (!descriptions[view]) return;
  document.querySelectorAll('[data-wafer-view]').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.waferView === view));
  });
  elements.waferSurface.className = `wafer-surface view-${view}`;
  elements.waferSurface.setAttribute(
    'aria-label',
    `${descriptions[view]} ${waferBlueprint.opcodeCells} opcode cells are arranged in four realm bands.`
  );
  elements.waferViewStatus.textContent = descriptions[view];
}

function selectMechanicsTab(name, moveFocus = false) {
  const tabs = [...document.querySelectorAll('[data-mechanics-tab]')];
  const panels = [...document.querySelectorAll('[data-mechanics-panel]')];
  for (const tab of tabs) {
    const selected = tab.dataset.mechanicsTab === name;
    tab.setAttribute('aria-selected', String(selected));
    tab.tabIndex = selected ? 0 : -1;
    if (selected && moveFocus) tab.focus();
  }
  for (const panel of panels) panel.hidden = panel.dataset.mechanicsPanel !== name;
}

function initializeMechanics() {
  renderCompositions();
  renderTongueLanes();
  buildOpcodeWafer();
  selectPrimitive('DATA');
  selectWaferView('disk');

  document.querySelectorAll('[data-primitive]').forEach((button) => {
    button.addEventListener('click', () => selectPrimitive(button.dataset.primitive));
  });
  document.querySelectorAll('[data-wafer-view]').forEach((button) => {
    button.addEventListener('click', () => selectWaferView(button.dataset.waferView));
  });
  document.querySelectorAll('[data-mechanics-tab]').forEach((tab) => {
    tab.addEventListener('click', () => selectMechanicsTab(tab.dataset.mechanicsTab));
    tab.addEventListener('keydown', (event) => {
      const tabs = [...document.querySelectorAll('[data-mechanics-tab]')];
      const current = tabs.indexOf(tab);
      let next = null;
      if (event.key === 'ArrowRight') next = (current + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (current - 1 + tabs.length) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next == null) return;
      event.preventDefault();
      selectMechanicsTab(tabs[next].dataset.mechanicsTab, true);
    });
  });
}

function suppliedMilestoneMark(milestone = {}, fallback = '') {
  const prefix =
    milestone.state === 'reported-verified' ? '✓' : milestone.state === 'next-free-node' ? '◇' : '';
  return `${prefix} ${milestone.label || fallback}`.trim();
}

function applyMechanicsModel(mechanics) {
  if (!mechanics || typeof mechanics !== 'object') return;

  if (Array.isArray(mechanics.primitives) && mechanics.primitives.length) {
    primitiveBlueprints = mechanics.primitives.map((primitive) => {
      const key = String(primitive.label || primitive.id || '').toUpperCase();
      const fallback =
        primitiveBlueprints.find((candidate) => candidate.key === key) || primitiveBlueprints[0];
      return {
        ...fallback,
        key,
        suppliedMark: suppliedMilestoneMark(primitive.milestone, fallback.suppliedMark),
        pattern: primitive.expression || fallback.pattern,
        form: primitive.expression || fallback.form,
        runtime:
          Array.isArray(primitive.runtime) && primitive.runtime.length
            ? primitive.runtime
            : fallback.runtime,
      };
    });
  }

  if (Array.isArray(mechanics.compositions) && mechanics.compositions.length) {
    compositionBlueprints = mechanics.compositions.map((composition) => ({
      form: composition.form,
      name: composition.name,
      meaning: composition.meaning,
    }));
  }

  if (Array.isArray(mechanics.tongue_lanes) && mechanics.tongue_lanes.length) {
    tongueBlueprints = mechanics.tongue_lanes.map((tongue) => ({
      name: tongue.tongue,
      lane: tongue.surface,
      phi: Number(tongue.phi),
    }));
  }

  if (mechanics.wafer && typeof mechanics.wafer === 'object') {
    const wafer = mechanics.wafer;
    waferBlueprint = {
      ...waferBlueprint,
      name: wafer.name || waferBlueprint.name,
      subtitle: wafer.subtitle || waferBlueprint.subtitle,
      opcodeCells: Number(wafer.opcode_cells) || waferBlueprint.opcodeCells,
      disk: wafer.disk || waferBlueprint.disk,
      sheet: wafer.sheet || waferBlueprint.sheet,
      trimCost: Number(wafer.reported_distance_error) || waferBlueprint.trimCost,
      realmDirection: wafer.realm_direction || waferBlueprint.realmDirection,
      control: wafer.control || waferBlueprint.control,
      provenance: wafer.provenance || waferBlueprint.provenance,
    };
  }

  renderCompositions();
  renderTongueLanes();
  buildOpcodeWafer();
  selectPrimitive(primitiveBlueprints[0].key);
  elements.waferName.textContent = waferBlueprint.name;
  elements.waferSubtitle.textContent = `${waferBlueprint.subtitle.charAt(0).toUpperCase()}${waferBlueprint.subtitle.slice(1)}.`;
  elements.waferEquation.textContent = waferBlueprint.sheet;
  elements.waferCellCount.textContent = String(waferBlueprint.opcodeCells);
  elements.waferTrimCost.textContent = waferBlueprint.trimCost.toExponential(3).replace('e-', 'e−');
  elements.waferNestId.textContent = waferBlueprint.control.id;
  elements.waferNestControl.textContent = `${waferBlueprint.control.label.replace(/nest\s*/i, '')} · ${waferBlueprint.control.direction}`;
  elements.waferProvenance.textContent = waferBlueprint.provenance;
  selectWaferView('disk');
}

async function hydrateMechanics() {
  try {
    const payload = await api('/api/mechanics');
    applyMechanicsModel(payload.mechanics || payload);
  } catch {
    // Older/offline servers keep the embedded owner-supplied reference map.
  }
}

async function bootstrap() {
  try {
    const payload = await api('/api/status');
    state.providers = payload.providers || [];
    state.sessions = payload.sessions || [];
    state.tools = payload.tools || [];
    state.commands = payload.commands || [];
    applyStatus(payload.status);
    renderTools();
    renderCommands();
    await hydrateMechanics();
  } catch (error) {
    elements.health.classList.remove('online');
    elements.modelLabel.textContent = 'server unavailable';
    appendMessage('error', `SCBE could not start: ${error.message}`, { className: 'error' });
  }
}

async function sendMessage(message) {
  const text = String(message || '').trim();
  if (!text || state.busy) return;
  appendMessage('user', text);
  if (elements.title.textContent === 'What are we making?')
    elements.title.textContent = text.slice(0, 64);
  elements.input.value = '';
  resizeInput();
  setBusy(true);
  const pending = appendMessage('assistant', 'Routing the next move…', { className: 'thinking' });
  try {
    const provider = elements.providerSelect.value || state.status?.provider;
    const model = elements.modelInput.value.trim() || state.status?.model;
    const payload = await api('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        session_id: state.sessionId,
        message: text,
        model: provider && model ? `${provider}/${model}` : undefined,
        permission_mode: elements.permission.value,
        approved_tools: elements.commandApproval.checked ? ['run_command'] : [],
      }),
    });
    pending.remove();
    appendMessage('assistant', payload.message || '(empty response)');
    elements.commandApproval.checked = false;
    ingestEvents(payload.events);
    applyStatus(payload.status);
    await refreshLists();
  } catch (error) {
    pending.remove();
    appendMessage('error', error.message, { className: 'error' });
  } finally {
    setBusy(false);
    elements.input.focus();
  }
}

async function refreshLists() {
  const payload = await api(`/api/status?session_id=${encodeURIComponent(state.sessionId)}`);
  state.sessions = payload.sessions || [];
  state.commands = payload.commands || [];
  renderSessions();
  renderCommands();
}

async function newSession() {
  try {
    const payload = await api('/api/session/new', {
      method: 'POST',
      body: JSON.stringify({ session_id: state.sessionId }),
    });
    clearMessages();
    applyStatus(payload.status);
    await refreshLists();
    elements.input.focus();
  } catch (error) {
    toast(error.message);
  }
}

async function resumeSession(sessionId) {
  if (state.busy || sessionId === state.sessionId) return;
  try {
    const payload = await api('/api/session/resume', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    });
    applyStatus(payload.status);
    renderSessionMessages(payload.messages || []);
    elements.title.textContent = payload.status.title || 'Conversation';
    await refreshLists();
  } catch (error) {
    toast(error.message);
  }
}

async function saveCommand() {
  const name = elements.commandName.value.trim();
  const template = elements.commandTemplate.value.trim();
  if (!name || !template) {
    elements.commandFeedback.textContent = 'Name and template are required.';
    return;
  }
  try {
    const payload = await api('/api/commands', {
      method: 'POST',
      body: JSON.stringify({
        action: 'new',
        name,
        scope: elements.commandScope.value,
        description: elements.commandDescription.value.trim(),
        template,
      }),
    });
    state.commands = payload.commands;
    renderCommands();
    elements.commandName.value = '';
    elements.commandDescription.value = '';
    elements.commandTemplate.value = '';
    elements.commandFeedback.textContent = `Saved /${name}.`;
  } catch (error) {
    elements.commandFeedback.textContent = error.message;
  }
}

async function removeCommand(command) {
  try {
    const payload = await api('/api/commands', {
      method: 'POST',
      body: JSON.stringify({ action: 'delete', name: command.name, scope: command.scope }),
    });
    state.commands = payload.commands;
    renderCommands();
  } catch (error) {
    toast(error.message);
  }
}

async function saveModel() {
  const provider = elements.providerSelect.value;
  const model = elements.modelInput.value.trim();
  if (!provider || !model) {
    elements.modelFeedback.textContent = 'Provider and model are required.';
    return;
  }
  try {
    await sendMessage(`/model ${provider}/${model}`);
    elements.modelDialog.close();
  } catch (error) {
    elements.modelFeedback.textContent = error.message;
  }
}

function resizeInput() {
  elements.input.style.height = 'auto';
  elements.input.style.height = `${Math.min(180, elements.input.scrollHeight)}px`;
}

elements.composer.addEventListener('submit', (event) => {
  event.preventDefault();
  sendMessage(elements.input.value);
});
elements.input.addEventListener('input', resizeInput);
elements.input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    elements.composer.requestSubmit();
  }
});
document.addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault();
    elements.input.focus();
  }
});
document.querySelectorAll('[data-prompt]').forEach((button) => {
  button.addEventListener('click', () => sendMessage(button.dataset.prompt));
});
elements.newSession.addEventListener('click', newSession);
elements.compact.addEventListener('click', () => sendMessage('/compact'));
elements.slashButton.addEventListener('click', () => {
  elements.input.value = '/help';
  elements.input.focus();
  resizeInput();
});
elements.commandsButton.addEventListener('click', () => elements.commandsDialog.showModal());
elements.modelButton.addEventListener('click', () => elements.modelDialog.showModal());
elements.mechanicsButton.addEventListener('click', () => elements.mechanicsDialog.showModal());
elements.mechanicsClose.addEventListener('click', () => elements.mechanicsDialog.close());
elements.mechanicsDialog.addEventListener('close', () => elements.mechanicsButton.focus());
elements.saveCommand.addEventListener('click', saveCommand);
elements.saveModel.addEventListener('click', saveModel);
elements.permission.addEventListener('change', () =>
  toast(`Permissions will use ${elements.permission.value} on the next message.`)
);
elements.providerSelect.addEventListener('change', () => {
  const provider = state.providers.find((item) => item.id === elements.providerSelect.value);
  if (provider) elements.modelInput.value = provider.defaultModel;
});

initializeMechanics();
bootstrap();
