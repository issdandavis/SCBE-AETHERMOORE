export function renderProgress(container, msg) {
  const payload = msg.payload || {};
  const current = payload.current || 0;
  const total = payload.total || 1;
  const label = payload.label || 'Processing...';
  const pct = Math.round((current / total) * 100);

  let card = container.querySelector('.ab-progress');
  if (!card) {
    card = document.createElement('div');
    card.className = 'ab-progress';
    container.appendChild(card);
  }

  card.innerHTML = `
    <div class="ab-progress__label">${escapeHtml(label)} (${current}/${total})</div>
    <div class="ab-progress__bar">
      <div class="ab-progress__fill" style="width: ${pct}%"></div>
    </div>
  `;
  container.scrollTop = container.scrollHeight;
  if (current >= total) {
    setTimeout(() => card.remove(), 2000);
  }
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
