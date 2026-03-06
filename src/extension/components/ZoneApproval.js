export function renderZoneApproval(container, msg, onDecision) {
  const zone = msg.zone || 'RED';
  const payload = msg.payload || {};
  const seq = msg.seq;

  const card = document.createElement('div');
  card.className = `ab-zone-card ab-zone-card--${zone}`;
  card.setAttribute('role', 'alertdialog');
  card.setAttribute('aria-label', `${zone} zone approval required`);

  card.innerHTML = `
    <div class="ab-zone-card__header">
      <strong>${zone} Zone — Approval Required</strong>
    </div>
    <div class="ab-zone-card__body">
      <div><strong>URL:</strong> ${escapeHtml(payload.url || '')}</div>
      <div><strong>Action:</strong> ${escapeHtml(payload.action || '')}</div>
      <div><strong>Reason:</strong> ${escapeHtml(payload.description || '')}</div>
    </div>
    <div class="ab-zone-card__actions">
      <button class="ab-btn ab-btn--approve" data-decision="allow">Allow</button>
      <button class="ab-btn ab-btn--deny" data-decision="deny">Deny</button>
      ${zone === 'RED' ? `
        <button class="ab-btn ab-btn--secondary" data-decision="allow_once">Allow Once</button>
        <button class="ab-btn ab-btn--secondary" data-decision="add_yellow">Add to Yellow</button>
      ` : ''}
    </div>
  `;

  card.querySelectorAll('[data-decision]').forEach((btn) => {
    btn.addEventListener('click', () => {
      onDecision(seq, btn.dataset.decision);
      card.remove();
    });
  });

  container.appendChild(card);
  container.scrollTop = container.scrollHeight;
  card.querySelector('button')?.focus();
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
