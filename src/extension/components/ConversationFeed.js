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
  const text = msg.payload?.text || msg.payload?.state || JSON.stringify(msg.payload);

  const el = document.createElement('div');
  el.className = `ab-message ab-message--${agent}`;
  el.innerHTML = `
    <div class="ab-message__header">
      <span class="ab-message__agent">${AGENT_NAMES[agent] || agent}</span>
      ${model ? `<span class="ab-message__model">${model}</span>` : ''}
    </div>
    <div class="ab-message__text">${escapeHtml(text)}</div>
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
