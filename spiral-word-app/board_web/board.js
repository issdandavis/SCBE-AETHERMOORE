'use strict';
const $ = (id) => document.getElementById(id);
const lanes = ['left', 'center', 'right'];
let board,
  sectionId,
  proposal,
  busy = false;
const dirty = new Set();
const displayedRevisions = {};
const tabId = sessionStorage.getItem('spiral-word-tab') || crypto.randomUUID();
sessionStorage.setItem('spiral-word-tab', tabId);
let recoveredDraftKey, recoveredDraftRaw, historyBoard, historyItems;
const draftPrefix = () => `spiral-word-draft:${board.id}:${sectionId}:`;
function stashDraft() {
  if (!board) return;
  try {
    const key = draftPrefix() + tabId;
    if (dirty.size) {
      localStorage.setItem(
        key,
        JSON.stringify({
          updated: Date.now(),
          lanes: Object.fromEntries(
            [...dirty].map((k) => [k, { values: fields(k), revision: displayedRevisions[k] }])
          ),
        })
      );
    } else {
      localStorage.removeItem(key);
      if (recoveredDraftKey && localStorage.getItem(recoveredDraftKey) === recoveredDraftRaw)
        localStorage.removeItem(recoveredDraftKey);
      recoveredDraftKey = recoveredDraftRaw = null;
    }
  } catch (_) {
    status('Browser draft recovery is unavailable. Save changes to keep this writing.', true);
  }
}
function restoreDraft() {
  recoveredDraftKey = recoveredDraftRaw = null;
  const candidates = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (!key.startsWith(draftPrefix())) continue;
    try {
      const raw = localStorage.getItem(key);
      candidates.push({ key, raw, value: JSON.parse(raw) });
    } catch (_) {}
  }
  candidates.sort((a, b) => b.value.updated - a.value.updated);
  const draft = candidates.find((d) => d.key === draftPrefix() + tabId) || candidates[0];
  if (!draft) return;
  recoveredDraftKey = draft.key;
  recoveredDraftRaw = draft.raw;
  for (const k of lanes) {
    const item = draft.value.lanes?.[k];
    if (!item || !Number.isInteger(item.revision)) continue;
    if (JSON.stringify(item.values) === JSON.stringify(fields(k))) continue;
    for (const key of ['text', 'speaker', 'format']) $(k + '-' + key).value = item.values[key];
    displayedRevisions[k] = item.revision;
    dirty.add(k);
    count(k);
  }
  if (dirty.size) status('Recovered an unsaved draft from this browser. Review it, then save.');
}
function filterSections() {
  if (!board) return;
  const query = $('section-search').value.toLocaleLowerCase().trim();
  for (const button of $('sections').children) {
    const s = board.sections.find((item) => item.id === button.dataset.section);
    button.hidden =
      !!query &&
      ![s.title, ...lanes.map((k) => s.lanes[k].text)]
        .join('\n')
        .toLocaleLowerCase()
        .includes(query);
  }
}
const section = () => board.sections.find((s) => s.id === sectionId);
const versions = () => Object.fromEntries(lanes.map((k) => [k, section().lanes[k].revision]));
const url = (suffix) => `/boards/${board.id}${suffix || ''}`;
function status(message, error = false) {
  $('status').textContent = message;
  $('status').style.color = error ? '#a43c36' : '';
}
async function api(path, method = 'GET', body) {
  const response = await fetch(path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const value = await response.json();
  if (!response.ok)
    throw new Error(
      typeof value.detail === 'string' ? value.detail : 'Please check the form fields.'
    );
  return value;
}
function count(k) {
  $(k + '-count').textContent = `${
    $(k + '-text')
      .value.trim()
      .split(/\s+/)
      .filter(Boolean).length
  } words`;
}
function fields(k) {
  return {
    speaker: $(k + '-speaker').value,
    format: $(k + '-format').value,
    text: $(k + '-text').value,
  };
}
function draw() {
  $('title').textContent = board.title;
  $('current-section').textContent =
    `${section().title} · Section ${board.sections.findIndex((s) => s.id === sectionId) + 1} of ${board.sections.length}`;
  $('sections').replaceChildren();
  for (const s of board.sections) {
    const button = document.createElement('button');
    button.textContent = s.title;
    button.dataset.section = s.id;
    button.className = s.id === sectionId ? 'active' : '';
    button.onclick = () =>
      perform(async () => {
        await save();
        sectionId = s.id;
        proposal = null;
        $('proposal-box').hidden = true;
        $('preview-box').hidden = true;
        draw();
        restoreDraft();
      }, true);
    $('sections').append(button);
  }
  for (const k of lanes) {
    if (!dirty.has(k)) {
      for (const key of ['speaker', 'format', 'text'])
        $(k + '-' + key).value = section().lanes[k][key];
      displayedRevisions[k] = section().lanes[k].revision;
    }
    count(k);
  }
  filterSections();
  const active = $('sections').querySelector('button.active');
  if (active && !active.hidden) {
    const frame = $('sections').getBoundingClientRect(),
      button = active.getBoundingClientRect();
    if (button.left < frame.left) $('sections').scrollLeft += button.left - frame.left;
    else if (button.right > frame.right) $('sections').scrollLeft += button.right - frame.right;
  }
  localStorage.setItem('spiral-word-section:' + board.id, sectionId);
}
async function save() {
  for (const k of [...dirty]) {
    const values = fields(k);
    board = await api(url(`/sections/${sectionId}/${k}`), 'PATCH', {
      // A different lane's response can contain unseen concurrent changes.
      // Compare against the revision the writer actually edited.
      expected_revision: displayedRevisions[k],
      ...values,
    });
    displayedRevisions[k] = section().lanes[k].revision;
    if (JSON.stringify(fields(k)) === JSON.stringify(values)) dirty.delete(k);
  }
  if (dirty.size)
    throw new Error('New changes arrived during saving. Save once more before continuing.');
  draw();
  stashDraft();
  status('All changes saved on this computer.');
}
async function perform(fn, navigating = false) {
  if (busy) return;
  busy = true;
  // Keep editing available; save() retains text typed while a request is in flight.
  document.querySelectorAll('button').forEach((b) => (b.disabled = true));
  if (navigating)
    document.querySelectorAll('input,select,textarea').forEach((el) => (el.disabled = true));
  try {
    await fn();
  } catch (error) {
    status(error.message + ' Your unsaved writing is still in the panels.', true);
  } finally {
    stashDraft();
    busy = false;
    document.querySelectorAll('button').forEach((b) => (b.disabled = false));
    if (navigating)
      document.querySelectorAll('input,select,textarea').forEach((el) => (el.disabled = false));
    if (board) $('documents').value = board.id;
    $('draft').disabled = !$('provider').value;
  }
}
async function catalog() {
  const items = await api('/boards');
  $('documents').replaceChildren();
  for (const item of items) {
    const option = document.createElement('option');
    option.value = item.id;
    option.textContent = item.title;
    $('documents').append(option);
  }
  if (board) $('documents').value = board.id;
  return items;
}
async function load(id) {
  board = await api('/boards/' + encodeURIComponent(id));
  const remembered = localStorage.getItem('spiral-word-section:' + board.id);
  sectionId = board.sections.some((s) => s.id === remembered) ? remembered : board.sections[0].id;
  dirty.clear();
  proposal = null;
  $('proposal-box').hidden = true;
  $('preview-box').hidden = true;
  draw();
  $('documents').value = board.id;
  localStorage.setItem('spiral-word-board', board.id);
  status('Ready. Your three panels are saved separately.');
  restoreDraft();
}
async function create(title, demo = false) {
  board = await api('/boards', 'POST', { title });
  sectionId = board.sections[0].id;
  dirty.clear();
  proposal = null;
  $('proposal-box').hidden = true;
  $('preview-box').hidden = true;
  draw();
  if (demo) {
    $('left-text').value = 'You came back.\nI kept the light burning.';
    $('right-text').value =
      'The river was higher than I remembered.\nBut I knew where to find you.';
    $('center-text').value =
      'Rain whispered against the pavilion roof. Mira stood beside a lantern, listening for footsteps.\n\n{{left:1}}\n\nRen stopped at the edge of the light.\n\n{{right:1}}\n\nFor a moment, neither of them moved.\n\n{{left:2}}\n\n{{right:2}}';
    lanes.forEach((k) => dirty.add(k));
    await save();
    draw();
  }
  await catalog();
  localStorage.setItem('spiral-word-board', board.id);
}
for (const k of lanes)
  for (const key of ['speaker', 'format', 'text'])
    $(k + '-' + key).addEventListener('input', () => {
      dirty.add(k);
      count(k);
      status('Unsaved changes · Ctrl / ⌘ + S to save.');
      stashDraft();
    });
for (const k of ['left', 'right'])
  $('insert-' + k).onclick = () => {
    const input = $('center-text');
    input.setRangeText(`{{${k}}}`, input.selectionStart, input.selectionEnd, 'end');
    input.dispatchEvent(new Event('input'));
    input.focus();
  };
$('save').onclick = () =>
  perform(async () => {
    await save();
    draw();
  });
$('preview-button').onclick = () =>
  perform(async () => {
    await save();
    const preview = await api(url('/preview'));
    $('preview').replaceChildren();
    for (const s of preview.sections) {
      const h = document.createElement('h3');
      h.textContent = s.title;
      const p = document.createElement('p');
      p.textContent = s.text;
      $('preview').append(h, p);
    }
    $('preview-box').hidden = false;
    $('preview-box').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
$('close-preview').onclick = () => {
  $('preview-box').hidden = true;
};
$('export').onclick = () =>
  perform(async () => {
    await save();
    await api(url('/preview'));
    location.href = url('/export.docx');
  });
$('new-section').onclick = () =>
  perform(async () => {
    await save();
    const title = prompt('Section title', 'Next scene');
    if (!title) return;
    board = await api(url('/sections'), 'POST', { title });
    sectionId = board.sections.at(-1).id;
    proposal = null;
    $('proposal-box').hidden = true;
    draw();
  }, true);
$('new-board').onclick = () =>
  perform(async () => {
    await save();
    const title = prompt('Document title', 'Untitled story');
    if (title) await create(title);
  }, true);
$('documents').onchange = () =>
  perform(async () => {
    const id = $('documents').value;
    await save();
    await load(id);
  }, true);
$('provider').onchange = () => {
  $('draft').disabled = busy || !$('provider').value;
};
$('section-search').oninput = filterSections;
async function changeOutline(kind) {
  await save();
  const sections = board.sections.map((s) => ({ id: s.id, title: s.title }));
  let title = board.title;
  const index = sections.findIndex((s) => s.id === sectionId);
  if (kind === 'document') {
    title = prompt('Document title', title);
    if (!title) return;
  } else if (kind === 'rename') {
    const value = prompt('Section title', sections[index].title);
    if (!value) return;
    sections[index].title = value;
  } else {
    const next = index + kind;
    if (next < 0 || next >= sections.length) return;
    [sections[index], sections[next]] = [sections[next], sections[index]];
  }
  board = await api(url('/outline'), 'PATCH', {
    expected_revision: board.revision,
    title,
    sections,
  });
  await catalog();
  draw();
  status('Outline saved. Panel contents are unchanged.');
}
for (const [id, kind] of [
  ['rename-section', 'rename'],
  ['rename-document', 'document'],
  ['earlier-section', -1],
  ['later-section', 1],
])
  $(id).onclick = () => perform(() => changeOutline(kind), true);
async function readHistory() {
  historyBoard = await api(url());
  const k = $('history-lane').value;
  const current = historyBoard.sections.find((s) => s.id === sectionId).lanes[k];
  historyItems = await api(url(`/sections/${sectionId}/${k}/history`));
  if (!historyItems.length) historyItems = [current];
  $('history-revision').replaceChildren();
  for (const item of historyItems) {
    const option = document.createElement('option');
    option.value = item.revision;
    option.textContent = `Revision ${item.revision}${item.revision === current.revision ? ' · latest saved' : ''}`;
    $('history-revision').append(option);
  }
  $('history-text').value = historyItems[0].text;
  $('history-note').textContent =
    'Review the saved writing below. Choosing a version changes your draft; Save commits it as a new revision.';
}
$('history-button').onclick = () =>
  perform(async () => {
    await readHistory();
    $('history-dialog').showModal();
  });
$('history-lane').onchange = () => perform(readHistory);
$('history-revision').onchange = () => {
  $('history-text').value = historyItems.find(
    (i) => i.revision === Number($('history-revision').value)
  ).text;
};
function chooseRevision(keepLocal) {
  const k = $('history-lane').value;
  if (
    keepLocal &&
    !confirm(
      'Use your current panel draft in place of the latest saved version when you next save?'
    )
  )
    return;
  if (
    !keepLocal &&
    dirty.has(k) &&
    !confirm('Replace this panel’s unsaved draft with the selected version?')
  )
    return;
  board = historyBoard;
  displayedRevisions[k] = section().lanes[k].revision;
  if (!keepLocal) {
    const item = historyItems.find((i) => i.revision === Number($('history-revision').value));
    for (const key of ['text', 'speaker', 'format']) $(k + '-' + key).value = item[key];
  }
  dirty.add(k);
  draw();
  stashDraft();
  $('history-dialog').close();
  status('Revision loaded as a draft. Save when you are ready.');
}
$('use-revision').onclick = () => chooseRevision(false);
$('keep-local').onclick = () => chooseRevision(true);
$('close-history').onclick = () => $('history-dialog').close();
$('draft').onclick = () =>
  perform(async () => {
    await save();
    status('Drafting a suggestion. Your saved scene stays in place.');
    proposal = await api(url(`/sections/${sectionId}/draft`), 'POST', {
      provider: $('provider').value,
      instruction: $('instruction').value || 'Write a cohesive scene while preserving both voices.',
      expected_context: versions(),
    });
    proposal.sectionId = sectionId;
    $('proposal').textContent = proposal.text;
    $('proposal-box').hidden = false;
    $('apply').textContent = proposal.diagnostic ? 'Diagnostic only' : 'Use in center panel';
    status(
      proposal.diagnostic
        ? 'Echo test returned its input; this is not a written scene.'
        : 'Suggestion ready. Review it before applying.'
    );
  });
$('apply').onclick = () =>
  perform(async () => {
    if (!proposal || proposal.diagnostic)
      throw new Error('Choose a writing provider to create a real proposal.');
    if (dirty.size || proposal.sectionId !== sectionId)
      throw new Error('A panel changed. Save it and request a fresh suggestion.');
    board = await api(url(`/sections/${sectionId}/center`), 'PATCH', {
      ...fields('center'),
      text: proposal.text,
      expected_revision: proposal.expected_context.center,
      expected_context: proposal.expected_context,
    });
    proposal = null;
    $('proposal-box').hidden = true;
    draw();
    status('Scene updated. Both source voices are preserved.');
  }, true);
$('discard').onclick = () => {
  proposal = null;
  $('proposal-box').hidden = true;
};
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault();
    perform(async () => {
      await save();
      draw();
    });
  }
});
window.addEventListener('beforeunload', (e) => {
  if (dirty.size) {
    e.preventDefault();
    e.returnValue = '';
  }
});
perform(async () => {
  const items = await catalog();
  const last = localStorage.getItem('spiral-word-board');
  if (items.length) await load(items.some((i) => i.id === last) ? last : items[0].id);
  else await create('Under the pavilion roof', true);
  const providers = await api('/ai/providers');
  for (const name of providers.providers) {
    const option = document.createElement('option');
    option.value = name;
    option.textContent = name === 'echo' ? 'Echo · connection test only' : name;
    $('provider').append(option);
  }
});
