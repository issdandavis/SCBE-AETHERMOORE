'use strict';
// Older stock Android WebViews still run the offline editor.
if (!Element.prototype.replaceChildren)
  Element.prototype.replaceChildren = function (...nodes) {
    while (this.firstChild) this.removeChild(this.firstChild);
    for (const node of nodes) this.appendChild(node);
  };
const $ = (id) => document.getElementById(id),
  M = SpiralMLA;
let profile,
  documentState,
  plugin = null;
const keys = {
  draft: 'spiralword.mla.draft.v1',
  templates: 'spiralword.mla.templates.v1',
  plugin: 'spiralword.mla.plugin.v1',
};
const announce = (text) => {
  $('status').textContent = text;
};
function read(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) || fallback;
  } catch {
    return fallback;
  }
}
function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    announce('Device storage is unavailable. Export a project to keep your writing.');
    return false;
  }
}
function collect() {
  const d = {};
  for (const k of M.fields) d[k] = $(k).value;
  return M.clean(d);
}
function paintText(parent, lines) {
  parent.replaceChildren();
  for (const line of lines) {
    const p = document.createElement('p');
    p.textContent = line;
    parent.append(p);
  }
}
function check() {
  const checks = M.validate(documentState);
  if (plugin)
    checks.push(
      ...M.pluginRules(plugin, documentState).map((c) => ({
        ...c,
        label: plugin.name + ': ' + c.label,
      }))
    );
  $('checks').replaceChildren();
  for (const c of checks) {
    const li = document.createElement('li'),
      button = document.createElement('button');
    li.className = c.ok ? 'pass' : 'todo';
    button.textContent = (c.ok ? '✓ ' : '○ ') + c.label;
    button.onclick = () => focusField(c.id);
    li.append(button);
    $('checks').append(li);
  }
  return checks;
}
function render() {
  const d = documentState;
  $('preview-running').textContent = `${d.lastName.trim() || 'LastName'} 1`;
  paintText($('preview-heading'), [
    `${d.firstName} ${d.lastName}`.trim() || 'Your name',
    d.instructor || 'Instructor',
    d.course || 'Course',
    M.dateText(d.date) || 'Day Month Year',
  ]);
  $('preview-title').textContent = d.title || 'Your Title';
  paintText(
    $('preview-body'),
    d.body.split('\n').filter((s) => s.trim()).length
      ? d.body.split('\n').filter((s) => s.trim())
      : ['Your paragraph starts here. The first line will indent automatically in Word.']
  );
  $('works-paper').hidden = !d.works.trim();
  paintText(
    $('preview-works'),
    d.works.split('\n').filter((s) => s.trim())
  );
  $('works-running').textContent = `${d.lastName.trim() || 'LastName'} · next page`;
  $('words').textContent = `${d.body.trim() ? d.body.trim().split(/\s+/u).length : 0} words`;
  $('plugin-label').textContent = plugin
    ? `Assignment rules: ${plugin.name}`
    : 'No additional assignment rules.';
  check();
}
function apply(d) {
  documentState = M.clean(d);
  for (const k of M.fields) $(k).value = documentState[k];
  render();
}
function view(preview) {
  document.body.classList.toggle('view-preview', preview);
  $('edit-tab').setAttribute('aria-pressed', String(!preview));
  $('preview-tab').setAttribute('aria-pressed', String(preview));
}
function focusField(id) {
  view(false);
  $(id).focus();
  $(id).scrollIntoView({ block: 'center', behavior: 'smooth' });
}
function highlight(id) {
  document
    .querySelectorAll('[data-zone]')
    .forEach((el) =>
      el.classList.toggle(
        'active',
        el.dataset.zone === id ||
          (el.dataset.zone === 'heading' &&
            ['firstName', 'instructor', 'course', 'date'].includes(id))
      )
    );
}
function download(name, bytes, mime) {
  if (window.AndroidFiles) {
    let s = '';
    for (let i = 0; i < bytes.length; i += 8192)
      s += String.fromCharCode(...bytes.subarray(i, i + 8192));
    AndroidFiles.save(name, mime, btoa(s));
    announce('Choose where to save your file.');
    return;
  }
  const url = URL.createObjectURL(new Blob([bytes], { type: mime })),
    a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 15000);
  announce('Download started: ' + name);
}
function exportWord() {
  try {
    documentState = collect();
    const missing = check().filter((c) => !c.ok);
    if (missing.length) {
      announce('Complete the highlighted checks before exporting.');
      view(true);
      $('checklist').scrollIntoView({ block: 'start' });
      return;
    }
    download(
      M.filename(documentState, $('filename-mode').value === 'template'),
      M.docx(documentState),
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    );
  } catch (e) {
    announce(e.message);
  }
}
function project() {
  return { schema: 'spiralword.mla.project.v1', profile: profile.id, document: documentState };
}
function exportProject() {
  download(
    'Spiral Word project.json',
    new TextEncoder().encode(JSON.stringify(project(), null, 2)),
    'application/json'
  );
}
async function importFile(input, handler) {
  const file = input.files[0];
  if (!file) return;
  try {
    if (file.size > 1500000) throw Error('Choose a file smaller than 1.5 MB.');
    const text = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsText(file);
    });
    handler(JSON.parse(text));
  } catch (e) {
    announce('Could not import: ' + e.message);
  }
  input.value = '';
}
function preserve() {
  return write(keys.draft + '.previous', documentState);
}
async function init() {
  profile = await (await fetch('profile.json')).json();
  documentState = M.clean(read(keys.draft, profile.defaults));
  if (window.AndroidFiles) {
    const card = document.createElement('details');
    card.className = 'card';
    card.innerHTML =
      '<summary>Connect a companion API</summary><p>Optional. Use your own HTTPS server, or a local connection through USB forwarding. Writing works without it.</p><label>API base URL<input id="api-url" type="url" placeholder="https://your-server/mla/api"></label><label>Access token (this session only)<input id="api-token" type="password" autocomplete="off"></label><div class="buttons"><button id="native-connect">Check connection</button><button id="native-validate">Send draft for format check</button></div><small>Sending a draft shares its contents with the server you choose. Never put a token in the URL.</small>';
    $('builder').append(card);
    $('api-url').value = read('spiralword.mla.api-url', '');
    for (const [id, operation] of [
      ['native-connect', 'profile'],
      ['native-validate', 'validate'],
    ])
      $(id).onclick = () => {
        const base = $('api-url').value.trim();
        if (!base) {
          announce('Enter the companion API URL.');
          return;
        }
        write('spiralword.mla.api-url', base);
        announce('Contacting your companion API…');
        AndroidFiles.api(
          base,
          $('api-token').value,
          operation,
          operation === 'validate' ? JSON.stringify(documentState) : ''
        );
      };
  }
  try {
    const saved = read(keys.plugin, null);
    if (saved) {
      M.pluginRules(saved, documentState);
      plugin = saved;
    }
  } catch {
    plugin = null;
  }
  apply(documentState);
  for (const k of M.fields) {
    $(k).addEventListener('input', () => {
      documentState = collect();
      if (write(keys.draft, documentState)) announce('Draft saved on this device.');
      render();
    });
    $(k).addEventListener('focus', () => highlight(k));
  }
  document
    .querySelectorAll('[data-zone]')
    .forEach((el) =>
      el.addEventListener('click', () =>
        focusField(el.dataset.zone === 'heading' ? 'firstName' : el.dataset.zone)
      )
    );
  $('edit-tab').onclick = () => view(false);
  $('preview-tab').onclick = () => view(true);
  $('check-tab').onclick = () => {
    view(true);
    $('checklist').focus();
    $('checklist').scrollIntoView({ block: 'start' });
  };
  $('show-guides').onchange = () => {
    $('paper').classList.toggle('guides', $('show-guides').checked);
  };
  $('export').onclick = exportWord;
  $('export-project').onclick = exportProject;
  $('save-template').onclick = () => {
    const name = $('template-name').value.trim();
    if (!name) {
      announce('Give your reusable template a label first.');
      $('template-name').focus();
      return;
    }
    const templates = read(keys.templates, []);
    templates.push({
      name,
      created: new Date().toISOString(),
      document: { ...documentState, title: '', body: '', works: '' },
    });
    if (write(keys.templates, templates))
      announce(
        'Template saved with your heading and MLA layout. Your current writing is still here.'
      );
  };
  $('load-template').onclick = () => {
    const templates = read(keys.templates, []);
    if (!templates.length) {
      announce('Save a template first.');
      return;
    }
    const choice = prompt(
      'Choose a template number:\n' + templates.map((t, i) => `${i + 1}. ${t.name}`).join('\n')
    );
    if (choice === null) return;
    const selected = templates[Number(choice) - 1];
    if (!selected) {
      announce('Choose a listed number.');
      return;
    }
    if (!preserve()) return;
    apply(selected.document);
    write(keys.draft, documentState);
    announce('Template opened. Previous draft is kept as a recovery copy.');
  };
  $('new-draft').onclick = () => {
    if (
      !confirm(
        'Start fresh writing? Your heading stays, and the current draft will be kept as a recovery copy.'
      )
    )
      return;
    if (!preserve()) return;
    apply({ ...documentState, title: '', body: '', works: '' });
    write(keys.draft, documentState);
    announce('Fresh draft ready.');
  };
  const recovery = document.createElement('button');
  recovery.id = 'restore-draft';
  recovery.textContent = 'Recover previous draft';
  $('new-draft').parentElement.append(recovery);
  recovery.onclick = () => {
    const previous = read(keys.draft + '.previous', null);
    if (!previous) {
      announce('No previous draft has been stored yet.');
      return;
    }
    const current = documentState;
    apply(previous);
    write(keys.draft + '.previous', current);
    write(keys.draft, documentState);
    announce('Previous draft recovered.');
  };
  $('import-project').onchange = () =>
    importFile($('import-project'), (obj) => {
      if (obj.schema !== 'spiralword.mla.project.v1' || obj.profile !== profile.id || !obj.document)
        throw Error('This is not a compatible MLA project.');
      const d = M.clean(obj.document);
      if (!preserve()) return;
      apply(d);
      write(keys.draft, d);
      announce('Project opened; previous draft saved for recovery.');
    });
  $('import-plugin').onchange = () =>
    importFile($('import-plugin'), (obj) => {
      M.pluginRules(obj, documentState);
      plugin = obj;
      write(keys.plugin, obj);
      render();
      announce('Assignment rules added.');
    });
  $('remove-plugin').onclick = () => {
    plugin = null;
    write(keys.plugin, null);
    render();
    announce('Additional assignment rules removed.');
  };
  $('api-check').onclick = async () => {
    try {
      const r = await fetch('api/profile');
      if (!r.ok) throw Error();
      const p = await r.json();
      if (p.id !== profile.id) throw Error();
      announce('Local Spiral Word API is available.');
    } catch {
      announce('Offline mode: the local API is not connected. Writing and Word export still work.');
    }
  };
  window.SpiralWord = Object.freeze({
    version: 1,
    getDocument: () => JSON.parse(JSON.stringify(documentState)),
    setDocument: (d) => {
      preserve();
      apply(d);
      write(keys.draft, documentState);
    },
    validate: () => check(),
    exportDocx: () => M.docx(documentState),
    restorePrevious: () => {
      const d = read(keys.draft + '.previous', null);
      if (d) {
        apply(d);
        write(keys.draft, documentState);
      }
    },
    getProject: project,
  });
}
window.onNativeSave = (ok, message) =>
  announce(message || (ok ? 'File saved.' : 'File was not saved.'));
window.onNativeApi = (ok, payload) => {
  if (!ok) {
    announce(payload);
    return;
  }
  try {
    const result = JSON.parse(payload);
    if (Array.isArray(result.checks))
      announce(
        `Server checked ${result.checks.length} items; ${result.checks.filter((c) => !c.ok).length} need attention.`
      );
    else if (result.id === profile.id) announce('Connected to the matching MLA profile.');
    else announce('Server responded with a different profile; check its configuration.');
  } catch {
    announce('The API returned an unreadable response.');
  }
};
init().catch((e) => announce('Could not open the writing desk: ' + e.message));
