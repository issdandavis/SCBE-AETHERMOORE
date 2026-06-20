// AetherDesktop content script — the HANDS, in your real logged-in Colab tab.
// It only ever runs an action the popup already cleared through the governed bridge (ALLOWED verdict),
// so the never-delete/L13/confirm gate is always in front of these DOM operations.

function runAll() {
  // Ctrl+F9 is Colab's "Run all" shortcut — more durable than clicking the menu.
  document.dispatchEvent(
    new KeyboardEvent('keydown', { key: 'F9', code: 'F9', keyCode: 120, ctrlKey: true, bubbles: true })
  );
  return 'run-all dispatched (Ctrl+F9)';
}

function readOutput(idx) {
  const cells = document.querySelectorAll('.cell');
  const c = cells[idx];
  if (!c) return '(cell ' + idx + ' not found; ' + cells.length + ' cells)';
  const o = c.querySelector('.output_area, .output, pre');
  return o ? (o.innerText || o.textContent || '').slice(0, 4000) : '(no output yet)';
}

function runCell(idx) {
  const cells = document.querySelectorAll('.cell');
  const c = cells[idx];
  if (!c) return '(cell ' + idx + ' not found)';
  c.scrollIntoView({ block: 'center' });
  c.click();
  c.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true, bubbles: true }));
  return 'ran cell ' + idx + ' (Ctrl+Enter)';
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  try {
    const p = msg.params || {};
    if (msg.action === 'colab_run_all') sendResponse({ ok: true, result: runAll() });
    else if (msg.action === 'colab_read_output') sendResponse({ ok: true, result: readOutput(p.cell_index) });
    else if (msg.action === 'colab_run_cell') sendResponse({ ok: true, result: runCell(p.cell_index) });
    else sendResponse({ ok: false, result: 'unsupported action: ' + msg.action });
  } catch (e) {
    sendResponse({ ok: false, result: String(e) });
  }
  return true;
});
