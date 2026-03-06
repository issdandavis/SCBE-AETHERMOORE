const AGENTS = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
const AGENT_LABELS = {
  KO: 'Commander', AV: 'Navigator', RU: 'Policy',
  CA: 'Compute', UM: 'Shadow', DR: 'Schema',
};

export function renderAgentGrid(container) {
  container.setAttribute('role', 'status');
  container.setAttribute('aria-label', 'Agent squad status');
  container.innerHTML = AGENTS.map((id) => `
    <div class="ab-agent-badge" id="badge-${id}" title="${AGENT_LABELS[id]}">
      <span class="ab-agent-badge__dot"></span>
      <span class="ab-agent-badge__name">${id}</span>
      <span class="ab-agent-badge__model" id="model-${id}"></span>
    </div>
  `).join('');
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
