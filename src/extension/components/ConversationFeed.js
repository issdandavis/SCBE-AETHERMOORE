const AGENT_NAMES = {
  KO: 'KO Commander', AV: 'AV Navigator', RU: 'RU Policy',
  CA: 'CA Compute', UM: 'UM Shadow', DR: 'DR Schema',
  user: 'You', system: 'System',
};

export function initConversationFeed(container) {
  container.innerHTML = '';
}

export function appendMessage(container, msg) {
  const agent = msg.agent || 'system';
  const model = msg.model || '';
  const payload = msg.payload || {};
  const text = getPrimaryText(payload);
  const plan = payload.plan && typeof payload.plan === 'object' ? payload.plan : null;
  const pageAnalysis = payload.page_analysis && typeof payload.page_analysis === 'object'
    ? payload.page_analysis
    : null;

  const el = document.createElement('div');
  el.className = `ab-message ab-message--${agent}`;
  el.innerHTML = `
    <div class="ab-message__header">
      <span class="ab-message__agent">${AGENT_NAMES[agent] || agent}</span>
      ${model ? `<span class="ab-message__model">${model}</span>` : ''}
    </div>
    ${text ? `<div class="ab-message__text">${escapeHtml(text)}</div>` : ''}
    ${plan ? renderPlanSection(plan) : ''}
    ${pageAnalysis ? renderPageAnalysisSection(pageAnalysis) : ''}
  `;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
}

export function appendUserMessage(container, text) {
  appendMessage(container, { agent: 'user', payload: { text } });
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function getPrimaryText(payload) {
  if (typeof payload.text === 'string' && payload.text.trim()) {
    return payload.text;
  }
  if (typeof payload.state === 'string' && payload.state.trim()) {
    return payload.state;
  }
  if (payload.plan || payload.page_analysis) {
    return '';
  }
  return JSON.stringify(payload);
}

function renderPlanSection(plan) {
  const badges = [
    createBadge('Intent', plan.intent || plan.task_type),
    createRiskBadge(plan.risk_tier || plan.zone),
    createBadge('Provider', plan.provider),
    boolBadge(plan.browser_action_required, 'Browser Action'),
    boolBadge(plan.escalation_ready, 'Escalation Ready'),
  ].filter(Boolean);
  const approvals = normalizeStringList(plan.required_approvals);
  const nextActions = normalizeActionList(plan.next_actions);
  const assignments = normalizeAssignmentList(plan.assignments);

  return `
    <section class="ab-structured ab-structured--plan">
      <div class="ab-structured__title">Command Plan</div>
      ${badges.length ? `<div class="ab-pill-row">${badges.join('')}</div>` : ''}
      ${renderKeyValueGrid([
        ['Selection', plan.selection_reason],
        ['Fallback', joinList(plan.fallback_chain)],
      ])}
      ${renderListSection('Next Actions', nextActions, { ordered: true })}
      ${renderListSection('Required Approvals', approvals)}
      ${renderListSection('Assignments', assignments)}
    </section>
  `;
}

function renderPageAnalysisSection(pageAnalysis) {
  const topologyLens = pageAnalysis.topology_lens && typeof pageAnalysis.topology_lens === 'object'
    ? pageAnalysis.topology_lens
    : null;
  const badges = [
    createBadge('Intent', pageAnalysis.intent || pageAnalysis.page_type),
    createRiskBadge(pageAnalysis.risk_tier),
    createBadge('Topics', countValue(pageAnalysis.topics)),
  ].filter(Boolean);
  const nextActions = normalizeActionList(pageAnalysis.next_actions);
  const approvals = normalizeStringList(pageAnalysis.required_approvals);
  const topics = normalizeStringList(pageAnalysis.topics);
  const metrics = [
    ['Words', pageAnalysis.word_count],
    ['Headings', pageAnalysis.heading_count],
    ['Links', pageAnalysis.link_count],
    ['Forms', pageAnalysis.form_count],
    ['Buttons', pageAnalysis.button_count],
    ['Tabs', pageAnalysis.tab_count],
  ].filter(([, value]) => Number.isFinite(value));

  return `
    <section class="ab-structured ab-structured--analysis">
      <div class="ab-structured__title">Page Analysis</div>
      ${pageAnalysis.page_summary || pageAnalysis.summary ? `
        <div class="ab-structured__summary">
          ${escapeHtml(pageAnalysis.page_summary || pageAnalysis.summary)}
        </div>
      ` : ''}
      ${badges.length ? `<div class="ab-pill-row">${badges.join('')}</div>` : ''}
      ${metrics.length ? renderMetricGrid(metrics) : ''}
      ${topologyLens ? renderTopologySection(topologyLens) : ''}
      ${topics.length ? renderListSection('Topics', topics) : ''}
      ${renderListSection('Next Actions', nextActions, { ordered: true })}
      ${renderListSection('Required Approvals', approvals)}
    </section>
  `;
}

function renderKeyValueGrid(rows) {
  const safeRows = rows.filter(([, value]) => value);
  if (!safeRows.length) {
    return '';
  }
  return `
    <div class="ab-key-grid">
      ${safeRows.map(([label, value]) => `
        <div class="ab-key-grid__item">
          <div class="ab-key-grid__label">${escapeHtml(label)}</div>
          <div class="ab-key-grid__value">${escapeHtml(String(value))}</div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderMetricGrid(metrics) {
  return `
    <div class="ab-metric-grid">
      ${metrics.map(([label, value]) => `
        <div class="ab-metric">
          <div class="ab-metric__value">${escapeHtml(String(value))}</div>
          <div class="ab-metric__label">${escapeHtml(label)}</div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderTopologySection(topologyLens) {
  const compass = Array.isArray(topologyLens.semantic_compass) ? topologyLens.semantic_compass : [];
  const signals = normalizeStringList(topologyLens.boundary_signals);
  const metrics = [
    ['Zone', topologyLens.zone],
    ['d_H', topologyLens.trust_distance],
    ['Radius', topologyLens.radius],
    ['Curvature', topologyLens.curvature],
    ['Link Pressure', topologyLens.link_pressure],
    ['Interaction', topologyLens.interaction_pressure],
    ['Growth', topologyLens.growth_signal],
  ].filter(([, value]) => value !== undefined && value !== null && value !== '');
  const badges = [
    createBadge('Primary Axis', topologyLens.primary_axis),
    createBadge('Growth Line', topologyLens.growth_label),
    topologyLens.zone ? createRiskBadge(topologyLens.zone) : '',
  ].filter(Boolean);

  return `
    <div class="ab-structured__section">
      <div class="ab-structured__section-title">Topology Lens</div>
      ${topologyLens.summary ? `<div class="ab-structured__summary">${escapeHtml(topologyLens.summary)}</div>` : ''}
      ${badges.length ? `<div class="ab-pill-row">${badges.join('')}</div>` : ''}
      ${metrics.length ? renderKeyValueGrid(metrics) : ''}
      ${compass.length ? `
        <div class="ab-topology-compass">
          ${compass.map((axis) => renderCompassAxis(axis)).join('')}
        </div>
      ` : ''}
      ${renderListSection('Boundary Signals', signals)}
    </div>
  `;
}

function renderCompassAxis(axis) {
  const axisName = typeof axis?.axis === 'string' ? axis.axis : 'Unknown';
  const score = Math.max(0, Math.min(1, Number(axis?.score || 0)));
  const hits = Number.isFinite(axis?.hits) ? axis.hits : 0;
  return `
    <div class="ab-topology-axis">
      <div class="ab-topology-axis__header">
        <span class="ab-topology-axis__name">${escapeHtml(axisName)}</span>
        <span class="ab-topology-axis__meta">${escapeHtml(`${Math.round(score * 100)}%`)}${hits ? ` | ${escapeHtml(String(hits))} hit${hits === 1 ? '' : 's'}` : ''}</span>
      </div>
      <div class="ab-topology-axis__bar">
        <div class="ab-topology-axis__fill" style="width:${score * 100}%"></div>
      </div>
    </div>
  `;
}

// Items are pre-escaped HTML strings (may contain safe markup like <strong>).
// All normalize*List() functions must escapeHtml() user-facing text before returning.
function renderListSection(title, items, opts = {}) {
  if (!items.length) {
    return '';
  }
  const tag = opts.ordered ? 'ol' : 'ul';
  return `
    <div class="ab-structured__section">
      <div class="ab-structured__section-title">${escapeHtml(title)}</div>
      <${tag} class="ab-structured__list">
        ${items.map((item) => `<li>${item}</li>`).join('')}
      </${tag}>
    </div>
  `;
}

function normalizeStringList(value) {
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (typeof item === 'string') {
          return escapeHtml(item);
        }
        if (item && typeof item === 'object') {
          const label = item.label || item.reason || item.name;
          return label ? escapeHtml(String(label)) : '';
        }
        return '';
      })
      .filter(Boolean);
  }
  if (typeof value === 'string' && value.trim()) {
    return [escapeHtml(value)];
  }
  if (typeof value === 'number' && value > 0) {
    return [escapeHtml(String(value))];
  }
  return [];
}

function normalizeActionList(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item, index) => {
      if (typeof item === 'string') {
        return escapeHtml(item);
      }
      if (!item || typeof item !== 'object') {
        return '';
      }
      const label = item.label || item.title || item.action || item.task || `Step ${index + 1}`;
      const reason = item.reason ? `<span class="ab-structured__detail">${escapeHtml(String(item.reason))}</span>` : '';
      const meta = [
        item.risk_tier ? createInlineBadge(item.risk_tier, 'risk') : '',
        item.requires_approval ? createInlineBadge('approval', 'approval') : '',
      ].filter(Boolean).join('');
      return `
        <div class="ab-structured__list-item">
          <div class="ab-structured__list-main">
            <span>${escapeHtml(String(label))}</span>
            ${meta ? `<span class="ab-inline-pill-row">${meta}</span>` : ''}
          </div>
          ${reason}
        </div>
      `;
    })
    .filter(Boolean);
}

function normalizeAssignmentList(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => {
      if (typeof item === 'string') {
        return escapeHtml(item);
      }
      if (!item || typeof item !== 'object') {
        return '';
      }
      const role = item.role || item.agent;
      const task = item.task || item.description;
      if (!role && !task) {
        return '';
      }
      if (role && task) {
        return `<strong>${escapeHtml(String(role))}</strong>: ${escapeHtml(String(task))}`;
      }
      return escapeHtml(String(role || task));
    })
    .filter(Boolean);
}

function createBadge(label, value) {
  if (value === undefined || value === null || value === '') {
    return '';
  }
  return `
    <span class="ab-pill">
      <span class="ab-pill__label">${escapeHtml(label)}</span>
      <span class="ab-pill__value">${escapeHtml(String(value))}</span>
    </span>
  `;
}

function createRiskBadge(value) {
  if (!value) {
    return '';
  }
  const normalized = toClassToken(value);
  return `
    <span class="ab-pill ab-pill--risk ab-pill--risk-${escapeHtml(normalized)}">
      <span class="ab-pill__label">Risk</span>
      <span class="ab-pill__value">${escapeHtml(String(value))}</span>
    </span>
  `;
}

function boolBadge(value, label) {
  if (!value) {
    return '';
  }
  return createBadge(label, 'Yes');
}

function createInlineBadge(value, variant) {
  return `<span class="ab-inline-pill ab-inline-pill--${escapeHtml(variant)}">${escapeHtml(String(value))}</span>`;
}

function joinList(value) {
  if (!Array.isArray(value) || !value.length) {
    return '';
  }
  return value.join(', ');
}

function countValue(value) {
  if (Array.isArray(value) && value.length) {
    return String(value.length);
  }
  return '';
}

function toClassToken(value) {
  return String(value)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}
