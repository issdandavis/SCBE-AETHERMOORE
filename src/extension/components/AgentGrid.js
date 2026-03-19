const AGENTS = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
const PROVIDERS = ['local', 'flash', 'haiku', 'sonnet', 'opus', 'grok'];
const AGENT_LABELS = {
  KO: 'Commander', AV: 'Navigator', RU: 'Policy',
  CA: 'Compute', UM: 'Shadow', DR: 'Schema',
};
const PROVIDER_LABELS = {
  local: 'Local',
  flash: 'Flash',
  haiku: 'Haiku',
  sonnet: 'Sonnet',
  opus: 'Opus',
  grok: 'Grok',
};

export function renderAgentGrid(container) {
  container.setAttribute('role', 'status');
  container.setAttribute('aria-label', 'Agent squad status');
  container.innerHTML = `
    <div class="ab-agent-grid__row" id="agent-grid-row">
      ${AGENTS.map((id) => `
        <div class="ab-agent-badge" id="badge-${id}" title="${AGENT_LABELS[id]}">
          <span class="ab-agent-badge__dot"></span>
          <span class="ab-agent-badge__name">${id}</span>
          <span class="ab-agent-badge__model" id="model-${id}"></span>
        </div>
      `).join('')}
    </div>
    <div class="ab-provider-strip" id="provider-strip" aria-live="polite"></div>
  `;
}

export function updateAgentBadge(agentId, state, model) {
  const badge = document.getElementById(`badge-${agentId}`);
  if (!badge) return;
  badge.classList.remove('ab-agent-badge--working', 'ab-agent-badge--done', 'ab-agent-badge--waiting', 'ab-agent-badge--error');
  if (state !== 'idle') {
    badge.classList.add(`ab-agent-badge--${state}`);
  }
  const modelEl = document.getElementById(`model-${agentId}`);
  if (modelEl && model) {
    modelEl.textContent = model;
  }
}

export function resetAllBadges() {
  AGENTS.forEach((id) => updateAgentBadge(id, 'idle'));
}

export function renderProviderHealth(snapshot = {}) {
  const strip = document.getElementById('provider-strip');
  if (!strip) return;
  const keys = PROVIDERS.filter((provider) => snapshot[provider]);
  if (!keys.length) {
    strip.innerHTML = `
      <div class="ab-provider-strip__label">Runtime</div>
      <div class="ab-provider-pill ab-provider-pill--unknown">Awaiting backend health</div>
    `;
    return;
  }

  strip.innerHTML = `
    <div class="ab-provider-strip__label">Runtime</div>
    ${keys.map((provider) => renderProviderPill(provider, snapshot[provider])).join('')}
  `;
}

export function clearProviderHealth() {
  const strip = document.getElementById('provider-strip');
  if (!strip) return;
  strip.innerHTML = `
    <div class="ab-provider-strip__label">Runtime</div>
    <div class="ab-provider-pill ab-provider-pill--unknown">Disconnected</div>
  `;
}

function renderProviderPill(provider, meta) {
  const ready = meta?.available === true;
  const reason = meta?.reason || 'unknown';
  const modelId = meta?.model_id || '';
  const statusClass = ready ? 'ready' : 'blocked';
  const statusText = ready ? 'ready' : abbreviateReason(reason);
  const title = [
    `${PROVIDER_LABELS[provider] || provider}: ${reason}`,
    modelId ? `model=${modelId}` : '',
    Array.isArray(meta?.packages) && meta.packages.length ? `packages=${meta.packages.join(',')}` : '',
  ].filter(Boolean).join(' | ');
  return `
    <div class="ab-provider-pill ab-provider-pill--${statusClass}" title="${escapeHtml(title)}">
      <span class="ab-provider-pill__name">${escapeHtml(PROVIDER_LABELS[provider] || provider)}</span>
      <span class="ab-provider-pill__status">${escapeHtml(statusText)}</span>
    </div>
  `;
}

function abbreviateReason(reason) {
  if (!reason) return 'blocked';
  if (reason === 'ready') return 'ready';
  if (reason === 'local_runtime') return 'local';
  if (reason.startsWith('missing_env:')) return 'env';
  if (reason.startsWith('missing_package:')) return 'pkg';
  return reason.replace(/^missing_/, '');
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
