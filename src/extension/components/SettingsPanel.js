import { loadSettings, saveSettings } from '../lib/storage.js';

const MODELS = ['opus', 'sonnet', 'haiku', 'flash', 'grok', 'local'];
const ROLES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
const ROLE_LABELS = {
  KO: 'Commander', AV: 'Navigator', RU: 'Policy',
  CA: 'Compute', UM: 'Shadow', DR: 'Schema',
};

export async function renderSettingsPanel(container, onClose) {
  const settings = await loadSettings();

  container.classList.remove('hidden');
  container.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2 style="font-size:16px;font-weight:600">Settings</h2>
      <button id="settings-close" class="ab-btn ab-btn--secondary">Close</button>
    </div>

    <section style="margin-bottom:16px">
      <h3 style="font-size:13px;font-weight:600;margin-bottom:8px">Model Routing</h3>
      ${ROLES.map((role) => `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
          <label style="width:80px;font-size:12px">${role} ${ROLE_LABELS[role]}</label>
          <select id="pref-${role}" style="flex:1;background:var(--bg-card);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:3px 6px;font-size:12px">
            ${MODELS.map((m) => `<option value="${m}" ${settings.preferences[role] === m ? 'selected' : ''}>${m}</option>`).join('')}
          </select>
        </div>
      `).join('')}
      <label style="display:flex;align-items:center;gap:6px;margin-top:8px;font-size:12px">
        <input type="checkbox" id="auto-cascade" ${settings.autoCascade ? 'checked' : ''}>
        Auto-cascade on rate limit
      </label>
    </section>

    <section style="margin-bottom:16px">
      <h3 style="font-size:13px;font-weight:600;margin-bottom:8px">Backend Connection</h3>
      <div style="display:flex;align-items:center;gap:8px">
        <label style="width:80px;font-size:12px">Port</label>
        <input id="setting-port" type="number" value="${settings.port}" min="1024" max="65535"
          style="width:80px;background:var(--bg-card);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:3px 6px;font-size:12px">
      </div>
    </section>

    <button id="settings-save" class="ab-btn ab-btn--primary" style="width:100%">Save</button>
  `;

  container.querySelector('#settings-close').addEventListener('click', () => {
    container.classList.add('hidden');
    onClose();
  });

  container.querySelector('#settings-save').addEventListener('click', async () => {
    const newSettings = { ...settings };
    ROLES.forEach((role) => {
      newSettings.preferences[role] = container.querySelector(`#pref-${role}`).value;
    });
    newSettings.autoCascade = container.querySelector('#auto-cascade').checked;
    newSettings.port = parseInt(container.querySelector('#setting-port').value, 10) || 8002;
    await saveSettings(newSettings);
    container.classList.add('hidden');
    onClose();
  });
}
