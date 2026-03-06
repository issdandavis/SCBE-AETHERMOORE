export function renderSummaryCard(container, opts) {
  const card = document.createElement('details');
  card.className = 'ab-message ab-message--KO';
  card.open = true;

  card.innerHTML = `
    <summary class="ab-message__header">
      <span class="ab-message__agent">KO Summary</span>
    </summary>
    <div class="ab-message__text">${escapeHtml(opts.summary)}</div>
    ${opts.topics?.length ? `<div style="margin-top:6px;font-size:11px;color:var(--text-muted)">Topics: ${opts.topics.join(', ')}</div>` : ''}
    ${opts.sources?.length ? `<div style="margin-top:4px;font-size:11px;color:var(--text-muted)">Sources: ${opts.sources.length}</div>` : ''}
  `;
  container.appendChild(card);
  container.scrollTop = container.scrollHeight;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
