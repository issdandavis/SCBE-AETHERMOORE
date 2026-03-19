export function renderDisconnectedBanner(container, { port, onServerStarted }) {
  container.innerHTML = `
    <div class="ab-disconnected">
      <div class="ab-disconnected__icon">&#x26A0;</div>
      <div class="ab-disconnected__text">
        <strong>Backend not connected</strong>
        <div>Trying ws://127.0.0.1:${escapeHtml(String(port))}/ws&hellip;</div>
      </div>
      <button class="ab-btn ab-btn--secondary" id="btn-retry-connect">Retry</button>
    </div>
  `;

  const retryBtn = container.querySelector('#btn-retry-connect');
  if (retryBtn) {
    retryBtn.addEventListener('click', () => {
      if (onServerStarted) onServerStarted();
    });
  }
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
