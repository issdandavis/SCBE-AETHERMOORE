// AetherDesktop popup — the governed control surface.
// Flow for every action: PROPOSE to the local bridge -> it screens (never-delete/L13/confirm) + seals ->
// only on ALLOWED do we tell the content script to actually do it in the Colab tab. The gate is always
// in front of the hands; nothing here can bypass it.

const BRIDGE = 'http://127.0.0.1:8777';
const out = document.getElementById('out');
const tokenInput = document.getElementById('token');

chrome.storage.local.get('token', (d) => { if (d.token) tokenInput.value = d.token; });
document.getElementById('save').onclick = () =>
  chrome.storage.local.set({ token: tokenInput.value }, () => show('token saved', 'hint'));

function show(text, cls) {
  out.textContent = text;
  out.className = cls || '';
}

async function govern(action, params, confirm) {
  const token = tokenInput.value.trim();
  if (!token) { show('paste the bridge X-Aether-Token first', 'refused'); return null; }
  const r = await fetch(BRIDGE + '/govern', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Aether-Token': token },
    body: JSON.stringify({ action, params, confirm }),
  });
  return r.json();
}

async function activeColabTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !/colab\.research\.google\.com/.test(tab.url || '')) throw new Error('open a Colab tab first');
  return tab;
}

async function propose(action, params) {
  let rec = await govern(action, params, null);
  if (!rec) return;
  if (rec.decision === 'NEEDS_CONFIRM') {
    const reason = prompt('This action is guarded. Reason to approve?');
    if (!reason) { show('cancelled (no confirm)', 'confirm'); return; }
    rec = await govern(action, params, reason);
  }
  if (!rec || rec.decision !== 'ALLOWED') {
    show('verdict: ' + (rec ? rec.decision : 'error') + '\n' + (rec && rec.next ? rec.next : ''),
         rec && rec.decision === 'REFUSED' ? 'refused' : 'confirm');
    return;
  }
  // ALLOWED + sealed -> now (and only now) run it in the page
  try {
    const tab = await activeColabTab();
    const res = await chrome.tabs.sendMessage(tab.id, { action, params });
    show('ALLOWED (sealed ' + (rec.seal || '').slice(0, 10) + ')\n\n' + (res ? res.result : '(no response)'), 'allowed');
  } catch (e) {
    show('ALLOWED but execution failed: ' + e.message, 'refused');
  }
}

for (const btn of document.querySelectorAll('.actions button')) {
  btn.onclick = () => {
    const params = btn.dataset.cell !== undefined ? { cell_index: Number(btn.dataset.cell) } : {};
    propose(btn.dataset.action, params);
  };
}
